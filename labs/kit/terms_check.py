"""Checks the provider checklist and the decision of lab 2.2 (files/incident/checklist.xlsx).
From labs/:

    uv run kit/terms_check.py [file]

Sheet «قائمة التحقق»: for each item and each provider, the clause number and whether the terms
are acceptable to the municipality (نعم, لا or بشرط). Sheet «القرار»: for each level, the decision
for each provider and use (مسموح, مشروط or محظور). It prints counts only, and stops at once on
a decision that sends non-Public data to the external provider.
"""
from __future__ import annotations

from common import FILES, LEVELS, arg_path, finish, fix, key, ok, read_sheet

path = arg_path(FILES / "incident" / "checklist.xlsx")
ref = key("lab_2_2_terms")
items = read_sheet(path, "قائمة التحقق")
dec = read_sheet(path, "القرار")
ANSWERS = ("نعم", "لا", "بشرط")
DECISIONS = ("مسموح", "مشروط", "محظور")
COLS = ["أ: نموذج توليدي", "أ: خدمة غير توليدية", "ب: نموذج توليدي", "ب: خدمة غير توليدية"]

filled = [r for r in items if r.get("مقبول لدى الأمانة؟ أ") or r.get("مقبول لدى الأمانة؟ ب")]
if not filled:
    fix("قائمة التحقق فارغة: لكل بند رقم البند في الشروط، ونعم أو لا أو بشرط لكل مزوّد")
else:
    acc = clause = 0
    for r in items:
        name = r["البند"]
        want = ref["acceptable"].get(name)
        if not want:
            continue
        for i, p in enumerate(("أ", "ب")):
            given = r.get(f"مقبول لدى الأمانة؟ {p}", "")
            if given and given not in ANSWERS:
                fix(f"{name} ({p}): «{given}» ليست من {', '.join(ANSWERS)}")
            acc += given == want[i]
            cl = r.get(f"ما تقوله شروط {p} (رقم البند)", "")
            clause += ref["clauses"][p][name].split()[0] in cl
        for crit in ref["critical"]:
            if name == crit and r.get("مقبول لدى الأمانة؟ ب", "") != want[1]:
                fix(f"بند حاسم لم يُحكم عليه كما ينبغي للمزوّد ب: {name}")
    total = 2 * len(ref["acceptable"])
    (ok if acc >= total - 2 else fix)(f"أحكام القبول المطابقة: {acc} من {total} (المطلوب {total - 2} فأكثر)")
    (ok if clause >= total - 2 else fix)(f"أرقام البنود المطابقة: {clause} من {total} (المطلوب {total - 2} فأكثر)")

if not any(r.get(c) for r in dec for c in COLS):
    fix("ورقة «القرار» فارغة: لكل مستوى حكم لكل مزوّد واستخدام")
else:
    good = 0
    for r in dec:
        lv = r["المستوى"]
        if lv not in LEVELS:
            continue
        for i, c in enumerate(COLS):
            given = r.get(c, "")
            if given and given not in DECISIONS:
                fix(f"القرار، {lv}، {c}: «{given}» ليست من {', '.join(DECISIONS)}")
            if c.startswith("ب") and lv != "عام" and given in ("مسموح", "مشروط"):
                fix(f"القرار يرسل «{lv}» إلى المزوّد ب ({c}): خدمة خارج المملكة")
            good += given == ref["decision"][lv][i]
    (ok if good == 16 else fix)(f"خلايا القرار المطابقة: {good} من 16")
raise SystemExit(finish("قائمة التحقق والقرار"))
