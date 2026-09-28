"""Step 01, LEVEL B - independent recomputation of the WP-MORPH-05B validation results.

This level re-derives every validation correlation from the frozen WP-MORPH-05A
aggregated validation-window files. Raw 50 m source data are not required.

If the frozen window files are not distributed with the package, the level
reports NOT_INCLUDED_WITH_REASON and the paper-reproduction level (Level A)
still reproduces every manuscript number and figure.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Never leave interpreter caches inside the distributed package tree, even when
# this script is invoked directly rather than through run_all.py.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import paths  # noqa: E402
from utils.reporting import write_json  # noqa: E402
from utils.tables import compare_to_frozen, write_csv  # noqa: E402
from utils.wp05b_engine import reproduce as reproduce_validation  # noqa: E402


def main() -> int:
    paths.ensure_output_dirs()

    windows_1km = paths.VALIDATION_WINDOWS_DIR / "validation_windows_1km.csv"
    windows_5km = paths.VALIDATION_WINDOWS_DIR / "validation_windows_5km.csv"

    if not (windows_1km.is_file() and windows_5km.is_file()):
        report = {
            "step": "01_reproduce_validation",
            "level": "B",
            "status": "NOT_INCLUDED_WITH_REASON",
            "reason": (
                "The frozen WP-MORPH-05A aggregated validation-window files are not "
                "distributed with this package. Level A still reproduces every "
                "manuscript number and figure from the frozen result-level tables."
            ),
        }
        write_json(paths.REPRODUCED_QC_DIR / "level_b_validation_report.json", report)
        print("=== STEP 01 - LEVEL B VALIDATION RECOMPUTATION ===")
        print("LEVEL_B_STATUS: NOT_INCLUDED_WITH_REASON")
        print(report["reason"])
        return 0

    authorized_cities = ["P001", "P003", "P005"]
    products = reproduce_validation(paths.VALIDATION_WINDOWS_DIR, authorized_cities)

    comparisons = {}
    reproduced_files = {}
    for name in (
        "validation_correlations.csv",
        "validation_direction_checks.csv",
        "validation_summary_by_city.csv",
        "validation_hypothesis_summary.csv",
    ):
        written = write_csv(products[name], paths.REPRODUCED_TABLES_DIR / name)
        reproduced_files[name] = str(written.relative_to(paths.PACKAGE_ROOT))
        comparisons[name] = compare_to_frozen(written, paths.VALIDATION_DIR / name)

    counts = products["_classification_counts"].set_index("classification")["count"].to_dict()

    status = "PASS" if all(c["status"] == "PASS" for c in comparisons.values()) else "FAIL"
    exact_bytes = all(c["byte_identical"] for c in comparisons.values())

    report = {
        "step": "01_reproduce_validation",
        "level": "B",
        "status": status,
        "raw_50m_data_read": False,
        "validation_unit_count": 36,
        "classification_counts": {k: int(v) for k, v in counts.items()},
        "byte_identical_to_frozen": exact_bytes,
        "reproduced_files": reproduced_files,
        "comparisons": comparisons,
    }
    write_json(paths.REPRODUCED_QC_DIR / "level_b_validation_report.json", report)

    print("=== STEP 01 - LEVEL B VALIDATION RECOMPUTATION ===")
    print(f"validation units       : {report['validation_unit_count']}")
    print(f"SAME_SIGN              : {report['classification_counts'].get('SAME_SIGN', 0)}")
    print(f"SIGN_REVERSAL          : {report['classification_counts'].get('SIGN_REVERSAL', 0)}")
    print(f"INSUFFICIENT_WINDOWS   : {report['classification_counts'].get('INSUFFICIENT_WINDOWS', 0)}")
    print(f"UNDEFINED              : {report['classification_counts'].get('UNDEFINED', 0)}")
    print(f"byte-identical to frozen: {exact_bytes}")
    for name, comparison in comparisons.items():
        print(f"{comparison['status']}  {name}  (values_match={comparison['values_match']})")
    print(f"LEVEL_B_STATUS: {status}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
