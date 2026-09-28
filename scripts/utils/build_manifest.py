"""PACKAGING UTILITY — run only before final archive creation.

This script **writes** ``MANIFEST_SHA256.csv``, the digest of the package as
distributed. It is deliberately **not** part of ``run_all.py``: a normal
reproduction run must never rewrite distributed package content.

Use it exactly once per release, after the package content is final and before
the archive is created:

    python scripts/utils/build_manifest.py

To check a package against its manifest, use
``scripts/utils/verify_manifest.py`` (which only reads).

The manifest lists every distributed file except the generated reproduction
outputs (``outputs_reproduced/``), interpreter caches, and the manifest itself,
which cannot contain its own digest.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Never leave interpreter caches inside the distributed package tree.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import paths  # noqa: E402
from utils.hashing import sha256_file  # noqa: E402

MANIFEST_NAME = "MANIFEST_SHA256.csv"
EXCLUDED_PREFIXES = ("outputs_reproduced/",)
# Runtime caches are not distributed content: they are recreated by the
# interpreter and their byte content depends on the interpreter build.
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".pyd")


def classify(relative_path: str) -> tuple[str, str, str]:
    """Return (role, frozen_or_generated, required_for_reproduction)."""
    if relative_path.startswith("data/frozen_inputs/"):
        return ("frozen_analytical_input", "frozen", "yes")
    if relative_path.startswith("data/validation_windows/"):
        return ("frozen_validation_window_input", "frozen", "level_b_optional")
    if relative_path.startswith("data/external_sources/"):
        return ("upstream_source_documentation", "authored", "no")
    if relative_path.startswith("config/WP-MORPH-05C_"):
        return ("frozen_method_contract_document", "frozen", "no")
    if relative_path.startswith("config/"):
        return ("reproduction_configuration", "authored", "yes")
    if relative_path.startswith("original_frozen_scripts/"):
        return ("historical_provenance_script", "frozen", "no")
    if relative_path.startswith("outputs_expected/"):
        return ("expected_reference_output", "frozen", "no")
    if relative_path.startswith("scripts/"):
        return ("reproduction_script", "authored", "yes")
    if relative_path.startswith("tests/"):
        return ("reproduction_test", "authored", "yes")
    if relative_path.startswith("manuscript_mapping/"):
        return ("manuscript_traceability", "generated", "no")
    if relative_path == "run_all.py":
        return ("one_command_entry_point", "authored", "yes")
    if relative_path in {"run_all.bat", "run_all.ps1"}:
        return ("convenience_launcher", "authored", "no")
    if relative_path == "environment.yml":
        return ("environment_definition", "authored", "yes")
    if relative_path == "requirements-lock.txt":
        return ("dependency_lock", "authored", "yes")
    if relative_path == "pyproject.toml":
        return ("project_metadata", "authored", "no")
    if relative_path in {"README.md", "REPRODUCIBILITY.md", "DATA_DICTIONARY.md", "METHODS_MAPPING.md"}:
        return ("documentation", "authored", "no")
    if relative_path in {"LICENSE.md", "CITATION.cff"}:
        return ("package_metadata", "authored", "no")
    return ("other", "authored", "no")


def collect(package_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(package_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(package_root).as_posix()
        if relative == MANIFEST_NAME or relative.startswith(EXCLUDED_PREFIXES):
            continue
        if EXCLUDED_PARTS.intersection(Path(relative).parts):
            continue
        if relative.endswith(EXCLUDED_SUFFIXES):
            continue
        role, kind, required = classify(relative)
        rows.append(
            {
                "relative_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": role,
                "frozen_or_generated": kind,
                "required_for_reproduction": required,
            }
        )
    return rows


def write_manifest(package_root: Path, rows: list[dict[str, object]], target: Path) -> Path:
    columns = [
        "relative_path",
        "size_bytes",
        "sha256",
        "role",
        "frozen_or_generated",
        "required_for_reproduction",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return target


def build(package_root: Path | None = None) -> tuple[Path, int]:
    root = Path(package_root) if package_root else paths.PACKAGE_ROOT
    rows = collect(root)
    target = write_manifest(root, rows, root / MANIFEST_NAME)
    return target, len(rows)


def main() -> int:
    print("PACKAGING UTILITY: rebuilding the distribution manifest.")
    print("This must only be run immediately before final archive creation.")
    target, count = build()
    print(f"manifest written : {target}")
    print(f"files listed     : {count}")
    print(f"manifest sha256  : {sha256_file(target)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
