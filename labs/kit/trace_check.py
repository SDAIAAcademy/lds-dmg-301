"""Checks the incident trace of lab 2.2 (files/incident/trace.xlsx, sheet «التتبع»). From labs/:

    uv run kit/trace_check.py [file]

It says which items do not match yet, never the right value.
"""
from __future__ import annotations

from common import FILES, arg_path, finish, fix, key, ok, read_sheet

path = arg_path(FILES / "incident" / "trace.xlsx")
rows = read_sheet(path, "التتبع")
ref = key("lab_2_2")


def same(item: str, given: str, right) -> bool:
    given = given.strip()
    if item.startswith("window_"):
        return given.replace(" ", "T")[:16] == str(right)[:16]
    if isinstance(right, int):
        try:
            return int(float(given)) == right
        except ValueError:
            return False
    return given == str(right)


empty = [r["البند"] for r in rows if not r.get("إجابتك")]
if len(empty) == len(rows):
    fix(f"{len(rows)} بندًا بلا إجابة: املأ عمود «إجابتك»")
else:
    good = 0
    for r in rows:
        item = r["البند"]
        if item not in ref:
            continue
        if not r.get("إجابتك"):
            fix(f"{item}: بلا إجابة")
        elif same(item, r["إجابتك"], ref[item]):
            good += 1
        else:
            fix(f"{item}: لا يطابق بعد. {r['السؤال']}")
    if good == len(rows):
        ok(f"البنود كلها تطابق ({good})")
raise SystemExit(finish("تتبع الحادثة"))
