"""
WP-MORPH-05B
Independent three-city morphology relationship validation.

PURPOSE
-------
Open the frozen WP-MORPH-05A validation aggregation products for the
first time and calculate ONLY the preregistered morphology relationships.

SOLE INPUT PACKAGE
------------------
This script reads ONLY the following five WP-MORPH-05A files:

    validation_windows_1km.csv
    validation_windows_5km.csv
    aggregation_contract.json
    validation_aggregation_freeze.json
    manifest.json

It MUST NOT read the original city Parquet files or any other upstream
QC / roster / exploratory-result file.

VALIDATION UNITS
----------------
3 cities x 2 scales x 2 selections x 3 variable pairs = 36 units.

FROZEN VARIABLE PAIRS
---------------------
1. building_coverage_mean
       <-> road_density_mean_km_per_km2
   Weighted Pearson weight = effective_area_m2

2. building_coverage_mean
       <-> height_conditional_mean_m
   Weighted Pearson weight = height_valid_area_m2

3. road_density_mean_km_per_km2
       <-> height_conditional_mean_m
   Weighted Pearson weight = height_valid_area_m2

For each validation unit report:
    n_total_windows
    n_pairwise_valid_windows
    valid_effective_area_m2
    Spearman rho
    weighted Pearson r

No p-values are computed or used.

FROZEN DIRECTION CLASSIFICATION
-------------------------------
The three WP03 candidate relationships are frozen as POSITIVE.

Minimum pairwise-valid windows = 10, inherited from WP03.

Unit classification:
    INSUFFICIENT_WINDOWS:
        n_pairwise_valid_windows < 10

    SIGN_REVERSAL:
        at least one defined coefficient is negative

    SAME_SIGN:
        both Spearman rho and weighted Pearson r are defined and positive

    UNDEFINED:
        otherwise, including zero coefficient or undefined coefficient
        after the minimum-window gate passes

This ordering intentionally makes any observed negative coefficient visible
as a sign reversal rather than hiding it behind another undefined metric.

NO RESULT-DEPENDENT FLEXIBILITY
-------------------------------
NO_CITY_REMOVED_AFTER_RESULTS
NO_SCALE_REMOVED_AFTER_RESULTS
NO_SELECTION_REMOVED_AFTER_RESULTS
NO_PAIR_REMOVED_AFTER_RESULTS
NO_METHOD_CHANGED_AFTER_RESULTS

FORMAL_CANU_GATES remain unchanged.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ============================================================
# 0. FIXED PATHS AND FROZEN SETTINGS
# ============================================================

ROOT = Path(r"C:\china_meld")

WP05A_DIR = (
    ROOT
    / "experiments"
    / "wp_morph05a_nonproduction"
    / "run_20260927_174448_460493"
)

OUTPUT_BASE = (
    ROOT
    / "experiments"
    / "wp_morph05b_nonproduction"
)

SOURCE_FILENAMES = [
    "validation_windows_1km.csv",
    "validation_windows_5km.csv",
    "aggregation_contract.json",
    "validation_aggregation_freeze.json",
    "manifest.json",
]

TARGET_CITY_COUNT = 3

EXPECTED_SCALES = [
    "1km",
    "5km",
]

EXPECTED_SELECTIONS = [
    "ALL",
    "COVERAGE_80",
]

COVERAGE_80_THRESHOLD = 0.80

MIN_PAIRWISE_VALID_WINDOWS = 10

EXPECTED_UNIT_COUNT = (
    TARGET_CITY_COUNT
    * len(EXPECTED_SCALES)
    * len(EXPECTED_SELECTIONS)
    * 3
)

ZERO_TOL = 1e-15

PAIR_DEFINITIONS = [
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


def parse_bool_series(
    series: pd.Series,
) -> pd.Series:
    if pd.api.types.is_bool_dtype(
        series
    ):
        return series.astype(bool)

    mapped = (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "1": True,
                "yes": True,
                "y": True,
                "t": True,
                "false": False,
                "0": False,
                "no": False,
                "n": False,
                "f": False,
            }
        )
    )

    require(
        mapped.notna().all(),
        (
            "coverage_80 contains values that "
            "cannot be parsed as boolean"
        ),
    )

    return mapped.astype(bool)


def finite_float(
    value: Any,
) -> float | None:
    try:
        x = float(value)
    except Exception:
        return None

    if not np.isfinite(x):
        return None

    return x


def coefficient_direction(
    value: float | None,
) -> str:
    if value is None:
        return "UNDEFINED"

    if not np.isfinite(value):
        return "UNDEFINED"

    if abs(value) <= ZERO_TOL:
        return "ZERO"

    if value > 0:
        return "POSITIVE"

    return "NEGATIVE"


# ============================================================
# 2. SOURCE PREFLIGHT
#    Reads only 05A contract/freeze/manifest before result CSVs
# ============================================================

def source_preflight() -> dict:
    print(
        "\n=== WP-MORPH-05B SOURCE PREFLIGHT ==="
    )

    source_paths = {
        name: (
            WP05A_DIR
            / name
        )
        for name
        in SOURCE_FILENAMES
    }

    for name, path in (
        source_paths.items()
    ):
        require(
            path.is_file(),
            (
                f"Missing frozen WP05A source: "
                f"{name}"
            ),
        )

    # These three metadata files are allowed to be read before
    # validation result values are opened.
    manifest = read_json(
        source_paths[
            "manifest.json"
        ]
    )

    contract = read_json(
        source_paths[
            "aggregation_contract.json"
        ]
    )

    freeze = read_json(
        source_paths[
            "validation_aggregation_freeze.json"
        ]
    )

    require(
        manifest.get(
            "work_package"
        )
        == "WP-MORPH-05A",
        (
            "Unexpected WP05A manifest identity"
        ),
    )

    require(
        manifest.get(
            "status"
        )
        == "NONPRODUCTION_VALIDATION_AGGREGATION",
        (
            "Unexpected WP05A manifest status"
        ),
    )

    require(
        manifest.get(
            "wp_morph05b_execution_authorized"
        )
        is True,
        (
            "WP05A manifest does not authorize "
            "WP-MORPH-05B execution"
        ),
    )

    require(
        manifest.get(
            "relationship_statistics_computed"
        )
        is False,
        (
            "WP05A unexpectedly reports "
            "relationship statistics already computed"
        ),
    )

    require(
        manifest.get(
            "correlations_computed"
        )
        is False,
        (
            "WP05A unexpectedly reports "
            "correlations already computed"
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
        contract.get(
            "contract_id"
        )
        == "WP-MORPH-05A-AGGREGATION-V1",
        (
            "Unexpected WP05A aggregation contract"
        ),
    )

    require(
        contract.get(
            "status"
        )
        == "FROZEN_BEFORE_RELATIONSHIP_ANALYSIS",
        (
            "WP05A aggregation contract "
            "is not frozen"
        ),
    )

    require(
        float(
            contract.get(
                "coverage_80_threshold"
            )
        )
        == COVERAGE_80_THRESHOLD,
        (
            "COVERAGE_80 threshold differs from frozen 0.80"
        ),
    )

    require(
        contract.get(
            "relationship_statistics_computed"
        )
        is False,
        (
            "Aggregation contract reports "
            "relationship statistics already computed"
        ),
    )

    require(
        contract.get(
            "correlations_computed"
        )
        is False,
        (
            "Aggregation contract reports "
            "correlations already computed"
        ),
    )

    require(
        freeze.get(
            "work_package"
        )
        == "WP-MORPH-05A",
        (
            "Unexpected aggregation freeze identity"
        ),
    )

    require(
        freeze.get(
            "status"
        )
        == "VALIDATION_AGGREGATION_FROZEN",
        (
            "WP05A validation aggregation "
            "is not frozen"
        ),
    )

    require(
        freeze.get(
            "wp_morph05b_execution_authorized"
        )
        is True,
        (
            "WP05A freeze does not authorize "
            "WP-MORPH-05B"
        ),
    )

    require(
        freeze.get(
            "relationship_statistics_computed"
        )
        is False,
        (
            "WP05A freeze reports relationship "
            "statistics already computed"
        ),
    )

    require(
        freeze.get(
            "correlations_computed"
        )
        is False,
        (
            "WP05A freeze reports correlations "
            "already computed"
        ),
    )

    authorized_city_ids = [
        str(x)
        for x
        in freeze.get(
            "authorized_city_ids",
            [],
        )
    ]

    require(
        len(
            authorized_city_ids
        )
        == TARGET_CITY_COUNT,
        (
            "WP05A freeze must contain "
            "exactly three authorized cities"
        ),
    )

    require(
        len(
            set(
                authorized_city_ids
            )
        )
        == TARGET_CITY_COUNT,
        (
            "Duplicate authorized city IDs "
            "in WP05A freeze"
        ),
    )

    manifest_city_ids = [
        str(x)
        for x
        in manifest.get(
            "authorized_city_ids",
            [],
        )
    ]

    require(
        manifest_city_ids
        == authorized_city_ids,
        (
            "WP05A manifest city IDs do not "
            "match aggregation freeze"
        ),
    )

    require(
        freeze.get(
            "spatial_scales"
        )
        == EXPECTED_SCALES,
        (
            "Frozen spatial scales differ from "
            "['1km', '5km']"
        ),
    )

    require(
        freeze.get(
            "selections"
        )
        == EXPECTED_SELECTIONS,
        (
            "Frozen selections differ from "
            "['ALL', 'COVERAGE_80']"
        ),
    )

    # Verify exact hashes of the four registered 05A outputs against
    # the 05A manifest. The manifest cannot register/hash itself,
    # so its own SHA-256 is frozen separately below.
    output_hashes = (
        manifest.get(
            "output_hashes",
            {},
        )
    )

    for filename in [
        "validation_windows_1km.csv",
        "validation_windows_5km.csv",
        "aggregation_contract.json",
        "validation_aggregation_freeze.json",
    ]:
        require(
            filename
            in output_hashes,
            (
                f"WP05A manifest does not register "
                f"{filename}"
            ),
        )

        actual = sha256_file(
            source_paths[
                filename
            ]
        )

        expected = str(
            output_hashes[
                filename
            ]
        ).upper()

        require(
            actual == expected,
            (
                f"WP05A source hash mismatch: "
                f"{filename}"
            ),
        )

    source_hashes = {
        name: sha256_file(
            path
        )
        for name, path
        in source_paths.items()
    }

    print(
        "WP05A_MANIFEST_SHA256:",
        source_hashes[
            "manifest.json"
        ],
    )

    print(
        "WP05A_AGGREGATION_CONTRACT_SHA256:",
        source_hashes[
            "aggregation_contract.json"
        ],
    )

    print(
        "WP05A_AGGREGATION_FREEZE_SHA256:",
        source_hashes[
            "validation_aggregation_freeze.json"
        ],
    )

    print(
        "AUTHORIZED_CITY_IDS:",
        authorized_city_ids,
    )

    print(
        "EXPECTED_VALIDATION_UNITS:",
        EXPECTED_UNIT_COUNT,
    )

    print(
        "P_VALUES_ALLOWED: NO"
    )

    print(
        "RAW_PARQUET_ACCESS_ALLOWED: NO"
    )

    print(
        "SOURCE_PREFLIGHT: PASS"
    )

    return {
        "source_paths": (
            source_paths
        ),
        "source_hashes": (
            source_hashes
        ),
        "manifest": (
            manifest
        ),
        "contract": (
            contract
        ),
        "freeze": (
            freeze
        ),
        "authorized_city_ids": (
            authorized_city_ids
        ),
    }


# ============================================================
# 3. METHOD FREEZE
#    Written BEFORE validation window values are read
# ============================================================

def build_method_contract(
    source: dict,
    script_sha256: str,
) -> dict:
    return {
        "work_package": (
            "WP-MORPH-05B"
        ),
        "contract_id": (
            "WP-MORPH-05B-METHOD-V1"
        ),
        "status": (
            "FROZEN_BEFORE_VALIDATION_RESULTS_OPENED"
        ),
        "freeze_timestamp_utc": (
            datetime.now(
                timezone.utc
            )
            .isoformat(
                timespec="seconds"
            )
        ),
        "script_sha256_before_results": (
            script_sha256
        ),
        "source_wp05a_hashes": (
            source[
                "source_hashes"
            ]
        ),
        "authorized_city_ids": (
            source[
                "authorized_city_ids"
            ]
        ),
        "scales": (
            EXPECTED_SCALES
        ),
        "selections": (
            EXPECTED_SELECTIONS
        ),
        "coverage_80_threshold": (
            COVERAGE_80_THRESHOLD
        ),
        "minimum_pairwise_valid_windows": (
            MIN_PAIRWISE_VALID_WINDOWS
        ),
        "expected_validation_unit_count": (
            EXPECTED_UNIT_COUNT
        ),
        "pairs": (
            PAIR_DEFINITIONS
        ),
        "statistics": {
            "spearman_rho": (
                "Pearson correlation of average ranks "
                "on pairwise-finite x/y windows; no p-value"
            ),
            "weighted_pearson_r": (
                "weighted covariance divided by weighted "
                "standard deviations using frozen pair weight"
            ),
        },
        "reported_per_unit": [
            "n_total_windows",
            "n_pairwise_valid_windows",
            "valid_effective_area_m2",
            "spearman_rho",
            "weighted_pearson_r",
        ],
        "classification_order": [
            "INSUFFICIENT_WINDOWS if n_pairwise_valid_windows < 10",
            "SIGN_REVERSAL if at least one defined coefficient < 0",
            "SAME_SIGN if both coefficients are defined and > 0",
            "UNDEFINED otherwise",
        ],
        "expected_sign": (
            "POSITIVE for all three frozen WP03 candidate relationships"
        ),
        "p_values_computed": False,
        "p_values_used_as_gate": False,
        "ordinary_independent_window_inference_claimed": False,
        "raw_parquet_access": False,
        "city_removal_after_results_allowed": False,
        "scale_removal_after_results_allowed": False,
        "selection_removal_after_results_allowed": False,
        "pair_removal_after_results_allowed": False,
        "method_change_after_results_allowed": False,
        "formal_canu_gates_changed": False,
    }


# ============================================================
# 4. RESULT FILE LOADING + STRUCTURAL QC
# ============================================================

def load_validation_windows(
    source: dict,
) -> tuple[
    dict[str, pd.DataFrame],
    dict[str, str],
]:
    tables = {}

    for scale_name, filename in [
        (
            "1km",
            "validation_windows_1km.csv",
        ),
        (
            "5km",
            "validation_windows_5km.csv",
        ),
    ]:
        path = (
            source[
                "source_paths"
            ][
                filename
            ]
        )

        table = pd.read_csv(
            path,
            encoding="utf-8-sig",
        )

        missing = (
            REQUIRED_WINDOW_COLUMNS
            - set(
                table.columns
            )
        )

        require(
            not missing,
            (
                f"{filename} missing columns: "
                f"{sorted(missing)}"
            ),
        )

        table[
            "city_id"
        ] = (
            table[
                "city_id"
            ]
            .astype(str)
        )

        table[
            "scale"
        ] = (
            table[
                "scale"
            ]
            .astype(str)
        )

        require(
            set(
                table[
                    "city_id"
                ].unique()
            )
            == set(
                source[
                    "authorized_city_ids"
                ]
            ),
            (
                f"{filename}: city set differs from "
                "frozen authorized cities"
            ),
        )

        require(
            set(
                table[
                    "scale"
                ].unique()
            )
            == {
                scale_name
            },
            (
                f"{filename}: unexpected scale values"
            ),
        )

        require(
            not table.duplicated(
                [
                    "city_id",
                    "window_row",
                    "window_col",
                ]
            ).any(),
            (
                f"{filename}: duplicate city/window keys"
            ),
        )

        table[
            "coverage_80"
        ] = (
            parse_bool_series(
                table[
                    "coverage_80"
                ]
            )
        )

        numeric_columns = [
            "effective_area_m2",
            "effective_area_fraction",
            "building_coverage_mean",
            "road_density_mean_km_per_km2",
            "height_valid_area_m2",
            "height_conditional_mean_m",
        ]

        for column in (
            numeric_columns
        ):
            table[
                column
            ] = pd.to_numeric(
                table[
                    column
                ],
                errors="coerce",
            )

        require(
            table[
                "effective_area_m2"
            ].notna().all(),
            (
                f"{filename}: missing effective_area_m2"
            ),
        )

        require(
            (
                table[
                    "effective_area_m2"
                ]
                >= 0
            ).all(),
            (
                f"{filename}: negative effective_area_m2"
            ),
        )

        require(
            table[
                "effective_area_fraction"
            ].notna().all(),
            (
                f"{filename}: missing effective_area_fraction"
            ),
        )

        derived_coverage80 = (
            table[
                "effective_area_fraction"
            ]
            >= COVERAGE_80_THRESHOLD
        )

        require(
            (
                derived_coverage80
                == table[
                    "coverage_80"
                ]
            ).all(),
            (
                f"{filename}: COVERAGE_80 flag differs "
                "from frozen 0.80 threshold"
            ),
        )

        tables[
            scale_name
        ] = (
            table
        )

    city_names = {}

    combined_names = pd.concat(
        [
            tables[
                "1km"
            ][
                [
                    "city_id",
                    "city_name",
                ]
            ],
            tables[
                "5km"
            ][
                [
                    "city_id",
                    "city_name",
                ]
            ],
        ],
        ignore_index=True,
    )

    for city_id in (
        source[
            "authorized_city_ids"
        ]
    ):
        names = (
            combined_names.loc[
                combined_names[
                    "city_id"
                ].eq(
                    city_id
                ),
                "city_name",
            ]
            .dropna()
            .astype(str)
            .str.strip()
        )

        names = [
            name
            for name
            in names.unique().tolist()
            if name
        ]

        require(
            len(names) == 1,
            (
                f"{city_id}: expected one frozen city name; "
                f"found {names}"
            ),
        )

        city_names[
            city_id
        ] = (
            names[
                0
            ]
        )

    return (
        tables,
        city_names,
    )


# ============================================================
# 5. CORRELATION FUNCTIONS
#    No hypothesis-test p-values
# ============================================================

def ordinary_pearson(
    x: np.ndarray,
    y: np.ndarray,
) -> float | None:
    if len(x) < 2:
        return None

    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    if (
        not np.isfinite(
            x
        ).all()
        or not np.isfinite(
            y
        ).all()
    ):
        return None

    x_center = (
        x
        - np.mean(
            x
        )
    )

    y_center = (
        y
        - np.mean(
            y
        )
    )

    denominator = float(
        np.sqrt(
            np.sum(
                x_center
                ** 2
            )
            * np.sum(
                y_center
                ** 2
            )
        )
    )

    if (
        not np.isfinite(
            denominator
        )
        or denominator
        <= ZERO_TOL
    ):
        return None

    numerator = float(
        np.sum(
            x_center
            * y_center
        )
    )

    result = (
        numerator
        / denominator
    )

    if not np.isfinite(
        result
    ):
        return None

    return float(
        np.clip(
            result,
            -1.0,
            1.0,
        )
    )


def spearman_rho(
    x: np.ndarray,
    y: np.ndarray,
) -> float | None:
    if len(x) < 2:
        return None

    x_rank = (
        pd.Series(
            x,
            dtype=float,
        )
        .rank(
            method="average"
        )
        .to_numpy(
            dtype=float
        )
    )

    y_rank = (
        pd.Series(
            y,
            dtype=float,
        )
        .rank(
            method="average"
        )
        .to_numpy(
            dtype=float
        )
    )

    return ordinary_pearson(
        x_rank,
        y_rank,
    )


def weighted_pearson_r(
    x: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
) -> float | None:
    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    w = np.asarray(
        w,
        dtype=float,
    )

    valid = (
        np.isfinite(
            x
        )
        & np.isfinite(
            y
        )
        & np.isfinite(
            w
        )
        & (
            w
            > 0
        )
    )

    x = (
        x[
            valid
        ]
    )

    y = (
        y[
            valid
        ]
    )

    w = (
        w[
            valid
        ]
    )

    if len(x) < 2:
        return None

    weight_sum = float(
        np.sum(
            w
        )
    )

    if (
        not np.isfinite(
            weight_sum
        )
        or weight_sum
        <= ZERO_TOL
    ):
        return None

    x_mean = float(
        np.sum(
            w
            * x
        )
        / weight_sum
    )

    y_mean = float(
        np.sum(
            w
            * y
        )
        / weight_sum
    )

    x_center = (
        x
        - x_mean
    )

    y_center = (
        y
        - y_mean
    )

    covariance = float(
        np.sum(
            w
            * x_center
            * y_center
        )
        / weight_sum
    )

    x_variance = float(
        np.sum(
            w
            * x_center
            * x_center
        )
        / weight_sum
    )

    y_variance = float(
        np.sum(
            w
            * y_center
            * y_center
        )
        / weight_sum
    )

    if (
        x_variance
        <= ZERO_TOL
        or y_variance
        <= ZERO_TOL
        or not np.isfinite(
            x_variance
        )
        or not np.isfinite(
            y_variance
        )
    ):
        return None

    denominator = float(
        np.sqrt(
            x_variance
            * y_variance
        )
    )

    if (
        denominator
        <= ZERO_TOL
        or not np.isfinite(
            denominator
        )
    ):
        return None

    result = (
        covariance
        / denominator
    )

    if not np.isfinite(
        result
    ):
        return None

    return float(
        np.clip(
            result,
            -1.0,
            1.0,
        )
    )


# ============================================================
# 6. DIRECTION CLASSIFICATION
# ============================================================

def classify_unit(
    n_pairwise_valid_windows: int,
    spearman_value: float | None,
    weighted_value: float | None,
) -> dict:
    spearman_direction = (
        coefficient_direction(
            spearman_value
        )
    )

    weighted_direction = (
        coefficient_direction(
            weighted_value
        )
    )

    if (
        n_pairwise_valid_windows
        < MIN_PAIRWISE_VALID_WINDOWS
    ):
        classification = (
            "INSUFFICIENT_WINDOWS"
        )

    elif (
        spearman_direction
        == "NEGATIVE"
        or weighted_direction
        == "NEGATIVE"
    ):
        classification = (
            "SIGN_REVERSAL"
        )

    elif (
        spearman_direction
        == "POSITIVE"
        and weighted_direction
        == "POSITIVE"
    ):
        classification = (
            "SAME_SIGN"
        )

    else:
        classification = (
            "UNDEFINED"
        )

    if (
        spearman_direction
        in {
            "POSITIVE",
            "NEGATIVE",
        }
        and weighted_direction
        in {
            "POSITIVE",
            "NEGATIVE",
        }
    ):
        coefficient_direction_agreement = (
            spearman_direction
            == weighted_direction
        )
    else:
        coefficient_direction_agreement = None

    return {
        "spearman_direction": (
            spearman_direction
        ),
        "weighted_pearson_direction": (
            weighted_direction
        ),
        "coefficient_direction_agreement": (
            coefficient_direction_agreement
        ),
        "classification": (
            classification
        ),
        "any_sign_reversal": (
            classification
            == "SIGN_REVERSAL"
        ),
    }


# ============================================================
# 7. COMPUTE THE 36 FROZEN VALIDATION UNITS
# ============================================================

def compute_validation_units(
    source: dict,
    tables: dict[str, pd.DataFrame],
    city_names: dict[str, str],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    correlation_rows = []
    direction_rows = []

    for city_id in (
        source[
            "authorized_city_ids"
        ]
    ):
        city_name = (
            city_names[
                city_id
            ]
        )

        for scale_name in (
            EXPECTED_SCALES
        ):
            city_table = (
                tables[
                    scale_name
                ]
                .loc[
                    tables[
                        scale_name
                    ][
                        "city_id"
                    ].eq(
                        city_id
                    )
                ]
                .copy()
            )

            require(
                not city_table.empty,
                (
                    f"{city_id} {scale_name}: "
                    "no frozen windows"
                ),
            )

            for selection in (
                EXPECTED_SELECTIONS
            ):
                if (
                    selection
                    == "ALL"
                ):
                    selected = (
                        city_table
                        .copy()
                    )

                elif (
                    selection
                    == "COVERAGE_80"
                ):
                    selected = (
                        city_table.loc[
                            city_table[
                                "coverage_80"
                            ]
                        ]
                        .copy()
                    )

                else:
                    raise RuntimeError(
                        f"Unexpected selection: {selection}"
                    )

                n_total_windows = int(
                    len(
                        selected
                    )
                )

                for pair in (
                    PAIR_DEFINITIONS
                ):
                    x_col = (
                        pair[
                            "x_variable"
                        ]
                    )

                    y_col = (
                        pair[
                            "y_variable"
                        ]
                    )

                    weight_col = (
                        pair[
                            "weight_variable"
                        ]
                    )

                    x = pd.to_numeric(
                        selected[
                            x_col
                        ],
                        errors="coerce",
                    )

                    y = pd.to_numeric(
                        selected[
                            y_col
                        ],
                        errors="coerce",
                    )

                    effective_area = pd.to_numeric(
                        selected[
                            "effective_area_m2"
                        ],
                        errors="coerce",
                    )

                    weights = pd.to_numeric(
                        selected[
                            weight_col
                        ],
                        errors="coerce",
                    )

                    pairwise_valid = (
                        np.isfinite(
                            x.to_numpy(
                                dtype=float
                            )
                        )
                        & np.isfinite(
                            y.to_numpy(
                                dtype=float
                            )
                        )
                    )

                    n_pairwise = int(
                        pairwise_valid.sum()
                    )

                    valid_effective_area_m2 = float(
                        effective_area.to_numpy(
                            dtype=float
                        )[
                            pairwise_valid
                        ].sum()
                    )

                    weighted_valid = (
                        pairwise_valid
                        & np.isfinite(
                            weights.to_numpy(
                                dtype=float
                            )
                        )
                        & (
                            weights.to_numpy(
                                dtype=float
                            )
                            > 0
                        )
                    )

                    n_weighted_valid = int(
                        weighted_valid.sum()
                    )

                    weight_sum_m2 = float(
                        weights.to_numpy(
                            dtype=float
                        )[
                            weighted_valid
                        ].sum()
                    )

                    if (
                        n_pairwise
                        >= MIN_PAIRWISE_VALID_WINDOWS
                    ):
                        rho = (
                            spearman_rho(
                                x.to_numpy(
                                    dtype=float
                                )[
                                    pairwise_valid
                                ],
                                y.to_numpy(
                                    dtype=float
                                )[
                                    pairwise_valid
                                ],
                            )
                        )

                        weighted_r = (
                            weighted_pearson_r(
                                x.to_numpy(
                                    dtype=float
                                )[
                                    pairwise_valid
                                ],
                                y.to_numpy(
                                    dtype=float
                                )[
                                    pairwise_valid
                                ],
                                weights.to_numpy(
                                    dtype=float
                                )[
                                    pairwise_valid
                                ],
                            )
                        )

                    else:
                        rho = None
                        weighted_r = None

                    direction = (
                        classify_unit(
                            n_pairwise,
                            rho,
                            weighted_r,
                        )
                    )

                    correlation_rows.append(
                        {
                            "city_id": (
                                city_id
                            ),
                            "city_name": (
                                city_name
                            ),
                            "scale": (
                                scale_name
                            ),
                            "selection": (
                                selection
                            ),
                            "pair_id": (
                                pair[
                                    "pair_id"
                                ]
                            ),
                            "x_variable": (
                                x_col
                            ),
                            "y_variable": (
                                y_col
                            ),
                            "expected_sign": (
                                pair[
                                    "expected_sign"
                                ]
                            ),
                            "weight_variable": (
                                weight_col
                            ),
                            "n_total_windows": (
                                n_total_windows
                            ),
                            "n_pairwise_valid_windows": (
                                n_pairwise
                            ),
                            "n_weighted_valid_windows": (
                                n_weighted_valid
                            ),
                            "valid_effective_area_m2": (
                                valid_effective_area_m2
                            ),
                            "weighted_pearson_weight_sum_m2": (
                                weight_sum_m2
                            ),
                            "spearman_rho": (
                                rho
                            ),
                            "weighted_pearson_r": (
                                weighted_r
                            ),
                            "p_value_computed": (
                                False
                            ),
                        }
                    )

                    direction_rows.append(
                        {
                            "city_id": (
                                city_id
                            ),
                            "city_name": (
                                city_name
                            ),
                            "scale": (
                                scale_name
                            ),
                            "selection": (
                                selection
                            ),
                            "pair_id": (
                                pair[
                                    "pair_id"
                                ]
                            ),
                            "expected_sign": (
                                pair[
                                    "expected_sign"
                                ]
                            ),
                            "n_total_windows": (
                                n_total_windows
                            ),
                            "n_pairwise_valid_windows": (
                                n_pairwise
                            ),
                            "spearman_rho": (
                                rho
                            ),
                            "weighted_pearson_r": (
                                weighted_r
                            ),
                            "spearman_direction": (
                                direction[
                                    "spearman_direction"
                                ]
                            ),
                            "weighted_pearson_direction": (
                                direction[
                                    "weighted_pearson_direction"
                                ]
                            ),
                            "coefficient_direction_agreement": (
                                direction[
                                    "coefficient_direction_agreement"
                                ]
                            ),
                            "classification": (
                                direction[
                                    "classification"
                                ]
                            ),
                            "any_sign_reversal": (
                                direction[
                                    "any_sign_reversal"
                                ]
                            ),
                        }
                    )

    correlations = pd.DataFrame(
        correlation_rows
    )

    directions = pd.DataFrame(
        direction_rows
    )

    require(
        len(
            correlations
        )
        == EXPECTED_UNIT_COUNT,
        (
            "Unexpected validation correlation unit count: "
            f"{len(correlations)} != {EXPECTED_UNIT_COUNT}"
        ),
    )

    require(
        len(
            directions
        )
        == EXPECTED_UNIT_COUNT,
        (
            "Unexpected direction-check unit count: "
            f"{len(directions)} != {EXPECTED_UNIT_COUNT}"
        ),
    )

    unit_keys = [
        "city_id",
        "scale",
        "selection",
        "pair_id",
    ]

    require(
        not correlations.duplicated(
            unit_keys
        ).any(),
        (
            "Duplicate frozen validation units "
            "in validation_correlations"
        ),
    )

    require(
        not directions.duplicated(
            unit_keys
        ).any(),
        (
            "Duplicate frozen validation units "
            "in validation_direction_checks"
        ),
    )

    return (
        correlations,
        directions,
    )


# ============================================================
# 8. SUMMARY TABLES
# ============================================================

def summarize_by_city(
    directions: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for (
        city_id,
        city_name,
        pair_id,
    ), group in (
        directions.groupby(
            [
                "city_id",
                "city_name",
                "pair_id",
            ],
            sort=True,
            dropna=False,
        )
    ):
        require(
            len(
                group
            )
            == 4,
            (
                f"{city_id} {pair_id}: "
                "expected four scale-selection units"
            ),
        )

        classification_counts = (
            group[
                "classification"
            ]
            .value_counts()
            .to_dict()
        )

        all_rows = (
            group.loc[
                group[
                    "selection"
                ].eq(
                    "ALL"
                )
            ]
        )

        coverage_rows = (
            group.loc[
                group[
                    "selection"
                ].eq(
                    "COVERAGE_80"
                )
            ]
        )

        require(
            set(
                all_rows[
                    "scale"
                ]
            )
            == set(
                EXPECTED_SCALES
            ),
            (
                f"{city_id} {pair_id}: "
                "ALL does not contain both scales"
            ),
        )

        require(
            set(
                coverage_rows[
                    "scale"
                ]
            )
            == set(
                EXPECTED_SCALES
            ),
            (
                f"{city_id} {pair_id}: "
                "COVERAGE_80 does not contain both scales"
            ),
        )

        rows.append(
            {
                "city_id": (
                    city_id
                ),
                "city_name": (
                    city_name
                ),
                "pair_id": (
                    pair_id
                ),
                "expected_sign": (
                    "POSITIVE"
                ),
                "units_total": (
                    4
                ),
                "same_sign_units": int(
                    classification_counts.get(
                        "SAME_SIGN",
                        0,
                    )
                ),
                "sign_reversal_units": int(
                    classification_counts.get(
                        "SIGN_REVERSAL",
                        0,
                    )
                ),
                "insufficient_windows_units": int(
                    classification_counts.get(
                        "INSUFFICIENT_WINDOWS",
                        0,
                    )
                ),
                "undefined_units": int(
                    classification_counts.get(
                        "UNDEFINED",
                        0,
                    )
                ),
                "all_four_units_same_sign": bool(
                    (
                        group[
                            "classification"
                        ]
                        == "SAME_SIGN"
                    ).all()
                ),
                "no_sign_reversal": bool(
                    not (
                        group[
                            "classification"
                        ]
                        == "SIGN_REVERSAL"
                    ).any()
                ),
                "all_selection_positive_at_both_scales": bool(
                    (
                        all_rows[
                            "classification"
                        ]
                        == "SAME_SIGN"
                    ).all()
                ),
                "coverage80_positive_at_both_scales": bool(
                    (
                        coverage_rows[
                            "classification"
                        ]
                        == "SAME_SIGN"
                    ).all()
                ),
                "spearman_weighted_direction_agreement_all_defined": bool(
                    group.loc[
                        group[
                            "coefficient_direction_agreement"
                        ].notna(),
                        "coefficient_direction_agreement",
                    ]
                    .astype(bool)
                    .all()
                )
                if (
                    group[
                        "coefficient_direction_agreement"
                    ].notna().any()
                )
                else False,
            }
        )

    summary = pd.DataFrame(
        rows
    )

    require(
        len(
            summary
        )
        == (
            TARGET_CITY_COUNT
            * len(
                PAIR_DEFINITIONS
            )
        ),
        (
            "Unexpected validation_summary_by_city row count"
        ),
    )

    return summary


def summarize_hypotheses(
    directions: pd.DataFrame,
    city_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for pair in (
        PAIR_DEFINITIONS
    ):
        pair_id = (
            pair[
                "pair_id"
            ]
        )

        group = (
            directions.loc[
                directions[
                    "pair_id"
                ].eq(
                    pair_id
                )
            ]
            .copy()
        )

        per_city = (
            city_summary.loc[
                city_summary[
                    "pair_id"
                ].eq(
                    pair_id
                )
            ]
            .copy()
        )

        require(
            len(
                group
            )
            == 12,
            (
                f"{pair_id}: expected 12 validation units"
            ),
        )

        require(
            len(
                per_city
            )
            == TARGET_CITY_COUNT,
            (
                f"{pair_id}: expected three city summaries"
            ),
        )

        counts = (
            group[
                "classification"
            ]
            .value_counts()
            .to_dict()
        )

        all_selection_group = (
            group.loc[
                group[
                    "selection"
                ].eq(
                    "ALL"
                )
            ]
        )

        coverage_group = (
            group.loc[
                group[
                    "selection"
                ].eq(
                    "COVERAGE_80"
                )
            ]
        )

        rows.append(
            {
                "pair_id": (
                    pair_id
                ),
                "x_variable": (
                    pair[
                        "x_variable"
                    ]
                ),
                "y_variable": (
                    pair[
                        "y_variable"
                    ]
                ),
                "expected_sign": (
                    pair[
                        "expected_sign"
                    ]
                ),
                "weight_variable": (
                    pair[
                        "weight_variable"
                    ]
                ),
                "validation_units_total": (
                    12
                ),
                "same_sign_units": int(
                    counts.get(
                        "SAME_SIGN",
                        0,
                    )
                ),
                "sign_reversal_units": int(
                    counts.get(
                        "SIGN_REVERSAL",
                        0,
                    )
                ),
                "insufficient_windows_units": int(
                    counts.get(
                        "INSUFFICIENT_WINDOWS",
                        0,
                    )
                ),
                "undefined_units": int(
                    counts.get(
                        "UNDEFINED",
                        0,
                    )
                ),
                "cities_all_four_units_same_sign": int(
                    per_city[
                        "all_four_units_same_sign"
                    ].sum()
                ),
                "cities_no_sign_reversal": int(
                    per_city[
                        "no_sign_reversal"
                    ].sum()
                ),
                "all_cities_all_selection_both_scales_same_sign": bool(
                    (
                        all_selection_group[
                            "classification"
                        ]
                        == "SAME_SIGN"
                    ).all()
                ),
                "all_cities_coverage80_both_scales_same_sign": bool(
                    (
                        coverage_group[
                            "classification"
                        ]
                        == "SAME_SIGN"
                    ).all()
                ),
                "all_12_units_same_sign": bool(
                    (
                        group[
                            "classification"
                        ]
                        == "SAME_SIGN"
                    ).all()
                ),
                "any_sign_reversal": bool(
                    (
                        group[
                            "classification"
                        ]
                        == "SIGN_REVERSAL"
                    ).any()
                ),
                "all_defined_coefficients_direction_agree": bool(
                    group.loc[
                        group[
                            "coefficient_direction_agreement"
                        ].notna(),
                        "coefficient_direction_agreement",
                    ]
                    .astype(bool)
                    .all()
                )
                if (
                    group[
                        "coefficient_direction_agreement"
                    ].notna().any()
                )
                else False,
            }
        )

    summary = pd.DataFrame(
        rows
    )

    require(
        len(
            summary
        )
        == len(
            PAIR_DEFINITIONS
        ),
        (
            "Unexpected validation_hypothesis_summary row count"
        ),
    )

    return summary


# ============================================================
# 9. MAIN
# ============================================================

def main() -> None:
    source = (
        source_preflight()
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

    script_path = Path(
        __file__
    ).resolve()

    script_sha_before = sha256_file(
        script_path
    )

    method_contract = (
        build_method_contract(
            source,
            script_sha_before,
        )
    )

    method_freeze_path = (
        output_dir
        / "method_freeze.json"
    )

    # CRITICAL ORDERING:
    # This freeze is written before validation window CSV values
    # are read into pandas.
    write_json(
        method_freeze_path,
        method_contract,
    )

    print(
        "\n=== WP-MORPH-05B METHOD FREEZE ==="
    )

    print(
        "METHOD_CONTRACT_ID:",
        method_contract[
            "contract_id"
        ],
    )

    print(
        "SCRIPT_SHA256_BEFORE_RESULTS:",
        script_sha_before,
    )

    print(
        "EXPECTED_VALIDATION_UNITS:",
        EXPECTED_UNIT_COUNT,
    )

    print(
        "MIN_PAIRWISE_VALID_WINDOWS:",
        MIN_PAIRWISE_VALID_WINDOWS,
    )

    print(
        "P_VALUES_COMPUTED: False"
    )

    print(
        "METHOD_FREEZE_WRITTEN_BEFORE_RESULT_CSV_READ: True"
    )

    print(
        "METHOD_FREEZE: PASS"
    )

    # ========================================================
    # FIRST OPENING OF FROZEN VALIDATION WINDOW VALUES
    # ========================================================

    tables, city_names = (
        load_validation_windows(
            source
        )
    )

    correlations, directions = (
        compute_validation_units(
            source,
            tables,
            city_names,
        )
    )

    city_summary = (
        summarize_by_city(
            directions
        )
    )

    hypothesis_summary = (
        summarize_hypotheses(
            directions,
            city_summary,
        )
    )

    # ========================================================
    # OUTPUTS
    # ========================================================

    correlations_path = (
        output_dir
        / "validation_correlations.csv"
    )

    directions_path = (
        output_dir
        / "validation_direction_checks.csv"
    )

    city_summary_path = (
        output_dir
        / "validation_summary_by_city.csv"
    )

    hypothesis_summary_path = (
        output_dir
        / "validation_hypothesis_summary.csv"
    )

    correlations.to_csv(
        correlations_path,
        index=False,
        encoding="utf-8-sig",
        float_format="%.12g",
    )

    directions.to_csv(
        directions_path,
        index=False,
        encoding="utf-8-sig",
        float_format="%.12g",
    )

    city_summary.to_csv(
        city_summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    hypothesis_summary.to_csv(
        hypothesis_summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    script_sha_after = sha256_file(
        script_path
    )

    require(
        script_sha_after
        == script_sha_before,
        (
            "Script SHA-256 changed after results were opened"
        ),
    )

    classification_counts = (
        directions[
            "classification"
        ]
        .value_counts()
        .to_dict()
    )

    qc_summary = {
        "work_package": (
            "WP-MORPH-05B"
        ),
        "status": (
            "VALIDATION_RELATIONSHIPS_COMPUTED_FROZEN_METHOD"
        ),
        "method_contract_id": (
            method_contract[
                "contract_id"
            ]
        ),
        "method_frozen_before_results_opened": (
            True
        ),
        "script_sha256_before_results": (
            script_sha_before
        ),
        "script_sha256_after_results": (
            script_sha_after
        ),
        "script_unchanged_during_analysis": (
            True
        ),
        "source_wp05a_hashes": (
            source[
                "source_hashes"
            ]
        ),
        "authorized_city_ids": (
            source[
                "authorized_city_ids"
            ]
        ),
        "validation_unit_count_expected": (
            EXPECTED_UNIT_COUNT
        ),
        "validation_unit_count_actual": int(
            len(
                correlations
            )
        ),
        "same_sign_units": int(
            classification_counts.get(
                "SAME_SIGN",
                0,
            )
        ),
        "sign_reversal_units": int(
            classification_counts.get(
                "SIGN_REVERSAL",
                0,
            )
        ),
        "insufficient_windows_units": int(
            classification_counts.get(
                "INSUFFICIENT_WINDOWS",
                0,
            )
        ),
        "undefined_units": int(
            classification_counts.get(
                "UNDEFINED",
                0,
            )
        ),
        "p_values_computed": (
            False
        ),
        "p_values_used_as_gate": (
            False
        ),
        "ordinary_independent_window_inference_claimed": (
            False
        ),
        "raw_parquet_files_read": (
            False
        ),
        "only_five_wp05a_sources_read": (
            True
        ),
        "NO_CITY_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_SCALE_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_SELECTION_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_PAIR_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_METHOD_CHANGED_AFTER_RESULTS": (
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
        method_freeze_path,
        correlations_path,
        directions_path,
        city_summary_path,
        hypothesis_summary_path,
        qc_summary_path,
    ]

    output_hashes = {
        path.name: sha256_file(
            path
        )
        for path
        in output_files
    }

    manifest = {
        "work_package": (
            "WP-MORPH-05B"
        ),
        "status": (
            "NONPRODUCTION_INDEPENDENT_VALIDATION_RELATIONSHIPS"
        ),
        "run_id": (
            run_id
        ),
        "source_wp05a_directory": (
            str(
                WP05A_DIR
            )
        ),
        "source_files_read": (
            SOURCE_FILENAMES
        ),
        "source_wp05a_hashes": (
            source[
                "source_hashes"
            ]
        ),
        "method_contract_id": (
            method_contract[
                "contract_id"
            ]
        ),
        "script_path": (
            str(
                script_path
            )
        ),
        "script_sha256_before_results": (
            script_sha_before
        ),
        "script_sha256_after_results": (
            script_sha_after
        ),
        "authorized_city_ids": (
            source[
                "authorized_city_ids"
            ]
        ),
        "expected_validation_units": (
            EXPECTED_UNIT_COUNT
        ),
        "actual_validation_units": int(
            len(
                correlations
            )
        ),
        "p_values_computed": (
            False
        ),
        "raw_parquet_files_read": (
            False
        ),
        "NO_CITY_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_SCALE_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_SELECTION_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_PAIR_REMOVED_AFTER_RESULTS": (
            True
        ),
        "NO_METHOD_CHANGED_AFTER_RESULTS": (
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

    # Console summary intentionally reports QC and classification counts,
    # but not the individual correlation coefficients. Detailed validation
    # values remain in frozen output tables.
    print(
        "\n=== WP-MORPH-05B FINAL QC SUMMARY ==="
    )

    print(
        "AUTHORIZED_CITY_IDS:",
        source[
            "authorized_city_ids"
        ],
    )

    print(
        "VALIDATION_UNIT_COUNT:",
        len(
            correlations
        ),
    )

    print(
        "EXPECTED_VALIDATION_UNIT_COUNT:",
        EXPECTED_UNIT_COUNT,
    )

    print(
        "SAME_SIGN_UNITS:",
        qc_summary[
            "same_sign_units"
        ],
    )

    print(
        "SIGN_REVERSAL_UNITS:",
        qc_summary[
            "sign_reversal_units"
        ],
    )

    print(
        "INSUFFICIENT_WINDOWS_UNITS:",
        qc_summary[
            "insufficient_windows_units"
        ],
    )

    print(
        "UNDEFINED_UNITS:",
        qc_summary[
            "undefined_units"
        ],
    )

    print(
        "P_VALUES_COMPUTED: False"
    )

    print(
        "RAW_PARQUET_FILES_READ: False"
    )

    print(
        "NO_CITY_REMOVED_AFTER_RESULTS: True"
    )

    print(
        "NO_SCALE_REMOVED_AFTER_RESULTS: True"
    )

    print(
        "NO_SELECTION_REMOVED_AFTER_RESULTS: True"
    )

    print(
        "NO_PAIR_REMOVED_AFTER_RESULTS: True"
    )

    print(
        "NO_METHOD_CHANGED_AFTER_RESULTS: True"
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
        "STATUS: "
        "VALIDATION_RELATIONSHIPS_COMPUTED_FROZEN_METHOD"
    )

    print(
        "OUTPUT:",
        output_dir,
    )

    print(
        "SCRIPT_SHA256:",
        script_sha_after,
    )


if __name__ == "__main__":
    main()
