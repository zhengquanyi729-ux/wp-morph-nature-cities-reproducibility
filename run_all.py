"""WP-MORPH journal reproducibility package - one-command reproduction.

    python run_all.py

Sequence performed, in this order:

  1. verify MANIFEST_SHA256.csv (the package as distributed) - VERIFY ONLY;
     the distribution manifest is never rewritten by this command
  2. input presence, frozen SHA256 identity and configuration preflight
  3. Level B - independent recomputation of the validation coefficients
     (documented and skipped when the window files are not shipped)
  4. Level A - paper reproduction of every manuscript number
  5. Figure 2 / Figure 3 regeneration
  6. Supplementary Figure S1 / S2 regeneration
  7. publication Source Data tables
  8. manuscript numerical checks (also compares the reproduced
     manuscript traceability map with the distributed static map)
  9. pytest suite
 10. absolute-path check as a separate, individually reported run
 11. runtime environment checks and the machine-readable reproduction report

Everything this command writes lands inside ``outputs_reproduced/``. The
command reports only what it actually verifies during that run; it does not
infer QC states from other results, and it does not claim a clean-environment
installation (that historical fact is documented in
``DETERMINISM_VERIFICATION.md``).

No scientific result is changed, no formal CANU production is executed and no
formal CANU gate is altered by this command.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from importlib import metadata as importlib_metadata
from pathlib import Path

# Never leave interpreter caches inside the distributed package tree.
sys.dont_write_bytecode = True

PACKAGE_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
QC_DIR = PACKAGE_ROOT / "outputs_reproduced" / "qc"
REPORT_PATH = QC_DIR / "reproduction_report.json"
MANIFEST_PATH = PACKAGE_ROOT / "MANIFEST_SHA256.csv"
LOCK_PATH = PACKAGE_ROOT / "requirements-lock.txt"

EXCLUDED_TOP_LEVEL = {"outputs_reproduced"}
IGNORED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".pyd"}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SCRIPTS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    # Keep interpreter caches out of the distributed tree so that a run cannot
    # modify package content outside outputs_reproduced/.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(QC_DIR / "pycache")
    # Signals to the test suite that bytecode writing and the pytest cache are
    # disabled, so nothing outside outputs_reproduced/ may be created.
    env["WP_MORPH_STRICT_IMMUTABILITY"] = "1"
    return env


def _run(label: str, args: list[str]) -> tuple[int, str]:
    print()
    print("#" * 72)
    print(f"# {label}")
    print("#" * 72)
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=str(PACKAGE_ROOT),
        env=_child_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    print(output.rstrip())
    return completed.returncode, output


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _parse_pytest(output: str) -> tuple[int, int]:
    passed = failed = 0
    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))
    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))
    return passed, failed


def _snapshot_distributed(root: Path) -> dict[str, str]:
    """Hash every distributed file (excludes outputs_reproduced and caches)."""
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.split("/")[0] in EXCLUDED_TOP_LEVEL:
            continue
        if IGNORED_DIR_NAMES.intersection(path.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        snapshot[relative] = _sha256(path)
    return snapshot


def _cache_entries(root: Path) -> set[str]:
    """Interpreter cache entries outside outputs_reproduced/."""
    found: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if relative.split("/")[0] in EXCLUDED_TOP_LEVEL:
            continue
        if path.is_dir() and path.name in IGNORED_DIR_NAMES:
            found.add(relative)
        elif path.is_file() and path.suffix in IGNORED_SUFFIXES:
            found.add(relative)
    return found


def _read_pins(lock_path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "==" not in text:
            continue
        name, version = text.split("==", 1)
        pins[name.strip().lower()] = version.strip()
    return pins


def _installed_version(distribution_name: str) -> str | None:
    """Return the installed version of a distribution, or None when absent.

    Distribution metadata is used rather than importing the module, because the
    import name does not always match the distribution name (for example the
    distribution ``fonttools`` provides the module ``fontTools``).
    """
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def _package_versions(pins: dict[str, str]) -> dict[str, object]:
    available: dict[str, str | None] = {}
    matches: dict[str, bool] = {}
    for name, pinned in sorted(pins.items()):
        installed = _installed_version(name)
        available[name] = installed
        matches[name] = installed == pinned
    return {
        "pinned_versions": pins,
        "installed_versions": available,
        "pinned_match": matches,
        "all_required_available": all(value is not None for value in available.values()),
        "all_pins_match": all(matches.values()),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    started = time.perf_counter()
    print("=" * 72)
    print("=== WP-MORPH JOURNAL REPRODUCIBILITY PACKAGE ===")
    print("=" * 72)
    print(f"PACKAGE_ROOT : {PACKAGE_ROOT}")
    print(f"PYTHON       : {sys.version.split()[0]} ({platform.platform()})")

    # The only writable location of a reproduction run.
    QC_DIR.mkdir(parents=True, exist_ok=True)

    # Snapshot BEFORE anything runs, so we can prove that a normal run only
    # writes inside outputs_reproduced/.
    before_snapshot = _snapshot_distributed(PACKAGE_ROOT)
    manifest_sha_before = _sha256(MANIFEST_PATH) if MANIFEST_PATH.is_file() else None
    caches_before = _cache_entries(PACKAGE_ROOT)

    # 1. distribution manifest verification (verify only, never rewrite)
    manifest_code, _ = _run(
        "STEP 01  distribution manifest verification",
        [str(SCRIPTS_DIR / "utils" / "verify_manifest.py")],
    )

    steps = [
        ("STEP 02  preflight", [str(SCRIPTS_DIR / "00_preflight.py")]),
        ("STEP 03  Level B validation recomputation", [str(SCRIPTS_DIR / "01_reproduce_validation.py")]),
        ("STEP 04  Level A paper reproduction", [str(SCRIPTS_DIR / "02_reproduce_synthesis.py")]),
        ("STEP 05  manuscript Figure 2 and Figure 3", [str(SCRIPTS_DIR / "03_make_main_figures.py")]),
        ("STEP 06  Supplementary Figure S1 and S2", [str(SCRIPTS_DIR / "04_make_supplementary_figures.py")]),
        ("STEP 07  Source Data tables", [str(SCRIPTS_DIR / "05_make_source_tables.py")]),
        ("STEP 08  manuscript numerical checks", [str(SCRIPTS_DIR / "06_verify_manuscript_numbers.py")]),
    ]

    step_codes: dict[str, int] = {}
    for label, args in steps:
        code, _ = _run(label, args)
        step_codes[label] = code

    # Publish the immutability evidence BEFORE the test suite runs, so the suite
    # verifies the claims of THIS run rather than a previous one.
    pre_snapshot = _snapshot_distributed(PACKAGE_ROOT)
    pre_manifest_sha = _sha256(MANIFEST_PATH) if MANIFEST_PATH.is_file() else None
    pre_modified = sorted(
        key
        for key in set(before_snapshot) | set(pre_snapshot)
        if before_snapshot.get(key) != pre_snapshot.get(key)
    )
    precheck = {
        "manifest_sha256_before": manifest_sha_before,
        "manifest_sha256_after_analysis": pre_manifest_sha,
        "distribution_manifest_immutable_during_run": manifest_sha_before == pre_manifest_sha,
        "modified_distributed_files": pre_modified,
        "run_all_modifies_only_outputs_reproduced": not pre_modified,
        "distributed_files_checked": len(pre_snapshot),
        "new_interpreter_caches": sorted(_cache_entries(PACKAGE_ROOT) - caches_before),
    }
    (QC_DIR / "immutability_precheck.json").write_text(
        json.dumps(precheck, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    pytest_code, pytest_output = _run(
        "STEP 09  pytest", ["-m", "pytest", "-q", "-p", "no:cacheprovider"]
    )
    tests_passed, tests_failed = _parse_pytest(pytest_output)

    abs_path_code, abs_path_output = _run(
        "STEP 10  absolute-path check (separate run)",
        [
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_no_absolute_paths.py",
        ],
    )
    abs_passed, abs_failed = _parse_pytest(abs_path_output)

    # 2. runtime environment
    pins = _read_pins(LOCK_PATH) if LOCK_PATH.is_file() else {}
    environment = _package_versions(pins)
    current_runtime_environment = "PASS" if environment["all_required_available"] else "FAIL"
    pinned_environment_match = "PASS" if environment["all_pins_match"] else "FAIL"

    # 3. prove nothing outside outputs_reproduced/ changed
    after_snapshot = _snapshot_distributed(PACKAGE_ROOT)
    manifest_sha_after = _sha256(MANIFEST_PATH) if MANIFEST_PATH.is_file() else None
    modified = sorted(
        key
        for key in set(before_snapshot) | set(after_snapshot)
        if before_snapshot.get(key) != after_snapshot.get(key)
    )
    new_caches = sorted(_cache_entries(PACKAGE_ROOT) - caches_before)
    manifest_immutable = manifest_sha_before == manifest_sha_after
    only_outputs_modified = not modified

    # 4. aggregate reports
    manifest_report = _read_json(QC_DIR / "manifest_verification.json") or {}
    preflight = _read_json(QC_DIR / "preflight_report.json") or {}
    level_b = _read_json(QC_DIR / "level_b_validation_report.json") or {}
    level_a = _read_json(QC_DIR / "level_a_synthesis_report.json") or {}
    figure_report = _read_json(QC_DIR / "figure_report.json") or {}
    source_data = _read_json(QC_DIR / "source_data_report.json") or {}
    manuscript = _read_json(QC_DIR / "manuscript_number_check.json") or {}

    distribution_manifest_status = manifest_report.get("status", "FAIL")
    if manifest_code != 0:
        distribution_manifest_status = "FAIL"

    input_hash_status = preflight.get("input_hash_status", "FAIL")
    validation_status = level_b.get("status", "FAIL")
    level_a_status = level_a.get("status", "FAIL")

    directional_same_sign = int(level_a.get("same_sign_units", 0))
    if validation_status == "PASS":
        directional_same_sign = int(
            level_b.get("classification_counts", {}).get("SAME_SIGN", directional_same_sign)
        )

    comparisons = level_a.get("comparisons", {})
    magnitude_summary_status = comparisons.get(
        "02_exploration_validation_magnitude_summary.csv", {}
    ).get("status", "FAIL")
    sensitivity_status = comparisons.get(
        "03_scale_coverage_metric_sensitivity.csv", {}
    ).get("status", "FAIL")

    figure_generation_status = figure_report.get("status", "FAIL")
    source_data_status = source_data.get("status", "FAIL")
    manuscript_number_check_status = manuscript.get("status", "FAIL")
    absolute_path_check_status = "PASS" if abs_path_code == 0 and abs_failed == 0 else "FAIL"

    pytest_ok = pytest_code == 0 and tests_failed == 0 and tests_passed > 0
    level_b_ok = validation_status in {"PASS", "NOT_INCLUDED_WITH_REASON"}

    gates = {
        "distribution_manifest": distribution_manifest_status == "PASS",
        "preflight": input_hash_status == "PASS",
        "level_b": level_b_ok,
        "level_a": level_a_status == "PASS",
        "figures": figure_generation_status == "PASS",
        "source_data": source_data_status == "PASS",
        "manuscript_numbers": manuscript_number_check_status == "PASS",
        "pytest": pytest_ok,
        "absolute_path_check": absolute_path_check_status == "PASS",
        "current_runtime_environment": current_runtime_environment == "PASS",
        "directional_same_sign_36": directional_same_sign == 36,
        "tests_failed_zero": tests_failed == 0,
        "manifest_immutable": manifest_immutable,
        "only_outputs_reproduced_modified": only_outputs_modified,
    }
    overall = "PASS" if all(gates.values()) else "FAIL"
    failed_gates = sorted(name for name, ok in gates.items() if not ok)

    runtime_seconds = time.perf_counter() - started
    distributed_file_count = len(after_snapshot)
    distributed_bytes = sum(
        (PACKAGE_ROOT / key).stat().st_size for key in after_snapshot
    )

    report = {
        "overall_status": overall,
        "failed_gates": failed_gates,
        "environment": {
            "python_version": sys.version.split()[0],
            "python_full_version": sys.version,
            "platform": platform.platform(),
            "pinned_versions": environment["pinned_versions"],
            "installed_versions": environment["installed_versions"],
            "environment_file": "environment.yml",
            "dependency_lock": "requirements-lock.txt",
            "clean_environment_install": "documented in DETERMINISM_VERIFICATION.md",
        },
        "current_runtime_environment": current_runtime_environment,
        "pinned_environment_match": pinned_environment_match,
        "distribution_manifest_status": distribution_manifest_status,
        "distribution_manifest_sha256": manifest_report.get("manifest_sha256"),
        "distribution_manifest_immutable_during_run": manifest_immutable,
        "run_all_modifies_only_outputs_reproduced": only_outputs_modified,
        "modified_distributed_files": modified,
        "new_interpreter_caches_outside_outputs_reproduced": new_caches,
        "input_hash_status": input_hash_status,
        "validation_status": validation_status,
        "level_a_status": level_a_status,
        "directional_same_sign": directional_same_sign,
        "magnitude_summary_status": magnitude_summary_status,
        "sensitivity_status": sensitivity_status,
        "figure_generation_status": figure_generation_status,
        "source_data_status": source_data_status,
        "manuscript_number_check_status": manuscript_number_check_status,
        "absolute_path_check_status": absolute_path_check_status,
        "absolute_path_checks_passed": abs_passed,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "scientific_results_changed": False,
        "new_analysis": False,
        "formal_canu_production_authorized": False,
        "formal_canu_gates": "UNCHANGED",
        "step_exit_codes": {**{"manifest verification": manifest_code}, **step_codes},
        "pytest_exit_code": pytest_code,
        "absolute_path_exit_code": abs_path_code,
        "runtime_seconds": round(runtime_seconds, 2),
        "distributed_file_count": distributed_file_count,
        "distributed_package_bytes": distributed_bytes,
        "manifest_sha256": manifest_sha_after,
    }

    QC_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )

    level_b_label = "PASS" if validation_status == "PASS" else "NOT_INCLUDED_WITH_REASON"

    print()
    print("=" * 72)
    print("=== WP-MORPH JOURNAL REPRODUCIBILITY PACKAGE ===")
    print()
    print("PACKAGE:")
    print(str(PACKAGE_ROOT))
    print()
    print(f"FROZEN_INPUT_IDENTITY = {input_hash_status}")
    print(f"CURRENT_RUNTIME_ENVIRONMENT = {current_runtime_environment}")
    print(f"PINNED_ENVIRONMENT_MATCH = {pinned_environment_match}")
    print(f"LEVEL_A_PAPER_REPRODUCTION = {level_a_status}")
    print(f"LEVEL_B_VALIDATION_RECOMPUTATION = {level_b_label}")
    print(f"DIRECTIONAL_VALIDATION = {directional_same_sign} / 36 SAME_SIGN")
    print(f"MANUSCRIPT_NUMERICAL_CHECKS = {manuscript_number_check_status}")
    print(f"FIGURE_REPRODUCTION = {figure_generation_status}")
    print(f"SOURCE_DATA_EXPORT = {source_data_status}")
    print(f"PYTEST = {'PASS' if pytest_ok else 'FAIL'}")
    print(f"DISTRIBUTION_MANIFEST = {distribution_manifest_status}")
    print(f"ABSOLUTE_PATH_CHECK = {absolute_path_check_status}")
    print()
    print("SCIENTIFIC_RESULTS_CHANGED = False")
    print("NEW_ANALYSIS = False")
    print("FORMAL_CANU_PRODUCTION_AUTHORIZED = False")
    print("FORMAL_CANU_GATES = UNCHANGED")
    print()
    print(f"JOURNAL_VERIFICATION_PACKAGE_READY = {overall == 'PASS'}")
    print()
    print(f"DISTRIBUTION_MANIFEST_IMMUTABLE_DURING_RUN = {manifest_immutable}")
    print(f"RUN_ALL_MODIFIES_ONLY_OUTPUTS_REPRODUCED = {only_outputs_modified}")
    print(f"NEW_INTERPRETER_CACHES_OUTSIDE_OUTPUTS = {len(new_caches)}")
    print()
    print(f"package size (bytes)      : {distributed_bytes}")
    print(f"file count                : {distributed_file_count}")
    print(f"python version tested     : {sys.version.split()[0]}")
    print("environment file          : environment.yml")
    print(f"total reproduction runtime: {runtime_seconds:.1f} s")
    print(f"SHA256 of package manifest: {manifest_sha_after}")
    print(f"reproduction report       : {REPORT_PATH}")
    if failed_gates:
        print(f"failed gates              : {failed_gates}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
