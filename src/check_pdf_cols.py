# -*- coding: utf-8 -*-
"""PDF取込の回帰試験。「¥40,000」が40円で入る不具合（2026-10-23）を、二度と入れないための確認。
   python src/check_pdf_cols.py
 ・行を列に割る部分は、PyMuPDFが無くても確かめられる
 ・PyMuPDFが入っていれば、実際のPDF（1行形式／罫線の表の形）も通す"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import close

fails = []


def check(name, ok, detail=""):
    print(("  OK   " if ok else "  NG   ") + name + (("  " + detail) if detail else ""))
    if not ok:
        fails.append(name)


CASES = [
    ("桁区切りは割らない", "2026-05-10  大和クリーン  清掃委託  ¥40,000", ["2026-05-10", "大和クリーン", "清掃委託", "¥40,000"]),
    ("桁区切りが2つ", "2026-05-12  港北ミート  仕入  ¥1,234,567", ["2026-05-12", "港北ミート", "仕入", "¥1,234,567"]),
    ("カンマ区切りの行は割る", "2026-05-10,大和クリーン,清掃委託,40000", ["2026-05-10", "大和クリーン", "清掃委託", "40000"]),
    ("カンマ区切り＋桁区切り", "2026-05-10,大和クリーン,清掃委託,40,000", ["2026-05-10", "大和クリーン", "清掃委託", "40,000"]),
    ("数字のあとの区切り", "A,100,B", ["A", "100", "B"]),
    ("タブ区切り", "品目\t数量\t金額", ["品目", "数量", "金額"]),
]
for name, line, want in CASES:
    got = close.pdf_cols(line)
    check(name, got == want, "" if got == want else "got=%r" % (got,))

# 実際のPDF（PyMuPDFがある時だけ）
if close.fitz is None:
    print("  --   PyMuPDFが無いので、実際のPDFの確認は省略")
else:
    fitz = close.fitz
    tmp = tempfile.mkdtemp()

    def make(name, rows, xs):
        doc = fitz.open()
        page = doc.new_page()
        y = 80
        for r in rows:
            for x, c in zip(xs, r):
                page.insert_text((x, y), c, fontname="helv", fontsize=11)
            y += 22
        path = os.path.join(tmp, name)
        doc.save(path)
        return path

    data = [["Date", "Vendor", "Item", "Amount"], ["2026-05-10", "Yamato", "Cleaning", "\xa540,000"],
            ["2026-05-12", "Kohoku", "Meat", "\xa51,234,567"]]
    # 1行に「空白2つ以上」で並べた形
    line_pdf = make("line.pdf", [["  ".join(r)] for r in data], [50])
    w = []
    rows = close.rows_of(line_pdf, w)
    check("1行形式のPDF：金額が欠けずに入る", [r[-1] for r in rows[1:]] == ["\xa540,000", "\xa51,234,567"], "rows=%r" % (rows,))
    check("1行形式のPDF：警告なし", w == [], repr(w))
    # 罫線の表の形（セルが別々の位置にある）
    table_pdf = make("table.pdf", data, [50, 150, 260, 380])
    w = []
    rows = close.rows_of(table_pdf, w)
    check("表の形のPDF：読めたことにしない（何も取り込まない）", rows == [], repr(rows))
    check("表の形のPDF：警告が出る", len(w) == 1 and "読み取れません" in w[0], repr(w))

print("結果:", "合格" if not fails else "不合格 %d件" % len(fails))
sys.exit(1 if fails else 0)
