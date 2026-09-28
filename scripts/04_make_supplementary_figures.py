"""Step 04 - regenerate Supplementary Figure S1 and Supplementary Figure S2.

  * Supplementary Figure S1 = city-level signed sensitivity structure
    (frozen stem: Fig_S1_city_level_sensitivity)
  * Supplementary Figure S2 = cross-city coefficient dispersion
    (frozen stem: Fig_S2_cross_city_dispersion)

This step also finalises the figure-level provenance records (captions, plotted
value audit, figure QC and figure manifest).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Never leave interpreter caches inside the distributed package tree, even when
# this script is invoked directly rather than through run_all.py.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import paths  # noqa: E402
from utils import wp05d_figure_engine as engine  # noqa: E402
from utils.hashing import sha256_file  # noqa: E402
from utils.reporting import read_json, write_json  # noqa: E402

STAGE_FILE = "figure_stage_main.json"


def main() -> int:
    paths.ensure_output_dirs()
    output_dir = paths.REPRODUCED_FIGURES_DIR
    qc_dir = paths.REPRODUCED_QC_DIR

    stage = read_json(qc_dir / STAGE_FILE)

    preflight = engine.run_preflight()
    engine.apply_style()

    _sign, mag, sens, prof = engine.load_inputs()

    s1_paths, s1_entries, s1_limits = engine.make_figure_s1(sens, output_dir)
    s2_paths, s2_entries, s2_params = engine.make_figure_s2(mag, output_dir)

    engine_path = Path(engine.__file__).resolve()
    sha_before = sha256_file(engine_path)

    figure_files = {
        "Fig_main_1_direction_magnitude": {
            ext: Path(p) for ext, p in stage["figure_files"]["Fig_main_1_direction_magnitude"].items()
        },
        "Fig_main_2_robustness_structure": {
            ext: Path(p) for ext, p in stage["figure_files"]["Fig_main_2_robustness_structure"].items()
        },
        "Fig_S1_city_level_sensitivity": {ext: Path(p) for ext, p in s1_paths.items()},
        "Fig_S2_cross_city_dispersion": {ext: Path(p) for ext, p in s2_paths.items()},
    }

    entries = list(stage["audit_entries"])
    entries.extend(s1_entries)
    entries.extend(s2_entries)
    entries.extend(
        [
            {
                "figure": "Figure 3",
                "panel": "shared colour scale",
                "source_file": engine.F_PROF,
                "source_columns": [
                    "median_abs_scale_delta",
                    "median_abs_coverage_delta",
                    "median_abs_metric_delta",
                ],
                "row_filter": "both phases (6 of 6 rows)",
                "row_count_used": int(len(prof)),
                "any_new_metric_computed": False,
                "presentation_parameters": stage["figure2_presentation"],
            },
            {
                "figure": "Supplementary Figure S2",
                "panel": "x-axis limits",
                "source_file": engine.F_MAG,
                "source_columns": ["exploration_range", "validation_range"],
                "row_filter": "all 24 analytical conditions across the three relationships",
                "row_count_used": int(len(mag)),
                "any_new_metric_computed": False,
                "presentation_parameters": s2_params,
            },
        ]
    )

    source_hashes = {name: sha256_file(engine.SOURCE_DIR / name) for name in engine.ANALYTICAL_FILES}
    for name, digest in source_hashes.items():
        expected = next(
            (
                entry["sha256"].upper()
                for entry in preflight["manifest"].get("generated_outputs", [])
                if entry["file_name"] == name
            ),
            None,
        )
        if expected is not None and expected != digest:
            raise RuntimeError(f"frozen input changed during figure production: {name}")

    audit_path = engine.write_data_audit(entries, qc_dir, engine.SOURCE_DIR)
    captions_path = engine.write_captions(
        qc_dir,
        tuple(stage["shared_xlim"]),
        stage["figure2_presentation"]["vmax"],
        s1_limits,
    )

    sha_after = sha256_file(engine_path)

    qc_path = engine.write_qc(
        qc_dir, preflight["qc"], sha_before, sha_after, figure_files, source_hashes
    )
    figure_qc = json.loads(Path(qc_path).read_text(encoding="utf-8"))["FIGURE_QC"]

    produced_paths = []
    for mapping in figure_files.values():
        produced_paths.extend(mapping[ext] for ext in ("png", "pdf", "svg"))
    produced_paths.extend([audit_path, captions_path, qc_path])

    manifest_path = engine.write_manifest(
        qc_dir,
        produced_paths,
        engine_path,
        sha_before,
        sha_after,
        source_hashes,
        figure_qc,
    )

    report = {
        "step": "04_make_supplementary_figures",
        "status": "PASS" if figure_qc == "PASS" else "FAIL",
        "figure_qc": figure_qc,
        "figures": {
            "Supplementary Figure S1": {
                "stem": "Fig_S1_city_level_sensitivity",
                "assessment_title": "City-level signed sensitivity structure",
                "files": {ext: str(Path(p).relative_to(paths.PACKAGE_ROOT)) for ext, p in s1_paths.items()},
            },
            "Supplementary Figure S2": {
                "stem": "Fig_S2_cross_city_dispersion",
                "assessment_title": "Cross-city coefficient dispersion",
                "files": {ext: str(Path(p).relative_to(paths.PACKAGE_ROOT)) for ext, p in s2_paths.items()},
            },
        },
        "figure_manifest": str(Path(manifest_path).relative_to(paths.PACKAGE_ROOT)),
        "figure_captions": str(Path(captions_path).relative_to(paths.PACKAGE_ROOT)),
        "figure_data_audit": str(Path(audit_path).relative_to(paths.PACKAGE_ROOT)),
        "figure_qc_report": str(Path(qc_path).relative_to(paths.PACKAGE_ROOT)),
        "figures_generated": len(figure_files),
    }
    write_json(qc_dir / "figure_report.json", report)

    print("=== STEP 04 - SUPPLEMENTARY FIGURES ===")
    for label in ("Supplementary Figure S1", "Supplementary Figure S2"):
        print(f"{label}: {report['figures'][label]['stem']}")
    print(f"figures generated      : {report['figures_generated']}")
    print(f"figure QC              : {figure_qc}")
    print(f"SUPPLEMENTARY_FIGURE_STATUS: {report['status']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
