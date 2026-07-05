# -*- coding: utf-8 -*-
"""架空データ生成器 ─ tenki-zero サンプル一式（架空5店舗・2026年5月）
- 売上: #12「売上集計ツール」の連携用CSV形式（日次×店舗）。渋谷/横浜/川崎/大宮は#12実サンプル由来、千葉のみ生成
- 経費: 取引先7社のバラバラ請求書(SJIS/TSV/挨拶行/合計行入り) + 経費正規化ツール出力と同形式の正規化CSV
- 勤怠: 一般的な勤怠システムのCSVエクスポート形式(SJIS)
実行: python src/gen_samples.py  (tenki-zero直下から)
"""
import os, io, csv, sys, random, datetime, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC12 = os.path.join(BASE, "..", "..", "記事12成果物", "サンプル_テスト用", "バラバラ日次テストデータ")

def P(*a): return os.path.join(BASE, *a)
for d in ["masters", "inbox/sales", "inbox/expenses", "inbox/attendance",
          "samples/請求書_受領分", "out"]:
    os.makedirs(P(*d.split("/")), exist_ok=True)

def W(rel, s, enc="utf-8-sig"):
    with open(P(*rel.split("/")), "w", encoding=enc, newline="") as f:
        f.write(s)

def num(s): return int(re.sub(r"[^\d]", "", s) or 0)

# ===== マスタ =====
W("masters/items.csv", "費目コード,費目名,区分\n"
  "COGS,仕入高,売上原価\nSAL,給与手当,販管費\nRENT,地代家賃,販管費\n"
  "UTIL,水道光熱費,販管費\nSUPL,消耗品費,販管費\nSHIP,荷造運賃,販管費\n"
  "TEL,通信費,販管費\nOUTS,外注費,販管費\nDISC,値引き,販管費\n"
  "WASTE,廃棄ロス,販管費\nDEPR,減価償却費,販管費\nLEASE,リース料,販管費\n"
  "FEE,支払手数料,販管費\nMISC,未分類,販管費\n")
W("masters/rules.csv", "取引先パターン,費目コード\n"
  "青果,COGS\nミート,COGS\n食品,COGS\n飲料,COGS\nbeverage,COGS\n水産,COGS\n"
  "不動産,RENT\n電力,UTIL\nオフィスプラス,SUPL\n急便,SHIP\nモバイル,TEL\nクリーン,OUTS\n"
  "値引,DISC\n廃棄,WASTE\n減価償却,DEPR\nリース,LEASE\n手数料,FEE\nカード,FEE\n")
W("masters/depts.csv", "部門コード,部門名\nHQ,本部\nSBY,渋谷店\nYKH,横浜店\nKWS,川崎店\nOMY,大宮店\nCHB,千葉店\n")
W("masters/holidays.csv", "日付,名称\n"
  "2026-01-01,元日\n2026-01-12,成人の日\n2026-02-11,建国記念の日\n2026-02-23,天皇誕生日\n"
  "2026-03-20,春分の日\n2026-04-29,昭和の日\n2026-05-03,憲法記念日\n2026-05-04,みどりの日\n"
  "2026-05-05,こどもの日\n2026-05-06,振替休日\n2026-07-20,海の日\n2026-08-11,山の日\n"
  "2026-09-21,敬老の日\n2026-09-22,国民の休日\n2026-09-23,秋分の日\n2026-10-12,スポーツの日\n"
  "2026-11-03,文化の日\n2026-11-23,勤労感謝の日\n")
