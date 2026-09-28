"""Step 05 - publication-friendly Source Data tables.

Each Source Data file contains exactly the frozen numerical values that are
plotted in the corresponding figure, and nothing else. The tables are derived
from the reproduced WP-MORPH-05C synthesis outputs written by step 02.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Never leave interpreter caches inside the distributed package tree, even when
# this script is invoked directly rather than through run_all.py.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import paths  # noqa: E402
from utils.reporting import write_json  # noqa: E402
from utils.tables import write_csv  # noqa: E402

F_SIGN = "01_directional_concordance.csv"
F_MAG = "02_exploration_validation_magnitude_summary.csv"
F_SENS = "03_scale_coverage_metric_sensitivity.csv"
F_PROF = "04_relationship_robustness_profile.csv"

SOURCE_DATA_NAMES = {
    "fig2": "Source Data Fig. 2.csv",
    "fig3": "Source Data Fig. 3.csv",
    "s1": "Source Data Supplementary Fig. S1.csv",
    "s2": "Source Data Supplementary Fig. S2.csv",
}


def _load(tables_dir: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(tables_dir / name, encoding="utf-8-sig")


def build_fig2(sign: pd.DataFrame, mag: pd.DataFrame) -> pd.DataFrame:
    """Panel A directional counts plus panels B-D magnitude values for Figure 2."""
    magnitude_columns = [
        "exploration_n",
        "exploration_median",
        "exploration_q1",
        "exploration_q3",
        "exploration_min",
        "exploration_max",
        "exploration_range",
        "validation_n",
        "validation_median",
        "validation_q1",
        "validation_q3",
        "validation_min",
        "validation_max",
        "validation_range",
        "median_shift",
        "absolute_median_shift",
    ]

    panel_a = sign.copy()
    panel_a.insert(0, "figure_panel", "a")
    panel_a["scale"] = pd.NA
    panel_a["selection"] = pd.NA
    panel_a["metric"] = pd.NA
    for column in magnitude_columns:
        panel_a[column] = pd.NA

    columns = [
        "figure_panel",
        "relationship",
        "scale",
        "selection",
        "metric",
        "validation_unit_count",
        "same_sign_count",
        "sign_reversal_count",
        "insufficient_count",
        "undefined_count",
        "directional_reproducibility_fraction",
        "exploration_n",
        "exploration_median",
        "exploration_q1",
        "exploration_q3",
        "exploration_min",
        "exploration_max",
        "exploration_range",
        "validation_n",
        "validation_median",
        "validation_q1",
        "validation_q3",
        "validation_min",
        "validation_max",
        "validation_range",
        "median_shift",
        "absolute_median_shift",
    ]

    panels = mag.copy()
    panels.insert(0, "figure_panel", "b-d")
    panels["validation_unit_count"] = pd.NA
    panels["same_sign_count"] = pd.NA
    panels["sign_reversal_count"] = pd.NA
    panels["insufficient_count"] = pd.NA
    panels["undefined_count"] = pd.NA
    panels["directional_reproducibility_fraction"] = pd.NA

    combined = pd.concat([panel_a[columns], panels[columns]], ignore_index=True)
    return combined


def build_s2(mag: pd.DataFrame) -> pd.DataFrame:
    """Cross-city coefficient dispersion plotted in Supplementary Figure S2."""
    return mag[
        [
            "relationship",
            "scale",
            "selection",
            "metric",
            "exploration_range",
            "validation_range",
        ]
    ].copy()


def main() -> int:
    paths.ensure_output_dirs()
    tables_dir = paths.REPRODUCED_TABLES_DIR

    sign = _load(tables_dir, F_SIGN)
    mag = _load(tables_dir, F_MAG)
    sens = _load(tables_dir, F_SENS)
    prof = _load(tables_dir, F_PROF)

    outputs = {
        "fig2": build_fig2(sign, mag),
        "fig3": prof.copy(),
        "s1": sens.copy(),
        "s2": build_s2(mag),
    }

    written = {}
    for key, frame in outputs.items():
        target = write_csv(frame, tables_dir / SOURCE_DATA_NAMES[key])
        written[key] = {
            "file": str(target.relative_to(paths.PACKAGE_ROOT)),
            "row_count": int(len(frame)),
            "column_count": int(frame.shape[1]),
            "columns": list(frame.columns),
        }

    report = {
        "step": "05_make_source_tables",
        "status": "PASS",
        "source_data_files": written,
        "derived_from": {
            "fig2": [F_SIGN, F_MAG],
            "fig3": [F_PROF],
            "s1": [F_SENS],
            "s2": [F_MAG],
        },
    }
    write_json(paths.REPRODUCED_QC_DIR / "source_data_report.json", report)

    print("=== STEP 05 - SOURCE DATA TABLES ===")
    for key, info in written.items():
        print(f"{info['file']}  (rows={info['row_count']}, columns={info['column_count']})")
    print("SOURCE_DATA_STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
