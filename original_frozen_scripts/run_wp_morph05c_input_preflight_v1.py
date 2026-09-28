"""
WP-MORPH-05C INPUT REGISTRATION PREFLIGHT V1

PURPOSE
-------
Register the complete frozen result-level input bundle required by
WP-MORPH-05C-METHOD-V1 before any 05C analytical implementation.

THIS SCRIPT DOES NOT:
- read raw 50 m data
- read WP05A window tables
- recompute any correlation coefficient
- change any frozen analytical rule
- create any WP05C synthesis result
- authorize formal CANU production

It only:
1. verifies identity of the three already registered WP05B result files;
2. registers validation_direction_checks.csv;
3. discovers the unique WP03 result-level CSV by frozen schema/key coverage;
4. computes SHA256 and file sizes;
5. writes a provenance/input-registry package;
6. sets ANALYTICAL_EXECUTION_AUTHORIZED only if every input gate passes.

METHOD CONTRACT
---------------
METHOD_CONTRACT_ID = WP-MORPH-05C-METHOD-V1
Frozen contract SHA256 =
936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# ============================================================
# 0. FROZEN PATHS / IDENTIFIERS
# ============================================================

ROOT = Path(r"C:\china_meld")

WP03_DIR = (
    ROOT
    / "experiments"
    / "wp_morph03_nonproduction"
    / "run_20260925_091713_378174"
)

WP05B_DIR = (
    ROOT
    / "experiments"
    / "wp_morph05b_nonproduction"
    / "run_20260927_175641_020702"
)

OUTPUT_BASE = (
    ROOT
    / "experiments"
    / "wp_morph05c_nonproduction"
)

METHOD_CONTRACT_ID = "WP-MORPH-05C-METHOD-V1"
METHOD_CONTRACT_SHA256 = (
    "936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3"
)

WP03_SCRIPT_SHA256 = (
    "06160D33D307BE7698C97419A77A60B8DD5DF2C863AC106EC84E24CDBB3F728F"
)

WP05B_SCRIPT_SHA256 = (
    "78E955CCAAA819826C44CEE9E5971B32374DCC9C93559D927F13A1ED9B017A54"
)

EXPECTED_WP03_CITIES = {"P004", "P026", "P037"}
EXPECTED_WP05B_CITIES = {"P001", "P003", "P005"}
EXPECTED_SCALES = {"1km", "5km"}
EXPECTED_SELECTIONS = {"ALL", "COVERAGE_80"}

PAIR_VARIABLES = {
    (
        "building_coverage_mean",
        "road_density_mean_km_per_km2",
    ): "BUILDING_ROAD",
    (
        "building_coverage_mean",
        "height_conditional_mean_m",
    ): "BUILDING_HEIGHT",
    (
        "road_density_mean_km_per_km2",
        "height_conditional_mean_m",
    ): "ROAD_HEIGHT",
}

EXPECTED_WP03_UNITS = 36
EXPECTED_WP05B_UNITS = 36

# These three hashes were registered at the 05C method-freeze step.
REGISTERED_WP05B_FILES = {
    "validation_correlations.csv": {
        "sha256": "B0A2CCCB5B42DAEED12B51CDC129F681FC05946B3C42A11065E97CC10E35E75B",
        "size_bytes": 7380,
    },
    "validation_summary_by_city.csv": {
        "sha256": "2280D081A347AC1053872A2C167940E37DA4471E2B2D3326A7734FC53AD92B1F",
        "size_bytes": 948,
    },
    "validation_hypothesis_summary.csv": {
        "sha256": "9CB157A722913EBD88ED7D3103E38DBE704BCA816338613944C92D3ABCCEF7C5",
        "size_bytes": 809,
    },
}

DIRECTION_FILENAME = "validation_direction_checks.csv"

WP03_REQUIRED_COLUMNS = {
    "city_id",
    "scale",
    "selection",
    "variable_x",
    "variable_y",
    "spearman_rho",
    "weighted_pearson_r",
}

DIRECTION_REQUIRED_COLUMNS = {
    "city_id",
    "city_name",
    "scale",
    "selection",
    "pair_id",
    "expected_sign",
    "n_total_windows",
    "n_pairwise_valid_windows",
    "spearman_rho",
    "weighted_pearson_r",
    "spearman_direction",
    "weighted_pearson_direction",
    "coefficient_direction_agreement",
    "classification",
    "any_sign_reversal",
}


# ============================================================
# 1. HELPERS
# ============================================================

def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def file_record(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "file_name": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def read_csv_header(path: Path) -> list[str]:
    # Header only: no analytical result values are loaded.
    return list(pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns)


def normalize_strings(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def make_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out = OUTPUT_BASE / f"input_preflight_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    return out


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


# ============================================================
# 2. VERIFY THE THREE PRE-REGISTERED WP05B FILES
# ============================================================

def verify_registered_wp05b_files() -> list[dict[str, Any]]:
    records = []

    for name, expected in REGISTERED_WP05B_FILES.items():
        path = WP05B_DIR / name

        require(
            path.is_file(),
            f"Missing registered WP05B file: {path}",
        )

        actual_hash = sha256_file(path)
        actual_size = path.stat().st_size

        require(
            actual_hash == expected["sha256"],
            (
                f"SHA256 mismatch for {name}\n"
                f"expected={expected['sha256']}\n"
                f"actual={actual_hash}"
            ),
        )

        require(
            actual_size == expected["size_bytes"],
            (
                f"File-size mismatch for {name}: "
                f"{actual_size} != {expected['size_bytes']}"
            ),
        )

        rec = file_record(path, "WP05B_REGISTERED_RESULT")
        rec["identity_gate"] = "PASS"
        records.append(rec)

    return records


# ============================================================
# 3. REGISTER / QC validation_direction_checks.csv
# ============================================================

def register_direction_checks() -> dict[str, Any]:
    path = WP05B_DIR / DIRECTION_FILENAME

    require(
        path.is_file(),
        f"Missing required WP05B direction file: {path}",
    )

    header = set(read_csv_header(path))
    missing = sorted(DIRECTION_REQUIRED_COLUMNS - header)

    require(
        not missing,
        f"{DIRECTION_FILENAME} missing columns: {missing}",
    )

    # Read only fields needed for frozen-unit identity and inherited direction QC.
    usecols = [
        "city_id",
        "scale",
        "selection",
        "pair_id",
        "expected_sign",
        "classification",
    ]
    df = pd.read_csv(path, usecols=usecols, encoding="utf-8-sig")

    for c in usecols:
        df[c] = normalize_strings(df[c])

    require(
        len(df) == EXPECTED_WP05B_UNITS,
        (
            f"{DIRECTION_FILENAME} row count "
            f"{len(df)} != {EXPECTED_WP05B_UNITS}"
        ),
    )

    unit_keys = ["city_id", "scale", "selection", "pair_id"]

    require(
        not df.duplicated(unit_keys).any(),
        f"Duplicate validation units in {DIRECTION_FILENAME}",
    )

    require(
        set(df["city_id"]) == EXPECTED_WP05B_CITIES,
        (
            "Unexpected validation city universe: "
            f"{sorted(set(df['city_id']))}"
        ),
    )

    require(
        set(df["scale"]) == EXPECTED_SCALES,
        (
            "Unexpected validation scale universe: "
            f"{sorted(set(df['scale']))}"
        ),
    )

    require(
        set(df["selection"]) == EXPECTED_SELECTIONS,
        (
            "Unexpected validation selection universe: "
            f"{sorted(set(df['selection']))}"
        ),
    )

    require(
        set(df["pair_id"]) == set(PAIR_VARIABLES.values()),
        (
            "Unexpected validation relationship universe: "
            f"{sorted(set(df['pair_id']))}"
        ),
    )

    require(
        set(df["expected_sign"]) == {"POSITIVE"},
        "Expected-sign universe is not exactly POSITIVE",
    )

    # This does not create a new direction rule; it verifies the already frozen
    # direction-check file against the already recorded 05B outcome.
    require(
        set(df["classification"]) == {"SAME_SIGN"},
        (
            "Direction file is inconsistent with the frozen 05B outcome; "
            f"classifications={sorted(set(df['classification']))}"
        ),
    )

    rec = file_record(path, "WP05B_DIRECTION_CHECKS")
    rec.update(
        {
            "schema_gate": "PASS",
            "coverage_gate": "PASS",
            "row_count": int(len(df)),
            "cities": sorted(EXPECTED_WP05B_CITIES),
            "scales": sorted(EXPECTED_SCALES),
            "selections": sorted(EXPECTED_SELECTIONS),
            "relationships": sorted(PAIR_VARIABLES.values()),
            "classification_universe": ["SAME_SIGN"],
        }
    )
    return rec


# ============================================================
# 4. DISCOVER UNIQUE WP03 FROZEN RESULT TABLE
# ============================================================

def wp03_candidate_files() -> list[dict[str, Any]]:
    require(
        WP03_DIR.is_dir(),
        f"Missing frozen WP03 run directory: {WP03_DIR}",
    )

    candidates = []

    for path in sorted(WP03_DIR.glob("*.csv")):
        try:
            columns = set(read_csv_header(path))
        except Exception as exc:
            candidates.append(
                {
                    "file_name": path.name,
                    "path": str(path),
                    "candidate": False,
                    "reason": f"HEADER_READ_ERROR: {type(exc).__name__}: {exc}",
                }
            )
            continue

        if not WP03_REQUIRED_COLUMNS.issubset(columns):
            continue

        # Load only frozen unit-identity fields; do not load correlation values.
        identity_cols = [
            "city_id",
            "scale",
            "selection",
            "variable_x",
            "variable_y",
        ]

        try:
            df = pd.read_csv(
                path,
                usecols=identity_cols,
                encoding="utf-8-sig",
            )
        except Exception as exc:
            candidates.append(
                {
                    "file_name": path.name,
                    "path": str(path),
                    "candidate": False,
                    "reason": f"IDENTITY_READ_ERROR: {type(exc).__name__}: {exc}",
                }
            )
            continue

        for c in identity_cols:
            df[c] = normalize_strings(df[c])

        observed_pairs = set(
            zip(
                df["variable_x"],
                df["variable_y"],
            )
        )

        unit_key_cols = [
            "city_id",
            "scale",
            "selection",
            "variable_x",
            "variable_y",
        ]

        gates = {
            "row_count": len(df) == EXPECTED_WP03_UNITS,
            "unique_units": not df.duplicated(unit_key_cols).any(),
            "city_universe": set(df["city_id"]) == EXPECTED_WP03_CITIES,
            "scale_universe": set(df["scale"]) == EXPECTED_SCALES,
            "selection_universe": (
                set(df["selection"]) == EXPECTED_SELECTIONS
            ),
            "pair_universe": observed_pairs == set(PAIR_VARIABLES.keys()),
        }

        candidate = all(gates.values())

        candidates.append(
            {
                "file_name": path.name,
                "path": str(path),
                "candidate": candidate,
                "row_count": int(len(df)),
                "gates": gates,
            }
        )

    return candidates


def register_wp03_result() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scanned = wp03_candidate_files()
    valid = [x for x in scanned if x.get("candidate") is True]

    require(
        len(valid) == 1,
        (
            "WP03 result-table discovery must yield exactly one valid "
            f"candidate, but found {len(valid)}.\n"
            "Valid candidates: "
            f"{[x['file_name'] for x in valid]}"
        ),
    )

    path = Path(valid[0]["path"])

    rec = file_record(path, "WP03_FROZEN_PAIRWISE_RESULT")
    rec.update(
        {
            "schema_gate": "PASS",
            "coverage_gate": "PASS",
            "row_count": EXPECTED_WP03_UNITS,
            "cities": sorted(EXPECTED_WP03_CITIES),
            "scales": sorted(EXPECTED_SCALES),
            "selections": sorted(EXPECTED_SELECTIONS),
            "relationships": sorted(PAIR_VARIABLES.values()),
            "coefficient_columns_present_but_not_recomputed": [
                "spearman_rho",
                "weighted_pearson_r",
            ],
            "source_run": str(WP03_DIR),
            "source_script_sha256_recorded": WP03_SCRIPT_SHA256,
        }
    )

    return rec, scanned


# ============================================================
# 5. OPTIONAL INTERNAL IDENTITY CROSS-CHECK FOR WP05B
# ============================================================

def verify_wp05b_correlation_unit_keys() -> dict[str, Any]:
    path = WP05B_DIR / "validation_correlations.csv"

    header = set(read_csv_header(path))
    required = {"city_id", "scale", "selection", "pair_id"}
    require(
        required.issubset(header),
        (
            "validation_correlations.csv missing unit-key columns: "
            f"{sorted(required - header)}"
        ),
    )

    df = pd.read_csv(
        path,
        usecols=["city_id", "scale", "selection", "pair_id"],
        encoding="utf-8-sig",
    )

    for c in df.columns:
        df[c] = normalize_strings(df[c])

    require(
        len(df) == EXPECTED_WP05B_UNITS,
        "validation_correlations.csv unit count is not 36",
    )

    require(
        not df.duplicated(
            ["city_id", "scale", "selection", "pair_id"]
        ).any(),
        "Duplicate keys in validation_correlations.csv",
    )

    return {
        "validation_correlations_unit_identity_gate": "PASS",
        "row_count": int(len(df)),
    }


# ============================================================
# 6. MAIN
# ============================================================

def main() -> None:
    print("=== WP-MORPH-05C INPUT REGISTRATION PREFLIGHT V1 ===")
    print("METHOD_CONTRACT_ID:", METHOD_CONTRACT_ID)
    print("METHOD_CONTRACT_SHA256:", METHOD_CONTRACT_SHA256)
    print("WP03_RUN:", WP03_DIR)
    print("WP05B_RUN:", WP05B_DIR)
    print()

    output_dir = make_output_dir()

    status = {
        "work_package": "WP-MORPH-05C",
        "stage": "INPUT_REGISTRATION_PREFLIGHT_V1",
        "method_contract_id": METHOD_CONTRACT_ID,
        "method_contract_sha256": METHOD_CONTRACT_SHA256,
        "wp03_run": str(WP03_DIR),
        "wp05b_run": str(WP05B_DIR),
        "formal_canu_production_authorized": False,
        "formal_canu_gates": "UNCHANGED",
        "raw_50m_data_read": False,
        "wp05a_window_data_read": False,
        "coefficients_reestimated": False,
        "analytical_synthesis_computed": False,
        "analytical_execution_authorized": False,
    }

    try:
        registered_wp05b = verify_registered_wp05b_files()
        direction_record = register_direction_checks()
        correlation_key_qc = verify_wp05b_correlation_unit_keys()
        wp03_record, wp03_scan = register_wp03_result()

        registry = {
            **status,
            "input_registration_qc": "PASS",
            "registered_inputs": (
                registered_wp05b
                + [direction_record, wp03_record]
            ),
            "wp05b_internal_identity_qc": correlation_key_qc,
            "wp03_csv_scan": wp03_scan,
            "analytical_execution_authorized": True,
            "authorization_scope": (
                "WP-MORPH-05C synthesis implementation under "
                "WP-MORPH-05C-METHOD-V1 only"
            ),
            "authorization_does_not_allow": [
                "raw 50m reads",
                "WP05A window reads",
                "coefficient re-estimation",
                "method changes",
                "formal CANU production",
            ],
        }

        write_json(
            output_dir / "wp_morph05c_input_registry.json",
            registry,
        )

        text = [
            "WP-MORPH-05C INPUT REGISTRATION PREFLIGHT V1",
            "=============================================",
            f"OUTPUT_DIR: {output_dir}",
            f"METHOD_CONTRACT_ID: {METHOD_CONTRACT_ID}",
            f"METHOD_CONTRACT_SHA256: {METHOD_CONTRACT_SHA256}",
            "",
            "INPUT_REGISTRATION_QC: PASS",
            "ANALYTICAL_EXECUTION_AUTHORIZED: True",
            "AUTHORIZATION_SCOPE: WP-MORPH-05C synthesis implementation only",
            "FORMAL_CANU_PRODUCTION_AUTHORIZED: False",
            "FORMAL_CANU_GATES: UNCHANGED",
            "",
            "WP03 RESULT FILE:",
            f"  {wp03_record['path']}",
            f"  SHA256: {wp03_record['sha256']}",
            f"  SIZE_BYTES: {wp03_record['size_bytes']}",
            "",
            "WP05B DIRECTION FILE:",
            f"  {direction_record['path']}",
            f"  SHA256: {direction_record['sha256']}",
            f"  SIZE_BYTES: {direction_record['size_bytes']}",
            "",
            "NO ANALYTICAL SYNTHESIS WAS COMPUTED.",
            "NO CORRELATION COEFFICIENT WAS REESTIMATED.",
        ]

        (output_dir / "preflight_summary.txt").write_text(
            "\n".join(text) + "\n",
            encoding="utf-8",
        )

        print("\n".join(text))

    except Exception as exc:
        blocked = {
            **status,
            "input_registration_qc": "BLOCKED",
            "analytical_execution_authorized": False,
            "block_reason": f"{type(exc).__name__}: {exc}",
        }

        write_json(
            output_dir / "wp_morph05c_input_registry_BLOCKED.json",
            blocked,
        )

        msg = (
            "\nINPUT_REGISTRATION_QC: BLOCKED\n"
            "ANALYTICAL_EXECUTION_AUTHORIZED: False\n"
            f"BLOCK_REASON: {type(exc).__name__}: {exc}\n"
            "FORMAL_CANU_PRODUCTION_AUTHORIZED: False\n"
            "FORMAL_CANU_GATES: UNCHANGED\n"
        )

        (output_dir / "preflight_summary_BLOCKED.txt").write_text(
            msg,
            encoding="utf-8",
        )

        print(msg)
        raise


if __name__ == "__main__":
    main()
