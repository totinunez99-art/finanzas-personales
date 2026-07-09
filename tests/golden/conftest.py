"""Descubrimiento de casos golden (docs/13). Sin PG: los tests de parser son puros."""

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = REPO_ROOT / "golden" / "cases"


def discover_cases(*, validates: str) -> list[tuple[str, Path, dict[str, Any]]]:
    """Casos activos cuyo manifiesto declara validar `validates`.
    Devuelve (id, carpeta, manifiesto) para parametrizar tests."""
    found: list[tuple[str, Path, dict[str, Any]]] = []
    if not CASES_DIR.exists():
        return found
    for manifest_path in sorted(CASES_DIR.rglob("case.yaml")):
        if "_TEMPLATE" in manifest_path.parts:
            continue
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "active":
            continue
        if validates not in manifest.get("validates", []):
            continue
        found.append((manifest["id"], manifest_path.parent, manifest))
    return found


def case_input(case_dir: Path) -> Path:
    inputs = sorted(case_dir.glob("input.*"))
    assert len(inputs) == 1, f"{case_dir}: se espera exactamente un input.*, hay {len(inputs)}"
    return inputs[0]
