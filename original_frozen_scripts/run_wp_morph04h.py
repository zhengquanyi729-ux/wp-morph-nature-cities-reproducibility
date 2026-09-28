"""
WP-MORPH-04H
Validation-city nomination and authorization.

Stages
------
A:
    Freeze the validation candidate pool using:
        - WP04 frozen protocol
        - WP04F frozen QC adjudication
        - WP04G verified canonical roster
        - WP04D frozen candidate identities

B:
    Apply the frozen ascending-P### selection rule and verify
    current Parquet row count + SHA256 until three candidates pass.

C:
    Re-verify the three nominated identities and, only if all
    source gates remain unchanged, create final authorization for:

        WP-MORPH-05 NONPRODUCTION independent validation

THIS SCRIPT DOES NOT
--------------------
- re-evaluate QC rules
- reconstruct QC evidence chains
- scan QC files
- search roster files
- inspect morphology values
- read building coverage
- read road density
- read building height
- calculate 1 km / 5 km morphology metrics
- calculate correlations
- alter formal CANU gates

Parquet access is limited to:
    - metadata row count
    - raw-file SHA256

Formal CANU production gates remain unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# 0. FIXED PATHS
# ============================================================

ROOT = Path(r"C:\china_meld")

WP04_DIR = (
    ROOT
    / "experiments"
    / "wp_morph04_nonproduction"
    / "run_20260925_093411_533467"
)

WP04D_DIR = (
    ROOT
    / "experiments"
    / "wp_morph04d_nonproduction"
    / "run_20260925_095750_110637"
)

WP04F_DIR = (
    ROOT
    / "experiments"
    / "wp_morph04f_nonproduction"
    / "run_20260927_125547_963054"
)

WP04G_DIR = (
    ROOT
    / "experiments"
    / "wp_morph04g_nonproduction"
    / "run_20260927_141545_387090"
)

OUTPUT_BASE = (
    ROOT
    / "experiments"
    / "wp_morph04h_nonproduction"
)

ACTIVE_POINTER = (
    OUTPUT_BASE
    / "active_run.json"
)

TARGET_CITY_COUNT = 3

EXPLORATION_CITIES = {
    "P004",
    "P026",
    "P037",
}

EXPECTED_ALL_CITY_IDS = {
    f"P{i:03d}"
    for i in range(1, 46)
}

EXPECTED_CANDIDATE_IDS = (
    EXPECTED_ALL_CITY_IDS
    - EXPLORATION_CITIES
)


# ============================================================
# 1. HELPERS
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

    return (
        digest
        .hexdigest()
        .upper()
    )


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
    if isinstance(
        value,
        bool,
    ):
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


def city_number(
    city_id: str,
) -> int:
    require(
        isinstance(
            city_id,
            str,
        )
        and len(city_id) == 4
        and city_id.startswith("P")
        and city_id[1:].isdigit(),
        f"Invalid city ID: {city_id}",
    )

    return int(
        city_id[1:]
    )


def manifest_path(
    run_dir: Path,
) -> Path:
    return (
        run_dir
        / "manifest.json"
    )


def load_manifest(
    run_dir: Path,
    expected_work_package: str,
) -> dict:
    path = (
        manifest_path(
            run_dir
        )
    )

    manifest = (
        read_json(
            path
        )
    )

    require(
        manifest.get(
            "work_package"
        )
        == expected_work_package,
        (
            f"{run_dir}: expected "
            f"{expected_work_package}, found "
            f"{manifest.get('work_package')}"
        ),
    )

    return manifest


def verify_registered_output(
    run_dir: Path,
    manifest: dict,
    filename: str,
) -> Path:
    hashes = (
        manifest.get(
            "output_hashes",
            {},
        )
    )

    require(
        filename
        in hashes,
        (
            f"{filename} is not registered "
            f"in {run_dir}/manifest.json"
        ),
    )

    path = (
        run_dir
        / filename
    )

    require(
        path.is_file(),
        f"Registered output missing: {path}",
    )

    actual = (
        sha256_file(
            path
        )
    )

    expected = str(
        hashes[
            filename
        ]
    ).upper()

    require(
        actual == expected,
        (
            "Registered output hash mismatch: "
            f"{path}"
        ),
    )

    return path


def verify_all_registered_outputs(
    run_dir: Path,
    manifest: dict,
) -> None:
    hashes = (
        manifest.get(
            "output_hashes",
            {},
        )
    )

    require(
        isinstance(
            hashes,
            dict,
        )
        and bool(
            hashes
        ),
        (
            f"No output hashes in "
            f"{run_dir}/manifest.json"
        ),
    )

    for relative_name, expected in (
        hashes.items()
    ):
        path = (
            run_dir
            / relative_name
        )

        require(
            path.is_file(),
            (
                "Registered source output "
                f"missing: {path}"
            ),
        )

        actual = (
            sha256_file(
                path
            )
        )

        require(
            actual
            == str(
                expected
            ).upper(),
            (
                "Registered source output "
                f"changed: {path}"
            ),
        )


def locate_registered_csv(
    run_dir: Path,
    manifest: dict,
    preferred_names: list[str],
    glob_pattern: str,
) -> Path:
    hashes = (
        manifest.get(
            "output_hashes",
            {},
        )
    )

    for name in (
        preferred_names
    ):
        if (
            name in hashes
            and (
                run_dir
                / name
            ).is_file()
        ):
            return (
                verify_registered_output(
                    run_dir,
                    manifest,
                    name,
                )
            )

    candidates = []

    for path in (
        run_dir.glob(
            glob_pattern
        )
    ):
        if (
            path.name
            in hashes
        ):
            verify_registered_output(
                run_dir,
                manifest,
                path.name,
            )

            candidates.append(
                path
            )

    require(
        len(candidates) == 1,
        (
            f"Unable to uniquely resolve "
            f"{glob_pattern} in {run_dir}; "
            f"found {len(candidates)}"
        ),
    )

    return candidates[0]


def create_active_run() -> Path:
    OUTPUT_BASE.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S_%f"
        )
    )

    run_dir = (
        OUTPUT_BASE
        / f"run_{run_id}"
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    write_json(
        ACTIVE_POINTER,
        {
            "run_dir": str(
                run_dir
            ),
            "created_at_utc": (
                datetime.now(
                    timezone.utc
                )
                .isoformat(
                    timespec="seconds"
                )
            ),
        },
    )

    return run_dir


def get_active_run() -> Path:
    pointer = (
        read_json(
            ACTIVE_POINTER
        )
    )

    run_dir = Path(
        pointer[
            "run_dir"
        ]
    )

    require(
        run_dir.is_dir(),
        (
            "Active WP04H run directory "
            f"does not exist: {run_dir}"
        ),
    )

    return run_dir


# ============================================================
# 2. VERIFY FROZEN UPSTREAM STATE
# ============================================================

def verify_upstream_sources() -> dict:
    print(
        "\n=== WP-MORPH-04H SOURCE PREFLIGHT ==="
    )

    wp04_manifest = (
        load_manifest(
            WP04_DIR,
            "WP-MORPH-04",
        )
    )

    wp04d_manifest = (
        load_manifest(
            WP04D_DIR,
            "WP-MORPH-04D",
        )
    )

    wp04f_manifest = (
        load_manifest(
            WP04F_DIR,
            "WP-MORPH-04F",
        )
    )

    wp04g_manifest = (
        load_manifest(
            WP04G_DIR,
            "WP-MORPH-04G",
        )
    )

    verify_all_registered_outputs(
        WP04_DIR,
        wp04_manifest,
    )

    verify_all_registered_outputs(
        WP04D_DIR,
        wp04d_manifest,
    )

    verify_all_registered_outputs(
        WP04F_DIR,
        wp04f_manifest,
    )

    verify_all_registered_outputs(
        WP04G_DIR,
        wp04g_manifest,
    )

    protocol_path = (
        verify_registered_output(
            WP04_DIR,
            wp04_manifest,
            "validation_protocol_v1.json",
        )
    )

    protocol = (
        read_json(
            protocol_path
        )
    )

    require(
        protocol.get(
            "protocol_id"
        )
        == "WP-MORPH-04-VALIDATION-V1",
        (
            "Unexpected frozen "
            "validation protocol"
        ),
    )

    require(
        protocol.get(
            "validation_execution_authorized"
        )
        is False,
        (
            "Original WP04 protocol should "
            "not already authorize execution"
        ),
    )

    target_count = int(
        protocol[
            "validation_target"
        ][
            "target_city_count"
        ]
    )

    require(
        target_count
        == TARGET_CITY_COUNT,
        (
            "Frozen target city count "
            f"is {target_count}, not 3"
        ),
    )

    selection_rule = str(
        protocol[
            "validation_target"
        ][
            "selection_rule"
        ]
    )

    require(
        "ascending"
        in selection_rule.lower(),
        (
            "Frozen validation protocol "
            "does not contain ascending-ID rule"
        ),
    )

    wp04f_qc_path = (
        verify_registered_output(
            WP04F_DIR,
            wp04f_manifest,
            "qc_summary.json",
        )
    )

    wp04f_qc = (
        read_json(
            wp04f_qc_path
        )
    )

    require(
        int(
            wp04f_qc.get(
                "strong_qc_pass_cities",
                -1,
            )
        )
        == 42,
        (
            "Frozen WP04F strong-QC count "
            "is no longer 42"
        ),
    )

    require(
        int(
            wp04f_qc.get(
                "strong_negative_cities",
                -1,
            )
        )
        == 1,
        (
            "Frozen WP04F strong-negative "
            "count is no longer 1"
        ),
    )

    require(
        wp04f_qc.get(
            "validation_execution_authorized"
        )
        is False,
        (
            "WP04F unexpectedly authorized "
            "validation"
        ),
    )

    wp04g_qc_path = (
        verify_registered_output(
            WP04G_DIR,
            wp04g_manifest,
            "qc_summary.json",
        )
    )

    wp04g_qc = (
        read_json(
            wp04g_qc_path
        )
    )

    require(
        wp04g_qc.get(
            "canonical_roster"
        )
        == "VERIFIED",
        (
            "WP04G canonical roster "
            "is not VERIFIED"
        ),
    )

    canonical_group = (
        wp04g_qc.get(
            "canonical_fingerprint_group"
        )
    )

    require(
        isinstance(
            canonical_group,
            str,
        )
        and canonical_group,
        (
            "WP04G canonical fingerprint "
            "group missing"
        ),
    )

    require(
        wp04g_qc.get(
            "qc_rules_reevaluated"
        )
        is False,
        (
            "WP04G unexpectedly reports "
            "QC-rule reevaluation"
        ),
    )

    require(
        wp04g_qc.get(
            "validation_execution_authorized"
        )
        is False,
        (
            "WP04G unexpectedly authorized "
            "validation"
        ),
    )

    identity_path = (
        locate_registered_csv(
            WP04D_DIR,
            wp04d_manifest,
            [
                "candidate_file_identity.csv",
            ],
            "candidate_file_identity*.csv",
        )
    )

    eligibility_path = (
        locate_registered_csv(
            WP04F_DIR,
            wp04f_manifest,
            [
                "candidate_eligibility_v2.csv",
                "candidate_eligibility.csv",
            ],
            "candidate_eligibility*.csv",
        )
    )

    roster_path = (
        verify_registered_output(
            WP04G_DIR,
            wp04g_manifest,
            "canonical_city_roster.csv",
        )
    )

    source_hashes = {
        "wp04_manifest_sha256": (
            sha256_file(
                WP04_DIR
                / "manifest.json"
            )
        ),
        "wp04d_manifest_sha256": (
            sha256_file(
                WP04D_DIR
                / "manifest.json"
            )
        ),
        "wp04f_manifest_sha256": (
            sha256_file(
                WP04F_DIR
                / "manifest.json"
            )
        ),
        "wp04g_manifest_sha256": (
            sha256_file(
                WP04G_DIR
                / "manifest.json"
            )
        ),
        "validation_protocol_sha256": (
            sha256_file(
                protocol_path
            )
        ),
    }

    print(
        "WP04_MANIFEST_SHA256:",
        source_hashes[
            "wp04_manifest_sha256"
        ],
    )

    print(
        "WP04D_MANIFEST_SHA256:",
        source_hashes[
            "wp04d_manifest_sha256"
        ],
    )

    print(
        "WP04F_MANIFEST_SHA256:",
        source_hashes[
            "wp04f_manifest_sha256"
        ],
    )

    print(
        "WP04G_MANIFEST_SHA256:",
        source_hashes[
            "wp04g_manifest_sha256"
        ],
    )

    print(
        "CANONICAL_ROSTER: VERIFIED"
    )

    print(
        "CANONICAL_FINGERPRINT_GROUP:",
        canonical_group,
    )

    print(
        "FROZEN_STRONG_QC_PASS_CITIES: 42"
    )

    print(
        "FROZEN_STRONG_NEGATIVE_CITIES: 1"
    )

    print(
        "TARGET_CITY_COUNT:",
        target_count,
    )

    print(
        "SOURCE_PREFLIGHT: PASS"
    )

    return {
        "protocol": (
            protocol
        ),
        "source_hashes": (
            source_hashes
        ),
        "canonical_group": (
            canonical_group
        ),
        "canonical_fingerprint": (
            wp04g_qc.get(
                "canonical_mapping_fingerprint"
            )
        ),
        "identity_path": (
            identity_path
        ),
        "eligibility_path": (
            eligibility_path
        ),
        "roster_path": (
            roster_path
        ),
    }


# ============================================================
# 3. STAGE A
#    Freeze clean validation candidate pool
# ============================================================

def run_stage_a() -> None:
    source = (
        verify_upstream_sources()
    )

    identity = pd.read_csv(
        source[
            "identity_path"
        ],
        encoding="utf-8-sig",
    )

    qc_status = pd.read_csv(
        source[
            "eligibility_path"
        ],
        encoding="utf-8-sig",
    )

    roster = pd.read_csv(
        source[
            "roster_path"
        ],
        encoding="utf-8-sig",
    )

    identity_required = {
        "city_id",
        "grid_path",
        "parquet_rows",
        "sha256",
        "metadata_check",
    }

    missing = (
        identity_required
        - set(
            identity.columns
        )
    )

    require(
        not missing,
        (
            "WP04D identity table missing: "
            f"{sorted(missing)}"
        ),
    )

    identity[
        "city_id"
    ] = (
        identity[
            "city_id"
        ]
        .astype(str)
    )

    require(
        set(
            identity[
                "city_id"
            ]
        )
        == EXPECTED_CANDIDATE_IDS,
        (
            "WP04D candidate identities "
            "are not the expected 42 cities"
        ),
    )

    require(
        identity[
            "city_id"
        ].is_unique,
        "Duplicate WP04D candidate identity",
    )

    qc_required = {
        "city_id",
        "strong_qc_pass_chains",
        "strong_negative_chains",
    }

    missing = (
        qc_required
        - set(
            qc_status.columns
        )
    )

    require(
        not missing,
        (
            "WP04F eligibility table missing: "
            f"{sorted(missing)}"
        ),
    )

    qc_status[
        "city_id"
    ] = (
        qc_status[
            "city_id"
        ]
        .astype(str)
    )

    require(
        set(
            qc_status[
                "city_id"
            ]
        )
        == EXPECTED_CANDIDATE_IDS,
        (
            "WP04F QC city set does "
            "not match 42 candidates"
        ),
    )

    roster_required = {
        "city_id",
        "city_name",
        "canonical_roster_verified",
        "canonical_fingerprint_group",
        "canonical_mapping_fingerprint",
    }

    missing = (
        roster_required
        - set(
            roster.columns
        )
    )

    require(
        not missing,
        (
            "WP04G canonical roster missing: "
            f"{sorted(missing)}"
        ),
    )

    roster[
        "city_id"
    ] = (
        roster[
            "city_id"
        ]
        .astype(str)
    )

    require(
        set(
            roster[
                "city_id"
            ]
        )
        == EXPECTED_ALL_CITY_IDS,
        (
            "WP04G canonical roster does "
            "not contain exactly P001-P045"
        ),
    )

    require(
        roster[
            "canonical_roster_verified"
        ].apply(
            parse_bool
        ).all(),
        (
            "Not all WP04G roster rows "
            "are marked verified"
        ),
    )

    roster_groups = {
        str(value)
        for value
        in roster[
            "canonical_fingerprint_group"
        ].dropna()
        if str(value).strip()
    }

    require(
        roster_groups
        == {
            source[
                "canonical_group"
            ]
        },
        (
            "Canonical roster group differs "
            "from WP04G QC summary"
        ),
    )

    pool = (
        identity.merge(
            qc_status[
                [
                    "city_id",
                    "strong_qc_pass_chains",
                    "strong_negative_chains",
                ]
            ],
            on="city_id",
            how="inner",
            validate="one_to_one",
        )
        .merge(
            roster[
                [
                    "city_id",
                    "city_name",
                    "canonical_fingerprint_group",
                    "canonical_mapping_fingerprint",
                ]
            ],
            on="city_id",
            how="left",
            validate="one_to_one",
        )
    )

    require(
        len(pool) == 42,
        (
            "Merged candidate pool "
            f"contains {len(pool)} rows, not 42"
        ),
    )

    pool[
        "metadata_pass"
    ] = (
        pool[
            "metadata_check"
        ]
        .astype(str)
        .str.upper()
        .eq(
            "PASS"
        )
    )

    pool[
        "frozen_qc_pass"
    ] = (
        pd.to_numeric(
            pool[
                "strong_qc_pass_chains"
            ],
            errors="raise",
        )
        > 0
    )

    pool[
        "frozen_negative_present"
    ] = (
        pd.to_numeric(
            pool[
                "strong_negative_chains"
            ],
            errors="raise",
        )
        > 0
    )

    pool[
        "canonical_city_mapped"
    ] = (
        pool[
            "city_name"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )

    pool[
        "eligible_pre_identity"
    ] = (
        pool[
            "metadata_pass"
        ]
        & pool[
            "frozen_qc_pass"
        ]
        & ~pool[
            "frozen_negative_present"
        ]
        & pool[
            "canonical_city_mapped"
        ]
    )

    pool[
        "city_sort"
    ] = (
        pool[
            "city_id"
        ].map(
            city_number
        )
    )

    pool = (
        pool.sort_values(
            "city_sort"
        )
        .drop(
            columns=[
                "city_sort",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    strong_pass_count = int(
        pool[
            "frozen_qc_pass"
        ].sum()
    )

    negative_count = int(
        pool[
            "frozen_negative_present"
        ].sum()
    )

    clean_count = int(
        pool[
            "eligible_pre_identity"
        ].sum()
    )

    require(
        strong_pass_count == 42,
        (
            "Frozen strong-pass city count "
            f"is {strong_pass_count}, expected 42"
        ),
    )

    require(
        negative_count == 1,
        (
            "Frozen negative city count "
            f"is {negative_count}, expected 1"
        ),
    )

    require(
        clean_count == 41,
        (
            "Expected 41 clean candidates "
            f"before identity check; found {clean_count}"
        ),
    )

    negative_ids = (
        pool.loc[
            pool[
                "frozen_negative_present"
            ],
            "city_id",
        ]
        .tolist()
    )

    run_dir = (
        create_active_run()
    )

    pool_path = (
        run_dir
        / "frozen_candidate_pool.csv"
    )

    pool.to_csv(
        pool_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "work_package": (
            "WP-MORPH-04H-A"
        ),
        "status": (
            "CANDIDATE_POOL_FROZEN"
        ),
        "canonical_roster": (
            "VERIFIED"
        ),
        "canonical_fingerprint_group": (
            source[
                "canonical_group"
            ]
        ),
        "canonical_mapping_fingerprint": (
            source[
                "canonical_fingerprint"
            ]
        ),
        "frozen_strong_qc_pass_cities": (
            strong_pass_count
        ),
        "frozen_negative_cities": (
            negative_count
        ),
        "frozen_negative_city_ids": (
            negative_ids
        ),
        "clean_candidates_pre_identity": (
            clean_count
        ),
        "target_city_count": (
            TARGET_CITY_COUNT
        ),
        "selection_rule": (
            source[
                "protocol"
            ][
                "validation_target"
            ][
                "selection_rule"
            ]
        ),
        "qc_rules_reevaluated": False,
        "roster_rules_reevaluated": False,
        "candidate_morphology_results_inspected": False,
        "validation_authorized": False,
        "source_hashes": (
            source[
                "source_hashes"
            ]
        ),
    }

    summary_path = (
        run_dir
        / "stage_a_summary.json"
    )

    write_json(
        summary_path,
        summary,
    )

    stage_manifest = {
        "work_package": (
            "WP-MORPH-04H-A"
        ),
        "status": (
            "CANDIDATE_POOL_FROZEN"
        ),
        "run_directory": str(
            run_dir
        ),
        "output_hashes": {
            "frozen_candidate_pool.csv": (
                sha256_file(
                    pool_path
                )
            ),
            "stage_a_summary.json": (
                sha256_file(
                    summary_path
                )
            ),
        },
        "script_sha256_at_stage_a": (
            sha256_file(
                Path(__file__).resolve()
            )
        ),
    }

    write_json(
        run_dir
        / "stage_a_manifest.json",
        stage_manifest,
    )

    print(
        "\n=== WP-MORPH-04H STAGE A ==="
    )

    print(
        "CANONICAL_ROSTER: VERIFIED"
    )

    print(
        "FROZEN_STRONG_QC_PASS_CITIES:",
        strong_pass_count,
    )

    print(
        "FROZEN_NEGATIVE_CITIES:",
        negative_count,
    )

    print(
        "FROZEN_NEGATIVE_CITY_IDS:",
        negative_ids,
    )

    print(
        "CLEAN_CANDIDATES_PRE_IDENTITY:",
        clean_count,
    )

    print(
        "TARGET_CITY_COUNT:",
        TARGET_CITY_COUNT,
    )

    print(
        "CANDIDATE_MORPHOLOGY_RESULTS_INSPECTED: NO"
    )

    print(
        "VALIDATION_AUTHORIZED: False"
    )

    print(
        "STAGE_A_OUTPUT:",
        run_dir,
    )

    print(
        "\nSTAGE A COMPLETE"
    )


# ============================================================
# 4. VERIFY STAGE-A OUTPUT
# ============================================================

def verify_stage_a(
    run_dir: Path,
) -> tuple[
    pd.DataFrame,
    dict,
]:
    manifest_path = (
        run_dir
        / "stage_a_manifest.json"
    )

    manifest = (
        read_json(
            manifest_path
        )
    )

    require(
        manifest.get(
            "work_package"
        )
        == "WP-MORPH-04H-A",
        "Invalid Stage-A manifest",
    )

    outputs = (
        manifest[
            "output_hashes"
        ]
    )

    for filename, expected in (
        outputs.items()
    ):
        path = (
            run_dir
            / filename
        )

        require(
            path.is_file(),
            (
                f"Stage-A output missing: "
                f"{path}"
            ),
        )

        require(
            sha256_file(
                path
            )
            == str(
                expected
            ).upper(),
            (
                f"Stage-A output changed: "
                f"{path}"
            ),
        )

    pool = pd.read_csv(
        run_dir
        / "frozen_candidate_pool.csv",
        encoding="utf-8-sig",
    )

    summary = (
        read_json(
            run_dir
            / "stage_a_summary.json"
        )
    )

    require(
        int(
            pool[
                "eligible_pre_identity"
            ].apply(
                parse_bool
            ).sum()
        )
        == 41,
        (
            "Stage-A frozen clean "
            "candidate count changed"
        ),
    )

    return (
        pool,
        summary,
    )


# ============================================================
# 5. STAGE B
#    Current identity verification and provisional nomination
# ============================================================

def run_stage_b() -> None:
    run_dir = (
        get_active_run()
    )

    pool, stage_a = (
        verify_stage_a(
            run_dir
        )
    )

    current_source = (
        verify_upstream_sources()
    )

    require(
        current_source[
            "source_hashes"
        ]
        == stage_a[
            "source_hashes"
        ],
        (
            "Upstream source hashes changed "
            "after Stage A"
        ),
    )

    clean = (
        pool.loc[
            pool[
                "eligible_pre_identity"
            ].apply(
                parse_bool
            )
        ]
        .copy()
    )

    clean[
        "city_sort"
    ] = (
        clean[
            "city_id"
        ].map(
            city_number
        )
    )

    clean = (
        clean.sort_values(
            "city_sort"
        )
        .drop(
            columns=[
                "city_sort",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    checks = []
    provisional = []

    print(
        "\n=== WP-MORPH-04H STAGE B ==="
    )

    print(
        "Applying frozen ascending-P### rule..."
    )

    for check_order, row in (
        clean.iterrows()
    ):
        city_id = str(
            row[
                "city_id"
            ]
        )

        path = Path(
            str(
                row[
                    "grid_path"
                ]
            )
        )

        expected_rows = int(
            row[
                "parquet_rows"
            ]
        )

        expected_sha = str(
            row[
                "sha256"
            ]
        ).upper()

        print(
            f"{city_id}: "
            "CURRENT_IDENTITY_CHECK...",
            flush=True,
        )

        exists = (
            path.is_file()
        )

        current_rows = None
        current_sha = ""
        row_match = False
        sha_match = False
        metadata_read_pass = False

        if exists:
            try:
                parquet = (
                    pq.ParquetFile(
                        path
                    )
                )

                current_rows = int(
                    parquet.metadata.num_rows
                )

                parquet.close()

                metadata_read_pass = True

                row_match = (
                    current_rows
                    == expected_rows
                )

            except Exception:
                metadata_read_pass = False

        if (
            exists
            and metadata_read_pass
            and row_match
        ):
            current_sha = (
                sha256_file(
                    path
                )
            )

            sha_match = (
                current_sha
                == expected_sha
            )

        identity_match = bool(
            exists
            and metadata_read_pass
            and row_match
            and sha_match
        )

        checks.append(
            {
                "check_order": (
                    check_order + 1
                ),
                "city_id": (
                    city_id
                ),
                "city_name": str(
                    row[
                        "city_name"
                    ]
                ),
                "grid_path": str(
                    path
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
                "file_exists": (
                    exists
                ),
                "metadata_read_pass": (
                    metadata_read_pass
                ),
                "row_count_match": (
                    row_match
                ),
                "sha256_match": (
                    sha_match
                ),
                "identity_match": (
                    identity_match
                ),
            }
        )

        if identity_match:
            print(
                f"{city_id}: IDENTITY_PASS"
            )

            provisional.append(
                {
                    "city_id": (
                        city_id
                    ),
                    "city_name": str(
                        row[
                            "city_name"
                        ]
                    ),
                    "grid_path": str(
                        path.resolve()
                    ),
                    "parquet_rows": (
                        current_rows
                    ),
                    "sha256": (
                        current_sha
                    ),
                }
            )

        else:
            print(
                f"{city_id}: IDENTITY_HOLD"
            )

        if (
            len(
                provisional
            )
            == TARGET_CITY_COUNT
        ):
            break

    checks_df = (
        pd.DataFrame(
            checks
        )
    )

    checks_path = (
        run_dir
        / "current_identity_check.csv"
    )

    checks_df.to_csv(
        checks_path,
        index=False,
        encoding="utf-8-sig",
    )

    enough = (
        len(
            provisional
        )
        == TARGET_CITY_COUNT
    )

    provisional_path = (
        run_dir
        / "provisional_nomination.json"
    )

    if enough:
        write_json(
            provisional_path,
            {
                "work_package": (
                    "WP-MORPH-04H-B"
                ),
                "status": (
                    "PROVISIONAL_NOMINATION_READY"
                ),
                "target_city_count": (
                    TARGET_CITY_COUNT
                ),
                "selected_cities": (
                    provisional
                ),
                "selection_rule": (
                    stage_a[
                        "selection_rule"
                    ]
                ),
                "selection_based_on_morphology_results": False,
                "candidate_morphology_results_inspected": False,
                "validation_execution_authorized": False,
            },
        )

    summary = {
        "work_package": (
            "WP-MORPH-04H-B"
        ),
        "status": (
            "PROVISIONAL_NOMINATION_READY"
            if enough
            else "HOLD_INSUFFICIENT_CURRENT_IDENTITIES"
        ),
        "identity_checks_performed": (
            len(
                checks_df
            )
        ),
        "identity_pass_count": int(
            checks_df[
                "identity_match"
            ].sum()
        ),
        "provisional_nominee_count": (
            len(
                provisional
            )
        ),
        "provisional_nominee_ids": [
            row[
                "city_id"
            ]
            for row
            in provisional
        ],
        "candidate_morphology_results_inspected": False,
        "qc_rules_reevaluated": False,
        "roster_rules_reevaluated": False,
        "validation_execution_authorized": False,
    }

    summary_path = (
        run_dir
        / "stage_b_summary.json"
    )

    write_json(
        summary_path,
        summary,
    )

    output_hashes = {
        "current_identity_check.csv": (
            sha256_file(
                checks_path
            )
        ),
        "stage_b_summary.json": (
            sha256_file(
                summary_path
            )
        ),
    }

    if enough:
        output_hashes[
            "provisional_nomination.json"
        ] = (
            sha256_file(
                provisional_path
            )
        )

    stage_b_manifest = {
        "work_package": (
            "WP-MORPH-04H-B"
        ),
        "status": (
            summary[
                "status"
            ]
        ),
        "output_hashes": (
            output_hashes
        ),
        "script_sha256_at_stage_b": (
            sha256_file(
                Path(__file__).resolve()
            )
        ),
    }

    write_json(
        run_dir
        / "stage_b_manifest.json",
        stage_b_manifest,
    )

    print(
        "\nIDENTITY_CHECKS_PERFORMED:",
        len(
            checks_df
        ),
    )

    print(
        "IDENTITY_PASS_COUNT:",
        int(
            checks_df[
                "identity_match"
            ].sum()
        ),
    )

    print(
        "PROVISIONAL_NOMINEE_COUNT:",
        len(
            provisional
        ),
    )

    print(
        "PROVISIONAL_NOMINEE_IDS:",
        [
            row[
                "city_id"
            ]
            for row
            in provisional
        ],
    )

    print(
        "VALIDATION_EXECUTION_AUTHORIZED: False"
    )

    if enough:
        print(
            "\nSTAGE B COMPLETE"
        )
        print(
            "Proceed to Stage C."
        )
    else:
        print(
            "\nSTAGE B HOLD"
        )
        print(
            "Do not run WP-MORPH-05."
        )


# ============================================================
# 6. VERIFY STAGE B
# ============================================================

def verify_stage_b(
    run_dir: Path,
) -> tuple[
    pd.DataFrame,
    dict,
    dict,
]:
    stage_b_manifest = (
        read_json(
            run_dir
            / "stage_b_manifest.json"
        )
    )

    require(
        stage_b_manifest.get(
            "work_package"
        )
        == "WP-MORPH-04H-B",
        "Invalid Stage-B manifest",
    )

    require(
        stage_b_manifest.get(
            "status"
        )
        == "PROVISIONAL_NOMINATION_READY",
        (
            "Stage B is not ready "
            "for final authorization"
        ),
    )

    for filename, expected in (
        stage_b_manifest[
            "output_hashes"
        ].items()
    ):
        path = (
            run_dir
            / filename
        )

        require(
            path.is_file(),
            (
                f"Stage-B output missing: "
                f"{path}"
            ),
        )

        require(
            sha256_file(
                path
            )
            == str(
                expected
            ).upper(),
            (
                f"Stage-B output changed: "
                f"{path}"
            ),
        )

    identity_checks = (
        pd.read_csv(
            run_dir
            / "current_identity_check.csv",
            encoding="utf-8-sig",
        )
    )

    stage_b_summary = (
        read_json(
            run_dir
            / "stage_b_summary.json"
        )
    )

    provisional = (
        read_json(
            run_dir
            / "provisional_nomination.json"
        )
    )

    nominees = (
        provisional.get(
            "selected_cities",
            [],
        )
    )

    require(
        len(
            nominees
        )
        == TARGET_CITY_COUNT,
        (
            "Provisional nomination does "
            "not contain exactly three cities"
        ),
    )

    passing_ids = (
        identity_checks.loc[
            identity_checks[
                "identity_match"
            ].apply(
                parse_bool
            ),
            "city_id",
        ]
        .astype(str)
        .tolist()
    )

    require(
        passing_ids[
            :TARGET_CITY_COUNT
        ]
        == [
            item[
                "city_id"
            ]
            for item
            in nominees
        ],
        (
            "Provisional nominees do not "
            "match first three identity-pass "
            "cities under frozen selection rule"
        ),
    )

    return (
        identity_checks,
        stage_b_summary,
        provisional,
    )


# ============================================================
# 7. STAGE C
#    Final identity recheck and authorization
# ============================================================

def run_stage_c() -> None:
    run_dir = (
        get_active_run()
    )

    pool, stage_a = (
        verify_stage_a(
            run_dir
        )
    )

    (
        stage_b_checks,
        stage_b,
        provisional,
    ) = (
        verify_stage_b(
            run_dir
        )
    )

    current_source = (
        verify_upstream_sources()
    )

    require(
        current_source[
            "source_hashes"
        ]
        == stage_a[
            "source_hashes"
        ],
        (
            "Upstream source state changed "
            "between Stage A and Stage C"
        ),
    )

    nominees = (
        provisional[
            "selected_cities"
        ]
    )

    final_checks = []

    print(
        "\n=== WP-MORPH-04H STAGE C ==="
    )

    print(
        "Final re-verification of "
        "three nominated Parquet identities..."
    )

    for nominee in (
        nominees
    ):
        city_id = str(
            nominee[
                "city_id"
            ]
        )

        path = Path(
            nominee[
                "grid_path"
            ]
        )

        expected_rows = int(
            nominee[
                "parquet_rows"
            ]
        )

        expected_sha = str(
            nominee[
                "sha256"
            ]
        ).upper()

        exists = (
            path.is_file()
        )

        current_rows = None
        current_sha = ""
        metadata_pass = False
        row_match = False
        sha_match = False

        if exists:
            try:
                parquet = (
                    pq.ParquetFile(
                        path
                    )
                )

                current_rows = int(
                    parquet.metadata.num_rows
                )

                parquet.close()

                metadata_pass = True

                row_match = (
                    current_rows
                    == expected_rows
                )

            except Exception:
                metadata_pass = False

        if (
            exists
            and metadata_pass
            and row_match
        ):
            current_sha = (
                sha256_file(
                    path
                )
            )

            sha_match = (
                current_sha
                == expected_sha
            )

        final_match = bool(
            exists
            and metadata_pass
            and row_match
            and sha_match
        )

        final_checks.append(
            {
                "city_id": (
                    city_id
                ),
                "city_name": (
                    nominee[
                        "city_name"
                    ]
                ),
                "grid_path": str(
                    path
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
                "final_identity_match": (
                    final_match
                ),
            }
        )

        print(
            f"{city_id}: "
            + (
                "FINAL_IDENTITY_PASS"
                if final_match
                else "FINAL_IDENTITY_HOLD"
            )
        )

    final_checks_df = (
        pd.DataFrame(
            final_checks
        )
    )

    final_checks_path = (
        run_dir
        / "final_identity_recheck.csv"
    )

    final_checks_df.to_csv(
        final_checks_path,
        index=False,
        encoding="utf-8-sig",
    )

    all_final_pass = bool(
        final_checks_df[
            "final_identity_match"
        ].all()
    )

    authorization = (
        all_final_pass
        and len(
            final_checks_df
        )
        == TARGET_CITY_COUNT
    )

    final_nomination_path = (
        run_dir
        / "validation_city_nomination.json"
    )

    if authorization:
        final_nomination = {
            "work_package": (
                "WP-MORPH-04H"
            ),
            "status": (
                "AUTHORIZED_FOR_WP_MORPH05_NONPRODUCTION"
            ),
            "authorization_scope": (
                "WP-MORPH-05 independent morphology "
                "validation only"
            ),
            "target_city_count": (
                TARGET_CITY_COUNT
            ),
            "selected_cities": [
                {
                    "selection_rank": (
                        index + 1
                    ),
                    "city_id": (
                        row[
                            "city_id"
                        ]
                    ),
                    "city_name": (
                        row[
                            "city_name"
                        ]
                    ),
                    "grid_path": (
                        row[
                            "grid_path"
                        ]
                    ),
                    "parquet_rows": int(
                        row[
                            "current_rows"
                        ]
                    ),
                    "sha256": (
                        row[
                            "current_sha256"
                        ]
                    ),
                }
                for index, row
                in final_checks_df.iterrows()
            ],
            "selection_rule": (
                stage_a[
                    "selection_rule"
                ]
            ),
            "canonical_roster": (
                "VERIFIED"
            ),
            "canonical_fingerprint_group": (
                stage_a[
                    "canonical_fingerprint_group"
                ]
            ),
            "canonical_mapping_fingerprint": (
                stage_a[
                    "canonical_mapping_fingerprint"
                ]
            ),
            "frozen_negative_city_ids": (
                stage_a[
                    "frozen_negative_city_ids"
                ]
            ),
            "qc_rules_reevaluated": False,
            "roster_rules_reevaluated": False,
            "selection_based_on_validation_outcomes": False,
            "candidate_morphology_results_inspected_before_selection": False,
            "formal_canu_production_authorized": False,
            "formal_canu_gates_changed": False,
            "validation_execution_authorized": True,
        }

        write_json(
            final_nomination_path,
            final_nomination,
        )

        final_status = (
            "AUTHORIZED_FOR_WP_MORPH05_NONPRODUCTION"
        )

    else:
        final_status = (
            "HOLD_FINAL_IDENTITY_RECHECK_FAILED"
        )

    qc_summary = {
        "work_package": (
            "WP-MORPH-04H"
        ),
        "status": (
            final_status
        ),
        "canonical_roster": (
            "VERIFIED"
        ),
        "canonical_fingerprint_group": (
            stage_a[
                "canonical_fingerprint_group"
            ]
        ),
        "frozen_strong_qc_pass_cities": (
            stage_a[
                "frozen_strong_qc_pass_cities"
            ]
        ),
        "frozen_negative_cities": (
            stage_a[
                "frozen_negative_cities"
            ]
        ),
        "frozen_negative_city_ids": (
            stage_a[
                "frozen_negative_city_ids"
            ]
        ),
        "clean_candidates_pre_identity": (
            stage_a[
                "clean_candidates_pre_identity"
            ]
        ),
        "nominated_city_count": (
            TARGET_CITY_COUNT
            if authorization
            else 0
        ),
        "nominated_city_ids": (
            final_checks_df[
                "city_id"
            ].tolist()
            if authorization
            else []
        ),
        "final_identity_pass": (
            all_final_pass
        ),
        "qc_rules_reevaluated": False,
        "roster_rules_reevaluated": False,
        "candidate_morphology_results_inspected": False,
        "validation_execution_authorized": (
            authorization
        ),
        "authorization_scope": (
            "WP-MORPH-05 NONPRODUCTION"
            if authorization
            else "NONE"
        ),
        "formal_canu_production_authorized": False,
        "formal_canu_gates_changed": False,
    }

    qc_path = (
        run_dir
        / "qc_summary.json"
    )

    write_json(
        qc_path,
        qc_summary,
    )

    output_hashes = {
        "frozen_candidate_pool.csv": (
            sha256_file(
                run_dir
                / "frozen_candidate_pool.csv"
            )
        ),
        "stage_a_summary.json": (
            sha256_file(
                run_dir
                / "stage_a_summary.json"
            )
        ),
        "stage_a_manifest.json": (
            sha256_file(
                run_dir
                / "stage_a_manifest.json"
            )
        ),
        "current_identity_check.csv": (
            sha256_file(
                run_dir
                / "current_identity_check.csv"
            )
        ),
        "stage_b_summary.json": (
            sha256_file(
                run_dir
                / "stage_b_summary.json"
            )
        ),
        "stage_b_manifest.json": (
            sha256_file(
                run_dir
                / "stage_b_manifest.json"
            )
        ),
        "provisional_nomination.json": (
            sha256_file(
                run_dir
                / "provisional_nomination.json"
            )
        ),
        "final_identity_recheck.csv": (
            sha256_file(
                final_checks_path
            )
        ),
        "qc_summary.json": (
            sha256_file(
                qc_path
            )
        ),
    }

    if authorization:
        output_hashes[
            "validation_city_nomination.json"
        ] = (
            sha256_file(
                final_nomination_path
            )
        )

    manifest = {
        "work_package": (
            "WP-MORPH-04H"
        ),
        "status": (
            final_status
        ),
        "run_directory": str(
            run_dir
        ),
        "source_hashes": (
            stage_a[
                "source_hashes"
            ]
        ),
        "script_path": str(
            Path(__file__).resolve()
        ),
        "script_sha256_at_finalization": (
            sha256_file(
                Path(__file__).resolve()
            )
        ),
        "canonical_roster": (
            "VERIFIED"
        ),
        "canonical_fingerprint_group": (
            stage_a[
                "canonical_fingerprint_group"
            ]
        ),
        "nominated_city_ids": (
            final_checks_df[
                "city_id"
            ].tolist()
            if authorization
            else []
        ),
        "validation_execution_authorized": (
            authorization
        ),
        "authorization_scope": (
            "WP-MORPH-05_NONPRODUCTION"
            if authorization
            else "NONE"
        ),
        "formal_canu_production_authorized": False,
        "formal_canu_gates_changed": False,
        "output_hashes": (
            output_hashes
        ),
    }

    manifest_path = (
        run_dir
        / "manifest.json"
    )

    write_json(
        manifest_path,
        manifest,
    )

    print(
        "\n=== WP-MORPH-04H FINAL SUMMARY ==="
    )

    print(
        "CANONICAL_ROSTER: VERIFIED"
    )

    print(
        "FINAL_IDENTITY_PASS:",
        all_final_pass,
    )

    print(
        "NOMINATED_CITY_COUNT:",
        (
            TARGET_CITY_COUNT
            if authorization
            else 0
        ),
    )

    print(
        "NOMINATED_CITY_IDS:",
        (
            final_checks_df[
                "city_id"
            ].tolist()
            if authorization
            else []
        ),
    )

    print(
        "CANDIDATE_MORPHOLOGY_RESULTS_INSPECTED: NO"
    )

    print(
        "QC_RULES_REEVALUATED: NO"
    )

    print(
        "ROSTER_RULES_REEVALUATED: NO"
    )

    print(
        "VALIDATION_EXECUTION_AUTHORIZED:",
        authorization,
    )

    print(
        "AUTHORIZATION_SCOPE:",
        (
            "WP-MORPH-05_NONPRODUCTION"
            if authorization
            else "NONE"
        ),
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
        "STATUS:",
        final_status,
    )

    print(
        "OUTPUT:",
        run_dir,
    )

    print(
        "SCRIPT_SHA256:",
        manifest[
            "script_sha256_at_finalization"
        ],
    )


# ============================================================
# 8. CLI
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "WP-MORPH-04H staged "
            "validation-city nomination"
        )
    )

    parser.add_argument(
        "--stage",
        required=True,
        choices=[
            "A",
            "B",
            "C",
            "a",
            "b",
            "c",
        ],
        help=(
            "A = freeze candidate pool; "
            "B = identity check + provisional nomination; "
            "C = final recheck + authorization"
        ),
    )

    args = (
        parser.parse_args()
    )

    stage = (
        args.stage.upper()
    )

    if stage == "A":
        run_stage_a()

    elif stage == "B":
        run_stage_b()

    elif stage == "C":
        run_stage_c()

    else:
        raise RuntimeError(
            f"Unsupported stage: {stage}"
        )


if __name__ == "__main__":
    main()
