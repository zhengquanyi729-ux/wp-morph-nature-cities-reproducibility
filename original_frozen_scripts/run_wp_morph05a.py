"""
WP-MORPH-05A
Independent three-city validation aggregation freeze.

PURPOSE
-------
Create the fixed 1 km and 5 km morphology aggregation tables for the
three validation cities authorized by WP-MORPH-04H.

SOLE AUTHORIZATION ENTRY
------------------------
WP-MORPH-04H validation_city_nomination.json

This script does NOT:
    - search for alternative validation cities
    - re-open roster adjudication
    - re-evaluate QC evidence
    - compute Spearman correlations
    - compute Pearson correlations
    - inspect or select results based on correlation direction/magnitude
    - modify the frozen 1 km / 5 km windows
    - modify ALL / COVERAGE_80 definitions
    - change formal CANU production gates

AUTHORIZED INPUT ACCESS
-----------------------
For each nominated validation city, the script:
    1. re-checks current Parquet row count and SHA-256 identity;
    2. reads only the fields required to construct the frozen
       1 km / 5 km aggregation products;
    3. writes aggregation products and QC records;
    4. does not calculate any cross-variable relationship statistic.

FROZEN AGGREGATION CONTRACT
---------------------------
Base grid:
    50 m.

Scales:
    1 km = 20 x 20 base-grid indices.
    5 km = 100 x 100 base-grid indices.

Window indexing:
    window_row = floor(grid_row / block_cells)
    window_col = floor(grid_col / block_cells)

ALL:
    all generated windows.

COVERAGE_80:
    effective_area_fraction >= 0.80

building_coverage_mean:
    sum(building_covered_area_m2) / sum(effective_area_m2)

road_density_mean_km_per_km2:
    [sum(road_length_m) / 1000] /
    [sum(effective_area_m2) / 1,000,000]

height_conditional_mean_m:
    weighted mean of building_height_main_m using
    supported_building_overlap_area_m2 as weights;
    cells without valid supported height remain missing and are not
    converted to zero.

STATUS
------
NONPRODUCTION_VALIDATION_AGGREGATION
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# 0. FIXED PATHS
# ============================================================

ROOT = Path(r"C:\china_meld")

WP04H_DIR = (
    ROOT
    / "experiments"
    / "wp_morph04h_nonproduction"
    / "run_20260927_172509_532787"
)

OUTPUT_BASE = (
    ROOT
    / "experiments"
    / "wp_morph05a_nonproduction"
)

TARGET_CITY_COUNT = 3

BASE_CELL_SIZE_M = 50

SCALES = {
    "1km": 20,
    "5km": 100,
}

COVERAGE_80_THRESHOLD = 0.80

REQUIRED_GRID_COLUMNS = [
    "pilot_id",
    "grid_row",
    "grid_col",
    "effective_area_m2",
    "building_covered_area_m2",
    "building_overlap_area_sum_m2",
    "supported_building_overlap_area_m2",
    "building_height_main_m",
    "road_length_m",
]

OPTIONAL_QC_COLUMNS = [
    "building_coverage_fraction",
    "road_length_density_km_per_km2",
    "height_support_fraction_of_built_overlap",
]

FLOAT_TOL_ABS = 1e-8
AREA_REL_TOL = 1e-9


# ============================================================
# 1. GENERAL HELPERS
# ============================================================

def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(
                16 * 1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest().upper()


def read_json(
    path: Path,
) -> dict:
    require(
        path.is_file(),
        f"Missing JSON: {path}",
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def write_json(
    path: Path,
    obj: dict,
) -> None:
    path.write_text(
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )


def parse_bool(
    value: Any,
) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return (
        str(value)
        .strip()
        .lower()
        in {
            "true",
            "1",
            "yes",
            "y",
            "t",
        }
    )


def safe_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except Exception:
        return None

    if not np.isfinite(result):
        return None

    return result


def relative_close(
    a: float,
    b: float,
    rel_tol: float = AREA_REL_TOL,
    abs_tol: float = FLOAT_TOL_ABS,
) -> bool:
    return bool(
        np.isclose(
            a,
            b,
            rtol=rel_tol,
            atol=abs_tol,
            equal_nan=False,
        )
    )


# ============================================================
# 2. VERIFY WP04H AUTHORIZATION
# ============================================================

def verify_wp04h_authorization() -> dict:
    print(
        "\n=== WP-MORPH-05A AUTHORIZATION PREFLIGHT ==="
    )

    manifest_path = (
        WP04H_DIR
        / "manifest.json"
    )

    qc_path = (
        WP04H_DIR
        / "qc_summary.json"
    )

    nomination_path = (
        WP04H_DIR
        / "validation_city_nomination.json"
    )

    manifest = read_json(
        manifest_path
    )

    qc = read_json(
        qc_path
    )

    nomination = read_json(
        nomination_path
    )

    require(
        manifest.get(
            "work_package"
        )
        == "WP-MORPH-04H",
        "Unexpected WP04H manifest identity",
    )

    require(
        manifest.get(
            "status"
        )
        == "AUTHORIZED_FOR_WP_MORPH05_NONPRODUCTION",
        (
            "WP04H manifest does not authorize "
            "WP-MORPH-05 nonproduction validation"
        ),
    )

    require(
        manifest.get(
            "validation_execution_authorized"
        )
        is True,
        (
            "WP04H manifest validation authorization "
            "is not True"
        ),
    )

    require(
        manifest.get(
            "formal_canu_production_authorized"
        )
        is False,
        (
            "Formal CANU production authorization "
            "must remain False"
        ),
    )

    require(
        manifest.get(
            "formal_canu_gates_changed"
        )
        is False,
        (
            "Formal CANU gates unexpectedly changed"
        ),
    )

    require(
        qc.get(
            "validation_execution_authorized"
        )
        is True,
        (
            "WP04H qc_summary does not authorize "
            "validation execution"
        ),
    )

    require(
        qc.get(
            "canonical_roster"
        )
        == "VERIFIED",
        (
            "WP04H canonical roster is not VERIFIED"
        ),
    )

    require(
        qc.get(
            "final_identity_pass"
        )
        is True,
        (
            "WP04H final identity gate did not pass"
        ),
    )

    require(
        nomination.get(
            "work_package"
        )
        == "WP-MORPH-04H",
        (
            "Unexpected nomination work package"
        ),
    )

    require(
        nomination.get(
            "status"
        )
        == "AUTHORIZED_FOR_WP_MORPH05_NONPRODUCTION",
        (
            "Nomination file does not authorize "
            "WP-MORPH-05 nonproduction validation"
        ),
    )

    require(
        nomination.get(
            "validation_execution_authorized"
        )
        is True,
        (
            "Nomination authorization is not True"
        ),
    )

    require(
        nomination.get(
            "formal_canu_production_authorized"
        )
        is False,
        (
            "Nomination must not authorize formal CANU"
        ),
    )

    output_hashes = (
        manifest.get(
            "output_hashes",
            {},
        )
    )

    for filename in [
        "qc_summary.json",
        "validation_city_nomination.json",
        "final_identity_recheck.csv",
    ]:
        require(
            filename
            in output_hashes,
            (
                f"WP04H manifest does not register {filename}"
            ),
        )

        path = (
            WP04H_DIR
            / filename
        )

        require(
            path.is_file(),
            f"Missing registered WP04H output: {path}",
        )

        actual = sha256_file(
            path
        )

        expected = str(
            output_hashes[
                filename
            ]
        ).upper()

        require(
            actual == expected,
            (
                f"WP04H registered output hash mismatch: "
                f"{filename}"
            ),
        )

    selected = (
        nomination.get(
            "selected_cities",
            [],
        )
    )

    require(
        isinstance(
            selected,
            list,
        )
        and len(selected)
        == TARGET_CITY_COUNT,
        (
            "Nomination must contain exactly "
            f"{TARGET_CITY_COUNT} validation cities"
        ),
    )

    ranks = [
        int(
            row[
                "selection_rank"
            ]
        )
        for row
        in selected
    ]

    require(
        ranks == [
            1,
            2,
            3,
        ],
        (
            "Nomination selection ranks are not [1, 2, 3]"
        ),
    )

    city_ids = [
        str(
            row[
                "city_id"
            ]
        )
        for row
        in selected
    ]

    require(
        len(
            set(
                city_ids
            )
        )
        == TARGET_CITY_COUNT,
        (
            "Duplicate validation city IDs in nomination"
        ),
    )

    manifest_city_ids = [
        str(x)
        for x
        in manifest.get(
            "nominated_city_ids",
            [],
        )
    ]

    require(
        manifest_city_ids
        == city_ids,
        (
            "WP04H manifest nominated_city_ids "
            "do not match nomination file"
        ),
    )

    qc_city_ids = [
        str(x)
        for x
        in qc.get(
            "nominated_city_ids",
            [],
        )
    ]

    require(
        qc_city_ids
        == city_ids,
        (
            "WP04H qc_summary nominated_city_ids "
            "do not match nomination file"
        ),
    )

    print(
        "WP04H_MANIFEST_SHA256:",
        sha256_file(
            manifest_path
        ),
    )

    print(
        "WP04H_NOMINATION_SHA256:",
        sha256_file(
            nomination_path
        ),
    )

    print(
        "AUTHORIZED_VALIDATION_CITY_IDS:",
        city_ids,
    )

    print(
        "AUTHORIZATION_SCOPE:",
        nomination.get(
            "authorization_scope"
        ),
    )

    print(
        "FORMAL_CANU_GATES: UNCHANGED"
    )

    print(
        "AUTHORIZATION_PREFLIGHT: PASS"
    )

    return {
        "manifest_path": (
            manifest_path
        ),
        "manifest": (
            manifest
        ),
        "qc_path": (
            qc_path
        ),
        "qc": (
            qc
        ),
        "nomination_path": (
            nomination_path
        ),
        "nomination": (
            nomination
        ),
        "selected_cities": (
            selected
        ),
        "city_ids": (
            city_ids
        ),
    }


# ============================================================
# 3. FROZEN AGGREGATION CONTRACT
# ============================================================

def build_aggregation_contract() -> dict:
    return {
        "contract_id": (
            "WP-MORPH-05A-AGGREGATION-V1"
        ),
        "status": (
            "FROZEN_BEFORE_RELATIONSHIP_ANALYSIS"
        ),
        "base_grid_cell_size_m": (
            BASE_CELL_SIZE_M
        ),
        "spatial_scales": {
            "1km": {
                "block_cells": 20,
                "nominal_window_size_m": 1000,
                "nominal_window_area_m2": 1_000_000,
            },
            "5km": {
                "block_cells": 100,
                "nominal_window_size_m": 5000,
                "nominal_window_area_m2": 25_000_000,
            },
        },
        "window_index_rule": (
            "window_row=floor(grid_row/block_cells); "
            "window_col=floor(grid_col/block_cells)"
        ),
        "selections": {
            "ALL": (
                "all generated windows"
            ),
            "COVERAGE_80": (
                "effective_area_fraction >= 0.80"
            ),
        },
        "coverage_80_threshold": (
            COVERAGE_80_THRESHOLD
        ),
        "variables": {
            "building_coverage_mean": (
                "sum(building_covered_area_m2) / "
                "sum(effective_area_m2)"
            ),
            "road_density_mean_km_per_km2": (
                "(sum(road_length_m)/1000) / "
                "(sum(effective_area_m2)/1e6)"
            ),
            "height_conditional_mean_m": (
                "weighted mean of building_height_main_m "
                "using supported_building_overlap_area_m2 "
                "as weights among valid supported-height cells"
            ),
        },
        "height_missing_rule": (
            "Height missingness remains missing. "
            "No missing height is converted to zero."
        ),
        "relationship_statistics_computed": False,
        "correlations_computed": False,
        "formal_canu_gates_changed": False,
    }


# ============================================================
# 4. INPUT IDENTITY + SCHEMA CHECK
# ============================================================

def verify_city_input(
    city_record: dict,
) -> dict:
    city_id = str(
        city_record[
            "city_id"
        ]
    )

    path = Path(
        city_record[
            "grid_path"
        ]
    )

    expected_rows = int(
        city_record[
            "parquet_rows"
        ]
    )

    expected_sha = str(
        city_record[
            "sha256"
        ]
    ).upper()

    require(
        path.is_file(),
        (
            f"{city_id}: nominated grid file missing: "
            f"{path}"
        ),
    )

    parquet = pq.ParquetFile(
        path
    )

    current_rows = int(
        parquet.metadata.num_rows
    )

    schema_names = set(
        parquet.schema_arrow.names
    )

    parquet.close()

    current_sha = sha256_file(
        path
    )

    row_match = (
        current_rows
        == expected_rows
    )

    sha_match = (
        current_sha
        == expected_sha
    )

    missing_required = [
        column
        for column
        in REQUIRED_GRID_COLUMNS
        if column
        not in schema_names
    ]

    optional_present = [
        column
        for column
        in OPTIONAL_QC_COLUMNS
        if column
        in schema_names
    ]

    require(
        row_match,
        (
            f"{city_id}: current row count changed "
            f"({current_rows} != {expected_rows})"
        ),
    )

    require(
        sha_match,
        (
            f"{city_id}: current SHA-256 changed"
        ),
    )

    require(
        not missing_required,
        (
            f"{city_id}: missing required grid columns: "
            f"{missing_required}"
        ),
    )

    return {
        "city_id": (
            city_id
        ),
        "city_name": str(
            city_record[
                "city_name"
            ]
        ),
        "selection_rank": int(
            city_record[
                "selection_rank"
            ]
        ),
        "grid_path": str(
            path.resolve()
        ),
        "expected_rows": (
            expected_rows
        ),
        "current_rows": (
            current_rows
        ),
        "expected_sha256": (
            expected_sha
        ),
        "current_sha256": (
            current_sha
        ),
        "row_count_match": (
            row_match
        ),
        "sha256_match": (
            sha_match
        ),
        "required_schema_pass": True,
        "optional_qc_columns_present": (
            ";".join(
                optional_present
            )
        ),
    }


# ============================================================
# 5. LOAD AUTHORIZED GRID COLUMNS ONLY
# ============================================================

def read_authorized_grid(
    identity_record: dict,
) -> pd.DataFrame:
    path = Path(
        identity_record[
            "grid_path"
        ]
    )

    parquet = pq.ParquetFile(
        path
    )

    schema_names = set(
        parquet.schema_arrow.names
    )

    parquet.close()

    columns = (
        REQUIRED_GRID_COLUMNS
        + [
            column
            for column
            in OPTIONAL_QC_COLUMNS
            if column
            in schema_names
        ]
    )

    frame = pd.read_parquet(
        path,
        columns=columns,
    )

    require(
        len(frame)
        == int(
            identity_record[
                "current_rows"
            ]
        ),
        (
            f"{identity_record['city_id']}: "
            "loaded row count differs from Parquet metadata"
        ),
    )

    return frame


# ============================================================
# 6. BASE-GRID QC
# ============================================================

def run_base_grid_qc(
    city_id: str,
    frame: pd.DataFrame,
) -> dict:
    require(
        frame[
            "grid_row"
        ].notna().all()
        and frame[
            "grid_col"
        ].notna().all(),
        (
            f"{city_id}: missing grid_row/grid_col"
        ),
    )

    require(
        not frame.duplicated(
            [
                "grid_row",
                "grid_col",
            ]
        ).any(),
        (
            f"{city_id}: duplicate grid_row/grid_col pairs"
        ),
    )

    pilot_values = (
        frame[
            "pilot_id"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    require(
        pilot_values == [
            city_id
        ],
        (
            f"{city_id}: pilot_id values do not match "
            f"authorized city: {pilot_values}"
        ),
    )

    for column in [
        "effective_area_m2",
        "building_covered_area_m2",
        "building_overlap_area_sum_m2",
        "supported_building_overlap_area_m2",
        "road_length_m",
    ]:
        values = pd.to_numeric(
            frame[
                column
            ],
            errors="coerce",
        )

        require(
            values.notna().all(),
            (
                f"{city_id}: nonnumeric or missing {column}"
            ),
        )

        require(
            np.isfinite(
                values.to_numpy(
                    dtype=float
                )
            ).all(),
            (
                f"{city_id}: nonfinite {column}"
            ),
        )

        require(
            (
                values
                >= -FLOAT_TOL_ABS
            ).all(),
            (
                f"{city_id}: negative {column}"
            ),
        )

    effective = pd.to_numeric(
        frame[
            "effective_area_m2"
        ],
        errors="raise",
    ).astype(float)

    covered = pd.to_numeric(
        frame[
            "building_covered_area_m2"
        ],
        errors="raise",
    ).astype(float)

    overlap = pd.to_numeric(
        frame[
            "building_overlap_area_sum_m2"
        ],
        errors="raise",
    ).astype(float)

    supported = pd.to_numeric(
        frame[
            "supported_building_overlap_area_m2"
        ],
        errors="raise",
    ).astype(float)

    require(
        (
            covered
            <= effective
            + np.maximum(
                1.0,
                np.abs(
                    effective
                ),
            )
            * 1e-9
        ).all(),
        (
            f"{city_id}: building_covered_area_m2 "
            "exceeds effective_area_m2"
        ),
    )

    require(
        (
            supported
            <= overlap
            + np.maximum(
                1.0,
                np.abs(
                    overlap
                ),
            )
            * 1e-9
        ).all(),
        (
            f"{city_id}: supported height overlap "
            "exceeds total building overlap"
        ),
    )

    height = pd.to_numeric(
        frame[
            "building_height_main_m"
        ],
        errors="coerce",
    ).astype(float)

    positive_support = (
        supported
        > FLOAT_TOL_ABS
    )

    invalid_height_with_support = (
        positive_support
        & ~np.isfinite(
            height
        )
    )

    require(
        not invalid_height_with_support.any(),
        (
            f"{city_id}: positive supported height area "
            "exists with missing/nonfinite building height"
        ),
    )

    optional_checks = {}

    if (
        "building_coverage_fraction"
        in frame.columns
    ):
        coverage_fraction = pd.to_numeric(
            frame[
                "building_coverage_fraction"
            ],
            errors="coerce",
        ).astype(float)

        valid_effective = (
            effective
            > FLOAT_TOL_ABS
        )

        derived = np.full(
            len(frame),
            np.nan,
            dtype=float,
        )

        derived[
            valid_effective.to_numpy()
        ] = (
            covered[
                valid_effective
            ].to_numpy()
            / effective[
                valid_effective
            ].to_numpy()
        )

        compared = (
            valid_effective.to_numpy()
            & np.isfinite(
                coverage_fraction.to_numpy()
            )
        )

        if compared.any():
            max_abs_diff = float(
                np.max(
                    np.abs(
                        coverage_fraction.to_numpy()[
                            compared
                        ]
                        - derived[
                            compared
                        ]
                    )
                )
            )
        else:
            max_abs_diff = None

        optional_checks[
            "building_coverage_fraction_max_abs_diff"
        ] = (
            max_abs_diff
        )

    if (
        "road_length_density_km_per_km2"
        in frame.columns
    ):
        road_density = pd.to_numeric(
            frame[
                "road_length_density_km_per_km2"
            ],
            errors="coerce",
        ).astype(float)

        road_length = pd.to_numeric(
            frame[
                "road_length_m"
            ],
            errors="raise",
        ).astype(float)

        valid_effective = (
            effective
            > FLOAT_TOL_ABS
        )

        derived = np.full(
            len(frame),
            np.nan,
            dtype=float,
        )

        derived[
            valid_effective.to_numpy()
        ] = (
            road_length[
                valid_effective
            ].to_numpy()
            * 1000.0
            / effective[
                valid_effective
            ].to_numpy()
        )

        compared = (
            valid_effective.to_numpy()
            & np.isfinite(
                road_density.to_numpy()
            )
        )

        if compared.any():
            max_abs_diff = float(
                np.max(
                    np.abs(
                        road_density.to_numpy()[
                            compared
                        ]
                        - derived[
                            compared
                        ]
                    )
                )
            )
        else:
            max_abs_diff = None

        optional_checks[
            "road_density_max_abs_diff"
        ] = (
            max_abs_diff
        )

    return {
        "city_id": (
            city_id
        ),
        "rows": int(
            len(
                frame
            )
        ),
        "unique_grid_indices": int(
            frame[
                [
                    "grid_row",
                    "grid_col",
                ]
            ]
            .drop_duplicates()
            .shape[
                0
            ]
        ),
        "effective_area_m2_sum": float(
            effective.sum()
        ),
        "building_covered_area_m2_sum": float(
            covered.sum()
        ),
        "road_length_m_sum": float(
            pd.to_numeric(
                frame[
                    "road_length_m"
                ],
                errors="raise",
            ).sum()
        ),
        "supported_height_area_m2_sum": float(
            supported.sum()
        ),
        "valid_height_support_rows": int(
            positive_support.sum()
        ),
        "optional_checks": (
            optional_checks
        ),
        "base_grid_qc": (
            "PASS"
        ),
    }


# ============================================================
# 7. AGGREGATION
# ============================================================

def aggregate_scale(
    city_id: str,
    city_name: str,
    frame: pd.DataFrame,
    scale_name: str,
    block_cells: int,
) -> pd.DataFrame:
    nominal_window_size_m = (
        block_cells
        * BASE_CELL_SIZE_M
    )

    nominal_window_area_m2 = (
        float(
            nominal_window_size_m
            ** 2
        )
    )

    work = pd.DataFrame(
        {
            "grid_row": pd.to_numeric(
                frame[
                    "grid_row"
                ],
                errors="raise",
            ).astype(
                np.int64
            ),
            "grid_col": pd.to_numeric(
                frame[
                    "grid_col"
                ],
                errors="raise",
            ).astype(
                np.int64
            ),
            "effective_area_m2": pd.to_numeric(
                frame[
                    "effective_area_m2"
                ],
                errors="raise",
            ).astype(float),
            "building_covered_area_m2": pd.to_numeric(
                frame[
                    "building_covered_area_m2"
                ],
                errors="raise",
            ).astype(float),
            "road_length_m": pd.to_numeric(
                frame[
                    "road_length_m"
                ],
                errors="raise",
            ).astype(float),
            "supported_height_area_m2": pd.to_numeric(
                frame[
                    "supported_building_overlap_area_m2"
                ],
                errors="raise",
            ).astype(float),
            "height_m": pd.to_numeric(
                frame[
                    "building_height_main_m"
                ],
                errors="coerce",
            ).astype(float),
        }
    )

    work[
        "window_row"
    ] = (
        work[
            "grid_row"
        ]
        // block_cells
    )

    work[
        "window_col"
    ] = (
        work[
            "grid_col"
        ]
        // block_cells
    )

    height_valid = (
        np.isfinite(
            work[
                "height_m"
            ].to_numpy()
        )
        & (
            work[
                "supported_height_area_m2"
            ].to_numpy()
            > FLOAT_TOL_ABS
        )
    )

    work[
        "height_valid_area_m2"
    ] = np.where(
        height_valid,
        work[
            "supported_height_area_m2"
        ].to_numpy(),
        0.0,
    )

    work[
        "height_weighted_sum_m3"
    ] = np.where(
        height_valid,
        work[
            "height_m"
        ].to_numpy()
        * work[
            "supported_height_area_m2"
        ].to_numpy(),
        0.0,
    )

    work[
        "height_valid_cell"
    ] = (
        height_valid.astype(
            np.int64
        )
    )

    grouped = (
        work.groupby(
            [
                "window_row",
                "window_col",
            ],
            sort=True,
            observed=True,
        )
        .agg(
            cell_count=(
                "grid_row",
                "size",
            ),
            effective_area_m2=(
                "effective_area_m2",
                "sum",
            ),
            building_covered_area_m2=(
                "building_covered_area_m2",
                "sum",
            ),
            road_length_m=(
                "road_length_m",
                "sum",
            ),
            height_valid_area_m2=(
                "height_valid_area_m2",
                "sum",
            ),
            height_weighted_sum_m3=(
                "height_weighted_sum_m3",
                "sum",
            ),
            height_valid_cell_count=(
                "height_valid_cell",
                "sum",
            ),
        )
        .reset_index()
    )

    effective = (
        grouped[
            "effective_area_m2"
        ].to_numpy(
            dtype=float
        )
    )

    building = (
        grouped[
            "building_covered_area_m2"
        ].to_numpy(
            dtype=float
        )
    )

    road = (
        grouped[
            "road_length_m"
        ].to_numpy(
            dtype=float
        )
    )

    height_area = (
        grouped[
            "height_valid_area_m2"
        ].to_numpy(
            dtype=float
        )
    )

    height_weighted = (
        grouped[
            "height_weighted_sum_m3"
        ].to_numpy(
            dtype=float
        )
    )

    building_coverage = np.full(
        len(
            grouped
        ),
        np.nan,
        dtype=float,
    )

    road_density = np.full(
        len(
            grouped
        ),
        np.nan,
        dtype=float,
    )

    height_mean = np.full(
        len(
            grouped
        ),
        np.nan,
        dtype=float,
    )

    height_area_fraction = np.full(
        len(
            grouped
        ),
        np.nan,
        dtype=float,
    )

    valid_effective = (
        effective
        > FLOAT_TOL_ABS
    )

    building_coverage[
        valid_effective
    ] = (
        building[
            valid_effective
        ]
        / effective[
            valid_effective
        ]
    )

    road_density[
        valid_effective
    ] = (
        road[
            valid_effective
        ]
        * 1000.0
        / effective[
            valid_effective
        ]
    )

    valid_height = (
        height_area
        > FLOAT_TOL_ABS
    )

    height_mean[
        valid_height
    ] = (
        height_weighted[
            valid_height
        ]
        / height_area[
            valid_height
        ]
    )

    valid_height_fraction = (
        valid_effective
    )

    height_area_fraction[
        valid_height_fraction
    ] = (
        height_area[
            valid_height_fraction
        ]
        / effective[
            valid_height_fraction
        ]
    )

    grouped.insert(
        0,
        "city_id",
        city_id,
    )

    grouped.insert(
        1,
        "city_name",
        city_name,
    )

    grouped.insert(
        2,
        "scale",
        scale_name,
    )

    grouped[
        "block_cells"
    ] = (
        block_cells
    )

    grouped[
        "nominal_window_size_m"
    ] = (
        nominal_window_size_m
    )

    grouped[
        "nominal_window_area_m2"
    ] = (
        nominal_window_area_m2
    )

    grouped[
        "effective_area_fraction"
    ] = (
        grouped[
            "effective_area_m2"
        ]
        / nominal_window_area_m2
    )

    require(
        (
            grouped[
                "effective_area_fraction"
            ]
            <= 1.0
            + 1e-6
        ).all(),
        (
            f"{city_id} {scale_name}: "
            "effective_area_fraction exceeds 1"
        ),
    )

    grouped[
        "coverage_80"
    ] = (
        grouped[
            "effective_area_fraction"
        ]
        >= COVERAGE_80_THRESHOLD
    )

    grouped[
        "building_coverage_mean"
    ] = (
        building_coverage
    )

    grouped[
        "road_density_mean_km_per_km2"
    ] = (
        road_density
    )

    grouped[
        "height_conditional_mean_m"
    ] = (
        height_mean
    )

    grouped[
        "height_valid_area_fraction_of_effective"
    ] = (
        height_area_fraction
    )

    grouped = grouped.drop(
        columns=[
            "height_weighted_sum_m3",
        ]
    )

    ordered_columns = [
        "city_id",
        "city_name",
        "scale",
        "block_cells",
        "window_row",
        "window_col",
        "cell_count",
        "nominal_window_size_m",
        "nominal_window_area_m2",
        "effective_area_m2",
        "effective_area_fraction",
        "coverage_80",
        "building_covered_area_m2",
        "building_coverage_mean",
        "road_length_m",
        "road_density_mean_km_per_km2",
        "height_valid_area_m2",
        "height_valid_area_fraction_of_effective",
        "height_valid_cell_count",
        "height_conditional_mean_m",
    ]

    grouped = grouped[
        ordered_columns
    ].sort_values(
        [
            "city_id",
            "window_row",
            "window_col",
        ]
    ).reset_index(
        drop=True
    )

    return grouped


# ============================================================
# 8. AGGREGATION QC
# ============================================================

def aggregation_qc(
    city_id: str,
    base_qc: dict,
    one_km: pd.DataFrame,
    five_km: pd.DataFrame,
) -> dict:
    source_effective = float(
        base_qc[
            "effective_area_m2_sum"
        ]
    )

    source_building = float(
        base_qc[
            "building_covered_area_m2_sum"
        ]
    )

    source_road = float(
        base_qc[
            "road_length_m_sum"
        ]
    )

    source_height_area = float(
        base_qc[
            "supported_height_area_m2_sum"
        ]
    )

    scale_checks = {}

    for scale_name, table in [
        (
            "1km",
            one_km,
        ),
        (
            "5km",
            five_km,
        ),
    ]:
        effective_sum = float(
            table[
                "effective_area_m2"
            ].sum()
        )

        building_sum = float(
            table[
                "building_covered_area_m2"
            ].sum()
        )

        road_sum = float(
            table[
                "road_length_m"
            ].sum()
        )

        height_area_sum = float(
            table[
                "height_valid_area_m2"
            ].sum()
        )

        effective_close = relative_close(
            effective_sum,
            source_effective,
        )

        building_close = relative_close(
            building_sum,
            source_building,
        )

        road_close = relative_close(
            road_sum,
            source_road,
        )

        height_area_close = relative_close(
            height_area_sum,
            source_height_area,
        )

        require(
            effective_close,
            (
                f"{city_id} {scale_name}: "
                "effective-area closure failed"
            ),
        )

        require(
            building_close,
            (
                f"{city_id} {scale_name}: "
                "building-area closure failed"
            ),
        )

        require(
            road_close,
            (
                f"{city_id} {scale_name}: "
                "road-length closure failed"
            ),
        )

        require(
            height_area_close,
            (
                f"{city_id} {scale_name}: "
                "height-valid-area closure failed"
            ),
        )

        scale_checks[
            scale_name
        ] = {
            "window_count_all": int(
                len(
                    table
                )
            ),
            "window_count_coverage80": int(
                table[
                    "coverage_80"
                ].sum()
            ),
            "height_valid_window_count_all": int(
                table[
                    "height_conditional_mean_m"
                ].notna()
                .sum()
            ),
            "height_valid_window_count_coverage80": int(
                (
                    table[
                        "coverage_80"
                    ]
                    & table[
                        "height_conditional_mean_m"
                    ].notna()
                ).sum()
            ),
            "effective_area_closure": (
                effective_close
            ),
            "building_area_closure": (
                building_close
            ),
            "road_length_closure": (
                road_close
            ),
            "height_valid_area_closure": (
                height_area_close
            ),
        }

    one_keys = (
        one_km[
            [
                "window_row",
                "window_col",
            ]
        ]
        .copy()
    )

    one_keys[
        "parent_5km_row"
    ] = (
        one_keys[
            "window_row"
        ]
        // 5
    )

    one_keys[
        "parent_5km_col"
    ] = (
        one_keys[
            "window_col"
        ]
        // 5
    )

    five_keys = {
        (
            int(row),
            int(col),
        )
        for row, col
        in five_km[
            [
                "window_row",
                "window_col",
            ]
        ].itertuples(
            index=False,
            name=None,
        )
    }

    missing_parent_count = sum(
        1
        for row, col
        in one_keys[
            [
                "parent_5km_row",
                "parent_5km_col",
            ]
        ].itertuples(
            index=False,
            name=None,
        )
        if (
            int(row),
            int(col),
        )
        not in five_keys
    )

    require(
        missing_parent_count == 0,
        (
            f"{city_id}: 1km-to-5km nesting failed "
            f"for {missing_parent_count} windows"
        ),
    )

    return {
        "city_id": (
            city_id
        ),
        "scale_checks": (
            scale_checks
        ),
        "nested_1km_to_5km": (
            True
        ),
        "aggregation_qc": (
            "PASS"
        ),
    }


# ============================================================
# 9. MAIN
# ============================================================

def main() -> None:
    authorization = (
        verify_wp04h_authorization()
    )

    contract = (
        build_aggregation_contract()
    )

    run_id = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S_%f"
        )
    )

    output_dir = (
        OUTPUT_BASE
        / f"run_{run_id}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    contract_path = (
        output_dir
        / "aggregation_contract.json"
    )

    write_json(
        contract_path,
        contract,
    )

    identity_rows = []
    base_qc_records = []
    aggregation_qc_records = []
    count_rows = []

    one_km_tables = []
    five_km_tables = []

    print(
        "\n=== VALIDATION INPUT IDENTITY CHECK ==="
    )

    for city_record in (
        authorization[
            "selected_cities"
        ]
    ):
        identity = (
            verify_city_input(
                city_record
            )
        )

        identity_rows.append(
            identity
        )

        print(
            f"{identity['city_id']}: "
            "IDENTITY_PASS"
        )

        frame = (
            read_authorized_grid(
                identity
            )
        )

        base_qc = (
            run_base_grid_qc(
                identity[
                    "city_id"
                ],
                frame,
            )
        )

        base_qc_records.append(
            base_qc
        )

        print(
            f"{identity['city_id']}: "
            "BASE_GRID_QC_PASS"
        )

        one_km = (
            aggregate_scale(
                identity[
                    "city_id"
                ],
                identity[
                    "city_name"
                ],
                frame,
                "1km",
                SCALES[
                    "1km"
                ],
            )
        )

        five_km = (
            aggregate_scale(
                identity[
                    "city_id"
                ],
                identity[
                    "city_name"
                ],
                frame,
                "5km",
                SCALES[
                    "5km"
                ],
            )
        )

        agg_qc = (
            aggregation_qc(
                identity[
                    "city_id"
                ],
                base_qc,
                one_km,
                five_km,
            )
        )

        aggregation_qc_records.append(
            agg_qc
        )

        one_km_tables.append(
            one_km
        )

        five_km_tables.append(
            five_km
        )

        for scale_name, table in [
            (
                "1km",
                one_km,
            ),
            (
                "5km",
                five_km,
            ),
        ]:
            count_rows.append(
                {
                    "city_id": (
                        identity[
                            "city_id"
                        ]
                    ),
                    "city_name": (
                        identity[
                            "city_name"
                        ]
                    ),
                    "scale": (
                        scale_name
                    ),
                    "window_count_all": int(
                        len(
                            table
                        )
                    ),
                    "window_count_coverage80": int(
                        table[
                            "coverage_80"
                        ].sum()
                    ),
                    "height_valid_window_count_all": int(
                        table[
                            "height_conditional_mean_m"
                        ]
                        .notna()
                        .sum()
                    ),
                    "height_valid_window_count_coverage80": int(
                        (
                            table[
                                "coverage_80"
                            ]
                            & table[
                                "height_conditional_mean_m"
                            ].notna()
                        ).sum()
                    ),
                }
            )

        print(
            f"{identity['city_id']}: "
            "1KM_5KM_AGGREGATION_QC_PASS"
        )

        del frame
        del one_km
        del five_km

    identity_df = pd.DataFrame(
        identity_rows
    ).sort_values(
        "selection_rank"
    ).reset_index(
        drop=True
    )

    one_km_all = pd.concat(
        one_km_tables,
        ignore_index=True,
    ).sort_values(
        [
            "city_id",
            "window_row",
            "window_col",
        ]
    ).reset_index(
        drop=True
    )

    five_km_all = pd.concat(
        five_km_tables,
        ignore_index=True,
    ).sort_values(
        [
            "city_id",
            "window_row",
            "window_col",
        ]
    ).reset_index(
        drop=True
    )

    counts_df = pd.DataFrame(
        count_rows
    ).sort_values(
        [
            "city_id",
            "scale",
        ]
    ).reset_index(
        drop=True
    )

    identity_path = (
        output_dir
        / "validation_source_identity.csv"
    )

    one_km_path = (
        output_dir
        / "validation_windows_1km.csv"
    )

    five_km_path = (
        output_dir
        / "validation_windows_5km.csv"
    )

    counts_path = (
        output_dir
        / "window_counts.csv"
    )

    base_qc_path = (
        output_dir
        / "base_grid_qc.json"
    )

    aggregation_qc_path = (
        output_dir
        / "aggregation_qc.json"
    )

    identity_df.to_csv(
        identity_path,
        index=False,
        encoding="utf-8-sig",
    )

    one_km_all.to_csv(
        one_km_path,
        index=False,
        encoding="utf-8-sig",
        float_format="%.12g",
    )

    five_km_all.to_csv(
        five_km_path,
        index=False,
        encoding="utf-8-sig",
        float_format="%.12g",
    )

    counts_df.to_csv(
        counts_path,
        index=False,
        encoding="utf-8-sig",
    )

    write_json(
        base_qc_path,
        {
            "work_package": (
                "WP-MORPH-05A"
            ),
            "records": (
                base_qc_records
            ),
        },
    )

    write_json(
        aggregation_qc_path,
        {
            "work_package": (
                "WP-MORPH-05A"
            ),
            "records": (
                aggregation_qc_records
            ),
        },
    )

    all_qc_pass = bool(
        len(
            identity_df
        )
        == TARGET_CITY_COUNT
        and all(
            row[
                "row_count_match"
            ]
            and row[
                "sha256_match"
            ]
            and row[
                "required_schema_pass"
            ]
            for row
            in identity_rows
        )
        and all(
            record[
                "base_grid_qc"
            ]
            == "PASS"
            for record
            in base_qc_records
        )
        and all(
            record[
                "aggregation_qc"
            ]
            == "PASS"
            for record
            in aggregation_qc_records
        )
    )

    require(
        all_qc_pass,
        (
            "WP-MORPH-05A final QC did not pass"
        ),
    )

    freeze_record = {
        "work_package": (
            "WP-MORPH-05A"
        ),
        "status": (
            "VALIDATION_AGGREGATION_FROZEN"
        ),
        "authorized_city_ids": (
            authorization[
                "city_ids"
            ]
        ),
        "aggregation_contract_id": (
            contract[
                "contract_id"
            ]
        ),
        "spatial_scales": [
            "1km",
            "5km",
        ],
        "selections": [
            "ALL",
            "COVERAGE_80",
        ],
        "relationship_statistics_computed": False,
        "correlations_computed": False,
        "validation_results_used_for_rule_changes": False,
        "wp_morph05b_execution_authorized": True,
        "formal_canu_production_authorized": False,
        "formal_canu_gates_changed": False,
    }

    freeze_path = (
        output_dir
        / "validation_aggregation_freeze.json"
    )

    write_json(
        freeze_path,
        freeze_record,
    )

    qc_summary = {
        "work_package": (
            "WP-MORPH-05A"
        ),
        "status": (
            "VALIDATION_AGGREGATION_FROZEN"
        ),
        "source_wp04h_manifest_sha256": (
            sha256_file(
                authorization[
                    "manifest_path"
                ]
            )
        ),
        "source_wp04h_nomination_sha256": (
            sha256_file(
                authorization[
                    "nomination_path"
                ]
            )
        ),
        "authorized_city_ids": (
            authorization[
                "city_ids"
            ]
        ),
        "authorized_city_count": (
            TARGET_CITY_COUNT
        ),
        "input_identity_pass": (
            True
        ),
        "base_grid_qc_pass": (
            True
        ),
        "aggregation_qc_pass": (
            True
        ),
        "aggregation_contract_frozen": (
            True
        ),
        "relationship_statistics_computed": (
            False
        ),
        "correlations_computed": (
            False
        ),
        "result_values_summarized_in_console": (
            False
        ),
        "wp_morph05b_execution_authorized": (
            True
        ),
        "formal_canu_production_authorized": (
            False
        ),
        "formal_canu_gates_changed": (
            False
        ),
    }

    qc_summary_path = (
        output_dir
        / "qc_summary.json"
    )

    write_json(
        qc_summary_path,
        qc_summary,
    )

    output_files = [
        contract_path,
        identity_path,
        one_km_path,
        five_km_path,
        counts_path,
        base_qc_path,
        aggregation_qc_path,
        freeze_path,
        qc_summary_path,
    ]

    output_hashes = {
        path.name: (
            sha256_file(
                path
            )
        )
        for path
        in output_files
    }

    script_path = Path(
        __file__
    ).resolve()

    manifest = {
        "work_package": (
            "WP-MORPH-05A"
        ),
        "status": (
            "NONPRODUCTION_VALIDATION_AGGREGATION"
        ),
        "run_id": (
            run_id
        ),
        "source_wp04h_directory": (
            str(
                WP04H_DIR
            )
        ),
        "source_wp04h_manifest_sha256": (
            sha256_file(
                authorization[
                    "manifest_path"
                ]
            )
        ),
        "source_wp04h_nomination_sha256": (
            sha256_file(
                authorization[
                    "nomination_path"
                ]
            )
        ),
        "authorized_city_ids": (
            authorization[
                "city_ids"
            ]
        ),
        "script_path": (
            str(
                script_path
            )
        ),
        "script_sha256_at_run": (
            sha256_file(
                script_path
            )
        ),
        "aggregation_contract_id": (
            contract[
                "contract_id"
            ]
        ),
        "relationship_statistics_computed": (
            False
        ),
        "correlations_computed": (
            False
        ),
        "wp_morph05b_execution_authorized": (
            True
        ),
        "formal_canu_production_authorized": (
            False
        ),
        "formal_canu_gates_changed": (
            False
        ),
        "output_hashes": (
            output_hashes
        ),
    }

    manifest_path = (
        output_dir
        / "manifest.json"
    )

    write_json(
        manifest_path,
        manifest,
    )

    print(
        "\n=== WP-MORPH-05A FINAL SUMMARY ==="
    )

    print(
        "AUTHORIZED_CITY_IDS:",
        authorization[
            "city_ids"
        ],
    )

    print(
        "INPUT_IDENTITY_PASS: True"
    )

    print(
        "BASE_GRID_QC_PASS: True"
    )

    print(
        "AGGREGATION_QC_PASS: True"
    )

    print(
        "AGGREGATION_CONTRACT_FROZEN: True"
    )

    print(
        "SPATIAL_SCALES: ['1km', '5km']"
    )

    print(
        "SELECTIONS: ['ALL', 'COVERAGE_80']"
    )

    print(
        "RELATIONSHIP_STATISTICS_COMPUTED: False"
    )

    print(
        "CORRELATIONS_COMPUTED: False"
    )

    print(
        "RESULT_VALUES_SUMMARIZED_IN_CONSOLE: False"
    )

    print(
        "WP_MORPH05B_EXECUTION_AUTHORIZED: True"
    )

    print(
        "FORMAL_CANU_PRODUCTION_AUTHORIZED: False"
    )

    print(
        "FORMAL_CANU_GATES: UNCHANGED"
    )

    print(
        "\n=== COMPLETED ==="
    )

    print(
        "STATUS: VALIDATION_AGGREGATION_FROZEN"
    )

    print(
        "OUTPUT:",
        output_dir,
    )

    print(
        "SCRIPT_SHA256:",
        manifest[
            "script_sha256_at_run"
        ],
    )


if __name__ == "__main__":
    main()
