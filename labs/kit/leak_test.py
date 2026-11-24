"""The leakage test of lab 1.2: 30 questions x 3 roles on the staff search assistant.

    uv run kit/leak_test.py                      # baseline, then files/retrieval/filter.json
    uv run kit/leak_test.py my_filter.json       # baseline, then another filter file

For every answer it compares each returned passage with the source system's access rules
(files/retrieval/source_acl.json) and writes two logs: out/leak_log_before.jsonl (the baseline
filter) and out/leak_log_after.jsonl (your filter). A leak is a passage the role may not see.
It also counts passages of any level other than «عام» that reach the generation step, and
passages labelled «عام» that carry an applicant's identifiers (a label error at the source: a
filter cannot fix it). Recall is the share of the passages the role may see, in the ideal top
five, that your filter still returns.
"""
from __future__ import annotations

import sys
from pathlib import Path

from assistant import Index, answer, check_filter, TOP_K
from common import FILES, OUT, fix, finish, has_personal_identifier, info, ok, read_json, rel, write_jsonl, arg_path

MIN_RECALL = 0.90
CAUSES = {
    "L1": "مستوى أعلى مما يحق للدور",
    "L2": "ملف طلب لغير الباحث المسند إليه",
    "L3": "مقطع بلا وسم مستوى",
}


def cause(doc: dict) -> str:
    if not doc.get("level"):
        return "L3"
    if doc.get("personal"):
        return "L2"
    return "L1"


def run(index: Index, spec: dict, queries, roles, acl) -> tuple[list[dict], dict]:
    log = []
    tally = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "SRC": 0, "ideal": 0, "kept": 0, "returned": 0}
    for q in queries:
        ranked = index.rank(q["text"])
        for role, r in roles.items():
            res = answer(index, q["text"], role, r["officer"], spec)
            ideal = [d["id"] for _, d in ranked if acl[d["id"]][role]][:TOP_K]
            got = [d["id"] for d in res["passages"]]
            tally["ideal"] += len(ideal)
            tally["kept"] += len(set(ideal) & set(got))
            tally["returned"] += len(got)
            for d in res["passages"]:
                row = {"query": q["id"], "role": role, "doc": d["id"], "label": d.get("level") or "",
                       "personal": d.get("personal", False), "assignee": d.get("assignee", ""),
                       "to_generation": d in res["generation"], "leak": "", "note": ""}
                if not acl[d["id"]][role]:
                    c = cause(d)
                    row["leak"] = c
                    tally[c] += 1
                if row["to_generation"] and d.get("level") != "عام":
                    row["note"] = "L4"
                    tally["L4"] += 1
                if d.get("level") == "عام" and has_personal_identifier(d["text"]):
                    row["note"] = (row["note"] + " SRC").strip()
                    tally["SRC"] += 1
                log.append(row)
    return log, tally


def show(name: str, t: dict) -> None:
    recall = t["kept"] / t["ideal"] if t["ideal"] else 0
    info(f"{name}: L1 {t['L1']} · L2 {t['L2']} · L3 {t['L3']} · إلى الخطوة التوليدية بغير العام (L4) {t['L4']} · "
         f"عام فيه معرّفات (SRC) {t['SRC']} · الاسترجاع {recall:.2f} · المقاطع {t['returned']}")


def main() -> int:
    spec_path = arg_path(FILES / "retrieval" / "filter.json")
    roles = read_json(FILES / "retrieval" / "roles.json")
    queries = read_json(FILES / "retrieval" / "queries.json")
    acl = read_json(FILES / "retrieval" / "source_acl.json")["acl"]
    base = read_json(FILES / "retrieval" / "filter_baseline.json")
    spec = read_json(spec_path)
    errs = check_filter(spec, list(roles))
    if errs:
        for e in errs:
            fix(f"{rel(spec_path)}: {e}")
        return finish("مرشّح يمكن تشغيله")
    index = Index()
    print(f"{len(queries)} سؤالًا × {len(roles)} أدوار على {len(index.docs)} وثيقة")
    for k, v in CAUSES.items():
        info(f"{k}: {v}")
    before_log, before = run(index, base, queries, roles, acl)
    after_log, after = run(index, spec, queries, roles, acl)
    write_jsonl(OUT / "leak_log_before.jsonl", before_log)
    write_jsonl(OUT / "leak_log_after.jsonl", after_log)
    print()
    show("قبل (المرشّح الأساسي)", before)
    show(f"بعد ({rel(spec_path)})", after)
    info("السجلان: out/leak_log_before.jsonl و out/leak_log_after.jsonl")
    print()
    leaks = after["L1"] + after["L2"] + after["L3"]
    if leaks:
        fix(f"بقي {leaks} تسربًا بعد المرشّح")
    else:
        ok("لا تسرب بعد المرشّح")
    if after["L4"]:
        fix(f"وصل {after['L4']} مقطعًا غير عام إلى الخطوة التوليدية")
    else:
        ok("الخطوة التوليدية لا تأخذ إلا العام")
    recall = after["kept"] / after["ideal"] if after["ideal"] else 0
    if recall < MIN_RECALL:
        fix(f"الاسترجاع {recall:.2f} أقل من {MIN_RECALL:.2f}: المرشّح يحجب ما يحق للأدوار رؤيته")
    else:
        ok(f"الاسترجاع {recall:.2f}")
    if after["SRC"]:
        info(f"{after['SRC']} مرة ظهر مقطع «عام» فيه معرّفات متقدم: خطأ وسم في المصدر، سجّله في label_errors.xlsx")
    return finish("سجلا الاختبار قبل المرشّح وبعده دون تسرب")


if __name__ == "__main__":
    sys.exit(main())
