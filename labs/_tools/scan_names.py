# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Scan every file of the course before a commit for what must never enter its history:
valid-shaped national IDs, mobiles, IBANs and card numbers, and the names of real brands,
products, apps and places. From the course root:

    uv run labs/_tools/scan_names.py

Prints each hit with its file; exits 1 when there is any. The case's own identifiers are
format-invalid on purpose (9-digit IDs and mobiles), so a hit is always worth a look. The
words of the tools slot (pgvector, OpenSearch, MCP) are allowed in course.json, the README,
the slides' notes and the sources only; they are not in the list below.
"""
from __future__ import annotations

import re
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {".git", "dist", "dist-pdf", ".shots", "out", "__pycache__", ".venv", "venv"}
TEXT = {".html", ".md", ".json", ".jsonl", ".py", ".txt", ".csv", ".toml", ".yml", ".yaml", ".mjs", ".js", ".css"}

PATTERNS = {
    "national ID (10 digits)": re.compile(r"(?<![\d-])[12]\d{9}(?!\d)"),
    "mobile (05 + 8 digits)": re.compile(r"(?<!\d)(?:\+?966|0)5\d{8}(?!\d)"),
    "IBAN": re.compile(r"\bSA\d{2}\s?(?:\d{4}\s?){5}\b"),
}
BRANDS = [
    "WhatsApp", "واتساب", "واتس اب", "Telegram", "تيليجرام", "Snapchat", "سناب", "Visa", "فيزا", "Mastercard", "ماستركارد",
    "مدى", "Absher", "أبشر", "Nafath", "نفاذ", "Tawakkalna", "توكلنا", "Balady", "بلدي", "Ejar", "إيجار", "Sakani", "سكني",
    "OpenAI", "ChatGPT", "GPT-", "Gemini", "Claude", "Anthropic", "Copilot", "Llama", "Mistral", "Azure", "AWS", "Amazon",
    "Google Cloud", "Oracle", "SAP", "Salesforce", "Microsoft", "Excel", "LibreOffice", "STC", "Riyadh", "الرياض", "Jeddah",
    "جدة", "Dammam", "الدمام", "مكة", "المدينة المنورة", "Hanwha",
]
ALLOW_FILES = {"labs/_tools/scan_names.py"}
# course-level files where the house rules name a product (the capstone submission link)
ALLOW_BRANDS_IN = {"course.json": {"Google"}, "README.md": {"Google"}}


def luhn(digits: str) -> bool:
    s = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    return s % 10 == 0


def texts(path: Path):
    if path.suffix == ".xlsx":
        import openpyxl

        wb = openpyxl.load_workbook(path, data_only=True)
        for ws in wb.worksheets:
            yield "\n".join(" ".join(str(v) for v in row if v is not None) for row in ws.iter_rows(values_only=True))
    elif path.suffix in TEXT:
        yield path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    hits = 0
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or any(part in SKIP for part in p.relative_to(ROOT).parts):
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in ALLOW_FILES:
            continue
        for t in texts(p):
            for name, rx in PATTERNS.items():
                for m in rx.finditer(t):
                    print(f"{rel}: {name}: {m.group(0)}")
                    hits += 1
            for m in re.finditer(r"(?<!\d)\d{13,19}(?!\d)", t):
                if luhn(m.group(0)):
                    print(f"{rel}: card-shaped number: {m.group(0)}")
                    hits += 1
            for b in BRANDS:
                rx = re.compile(r"(?<![\w])" + re.escape(b) + r"(?![\w])") if b.isascii() else re.compile(r"(?<![؀-ۿ])" + re.escape(b) + r"(?![؀-ۿ])")
                if rx.search(t):
                    print(f"{rel}: brand or place: {b}")
                    hits += 1
    print(f"scan: {hits} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
