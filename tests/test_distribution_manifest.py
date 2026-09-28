"""MANIFEST_SHA256.csv must describe the distributed package exactly."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from utils import paths

sys.path.insert(0, str(paths.PACKAGE_ROOT / "scripts"))

from utils.verify_manifest import (  # noqa: E402
    IGNORED_DIR_NAMES,
    IGNORED_SUFFIXES,
    MANIFEST_NAME,
    read_manifest,
    verify,
)


def test_manifest_verification_passes():
    result = verify()
    assert result["status"] == "PASS", result.get("failures")
    assert result["listed_files"] > 0
    assert result["verified_files"] == result["listed_files"]
    assert result["unlisted_files"] == []


def test_manifest_lists_every_distributed_file():
    rows = read_manifest(paths.PACKAGE_ROOT / MANIFEST_NAME)
    listed = {row["relative_path"] for row in rows}
    actual = set()
    for path in sorted(paths.PACKAGE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(paths.PACKAGE_ROOT).as_posix()
        if relative.split("/")[0] == "outputs_reproduced":
            continue
        if IGNORED_DIR_NAMES.intersection(path.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        if relative == MANIFEST_NAME:
            continue
        actual.add(relative)
    assert actual == listed


def test_manifest_does_not_claim_generated_outputs():
    rows = read_manifest(paths.PACKAGE_ROOT / MANIFEST_NAME)
    assert not [
        row for row in rows if row["relative_path"].startswith("outputs_reproduced/")
    ]


def test_manifest_has_the_required_columns():
    with (paths.PACKAGE_ROOT / MANIFEST_NAME).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "relative_path",
            "size_bytes",
            "sha256",
            "role",
            "frozen_or_generated",
            "required_for_reproduction",
        ]


def test_manifest_is_not_regenerated_by_a_normal_run():
    """The manifest hash recorded during run_all must still match the file."""
    import json

    report_path = paths.REPRODUCED_QC_DIR / "reproduction_report.json"
    if not report_path.is_file():
        return  # run_all has not been executed yet in this checkout
    report = json.loads(report_path.read_text(encoding="utf-8"))
    from utils.hashing import sha256_file

    assert report["distribution_manifest_immutable_during_run"] is True
    assert report["manifest_sha256"] == sha256_file(paths.PACKAGE_ROOT / MANIFEST_NAME)
