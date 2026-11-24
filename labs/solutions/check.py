"""Run every lab's reference solution through the kit and assert its numbers. From labs/:

    uv run solutions/check.py            # every lab
    uv run solutions/check.py 1.2 2.1    # some of them

For each lab the supplied starting files must NOT pass (they still hold the task, and the tool
must not crash on them), and the reference files in solutions/reference/ must pass with the
numbers the slides and the trainer notes quote. No lab calls a language model. Outputs go to
out/, which you may delete. For the trainer, lab 1.1 also prints each row's decision against
the key, which the participant's check never prints.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")


def run(*args: str) -> tuple[int, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, *args], cwd=LABS, capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout + p.stderr


def expect(cmd: list[str], code: int, *needles: str) -> str:
    c, text = run(*cmd)
    assert c == code, f"{' '.join(cmd)}: exit {c}, expected {code}\n{text[-2500:]}"
    assert "Traceback" not in text, f"{' '.join(cmd)} crashed\n{text[-2500:]}"
    for n in needles:
        assert re.search(n, text), f"{' '.join(cmd)}: missing {n!r}\n{text[-2500:]}"
    return text


def lab_1_1() -> None:
    expect(["kit/eligibility_check.py", "files/eligibility/requests.xlsx"], 1, "12 طلبًا بلا قرار")
    t = expect(["kit/eligibility_check.py", "solutions/reference/decisions_reference.xlsx"], 0,
               "الأحكام المطابقة للمفتاح: 12 من 12", "RESULT: PASS")
    print([l for l in t.splitlines() if "المطابقة" in l][0])
    sys.path.insert(0, str(LABS / "kit"))
    from common import read_sheet  # noqa: E402
    key = json.loads((LABS / "solutions/reference/lab_1_1.json").read_text(encoding="utf-8"))
    rows = read_sheet(LABS / "solutions/reference/decisions_reference.xlsx", "القرارات")
    counts = {}
    for r in rows:
        assert r["القرار"] == key[r["الطلب"]]["decision"]
        counts[r["القرار"]] = counts.get(r["القرار"], 0) + 1
    assert counts == {"مسموح": 4, "مشروط": 4, "محظور": 4}, counts
    print("lab 1.1 key:", "، ".join(f"{k} {v}" for k, v in counts.items()))


def lab_1_2() -> None:
    t = expect(["kit/leak_test.py"], 1, r"قبل \(المرشّح الأساسي\): L1 48 · L2 17 · L3 28 · .*L4\) 237", "بقي 93 تسربًا")
    t = expect(["kit/leak_test.py", "solutions/reference/filter_reference.json"], 0,
               r"L1 0 · L2 0 · L3 0 · .*L4\) 0 .*الاسترجاع 0\.96", "RESULT: PASS")
    print([l for l in t.splitlines() if "بعد" in l][0].strip())
    post = json.loads((LABS / "solutions/reference/filter_reference.json").read_text(encoding="utf-8"))
    post["mode"] = "post"
    out = LABS / "out"
    out.mkdir(exist_ok=True)
    (out / "filter_post.json").write_text(json.dumps(post, ensure_ascii=False), encoding="utf-8")
    t = expect(["kit/leak_test.py", "out/filter_post.json"], 1, "الاسترجاع")
    print("post-filter (stretch):", [l for l in t.splitlines() if "بعد" in l][0].strip())
    expect(["kit/pii_scan.py"], 0, "وُجدت معرّفات في 4")
    expect(["kit/label_errors_check.py"], 1, "فارغ")
    t = expect(["kit/label_errors_check.py", "solutions/reference/label_errors_reference.xlsx"], 0,
               "مقاطع بلا وسم مستوى: 18 من 18", "ملفات طلبات بلا مسند إليه: 10 من 10", "4 من 4", "RESULT: PASS")


def lab_2_1() -> None:
    t = expect(["kit/agent_test.py"], 1, "RESULT: 16 to fix", "T07 send_email", "T07 list_inspector_slots",
               "T10 get_application_summary: national_id, mobile")
    expect(["kit/agent_run.py", "T07"], 0, "surveys@contractor.example")
    t = expect(["kit/agent_test.py", "solutions/reference/permissions_reference.json"], 0,
               r"نُفّذت كلها \(10\)", r"مُنعت كلها \(8\)", "لا حقل شخصي", "RESULT: PASS")
    expect(["kit/agent_run.py", "sms-free", "solutions/reference/permissions_reference.json"], 0,
           "مُنع · approval · خارج النطاق: template_id")
    expect(["kit/agent_run.py", "sms-free"], 0, "نُفّذ · scoped")
    # segregation of duties: the owner approving its own agent fails the test
    spec = json.loads((LABS / "solutions/reference/permissions_reference.json").read_text(encoding="utf-8"))
    spec["tools"]["send_sms_to_applicant"]["approver"] = "رئيس الخدمات الرقمية"
    out = LABS / "out"
    out.mkdir(exist_ok=True)
    (out / "spec_owner.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    expect(["kit/agent_test.py", "out/spec_owner.json"], 1, "هو مالك الوكيل")
    print("lab 2.1: open spec 16 to fix; reference passes 10 allowed, 8 blocked")


def lab_2_2() -> None:
    key = json.loads((LABS / "solutions/reference/lab_2_2.json").read_text(encoding="utf-8"))
    assert (key["requests_to_b_summarise"], key["requests_with_restricted"], key["requests_with_secret"],
            key["distinct_applications"]) == (423, 419, 32, 80), key
    expect(["kit/log_query.py", "--step", "summarise", "--route", "provider_b"], 0, "الطلبات: 423", "المختلفة في هذه المقاطع: 80")
    expect(["kit/log_query.py", "--from", "2026-10-06T14:05", "--to", "2026-10-08T10:40", "--route", "provider_b"], 0, "الطلبات: 440")
    expect(["kit/log_query.py", "--step", "summarise", "--route", "provider_b", "--level", "مقيد"], 0, "الطلبات: 419")
    expect(["kit/log_query.py", "--step", "summarise", "--route", "provider_b", "--level", "سري"], 0, "الطلبات: 32")
    expect(["kit/trace_check.py"], 1, "بلا إجابة")
    expect(["kit/trace_check.py", "solutions/reference/trace_reference.xlsx"], 0, r"تطابق \(12\)", "RESULT: PASS")
    expect(["kit/terms_check.py"], 1, "فارغة")
    expect(["kit/terms_check.py", "solutions/reference/checklist_reference.xlsx"], 0, "16 من 16", "RESULT: PASS")
    print("lab 2.2: 423 requests to B, 419 with Restricted, 32 with Secret, 80 applications; 440 if translation is counted")


LABS_ALL = {"1.1": lab_1_1, "1.2": lab_1_2, "2.1": lab_2_1, "2.2": lab_2_2}


def main() -> int:
    which = sys.argv[1:] or list(LABS_ALL)
    for lab in which:
        print(f"== lab {lab}")
        LABS_ALL[lab]()
        print(f"lab {lab}: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
