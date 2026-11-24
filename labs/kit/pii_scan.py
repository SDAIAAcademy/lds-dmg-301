"""Scan the passages labelled «عام» in the index for the shapes of an applicant's identifiers
(a national ID or a mobile number in this case's synthetic formats). From labs/:

    uv run kit/pii_scan.py

A hit is a label error at the source: the document was published or labelled «عام» while it
carries personal data. A label filter cannot catch it; the data steward must relabel it.
"""
from __future__ import annotations

import sys

from common import FILES, has_personal_identifier, read_jsonl


def main() -> int:
    docs = read_jsonl(FILES / "retrieval" / "index.jsonl")
    public = [d for d in docs if d.get("level") == "عام"]
    hits = [d for d in public if has_personal_identifier(d["text"])]
    print(f"فُحص {len(public)} مقطعًا موسومًا «عام»؛ وُجدت معرّفات في {len(hits)}:")
    for d in hits:
        print(f"- {d['id']} {d['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
