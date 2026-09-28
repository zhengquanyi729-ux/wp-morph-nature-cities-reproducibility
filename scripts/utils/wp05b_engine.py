"""WP-MORPH-05B validation-coefficient recomputation.

This module is a path-independent reimplementation of the frozen WP-MORPH-05B
computation (``original_frozen_scripts/run_wp_morph05b.py``, SHA256
78E955CCAAA819826C44CEE9E5971B32374DCC9C93559D927F13A1ED9B017A54).

Every mathematical rule is preserved exactly:

  * Spearman rho is the Pearson correlation of average ranks.
  * Weighted Pearson r is the weighted covariance divided by the weighted
    standard deviations of x and y using the frozen relationship weight.
  * The pairwise-valid subset requires finite x and y; the weighted subset
    additionally requires a finite strictly positive weight.
  * Missing building height remains missing and is never replaced by zero.
  * Classification order: INSUFFICIENT_WINDOWS -> SIGN_REVERSAL -> SAME_SIGN
    -> UNDEFINED.
  * No p-value, no significance test, no threshold and no composite score is
    computed.

The module carries no absolute path. It reads whatever validation-window
files the caller points it at.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MIN_PAIRWISE_VALID_WINDOWS = 10
ZERO_TOL = 1e-15

EXPECTED_SCALES = ["1km", "5km"]
EXPECTED_SELECTIONS = ["ALL", "COVERAGE_80"]
TARGET_CITY_COUNT = 3

PAIR_DEFINITIONS: list[dict[str, str]] = [
    {
        "pair_id": "BUILDING_ROAD",
        "x_variable": "building_coverage_mean",
        "y_variable": "road_density_mean_km_per_km2",
        "weight_variable": "effective_area_m2",
        "expected_sign": "POSITIVE",
    },
    {
        "pair_id": "BUILDING_HEIGHT",
        "x_variable": "building_coverage_mean",
        "y_variable": "height_conditional_mean_m",
        "weight_variable": "height_valid_area_m2",
        "expected_sign": "POSITIVE",
    },
    {
        "pair_id": "ROAD_HEIGHT",
        "x_variable": "road_density_mean_km_per_km2",
        "y_variable": "height_conditional_mean_m",
        "weight_variable": "height_valid_area_m2",
        "expected_sign": "POSITIVE",
    },
]

REQUIRED_WINDOW_COLUMNS = {
    "city_id",
    "city_name",
    "scale",
    "window_row",
    "window_col",
    "effective_area_m2",
    "effective_area_fraction",
    "coverage_80",
    "building_coverage_mean",
    "road_density_mean_km_per_km2",
    "height_valid_area_m2",
    "height_conditional_mean_m",
}


class ValidationReproductionError(RuntimeError):
    """Raised when a frozen input or a reproduced result is not as expected."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationReproductionError(message)


# ---------------------------------------------------------------------------
# correlation primitives (verbatim mathematical port)
# ---------------------------------------------------------------------------


def ordinary_pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 2:
        return None

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return None

    x_center = x - np.mean(x)
    y_center = y - np.mean(y)

    denominator = float(np.sqrt(np.sum(x_center**2) * np.sum(y_center**2)))
    if not np.isfinite(denominator) or denominator <= ZERO_TOL:
        return None

    result = float(np.sum(x_center * y_center)) / denominator
    if not np.isfinite(result):
        return None

    return float(np.clip(result, -1.0, 1.0))


