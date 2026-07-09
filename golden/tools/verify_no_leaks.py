"""Escáner de fugas de datos personales en golden/cases (docs/13 §3).

Detecta: RUT chileno, tarjetas (Luhn 13-19 dígitos), emails, y términos de una
lista local prohibida (golden/originals/forbidden_terms.txt, gitignored — nombres
reales del usuario). Corre en CI vía tests/golden/test_no_leaks.py.

Uso directo: python golden/tools/verify_no_leaks.py
"""

import re
import sys
from pathlib import Path

RUT_DOTTED = re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[0-9kK]\b")
RUT_PLAIN = re.compile(r"\b\d{7,8}-[0-9kK]\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")

SCANNED_SUFFIXES = {".csv", ".json", ".yaml", ".yml", ".txt", ".eml", ".md", ".html"}


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _forbidden_terms(repo_root: Path) -> list[str]:
    path = repo_root / "golden" / "originals" / "forbidden_terms.txt"
    if not path.exists():
        return []
    return [t.strip().lower() for t in path.read_text(encoding="utf-8").splitlines() if t.strip()]


def scan_text(text: str, terms: list[str]) -> list[str]:
    findings: list[str] = []
    for pattern, label in ((RUT_DOTTED, "RUT"), (RUT_PLAIN, "RUT"), (EMAIL, "email")):
        for match in pattern.finditer(text):
            findings.append(f"{label}: {match.group(0)}")
    for match in CARD_CANDIDATE.finditer(text):
        digits = re.sub(r"[ -]", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            findings.append(f"posible tarjeta (Luhn): {match.group(0)}")
    lowered = text.lower()
    findings.extend(f"término prohibido: {term}" for term in terms if term in lowered)
    return findings


def scan_cases(repo_root: Path) -> list[str]:
    cases_dir = repo_root / "golden" / "cases"
    terms = _forbidden_terms(repo_root)
    findings: list[str] = []
    for path in sorted(cases_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(
            f"{path.relative_to(repo_root)} -> {finding}" for finding in scan_text(text, terms)
        )
    return findings


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    findings = scan_cases(repo_root)
    if findings:
        print("FUGAS DETECTADAS — prohibido commitear:")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print("Sin fugas detectadas en golden/cases.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
