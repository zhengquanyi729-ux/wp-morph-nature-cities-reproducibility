"""WP-MORPH-05C exploration-validation concordance synthesis.

Path-independent reimplementation of the frozen WP-MORPH-05C synthesis
(``original_frozen_scripts/run_wp_morph05c_synthesis_v1.py``, SHA256
EA6A883787587A715486B2181ACFB518942003207A38A6CE8E660ED72DB51EDB).

The synthesis is descriptive and reads frozen result-level inputs only:

  * ``pairwise_relations.csv``                    (WP-MORPH-03, exploration phase)
  * ``validation_correlations.csv``               (WP-MORPH-05B, validation phase)
  * ``validation_direction_checks.csv``           (WP-MORPH-05B, classification)

No coefficient is re-estimated, no raw 50 m data is read and no validation
window data is read at this level. No p-value, significance test, post-hoc
success threshold, composite robustness score or relationship ranking is
defined.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

METHOD_CONTRACT_ID = "WP-MORPH-05C-METHOD-V1"
METHOD_CONTRACT_SHA256 = "936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3"
IMPLEMENTATION_SPEC_ID = "WP-MORPH-05C-IMPLEMENTATION-V1"

EXPECTED_EXPLORATION_CITIES = ["P004", "P026", "P037"]
EXPECTED_VALIDATION_CITIES = ["P001", "P003", "P005"]
SCALES = ["1km", "5km"]
SELECTIONS = ["ALL", "COVERAGE_80"]
RELATIONSHIPS = ["BUILDING_ROAD", "BUILDING_HEIGHT", "ROAD_HEIGHT"]
METRICS = ["SPEARMAN_RHO", "WEIGHTED_PEARSON_R"]

PAIR_MAP = {
    ("building_coverage_mean", "road_density_mean_km_per_km2"): "BUILDING_ROAD",
    ("building_coverage_mean", "height_conditional_mean_m"): "BUILDING_HEIGHT",
    ("road_density_mean_km_per_km2", "height_conditional_mean_m"): "ROAD_HEIGHT",
}

EXPECTED_PHASE_UNITS = 36
MIN_VALID_WINDOWS = 10

Q1 = 0.25
Q3 = 0.75
QUANTILE_INTERPOLATION = "linear"

OUTPUT_01 = "01_directional_concordance.csv"
OUTPUT_02 = "02_exploration_validation_magnitude_summary.csv"
OUTPUT_03 = "03_scale_coverage_metric_sensitivity.csv"
OUTPUT_04 = "04_relationship_robustness_profile.csv"

EXPECTED_OUTPUT_ROWS = {
    OUTPUT_01: 3,
    OUTPUT_02: 24,
    OUTPUT_03: 216,
    OUTPUT_04: 6,
}


class SynthesisReproductionError(RuntimeError):
    """Raised when a frozen input or a reproduced result is not as expected."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SynthesisReproductionError(message)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def finite_series(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    return x[np.isfinite(x)].astype(float)


def qlinear(series: pd.Series, q: float) -> float:
    x = finite_series(series)
    require(len(x) > 0, "Cannot calculate quantile on an empty finite series")
    return float(x.quantile(q, interpolation=QUANTILE_INTERPOLATION))


def median_finite(series: pd.Series) -> float:
    x = finite_series(series)
    require(len(x) > 0, "Cannot calculate median on an empty finite series")
    return float(x.median())


def min_finite(series: pd.Series) -> float:
    x = finite_series(series)
    require(len(x) > 0, "Cannot calculate minimum on an empty finite series")
    return float(x.min())


def max_finite(series: pd.Series) -> float:
    x = finite_series(series)
    require(len(x) > 0, "Cannot calculate maximum on an empty finite series")
    return float(x.max())


