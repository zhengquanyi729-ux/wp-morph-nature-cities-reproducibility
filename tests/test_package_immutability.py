"""A normal reproduction run must modify only outputs_reproduced/.

``run_all.py`` hashes every distributed file before it starts and again after
its analysis steps, and publishes that evidence as
``outputs_reproduced/qc/immutability_precheck.json`` before the test suite
runs. These tests read that current-run evidence rather than inferring it.
"""

from __future__ import annotations

import csv
import json

from utils import paths
from utils.hashing import sha256_file

STATIC_MAP = "manuscript_mapping/manuscript_result_map.csv"
MANIFEST = "MANIFEST_SHA256.csv"


def _manifest_hashes() -> dict[str, str]:
    with (paths.PACKAGE_ROOT / MANIFEST).open("r", encoding="utf-8", newline="") as handle:
        return {row["relative_path"]: row["sha256"] for row in csv.DictReader(handle)}


def _precheck() -> dict:
    path = paths.REPRODUCED_QC_DIR / "immutability_precheck.json"
    assert path.is_file(), "run `python run_all.py` first"
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_all_modified_no_distributed_file():
    precheck = _precheck()
    assert precheck["modified_distributed_files"] == []
    assert precheck["run_all_modifies_only_outputs_reproduced"] is True
    assert precheck["distribution_manifest_immutable_during_run"] is True


def test_distribution_manifest_hash_is_unchanged_by_the_run():
    precheck = _precheck()
    assert precheck["manifest_sha256_before"] == precheck["manifest_sha256_after_analysis"]
    assert precheck["manifest_sha256_after_analysis"] == sha256_file(paths.PACKAGE_ROOT / MANIFEST)


def test_distributed_traceability_map_is_static_and_unchanged():
    manifest = _manifest_hashes()
    assert STATIC_MAP in manifest, "the distributed traceability map must be in the manifest"
    assert sha256_file(paths.PACKAGE_ROOT / STATIC_MAP) == manifest[STATIC_MAP]


def test_reproduced_map_matches_the_distributed_map():
    reproduced = paths.REPRODUCED_QC_DIR / "manuscript_result_map_reproduced.csv"
    assert reproduced.is_file(), "run `python run_all.py` first"
    assert sha256_file(reproduced) == sha256_file(paths.PACKAGE_ROOT / STATIC_MAP)


def test_manuscript_checks_write_inside_outputs_reproduced_only():
    report_path = paths.REPRODUCED_QC_DIR / "manuscript_number_check.json"
    assert report_path.is_file(), "run `python run_all.py` first"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["reproduced_map_file"].startswith("outputs_reproduced/")
    assert report["distributed_map_file"] == STATIC_MAP
    assert report["static_map_match"] is True


def test_manifest_contains_no_interpreter_cache_entries():
    """Interpreter caches are never distributed content."""
    manifest = _manifest_hashes()
    offenders = [
        path
        for path in manifest
        if "__pycache__" in path
        or ".pytest_cache" in path
        or path.endswith((".pyc", ".pyo", ".pyd"))
    ]
    assert not offenders, offenders


def test_run_created_no_interpreter_cache_outside_outputs_reproduced():
    """run_all disables bytecode writing and the pytest cache for its children."""
    precheck = _precheck()
    assert precheck["new_interpreter_caches"] == []


def test_every_entry_point_disables_bytecode_writing():
    """Directly invoking any journal-facing entry point must not create caches.

    Library modules under scripts/utils/ are imported by these entry points and
    are therefore covered by the entry point's flag, which is set before the
    import happens.
    """
    offenders = []
    candidates = [paths.PACKAGE_ROOT / "run_all.py"]
    candidates += sorted((paths.PACKAGE_ROOT / "scripts").rglob("*.py"))
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if '__name__ == "__main__"' not in text:
            continue
        if "sys.dont_write_bytecode = True" not in text:
            offenders.append(path.relative_to(paths.PACKAGE_ROOT).as_posix())
    assert not offenders, offenders
