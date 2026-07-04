# -*- coding: utf-8 -*-
"""tenki-zero ─ 月次締め（転記ゼロ）

使い方:
    python close.py 2026-05          … コマンドで締める
    python app.py                    … ブラウザの受付画面から使う（推奨）

inbox/ に放り込まれた〈売上・経費・勤怠〉を読み、SQLite（数字の泉）を作り直し、
out/YYYY-MM/ に月次帳票一式（CSV/HTML/Excel）を出力する。

設計原則:
  - 源流で一度だけ記録（数字の住所は1か所）→ 転記は構造的に存在しない
  - 判断は人（masters/ の費目・ルール）、適用は機械
  - 出力は専門システム（会計ソフト・税理士）に渡す直前まで
  - 現実データは汚い前提: SJIS/UTF-8自動判定・列名ゆれ吸収・¥カンマ除去・重複自動排除
  - CSVだけなら標準ライブラリのみで動く。Excel/PDFの取込とExcel帳票は“借り物”
    （openpyxl / PyMuPDF ― requirements.txt）を入れた時だけ有効になる
"""
import os, io, csv, re, sys, sqlite3, datetime

# 借り物の部品はlib/に同梱済み(=増築済みでお届け)。venv等に自前導入があればそちらでも動く
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
try:
    import openpyxl                     # 借り物① Excel読み書き
except ImportError:
    openpyxl = None
try:
    import fitz                         # 借り物② PDF読み取り(PyMuPDF)
except ImportError:                     # 32bit環境や他OSでは同梱版が動かない場合あり→CSV機能のみで続行
    fitz = None

BASE = os.path.dirname(os.path.abspath(__file__))
J = os.path.join

# ---------- 汚いデータ吸収 ----------
def smart_read(path):
    raw = open(path, "rb").read()
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8")
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")

