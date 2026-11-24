"""Check the list of label errors at the source that lab 1.2 hands to the data steward. From labs/:

    uv run kit/label_errors_check.py [files/retrieval/label_errors.xlsx]

It says how many documents of each kind of error your list holds, never which ones are missing.
"""
from __future__ import annotations

import sys

from common import FILES, arg_path, finish, fix, key, ok, read_sheet, rel

GROUPS = {
    "d1_missing_level": "مقاطع بلا وسم مستوى",
    "d2_missing_assignee": "ملفات طلبات بلا مسند إليه",
    "d3_public_with_identifiers": "وثائق «عام» فيها معرّفات متقدم",
}


def main() -> int:
    path = arg_path(FILES / "retrieval" / "label_errors.xlsx")
    rows = read_sheet(path, "أخطاء الوسم")
    k = key("lab_1_2")
    listed = {r.get("الوثيقة", "") for r in rows if r.get("الوثيقة")}
    if not rows:
        fix(f"{rel(path)} فارغ: سجّل كل وثيقة فيها خطأ وسم في المصدر")
        return finish("قائمة أخطاء الوسم لممثل البيانات")
    for r in rows:
        if not r.get("ما يُطلب من ممثل البيانات"):
            fix(f"{r.get('الوثيقة', '?')}: اكتب ما يُطلب من ممثل البيانات")
    known = set().union(*map(set, (k[g] for g in GROUPS)))
    extra = sorted(listed - known)
    if extra:
        fix(f"{len(extra)} وثيقة في قائمتك ليس فيها خطأ وسم في المصدر")
    for g, label in GROUPS.items():
        found = len(listed & set(k[g]))
        total = len(k[g])
        (ok if found == total else fix)(f"{label}: {found} من {total}")
    return finish("قائمة أخطاء الوسم لممثل البيانات")


if __name__ == "__main__":
    sys.exit(main())
