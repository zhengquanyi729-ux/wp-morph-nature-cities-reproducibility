"""Synthesis results: frozen row counts, frozen summary values and manuscript anchors."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from utils import paths
from utils.hashing import sha256_file

SYNTHESIS_FILES = (
    "01_directional_concordance.csv",
    "02_exploration_validation_magnitude_summary.csv",
    "03_scale_coverage_metric_sensitivity.csv",
    "04_relationship_robustness_profile.csv",
)


def _reproduced(name: str) -> pd.DataFrame:
    return pd.read_csv(paths.REPRODUCED_TABLES_DIR / name, encoding="utf-8-sig")


@pytest.mark.parametrize("name", SYNTHESIS_FILES)
def test_row_counts(name, expected_outputs):
    frame = _reproduced(name)
    assert len(frame) == expected_outputs["wp05c_outputs"][name]["row_count"]


@pytest.mark.parametrize("name", SYNTHESIS_FILES)
def test_reproduced_tables_are_byte_identical_to_frozen(name):
    reproduced = paths.REPRODUCED_TABLES_DIR / name
    frozen = paths.SYNTHESIS_DIR / name
    assert reproduced.is_file(), f"run `python run_all.py` first: {reproduced}"
    assert sha256_file(reproduced) == sha256_file(frozen)


def test_directional_concordance_values(expected_outputs):
    frame = _reproduced("01_directional_concordance.csv")
    assert int(frame["same_sign_count"].sum()) == 36
    assert int(frame["sign_reversal_count"].sum()) == 0
    assert int(frame["insufficient_count"].sum()) == 0
    assert int(frame["undefined_count"].sum()) == 0
    assert (frame["validation_unit_count"] == 12).all()


def test_frozen_robustness_profile_medians(expected_outputs):
    frame = _reproduced("04_relationship_robustness_profile.csv")
    tolerance = expected_outputs["manuscript_anchor_tolerance"]
    expected = expected_outputs["robustness_profile_medians"]["04_relationship_robustness_profile.csv"]

    for relationship, phases in expected.items():
        for phase, columns in phases.items():
            row = frame[(frame["phase"] == phase) & (frame["relationship"] == relationship)]
            assert len(row) == 1, f"missing profile row for {phase}/{relationship}"
            for column, value in columns.items():
                assert math.isclose(
                    float(row.iloc[0][column]), float(value), rel_tol=0.0, abs_tol=tolerance
                ), f"{phase}/{relationship}/{column}"


def test_manuscript_anchor_values(expected_outputs):
    magnitude = _reproduced("02_exploration_validation_magnitude_summary.csv")

    def lookup(row_filter: str) -> pd.Series:
        parts = dict(item.strip().split("=") for item in row_filter.split(";"))
        query = magnitude
        for column, value in parts.items():
            query = query[query[column] == value]
        assert len(query) == 1, row_filter
        return query.iloc[0]

    for check in expected_outputs["manuscript_anchor_checks"]:
        if check["check_id"] == "A_direction_36_of_36":
            continue  # covered by the validation tests
        tolerance = (
            0.0
            if isinstance(check["expected_value"], int)
            else expected_outputs["manuscript_anchor_tolerance"]
        )
        row = lookup(check["filter"])
        column = check["source_columns"][0]
        assert math.isclose(
            float(row[column]), float(check["expected_value"]), rel_tol=0.0, abs_tol=tolerance
        ), check["check_id"]


def test_localized_checks(expected_outputs):
    localized = expected_outputs["localized_checks"]
    correlations = pd.read_csv(
        paths.VALIDATION_DIR / "validation_correlations.csv", encoding="utf-8-sig"
    )

    def p005(scale, selection):
        hit = correlations[
            (correlations["city_id"] == "P005")
            & (correlations["scale"] == scale)
            & (correlations["selection"] == selection)
            & (correlations["pair_id"] == "BUILDING_HEIGHT")
        ]
        assert len(hit) == 1
        return hit.iloc[0]

    all_5km = p005("5km", "ALL")
    c80_5km = p005("5km", "COVERAGE_80")

    assert math.isclose(
        float(all_5km["spearman_rho"]),
        localized["P005_BUILDING_HEIGHT_5km_spearman_ALL"],
        abs_tol=5e-4,
    )
    assert math.isclose(
        float(c80_5km["spearman_rho"]),
        localized["P005_BUILDING_HEIGHT_5km_spearman_COVERAGE_80"],
        abs_tol=5e-4,
    )
    assert math.isclose(
        abs(float(all_5km["spearman_rho"]) - float(c80_5km["spearman_rho"])),
        localized["P005_BUILDING_HEIGHT_5km_spearman_absolute_change"],
        abs_tol=5e-4,
    )

    p005_1km = correlations[
        (correlations["city_id"] == "P005")
        & (correlations["scale"] == "1km")
        & (correlations["selection"] == "ALL")
        & (correlations["pair_id"] == "BUILDING_HEIGHT")
    ].iloc[0]
    assert math.isclose(
        float(p005_1km["spearman_rho"]),
        localized["P005_BUILDING_HEIGHT_1km_ALL_spearman"],
        abs_tol=5e-4,
    )
    assert math.isclose(
        float(p005_1km["weighted_pearson_r"]),
        localized["P005_BUILDING_HEIGHT_1km_ALL_weighted_pearson"],
        abs_tol=5e-4,
    )
    assert math.isclose(
        abs(float(p005_1km["spearman_rho"]) - float(p005_1km["weighted_pearson_r"])),
        localized["P005_BUILDING_HEIGHT_1km_ALL_absolute_metric_difference"],
        abs_tol=5e-4,
    )


def test_no_forbidden_quantities_exist_in_synthesis_outputs():
    forbidden = ("p_value", "pvalue_significance", "robustness_score", "rank", "z_score")
    for name in SYNTHESIS_FILES:
        columns = " ".join(_reproduced(name).columns).lower()
        for token in forbidden:
            assert token not in columns, f"{name} exposes forbidden column token '{token}'"
