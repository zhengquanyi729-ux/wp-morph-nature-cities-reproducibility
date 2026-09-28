"""Validation results: 36 conditions, 36 SAME_SIGN, no reversal / insufficiency / undefined."""

from __future__ import annotations

import pandas as pd

from utils import paths
from utils.hashing import sha256_file

FROZEN = "data/frozen_inputs/validation/validation_direction_checks.csv"


def _direction_table() -> pd.DataFrame:
    reproduced = paths.REPRODUCED_TABLES_DIR / "validation_direction_checks.csv"
    source = reproduced if reproduced.is_file() else paths.PACKAGE_ROOT / FROZEN
    return pd.read_csv(source, encoding="utf-8-sig")


def test_validation_unit_count_is_36():
    table = _direction_table()
    assert len(table) == 36
    assert not table.duplicated(["city_id", "scale", "selection", "pair_id"]).any()


def test_validation_classification_counts():
    counts = _direction_table()["classification"].value_counts().to_dict()
    assert counts.get("SAME_SIGN", 0) == 36
    assert counts.get("SIGN_REVERSAL", 0) == 0
    assert counts.get("INSUFFICIENT_WINDOWS", 0) == 0
    assert counts.get("UNDEFINED", 0) == 0


def test_every_condition_is_positive_both_coefficients():
    table = _direction_table()
    assert set(table["expected_sign"]) == {"POSITIVE"}
    assert (table["spearman_direction"] == "POSITIVE").all()
    assert (table["weighted_pearson_direction"] == "POSITIVE").all()
    assert table["coefficient_direction_agreement"].astype(bool).all()
    assert not table["any_sign_reversal"].astype(bool).any()
    assert (table["n_pairwise_valid_windows"] >= 10).all()


def test_universe_is_frozen():
    table = _direction_table()
    assert set(table["city_id"]) == {"P001", "P003", "P005"}
    assert set(table["scale"]) == {"1km", "5km"}
    assert set(table["selection"]) == {"ALL", "COVERAGE_80"}
    assert set(table["pair_id"]) == {"BUILDING_ROAD", "BUILDING_HEIGHT", "ROAD_HEIGHT"}


def test_no_p_values_are_recorded():
    table = _direction_table()
    assert "p_value" not in " ".join(table.columns).lower()

    correlations = pd.read_csv(
        paths.VALIDATION_DIR / "validation_correlations.csv", encoding="utf-8-sig"
    )
    assert "p_value_computed" in correlations.columns
    assert not correlations["p_value_computed"].astype(str).str.lower().eq("true").any()


def test_level_b_reproduction_is_byte_identical_when_included():
    reproduced = paths.REPRODUCED_TABLES_DIR / "validation_direction_checks.csv"
    if not reproduced.is_file():
        return  # Level B not included: documented in outputs_reproduced/qc
    frozen = paths.PACKAGE_ROOT / FROZEN
    assert sha256_file(reproduced) == sha256_file(frozen)
