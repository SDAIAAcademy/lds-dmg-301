"""The staff search assistant of the Land Grants Service, as a small stand-in you can read.

It ranks the indexed passages for a question (BM25 over Arabic tokens), applies the label
filter of files/retrieval/filter.json before ranking (mode "pre") or after it (mode "post"),
returns the top five passages, and passes to its generation step only the passages whose
level is in generation_levels. The generation step is scripted: it calls no model, it only
records what a model would have received.

Ask one question as one role:

    uv run kit/assistant.py front_desk "ما المستندات المطلوبة لطلب المنحة"
    uv run kit/assistant.py committee "ما قررته اللجنة في نقاط الأولوية" files/retrieval/filter.json
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

from common import FILES, LEVELS, read_json, read_jsonl, tokens

TOP_K = 5


class Index:
    def __init__(self, path: Path = FILES / "retrieval" / "index.jsonl"):
        self.docs = read_jsonl(path)
        self.by_id = {d["id"]: d for d in self.docs}
        self.tf = [Counter(tokens(d["title"] + " " + d["text"])) for d in self.docs]
        self.len = [sum(t.values()) for t in self.tf]
        self.avg = sum(self.len) / len(self.len)
        df = Counter()
        for t in self.tf:
            df.update(t.keys())
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def rank(self, query: str) -> list[tuple[float, dict]]:
        q = tokens(query)
        out = []
        for d, tf, ln in zip(self.docs, self.tf, self.len):
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if f:
                    s += self.idf[w] * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * ln / self.avg))
            if s > 0:
                out.append((s, d))
        out.sort(key=lambda x: (-x[0], x[1]["id"]))
        return out


def check_filter(spec: dict, roles: list[str]) -> list[str]:
    """Problems in a filter spec that would make the run meaningless; empty when it is usable."""
    errs = []
    if spec.get("mode", "pre") not in ("pre", "post"):
        errs.append("mode يجب أن يكون pre أو post")
    if spec.get("missing_label") not in ("allow", "deny"):
        errs.append("missing_label يجب أن يكون allow أو deny")
    for lv in spec.get("generation_levels", []):
        if lv not in LEVELS:
            errs.append(f"مستوى غير معروف في generation_levels: {lv}")
    for r in roles:
        rs = spec.get("roles", {}).get(r)
        if not isinstance(rs, dict):
            errs.append(f"لا يوجد إعداد للدور {r} في roles")
            continue
        for lv in rs.get("levels", []):
            if lv not in LEVELS:
                errs.append(f"مستوى غير معروف للدور {r}: {lv}")
        if rs.get("cases") not in ("none", "assigned", "all"):
            errs.append(f"cases للدور {r} يجب أن يكون none أو assigned أو all")
    return errs


def allowed(doc: dict, role: str, officer: str, spec: dict) -> bool:
    level = doc.get("level", "")
    if not level:
        return spec.get("missing_label") == "allow"
    rs = spec["roles"][role]
    if level not in rs.get("levels", []):
        return False
    if doc.get("personal"):
        rule = rs.get("cases", "none")
        if rule == "none":
            return False
        if rule == "assigned":
            return bool(doc.get("assignee")) and doc.get("assignee") == officer
    return True


def answer(index: Index, query: str, role: str, officer: str, spec: dict) -> dict:
    ranked = index.rank(query)
    if spec.get("mode", "pre") == "pre":
        passages = [d for _, d in ranked if allowed(d, role, officer, spec)][:TOP_K]
    else:
        passages = [d for _, d in ranked[:TOP_K] if allowed(d, role, officer, spec)]
    gen = [d for d in passages if d.get("level") in spec.get("generation_levels", [])]
    return {"passages": passages, "generation": gen}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    role, query = sys.argv[1], sys.argv[2]
    spec = read_json(Path(sys.argv[3]) if len(sys.argv) > 3 else FILES / "retrieval" / "filter.json")
    roles = read_json(FILES / "retrieval" / "roles.json")
    if role not in roles:
        print(f"[FIX] دور غير معروف: {role}. الأدوار: {', '.join(roles)}")
        return 2
    errs = check_filter(spec, list(roles))
    if errs:
        for e in errs:
            print(f"[FIX] {e}")
        return 2
    res = answer(Index(), query, role, roles[role]["officer"], spec)
    print(f"الدور: {roles[role]['name']}   السؤال: {query}")
    for d in res["passages"]:
        to_gen = "← إلى الخطوة التوليدية" if d in res["generation"] else "مقتطف يُعرض كما هو"
        print(f"- {d['id']} [{d.get('level') or 'بلا وسم'}] {d['title']}  ({to_gen})")
    if not res["passages"]:
        print("لا مقاطع مسموحة لهذا الدور.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
