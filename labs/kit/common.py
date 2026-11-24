"""Shared helpers of the LDS-DMG-301 lab kit. Run every kit command from the labs/ folder:

    uv run kit/<command>.py [file]

Each check reads a file you filled, prints [OK] and [FIX] lines and ends with
RESULT: PASS or RESULT: n to fix. A check never prints the reference answer itself.
No command calls a language model: the assistant's generation step and the agent's model are
scripted stand-ins, and everything else runs for real on the synthetic case files.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
FILES = LABS / "files"
KEYS = LABS / "solutions" / "reference"
OUT = LABS / "out"

LEVELS = ["عام", "مقيد", "سري", "سري للغاية"]

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

PROBLEMS: list[str] = []


def ok(text: str) -> None:
    print(f"[OK]  {text}")


def fix(text: str) -> None:
    PROBLEMS.append(text)
    print(f"[FIX] {text}")


def info(text: str) -> None:
    print(f"      {text}")


def finish(evidence: str) -> int:
    print()
    if PROBLEMS:
        print(f"RESULT: {len(PROBLEMS)} to fix. النتيجة: بنود تحتاج إصلاحًا (العدد: {len(PROBLEMS)}) قبل: {evidence}")
        return 1
    print(f"RESULT: PASS. النتيجة: تحقق {evidence}")
    return 0


def clean(v) -> str:
    if v is None:
        return ""
    return " ".join(str(v).split())


def rel(path: Path) -> str:
    """A path for printing: relative to labs/, never a path on this computer."""
    try:
        return path.resolve().relative_to(LABS).as_posix()
    except ValueError:
        return path.name


def arg_path(default: Path, index: int = 1) -> Path:
    if len(sys.argv) > index:
        p = Path(sys.argv[index])
        return p if p.is_absolute() else (Path.cwd() / p)
    return default


def read_json(path: Path):
    if not path.exists():
        print(f"[FIX] الملف غير موجود: {rel(path)}")
        sys.exit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[FIX] {rel(path)} ليس JSON صالحًا: السطر {e.lineno}، العمود {e.colno}: {e.msg}")
        print("      أكثر الأسباب: فاصلة زائدة قبل } أو ]، أو علامة تنصيص ناقصة.")
        sys.exit(2)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def read_sheet(path: Path, name: str) -> list[dict]:
    import openpyxl

    if not path.exists():
        print(f"[FIX] الملف غير موجود: {rel(path)}")
        sys.exit(2)
    wb = openpyxl.load_workbook(path, data_only=True)
    if name not in wb.sheetnames:
        print(f"[FIX] لا توجد ورقة باسم {name} في {path.name}")
        sys.exit(2)
    rows = list(wb[name].iter_rows(values_only=True))
    head = [clean(h) for h in rows[0]]
    out = []
    for r in rows[1:]:
        if all(clean(v) == "" for v in r):
            continue
        out.append({h: clean(v) for h, v in zip(head, r) if h})
    return out


def key(name: str):
    """A reference key the checks compare with (solutions/reference/<name>.json). A trainee copy
    of the course has no solutions folder: the trainer runs the check then."""
    path = KEYS / f"{name}.json"
    if not path.exists():
        print("[FIX] مفتاح المرجع غير موجود في هذه النسخة (solutions/reference). اطلب من المدرب تشغيل الفحص.")
        sys.exit(2)
    return json.loads(path.read_text(encoding="utf-8"))


# Arabic text: a light normaliser and tokenizer for the search index of lab 1.2
_AR_NORM = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"})
_DIACRITICS = re.compile(r"[ً-ْـ]")
_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال")


def tokens(text: str) -> list[str]:
    text = _DIACRITICS.sub("", text).translate(_AR_NORM).lower()
    out = []
    for w in re.findall(r"[\w-]+", text):
        for p in _PREFIXES:
            if w.startswith(p) and len(w) - len(p) >= 3:
                w = w[len(p):]
                break
        if len(w) >= 2:
            out.append(w)
    return out


# Shapes of personal identifiers in this case: the case's synthetic IDs have 9 digits and its
# mobiles 9 digits starting 05, on purpose, so that no value is a valid real number.
ID_SHAPE = re.compile(r"(?<!\d)1\d{8}(?!\d)")
MOBILE_SHAPE = re.compile(r"(?<!\d)05\d{7}(?!\d)")


def has_personal_identifier(text: str) -> bool:
    return bool(ID_SHAPE.search(text) or MOBILE_SHAPE.search(text))
