"""Step 00 - input presence, frozen identity and configuration preflight.

Hard gate: if any distributed frozen input is missing, resized or has a
different SHA256 than the recorded expectation, the pipeline stops. The
package never repairs, regenerates or substitutes a frozen input.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Never leave interpreter caches inside the distributed package tree, even when
# this script is invoked directly rather than through run_all.py.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import paths  # noqa: E402
from utils.hashing import read_json, sha256_file  # noqa: E402
from utils.reporting import write_json  # noqa: E402

# Frozen city roster labels. These are record labels only; they take part in no
# computation. The mapping was verified against the frozen canonical city roster
# of the validation-city nomination chain (see REPRODUCIBILITY.md section 5.4).
EXPECTED_CITY_NAMES = {
    "P001": "Beijing",
    "P003": "Guangzhou",
    "P004": "Shenzhen",
    "P005": "Wuhan",
    "P026": "Luoyang",
    "P037": "Xining",
}


def main() -> int:
    paths.ensure_output_dirs()

    expected_hashes = read_json(paths.CONFIG_DIR / "expected_hashes.json")
    config = read_json(paths.CONFIG_DIR / "frozen_analysis_config.json")
    expected_outputs = read_json(paths.CONFIG_DIR / "expected_outputs.json")

    records = []
    failures = []

    for relative_path, spec in sorted(expected_hashes["files"].items()):
        target = paths.PACKAGE_ROOT / relative_path
        exists = target.is_file()
        record = {
            "relative_path": relative_path,
            "role": spec.get("role"),
            "present": exists,
            "expected_size_bytes": spec["size_bytes"],
            "expected_sha256": spec["sha256"],
        }
        if not exists:
            record["status"] = "MISSING"
            failures.append(f"missing frozen input: {relative_path}")
            records.append(record)
            continue

        actual_size = target.stat().st_size
        actual_hash = sha256_file(target)
        record["actual_size_bytes"] = actual_size
        record["actual_sha256"] = actual_hash

        size_ok = actual_size == spec["size_bytes"]
        hash_ok = actual_hash == spec["sha256"]
        record["status"] = "PASS" if (size_ok and hash_ok) else "MISMATCH"

        if not size_ok:
            failures.append(
                f"size mismatch: {relative_path} ({actual_size} != {spec['size_bytes']})"
            )
        if not hash_ok:
            failures.append(f"SHA256 mismatch: {relative_path}")
        records.append(record)

    # --- configuration self-consistency (no scientific rule is modified) ---
    config_checks = {
        "exploration_cities": config["exploration_cities"] == ["P004", "P026", "P037"],
        "validation_cities": config["validation_cities"] == ["P001", "P003", "P005"],
        "scales": config["scales"] == ["1km", "5km"],
        "selections": config["selections"] == ["ALL", "COVERAGE_80"],
        "relationships": config["relationships"]
        == ["BUILDING_ROAD", "BUILDING_HEIGHT", "ROAD_HEIGHT"],
        "metrics": config["metrics"] == ["SPEARMAN_RHO", "WEIGHTED_PEARSON_R"],
        "minimum_pairwise_valid_windows": config["minimum_pairwise_valid_windows"] == 10,
        "expected_sign": config["expected_sign"] == "POSITIVE",
        "expected_validation_unit_count": config["expected_validation_unit_count"] == 36,
        "formal_canu_production_authorized": config["formal_canu_production_authorized"] is False,
        "formal_canu_gates": config["formal_canu_gates"] == "UNCHANGED",
        "new_analysis_allowed": config["new_analysis_allowed"] is False,
        "city_names": config["city_names"] == EXPECTED_CITY_NAMES,
    }
    for name, ok in config_checks.items():
        if not ok:
            failures.append(f"frozen configuration check failed: {name}")

    output_row_checks = {
        name: spec["row_count"] for name, spec in expected_outputs["wp05c_outputs"].items()
    }

    report = {
        "step": "00_preflight",
        "status": "PASS" if not failures else "FAIL",
        "input_hash_status": "PASS" if not failures else "FAIL",
        "files_checked": len(records),
        "expected_output_row_counts": output_row_checks,
        "configuration_checks": config_checks,
        "records": records,
        "failures": failures,
    }
    write_json(paths.REPRODUCED_QC_DIR / "preflight_report.json", report)

    print("=== STEP 00 - PREFLIGHT ===")
    print(f"files checked          : {len(records)}")
    print(f"frozen identity status : {report['input_hash_status']}")
    print(f"configuration status   : {'PASS' if all(config_checks.values()) else 'FAIL'}")
    for failure in failures:
        print(f"FAIL  {failure}")
    print(f"PREFLIGHT_STATUS: {report['status']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