def rows_of(path, warnings):
    """CSV/TSV/Excel/PDF を同じ「行の表」に揃える"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        if not openpyxl:
            warnings.append("openpyxl未導入のためExcelをスキップ: " + os.path.basename(path))
            return []
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        return [[("" if c is None else str(c)) for c in row]
                for row in ws.iter_rows(values_only=True)
                if any(c is not None and str(c).strip() for c in row)]
    if ext == ".pdf":
        if not fitz:
            warnings.append("PyMuPDF未導入のためPDFをスキップ: " + os.path.basename(path))
            return []
        doc = fitz.open(path)
        lines = []
        for page in doc:
            lines += [l for l in page.get_text().splitlines() if l.strip()]
        rows = [re.split(r"[,\t]|\s{2,}", l.strip()) for l in lines]
        if not any(len(r) >= 2 for r in rows):
            warnings.append("PDFから表を読み取れませんでした（AIに『CSVにして』と頼むのが早道です）: "
                            + os.path.basename(path))
        return rows
    text = smart_read(path).replace("\r\n", "\n").replace("\r", "\n")
    delim = "\t" if text.count("\t") > text.count(",") else ","
    return [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]

def num(s):
    t = re.sub(r"[^0-9.\-]", "", str(s))
    try:
        return float(t)
    except ValueError:
        return 0.0

def dt(s):
    m = re.match(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", str(s).strip())
    return "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

ALIAS = {
    "date": ["日付", "請求日", "取引日", "営業日", "伝票日付", "date"],
    "store": ["店舗", "店名", "所属", "store"],
    "amount": ["売上", "金額", "請求額", "税込金額", "金額(税込)", "amount", "total"],
    "vendor": ["取引先", "仕入先", "請求元", "支払先", "vendor"],
    "item": ["品目", "内容", "摘要", "品名", "item"],
    "emp": ["従業員コード", "社員コード", "emp"],
    "minutes": ["実労働時間(分)", "労働時間(分)", "実労働分", "minutes"],
}
def header_map(hdr):
    m = {}
    for i, h in enumerate(hdr):
        k = str(h).strip()
        for field, names in ALIAS.items():
            if k in names:
                m[field] = i
    return m

def read_table(path, need, warnings):
    rows = rows_of(path, warnings)
    for hi in range(min(10, len(rows))):
        m = header_map(rows[hi])
        if all(k in m for k in need):
            out = []
            for r in rows[hi + 1:]:
                rec = {k: (str(r[i]).strip() if i < len(r) else "") for k, i in m.items()}
                out.append(rec)
            return out
    if rows:
        warnings.append("ヘッダを見つけられずスキップ: " + os.path.basename(path))
    return []

def load_master(name):
    p = J(BASE, "masters", name)
    return [r for r in csv.reader(io.StringIO(smart_read(p))) if any(c.strip() for c in r)][1:]

def vendor_from_filename(path):
    return re.sub(r"(_請求書|請求書?|_invoice|invoice)$", "",
                  os.path.splitext(os.path.basename(path))[0], flags=re.I)

# ---------- 取込 → SQLite（重複は自動排除・毎回作り直し＝冪等） ----------
def build_db(month, warnings):
    items = {c: (n, g) for c, n, g in load_master("items.csv")}
    rules = load_master("rules.csv")
    emps = {r[0]: r for r in load_master("employees.csv")}

    con = sqlite3.connect(J(BASE, "out", "tenki.sqlite"))
    con.executescript("""
      DROP TABLE IF EXISTS sales;      CREATE TABLE sales(date TEXT, store TEXT, amount REAL, src TEXT);
      DROP TABLE IF EXISTS expenses;   CREATE TABLE expenses(date TEXT, vendor TEXT, item TEXT, amount REAL,
                                          item_code TEXT, item_name TEXT, src TEXT);
      DROP TABLE IF EXISTS attendance; CREATE TABLE attendance(date TEXT, emp TEXT, name TEXT, store TEXT,
                                          minutes REAL, src TEXT);
    """)
    dedup = {"sales_replaced": 0, "expenses_skipped": 0, "attendance_replaced": 0}
    month_of = lambda d: d and d[:7] == month
    scan = lambda sub: [J(BASE, "inbox", sub, f) for f in sorted(os.listdir(J(BASE, "inbox", sub)))
                        if not f.startswith(".")
                        and f.lower().endswith((".csv", ".tsv", ".txt", ".xlsx", ".xlsm", ".pdf"))]

    # 売上: 同一(日付,店舗)は後から読んだものが優先(再アップロード=上書き)
    sales = {}
    for p in scan("sales"):
        for r in read_table(p, ("date", "amount"), warnings):
            d = dt(r.get("date"))
            if not (month_of(d) and num(r.get("amount"))):
                continue
            store = r.get("store") or vendor_from_filename(p)
            key = (d, store)
            if key in sales:
                dedup["sales_replaced"] += 1
            sales[key] = (num(r["amount"]), os.path.basename(p))
    for (d, s), (a, src) in sales.items():
        con.execute("INSERT INTO sales VALUES(?,?,?,?)", (d, s, a, src))

    # 経費: 完全一致行(日付,取引先,品目,金額)の重複はスキップ。合計/小計行も除外
    seen = set()
    for p in scan("expenses"):
        fallback = vendor_from_filename(p)
        for r in read_table(p, ("date", "amount"), warnings):
            d = dt(r.get("date"))
            item = r.get("item", "")
            if re.search(r"合計|小計|total", item, re.I):
                continue
            if not (month_of(d) and num(r.get("amount"))):
                continue
            vendor = r.get("vendor") or fallback
            key = (d, vendor, item, round(num(r["amount"])))
            if key in seen:
                dedup["expenses_skipped"] += 1
                continue
            seen.add(key)
            code = "MISC"
            for pat, c in rules:
                if pat.lower() in vendor.lower():
                    code = c
                    break
            con.execute("INSERT INTO expenses VALUES(?,?,?,?,?,?,?)",
                        (d, vendor, item, num(r["amount"]), code,
                         items.get(code, (code, ""))[0], os.path.basename(p)))

    # 勤怠: 同一(日付,従業員)は後勝ち
    att = {}
    for p in scan("attendance"):
        for r in read_table(p, ("date", "emp", "minutes"), warnings):
            d = dt(r.get("date"))
            if not month_of(d):
                continue
            key = (d, r["emp"])
            if key in att:
                dedup["attendance_replaced"] += 1
            e = emps.get(r["emp"])
            att[key] = (r.get("name", e[1] if e else ""), e[2] if e else r.get("store", ""),
                        num(r["minutes"]), os.path.basename(p))
    for (d, emp), (name, store, mins, src) in att.items():
        con.execute("INSERT INTO attendance VALUES(?,?,?,?,?,?)", (d, emp, name, store, mins, src))

    con.commit()
    return con, items, emps, dedup

# ---------- 帳票 ----------
def yen(n): return "¥{:,}".format(round(n))
def wcsv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def payroll(con, emps):
    out = []
    for code, (c, name, dept, wtype, rate) in sorted(emps.items()):
        mins = con.execute("SELECT COALESCE(SUM(minutes),0), COUNT(DISTINCT date) FROM attendance WHERE emp=?",
                           (code,)).fetchone()
        base = int(rate) if wtype == "月給" else round(mins[0] / 60 * int(rate))
        out.append([code, name, dept, wtype, rate, mins[1], round(mins[0] / 60, 1), base])
    return out

def close(month):
    warnings = []
    outdir = J(BASE, "out", month)
    os.makedirs(outdir, exist_ok=True)
    con, items, emps, dedup = build_db(month, warnings)

    sales_total = con.execute("SELECT COALESCE(SUM(amount),0) FROM sales").fetchone()[0]
    if not sales_total:
        return {"ok": False, "error": "%s の売上データが見つかりません。inbox/sales/ を確認してください。" % month,
                "warnings": warnings}
    by_store = con.execute("SELECT store, SUM(amount) FROM sales GROUP BY store ORDER BY 2 DESC").fetchall()
    by_day = con.execute("SELECT date, SUM(amount) FROM sales GROUP BY date ORDER BY 1").fetchall()
    exp = con.execute("SELECT item_code, item_name, SUM(amount), COUNT(*) FROM expenses GROUP BY 1,2 ORDER BY 3 DESC").fetchall()
    misc = con.execute("SELECT date, vendor, item, amount FROM expenses WHERE item_code='MISC'").fetchall()
    pay = payroll(con, emps)
    pay_total = sum(r[7] for r in pay)
    cogs = sum(a for c, n, a, k in exp if items.get(c, ("", ""))[1] == "売上原価")
    sga_inv = [(n, a) for c, n, a, k in exp if items.get(c, ("", ""))[1] != "売上原価"]
    sga_total = sum(a for _, a in sga_inv) + pay_total
    gross = sales_total - cogs
    op = gross - sga_total

    pl_rows = [["売上高", round(sales_total), ""],
               ["売上原価(仕入高)", round(cogs), "経費データより"],
               ["売上総利益", round(gross), "粗利率 {:.1f}%".format(gross / sales_total * 100)],
               ["給与手当", pay_total, "勤怠データより"]]
    pl_rows += [[n, round(a), "請求書より"] for n, a in sorted(sga_inv, key=lambda x: -x[1])]
    pl_rows += [["販管費計", round(sga_total), ""],
                ["営業利益", round(op), "営業利益率 {:.1f}%".format(op / sales_total * 100)]]
    wcsv(J(outdir, "01_月次損益.csv"), ["科目", "金額", "備考"], pl_rows)

    exp_total = cogs + sum(a for _, a in sga_inv)
    exp_rows = [[n, round(a), k, round(a / exp_total * 100, 1)] for c, n, a, k in exp]
    wcsv(J(outdir, "02_経費内訳_費目別.csv"), ["費目", "金額", "明細数", "構成比%"], exp_rows)
    store_rows = [[s, round(a), round(a / sales_total * 100, 1)] for s, a in by_store]
    wcsv(J(outdir, "03_売上計上_店舗別.csv"), ["店舗", "売上", "構成比%"], store_rows)
    att = con.execute("SELECT emp, name, store, COUNT(DISTINCT date), SUM(minutes) FROM attendance GROUP BY 1,2,3 ORDER BY 1").fetchall()
    wcsv(J(outdir, "04_勤怠集計.csv"), ["従業員コード", "氏名", "所属", "出勤日数", "実労働時間(h)"],
         [[e, n, s, d, round(m / 60, 1)] for e, n, s, d, m in att])
    wcsv(J(outdir, "05_給与もと資料.csv"),
         ["従業員コード", "氏名", "所属", "給与区分", "単価", "出勤日数", "実労働時間(h)", "基本支給額(もと)"], pay)
    dept_pay = {}
    for r in pay:
        dept_pay[r[2]] = dept_pay.get(r[2], 0) + r[7]
    dept_rows = [[s, round(a), dept_pay.get(s, 0), round(dept_pay.get(s, 0) / a * 100, 1)] for s, a in by_store]
    wcsv(J(outdir, "06_部門別実績.csv"), ["部門", "売上", "人件費(もと)", "人件費率%"], dept_rows)

    j = [[d, "売上高", "", round(a), "売上計上 " + s, s] for d, s, a in
         con.execute("SELECT date, store, amount FROM sales ORDER BY date").fetchall()]
    j += [[d, i2, c, round(a), (v + " " + it).strip(), ""] for d, v, it, a, c, i2 in
          con.execute("SELECT date, vendor, item, amount, item_code, item_name FROM expenses ORDER BY date").fetchall()]
    wcsv(J(outdir, "08_税理士パック_仕訳候補.csv"), ["日付", "科目", "費目コード", "金額", "摘要", "部門"], j)
    wcsv(J(outdir, "09_月次収支サマリ.csv"), ["区分", "金額"],
         [["収入(売上)", round(sales_total)], ["支出(経費+給与もと)", round(cogs + sga_total)],
          ["差引", round(sales_total - cogs - sga_total)]])

    dashboard(outdir, month, sales_total, gross, op, pay_total, cogs, by_store, by_day, exp, items, misc, dept_pay)
    if openpyxl:
        excel_report(outdir, month, pl_rows, exp_rows, store_rows, dept_rows)
    else:
        warnings.append("openpyxl未導入のためExcel帳票(10_月次報告.xlsx)は省略（requirements.txt参照）")

    outputs = sorted(f for f in os.listdir(outdir) if not f.startswith("."))
    return {"ok": True, "month": month, "sales": round(sales_total), "gross": round(gross),
            "gross_rate": round(gross / sales_total * 100, 1), "op": round(op),
            "op_rate": round(op / sales_total * 100, 1), "misc": len(misc),
            "dedup": dedup, "warnings": warnings, "outdir": outdir, "outputs": outputs}

def excel_report(outdir, month, pl_rows, exp_rows, store_rows, dept_rows):
    """役員会議・銀行提出にそのまま使えるExcelブック（借り物openpyxl使用）"""
    wb = openpyxl.Workbook()
    bold = openpyxl.styles.Font(bold=True)
    fill = openpyxl.styles.PatternFill("solid", fgColor="1F4E79")
    white = openpyxl.styles.Font(bold=True, color="FFFFFF")
    def sheet(name, header, rows, money_cols):
        ws = wb.create_sheet(name)
        ws.append(header)
        for c in ws[1]:
            c.font = white
            c.fill = fill
        for r in rows:
            ws.append(r)
        for col in money_cols:
            for cell in ws[openpyxl.utils.get_column_letter(col)][1:]:
                cell.number_format = "#,##0"
        for i, _ in enumerate(header, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 18
        return ws
    wb.remove(wb.active)
    sheet("月次損益", ["科目", "金額", "備考"], pl_rows, [2])
    sheet("経費内訳", ["費目", "金額", "明細数", "構成比%"], exp_rows, [2])
    sheet("店舗別売上", ["店舗", "売上", "構成比%"], store_rows, [2])
    sheet("部門別実績", ["部門", "売上", "人件費(もと)", "人件費率%"], dept_rows, [2, 3])
    wb["月次損益"]["E1"] = "%s 月次報告（tenki-zero自動出力）" % month
    wb["月次損益"]["E1"].font = bold
    wb.save(J(outdir, "10_月次報告_%s.xlsx" % month))

# ---------- 役員ダッシュボード ----------
def svg_bars(pairs, color, fmt=lambda v: "¥" + format(round(v / 1000), ",") + "k"):
    W, H, pl, pb, pt = 640, 220, 10, 30, 22
    if not pairs:
        return ""
    mx = max(v for _, v in pairs)
    n = len(pairs)
    gap = (W - pl * 2) / n
    bw = min(56, gap * 0.62)
    b = ""
    for i, (lab, v) in enumerate(pairs):
        x = pl + gap * i + (gap - bw) / 2
        h = (H - pt - pb) * (v / mx)
        y = pt + (H - pt - pb) - h
        b += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
              '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="10.5" fill="#c3d2e4">%s</text>'
              '<text x="%.1f" y="%d" text-anchor="middle" font-size="11" fill="#aebccd">%s</text>'
              % (x, y, bw, h, color, x + bw / 2, y - 4, fmt(v), x + bw / 2, H - pb + 15, lab))
    return '<svg viewBox="0 0 %d %d" width="100%%" style="max-width:680px">%s</svg>' % (W, H, b)

def dashboard(outdir, month, sales, gross, op, pay_total, cogs, by_store, by_day, exp, items, misc, dept_pay):
    wd = ["月", "火", "水", "木", "金", "土", "日"]
    wsum = {}
    for d, a in by_day:
        w = wd[datetime.date(*map(int, d.split("-"))).weekday()]
        wsum[w] = wsum.get(w, 0) + a
    top_wd = max(wsum, key=wsum.get)
    top_store, top_amt = by_store[0]
    low_store, low_amt = by_store[-1]
    sga_exp = [(n, a) for c, n, a, k in exp if items.get(c, ("", ""))[1] != "売上原価"]
    comments = [
        "売上トップは %s（%s・構成比 %.1f%%）。最下位 %s（%s）との差は %.1f倍 ―― てこ入れ余地の目安。"
        % (top_store, yen(top_amt), top_amt / sales * 100, low_store, yen(low_amt), top_amt / max(low_amt, 1)),
        "曜日では %s曜が最大（%s）。仕込み・シフトは%s曜に厚く。" % (top_wd, yen(wsum[top_wd]), top_wd),
        "原価率 %.1f%%（仕入 %s）。粗利率 %.1f%%。" % (cogs / sales * 100, yen(cogs), gross / sales * 100),
        "人件費率 %.1f%%（給与もと %s）。店舗別の人件費率は 06_部門別実績 を参照。" % (pay_total / sales * 100, yen(pay_total)),
        "販管費で大きいのは %s。" % "、".join("%s %s" % (n, yen(a)) for n, a in sorted(sga_exp, key=lambda x: -x[1])[:3]),
    ]
    comments.append("未分類の経費が %d件。masters/rules.csv にルール追加を。" % len(misc) if misc
                    else "経費の未分類は 0件 ―― 仕分けルールは健在です。")
    kpi = (("売上高", yen(sales)), ("売上総利益", yen(gross)), ("営業利益", yen(op)),
           ("原価率", "%.1f%%" % (cogs / sales * 100)), ("人件費率", "%.1f%%" % (pay_total / sales * 100)))
    kpis = "".join('<div class="kpi"><div class="v">%s</div><div class="k">%s</div></div>' % (v, k) for k, v in kpi)
    daily = svg_bars([(d[8:], a) for d, a in by_day][::3], "#5aa2e6")
    stores = svg_bars(by_store, "#37c39a")
    expsvg = svg_bars([(n, a) for c, n, a, k in exp][:7], "#f5a524")
    lis = "".join("<li>%s</li>" % c for c in comments)
    html = """<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<title>役員ダッシュボード %(m)s</title><style>
