"""City-name metadata must match the frozen canonical roster."""

from __future__ import annotations

import json

from utils import paths

EXPECTED_CITY_NAMES = {
    "P001": "Beijing",
    "P003": "Guangzhou",
    "P004": "Shenzhen",
    "P005": "Wuhan",
    "P026": "Luoyang",
    "P037": "Xining",
}

# The v1.0 release mislabelled the two exploration cities. These two strings
# were the erroneous labels. They must never appear next to an exploration
# city identifier anywhere in the distributed package. (The first string is the
# label of P002, which lies outside the frozen analytical universe; the second
# is not used by any city in this study.)
STALE_LABELS = (
    "Shang" + "hai",
    "Har" + "bin",
)
EXPLORATION_IDS = ("P004", "P026", "P037")

# `original_frozen_scripts/` is historical provenance and is never scanned.
SCANNED_SUFFIXES = {".json", ".md", ".csv", ".py", ".txt", ".toml", ".cff", ".yml", ".bat", ".ps1"}
SKIPPED_TOP_LEVEL = {"original_frozen_scripts", "outputs_reproduced"}


def test_config_city_names_match_frozen_roster(frozen_config):
    assert frozen_config["city_names"] == EXPECTED_CITY_NAMES


def test_city_ids_are_unchanged(frozen_config):
    assert set(frozen_config["exploration_cities"]) == {"P004", "P026", "P037"}
    assert set(frozen_config["validation_cities"]) == {"P001", "P003", "P005"}
    assert set(frozen_config["city_names"]) == {
        "P001",
        "P003",
        "P004",
        "P005",
        "P026",
        "P037",
    }


def test_no_stale_city_name_mapping_anywhere_in_the_package():
    """P026 is Luoyang and P037 is Xining.

    No distributed file may associate an exploration city with a stale label.
    """
    offenders: list[str] = []
    for path in sorted(paths.PACKAGE_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        relative = path.relative_to(paths.PACKAGE_ROOT).as_posix()
        if relative.split("/")[0] in SKIPPED_TOP_LEVEL:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")

        for line_number, line in enumerate(text.splitlines(), start=1):
            has_exploration_id = any(city_id in line for city_id in EXPLORATION_IDS)
            if has_exploration_id and any(label in line for label in STALE_LABELS):
                offenders.append(f"{relative}:{line_number}: exploration city with stale label")

        # The JSON config is also checked structurally (multi-line formatting).
        if relative == "config/frozen_analysis_config.json":
            config = json.loads(text)
            assert config["city_names"] == EXPECTED_CITY_NAMES

    assert not offenders, offenders


def test_frozen_validation_table_city_names_are_untouched():
    """Validation city labels in the frozen data must be unchanged."""
    import pandas as pd

    table = pd.read_csv(
        paths.VALIDATION_DIR / "validation_correlations.csv", encoding="utf-8-sig"
    )
    mapping = dict(zip(table["city_id"], table["city_name"]))
    assert mapping == {"P001": "Beijing", "P003": "Guangzhou", "P005": "Wuhan"}
