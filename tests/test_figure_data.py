"""Figure data: every plotted value must equal the frozen analytical output."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from utils import paths

STEMS = {
    "Fig_main_1_direction_magnitude": "Figure 2",
    "Fig_main_2_robustness_structure": "Figure 3",
    "Fig_S1_city_level_sensitivity": "Supplementary Figure S1",
    "Fig_S2_cross_city_dispersion": "Supplementary Figure S2",
}

SOURCE_DATA = {
    "fig2": "Source Data Fig. 2.csv",
    "fig3": "Source Data Fig. 3.csv",
    "s1": "Source Data Supplementary Fig. S1.csv",
    "s2": "Source Data Supplementary Fig. S2.csv",
}


def _frozen(name: str) -> pd.DataFrame:
    return pd.read_csv(paths.SYNTHESIS_DIR / name, encoding="utf-8-sig")


def _source(key: str) -> pd.DataFrame:
    return pd.read_csv(paths.REPRODUCED_TABLES_DIR / SOURCE_DATA[key], encoding="utf-8-sig")


@pytest.mark.parametrize("stem", STEMS)
@pytest.mark.parametrize("extension", ["png", "pdf", "svg"])
def test_figure_files_exist(stem, extension):
    target = paths.REPRODUCED_FIGURES_DIR / f"{stem}.{extension}"
    assert target.is_file(), f"missing regenerated figure: {target}"
    assert target.stat().st_size > 0


def test_figure_2_values_match_frozen_outputs():
    sign = _frozen("01_directional_concordance.csv")
    magnitude = _frozen("02_exploration_validation_magnitude_summary.csv")
    source = _source("fig2")

    panel_a = source[source["figure_panel"] == "a"]
    assert len(panel_a) == len(sign)
    for relationship in sign["relationship"]:
        expected = sign[sign["relationship"] == relationship].iloc[0]
        produced = panel_a[panel_a["relationship"] == relationship].iloc[0]
        for column in (
            "validation_unit_count",
            "same_sign_count",
            "sign_reversal_count",
            "insufficient_count",
            "undefined_count",
        ):
            assert int(produced[column]) == int(expected[column]), column

    panels = source[source["figure_panel"] == "b-d"]
    assert len(panels) == len(magnitude)
    key = ["relationship", "scale", "selection", "metric"]
    merged = panels.merge(
        magnitude[key + ["exploration_median", "validation_median", "exploration_min",
                         "exploration_max", "validation_min", "validation_max"]],
        on=key,
        how="left",
        suffixes=("", "_frozen"),
    )
    assert len(merged) == len(magnitude)
    for column in (
        "exploration_median",
        "validation_median",
        "exploration_min",
        "exploration_max",
        "validation_min",
        "validation_max",
    ):
        assert np.allclose(
            merged[column].to_numpy(dtype=float),
            merged[f"{column}_frozen"].to_numpy(dtype=float),
            rtol=0.0,
            atol=1e-12,
        ), column


def test_figure_3_values_match_frozen_outputs():
    profile = _frozen("04_relationship_robustness_profile.csv")
    source = _source("fig3")
    assert list(source.columns) == list(profile.columns)
    assert len(source) == len(profile)
    for column in ("median_abs_scale_delta", "median_abs_coverage_delta", "median_abs_metric_delta"):
        assert np.allclose(
            source[column].to_numpy(dtype=float),
            profile[column].to_numpy(dtype=float),
            rtol=0.0,
            atol=1e-12,
        ), column


def test_supplementary_figure_s1_values_match_frozen_outputs():
    sensitivity = _frozen("03_scale_coverage_metric_sensitivity.csv")
    source = _source("s1")
    assert list(source.columns) == list(sensitivity.columns)
    assert len(source) == len(sensitivity)
    assert np.allclose(
        source["signed_delta"].to_numpy(dtype=float),
        sensitivity["signed_delta"].to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-12,
    )


def test_supplementary_figure_s2_values_match_frozen_outputs():
    magnitude = _frozen("02_exploration_validation_magnitude_summary.csv")
    source = _source("s2")
    assert len(source) == len(magnitude)
    key = ["relationship", "scale", "selection", "metric"]
    merged = source.merge(magnitude, on=key, how="left", suffixes=("", "_frozen"))
    for column in ("exploration_range", "validation_range"):
        assert np.allclose(
            merged[column].to_numpy(dtype=float),
            merged[f"{column}_frozen"].to_numpy(dtype=float),
            rtol=0.0,
            atol=1e-12,
        ), column


def test_figure_data_audit_declares_no_new_metric():
    import json

    audit_path = paths.REPRODUCED_QC_DIR / "figure_data_audit.json"
    assert audit_path.is_file()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["any_new_metric_computed_all_false"] is True
    assert len(audit["entries"]) >= 4
