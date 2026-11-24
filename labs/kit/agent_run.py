"""Runs the scheduling agent of lab 2.1 on one task, or all twelve, and prints its trace.
From labs/:

    uv run kit/agent_run.py                         # all tasks, files/agent/permissions.json
    uv run kit/agent_run.py T07                     # one task
    uv run kit/agent_run.py sms-free                # the stretch task
    uv run kit/agent_run.py T07 my_spec.json        # another spec file

The model is a scripted stand-in (see kit/agent.py): no model is called. The trace is written to
out/agent_log.jsonl.
"""
from __future__ import annotations

import sys
from pathlib import Path

from agent import AGENT, load, run_task
from common import OUT, rel, write_jsonl

args = sys.argv[1:]
which = next((a for a in args if not a.endswith(".json")), "all")
spec_arg = next((a for a in args if a.endswith(".json")), None)
spec_path = (Path(spec_arg) if Path(spec_arg).is_absolute() else Path.cwd() / spec_arg) if spec_arg else AGENT / "permissions.json"

servers, spec, tasks = load(spec_path)
pool = tasks["tasks"] + tasks.get("extra", [])
chosen = pool if which == "all" else [t for t in pool if t["id"] == which]
if not chosen:
    print(f"[FIX] لا مهمة بهذا المعرّف: {which}. المعرّفات: " + "، ".join(t["id"] for t in pool))
    sys.exit(2)
if which == "all":
    chosen = tasks["tasks"]

listed = [n for n, r in spec.get("tools", {}).items() if isinstance(r, dict) and r.get("mode", "denied") != "denied"]
print(f"المواصفة: {rel(spec_path)}")
print(f"الأدوات الظاهرة للنموذج ({len(listed)}): " + "، ".join(listed))
log = []
for task in chosen:
    print()
    print(f"[{task['id']}] {task['request']}")
    for ev in run_task(servers, spec, task):
        log.append(ev)
        shown = ", ".join(f"{k}={v}" for k, v in ev["args"].items())
        verdict = "نُفّذ" if ev["allowed"] else "مُنع"
        print(f"  {ev['tool']}({shown})")
        print(f"     {verdict} · {ev['mode']} · {ev['why']}")
        if ev["allowed"]:
            print(f"     إلى النموذج: {', '.join(ev['fields']) or 'لا شيء'}")
        if ev["personal"]:
            print(f"     ! حقول شخصية وصلت إلى النموذج: {', '.join(ev['personal'])}")
        if ev["injected"]:
            print(f"     ! نص من مخرجات الأداة وصل إلى النموذج: «{ev['injected']}»")

write_jsonl(OUT / "agent_log.jsonl", log)
print()
print(f"السجل: {rel(OUT / 'agent_log.jsonl')}")
