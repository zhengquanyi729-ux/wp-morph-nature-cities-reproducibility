"""Relative-path resolution for the WP-MORPH reproducibility package.

The package must run from any location and must not require access to the
original project directory. Every path is anchored to the package root, which
is discovered by walking up from this file until ``run_all.py`` is found.
"""

from __future__ import annotations

from pathlib import Path


def find_package_root(start: Path | None = None) -> Path:
    """Return the package root directory (the folder holding ``run_all.py``)."""
    origin = Path(start) if start is not None else Path(__file__)
    origin = origin.resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / "run_all.py").is_file():
            return candidate
    raise RuntimeError(
        "Could not locate the package root. Expected to find run_all.py in "
        f"{origin} or any parent directory."
    )


PACKAGE_ROOT: Path = find_package_root()

CONFIG_DIR: Path = PACKAGE_ROOT / "config"
DATA_DIR: Path = PACKAGE_ROOT / "data"
FROZEN_INPUTS_DIR: Path = DATA_DIR / "frozen_inputs"
EXPLORATION_DIR: Path = FROZEN_INPUTS_DIR / "exploration"
VALIDATION_DIR: Path = FROZEN_INPUTS_DIR / "validation"
SYNTHESIS_DIR: Path = FROZEN_INPUTS_DIR / "synthesis"
VALIDATION_WINDOWS_DIR: Path = DATA_DIR / "validation_windows"
EXTERNAL_SOURCES_DIR: Path = DATA_DIR / "external_sources"

SCRIPTS_DIR: Path = PACKAGE_ROOT / "scripts"
ORIGINAL_FROZEN_SCRIPTS_DIR: Path = PACKAGE_ROOT / "original_frozen_scripts"
MANUSCRIPT_MAPPING_DIR: Path = PACKAGE_ROOT / "manuscript_mapping"
TESTS_DIR: Path = PACKAGE_ROOT / "tests"

OUTPUTS_EXPECTED_DIR: Path = PACKAGE_ROOT / "outputs_expected"
OUTPUTS_REPRODUCED_DIR: Path = PACKAGE_ROOT / "outputs_reproduced"
REPRODUCED_TABLES_DIR: Path = OUTPUTS_REPRODUCED_DIR / "tables"
REPRODUCED_FIGURES_DIR: Path = OUTPUTS_REPRODUCED_DIR / "figures"
REPRODUCED_QC_DIR: Path = OUTPUTS_REPRODUCED_DIR / "qc"

EXPECTED_TABLES_DIR: Path = OUTPUTS_EXPECTED_DIR / "tables"
EXPECTED_FIGURES_DIR: Path = OUTPUTS_EXPECTED_DIR / "figures"
EXPECTED_QC_DIR: Path = OUTPUTS_EXPECTED_DIR / "qc"

MANIFEST_PATH: Path = PACKAGE_ROOT / "MANIFEST_SHA256.csv"
REPRODUCTION_REPORT_PATH: Path = REPRODUCED_QC_DIR / "reproduction_report.json"


def ensure_output_dirs() -> None:
    for directory in (
        OUTPUTS_REPRODUCED_DIR,
        REPRODUCED_TABLES_DIR,
        REPRODUCED_FIGURES_DIR,
        REPRODUCED_QC_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