def spearman_rho(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 2:
        return None

    x_rank = pd.Series(x, dtype=float).rank(method="average").to_numpy(dtype=float)
    y_rank = pd.Series(y, dtype=float).rank(method="average").to_numpy(dtype=float)

    return ordinary_pearson(x_rank, y_rank)


def weighted_pearson_r(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float | None:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(w, dtype=float)

    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0)
    x = x[valid]
    y = y[valid]
    w = w[valid]

    if len(x) < 2:
        return None

    weight_sum = float(np.sum(w))
    if not np.isfinite(weight_sum) or weight_sum <= ZERO_TOL:
        return None

    x_mean = float(np.sum(w * x) / weight_sum)
    y_mean = float(np.sum(w * y) / weight_sum)

    x_center = x - x_mean
    y_center = y - y_mean

    covariance = float(np.sum(w * x_center * y_center) / weight_sum)
    x_variance = float(np.sum(w * x_center * x_center) / weight_sum)
    y_variance = float(np.sum(w * y_center * y_center) / weight_sum)

    if (
        x_variance <= ZERO_TOL
        or y_variance <= ZERO_TOL
        or not np.isfinite(x_variance)
        or not np.isfinite(y_variance)
    ):
        return None

    denominator = float(np.sqrt(x_variance * y_variance))
    if denominator <= ZERO_TOL or not np.isfinite(denominator):
        return None

    result = covariance / denominator
    if not np.isfinite(result):
        return None

    return float(np.clip(result, -1.0, 1.0))


def coefficient_direction(value: float | None) -> str | None:
    if value is None:
        return None
    if not np.isfinite(value):
        return None
    if value > ZERO_TOL:
        return "POSITIVE"
    if value < -ZERO_TOL:
        return "NEGATIVE"
    return None


def classify_unit(
    n_pairwise_valid_windows: int,
    spearman_value: float | None,
    weighted_value: float | None,
) -> dict[str, Any]:
    spearman_direction = coefficient_direction(spearman_value)
    weighted_direction = coefficient_direction(weighted_value)

    if n_pairwise_valid_windows < MIN_PAIRWISE_VALID_WINDOWS:
        classification = "INSUFFICIENT_WINDOWS"
    elif spearman_direction == "NEGATIVE" or weighted_direction == "NEGATIVE":
        classification = "SIGN_REVERSAL"
    elif spearman_direction == "POSITIVE" and weighted_direction == "POSITIVE":
        classification = "SAME_SIGN"
    else:
        classification = "UNDEFINED"

    if spearman_direction in {"POSITIVE", "NEGATIVE"} and weighted_direction in {
        "POSITIVE",
        "NEGATIVE",
    }:
        coefficient_direction_agreement: bool | None = spearman_direction == weighted_direction
    else:
        coefficient_direction_agreement = None

    return {
        "spearman_direction": spearman_direction,
        "weighted_pearson_direction": weighted_direction,
        "coefficient_direction_agreement": coefficient_direction_agreement,
        "classification": classification,
        "any_sign_reversal": classification == "SIGN_REVERSAL",
    }


# ---------------------------------------------------------------------------
# window loading
# ---------------------------------------------------------------------------


def load_validation_windows(windows_dir: Path) -> dict[str, pd.DataFrame]:
    windows_dir = Path(windows_dir)
    tables: dict[str, pd.DataFrame] = {}
    for scale in EXPECTED_SCALES:
        path = windows_dir / f"validation_windows_{scale}.csv"
        require(path.is_file(), f"Missing validation-window file: {path}")
        table = pd.read_csv(path, encoding="utf-8-sig")
        missing = REQUIRED_WINDOW_COLUMNS - set(table.columns)
        require(not missing, f"{path.name} lacks required columns: {sorted(missing)}")
        table["coverage_80"] = table["coverage_80"].astype(bool)
        tables[scale] = table
    return tables


def city_names(tables: dict[str, pd.DataFrame]) -> dict[str, str]:
    names: dict[str, str] = {}
    for table in tables.values():
        for city_id, city_name in zip(table["city_id"], table["city_name"]):
            names.setdefault(str(city_id), str(city_name))
    return names


# ---------------------------------------------------------------------------
# computation
# ---------------------------------------------------------------------------


def compute_validation_units(
    tables: dict[str, pd.DataFrame],
    authorized_city_ids: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    names = city_names(tables)
    correlation_rows: list[dict[str, Any]] = []
    direction_rows: list[dict[str, Any]] = []

    for city_id in authorized_city_ids:
        city_name = names[city_id]

        for scale_name in EXPECTED_SCALES:
            city_table = tables[scale_name].loc[tables[scale_name]["city_id"].eq(city_id)].copy()
            require(not city_table.empty, f"{city_id} {scale_name}: no frozen windows")

            for selection in EXPECTED_SELECTIONS:
                if selection == "ALL":
                    selected = city_table.copy()
                elif selection == "COVERAGE_80":
                    selected = city_table.loc[city_table["coverage_80"]].copy()
                else:
                    raise ValidationReproductionError(f"Unexpected selection: {selection}")

                n_total_windows = int(len(selected))

                for pair in PAIR_DEFINITIONS:
                    x_col = pair["x_variable"]
                    y_col = pair["y_variable"]
                    weight_col = pair["weight_variable"]

                    x = pd.to_numeric(selected[x_col], errors="coerce")
                    y = pd.to_numeric(selected[y_col], errors="coerce")
                    effective_area = pd.to_numeric(selected["effective_area_m2"], errors="coerce")
                    weights = pd.to_numeric(selected[weight_col], errors="coerce")

                    pairwise_valid = np.isfinite(x.to_numpy(dtype=float)) & np.isfinite(
                        y.to_numpy(dtype=float)
                    )
                    n_pairwise = int(pairwise_valid.sum())

                    valid_effective_area_m2 = float(
                        effective_area.to_numpy(dtype=float)[pairwise_valid].sum()
                    )

                    weighted_valid = (
                        pairwise_valid
                        & np.isfinite(weights.to_numpy(dtype=float))
                        & (weights.to_numpy(dtype=float) > 0)
                    )
                    n_weighted_valid = int(weighted_valid.sum())
                    weight_sum_m2 = float(weights.to_numpy(dtype=float)[weighted_valid].sum())

                    if n_pairwise >= MIN_PAIRWISE_VALID_WINDOWS:
                        rho = spearman_rho(
                            x.to_numpy(dtype=float)[pairwise_valid],
                            y.to_numpy(dtype=float)[pairwise_valid],
                        )
                        weighted_r = weighted_pearson_r(
                            x.to_numpy(dtype=float)[pairwise_valid],
                            y.to_numpy(dtype=float)[pairwise_valid],
                            weights.to_numpy(dtype=float)[pairwise_valid],
                        )
                    else:
                        rho = None
                        weighted_r = None

                    direction = classify_unit(n_pairwise, rho, weighted_r)

                    correlation_rows.append(
                        {
                            "city_id": city_id,
                            "city_name": city_name,
                            "scale": scale_name,
                            "selection": selection,
                            "pair_id": pair["pair_id"],
                            "x_variable": x_col,
                            "y_variable": y_col,
                            "expected_sign": pair["expected_sign"],
                            "weight_variable": weight_col,
                            "n_total_windows": n_total_windows,
                            "n_pairwise_valid_windows": n_pairwise,
                            "n_weighted_valid_windows": n_weighted_valid,
                            "valid_effective_area_m2": valid_effective_area_m2,
                            "weighted_pearson_weight_sum_m2": weight_sum_m2,
                            "spearman_rho": rho,
                            "weighted_pearson_r": weighted_r,
                            "p_value_computed": False,
                        }
                    )

                    direction_rows.append(
                        {
                            "city_id": city_id,
                            "city_name": city_name,
                            "scale": scale_name,
                            "selection": selection,
                            "pair_id": pair["pair_id"],
                            "expected_sign": pair["expected_sign"],
                            "n_total_windows": n_total_windows,
                            "n_pairwise_valid_windows": n_pairwise,
                            "spearman_rho": rho,
                            "weighted_pearson_r": weighted_r,
                            "spearman_direction": direction["spearman_direction"],
                            "weighted_pearson_direction": direction["weighted_pearson_direction"],
                            "coefficient_direction_agreement": direction[
                                "coefficient_direction_agreement"
                            ],
                            "classification": direction["classification"],
                            "any_sign_reversal": direction["any_sign_reversal"],
                        }
                    )

    correlations = pd.DataFrame(correlation_rows)
    directions = pd.DataFrame(direction_rows)
    return correlations, directions


def summarize_by_city(directions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for (city_id, city_name, pair_id), group in directions.groupby(
        ["city_id", "city_name", "pair_id"], sort=True, dropna=False
    ):
        require(len(group) == 4, f"{city_id} {pair_id}: expected four scale-selection units")

        counts = group["classification"].value_counts().to_dict()
        all_rows = group.loc[group["selection"].eq("ALL")]
        coverage_rows = group.loc[group["selection"].eq("COVERAGE_80")]

        rows.append(
            {
                "city_id": city_id,
                "city_name": city_name,
                "pair_id": pair_id,
                "expected_sign": "POSITIVE",
                "units_total": 4,
                "same_sign_units": int(counts.get("SAME_SIGN", 0)),
                "sign_reversal_units": int(counts.get("SIGN_REVERSAL", 0)),
                "insufficient_windows_units": int(counts.get("INSUFFICIENT_WINDOWS", 0)),
                "undefined_units": int(counts.get("UNDEFINED", 0)),
                "all_four_units_same_sign": bool((group["classification"] == "SAME_SIGN").all()),
                "no_sign_reversal": bool(not (group["classification"] == "SIGN_REVERSAL").any()),
                "all_selection_positive_at_both_scales": bool(
                    (all_rows["classification"] == "SAME_SIGN").all()
                ),
                "coverage80_positive_at_both_scales": bool(
                    (coverage_rows["classification"] == "SAME_SIGN").all()
                ),
                "spearman_weighted_direction_agreement_all_defined": bool(
                    group.loc[
                        group["coefficient_direction_agreement"].notna(),
                        "coefficient_direction_agreement",
                    ]
                    .astype(bool)
                    .all()
                )
                if group["coefficient_direction_agreement"].notna().any()
                else False,
            }
        )

    summary = pd.DataFrame(rows)
    require(
        len(summary) == TARGET_CITY_COUNT * len(PAIR_DEFINITIONS),
        "Unexpected validation_summary_by_city row count",
    )
    return summary


def summarize_hypotheses(directions: pd.DataFrame, city_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for pair in PAIR_DEFINITIONS:
        pair_id = pair["pair_id"]
        group = directions.loc[directions["pair_id"].eq(pair_id)].copy()
        per_city = city_summary.loc[city_summary["pair_id"].eq(pair_id)].copy()

        require(len(group) == 12, f"{pair_id}: expected 12 validation units")
        require(len(per_city) == TARGET_CITY_COUNT, f"{pair_id}: expected three city summaries")

        counts = group["classification"].value_counts().to_dict()
        all_selection_group = group.loc[group["selection"].eq("ALL")]
        coverage_group = group.loc[group["selection"].eq("COVERAGE_80")]

        rows.append(
            {
                "pair_id": pair_id,
                "x_variable": pair["x_variable"],
                "y_variable": pair["y_variable"],
                "expected_sign": pair["expected_sign"],
                "weight_variable": pair["weight_variable"],
                "validation_units_total": 12,
                "same_sign_units": int(counts.get("SAME_SIGN", 0)),
                "sign_reversal_units": int(counts.get("SIGN_REVERSAL", 0)),
                "insufficient_windows_units": int(counts.get("INSUFFICIENT_WINDOWS", 0)),
                "undefined_units": int(counts.get("UNDEFINED", 0)),
                "cities_all_four_units_same_sign": int(
                    per_city["all_four_units_same_sign"].sum()
                ),
                "cities_no_sign_reversal": int(per_city["no_sign_reversal"].sum()),
                "all_cities_all_selection_both_scales_same_sign": bool(
                    (all_selection_group["classification"] == "SAME_SIGN").all()
                ),
                "all_cities_coverage80_both_scales_same_sign": bool(
                    (coverage_group["classification"] == "SAME_SIGN").all()
                ),
                "all_12_units_same_sign": bool((group["classification"] == "SAME_SIGN").all()),
                "any_sign_reversal": bool((group["classification"] == "SIGN_REVERSAL").any()),
                "all_defined_coefficients_direction_agree": bool(
                    group.loc[
                        group["coefficient_direction_agreement"].notna(),
                        "coefficient_direction_agreement",
                    ]
                    .astype(bool)
                    .all()
                )
                if group["coefficient_direction_agreement"].notna().any()
                else False,
            }
        )

    summary = pd.DataFrame(rows)
    require(
        len(summary) == len(PAIR_DEFINITIONS),
        "Unexpected validation_hypothesis_summary row count",
    )
    return summary


def reproduce(
    windows_dir: Path,
    authorized_city_ids: list[str],
) -> dict[str, pd.DataFrame]:
    """Recompute every WP-MORPH-05B product from the frozen validation windows."""
    tables = load_validation_windows(windows_dir)
    correlations, directions = compute_validation_units(tables, authorized_city_ids)

    require(len(correlations) == 36, "Unexpected validation correlation unit count")
    require(len(directions) == 36, "Unexpected direction-check unit count")

    keys = ["city_id", "scale", "selection", "pair_id"]
    require(not correlations.duplicated(keys).any(), "Duplicate validation units")
    require(not directions.duplicated(keys).any(), "Duplicate direction-check units")

    counts = directions["classification"].value_counts().to_dict()

    return {
        "validation_correlations.csv": correlations,
        "validation_direction_checks.csv": directions,
        "validation_summary_by_city.csv": summarize_by_city(directions),
        "validation_hypothesis_summary.csv": summarize_hypotheses(
            directions, summarize_by_city(directions)
        ),
        "_classification_counts": pd.DataFrame(
            [
                {"classification": key, "count": int(counts.get(key, 0))}
                for key in ("SAME_SIGN", "SIGN_REVERSAL", "INSUFFICIENT_WINDOWS", "UNDEFINED")
            ]
        ),
    }
