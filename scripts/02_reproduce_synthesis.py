"""Step 02, LEVEL A - paper-level reproduction of every manuscript number.

The four frozen WP-MORPH-05C synthesis tables are recomputed from the frozen
result-level inputs (WP-MORPH-03 exploration coefficients and WP-MORPH-05B
validation coefficients). No coefficient is re-estimated and no raw data are
read at this level.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Never leave interpreter caches inside the distributed package tree, even when
# this script is invoked directly rather than through run_all.py.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import paths  # noqa: E402
from utils.hashing import sha256_file  # noqa: E402
from utils.reporting import write_json  # noqa: E402
from utils.tables import compare_to_frozen, write_csv  # noqa: E402
from utils.wp05c_engine import reproduce as reproduce_synthesis  # noqa: E402


def main() -> int:
    paths.ensure_output_dirs()

    products = reproduce_synthesis(
        paths.EXPLORATION_DIR / "pairwise_relations.csv",
        paths.VALIDATION_DIR / "validation_correlations.csv",
        paths.VALIDATION_DIR / "validation_direction_checks.csv",
    )

    comparisons = {}
    reproduced_files = {}
    for name in (
        "01_directional_concordance.csv",
        "02_exploration_validation_magnitude_summary.csv",
        "03_scale_coverage_metric_sensitivity.csv",
        "04_relationship_robustness_profile.csv",
    ):
        written = write_csv(products[name], paths.REPRODUCED_TABLES_DIR / name)
        reproduced_files[name] = str(written.relative_to(paths.PACKAGE_ROOT))
        comparisons[name] = compare_to_frozen(written, paths.SYNTHESIS_DIR / name)

    qc = products["_qc"].set_index("metric")["value"].to_dict()

    directional = products["01_directional_concordance.csv"]
    directional_ok = (
        int(directional["same_sign_count"].sum()) == 36
        and int(directional["sign_reversal_count"].sum()) == 0
        and int(directional["insufficient_count"].sum()) == 0
        and int(directional["undefined_count"].sum()) == 0
    )

    status = (
        "PASS"
        if directional_ok and all(c["status"] == "PASS" for c in comparisons.values())
        else "FAIL"
    )

    report = {
        "step": "02_reproduce_synthesis",
        "level": "A",
        "status": status,
        "coefficients_reestimated": False,
        "raw_50m_data_read": False,
        "validation_unit_count": int(qc["validation_unit_count"]),
        "same_sign_units": int(qc["same_sign_units"]),
        "sign_reversal_units": int(qc["sign_reversal_units"]),
        "insufficient_windows_units": int(qc["insufficient_windows_units"]),
        "undefined_units": int(qc["undefined_units"]),
        "canonical_coefficient_rows": int(qc["canonical_coefficient_rows"]),
        "byte_identical_to_frozen": all(c["byte_identical"] for c in comparisons.values()),
        "reproduced_files": reproduced_files,
        "reproduced_hashes": {
            name: sha256_file(paths.REPRODUCED_TABLES_DIR / name) for name in reproduced_files
        },
        "comparisons": comparisons,
    }
    write_json(paths.REPRODUCED_QC_DIR / "level_a_synthesis_report.json", report)

    print("=== STEP 02 - LEVEL A PAPER REPRODUCTION ===")
    print(f"validation units       : {report['validation_unit_count']}")
    print(f"directional SAME_SIGN  : {report['same_sign_units']} / {report['validation_unit_count']}")
    print(f"canonical coefficient rows: {report['canonical_coefficient_rows']}")
    print(f"coefficients re-estimated : {report['coefficients_reestimated']}")
    for name, comparison in comparisons.items():
        print(
            f"{comparison['status']}  {name}  "
            f"(rows={comparison['row_count_reproduced']}, "
            f"byte_identical={comparison['byte_identical']})"
        )
    print(f"LEVEL_A_STATUS: {status}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