def normalize_text(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for column in cols:
        df[column] = df[column].astype(str).str.strip()
    return df


# ---------------------------------------------------------------------------
# frozen result-level inputs
# ---------------------------------------------------------------------------


def load_exploration(wp03_csv: Path) -> pd.DataFrame:
    required = {
        "city_id",
        "scale",
        "selection",
        "variable_x",
        "variable_y",
        "valid_pair_windows",
        "spearman_rho",
        "weighted_pearson_r",
        "status",
    }
    df = pd.read_csv(wp03_csv, encoding="utf-8-sig")
    require(required.issubset(df.columns), f"WP03 schema mismatch: {sorted(required - set(df.columns))}")

    df = normalize_text(
        df, ["city_id", "scale", "selection", "variable_x", "variable_y", "status"]
    )
    df["pair_id"] = [PAIR_MAP.get((x, y)) for x, y in zip(df["variable_x"], df["variable_y"])]

    require(df["pair_id"].notna().all(), "WP03 contains an unexpected relationship")
    require(len(df) == EXPECTED_PHASE_UNITS, "WP03 must contain exactly 36 frozen units")
    require(set(df["city_id"]) == set(EXPECTED_EXPLORATION_CITIES), "WP03 city universe changed")
    require(set(df["scale"]) == set(SCALES), "WP03 scale universe changed")
    require(set(df["selection"]) == set(SELECTIONS), "WP03 selection universe changed")
    require(set(df["pair_id"]) == set(RELATIONSHIPS), "WP03 relationship universe changed")
    require(
        (pd.to_numeric(df["valid_pair_windows"], errors="coerce") >= MIN_VALID_WINDOWS).all(),
        "WP03 contains a unit below the frozen minimum valid-window gate",
    )

    unit_keys = ["city_id", "scale", "selection", "pair_id"]
    require(not df.duplicated(unit_keys).any(), "WP03 contains duplicate frozen units")

    for column in ("spearman_rho", "weighted_pearson_r"):
        values = pd.to_numeric(df[column], errors="coerce")
        require(np.isfinite(values).all(), f"WP03 has an undefined inherited coefficient: {column}")

    out = df[
        ["city_id", "scale", "selection", "pair_id", "spearman_rho", "weighted_pearson_r"]
    ].copy()
    out.insert(0, "phase", "EXPLORATION")
    return out


def load_validation(validation_correlations_csv: Path) -> pd.DataFrame:
    required = {
        "city_id",
        "scale",
        "selection",
        "pair_id",
        "expected_sign",
        "n_pairwise_valid_windows",
        "spearman_rho",
        "weighted_pearson_r",
        "p_value_computed",
    }
    df = pd.read_csv(validation_correlations_csv, encoding="utf-8-sig")
    require(
        required.issubset(df.columns),
        f"WP05B correlation schema mismatch: {sorted(required - set(df.columns))}",
    )

    df = normalize_text(df, ["city_id", "scale", "selection", "pair_id", "expected_sign"])

    require(len(df) == EXPECTED_PHASE_UNITS, "WP05B must contain exactly 36 frozen units")
    require(set(df["city_id"]) == set(EXPECTED_VALIDATION_CITIES), "WP05B city universe changed")
    require(set(df["scale"]) == set(SCALES), "WP05B scale universe changed")
    require(set(df["selection"]) == set(SELECTIONS), "WP05B selection universe changed")
    require(set(df["pair_id"]) == set(RELATIONSHIPS), "WP05B relationship universe changed")
    require(set(df["expected_sign"]) == {"POSITIVE"}, "WP05B expected sign changed")
    require(
        (pd.to_numeric(df["n_pairwise_valid_windows"], errors="coerce") >= MIN_VALID_WINDOWS).all(),
        "WP05B contains a unit below the frozen minimum valid-window gate",
    )

    flags = df["p_value_computed"].astype(str).str.strip().str.lower()
    require(set(flags).issubset({"false", "0"}), "WP05B unexpectedly reports p-values computed")

    unit_keys = ["city_id", "scale", "selection", "pair_id"]
    require(not df.duplicated(unit_keys).any(), "WP05B contains duplicate frozen units")

    for column in ("spearman_rho", "weighted_pearson_r"):
        values = pd.to_numeric(df[column], errors="coerce")
        require(np.isfinite(values).all(), f"WP05B has an undefined inherited coefficient: {column}")

    out = df[
        ["city_id", "scale", "selection", "pair_id", "spearman_rho", "weighted_pearson_r"]
    ].copy()
    out.insert(0, "phase", "VALIDATION")
    return out


def load_direction_checks(direction_checks_csv: Path) -> pd.DataFrame:
    required = {"city_id", "scale", "selection", "pair_id", "expected_sign", "classification"}
    df = pd.read_csv(direction_checks_csv, encoding="utf-8-sig")
    require(required.issubset(df.columns), "WP05B direction-check schema mismatch")

    df = normalize_text(
        df, ["city_id", "scale", "selection", "pair_id", "expected_sign", "classification"]
    )
    require(len(df) == 36, "Direction-check table must contain 36 units")
    require(set(df["expected_sign"]) == {"POSITIVE"}, "Expected sign changed in direction checks")

    unit_keys = ["city_id", "scale", "selection", "pair_id"]
    require(not df.duplicated(unit_keys).any(), "Duplicate direction-check units")
    return df


# ---------------------------------------------------------------------------
# canonical long coefficient table
# ---------------------------------------------------------------------------


def canonical_long(exploration: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    base = pd.concat([exploration, validation], ignore_index=True)

    rows: list[dict[str, Any]] = []
    for row in base.itertuples(index=False):
        rows.append(
            {
                "phase": row.phase,
                "city_id": row.city_id,
                "relationship": row.pair_id,
                "scale": row.scale,
                "selection": row.selection,
                "metric": "SPEARMAN_RHO",
                "coefficient": float(row.spearman_rho),
            }
        )
        rows.append(
            {
                "phase": row.phase,
                "city_id": row.city_id,
                "relationship": row.pair_id,
                "scale": row.scale,
                "selection": row.selection,
                "metric": "WEIGHTED_PEARSON_R",
                "coefficient": float(row.weighted_pearson_r),
            }
        )

    long = pd.DataFrame(rows)
    require(len(long) == 144, "Canonical coefficient table must contain 144 rows")
    require(np.isfinite(long["coefficient"]).all(), "Canonical coefficient table has non-finite values")
    return long


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------


def make_directional_concordance(direction: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for relationship in RELATIONSHIPS:
        group = direction.loc[direction["pair_id"] == relationship]
        counts = group["classification"].value_counts().to_dict()

        same = int(counts.get("SAME_SIGN", 0))
        reversal = int(counts.get("SIGN_REVERSAL", 0))
        insufficient = int(counts.get("INSUFFICIENT_WINDOWS", 0))
        undefined = int(counts.get("UNDEFINED", 0))
        eligible = same + reversal + undefined

        rows.append(
            {
                "relationship": relationship,
                "expected_sign": "POSITIVE",
                "exploration_city_count": 3,
                "validation_city_count": 3,
                "validation_unit_count": int(len(group)),
                "same_sign_count": same,
                "sign_reversal_count": reversal,
                "insufficient_count": insufficient,
                "undefined_count": undefined,
                "directional_reproducibility_fraction": (
                    float(same / eligible) if eligible > 0 else np.nan
                ),
            }
        )

    out = pd.DataFrame(rows)
    require(len(out) == 3, "Directional-concordance output must contain 3 rows")
    return out


def summarize_phase_coefficients(group: pd.DataFrame, prefix: str) -> dict[str, Any]:
    series = finite_series(group["coefficient"])
    require(len(series) == 3, f"{prefix}: expected exactly 3 frozen city coefficients")

    minimum = float(series.min())
    maximum = float(series.max())

    return {
        f"{prefix}_n": int(len(series)),
        f"{prefix}_median": float(series.median()),
        f"{prefix}_q1": float(series.quantile(Q1, interpolation=QUANTILE_INTERPOLATION)),
        f"{prefix}_q3": float(series.quantile(Q3, interpolation=QUANTILE_INTERPOLATION)),
        f"{prefix}_min": minimum,
        f"{prefix}_max": maximum,
        f"{prefix}_range": maximum - minimum,
    }


def make_magnitude_summary(long: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for relationship in RELATIONSHIPS:
        for scale in SCALES:
            for selection in SELECTIONS:
                for metric in METRICS:
                    query = long.loc[
                        (long["relationship"] == relationship)
                        & (long["scale"] == scale)
                        & (long["selection"] == selection)
                        & (long["metric"] == metric)
                    ]

                    exploration_stats = summarize_phase_coefficients(
                        query.loc[query["phase"] == "EXPLORATION"], "exploration"
                    )
                    validation_stats = summarize_phase_coefficients(
                        query.loc[query["phase"] == "VALIDATION"], "validation"
                    )

                    shift = validation_stats["validation_median"] - exploration_stats["exploration_median"]

                    rows.append(
                        {
                            "relationship": relationship,
                            "scale": scale,
                            "selection": selection,
                            "metric": metric,
                            **exploration_stats,
                            **validation_stats,
                            "median_shift": shift,
                            "absolute_median_shift": abs(shift),
                        }
                    )

    out = pd.DataFrame(rows)
    require(len(out) == 24, "Magnitude-summary output must contain 24 rows")
    return out


def get_one(
    long: pd.DataFrame,
    phase: str,
    city: str,
    relationship: str,
    scale: str,
    selection: str,
    metric: str,
) -> float:
    query = long.loc[
        (long["phase"] == phase)
        & (long["city_id"] == city)
        & (long["relationship"] == relationship)
        & (long["scale"] == scale)
        & (long["selection"] == selection)
        & (long["metric"] == metric),
        "coefficient",
    ]
    require(len(query) == 1, "Expected exactly one frozen coefficient for sensitivity lookup")
    value = float(query.iloc[0])
    require(np.isfinite(value), "Sensitivity lookup encountered a non-finite coefficient")
    return value


def make_sensitivity(long: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    phase_cities = {
        "EXPLORATION": EXPECTED_EXPLORATION_CITIES,
        "VALIDATION": EXPECTED_VALIDATION_CITIES,
    }

    for phase, cities in phase_cities.items():
        for city in cities:
            for relationship in RELATIONSHIPS:
                # SCALE: b - a = 5km - 1km
                for selection in SELECTIONS:
                    for metric in METRICS:
                        a = get_one(long, phase, city, relationship, "1km", selection, metric)
                        b = get_one(long, phase, city, relationship, "5km", selection, metric)
                        delta = b - a
                        rows.append(
                            {
                                "phase": phase,
                                "city_id": city,
                                "relationship": relationship,
                                "dimension": "SCALE",
                                "conditioning_scale_or_selection": selection,
                                "metric": metric,
                                "comparison_a": "1km",
                                "comparison_b": "5km",
                                "coefficient_a": a,
                                "coefficient_b": b,
                                "signed_delta": delta,
                                "absolute_delta": abs(delta),
                            }
                        )

                # COVERAGE: b - a = COVERAGE_80 - ALL
                for scale in SCALES:
                    for metric in METRICS:
                        a = get_one(long, phase, city, relationship, scale, "ALL", metric)
                        b = get_one(long, phase, city, relationship, scale, "COVERAGE_80", metric)
                        delta = b - a
                        rows.append(
                            {
                                "phase": phase,
                                "city_id": city,
                                "relationship": relationship,
                                "dimension": "COVERAGE",
                                "conditioning_scale_or_selection": scale,
                                "metric": metric,
                                "comparison_a": "ALL",
                                "comparison_b": "COVERAGE_80",
                                "coefficient_a": a,
                                "coefficient_b": b,
                                "signed_delta": delta,
                                "absolute_delta": abs(delta),
                            }
                        )

                # METRIC / WEIGHTING: b - a = weighted Pearson r - Spearman rho
                for scale in SCALES:
                    for selection in SELECTIONS:
                        a = get_one(long, phase, city, relationship, scale, selection, "SPEARMAN_RHO")
                        b = get_one(
                            long, phase, city, relationship, scale, selection, "WEIGHTED_PEARSON_R"
                        )
                        delta = b - a
                        rows.append(
                            {
                                "phase": phase,
                                "city_id": city,
                                "relationship": relationship,
                                "dimension": "METRIC",
                                "conditioning_scale_or_selection": f"{scale}|{selection}",
                                "metric": "SPEARMAN_VS_WEIGHTED_PEARSON",
                                "comparison_a": "SPEARMAN_RHO",
                                "comparison_b": "WEIGHTED_PEARSON_R",
                                "coefficient_a": a,
                                "coefficient_b": b,
                                "signed_delta": delta,
                                "absolute_delta": abs(delta),
                            }
                        )

    out = pd.DataFrame(rows)
    require(len(out) == 216, "Sensitivity output must contain 216 rows")
    return out


def cross_city_ranges(long: pd.DataFrame, phase: str, relationship: str) -> list[float]:
    values: list[float] = []
    for scale in SCALES:
        for selection in SELECTIONS:
            for metric in METRICS:
                group = long.loc[
                    (long["phase"] == phase)
                    & (long["relationship"] == relationship)
                    & (long["scale"] == scale)
                    & (long["selection"] == selection)
                    & (long["metric"] == metric),
                    "coefficient",
                ]
                require(len(group) == 3, "Cross-city range expected exactly three frozen cities")
                values.append(float(group.max() - group.min()))
    require(len(values) == 8, "Expected eight cross-city ranges per phase/relationship")
    return values


def make_robustness_profile(
    long: pd.DataFrame,
    sensitivity: pd.DataFrame,
    direction: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for phase in ["EXPLORATION", "VALIDATION"]:
        for relationship in RELATIONSHIPS:
            ranges = cross_city_ranges(long, phase, relationship)

            scale_group = sensitivity.loc[
                (sensitivity["phase"] == phase)
                & (sensitivity["relationship"] == relationship)
                & (sensitivity["dimension"] == "SCALE")
            ]
            coverage_group = sensitivity.loc[
                (sensitivity["phase"] == phase)
                & (sensitivity["relationship"] == relationship)
                & (sensitivity["dimension"] == "COVERAGE")
            ]
            metric_group = sensitivity.loc[
                (sensitivity["phase"] == phase)
                & (sensitivity["relationship"] == relationship)
                & (sensitivity["dimension"] == "METRIC")
            ]

            require(len(scale_group) == 12, "Expected 12 scale deltas per phase/relationship")
            require(len(coverage_group) == 12, "Expected 12 coverage deltas per phase/relationship")
            require(len(metric_group) == 12, "Expected 12 metric deltas per phase/relationship")

            if phase == "VALIDATION":
                direction_group = direction.loc[direction["pair_id"] == relationship]
                counts = direction_group["classification"].value_counts().to_dict()
                same_count: Any = int(counts.get("SAME_SIGN", 0))
                eligible_count: Any = int(
                    counts.get("SAME_SIGN", 0)
                    + counts.get("SIGN_REVERSAL", 0)
                    + counts.get("UNDEFINED", 0)
                )
            else:
                # Frozen implementation decision: no retrospective WP03
                # SAME_SIGN classification is introduced for the exploration phase.
                same_count = np.nan
                eligible_count = np.nan

            rows.append(
                {
                    "phase": phase,
                    "relationship": relationship,
                    "directional_same_sign_count": same_count,
                    "directional_eligible_count": eligible_count,
                    "median_cross_city_range": float(np.median(ranges)),
                    "max_cross_city_range": float(np.max(ranges)),
                    "median_abs_scale_delta": median_finite(scale_group["absolute_delta"]),
                    "max_abs_scale_delta": max_finite(scale_group["absolute_delta"]),
                    "median_abs_coverage_delta": median_finite(coverage_group["absolute_delta"]),
                    "max_abs_coverage_delta": max_finite(coverage_group["absolute_delta"]),
                    "median_abs_metric_delta": median_finite(metric_group["absolute_delta"]),
                    "max_abs_metric_delta": max_finite(metric_group["absolute_delta"]),
                }
            )

    out = pd.DataFrame(rows)
    require(len(out) == 6, "Robustness-profile output must contain 6 rows")
    return out


def reproduce(wp03_csv: Path, validation_correlations_csv: Path, direction_checks_csv: Path) -> dict[str, pd.DataFrame]:
    """Recompute every WP-MORPH-05C synthesis product from frozen result-level inputs."""
    exploration = load_exploration(wp03_csv)
    validation = load_validation(validation_correlations_csv)
    direction = load_direction_checks(direction_checks_csv)

    long = canonical_long(exploration, validation)

    out01 = make_directional_concordance(direction)
    out02 = make_magnitude_summary(long)
    out03 = make_sensitivity(long)
    out04 = make_robustness_profile(long, out03, direction)

    outputs = {
        OUTPUT_01: out01,
        OUTPUT_02: out02,
        OUTPUT_03: out03,
        OUTPUT_04: out04,
    }

    for name, frame in outputs.items():
        require(
            len(frame) == EXPECTED_OUTPUT_ROWS[name],
            f"{name}: expected {EXPECTED_OUTPUT_ROWS[name]} rows, found {len(frame)}",
        )

    counts = direction["classification"].value_counts().to_dict()
    outputs["_qc"] = pd.DataFrame(
        [
            {"metric": "validation_unit_count", "value": int(len(direction))},
            {"metric": "same_sign_units", "value": int(counts.get("SAME_SIGN", 0))},
            {"metric": "sign_reversal_units", "value": int(counts.get("SIGN_REVERSAL", 0))},
            {"metric": "insufficient_windows_units", "value": int(counts.get("INSUFFICIENT_WINDOWS", 0))},
            {"metric": "undefined_units", "value": int(counts.get("UNDEFINED", 0))},
            {"metric": "canonical_coefficient_rows", "value": int(len(long))},
        ]
    )
    return outputs
