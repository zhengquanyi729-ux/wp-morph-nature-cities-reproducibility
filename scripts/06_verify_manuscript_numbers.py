"""Step 06 - manuscript numerical regression checks.

Every numerical claim made in Results 3.1-3.4 is re-derived from the reproduced
frozen tables and compared with the value reported in the manuscript. The
script writes a machine-readable check report and the human-readable
``manuscript_mapping/manuscript_result_map.csv`` traceability table.

No new statistical quantity is defined here. Every checked quantity already
exists in a frozen WP-MORPH-05C output table.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

import pandas as pd

# Never leave interpreter caches inside the distributed package tree, even when
# this script is invoked directly rather than through run_all.py.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import paths  # noqa: E402
from utils.reporting import read_json, write_json  # noqa: E402
from utils.tables import compare_to_frozen, write_csv  # noqa: E402

EXACT_TOL = 5e-05
DISPLAY_TOL = 0.001


def _resolve_reproduced_or_frozen(name: str) -> Path:
    reproduced = paths.REPRODUCED_TABLES_DIR / name
    if reproduced.is_file():
        return reproduced
    frozen = paths.VALIDATION_DIR / name
    if frozen.is_file():
        return frozen
    raise FileNotFoundError(f"cannot resolve table {name}")


def _magnitude_row(mag: pd.DataFrame, relationship: str, scale: str, selection: str, metric: str) -> pd.Series:
    hit = mag[
        (mag["relationship"] == relationship)
        & (mag["scale"] == scale)
        & (mag["selection"] == selection)
        & (mag["metric"] == metric)
    ]
    if len(hit) != 1:
        raise AssertionError(
            f"expected one magnitude row for {relationship}/{scale}/{selection}/{metric}"
        )
    return hit.iloc[0]


def _profile_row(prof: pd.DataFrame, phase: str, relationship: str) -> pd.Series:
    hit = prof[(prof["phase"] == phase) & (prof["relationship"] == relationship)]
    if len(hit) != 1:
        raise AssertionError(f"expected one profile row for {phase}/{relationship}")
    return hit.iloc[0]


def _sensitivity_value(
    sens: pd.DataFrame,
    phase: str,
    city: str,
    relationship: str,
    dimension: str,
    conditioning: str,
    metric: str,
) -> float:
    hit = sens[
        (sens["phase"] == phase)
        & (sens["city_id"] == city)
        & (sens["relationship"] == relationship)
        & (sens["dimension"] == dimension)
        & (sens["conditioning_scale_or_selection"] == conditioning)
        & (sens["metric"] == metric)
    ]
    if len(hit) != 1:
        raise AssertionError(
            f"expected one sensitivity row for {phase}/{city}/{relationship}/{dimension}/"
            f"{conditioning}/{metric}"
        )
    return float(hit.iloc[0]["signed_delta"])


def build_checks(
    direction: pd.DataFrame,
    sign: pd.DataFrame,
    mag: pd.DataFrame,
    sens: pd.DataFrame,
    prof: pd.DataFrame,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(
        claim_id: str,
        location: str,
        claim: str,
        source_file: str,
        source_columns: str,
        row_filter: str,
        calculation: str,
        expected: Any,
        produced: Callable[[], Any],
        tolerance: float,
    ) -> None:
        checks.append(
            {
                "claim_id": claim_id,
                "manuscript_location": location,
                "reported_claim": claim,
                "source_file": source_file,
                "source_columns": source_columns,
                "filter": row_filter,
                "calculation": calculation,
                "expected_value": expected,
                "reproduced_value": produced(),
                "tolerance": tolerance,
            }
        )

    counts = direction["classification"].value_counts().to_dict()

    # ---------------- Results 3.1 ----------------
    add(
        "3.1_total_same_sign",
        "Results 3.1",
        "36 of 36 validation conditions retained the prespecified positive direction",
        "validation_direction_checks.csv",
        "classification",
        "all frozen validation conditions",
        "count(classification == SAME_SIGN)",
        36,
        lambda: int(counts.get("SAME_SIGN", 0)),
        0.0,
    )
    add(
        "3.1_no_sign_reversal",
        "Results 3.1",
        "No validation condition showed a sign reversal",
        "validation_direction_checks.csv",
        "classification",
        "all frozen validation conditions",
        "count(classification == SIGN_REVERSAL)",
        0,
        lambda: int(counts.get("SIGN_REVERSAL", 0)),
        0.0,
    )
    add(
        "3.1_no_insufficient_windows",
        "Results 3.1",
        "No validation condition had insufficient pairwise-valid windows",
        "validation_direction_checks.csv",
        "classification",
        "all frozen validation conditions",
        "count(classification == INSUFFICIENT_WINDOWS)",
        0,
        lambda: int(counts.get("INSUFFICIENT_WINDOWS", 0)),
        0.0,
    )
    add(
        "3.1_no_undefined",
        "Results 3.1",
        "No validation condition had an undefined coefficient combination",
        "validation_direction_checks.csv",
        "classification",
        "all frozen validation conditions",
        "count(classification == UNDEFINED)",
        0,
        lambda: int(counts.get("UNDEFINED", 0)),
        0.0,
    )
    for relationship in ("BUILDING_ROAD", "BUILDING_HEIGHT", "ROAD_HEIGHT"):
        add(
            f"3.1_{relationship}_12_of_12",
            "Results 3.1",
            f"{relationship} produced 12 of 12 SAME_SIGN validation conditions",
            "validation_direction_checks.csv",
            "classification",
            f"pair_id == {relationship}",
            "count(classification == SAME_SIGN)",
            12,
            (
                lambda rel=relationship: int(
                    (direction.loc[direction["pair_id"] == rel, "classification"] == "SAME_SIGN").sum()
                )
            ),
            0.0,
        )

    # ---------------- Results 3.2 ----------------
    br_shifts = mag.loc[mag["relationship"] == "BUILDING_ROAD", "median_shift"]
    add(
        "3.2_building_road_all_shifts_negative",
        "Results 3.2",
        "BUILDING_ROAD validation medians were lower than exploration medians in all eight "
        "scale/selection/metric combinations",
        "02_exploration_validation_magnitude_summary.csv",
        "median_shift",
        "relationship == BUILDING_ROAD (8 of 24 rows)",
        "count(median_shift < 0)",
        8,
        lambda: int((br_shifts < 0).sum()),
        0.0,
    )

    br_smallest = _magnitude_row(mag, "BUILDING_ROAD", "5km", "ALL", "SPEARMAN_RHO")
    add(
        "3.2_building_road_smallest_exploration",
        "Results 3.2",
        "BUILDING_ROAD smallest shift: 5 km ALL Spearman exploration median 0.734",
        "02_exploration_validation_magnitude_summary.csv",
        "exploration_median",
        "relationship=BUILDING_ROAD; scale=5km; selection=ALL; metric=SPEARMAN_RHO",
        "frozen exploration median of the three exploration cities",
        0.733981031691,
        lambda: float(br_smallest["exploration_median"]),
        EXACT_TOL,
    )
    add(
        "3.2_building_road_smallest_validation",
        "Results 3.2",
        "BUILDING_ROAD smallest shift: 5 km ALL Spearman validation median 0.727",
        "02_exploration_validation_magnitude_summary.csv",
        "validation_median",
        "relationship=BUILDING_ROAD; scale=5km; selection=ALL; metric=SPEARMAN_RHO",
        "frozen validation median of the three validation cities",
        0.727080205595,
        lambda: float(br_smallest["validation_median"]),
        EXACT_TOL,
    )

    br_largest = _magnitude_row(mag, "BUILDING_ROAD", "5km", "COVERAGE_80", "WEIGHTED_PEARSON_R")
    add(
        "3.2_building_road_largest_exploration",
        "Results 3.2",
        "BUILDING_ROAD largest shift: 5 km Coverage >= 80% weighted Pearson exploration median 0.749",
        "02_exploration_validation_magnitude_summary.csv",
        "exploration_median",
        "relationship=BUILDING_ROAD; scale=5km; selection=COVERAGE_80; metric=WEIGHTED_PEARSON_R",
        "frozen exploration median of the three exploration cities",
        0.749126522217,
        lambda: float(br_largest["exploration_median"]),
        EXACT_TOL,
    )
    add(
        "3.2_building_road_largest_validation",
        "Results 3.2",
        "BUILDING_ROAD largest shift: 5 km Coverage >= 80% weighted Pearson validation median 0.617",
        "02_exploration_validation_magnitude_summary.csv",
        "validation_median",
        "relationship=BUILDING_ROAD; scale=5km; selection=COVERAGE_80; metric=WEIGHTED_PEARSON_R",
        "frozen validation median of the three validation cities",
        0.616589927411,
        lambda: float(br_largest["validation_median"]),
        EXACT_TOL,
    )
    add(
        "3.2_building_road_largest_is_max_abs",
        "Results 3.2",
        "BUILDING_ROAD largest median shift occurred at 5 km Coverage >= 80% weighted Pearson",
        "02_exploration_validation_magnitude_summary.csv",
        "absolute_median_shift",
        "relationship == BUILDING_ROAD (8 of 24 rows)",
        "argmax(absolute_median_shift) maps to scale=5km; selection=COVERAGE_80; "
        "metric=WEIGHTED_PEARSON_R",
        "5km/COVERAGE_80/WEIGHTED_PEARSON_R",
        lambda: str(
            mag.loc[mag["relationship"] == "BUILDING_ROAD"]
            .sort_values("absolute_median_shift", ascending=False)
            .iloc[0][["scale", "selection", "metric"]]
            .str.cat(sep="/")
        ),
        0.0,
    )

    building_height_cases = [
        ("3.2_bh_1km_all_spearman", "1km", "ALL", "SPEARMAN_RHO", 0.589260652412, 0.65220320208),
        ("3.2_bh_1km_all_weighted", "1km", "ALL", "WEIGHTED_PEARSON_R", 0.344714452551, 0.300487372702),
        ("3.2_bh_5km_all_spearman", "5km", "ALL", "SPEARMAN_RHO", 0.553010873099, 0.629205610731),
        ("3.2_bh_5km_all_weighted", "5km", "ALL", "WEIGHTED_PEARSON_R", 0.573628215892, 0.624071314576),
        ("3.2_bh_5km_c80_spearman", "5km", "COVERAGE_80", "SPEARMAN_RHO", 0.513294671189, 0.457618377872),
        ("3.2_bh_5km_c80_weighted", "5km", "COVERAGE_80", "WEIGHTED_PEARSON_R", 0.541014968327, 0.623192609824),
    ]
    for claim_id, scale, selection, metric, expected_exploration, expected_validation in building_height_cases:
        row = _magnitude_row(mag, "BUILDING_HEIGHT", scale, selection, metric)
        label = f"{scale} {selection} {metric}"
        add(
            f"{claim_id}_exploration",
            "Results 3.2",
            f"BUILDING_HEIGHT {label} exploration median {expected_exploration}",
            "02_exploration_validation_magnitude_summary.csv",
            "exploration_median",
            f"relationship=BUILDING_HEIGHT; scale={scale}; selection={selection}; metric={metric}",
            "frozen exploration median of the three exploration cities",
            expected_exploration,
            (lambda r=row: float(r["exploration_median"])),
            EXACT_TOL,
        )
        add(
            f"{claim_id}_validation",
            "Results 3.2",
            f"BUILDING_HEIGHT {label} validation median {expected_validation}",
            "02_exploration_validation_magnitude_summary.csv",
            "validation_median",
            f"relationship=BUILDING_HEIGHT; scale={scale}; selection={selection}; metric={metric}",
            "frozen validation median of the three validation cities",
            expected_validation,
            (lambda r=row: float(r["validation_median"])),
            EXACT_TOL,
        )

    road_height_cases = [
        ("3.2_rh_1km_all_spearman", "1km", "ALL", "SPEARMAN_RHO", 0.651295651439, 0.518038844168),
        ("3.2_rh_1km_all_weighted", "1km", "ALL", "WEIGHTED_PEARSON_R", 0.650961587179, 0.53068746359),
    ]
    for claim_id, scale, selection, metric, expected_exploration, expected_validation in road_height_cases:
        row = _magnitude_row(mag, "ROAD_HEIGHT", scale, selection, metric)
        label = f"{scale} {selection} {metric}"
        add(
            f"{claim_id}_exploration",
            "Results 3.2",
            f"ROAD_HEIGHT {label} exploration median {expected_exploration}",
            "02_exploration_validation_magnitude_summary.csv",
            "exploration_median",
            f"relationship=ROAD_HEIGHT; scale={scale}; selection={selection}; metric={metric}",
            "frozen exploration median of the three exploration cities",
            expected_exploration,
            (lambda r=row: float(r["exploration_median"])),
            EXACT_TOL,
        )
        add(
            f"{claim_id}_validation",
            "Results 3.2",
            f"ROAD_HEIGHT {label} validation median {expected_validation}",
            "02_exploration_validation_magnitude_summary.csv",
            "validation_median",
            f"relationship=ROAD_HEIGHT; scale={scale}; selection={selection}; metric={metric}",
            "frozen validation median of the three validation cities",
            expected_validation,
            (lambda r=row: float(r["validation_median"])),
            EXACT_TOL,
        )

    rh_5km = mag[(mag["relationship"] == "ROAD_HEIGHT") & (mag["scale"] == "5km")]
    add(
        "3.2_rh_5km_shifts_negative",
        "Results 3.2",
        "ROAD_HEIGHT 5 km shifts remained negative across all four analytical conditions",
        "02_exploration_validation_magnitude_summary.csv",
        "median_shift",
        "relationship == ROAD_HEIGHT; scale == 5km (4 of 24 rows)",
        "count(median_shift < 0)",
        4,
        lambda: int((rh_5km["median_shift"] < 0).sum()),
        0.0,
    )

    # ---------------- Results 3.3 ----------------
    median_scale_claims = [
        ("BUILDING_ROAD", 0.066931008414, 0.149844609776),
        ("BUILDING_HEIGHT", 0.078152199798, 0.174939730572),
        ("ROAD_HEIGHT", 0.136254986892, 0.193374476081),
    ]
    for relationship, expected_exploration, expected_validation in median_scale_claims:
        add(
            f"3.3_{relationship}_median_scale_exploration",
            "Results 3.3",
            f"{relationship} median absolute scale change {expected_exploration} in exploration",
            "04_relationship_robustness_profile.csv",
            "median_abs_scale_delta",
            f"phase == EXPLORATION; relationship == {relationship}",
            "frozen median absolute scale delta",
            expected_exploration,
            (lambda rel=relationship: float(_profile_row(prof, "EXPLORATION", rel)["median_abs_scale_delta"])),
            EXACT_TOL,
        )
        add(
            f"3.3_{relationship}_median_scale_validation",
            "Results 3.3",
            f"{relationship} median absolute scale change {expected_validation} in validation",
            "04_relationship_robustness_profile.csv",
            "median_abs_scale_delta",
            f"phase == VALIDATION; relationship == {relationship}",
            "frozen median absolute scale delta",
            expected_validation,
            (lambda rel=relationship: float(_profile_row(prof, "VALIDATION", rel)["median_abs_scale_delta"])),
            EXACT_TOL,
        )

    for phase in ("EXPLORATION", "VALIDATION"):
        subset = prof[prof["phase"] == phase]
        add(
            f"3.3_road_height_largest_median_scale_{phase.lower()}",
            "Results 3.3",
            f"ROAD_HEIGHT had the largest observed median scale sensitivity in {phase.lower()}",
            "04_relationship_robustness_profile.csv",
            "median_abs_scale_delta",
            f"phase == {phase} (3 of 6 rows)",
            "argmax(median_abs_scale_delta)",
            "ROAD_HEIGHT",
            lambda s=subset: str(s.sort_values("median_abs_scale_delta", ascending=False).iloc[0]["relationship"]),
            0.0,
        )

    for phase, expected in (("EXPLORATION", 0.337430978364), ("VALIDATION", 0.37407699909)):
        add(
            f"3.3_building_height_max_scale_{phase.lower()}",
            "Results 3.3",
            f"BUILDING_HEIGHT maximum absolute scale change {expected} in {phase.lower()}",
            "04_relationship_robustness_profile.csv",
            "max_abs_scale_delta",
            f"phase == {phase}; relationship == BUILDING_HEIGHT",
            "frozen maximum absolute scale delta",
            expected,
            (lambda ph=phase: float(_profile_row(prof, ph, "BUILDING_HEIGHT")["max_abs_scale_delta"])),
            EXACT_TOL,
        )

    for phase, expected in (("EXPLORATION", 0.331438001526), ("VALIDATION", 0.279586989477)):
        subset = prof[prof["phase"] == phase]
        add(
            f"3.3_building_height_largest_coverage_relationship_{phase.lower()}",
            "Results 3.3",
            f"BUILDING_HEIGHT had the largest maximum absolute coverage change in {phase.lower()} ({expected})",
            "04_relationship_robustness_profile.csv",
            "max_abs_coverage_delta",
            f"phase == {phase} (3 of 6 rows)",
            "argmax(max_abs_coverage_delta)",
            "BUILDING_HEIGHT",
            lambda s=subset: str(
                s.sort_values("max_abs_coverage_delta", ascending=False).iloc[0]["relationship"]
            ),
            0.0,
        )
        add(
            f"3.3_building_height_max_coverage_{phase.lower()}",
            "Results 3.3",
            f"BUILDING_HEIGHT maximum absolute coverage change {expected} in {phase.lower()}",
            "04_relationship_robustness_profile.csv",
            "max_abs_coverage_delta",
            f"phase == {phase}; relationship == BUILDING_HEIGHT",
            "frozen maximum absolute coverage delta",
            expected,
            (lambda ph=phase: float(_profile_row(prof, ph, "BUILDING_HEIGHT")["max_abs_coverage_delta"])),
            EXACT_TOL,
        )

    exploration_coverage = prof.loc[prof["phase"] == "EXPLORATION", "median_abs_coverage_delta"]
    validation_coverage = prof.loc[prof["phase"] == "VALIDATION", "median_abs_coverage_delta"]
    add(
        "3.3_exploration_coverage_range",
        "Results 3.3",
        "Median absolute coverage changes remained between approximately 0.012 and 0.023 in exploration",
        "04_relationship_robustness_profile.csv",
        "median_abs_coverage_delta",
        "phase == EXPLORATION (3 of 6 rows)",
        "min and max of the exploration median absolute coverage changes",
        "[0.012, 0.023]",
        lambda: "[{}, {}]".format(
            round(float(exploration_coverage.min()), 3), round(float(exploration_coverage.max()), 3)
        ),
        DISPLAY_TOL,
    )
    add(
        "3.3_validation_coverage_range",
        "Results 3.3",
        "Median absolute coverage changes remained between approximately 0.013 and 0.017 in validation",
        "04_relationship_robustness_profile.csv",
        "median_abs_coverage_delta",
        "phase == VALIDATION (3 of 6 rows)",
        "min and max of the validation median absolute coverage changes",
        "[0.013, 0.017]",
        lambda: "[{}, {}]".format(
            round(float(validation_coverage.min()), 3), round(float(validation_coverage.max()), 3)
        ),
        DISPLAY_TOL,
    )

    def direction_row(city: str, scale: str, selection: str, pair: str) -> pd.Series:
        hit = direction[
            (direction["city_id"] == city)
            & (direction["scale"] == scale)
            & (direction["selection"] == selection)
            & (direction["pair_id"] == pair)
        ]
        if len(hit) != 1:
            raise AssertionError(
                f"expected one validation row for {city}/{scale}/{selection}/{pair}"
            )
        return hit.iloc[0]

    p005_all_5km = float(direction_row("P005", "5km", "ALL", "BUILDING_HEIGHT")["spearman_rho"])
    p005_c80_5km = float(
        direction_row("P005", "5km", "COVERAGE_80", "BUILDING_HEIGHT")["spearman_rho"]
    )
    add(
        "3.3_p005_5km_spearman_all",
        "Results 3.3",
        "P005 5 km Spearman coefficient 0.730 under ALL windows",
        "validation_correlations.csv",
        "spearman_rho",
        "city_id == P005; scale == 5km; selection == ALL; pair_id == BUILDING_HEIGHT",
        "frozen validation correlation coefficient",
        0.730,
        lambda: p005_all_5km,
        DISPLAY_TOL,
    )
    add(
        "3.3_p005_5km_spearman_c80",
        "Results 3.3",
        "P005 5 km Spearman coefficient 0.450 under Coverage >= 80%",
        "validation_correlations.csv",
        "spearman_rho",
        "city_id == P005; scale == 5km; selection == COVERAGE_80; pair_id == BUILDING_HEIGHT",
        "frozen validation correlation coefficient",
        0.450,
        lambda: p005_c80_5km,
        DISPLAY_TOL,
    )
    add(
        "3.3_p005_5km_absolute_change",
        "Results 3.3",
        "P005 5 km absolute change 0.280 between ALL and Coverage >= 80%",
        "validation_correlations.csv",
        "spearman_rho",
        "city_id == P005; scale == 5km; pair_id == BUILDING_HEIGHT",
        "abs(spearman_rho(COVERAGE_80) - spearman_rho(ALL))",
        0.280,
        lambda: abs(p005_all_5km - p005_c80_5km),
        DISPLAY_TOL,
    )

    # ---------------- Results 3.4 ----------------
    for phase, expected in (("EXPLORATION", 0.208776326869), ("VALIDATION", 0.237048499457)):
        subset = prof[prof["phase"] == phase]
        add(
            f"3.4_building_height_median_metric_{phase.lower()}",
            "Results 3.4",
            f"BUILDING_HEIGHT median absolute metric/weighting difference {expected} in {phase.lower()}",
            "04_relationship_robustness_profile.csv",
            "median_abs_metric_delta",
            f"phase == {phase}; relationship == BUILDING_HEIGHT",
            "frozen median absolute metric delta",
            expected,
            (lambda ph=phase: float(_profile_row(prof, ph, "BUILDING_HEIGHT")["median_abs_metric_delta"])),
            EXACT_TOL,
        )
        add(
            f"3.4_building_height_largest_metric_{phase.lower()}",
            "Results 3.4",
            f"BUILDING_HEIGHT showed the largest median absolute metric/weighting difference in {phase.lower()}",
            "04_relationship_robustness_profile.csv",
            "median_abs_metric_delta",
            f"phase == {phase} (3 of 6 rows)",
            "argmax(median_abs_metric_delta)",
            "BUILDING_HEIGHT",
            lambda s=subset: str(s.sort_values("median_abs_metric_delta", ascending=False).iloc[0]["relationship"]),
            0.0,
        )

    for relationship, expected in (("BUILDING_ROAD", 0.0340193877405), ("ROAD_HEIGHT", 0.0805404459835)):
        add(
            f"3.4_{relationship}_validation_median_metric",
            "Results 3.4",
            f"{relationship} validation median absolute metric/weighting difference {expected}",
            "04_relationship_robustness_profile.csv",
            "median_abs_metric_delta",
            f"phase == VALIDATION; relationship == {relationship}",
            "frozen median absolute metric delta",
            expected,
            (lambda rel=relationship: float(_profile_row(prof, "VALIDATION", rel)["median_abs_metric_delta"])),
            EXACT_TOL,
        )

    p005_1km_all = direction_row("P005", "1km", "ALL", "BUILDING_HEIGHT")
    p005_1km_c80 = direction_row("P005", "1km", "COVERAGE_80", "BUILDING_HEIGHT")
    add(
        "3.4_p005_1km_all_spearman",
        "Results 3.4",
        "P005 1 km ALL Spearman rho 0.664",
        "validation_correlations.csv",
        "spearman_rho",
        "city_id == P005; scale == 1km; selection == ALL; pair_id == BUILDING_HEIGHT",
        "frozen validation correlation coefficient",
        0.664,
        lambda: float(p005_1km_all["spearman_rho"]),
        DISPLAY_TOL,
    )
    add(
        "3.4_p005_1km_all_weighted",
        "Results 3.4",
        "P005 1 km ALL weighted Pearson r 0.289",
        "validation_correlations.csv",
        "weighted_pearson_r",
        "city_id == P005; scale == 1km; selection == ALL; pair_id == BUILDING_HEIGHT",
        "frozen validation correlation coefficient",
        0.289,
        lambda: float(p005_1km_all["weighted_pearson_r"]),
        DISPLAY_TOL,
    )
    add(
        "3.4_p005_1km_all_metric_difference",
        "Results 3.4",
        "P005 1 km ALL absolute metric difference 0.375",
        "validation_correlations.csv",
        "spearman_rho; weighted_pearson_r",
        "city_id == P005; scale == 1km; selection == ALL; pair_id == BUILDING_HEIGHT",
        "abs(weighted_pearson_r - spearman_rho)",
        0.375,
        lambda: abs(float(p005_1km_all["spearman_rho"]) - float(p005_1km_all["weighted_pearson_r"])),
        DISPLAY_TOL,
    )
    add(
        "3.4_p005_1km_c80_metric_difference",
        "Results 3.4",
        "P005 1 km Coverage >= 80% absolute metric difference 0.348",
        "validation_correlations.csv",
        "spearman_rho; weighted_pearson_r",
        "city_id == P005; scale == 1km; selection == COVERAGE_80; pair_id == BUILDING_HEIGHT",
        "abs(weighted_pearson_r - spearman_rho)",
        0.348,
        lambda: abs(float(p005_1km_c80["spearman_rho"]) - float(p005_1km_c80["weighted_pearson_r"])),
        DISPLAY_TOL,
    )

    # cross-checks against Supplementary Figure S1 source values
    add(
        "3.3_s1_p005_5km_signed_coverage_delta",
        "Supplementary Figure S1",
        "P005 5 km signed coverage delta for BUILDING_HEIGHT Spearman",
        "03_scale_coverage_metric_sensitivity.csv",
        "signed_delta",
        "phase=VALIDATION; city_id=P005; relationship=BUILDING_HEIGHT; dimension=COVERAGE; "
        "conditioning=5km; metric=SPEARMAN_RHO",
        "frozen signed coverage delta",
        -0.279587,
        lambda: _sensitivity_value(
            sens, "VALIDATION", "P005", "BUILDING_HEIGHT", "COVERAGE", "5km", "SPEARMAN_RHO"
        ),
        EXACT_TOL,
    )
    add(
        "3.4_s1_p005_1km_signed_metric_delta",
        "Supplementary Figure S1",
        "P005 1 km ALL signed metric delta for BUILDING_HEIGHT",
        "03_scale_coverage_metric_sensitivity.csv",
        "signed_delta",
        "phase=VALIDATION; city_id=P005; relationship=BUILDING_HEIGHT; dimension=METRIC; "
        "conditioning=1km|ALL; metric=SPEARMAN_VS_WEIGHTED_PEARSON",
        "frozen signed metric delta",
        -0.375157,
        lambda: _sensitivity_value(
            sens,
            "VALIDATION",
            "P005",
            "BUILDING_HEIGHT",
            "METRIC",
            "1km|ALL",
            "SPEARMAN_VS_WEIGHTED_PEARSON",
        ),
        EXACT_TOL,
    )

    return checks


def evaluate(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for check in checks:
        expected = check["expected_value"]
        produced = check["reproduced_value"]
        tolerance = check["tolerance"]

        if isinstance(expected, (int, float)) and isinstance(produced, (int, float)):
            status = "PASS" if abs(float(expected) - float(produced)) <= tolerance else "FAIL"
        else:
            status = "PASS" if str(expected) == str(produced) else "FAIL"
        check["status"] = status
    return checks


def main() -> int:
    paths.ensure_output_dirs()

    direction = pd.read_csv(_resolve_reproduced_or_frozen("validation_direction_checks.csv"), encoding="utf-8-sig")
    sign = pd.read_csv(paths.REPRODUCED_TABLES_DIR / "01_directional_concordance.csv", encoding="utf-8-sig")
    mag = pd.read_csv(
        paths.REPRODUCED_TABLES_DIR / "02_exploration_validation_magnitude_summary.csv", encoding="utf-8-sig"
    )
    sens = pd.read_csv(
        paths.REPRODUCED_TABLES_DIR / "03_scale_coverage_metric_sensitivity.csv", encoding="utf-8-sig"
    )
    prof = pd.read_csv(
        paths.REPRODUCED_TABLES_DIR / "04_relationship_robustness_profile.csv", encoding="utf-8-sig"
    )

    checks = evaluate(build_checks(direction, sign, mag, sens, prof))
    failed = [c for c in checks if c["status"] != "PASS"]

    report = {
        "step": "06_verify_manuscript_numbers",
        "status": "PASS" if not failed else "FAIL",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_claim_ids": [c["claim_id"] for c in failed],
        "checks": checks,
    }
    write_json(paths.REPRODUCED_QC_DIR / "manuscript_number_check.json", report)

    mapping = pd.DataFrame(
        [
            {
                "manuscript_location": c["manuscript_location"],
                "reported_claim": c["reported_claim"],
                "source_file": c["source_file"],
                "source_columns": c["source_columns"],
                "filter": c["filter"],
                "calculation": c["calculation"],
                "expected_value": c["expected_value"],
                "reproduced_value": c["reproduced_value"],
                "status": c["status"],
            }
            for c in checks
        ]
    )
    # Reproduction writes ONLY inside outputs_reproduced/. The distributed
    # traceability map (manuscript_mapping/manuscript_result_map.csv) is static
    # package content and is never rewritten during a verification run; the
    # freshly derived map is compared against it instead.
    reproduced_map_path = write_csv(
        mapping, paths.REPRODUCED_QC_DIR / "manuscript_result_map_reproduced.csv"
    )
    distributed_map_path = paths.MANUSCRIPT_MAPPING_DIR / "manuscript_result_map.csv"
    static_map_comparison = (
        compare_to_frozen(reproduced_map_path, distributed_map_path)
        if distributed_map_path.is_file()
        else {
            "status": "FAIL",
            "detail": "distributed manuscript_result_map.csv is missing",
        }
    )

    # Relative paths are recorded in POSIX form so the report is identical on
    # Windows and Linux.
    report["reproduced_map_file"] = reproduced_map_path.relative_to(paths.PACKAGE_ROOT).as_posix()
    report["distributed_map_file"] = distributed_map_path.relative_to(paths.PACKAGE_ROOT).as_posix()
    report["static_map_comparison"] = static_map_comparison
    report["static_map_match"] = static_map_comparison["status"] == "PASS"
    if not report["static_map_match"]:
        report["status"] = "FAIL"
    write_json(paths.REPRODUCED_QC_DIR / "manuscript_number_check.json", report)

    print("=== STEP 06 - MANUSCRIPT NUMBER CHECKS ===")
    print(f"checks total           : {report['checks_total']}")
    print(f"checks passed          : {report['checks_passed']}")
    print(f"checks failed          : {report['checks_failed']}")
    for check in failed:
        print(
            f"FAIL  {check['claim_id']}: expected {check['expected_value']!r}, "
            f"reproduced {check['reproduced_value']!r}"
        )
    print(f"distributed traceability map match: {report['static_map_match']}")
    print(f"MANUSCRIPT_NUMBER_STATUS: {report['status']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
