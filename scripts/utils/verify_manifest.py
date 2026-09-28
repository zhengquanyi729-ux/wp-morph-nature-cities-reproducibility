"""Verify the distributed package against MANIFEST_SHA256.csv.

``MANIFEST_SHA256.csv`` records the package as distributed. It is written once,
before the archive is created (see ``build_manifest.py``), and is **never**
rewritten during normal reproduction. This module only verifies.

Checks performed:

  1. every file listed in the manifest is present;
  2. its size and SHA256 match the recorded values;
  3. no distributed file exists outside the manifest (an unlisted extra file
     would mean the archive under verification is not the distributed package).

Interpreter caches (``__pycache__``, ``.pytest_cache``) and the generated
``outputs_reproduced/`` tree are not distributed content and are ignored.
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
from utils.reporting import write_json  # noqa: E402

MANIFEST_NAME = "MANIFEST_SHA256.csv"
IGNORED_TOP_LEVEL = {"outputs_reproduced"}
IGNORED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".pyd"}


def read_manifest(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def verify(package_root: Path | None = None) -> dict:
    root = Path(package_root) if package_root else paths.PACKAGE_ROOT
    manifest_path = root / MANIFEST_NAME

    if not manifest_path.is_file():
        return {
            "step": "verify_manifest",
            "status": "FAIL",
            "manifest_present": False,
            "detail": f"missing distribution manifest: {manifest_path}",
        }

    rows = read_manifest(manifest_path)
    failures: list[str] = []
    verified = 0

    listed: set[str] = set()
    for row in rows:
        relative = row["relative_path"]
        listed.add(relative)
        target = root / relative
        if not target.is_file():
            failures.append(f"missing: {relative}")
            continue
        actual_size = target.stat().st_size
        if str(actual_size) != str(row["size_bytes"]):
            failures.append(f"size mismatch: {relative}")
            continue
        if sha256_file(target) != row["sha256"]:
            failures.append(f"sha256 mismatch: {relative}")
            continue
        verified += 1

    # Detect unlisted distributed files.
    unlisted: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        first_part = relative.split("/")[0]
        if first_part in IGNORED_TOP_LEVEL:
            continue
        if IGNORED_DIR_NAMES.intersection(path.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        if relative == MANIFEST_NAME:
            continue
        if relative not in listed:
            unlisted.append(relative)

    if unlisted:
        failures.append(f"unlisted distributed files: {sorted(unlisted)}")

    return {
        "step": "verify_manifest",
        "status": "PASS" if not failures else "FAIL",
        "manifest_present": True,
        "manifest_file": MANIFEST_NAME,
        "manifest_sha256": sha256_file(manifest_path),
        "listed_files": len(rows),
        "verified_files": verified,
        "unlisted_files": sorted(unlisted),
        "failures": failures,
    }


def main() -> int:
    result = verify()
    if paths.OUTPUTS_REPRODUCED_DIR.exists():
        write_json(paths.REPRODUCED_QC_DIR / "manifest_verification.json", result)

    print("=== DISTRIBUTION MANIFEST VERIFICATION ===")
    print(f"manifest file          : {MANIFEST_NAME}")
    print(f"manifest sha256        : {result.get('manifest_sha256', 'n/a')}")
    print(f"listed files           : {result.get('listed_files', 0)}")
    print(f"verified files         : {result.get('verified_files', 0)}")
    for failure in result.get("failures", []):
        print(f"FAIL  {failure}")
    print(f"DISTRIBUTION_MANIFEST: {result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
