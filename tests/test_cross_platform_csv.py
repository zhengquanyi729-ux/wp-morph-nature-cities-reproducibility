"""Frozen CSV reproduction must be byte-identical on Windows and on Linux.

pandas' default CSV line terminator is ``os.linesep``, which silently produces
LF on Linux and would break byte-level identity with the frozen CRLF files.
The package therefore pins the terminator explicitly, and this module proves the
output no longer depends on the operating system.

The Linux condition is reproduced faithfully by setting ``os.linesep`` to the
Linux value ("\\n") before the writer is exercised: that is exactly the value
pandas would consult on Linux.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

from utils import paths
from utils.hashing import sha256_file
from utils.tables import CSV_ENCODING, CSV_FLOAT_FORMAT, CSV_LINE_TERMINATOR, write_csv
from utils.wp05b_engine import reproduce as reproduce_validation
from utils.wp05c_engine import reproduce as reproduce_synthesis

FROZEN_TABLES = {
    "validation_correlations.csv": "validation",
    "validation_direction_checks.csv": "validation",
    "validation_summary_by_city.csv": "validation",
    "validation_hypothesis_summary.csv": "validation",
    "01_directional_concordance.csv": "synthesis",
    "02_exploration_validation_magnitude_summary.csv": "synthesis",
    "03_scale_coverage_metric_sensitivity.csv": "synthesis",
    "04_relationship_robustness_profile.csv": "synthesis",
}


def test_writer_pins_the_line_terminator():
    assert CSV_LINE_TERMINATOR == "\r\n"
    assert CSV_ENCODING == "utf-8-sig"
    assert CSV_FLOAT_FORMAT == "%.12g"


def test_every_frozen_csv_write_pins_the_line_terminator():
    """No runnable file may call to_csv without an explicit lineterminator."""
    pattern = re.compile(r"\.to_csv\s*\(", re.MULTILINE)
    offenders: list[str] = []
    for path in sorted((paths.PACKAGE_ROOT / "scripts").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            tail = text[match.start() : match.start() + 600]
            if "lineterminator" not in tail:
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.name}:{line}")
    assert not offenders, offenders


def test_frozen_tables_are_crlf_on_disk():
    for name, kind in FROZEN_TABLES.items():
        directory = paths.VALIDATION_DIR if kind == "validation" else paths.SYNTHESIS_DIR
        payload = (directory / name).read_bytes()
        assert b"\r\n" in payload, f"{name} does not use CRLF"
        assert payload.replace(b"\r\n", b"").count(b"\n") == 0, f"{name} mixes LF and CRLF"


def _reproduce_all(destination) -> dict:
    products = {}
    products.update(
        reproduce_validation(paths.VALIDATION_WINDOWS_DIR, ["P001", "P003", "P005"])
    )
    products.update(
        reproduce_synthesis(
            paths.EXPLORATION_DIR / "pairwise_relations.csv",
            paths.VALIDATION_DIR / "validation_correlations.csv",
            paths.VALIDATION_DIR / "validation_direction_checks.csv",
        )
    )
    written = {}
    for name in FROZEN_TABLES:
        written[name] = write_csv(products[name], destination / name)
    return written


def _frozen_path(name: str):
    kind = FROZEN_TABLES[name]
    directory = paths.VALIDATION_DIR if kind == "validation" else paths.SYNTHESIS_DIR
    return directory / name


@pytest.mark.parametrize("linesep", ["\r\n", "\n"], ids=["windows-linesep", "linux-linesep"])
def test_all_eight_tables_reproduce_byte_identically(tmp_path, linesep):
    original = os.linesep
    os.linesep = linesep
    try:
        # pandas opens output files with newline="" and writes the configured
        # terminator literally, so this simulates the Linux runtime faithfully.
        written = _reproduce_all(tmp_path)
    finally:
        os.linesep = original

    for name, produced in written.items():
        frozen = _frozen_path(name)
        assert sha256_file(produced) == sha256_file(frozen), (
            f"{name} is not byte-identical to the frozen file "
            f"(os.linesep={linesep!r})"
        )


def test_output_does_not_depend_on_os_linesep(tmp_path):
    original = os.linesep
    try:
        os.linesep = "\r\n"
        windows = {name: sha256_file(p) for name, p in _reproduce_all(tmp_path / "win").items()}
        os.linesep = "\n"
        linux = {name: sha256_file(p) for name, p in _reproduce_all(tmp_path / "lnx").items()}
    finally:
        os.linesep = original
    assert windows == linux