# 製造小売ミックス: 各店に調理(製造)担当+販売パートを売上規模に応じて配置(計28人)
W("masters/employees.csv", "従業員コード,氏名,所属,給与区分,単価\n"
  "E001,三田 統括,本部,月給,350000\nE002,佐藤 企画,本部,月給,240000\nE003,岡本 事務,本部,時給,1100\n"
  "E101,鈴木 店長,渋谷店,月給,280000\nE102,田中 スタッフ,渋谷店,時給,1250\n"
  "E103,井上 調理,渋谷店,時給,1250\nE104,松本 パート,渋谷店,時給,1100\n"
  "E105,木村 パート,渋谷店,時給,1080\nE106,林 パート,渋谷店,時給,1100\nE107,山田 パート,渋谷店,時給,1080\n"
  "E201,高橋 店長,横浜店,月給,280000\nE202,伊藤 スタッフ,横浜店,時給,1200\n"
  "E203,斎藤 調理,横浜店,時給,1250\nE204,清水 パート,横浜店,時給,1080\n"
  "E205,山口 パート,横浜店,時給,1060\nE206,森 パート,横浜店,時給,1100\n"
  "E301,渡辺 店長,川崎店,月給,280000\nE302,山本 スタッフ,川崎店,時給,1150\n"
  "E303,池田 調理,川崎店,時給,1200\nE304,橋本 パート,川崎店,時給,1060\n"
  "E401,中村 店長,大宮店,月給,280000\nE402,小林 スタッフ,大宮店,時給,1150\n"
  "E403,石川 調理,大宮店,時給,1200\nE404,前田 パート,大宮店,時給,1060\nE405,阿部 パート,大宮店,時給,1050\n"
  "E501,加藤 店長,千葉店,月給,280000\nE502,吉田 スタッフ,千葉店,時給,1150\n"
  "E503,藤田 調理,千葉店,時給,1200\n")

# ===== 売上連携CSV =====
daily = {}
srcs = [("店舗A.csv", "utf-8", 0, 1, ",", 1, "大宮店"),
        ("渋谷店_uriage.csv", "utf-8", 0, 2, ",", 2, "渋谷店"),
        ("shopC.tsv", "utf-8", 0, 2, "\t", 1, "川崎店"),
        ("横浜店_sjis.csv", "cp932", 0, 2, ",", 1, "横浜店")]