body{margin:0;font-family:"Segoe UI","Yu Gothic UI",Meiryo,sans-serif;color:#e9f0fa;line-height:1.6;
 background:linear-gradient(165deg,#0a1020,#0c162b 55%%,#0a1224);min-height:100vh}
.wrap{max-width:1000px;margin:0 auto;padding:24px 18px}
h1{font-size:1.4rem;background:linear-gradient(112deg,#fff,#8fd0ff 60%%,#ffd67a);-webkit-background-clip:text;color:transparent}
.card{background:rgba(16,25,44,.66);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:16px 20px;margin:14px 0}
h3{font-size:1rem;color:#eaf3ff;border-left:4px solid #5aa2e6;padding-left:10px}
.kpis{display:flex;gap:12px;flex-wrap:wrap}
.kpi{flex:1;min-width:140px;background:linear-gradient(158deg,rgba(74,150,235,.22),rgba(13,22,42,.66));
 border:1px solid rgba(255,255,255,.1);border-radius:13px;padding:12px 14px}
.kpi .v{font-size:1.3rem;font-weight:800;color:#eaf4ff}.kpi .k{font-size:.74rem;color:#9fb2c9}
li{margin:.35em 0}.muted{color:#8ea1b8;font-size:.8rem}
</style></head><body><div class="wrap">
<h1>役員ダッシュボード ─ %(m)s</h1>
<div class="card"><div class="kpis">%(kpis)s</div></div>
<div class="card"><h3>分析コメント（自動生成）</h3><ul>%(lis)s</ul></div>
<div class="card"><h3>店舗別 売上</h3>%(stores)s</div>
<div class="card"><h3>日次売上の推移（3日おき）</h3>%(daily)s</div>
<div class="card"><h3>経費 費目別（上位）</h3>%(expsvg)s</div>
<p class="muted">tenki-zero 自動出力 ─ 数字の出所: inbox/（売上・経費・勤怠）。転記は行われていません。</p>
</div></body></html>""" % dict(m=month, kpis=kpis, lis=lis, stores=stores, daily=daily, expsvg=expsvg)
    with open(J(outdir, "07_役員ダッシュボード.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    if len(sys.argv) != 2 or not re.match(r"^\d{4}-\d{2}$", sys.argv[1]):
        print("使い方: python close.py YYYY-MM   例: python close.py 2026-05")
        sys.exit(1)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = close(sys.argv[1])
    if not r["ok"]:
        print("エラー:", r["error"])
        sys.exit(1)
    print("=== %s 月次締め 完了 ===" % r["month"])
    print("売上 %s ／ 粗利 %s(%.1f%%) ／ 営業利益 %s(%.1f%%)"
          % (yen(r["sales"]), yen(r["gross"]), r["gross_rate"], yen(r["op"]), r["op_rate"]))
    d = r["dedup"]
    if any(d.values()):
        print("重複排除: 売上上書き%d件 / 経費スキップ%d件 / 勤怠上書き%d件"
              % (d["sales_replaced"], d["expenses_skipped"], d["attendance_replaced"]))
    print("未分類: %d件%s" % (r["misc"], " → masters/rules.csv にルール追加を" if r["misc"] else "（なし）"))
    for w in r["warnings"]:
        print("注意:", w)
    print("出力先:", r["outdir"])
