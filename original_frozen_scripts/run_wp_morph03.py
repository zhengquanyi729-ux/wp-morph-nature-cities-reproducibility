
"""
WP-MORPH-03
Three-city morphology relationships and cross-scale stability.

Inputs:
    WP-MORPH-02B window_metrics_1km.csv
    WP-MORPH-02B window_metrics_5km.csv
    WP-MORPH-02B qc_summary.json
    WP-MORPH-02B manifest.json

Analyses:
    1. Pairwise Spearman rank correlation
    2. Effective-area-weighted Pearson correlation
    3. Window effective-area sensitivity
    4. Conditional-height sample diagnostics
    5. Within-city cross-scale relationship comparison

Outputs:
    pairwise_relations.csv
    window_coverage_diagnostics.csv
    cross_scale_stability.csv
    qc_summary.json
    manifest.json

Status:
    NONPRODUCTION_EXPLORATORY

This script does NOT:
    - create or modify CANU units
    - classify land or residential deficits
    - use CUGUV / GeoLink labels
    - run RF, LightGBM, repartition or P003
    - modify frozen inputs or scientific gates
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# 0. CONFIGURATION
# ============================================================

ROOT = Path(r"C:\china_meld")

SOURCE_DIR = (
    ROOT
    / "experiments"
    / "wp_morph02b_nonproduction"
    / "run_20260925_091105_413694"
)

OUTPUT_BASE = (
    ROOT
    / "experiments"
    / "wp_morph03_nonproduction"
)

EXPECTED_CITIES = [
    "P004",
    "P026",
    "P037",
]

SCALE_CONFIG = {
    "1km": {
        "nominal_area_m2": 1_000_000.0,
        "expected_windows": {
            "P004": 1914,
            "P026": 1931,
            "P037": 666,
        },
    },
    "5km": {
        "nominal_area_m2": 25_000_000.0,
        "expected_windows": {
            "P004": 101,
            "P026": 127,
            "P037": 47,
        },
    },
}

# Fixed before analysis:
#
# ALL:
#   Every window with valid pairwise data.
#
# COVERAGE_80:
#   Only windows with >=80% of their nominal effective area.
#
# Window effective-area fraction is NOT physical land truth.
# A low value may reflect the frozen mask, study boundary,
# water masking or other features of the analysis domain.

WINDOW_SELECTIONS = {
    "ALL": 0.0,
    "COVERAGE_80": 0.80,
}

# Minimum number of valid windows required to report
# a descriptive pairwise relationship.
MIN_VALID_WINDOWS = 10

# Fixed variable set.
BUILDING = "building_coverage_mean"

ROAD = "road_density_mean_km_per_km2"

HEIGHT = "height_conditional_mean_m"

VARIABLE_PAIRS = [
    (BUILDING, ROAD),
    (BUILDING, HEIGHT),
    (ROAD, HEIGHT),
]

REQUIRED_COLUMNS = [
    "city_id",
    "scale",
    "window_row",
    "window_col",
    "cell_count",
    "effective_area_m2",
    "built_cell_area_m2",
    "height_valid_cell_area_m2",
    "building_coverage_mean",
    "road_density_mean_km_per_km2",
    "height_conditional_mean_m",
]

# Additive fields used to verify that 1 km and 5 km
# results describe the same frozen input domain.
ADDITIVE_CHECK_FIELDS = [
    "cell_count",
    "effective_area_m2",
    "built_cell_area_m2",
    "height_valid_cell_area_m2",
]

FRACTION_TOL = 1e-8

AREA_ABS_TOL = 1e-4

AREA_REL_TOL = 1e-10


# ============================================================
# 1. HELPERS
# ============================================================

def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(4 * 1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest().upper()


def read_json(path: Path) -> dict:

    require(
        path.is_file(),
        f"Missing required file: {path}",
    )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def finite_array(values) -> np.ndarray:

    return np.isfinite(
        np.asarray(values, dtype=np.float64)
    )


def weighted_pearson(
    x: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
) -> float:

    """
    Effective-area-weighted Pearson correlation.

    This is NOT weighted Spearman.
    """

    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)

    valid = (
        np.isfinite(x)
        & np.isfinite(y)
        & np.isfinite(w)
        & (w > 0)
    )

    x = x[valid]
    y = y[valid]
    w = w[valid]

    if len(x) < MIN_VALID_WINDOWS:
        return np.nan

    mx = np.average(x, weights=w)
    my = np.average(y, weights=w)

    dx = x - mx
    dy = y - my

    vx = np.average(dx * dx, weights=w)
    vy = np.average(dy * dy, weights=w)

    if vx <= 0 or vy <= 0:
        return np.nan

    covariance = np.average(
        dx * dy,
        weights=w,
    )

    result = covariance / np.sqrt(vx * vy)

    return float(np.clip(result, -1.0, 1.0))


def spearman_rho(
    x: np.ndarray,
    y: np.ndarray,
) -> float:

    """
    Ordinary, unweighted Spearman correlation.

    Average ranks are assigned to tied values.
    """

    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    valid = np.isfinite(x) & np.isfinite(y)

    x = x[valid]
    y = y[valid]

    if len(x) < MIN_VALID_WINDOWS:
        return np.nan

    if np.unique(x).size < 2:
        return np.nan

    if np.unique(y).size < 2:
        return np.nan

    rx = pd.Series(x).rank(
        method="average"
    ).to_numpy(dtype=np.float64)

    ry = pd.Series(y).rank(
        method="average"
    ).to_numpy(dtype=np.float64)

    return float(
        np.corrcoef(rx, ry)[0, 1]
    )


def relationship_sign(value) -> str:

    if not np.isfinite(value):
        return "UNDEFINED"

    if value > 0:
        return "POSITIVE"

    if value < 0:
        return "NEGATIVE"

    return "ZERO"


# ============================================================
# 2. INPUT PREFLIGHT
# ============================================================

def preflight() -> dict:

    print("\n=== WP-MORPH-03 INPUT PREFLIGHT ===")

    manifest_path = SOURCE_DIR / "manifest.json"
    qc_path = SOURCE_DIR / "qc_summary.json"

    manifest = read_json(manifest_path)
    source_qc = read_json(qc_path)

    require(
        manifest.get("work_package") == "WP-MORPH-02B",
        "Unexpected source work package",
    )

    require(
        manifest.get("status")
        == "NONPRODUCTION_DESCRIPTIVE",
        "Unexpected source status",
    )

    require(
        manifest.get("overall_qc") == "PASS",
        "Source manifest QC is not PASS",
    )

    require(
        source_qc.get("overall_qc") == "PASS",
        "Source QC summary is not PASS",
    )

    output_hashes = manifest.get(
        "output_hashes", {}
    )

    require(
        isinstance(output_hashes, dict)
        and bool(output_hashes),
        "Source output hashes missing",
    )

    # Verify every output registered by WP-MORPH-02B.
    for relative_path, expected_hash in output_hashes.items():

        path = SOURCE_DIR / relative_path

        require(
            path.is_file(),
            f"Missing WP02B output: {path}",
        )

        actual_hash = sha256_file(path)

        require(
            actual_hash == expected_hash.upper(),
            f"WP02B output hash mismatch: {relative_path}",
        )

    require(
        source_qc.get("status")
        == "NONPRODUCTION_DESCRIPTIVE",
        "Unexpected source QC status",
    )

    previous_window_qc = source_qc.get(
        "window_qc", []
    )

    for record in previous_window_qc:

        require(
            record.get("status") == "PASS",
            "A source window QC record is not PASS",
        )

    source_summaries = source_qc.get(
        "source_summaries", {}
    )

    for city_id in EXPECTED_CITIES:

        require(
            city_id in source_summaries,
            f"{city_id}: source summary missing",
        )

    print(
        "SOURCE_MANIFEST_SHA256:",
        sha256_file(manifest_path),
    )

    print("SOURCE_OUTPUT_HASHES: PASS")

    print("SOURCE_QC: PASS")

    return {
        "manifest_path": manifest_path,
        "manifest_hash": sha256_file(manifest_path),
        "source_qc": source_qc,
    }


# ============================================================
# 3. READ AND VALIDATE WINDOW DATA
# ============================================================

def load_windows() -> pd.DataFrame:

    print("\n=== LOADING WINDOW DATA ===")

    frames = []

    for scale in SCALE_CONFIG:

        path = SOURCE_DIR / f"window_metrics_{scale}.csv"

        require(
            path.is_file(),
            f"Missing window CSV: {path}",
        )

        frame = pd.read_csv(
            path,
            encoding="utf-8-sig",
        )

        missing = sorted(
            set(REQUIRED_COLUMNS) - set(frame.columns)
        )

        require(
            not missing,
            f"{scale}: missing columns {missing}",
        )

        require(
            frame["scale"].eq(scale).all(),
            f"{scale}: unexpected scale values",
        )

        require(
            set(frame["city_id"].unique())
            == set(EXPECTED_CITIES),
            f"{scale}: unexpected city identities",
        )

        # Validate numeric and index fields.
        numeric_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in ("city_id", "scale")
        ]

        for column in numeric_columns:

            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

        for column in [
            "window_row",
            "window_col",
            "cell_count",
        ]:

            values = frame[column]

            require(
                finite_array(values).all(),
                f"{scale}: invalid {column}",
            )

            require(
                (values == np.floor(values)).all(),
                f"{scale}: noninteger {column}",
            )

            frame[column] = values.astype(np.int64)

        require(
            not frame.duplicated(
                ["city_id", "window_row", "window_col"]
            ).any(),
            f"{scale}: duplicate window identifiers",
        )

        for city_id in EXPECTED_CITIES:

            part = frame.loc[
                frame["city_id"] == city_id
            ]

            expected_count = (
                SCALE_CONFIG[scale]
                ["expected_windows"][city_id]
            )

            require(
                len(part) == expected_count,
                (
                    f"{city_id} {scale}: window count "
                    f"{len(part)} != {expected_count}"
                ),
            )

        require(
            finite_array(
                frame["effective_area_m2"]
            ).all(),
            f"{scale}: invalid effective area",
        )

        require(
            (frame["effective_area_m2"] > 0).all(),
            f"{scale}: nonpositive effective area",
        )

        nominal_area = (
            SCALE_CONFIG[scale]["nominal_area_m2"]
        )

        frame["window_effective_area_fraction"] = (
            frame["effective_area_m2"]
            / nominal_area
        )

        fraction = frame[
            "window_effective_area_fraction"
        ]

        require(
            (
                (fraction > 0)
                & (fraction <= 1 + FRACTION_TOL)
            ).all(),
            f"{scale}: effective area exceeds nominal area",
        )

        # Check height denominator logic.
        height_area = frame[
            "height_valid_cell_area_m2"
        ]

        built_area = frame[
            "built_cell_area_m2"
        ]

        require(
            finite_array(height_area).all()
            and finite_array(built_area).all(),
            f"{scale}: invalid conditional-area fields",
        )

        require(
            (height_area >= -AREA_ABS_TOL).all()
            and (built_area >= -AREA_ABS_TOL).all(),
            f"{scale}: negative conditional area",
        )

        require(
            (
                height_area
                <= built_area + AREA_ABS_TOL
            ).all(),
            f"{scale}: height area exceeds built area",
        )

        no_height = height_area <= 0

        require(
            frame.loc[
                no_height,
                HEIGHT,
            ].isna().all(),
            f"{scale}: height value without valid area",
        )

        has_height = height_area > 0

        require(
            finite_array(
                frame.loc[has_height, HEIGHT]
            ).all(),
            f"{scale}: missing height with valid area",
        )

        # Basic variable ranges.
        coverage = frame[BUILDING]
        road = frame[ROAD]

        require(
            finite_array(coverage).all()
            and (
                (coverage >= -FRACTION_TOL)
                & (coverage <= 1 + FRACTION_TOL)
            ).all(),
            f"{scale}: invalid coverage values",
        )

        require(
            finite_array(road).all()
            and (road >= -FRACTION_TOL).all(),
            f"{scale}: invalid road density",
        )

        frames.append(frame)

        print(
            f"{scale}: WINDOWS={len(frame):,}; "
            "SCHEMA_QC=PASS"
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )


# ============================================================
# 4. VERIFY 1 KM / 5 KM AGGREGATION CONSISTENCY
# ============================================================

def cross_scale_qc(
    windows: pd.DataFrame,
    source_qc: dict,
) -> list[dict]:

    print("\n=== CROSS-SCALE QC ===")

    records = []

    for city_id in EXPECTED_CITIES:

        one = windows.loc[
            windows["city_id"].eq(city_id)
            & windows["scale"].eq("1km")
        ].copy()

        five = windows.loc[
            windows["city_id"].eq(city_id)
            & windows["scale"].eq("5km")
        ].copy()

        # The original windows use floor(grid_index / 20)
        # and floor(grid_index / 100).
        #
        # Therefore floor(1km_index / 5) must recover
        # the corresponding 5km index, including
        # for negative integer indices.

        one["parent_row"] = (
            one["window_row"] // 5
        )

        one["parent_col"] = (
            one["window_col"] // 5
        )

        grouped = one.groupby(
            ["parent_row", "parent_col"],
            sort=True,
        )[ADDITIVE_CHECK_FIELDS].sum()

        comparison = five.set_index(
            ["window_row", "window_col"]
        )[ADDITIVE_CHECK_FIELDS]

        require(
            set(grouped.index) == set(comparison.index),
            (
                f"{city_id}: 1km-to-5km "
                "window identity mismatch"
            ),
        )

        grouped = grouped.reindex(
            comparison.index
        )

        field_errors = {}

        for field in ADDITIVE_CHECK_FIELDS:

            actual = grouped[field].to_numpy(
                dtype=np.float64
            )

            expected = comparison[field].to_numpy(
                dtype=np.float64
            )

            if field == "cell_count":

                field_ok = np.array_equal(
                    actual,
                    expected,
                )

            else:

                field_ok = np.allclose(
                    actual,
                    expected,
                    rtol=AREA_REL_TOL,
                    atol=AREA_ABS_TOL,
                )

            maximum_error = float(
                np.max(np.abs(actual - expected))
            )

            field_errors[field] = maximum_error

            require(
                field_ok,
                (
                    f"{city_id}: cross-scale mismatch "
                    f"for {field}; max error={maximum_error}"
                ),
            )

        expected_source_area = float(
            source_qc["source_summaries"]
            [city_id]["effective_area_m2"]
        )

        actual_source_area = float(
            one["effective_area_m2"].sum()
        )

        require(
            np.isclose(
                actual_source_area,
                expected_source_area,
                rtol=AREA_REL_TOL,
                atol=AREA_ABS_TOL,
            ),
            f"{city_id}: source area does not close",
        )

        records.append({
            "city_id": city_id,
            "status": "PASS",
            "parent_5km_windows": len(grouped),
            "maximum_field_errors": field_errors,
        })

        print(
            f"{city_id}: "
            f"5KM_PARENTS={len(grouped)}; "
            "AGGREGATION_QC=PASS"
        )

    return records


# ============================================================
# 5. WINDOW COVERAGE DIAGNOSTICS
# ============================================================

def coverage_diagnostics(
    windows: pd.DataFrame,
) -> pd.DataFrame:

    records = []

    for (city_id, scale), part in windows.groupby(
        ["city_id", "scale"],
        sort=True,
    ):

        fraction = part[
            "window_effective_area_fraction"
        ]

        total_area = float(
            part["effective_area_m2"].sum()
        )

        for selection_name, threshold in (
            WINDOW_SELECTIONS.items()
        ):

            selected = fraction >= threshold

            count = int(selected.sum())

            selected_area = float(
                part.loc[
                    selected,
                    "effective_area_m2",
                ].sum()
            )

            height_available = (
                selected
                & (
                    part["height_valid_cell_area_m2"]
                    > 0
                )
                & part[HEIGHT].notna()
            )

            records.append({
                "city_id": city_id,
                "scale": scale,
                "selection": selection_name,
                "minimum_effective_area_fraction": (
                    threshold
                ),
                "all_windows": int(len(part)),
                "selected_windows": count,
                "excluded_windows": int(
                    len(part) - count
                ),
                "total_effective_area_km2": (
                    total_area / 1e6
                ),
                "selected_effective_area_km2": (
                    selected_area / 1e6
                ),
                "selected_area_fraction": (
                    selected_area / total_area
                ),
                "selected_height_valid_windows": int(
                    height_available.sum()
                ),
            })

    return pd.DataFrame(records)


# ============================================================
# 6. PAIRWISE RELATIONSHIPS
# ============================================================

def calculate_pairwise_relations(
    windows: pd.DataFrame,
) -> pd.DataFrame:

    records = []

    for (city_id, scale), part in windows.groupby(
        ["city_id", "scale"],
        sort=True,
    ):

        for selection_name, threshold in (
            WINDOW_SELECTIONS.items()
        ):

            selected = part.loc[
                part[
                    "window_effective_area_fraction"
                ] >= threshold
            ]

            for variable_x, variable_y in VARIABLE_PAIRS:

                # 2D pairs:
                #     denominator = effective window area.
                #
                # Height pairs:
                #     denominator = valid-height cell area.
                #
                # In either case the association is between
                # window-level metric values, not cell values.

                includes_height = (
                    HEIGHT in (variable_x, variable_y)
                )

                weight_col = (
                    "height_valid_cell_area_m2"
                    if includes_height
                    else "effective_area_m2"
                )

                x = selected[variable_x].to_numpy(
                    dtype=np.float64
                )

                y = selected[variable_y].to_numpy(
                    dtype=np.float64
                )

                weights = selected[
                    weight_col
                ].to_numpy(
                    dtype=np.float64
                )

                valid = (
                    np.isfinite(x)
                    & np.isfinite(y)
                    & np.isfinite(weights)
                    & (weights > 0)
                )

                x_valid = x[valid]
                y_valid = y[valid]
                w_valid = weights[valid]

                n_valid = len(x_valid)

                if n_valid < MIN_VALID_WINDOWS:

                    rho = np.nan
                    weighted_r = np.nan

                    status = "INSUFFICIENT_WINDOWS"

                else:

                    rho = spearman_rho(
                        x_valid,
                        y_valid,
                    )

                    weighted_r = weighted_pearson(
                        x_valid,
                        y_valid,
                        w_valid,
                    )

                    status = (
                        "DESCRIPTIVE_OK"
                        if (
                            np.isfinite(rho)
                            and np.isfinite(weighted_r)
                        )
                        else "UNDEFINED_VARIANCE"
                    )

                records.append({
                    "city_id": city_id,
                    "scale": scale,
                    "selection": selection_name,
                    "variable_x": variable_x,
                    "variable_y": variable_y,
                    "all_selected_windows": int(
                        len(selected)
                    ),
                    "valid_pair_windows": n_valid,
                    "weight_type": weight_col,
                    "weight_sum_km2": float(
                        w_valid.sum() / 1e6
                    ),
                    "spearman_rho": rho,
                    "weighted_pearson_r": weighted_r,
                    "spearman_sign": (
                        relationship_sign(rho)
                    ),
                    "weighted_pearson_sign": (
                        relationship_sign(weighted_r)
                    ),
                    "status": status,
                })

    return pd.DataFrame(records)


# ============================================================
# 7. CROSS-SCALE STABILITY
# ============================================================

def cross_scale_stability(
    relations: pd.DataFrame,
) -> pd.DataFrame:

    records = []

    for city_id in EXPECTED_CITIES:

        for selection_name in WINDOW_SELECTIONS:

            for variable_x, variable_y in VARIABLE_PAIRS:

                subset = relations.loc[
                    relations["city_id"].eq(city_id)
                    & relations["selection"].eq(
                        selection_name
                    )
                    & relations["variable_x"].eq(
                        variable_x
                    )
                    & relations["variable_y"].eq(
                        variable_y
                    )
                ]

                require(
                    len(subset) == 2,
                    (
                        f"{city_id}: missing 1km/5km "
                        "relationship record"
                    ),
                )

                rows = subset.set_index("scale")

                require(
                    {"1km", "5km"}.issubset(
                        rows.index
                    ),
                    (
                        f"{city_id}: incomplete "
                        "cross-scale records"
                    ),
                )

                for metric in [
                    "spearman_rho",
                    "weighted_pearson_r",
                ]:

                    value_1km = float(
                        rows.loc["1km", metric]
                    )

                    value_5km = float(
                        rows.loc["5km", metric]
                    )

                    finite = (
                        np.isfinite(value_1km)
                        and np.isfinite(value_5km)
                    )

                    if finite:

                        sign_1km = relationship_sign(
                            value_1km
                        )

                        sign_5km = relationship_sign(
                            value_5km
                        )

                        same_sign = (
                            sign_1km == sign_5km
                        )

                        absolute_change = abs(
                            value_5km - value_1km
                        )

                        status = (
                            "SAME_SIGN"
                            if same_sign
                            else "SIGN_CHANGE"
                        )

                    else:

                        sign_1km = relationship_sign(
                            value_1km
                        )

                        sign_5km = relationship_sign(
                            value_5km
                        )

                        same_sign = None
                        absolute_change = np.nan

                        status = "UNDEFINED"

                    records.append({
                        "city_id": city_id,
                        "selection": selection_name,
                        "variable_x": variable_x,
                        "variable_y": variable_y,
                        "association_metric": metric,
                        "value_1km": value_1km,
                        "value_5km": value_5km,
                        "sign_1km": sign_1km,
                        "sign_5km": sign_5km,
                        "same_sign": same_sign,
                        "absolute_change": absolute_change,
                        "status": status,
                    })

    return pd.DataFrame(records)


# ============================================================
# 8. MAIN
# ============================================================

def main():

    source = preflight()

    windows = load_windows()

    scale_qc = cross_scale_qc(
        windows,
        source["source_qc"],
    )

    print("\n=== ANALYSIS ===")

    coverage_df = coverage_diagnostics(
        windows
    )

    relations_df = calculate_pairwise_relations(
        windows
    )

    stability_df = cross_scale_stability(
        relations_df
    )

    # Data/schema/aggregation QC is independent of whether
    # a particular relationship can be estimated.
    #
    # INS UFFICIENT_WINDOWS and UNDEFINED_VARIANCE remain
    # explicitly reported in the relationship tables.

    qc_status = (
        "PASS"
        if all(
            record["status"] == "PASS"
            for record in scale_qc
        )
        else "HOLD"
    )

    print("\n=== WINDOW COVERAGE ===")

    print(
        coverage_df[
            [
                "city_id",
                "scale",
                "selection",
                "selected_windows",
                "excluded_windows",
                "selected_area_fraction",
                "selected_height_valid_windows",
            ]
        ].to_string(index=False)
    )

    print("\n=== PAIRWISE RELATIONSHIPS ===")

    print(
        relations_df[
            [
                "city_id",
                "scale",
                "selection",
                "variable_x",
                "variable_y",
                "valid_pair_windows",
                "spearman_rho",
                "weighted_pearson_r",
                "status",
            ]
        ].to_string(index=False)
    )

    print("\n=== CROSS-SCALE STABILITY ===")

    print(
        stability_df[
            [
                "city_id",
                "selection",
                "variable_x",
                "variable_y",
                "association_metric",
                "value_1km",
                "value_5km",
                "status",
            ]
        ].to_string(index=False)
    )

    print("\n=== QC ===")
    print("OVERALL_QC:", qc_status)

    if qc_status != "PASS":

        print(
            "OUTPUT_NOT_CREATED: "
            "cross-scale QC did not pass"
        )

        return

    # --------------------------------------------------------
    # Create a new nonproduction output directory.
    # All analysis and QC above are complete before writing.
    # --------------------------------------------------------

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_dir = (
        OUTPUT_BASE / f"run_{run_id}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    outputs = {
        "pairwise_relations.csv": relations_df,
        "window_coverage_diagnostics.csv": coverage_df,
        "cross_scale_stability.csv": stability_df,
    }

    for filename, table in outputs.items():

        table.to_csv(
            output_dir / filename,
            index=False,
            encoding="utf-8-sig",
        )

    qc_summary = {
        "work_package": "WP-MORPH-03",
        "status": "NONPRODUCTION_EXPLORATORY",
        "overall_qc": qc_status,
        "source_work_package": "WP-MORPH-02B",
        "source_manifest_sha256": source[
            "manifest_hash"
        ],
        "cross_scale_qc": scale_qc,
        "registered_variables": [
            BUILDING,
            ROAD,
            HEIGHT,
        ],
        "registered_pairs": [
            list(pair)
            for pair in VARIABLE_PAIRS
        ],
        "window_selections": WINDOW_SELECTIONS,
        "minimum_valid_windows": MIN_VALID_WINDOWS,
        "limitations": [
            "Relationships are descriptive, not causal",
            "No statistical significance test is performed",
            "Spatial autocorrelation is not accounted for",
            "Spearman is unweighted",
            "Weighted Pearson uses explicit area weights",
            "Height analysis uses valid-height area weights",
            "Incomplete-window sensitivity is reported",
            "No residential-deficit labels are used",
            "No formal CANU result is generated",
            "No scientific gate is modified",
        ],
    }

    qc_path = output_dir / "qc_summary.json"

    qc_path.write_text(
        json.dumps(
            qc_summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_hashes = {
        filename: sha256_file(
            output_dir / filename
        )
        for filename in outputs
    }

    output_hashes["qc_summary.json"] = sha256_file(
        qc_path
    )

    script_path = Path(__file__).resolve()

    require(
        script_path.is_file(),
        "Unable to verify current script",
    )

    manifest = {
        "work_package": "WP-MORPH-03",
        "status": "NONPRODUCTION_EXPLORATORY",
        "run_id": run_id,
        "source_directory": str(SOURCE_DIR),
        "source_manifest_sha256": source[
            "manifest_hash"
        ],
        "script_path": str(script_path),
        "script_sha256_at_run": sha256_file(
            script_path
        ),
        "registered_scales": SCALE_CONFIG,
        "registered_variables": [
            BUILDING,
            ROAD,
            HEIGHT,
        ],
        "registered_pairs": [
            list(pair)
            for pair in VARIABLE_PAIRS
        ],
        "registered_selections": WINDOW_SELECTIONS,
        "minimum_valid_windows": MIN_VALID_WINDOWS,
        "output_hashes": output_hashes,
        "overall_qc": qc_status,
        "formal_canu_gates_changed": False,
    }

    manifest_path = output_dir / "manifest.json"

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n=== COMPLETED ===")

    print("STATUS: NONPRODUCTION_EXPLORATORY")
    print("OVERALL_QC:", qc_status)
    print("OUTPUT:", output_dir)
    print("SCRIPT_SHA256:", manifest["script_sha256_at_run"])
    print("FORMAL_CANU_GATES: UNCHANGED")


if __name__ == "__main__":
    main()