for fn, enc, d_i, a_i, delim, skip, store in srcs:
    raw = open(os.path.join(SRC12, fn), "rb").read().decode(enc)
    rows = [r for r in csv.reader(io.StringIO(raw), delimiter=delim) if any(x.strip() for x in r)]
    for r in rows[skip:]:
        m = re.match(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", r[d_i])
        if not m: continue
        d = "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        daily[(d, store)] = daily.get((d, store), 0) + num(r[a_i])
mult = [0.95, 0.90, 1.00, 1.00, 1.15, 1.35, 1.20]  # 月..日
for day in range(1, 32):  # 千葉店のみ生成(POS週売上248,120円/週≒35,400円/日ベース)
    d = datetime.date(2026, 5, day)
    j = ((d.toordinal() * 13 + 7) % 11 - 5) / 100.0
    daily[(d.isoformat(), "千葉店")] = int(round(35400 * mult[d.weekday()] * (1 + j) / 100.0)) * 100
lines = ["日付,店舗,売上"] + ["%s,%s,%d" % (d, s, v) for (d, s), v in sorted(daily.items())]
W("inbox/sales/売上連携_2026-05-01_2026-05-31.csv", "\n".join(lines) + "\n")
tot_sales = sum(daily.values())
print("売上連携CSV: %d行 / 総売上 %s円" % (len(daily), format(tot_sales, ",")))

# ===== 内部経費(値引き・廃棄・減価償却・リース・カード手数料) =====
store_tot = {}
for (d, s), v in daily.items():
    store_tot[s] = store_tot.get(s, 0) + v
ie = ["日付,取引先,品目,金額"]
for s, tot in sorted(store_tot.items(), key=lambda x: -x[1]):
    ie.append("2026-05-31,社内,%s 売上値引き,%d" % (s, int(round(tot * 0.012 / 100)) * 100))
    ie.append("2026-05-31,社内,%s 廃棄ロス,%d" % (s, int(round(tot * 0.007 / 100)) * 100))
    ie.append("2026-05-25,カード会社,%s カード決済手数料,%d" % (s, int(round(tot * 0.016 / 100)) * 100))
ie.append("2026-05-31,社内,減価償却費(本部),180000")
ie.append("2026-05-05,みらいリース,設備リース料,90000")
ie.append("2026-05-05,みらいリース,車両リース料,120000")
W("inbox/expenses/内部経費_2026-05.csv", "\n".join(ie) + "\n")
print("内部経費CSV: %d行" % (len(ie) - 1))

# ===== 請求書(受領分・バラバラ) =====
rnd = random.Random(20260531)
def spread(total, items, n):
    ws = [rnd.uniform(0.6, 1.4) for _ in range(n)]; sw = sum(ws)
    amts = [int(round(total * w / sw / 100)) * 100 for w in ws]
    amts[-1] += total - sum(amts)
    days = sorted(rnd.sample(range(1, 29), k=min(n, 28)))
    return [(datetime.date(2026, 5, days[i % len(days)]).isoformat(), rnd.choice(items), amts[i]) for i in range(n)]

def yen_c(a): return '"\\{:,}"'.format(a)  # SJISでは¥=0x5C(バックスラッシュ)。#12横浜POSと同じ表記
INV = {}
rows = spread(2700000, ["野菜(葉物)", "野菜(根菜)", "果物", "青果セット"], 16)
s = "株式会社青海青果　御請求書（2026年5月分）いつもお世話になっております。\n請求日,品目,金額\n"
s += "\n".join("%s,%s,%s" % (d.replace("-", "/"), i, yen_c(a)) for d, i, a in rows) + "\n"
s += "合計,,%s\n" % yen_c(sum(a for _, _, a in rows))
INV["青海青果_請求書.csv"] = ("cp932", s)

rows = spread(3300000, ["牛肉", "豚肉", "鶏肉", "加工肉"], 14)
INV["港北ミート_請求書.csv"] = ("utf-8", "請求日,品目,金額\n" + "\n".join("%s,%s,%d" % r for r in rows) + "\n")

rows = spread(2400000, ["調味料", "乾物", "冷凍食品", "米"], 12)
s = "取引日,取引先,内容,金額\n" + "\n".join("%s,富士食品,%s,%d" % r for r in rows) + "\n"
s += "2026-05-31,富士食品,小計,%d\n" % sum(a for _, _, a in rows)
INV["富士食品_請求書.csv"] = ("utf-8", s)

rows = spread(1400000, ["soft drink", "beer", "tea", "water"], 10)
INV["yamato_beverage.tsv"] = ("utf-8", "date\titem\tamount\n" + "\n".join("%s\t%s\t%d" % r for r in rows) + "\n")

rents = [("本部", 180000), ("渋谷店", 260000), ("横浜店", 230000), ("川崎店", 200000), ("大宮店", 205000), ("千葉店", 205000)]
INV["高橋不動産_請求書.csv"] = ("utf-8", "請求日,内容,金額\n" + "\n".join("2026-05-01,%s賃料,%d" % r for r in rents) + "\n")

elec = [("本部", 28000), ("渋谷店", 72000), ("横浜店", 65000), ("川崎店", 58000), ("大宮店", 60000), ("千葉店", 59000)]
INV["関東電力_請求書.csv"] = ("cp932", "請求日,内容,金額\n" + "\n".join("2026/5/15,%s電気料金,%d" % r for r in elec) + "\n")

rows = spread(92000, ["コピー用紙", "レジロール", "洗剤・清掃用品", "文具"], 8)
INV["オフィスプラス_請求書.csv"] = ("utf-8", "日付,品目,金額\n" + "\n".join("%s,%s,%d" % r for r in rows) + "\n")
rows = spread(144000, ["店舗間配送", "仕入配送"], 4)
INV["ロジ急便_請求書.csv"] = ("utf-8", "日付,内容,金額\n" + "\n".join("%s,%s,%d" % r for r in rows) + "\n")
INV["さくらモバイル_請求書.csv"] = ("utf-8", "請求日,内容,金額\n2026-05-20,モバイル回線6回線,66000\n")

for fn, (enc, body) in INV.items():
    with open(P("samples", "請求書_受領分", fn), "w", encoding=enc, newline="") as f:
        f.write(body)
print("請求書: %dファイル生成" % len(INV))

# ===== 正規化済み経費CSV(経費正規化ツールの出力と同形式) =====
norm = []
for fn, (enc, body) in INV.items():
    vendor = re.sub(r"(_請求書|\.csv|\.tsv)", "", fn)
    delim = "\t" if fn.endswith(".tsv") else ","
    rows = [r for r in csv.reader(io.StringIO(body), delimiter=delim) if any(x.strip() for x in r)]
    hi = next(i for i, r in enumerate(rows) if any(re.search(r"日付|請求日|取引日|date", c) for c in r))
    hdr = rows[hi]
    def col(pats):
        for i, h in enumerate(hdr):
            if re.search(pats, h, re.I): return i
        return None
    di, ii, ai, vi = col(r"日付|請求日|取引日|date"), col(r"品目|内容|摘要|item"), col(r"金額|amount"), col(r"取引先")
    for r in rows[hi + 1:]:
        item = (r[ii] if ii is not None and ii < len(r) else "").strip()
        if re.search(r"合計|小計|total", item, re.I): continue
        m = re.match(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", r[di])
        if not m: continue
        d = "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        a = num(r[ai])
        v = (r[vi].strip() if vi is not None else vendor)
        if a: norm.append((d, v, item, a))
# 三崎水産(Excel請求書・水産→仕入) と 大和クリーン(PDF請求書・クリーン→外注) も正規化経費に含める
# ＝生の請求書(11ファイル)を入れても、この正規化CSVを入れても、同じ数字になるように一本化
norm += [("2026-05-06", "三崎水産", "まぐろ", 148000), ("2026-05-09", "三崎水産", "白身魚", 96000),
         ("2026-05-13", "三崎水産", "貝類", 73000), ("2026-05-16", "三崎水産", "鮭", 118000),
         ("2026-05-20", "三崎水産", "まぐろ", 139000), ("2026-05-23", "三崎水産", "青魚", 87000),
         ("2026-05-27", "三崎水産", "えび", 104000), ("2026-05-30", "三崎水産", "白身魚", 55000),
         ("2026-05-10", "大和クリーン", "店舗清掃サービス(5店舗)", 40000), ("2026-05-24", "大和クリーン", "定期清掃(本部)", 15000)]
norm.sort()
W("inbox/expenses/経費正規化_2026-05.csv",
  "\n".join(["日付,取引先,品目,金額,メモ"] + ["%s,%s,%s,%d," % r for r in norm]) + "\n")
print("正規化経費CSV: %d行 / 合計 %s円" % (len(norm), format(sum(a for *_, a in norm), ",")))

# ===== 勤怠CSV(勤怠システム出力形式・SJIS) =====
emps = [r for r in csv.reader(io.StringIO(open(P("masters", "employees.csv"), encoding="utf-8-sig").read())) if r][1:]
att = ["日付,従業員コード,氏名,所属,出勤時刻,退勤時刻,休憩時間(分),実労働時間(分)"]
rndA = random.Random(20260501)
tot_min = {}
for day in range(1, 32):
    d = datetime.date(2026, 5, day); wd = d.weekday()
    for code, name, dept, wtype, rate in emps:
        if wtype == "月給":
            if wd == 6: continue
            if wd == 5 and code in ("E001", "E002"): continue
            si = rndA.choice(["08:55", "09:00", "09:05"]); brk = 60
            work = 8 * 60 + rndA.choice([-15, 0, 0, 15, 30])
        else:
            if wd in (2, 6): continue
            si = rndA.choice(["10:00", "11:00", "12:00"]); brk = 45
            work = rndA.choice([240, 300, 300, 360, 420])
        h, m = map(int, si.split(":"))
        end = datetime.datetime(2026, 5, day, h, m) + datetime.timedelta(minutes=work + brk)
        att.append("%s,%s,%s,%s,%s,%s,%d,%d" % (d.isoformat(), code, name, dept, si, end.strftime("%H:%M"), brk, work))
        tot_min[code] = tot_min.get(code, 0) + work
with open(P("inbox", "attendance", "勤怠_2026-05.csv"), "w", encoding="cp932", newline="") as f:
    f.write("\n".join(att) + "\n")
print("勤怠CSV: %d行 (SJIS)" % (len(att) - 1))

pay = sum(int(r[4]) if r[3] == "月給" else round(tot_min.get(r[0], 0) / 60 * int(r[4])) for r in emps)
print("人件費概算: %s円" % format(pay, ","))
print("PL見込み: 売上%s / 請求書経費%s / 人件費%s" % tuple(format(x, ",") for x in (tot_sales, sum(a for *_, a in norm), pay)))
