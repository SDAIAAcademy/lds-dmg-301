"""The field-inspection scheduling agent of lab 2.1: two tool servers, a permission gate that
reads the permission spec, and a scripted stand-in for the model.

The tool servers and the gate run for real on the synthetic files in files/agent/. The model is
a stand-in: it follows the steps of each task in tasks.json, and it does what tool output tells
it (a step marked "when": "seen:message" happens only if an instruction inside a tool result
reached it). It never refuses on its own, so whatever is blocked is blocked by the spec.
"""
from __future__ import annotations

from common import FILES, read_json

AGENT = FILES / "agent"
MODES = ("denied", "read_only", "scoped", "approval")
# Fields that identify a person or describe them, and never need to reach the model here.
PERSONAL = ("national_id", "mobile", "family_size", "income_band", "medical_priority", "plot_note",
            "application_no", "documents")


class Servers:
    """The two tool servers: application files, and slots and messaging."""

    def __init__(self) -> None:
        self.apps = read_json(AGENT / "applications.json")["applications"]
        self.slots = read_json(AGENT / "slots.json")["slots"]
        self.catalog = {t["name"]: t for t in read_json(AGENT / "tools.json")["tools"]}
        self.roles = read_json(AGENT / "roles.json")
        self.by_handle = {a["handle"]: a for a in self.apps}

    def resolve(self, value):
        """@app:<status>:<district> and @slot:<district>:<week> stand for what the user named."""
        if isinstance(value, str) and value.startswith("@app:"):
            _, status, district = value.split(":")
            return next(a["handle"] for a in self.apps if a["status"] == status and a["district"] == district)
        if isinstance(value, str) and value.startswith("@slot:"):
            _, district, week = value.split(":")
            return next(s["slot_id"] for s in self.slots if s["district"] == district and s["week"] == int(week))
        return value

    def call(self, tool: str, args: dict):
        a = self.by_handle.get(args.get("handle", ""))
        if tool == "search_applications":
            return [x for x in self.apps if x["status"] == args.get("status") and x["district"] == args.get("district")]
        if tool == "get_application_summary":
            return [a] if a else []
        if tool == "get_application_documents":
            return [{"handle": a["handle"], "documents": f"صورة الهوية {a['national_id']}، الصك، سجل الأسرة ({a['family_size']} أفراد)",
                     "national_id": a["national_id"], "mobile": a["mobile"]}] if a else []
        if tool == "list_inspector_slots":
            return [s for s in self.slots if s["district"] == args.get("district") and s["week"] == int(args.get("week", 0))]
        if tool == "book_inspection":
            return [{"slot_id": args.get("slot_id"), "handle": args.get("handle"), "result": "حُجز"}]
        if tool == "send_sms_to_applicant":
            return [{"handle": args.get("handle"), "result": "أُرسلت إلى الرقم المسجل في الملف"}]
        if tool == "update_status":
            return [{"handle": args.get("handle"), "result": f"الحالة الآن: {args.get('status')}"}]
        if tool == "add_note":
            return [{"handle": args.get("handle"), "result": "أُضيفت الملاحظة"}]
        if tool == "send_email":
            return [{"result": f"أُرسل إلى {args.get('to')}"}]
        if tool == "export_applications_csv":
            return [{"result": "صُدّرت الطلبات كلها إلى المجلد المشترك", "rows": len(self.apps)}]
        return []


def gate(servers: Servers, spec: dict, tool: str, args: dict) -> dict:
    """Decides one call under the permission spec. Returns {allowed, why, mode, approver}."""
    rule = spec.get("tools", {}).get(tool)
    if not isinstance(rule, dict) or rule.get("mode", "denied") == "denied":
        return {"allowed": False, "mode": "denied", "why": "الأداة ممنوعة: لا تظهر للنموذج في قائمة الأدوات"}
    mode = rule.get("mode")
    if mode not in MODES:
        return {"allowed": False, "mode": str(mode), "why": f"نمط غير معروف: {mode}"}
    kind = servers.catalog.get(tool, {}).get("kind", "write")
    if mode == "read_only" and kind != "read":
        return {"allowed": False, "mode": mode, "why": "النمط للقراءة فقط، والأداة تكتب"}
    target = servers.by_handle.get(args.get("handle", ""), {})
    for k, values in (rule.get("scope") or {}).items():
        actual = args[k] if k in args else target.get(k)
        if actual is not None and str(actual) not in [str(v) for v in values]:
            return {"allowed": False, "mode": mode, "why": f"خارج النطاق: {k} = {actual}"}
    if mode == "approval":
        approver = rule.get("approver", "")
        owner = servers.roles.get("agent_owner")
        if approver not in servers.roles.get("approver_roles", []):
            return {"allowed": False, "mode": mode, "why": "لا موافق معروف لهذه الأداة"}
        if approver == owner:
            return {"allowed": False, "mode": mode, "approver": approver,
                    "why": "الموافق هو مالك الوكيل نفسه: لا فصل بين المهام"}
        return {"allowed": True, "mode": mode, "approver": approver, "why": f"بعد موافقة {approver}"}
    return {"allowed": True, "mode": mode, "why": "ضمن النطاق" if mode == "scoped" else "قراءة"}


def to_model(rule: dict, rows: list[dict]) -> list[dict]:
    """What reaches the model from a tool result: only the listed fields (none listed: all)."""
    fields = (rule or {}).get("fields") or []
    if not fields:
        return rows
    return [{k: v for k, v in r.items() if k in fields} for r in rows]


def run_task(servers: Servers, spec: dict, task: dict) -> list[dict]:
    """Runs one task with the stand-in model. Returns one event per step."""
    seen: dict[str, str] = {}
    events = []
    for step in task["steps"]:
        when = step.get("when", "")
        if when.startswith("seen:") and not seen.get(when[5:]):
            continue
        if when.startswith("unseen:") and seen.get(when[7:]):
            continue
        args = {k: servers.resolve(v) for k, v in step["args"].items()}
        decision = gate(servers, spec, step["tool"], args)
        ev = {"task": task["id"], "tool": step["tool"], "args": args, "expect": step["expect"],
              "allowed": decision["allowed"], "mode": decision["mode"], "why": decision["why"],
              "approver": decision.get("approver", ""), "fields": [], "personal": [], "injected": ""}
        if decision["allowed"]:
            rows = to_model(spec["tools"].get(step["tool"]), servers.call(step["tool"], args))
            names = sorted({k for r in rows for k in r})
            ev["fields"] = names
            ev["personal"] = [f for f in PERSONAL if f in names]
            for r in rows:
                for k, v in r.items():
                    if v not in ("", [], None):
                        seen[k] = str(v)
            msgs = [r.get("message") for r in rows if r.get("message")]
            ev["injected"] = msgs[0] if msgs else ""
        events.append(ev)
    return events


def load(spec_path):
    return Servers(), read_json(spec_path), read_json(AGENT / "tasks.json")
