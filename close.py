# -*- coding: utf-8 -*-
"""tenki-zero ─ 月次締め（転記ゼロ）

使い方:
    python close.py 2026-05

inbox/ に放り込まれた〈売上・経費・勤怠〉を読み、SQLite（数字の泉）を作り直し、
out/YYYY-MM/ に月次帳票一式を出力する。手作業は「未分類の確認」と「税理士へ渡す」だけ。

設計原則:
  - 源流で一度だけ記録（数字の住所は1か所）→ 転記は構造的に存在しない
  - 判断は人（masters/ の費目・ルール）、適用は機械
  - 出力は専門システム（会計ソフト・税理士）に渡す直前まで
  - 現実データは汚い前提: SJIS/UTF-8自動判定・列名ゆれ吸収・¥カンマ除去
"""
import os, io, csv, re, sys, sqlite3, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
J = os.path.join

# ---------- 汚いデータ吸収（#12と同じ思想） ----------
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

def rows_of(path):
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

ALIAS = {  # 列名の表記ゆれ → 正規名
    "date": ["日付", "請求日", "取引日", "営業日", "date"],
    "store": ["店舗", "店名", "所属", "store"],
    "amount": ["売上", "金額", "請求額", "amount"],
    "vendor": ["取引先", "仕入先", "請求元", "vendor"],
    "item": ["品目", "内容", "摘要", "item"],
    "memo": ["メモ", "備考", "memo"],
    "emp": ["従業員コード", "社員コード", "emp"],
    "name": ["氏名", "名前", "name"],
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

def read_table(path, need):
    """ヘッダ行を自動検出して {正規名:値} の行リストに"""
    rows = rows_of(path)
    for hi in range(min(8, len(rows))):
        m = header_map(rows[hi])
        if all(k in m for k in need):
            out = []
            for r in rows[hi + 1:]:
                rec = {k: (r[i].strip() if i < len(r) else "") for k, i in m.items()}
                out.append(rec)
            return out
    print("  ! ヘッダ不明のためスキップ:", os.path.basename(path))
    return []

def load_master(name):
    p = J(BASE, "masters", name)
    return [r for r in csv.reader(io.StringIO(smart_read(p))) if any(c.strip() for c in r)][1:]

# ---------- 取込 → SQLite（数字の泉・毎回作り直し＝冪等） ----------
def build_db(month):
    items = {c: (n, g) for c, n, g in load_master("items.csv")}
    rules = load_master("rules.csv")                      # [pattern, item_code]
    emps = {r[0]: r for r in load_master("employees.csv")}  # code -> row

    con = sqlite3.connect(J(BASE, "out", "tenki.sqlite"))
    con.executescript("""
      DROP TABLE IF EXISTS sales;      CREATE TABLE sales(date TEXT, store TEXT, amount REAL, src TEXT);
      DROP TABLE IF EXISTS expenses;   CREATE TABLE expenses(date TEXT, vendor TEXT, item TEXT, amount REAL,
                                          item_code TEXT, item_name TEXT, src TEXT);
      DROP TABLE IF EXISTS attendance; CREATE TABLE attendance(date TEXT, emp TEXT, name TEXT, store TEXT,
                                          minutes REAL, src TEXT);
    """)
    def month_of(d): return d and d[:7] == month

    scan = lambda sub: [J(BASE, "inbox", sub, f) for f in sorted(os.listdir(J(BASE, "inbox", sub)))
                        if f.lower().endswith((".csv", ".tsv", ".txt"))]
    for p in scan("sales"):
        for r in read_table(p, ("date", "store", "amount")):
            d = dt(r["date"])
            if month_of(d) and num(r["amount"]):
                con.execute("INSERT INTO sales VALUES(?,?,?,?)", (d, r["store"], num(r["amount"]), os.path.basename(p)))
    for p in scan("expenses"):
        for r in read_table(p, ("date", "vendor", "amount")):
            d = dt(r["date"])
            if not (month_of(d) and num(r["amount"])):
                continue
            code = "MISC"
            for pat, c in rules:
                if pat.lower() in r["vendor"].lower():
                    code = c
                    break
            con.execute("INSERT INTO expenses VALUES(?,?,?,?,?,?,?)",
                        (d, r["vendor"], r.get("item", ""), num(r["amount"]),
                         code, items.get(code, (code, ""))[0], os.path.basename(p)))
    for p in scan("attendance"):
        for r in read_table(p, ("date", "emp", "minutes")):
            d = dt(r["date"])
            if month_of(d):
                e = emps.get(r["emp"])
                con.execute("INSERT INTO attendance VALUES(?,?,?,?,?,?)",
                            (d, r["emp"], r.get("name", e[1] if e else ""), e[2] if e else r.get("store", ""),
                             num(r["minutes"]), os.path.basename(p)))
    con.commit()
    return con, items, emps

# ---------- 帳票 ----------
def yen(n): return "¥{:,}".format(round(n))
def wcsv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def payroll(con, emps):
    """給与のもと資料（勤怠×単価。所得税・社保の本演算はしない＝専門側）"""
    out = []
    for code, (c, name, dept, wtype, rate) in sorted(emps.items()):
        mins = con.execute("SELECT COALESCE(SUM(minutes),0), COUNT(DISTINCT date) FROM attendance WHERE emp=?",
                           (code,)).fetchone()
        hours, days = round(mins[0] / 60, 1), mins[1]
        base = int(rate) if wtype == "月給" else round(mins[0] / 60 * int(rate))
        out.append([code, name, dept, wtype, rate, days, hours, base])
    return out

def close(month):
    outdir = J(BASE, "out", month)
    os.makedirs(outdir, exist_ok=True)
    con, items, emps = build_db(month)

    sales_total = con.execute("SELECT COALESCE(SUM(amount),0) FROM sales").fetchone()[0]
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

    # 01 月次損益
    pl_rows = [["売上高", round(sales_total), ""],
               ["売上原価(仕入高)", round(cogs), "経費データより"],
               ["売上総利益", round(gross), "粗利率 {:.1f}%".format(gross / sales_total * 100 if sales_total else 0)],
               ["給与手当", pay_total, "勤怠データより"]]
    pl_rows += [[n, round(a), "請求書より"] for n, a in sorted(sga_inv, key=lambda x: -x[1])]
    pl_rows += [["販管費計", round(sga_total), ""],
                ["営業利益", round(op), "営業利益率 {:.1f}%".format(op / sales_total * 100 if sales_total else 0)]]
    wcsv(J(outdir, "01_月次損益.csv"), ["科目", "金額", "備考"], pl_rows)

    # 02〜06
    wcsv(J(outdir, "02_経費内訳_費目別.csv"), ["費目", "金額", "明細数", "構成比%"],
         [[n, round(a), k, round(a / (cogs + sum(x for _, x in sga_inv)) * 100, 1)] for c, n, a, k in exp])
    wcsv(J(outdir, "03_売上計上_店舗別.csv"), ["店舗", "売上", "構成比%"],
         [[s, round(a), round(a / sales_total * 100, 1)] for s, a in by_store])
    att = con.execute("SELECT emp, name, store, COUNT(DISTINCT date), SUM(minutes) FROM attendance GROUP BY 1,2,3 ORDER BY 1").fetchall()
    wcsv(J(outdir, "04_勤怠集計.csv"), ["従業員コード", "氏名", "所属", "出勤日数", "実労働時間(h)"],
         [[e, n, s, d, round(m / 60, 1)] for e, n, s, d, m in att])
    wcsv(J(outdir, "05_給与もと資料.csv"),
         ["従業員コード", "氏名", "所属", "給与区分", "単価", "出勤日数", "実労働時間(h)", "基本支給額(もと)"], pay)
    dept_pay = {}
    for r in pay:
        dept_pay[r[2]] = dept_pay.get(r[2], 0) + r[7]
    wcsv(J(outdir, "06_部門別実績.csv"), ["部門", "売上", "人件費(もと)", "人件費率%"],
         [[s, round(a), dept_pay.get(s, 0), round(dept_pay.get(s, 0) / a * 100, 1)] for s, a in by_store])

    # 08 税理士パック（仕訳候補＝専門システムへ渡す直前まで）
    j = [[d, "売上高", "", round(a), "売上計上 " + s, s] for d, s, a in
         con.execute("SELECT date, store, amount FROM sales ORDER BY date").fetchall()]
    j += [[d, i2, c, round(a), v + " " + it, ""] for d, v, it, a, c, i2 in
          con.execute("SELECT date, vendor, item, amount, item_code, item_name FROM expenses ORDER BY date").fetchall()]
    wcsv(J(outdir, "08_税理士パック_仕訳候補.csv"), ["日付", "科目", "費目コード", "金額", "摘要", "部門"], j)

    # 09 月次収支サマリ
    wcsv(J(outdir, "09_月次収支サマリ.csv"), ["区分", "金額"],
         [["収入(売上)", round(sales_total)], ["支出(経費+給与もと)", round(cogs + sga_total)],
          ["差引", round(sales_total - cogs - sga_total)]])

    # 07 役員ダッシュボード（数字＋グラフ＋分析）
    dashboard(outdir, month, sales_total, gross, op, pay_total, cogs, by_store, by_day, exp, items, misc, dept_pay)

    print("=== %s 月次締め 完了 ===" % month)
    print("売上 %s ／ 粗利 %s(%.1f%%) ／ 営業利益 %s(%.1f%%)" %
          (yen(sales_total), yen(gross), gross / sales_total * 100, yen(op), op / sales_total * 100))
    print("未分類: %d件 %s" % (len(misc), "→ 02_経費内訳とmasters/rules.csvを確認" if misc else "(なし)"))
    print("出力先:", outdir)

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
    # 分析コメント（ルールベース・数字の根拠つき）
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
    daily = svg_bars([(d[8:], a) for d, a in by_day][::3], "#5aa2e6")  # 3日おき表示
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
<p class="muted">tenki-zero 自動出力 ─ 数字の出所: inbox/（売上連携CSV・経費正規化CSV・勤怠CSV）。転記は行われていません。</p>
</div></body></html>""" % dict(m=month, kpis=kpis, lis=lis, stores=stores, daily=daily, expsvg=expsvg)
    with open(J(outdir, "07_役員ダッシュボード.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    if len(sys.argv) != 2 or not re.match(r"^\d{4}-\d{2}$", sys.argv[1]):
        print("使い方: python close.py YYYY-MM   例: python close.py 2026-05")
        sys.exit(1)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    close(sys.argv[1])
