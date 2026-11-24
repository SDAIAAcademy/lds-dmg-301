"""Check the eligibility matrix of lab 1.1. From labs/:

    uv run kit/eligibility_check.py [files/eligibility/requests.xlsx]

It reads the sheet «القرارات», checks that every row is complete, and says how many decisions
match the key: the count only, never which rows. Passing: ten of twelve or more, and no
Restricted-or-higher data sent to an external model.
"""
from __future__ import annotations

import re
import sys

from common import FILES, LEVELS, arg_path, finish, fix, key, ok, read_sheet, rel

DECISIONS = ["مسموح", "مشروط", "محظور"]
RULES = {f"N{i}" for i in range(1, 8)} | {f"M{i}" for i in range(1, 9)}
NEEDED = 10


def main() -> int:
    path = arg_path(FILES / "eligibility" / "requests.xlsx")
    rows = {r.get("الطلب", ""): r for r in read_sheet(path, "القرارات")}
    k = key("lab_1_1")
    empty = 0
    for rid in k:
        r = rows.get(rid)
        if not r or not r.get("القرار"):
            empty += 1
            continue
        if r["القرار"] not in DECISIONS:
            fix(f"{rid}: القرار يجب أن يكون واحدًا من: {'، '.join(DECISIONS)}")
        ids = set(re.findall(r"[NM]\d", r.get("القواعد", "").upper()))
        if not ids:
            fix(f"{rid}: اذكر القواعد التي بنيت عليها الحكم (مثل N1، M4)")
        elif ids - RULES:
            fix(f"{rid}: قاعدة غير موجودة في rules.md: {'، '.join(sorted(ids - RULES))}")
        if r["القرار"] == "مشروط" and not r.get("الشروط"):
            fix(f"{rid}: الحكم مشروط بلا شروط مكتوبة")
        if not r.get("المبرر"):
            fix(f"{rid}: اكتب المبرر في جملة")
    if empty:
        fix(f"{empty} طلبًا بلا قرار في {rel(path)}")
        return finish("مصفوفة الأهلية")
    match = sum(1 for rid, v in k.items() if rows[rid]["القرار"] == v["decision"])
    external = sum(1 for rid, v in k.items()
                   if v["tier"] == "خارجي" and LEVELS.index(v["level"]) >= 1 and rows[rid]["القرار"] != "محظور")
    if external:
        fix(f"{external} حكمًا يرسل بيانات «مقيد» فأعلى إلى نموذج خارجي: هذا يُسقط المصفوفة مهما بلغت المطابقة")
    (ok if match >= NEEDED else fix)(f"الأحكام المطابقة للمفتاح: {match} من {len(k)} (المطلوب {NEEDED})")
    return finish("مصفوفة أهلية تطابق المفتاح في عشرة طلبات من اثني عشر")


if __name__ == "__main__":
    sys.exit(main())
