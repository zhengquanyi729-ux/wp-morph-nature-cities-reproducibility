"""
WP-MORPH-05C
Exploration–Validation Concordance Synthesis
Execution Script V1

METHOD CONTRACT:
    WP-MORPH-05C-METHOD-V1

IMPLEMENTATION SPEC:
    WP-MORPH-05C-IMPLEMENTATION-V1

SCOPE:
    Descriptive synthesis of already frozen WP03 and WP05B result tables.

STRICTLY PROHIBITED:
    - raw 50 m data reads
    - WP05A validation-window reads
    - coefficient re-estimation
    - new cities/scales/selections/relationships/metrics
    - p-values or significance testing
    - post-hoc success thresholds
    - composite robustness scores
    - relationship rankings
    - formal CANU production authorization
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ============================================================
# 0. FROZEN IDS / PATHS / HASHES
# ============================================================

ROOT = Path(r"C:\china_meld")

METHOD_CONTRACT_ID = "WP-MORPH-05C-METHOD-V1"
METHOD_CONTRACT_SHA256 = (
    "936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3"
)
IMPLEMENTATION_SPEC_ID = "WP-MORPH-05C-IMPLEMENTATION-V1"

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
PREFLIGHT_DIR = (
    ROOT
    / "experiments"
    / "wp_morph05c_nonproduction"
    / "input_preflight_20260927_191052_983557"
)
OUTPUT_BASE = (
    ROOT
    / "experiments"
    / "wp_morph05c_nonproduction"
)

WP03_RESULT = WP03_DIR / "pairwise_relations.csv"
WP05B_CORR = WP05B_DIR / "validation_correlations.csv"
WP05B_DIRCHECK = WP05B_DIR / "validation_direction_checks.csv"
WP05B_CITYSUM = WP05B_DIR / "validation_summary_by_city.csv"
WP05B_HYPSUM = WP05B_DIR / "validation_hypothesis_summary.csv"

FROZEN_INPUTS = {
    WP03_RESULT: {
        "role": "WP03_FROZEN_PAIRWISE_RESULT",
        "sha256": "34AD797084524C5FC471877B4A8B7011B54FAAECF0DA58ECCF07D9655C922920",
        "size_bytes": 7059,
    },
    WP05B_CORR: {
        "role": "WP05B_VALIDATION_CORRELATIONS",
        "sha256": "B0A2CCCB5B42DAEED12B51CDC129F681FC05946B3C42A11065E97CC10E35E75B",
        "size_bytes": 7380,
    },
    WP05B_DIRCHECK: {
        "role": "WP05B_DIRECTION_CHECKS",
        "sha256": "15E31E50CAAB5F6A786209BBBB8C1249EB4AB8F39E00601038046946CEE880E3",
        "size_bytes": 4794,
    },
    WP05B_CITYSUM: {
        "role": "WP05B_CITY_SUMMARY",
        "sha256": "2280D081A347AC1053872A2C167940E37DA4471E2B2D3326A7734FC53AD92B1F",
        "size_bytes": 948,
    },
    WP05B_HYPSUM: {
        "role": "WP05B_HYPOTHESIS_SUMMARY",
        "sha256": "9CB157A722913EBD88ED7D3103E38DBE704BCA816338613944C92D3ABCCEF7C5",
        "size_bytes": 809,
    },
}

EXPECTED_EXPLORATION_CITIES = ["P004", "P026", "P037"]
EXPECTED_VALIDATION_CITIES = ["P001", "P003", "P005"]
SCALES = ["1km", "5km"]
SELECTIONS = ["ALL", "COVERAGE_80"]
RELATIONSHIPS = ["BUILDING_ROAD", "BUILDING_HEIGHT", "ROAD_HEIGHT"]
METRICS = ["SPEARMAN_RHO", "WEIGHTED_PEARSON_R"]

PAIR_MAP = {
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


# ============================================================
# 1. GENERAL HELPERS
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


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def finite_series(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    return x[np.isfinite(x)].astype(float)


def qlinear(s: pd.Series, q: float) -> float:
    x = finite_series(s)
    require(len(x) > 0, "Cannot calculate quantile on empty finite series")
    return float(x.quantile(q, interpolation=QUANTILE_INTERPOLATION))


def median_finite(s: pd.Series) -> float:
    x = finite_series(s)
    require(len(x) > 0, "Cannot calculate median on empty finite series")
    return float(x.median())


def min_finite(s: pd.Series) -> float:
    x = finite_series(s)
    require(len(x) > 0, "Cannot calculate minimum on empty finite series")
    return float(x.min())


def max_finite(s: pd.Series) -> float:
    x = finite_series(s)
    require(len(x) > 0, "Cannot calculate maximum on empty finite series")
    return float(x.max())


def normalize_text(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def make_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = OUTPUT_BASE / f"run_{stamp}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def record_file(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "path": str(path),
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


# ============================================================
# 2. PRE-SYNTHESIS IDENTITY GATES
# ============================================================

def verify_preflight() -> dict[str, Any]:
    registry = PREFLIGHT_DIR / "wp_morph05c_input_registry.json"
    require(registry.is_file(), f"Missing preflight registry: {registry}")

    obj = json.loads(registry.read_text(encoding="utf-8"))

    require(
        obj.get("input_registration_qc") == "PASS",
        "05C input-registration preflight did not PASS",
    )
    require(
        obj.get("analytical_execution_authorized") is True,
        "05C preflight did not authorize analytical execution",
    )
    require(
        obj.get("method_contract_id") == METHOD_CONTRACT_ID,
        "Preflight METHOD_CONTRACT_ID mismatch",
    )
    require(
        obj.get("method_contract_sha256") == METHOD_CONTRACT_SHA256,
        "Preflight method-contract SHA256 mismatch",
    )
    require(
        obj.get("formal_canu_production_authorized") is False,
        "Formal CANU production must remain unauthorized",
    )

    return record_file(registry, "WP05C_INPUT_PREFLIGHT_REGISTRY")


def verify_frozen_inputs() -> list[dict[str, Any]]:
    records = []

    for path, expected in FROZEN_INPUTS.items():
        require(path.is_file(), f"Missing frozen input: {path}")

        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)

        require(
            actual_size == expected["size_bytes"],
            (
                f"Size mismatch: {path.name}: "
                f"{actual_size} != {expected['size_bytes']}"
            ),
        )
        require(
            actual_hash == expected["sha256"],
            (
                f"SHA256 mismatch: {path.name}\n"
                f"expected={expected['sha256']}\n"
                f"actual={actual_hash}"
            ),
        )

        rec = record_file(path, expected["role"])
        rec["identity_gate"] = "PASS"
        records.append(rec)

    return records


# ============================================================
# 3. LOAD ONLY FROZEN RESULT-LEVEL TABLES
# ============================================================

def load_wp03() -> pd.DataFrame:
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

    df = pd.read_csv(WP03_RESULT, encoding="utf-8-sig")
    require(required.issubset(df.columns), f"WP03 schema mismatch: {sorted(required - set(df.columns))}")

    df = normalize_text(
        df,
        ["city_id", "scale", "selection", "variable_x", "variable_y", "status"],
    )

    df["pair_id"] = [
        PAIR_MAP.get((x, y))
        for x, y in zip(df["variable_x"], df["variable_y"])
    ]

    require(df["pair_id"].notna().all(), "WP03 contains an unexpected relationship")
    require(len(df) == EXPECTED_PHASE_UNITS, "WP03 must contain exactly 36 frozen units")
    require(set(df["city_id"]) == set(EXPECTED_EXPLORATION_CITIES), "WP03 city universe changed")
    require(set(df["scale"]) == set(SCALES), "WP03 scale universe changed")
    require(set(df["selection"]) == set(SELECTIONS), "WP03 selection universe changed")
    require(set(df["pair_id"]) == set(RELATIONSHIPS), "WP03 relationship universe changed")
    require((pd.to_numeric(df["valid_pair_windows"], errors="coerce") >= MIN_VALID_WINDOWS).all(),
            "WP03 contains a unit below frozen minimum valid-window gate")

    unit_keys = ["city_id", "scale", "selection", "pair_id"]
    require(not df.duplicated(unit_keys).any(), "WP03 contains duplicate frozen units")

    for c in ["spearman_rho", "weighted_pearson_r"]:
        vals = pd.to_numeric(df[c], errors="coerce")
        require(np.isfinite(vals).all(), f"WP03 has undefined inherited coefficient: {c}")

    out = df[
        [
            "city_id",
            "scale",
            "selection",
            "pair_id",
            "spearman_rho",
            "weighted_pearson_r",
        ]
    ].copy()
    out.insert(0, "phase", "EXPLORATION")
    return out


def load_wp05b_correlations() -> pd.DataFrame:
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

    df = pd.read_csv(WP05B_CORR, encoding="utf-8-sig")
    require(required.issubset(df.columns), f"WP05B correlation schema mismatch: {sorted(required - set(df.columns))}")

    df = normalize_text(df, ["city_id", "scale", "selection", "pair_id", "expected_sign"])

    require(len(df) == EXPECTED_PHASE_UNITS, "WP05B must contain exactly 36 frozen units")
    require(set(df["city_id"]) == set(EXPECTED_VALIDATION_CITIES), "WP05B city universe changed")
    require(set(df["scale"]) == set(SCALES), "WP05B scale universe changed")
    require(set(df["selection"]) == set(SELECTIONS), "WP05B selection universe changed")
    require(set(df["pair_id"]) == set(RELATIONSHIPS), "WP05B relationship universe changed")
    require(set(df["expected_sign"]) == {"POSITIVE"}, "WP05B expected sign changed")
    require((pd.to_numeric(df["n_pairwise_valid_windows"], errors="coerce") >= MIN_VALID_WINDOWS).all(),
            "WP05B contains a unit below frozen minimum valid-window gate")

    pval = df["p_value_computed"].astype(str).str.strip().str.lower()
    require(set(pval).issubset({"false", "0"}), "WP05B unexpectedly reports p-values computed")

    unit_keys = ["city_id", "scale", "selection", "pair_id"]
    require(not df.duplicated(unit_keys).any(), "WP05B contains duplicate frozen units")

    for c in ["spearman_rho", "weighted_pearson_r"]:
        vals = pd.to_numeric(df[c], errors="coerce")
        require(np.isfinite(vals).all(), f"WP05B has undefined inherited coefficient: {c}")

    out = df[
        [
            "city_id",
            "scale",
            "selection",
            "pair_id",
            "spearman_rho",
            "weighted_pearson_r",
        ]
    ].copy()
    out.insert(0, "phase", "VALIDATION")
    return out


def load_direction_checks() -> pd.DataFrame:
    required = {
        "city_id",
        "scale",
        "selection",
        "pair_id",
        "expected_sign",
        "classification",
    }
    df = pd.read_csv(WP05B_DIRCHECK, encoding="utf-8-sig")
    require(required.issubset(df.columns), "WP05B direction-check schema mismatch")

    df = normalize_text(
        df,
        ["city_id", "scale", "selection", "pair_id", "expected_sign", "classification"],
    )

    require(len(df) == 36, "Direction-check table must contain 36 units")
    require(set(df["expected_sign"]) == {"POSITIVE"}, "Expected sign changed in direction checks")

    unit_keys = ["city_id", "scale", "selection", "pair_id"]
    require(not df.duplicated(unit_keys).any(), "Duplicate direction-check units")
    return df


def qc_frozen_summary_tables(direction: pd.DataFrame) -> dict[str, Any]:
    city = pd.read_csv(WP05B_CITYSUM, encoding="utf-8-sig")
    hyp = pd.read_csv(WP05B_HYPSUM, encoding="utf-8-sig")

    require(len(city) == 9, "validation_summary_by_city.csv row count changed")
    require(len(hyp) == 3, "validation_hypothesis_summary.csv row count changed")

    dir_counts = direction["classification"].value_counts().to_dict()
    require(dir_counts.get("SAME_SIGN", 0) == 36, "Frozen 36/36 SAME_SIGN outcome changed")
    require(dir_counts.get("SIGN_REVERSAL", 0) == 0, "Unexpected sign reversal")
    require(dir_counts.get("INSUFFICIENT_WINDOWS", 0) == 0, "Unexpected insufficient-window unit")
    require(dir_counts.get("UNDEFINED", 0) == 0, "Unexpected undefined unit")

    require(
        int(pd.to_numeric(hyp["validation_units_total"]).sum()) == 36,
        "Hypothesis-summary total units != 36",
    )
    require(
        int(pd.to_numeric(hyp["same_sign_units"]).sum()) == 36,
        "Hypothesis-summary SAME_SIGN total != 36",
    )
    require(
        int(pd.to_numeric(hyp["sign_reversal_units"]).sum()) == 0,
        "Hypothesis-summary sign reversals != 0",
    )

    return {
        "validation_unit_count": 36,
        "same_sign_units": 36,
        "sign_reversal_units": 0,
        "insufficient_windows_units": 0,
        "undefined_units": 0,
        "summary_crosscheck": "PASS",
    }


# ============================================================
# 4. CANONICAL LONG COEFFICIENT TABLE
# ============================================================

def canonical_long(wp03: pd.DataFrame, wp05b: pd.DataFrame) -> pd.DataFrame:
    base = pd.concat([wp03, wp05b], ignore_index=True)

    rows = []
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
    require(np.isfinite(long["coefficient"]).all(), "Canonical coefficient table contains non-finite values")
    return long


# ============================================================
# 5. OUTPUT 01: DIRECTIONAL CONCORDANCE
# ============================================================

def make_directional_concordance(direction: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for rel in RELATIONSHIPS:
        g = direction.loc[direction["pair_id"] == rel]
        counts = g["classification"].value_counts().to_dict()

        same = int(counts.get("SAME_SIGN", 0))
        rev = int(counts.get("SIGN_REVERSAL", 0))
        insuff = int(counts.get("INSUFFICIENT_WINDOWS", 0))
        undef = int(counts.get("UNDEFINED", 0))
        eligible = same + rev + undef

        rows.append(
            {
                "relationship": rel,
                "expected_sign": "POSITIVE",
                "exploration_city_count": 3,
                "validation_city_count": 3,
                "validation_unit_count": int(len(g)),
                "same_sign_count": same,
                "sign_reversal_count": rev,
                "insufficient_count": insuff,
                "undefined_count": undef,
                "directional_reproducibility_fraction": (
                    float(same / eligible) if eligible > 0 else np.nan
                ),
            }
        )

    out = pd.DataFrame(rows)
    require(len(out) == 3, "Directional-concordance output must contain 3 rows")
    return out


# ============================================================
# 6. OUTPUT 02: EXPLORATION–VALIDATION MAGNITUDE SUMMARY
# ============================================================

def summarize_phase_coefficients(g: pd.DataFrame, prefix: str) -> dict[str, Any]:
    s = finite_series(g["coefficient"])
    require(len(s) == 3, f"{prefix}: expected exactly 3 frozen city coefficients")

    mn = float(s.min())
    mx = float(s.max())

    return {
        f"{prefix}_n": int(len(s)),
        f"{prefix}_median": float(s.median()),
        f"{prefix}_q1": float(s.quantile(Q1, interpolation=QUANTILE_INTERPOLATION)),
        f"{prefix}_q3": float(s.quantile(Q3, interpolation=QUANTILE_INTERPOLATION)),
        f"{prefix}_min": mn,
        f"{prefix}_max": mx,
        f"{prefix}_range": mx - mn,
    }


def make_magnitude_summary(long: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for rel in RELATIONSHIPS:
        for scale in SCALES:
            for selection in SELECTIONS:
                for metric in METRICS:
                    q = long.loc[
                        (long["relationship"] == rel)
                        & (long["scale"] == scale)
                        & (long["selection"] == selection)
                        & (long["metric"] == metric)
                    ]

                    eg = q.loc[q["phase"] == "EXPLORATION"]
                    vg = q.loc[q["phase"] == "VALIDATION"]

                    er = summarize_phase_coefficients(eg, "exploration")
                    vr = summarize_phase_coefficients(vg, "validation")

                    shift = vr["validation_median"] - er["exploration_median"]

                    rows.append(
                        {
                            "relationship": rel,
                            "scale": scale,
                            "selection": selection,
                            "metric": metric,
                            **er,
                            **vr,
                            "median_shift": shift,
                            "absolute_median_shift": abs(shift),
                        }
                    )

    out = pd.DataFrame(rows)
    require(len(out) == 24, "Magnitude-summary output must contain 24 rows")
    return out


# ============================================================
# 7. OUTPUT 03: SCALE / COVERAGE / METRIC SENSITIVITY
# ============================================================

def get_one(
    long: pd.DataFrame,
    phase: str,
    city: str,
    rel: str,
    scale: str,
    selection: str,
    metric: str,
) -> float:
    q = long.loc[
        (long["phase"] == phase)
        & (long["city_id"] == city)
        & (long["relationship"] == rel)
        & (long["scale"] == scale)
        & (long["selection"] == selection)
        & (long["metric"] == metric),
        "coefficient",
    ]
    require(len(q) == 1, "Expected exactly one frozen coefficient for sensitivity lookup")
    v = float(q.iloc[0])
    require(np.isfinite(v), "Sensitivity lookup encountered non-finite coefficient")
    return v


def make_sensitivity(long: pd.DataFrame) -> pd.DataFrame:
    rows = []

    phase_cities = {
        "EXPLORATION": EXPECTED_EXPLORATION_CITIES,
        "VALIDATION": EXPECTED_VALIDATION_CITIES,
    }

    for phase, cities in phase_cities.items():
        for city in cities:
            for rel in RELATIONSHIPS:

                # SCALE: B - A = 5km - 1km
                for selection in SELECTIONS:
                    for metric in METRICS:
                        a = get_one(long, phase, city, rel, "1km", selection, metric)
                        b = get_one(long, phase, city, rel, "5km", selection, metric)
                        d = b - a
                        rows.append(
                            {
                                "phase": phase,
                                "city_id": city,
                                "relationship": rel,
                                "dimension": "SCALE",
                                "conditioning_scale_or_selection": selection,
                                "metric": metric,
                                "comparison_a": "1km",
                                "comparison_b": "5km",
                                "coefficient_a": a,
                                "coefficient_b": b,
                                "signed_delta": d,
                                "absolute_delta": abs(d),
                            }
                        )

                # COVERAGE: B - A = COVERAGE_80 - ALL
                for scale in SCALES:
                    for metric in METRICS:
                        a = get_one(long, phase, city, rel, scale, "ALL", metric)
                        b = get_one(long, phase, city, rel, scale, "COVERAGE_80", metric)
                        d = b - a
                        rows.append(
                            {
                                "phase": phase,
                                "city_id": city,
                                "relationship": rel,
                                "dimension": "COVERAGE",
                                "conditioning_scale_or_selection": scale,
                                "metric": metric,
                                "comparison_a": "ALL",
                                "comparison_b": "COVERAGE_80",
                                "coefficient_a": a,
                                "coefficient_b": b,
                                "signed_delta": d,
                                "absolute_delta": abs(d),
                            }
                        )

                # METRIC: B - A = weighted Pearson - Spearman
                for scale in SCALES:
                    for selection in SELECTIONS:
                        a = get_one(
                            long, phase, city, rel, scale, selection, "SPEARMAN_RHO"
                        )
                        b = get_one(
                            long, phase, city, rel, scale, selection, "WEIGHTED_PEARSON_R"
                        )
                        d = b - a
                        rows.append(
                            {
                                "phase": phase,
                                "city_id": city,
                                "relationship": rel,
                                "dimension": "METRIC",
                                "conditioning_scale_or_selection": f"{scale}|{selection}",
                                "metric": "SPEARMAN_VS_WEIGHTED_PEARSON",
                                "comparison_a": "SPEARMAN_RHO",
                                "comparison_b": "WEIGHTED_PEARSON_R",
                                "coefficient_a": a,
                                "coefficient_b": b,
                                "signed_delta": d,
                                "absolute_delta": abs(d),
                            }
                        )

    out = pd.DataFrame(rows)
    require(len(out) == 216, "Sensitivity output must contain 216 rows")
    return out


# ============================================================
# 8. OUTPUT 04: RELATIONSHIP ROBUSTNESS PROFILE
# ============================================================

def cross_city_ranges(long: pd.DataFrame, phase: str, rel: str) -> list[float]:
    vals = []
    for scale in SCALES:
        for selection in SELECTIONS:
            for metric in METRICS:
                g = long.loc[
                    (long["phase"] == phase)
                    & (long["relationship"] == rel)
                    & (long["scale"] == scale)
                    & (long["selection"] == selection)
                    & (long["metric"] == metric),
                    "coefficient",
                ]
                require(len(g) == 3, "Cross-city range expected exactly three frozen cities")
                vals.append(float(g.max() - g.min()))
    require(len(vals) == 8, "Expected eight cross-city ranges per phase/relationship")
    return vals


def make_robustness_profile(
    long: pd.DataFrame,
    sensitivity: pd.DataFrame,
    direction: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for phase in ["EXPLORATION", "VALIDATION"]:
        for rel in RELATIONSHIPS:
            ranges = cross_city_ranges(long, phase, rel)

            sg = sensitivity.loc[
                (sensitivity["phase"] == phase)
                & (sensitivity["relationship"] == rel)
                & (sensitivity["dimension"] == "SCALE")
            ]
            cg = sensitivity.loc[
                (sensitivity["phase"] == phase)
                & (sensitivity["relationship"] == rel)
                & (sensitivity["dimension"] == "COVERAGE")
            ]
            mg = sensitivity.loc[
                (sensitivity["phase"] == phase)
                & (sensitivity["relationship"] == rel)
                & (sensitivity["dimension"] == "METRIC")
            ]

            require(len(sg) == 12, "Expected 12 scale deltas per phase/relationship")
            require(len(cg) == 12, "Expected 12 coverage deltas per phase/relationship")
            require(len(mg) == 12, "Expected 12 metric deltas per phase/relationship")

            if phase == "VALIDATION":
                dg = direction.loc[direction["pair_id"] == rel]
                counts = dg["classification"].value_counts().to_dict()
                same_count: Any = int(counts.get("SAME_SIGN", 0))
                eligible_count: Any = int(
                    counts.get("SAME_SIGN", 0)
                    + counts.get("SIGN_REVERSAL", 0)
                    + counts.get("UNDEFINED", 0)
                )
            else:
                # Frozen implementation decision:
                # do not create a new retrospective WP03 SAME_SIGN classification.
                same_count = np.nan
                eligible_count = np.nan

            rows.append(
                {
                    "phase": phase,
                    "relationship": rel,
                    "directional_same_sign_count": same_count,
                    "directional_eligible_count": eligible_count,
                    "median_cross_city_range": float(np.median(ranges)),
                    "max_cross_city_range": float(np.max(ranges)),
                    "median_abs_scale_delta": median_finite(sg["absolute_delta"]),
                    "max_abs_scale_delta": max_finite(sg["absolute_delta"]),
                    "median_abs_coverage_delta": median_finite(cg["absolute_delta"]),
                    "max_abs_coverage_delta": max_finite(cg["absolute_delta"]),
                    "median_abs_metric_delta": median_finite(mg["absolute_delta"]),
                    "max_abs_metric_delta": max_finite(mg["absolute_delta"]),
                }
            )

    out = pd.DataFrame(rows)
    require(len(out) == 6, "Robustness-profile output must contain 6 rows")
    return out


# ============================================================
# 9. WRITE / QC
# ============================================================

def write_csv_frozen(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
        float_format="%.12g",
    )


def main() -> None:
    script_path = Path(__file__).resolve()
    script_sha_before = sha256_file(script_path)

    print("=== WP-MORPH-05C SYNTHESIS V1 ===")
    print("METHOD_CONTRACT_ID:", METHOD_CONTRACT_ID)
    print("METHOD_CONTRACT_SHA256:", METHOD_CONTRACT_SHA256)
    print("IMPLEMENTATION_SPEC_ID:", IMPLEMENTATION_SPEC_ID)
    print("SCRIPT_SHA256_BEFORE_SYNTHESIS:", script_sha_before)
    print()

    output_dir = make_output_dir()

    # Identity gates happen before analytical result tables are synthesized.
    preflight_record = verify_preflight()
    input_records = verify_frozen_inputs()

    wp03 = load_wp03()
    wp05b = load_wp05b_correlations()
    direction = load_direction_checks()
    frozen_summary_qc = qc_frozen_summary_tables(direction)

    long = canonical_long(wp03, wp05b)

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

    for name, df in outputs.items():
        require(
            len(df) == EXPECTED_OUTPUT_ROWS[name],
            f"{name} row count changed",
        )
        write_csv_frozen(df, output_dir / name)

    script_sha_after = sha256_file(script_path)
    require(
        script_sha_after == script_sha_before,
        (
            "SCRIPT CHANGED DURING SYNTHESIS: "
            f"{script_sha_before} != {script_sha_after}"
        ),
    )

    # Machine-readable contract snapshot.
    method_contract = {
        "method_contract_id": METHOD_CONTRACT_ID,
        "method_contract_sha256": METHOD_CONTRACT_SHA256,
        "implementation_spec_id": IMPLEMENTATION_SPEC_ID,
        "status": "EXECUTED_WITHOUT_METHOD_CHANGE",
        "quartile_method": (
            "pandas Series.quantile with interpolation='linear'"
        ),
        "delta_orientation": {
            "SCALE": "5km - 1km",
            "COVERAGE": "COVERAGE_80 - ALL",
            "METRIC": "weighted_Pearson_r - Spearman_rho",
        },
        "exploration_profile_direction_counts": (
            "NA; no retrospective WP03 SAME_SIGN classification introduced"
        ),
        "validation_profile_direction_counts": (
            "inherited from frozen WP05B validation_direction_checks.csv"
        ),
        "p_values_allowed": False,
        "posthoc_success_threshold_allowed": False,
        "composite_robustness_score_allowed": False,
        "relationship_ranking_allowed": False,
    }
    write_json(output_dir / "method_contract.json", method_contract)

    qc_summary = {
        "work_package": "WP-MORPH-05C",
        "method_contract_id": METHOD_CONTRACT_ID,
        "implementation_spec_id": IMPLEMENTATION_SPEC_ID,
        "overall_qc": "PASS",
        "input_identity_qc": "PASS",
        "preflight_registry_qc": "PASS",
        "wp03_unit_count": int(len(wp03)),
        "wp05b_unit_count": int(len(wp05b)),
        "canonical_coefficient_rows": int(len(long)),
        "output_row_counts": {
            name: int(len(df))
            for name, df in outputs.items()
        },
        **frozen_summary_qc,
        "raw_50m_data_read": False,
        "wp05a_window_data_read": False,
        "coefficients_reestimated": False,
        "exploration_cities_changed": False,
        "validation_cities_changed": False,
        "scales_changed": False,
        "selections_changed": False,
        "relationships_changed": False,
        "metrics_changed": False,
        "weights_changed": False,
        "p_values_computed": False,
        "posthoc_success_threshold_used": False,
        "composite_robustness_score_computed": False,
        "relationship_ranking_computed": False,
        "formal_canu_production_authorized": False,
        "formal_canu_gates": "UNCHANGED",
        "script_sha256_before_synthesis": script_sha_before,
        "script_sha256_after_synthesis": script_sha_after,
        "no_method_changed_after_results": (
            script_sha_before == script_sha_after
        ),
    }
    write_json(output_dir / "qc_summary.json", qc_summary)

    generated_records = [
        record_file(output_dir / name, f"WP05C_OUTPUT_{name}")
        for name in [
            OUTPUT_01,
            OUTPUT_02,
            OUTPUT_03,
            OUTPUT_04,
            "method_contract.json",
            "qc_summary.json",
        ]
    ]

    manifest = {
        "work_package": "WP-MORPH-05C",
        "title": "Exploration–Validation Concordance Synthesis",
        "status": "NONPRODUCTION_SYNTHESIS",
        "output_dir": str(output_dir),
        "method_contract_id": METHOD_CONTRACT_ID,
        "method_contract_sha256": METHOD_CONTRACT_SHA256,
        "implementation_spec_id": IMPLEMENTATION_SPEC_ID,
        "script_path": str(script_path),
        "script_sha256_before_synthesis": script_sha_before,
        "script_sha256_after_synthesis": script_sha_after,
        "input_preflight": preflight_record,
        "frozen_inputs": input_records,
        "generated_outputs": generated_records,
        "formal_canu_production_authorized": False,
        "formal_canu_gates": "UNCHANGED",
    }
    write_json(output_dir / "manifest.json", manifest)

    # Add final manifest identity after it exists.
    manifest_hash = sha256_file(output_dir / "manifest.json")

    print("INPUT_IDENTITY_QC: PASS")
    print("SYNTHESIS_QC: PASS")
    print("DIRECTIONAL_VALIDATION: 36 / 36 SAME_SIGN")
    print("P_VALUES_COMPUTED: False")
    print("COEFFICIENTS_REESTIMATED: False")
    print("POSTHOC_SUCCESS_THRESHOLD_USED: False")
    print("COMPOSITE_ROBUSTNESS_SCORE_COMPUTED: False")
    print("RELATIONSHIP_RANKING_COMPUTED: False")
    print("SCRIPT_SHA256_AFTER_SYNTHESIS:", script_sha_after)
    print("NO_METHOD_CHANGED_AFTER_RESULTS:", script_sha_before == script_sha_after)
    print("FORMAL_CANU_PRODUCTION_AUTHORIZED: False")
    print("FORMAL_CANU_GATES: UNCHANGED")
    print("OUTPUT_DIR:", output_dir)
    print("MANIFEST_SHA256:", manifest_hash)


if __name__ == "__main__":
    main()
