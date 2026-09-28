"""Shared helpers for the WP-MORPH journal reproducibility package.

Every path used by the package is derived from the package root. No module in
this package may contain a user-specific absolute path.
"""

from .paths import (  # noqa: F401
    PACKAGE_ROOT,
    CONFIG_DIR,
    DATA_DIR,
    FROZEN_INPUTS_DIR,
    EXPLORATION_DIR,
    VALIDATION_DIR,
    SYNTHESIS_DIR,
    VALIDATION_WINDOWS_DIR,
    OUTPUTS_EXPECTED_DIR,
    OUTPUTS_REPRODUCED_DIR,
    REPRODUCED_TABLES_DIR,
    REPRODUCED_FIGURES_DIR,
    REPRODUCED_QC_DIR,
    MANUSCRIPT_MAPPING_DIR,
    TESTS_DIR,
)

__all__ = [
    "PACKAGE_ROOT",
    "CONFIG_DIR",
    "DATA_DIR",
    "FROZEN_INPUTS_DIR",
    "EXPLORATION_DIR",
    "VALIDATION_DIR",
    "SYNTHESIS_DIR",
    "VALIDATION_WINDOWS_DIR",
    "OUTPUTS_EXPECTED_DIR",
    "OUTPUTS_REPRODUCED_DIR",
    "REPRODUCED_TABLES_DIR",
    "REPRODUCED_FIGURES_DIR",
    "REPRODUCED_QC_DIR",
    "MANUSCRIPT_MAPPING_DIR",
    "TESTS_DIR",
]
