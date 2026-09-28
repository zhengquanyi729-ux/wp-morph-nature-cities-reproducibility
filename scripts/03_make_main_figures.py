"""Step 03 - regenerate manuscript Figure 2 and Figure 3.

Both figures are produced by the frozen WP-MORPH-05D figure logic, retained
verbatim in ``scripts/utils/wp05d_figure_engine.py`` and restricted to the
frozen result-level synthesis tables distributed with this package.

  * Figure 2 = directional reproducibility and exploration-validation
    magnitude concordance (frozen stems: Fig_main_1_direction_magnitude)
  * Figure 3 = relationship-specific robustness structure
    (frozen stem: Fig_main_2_robustness_structure)

Outputs: 600 dpi PNG, PDF and SVG in outputs_reproduced/figures/.
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
from utils.reporting import write_json  # noqa: E402

STAGE_FILE = "figure_stage_main.json"


def main() -> int:
    paths.ensure_output_dirs()
    output_dir = paths.REPRODUCED_FIGURES_DIR
    qc_dir = paths.REPRODUCED_QC_DIR

    preflight = engine.run_preflight()
    engine.apply_style()

    sign, mag, sens, prof = engine.load_inputs()

    fig2_paths, fig2_entries = engine.make_figure1(sign, mag, output_dir)
    fig3_paths, fig3_entries, fig3_params = engine.make_figure2(prof, output_dir)

    xlim = engine.shared_xlim(mag)

    stage = {
        "step": "03_make_main_figures",
        "status": "PASS",
        "figures": {
            "Figure 2": {
                "stem": "Fig_main_1_direction_magnitude",
                "assessment_title": "Directional reproducibility and magnitude concordance",
                "files": {ext: str(Path(p).relative_to(paths.PACKAGE_ROOT)) for ext, p in fig2_paths.items()},
            },
            "Figure 3": {
                "stem": "Fig_main_2_robustness_structure",
                "assessment_title": "Relationship-specific robustness structure",
                "files": {ext: str(Path(p).relative_to(paths.PACKAGE_ROOT)) for ext, p in fig3_paths.items()},
            },
        },
        "figure_files": {
            "Fig_main_1_direction_magnitude": {
                ext: str(Path(p)) for ext, p in fig2_paths.items()
            },
            "Fig_main_2_robustness_structure": {
                ext: str(Path(p)) for ext, p in fig3_paths.items()
            },
        },
        "audit_entries": [*fig2_entries, *fig3_entries],
        "shared_xlim": list(xlim),
        "figure2_presentation": fig3_params,
        "source_files_verified": sorted(engine.ANALYTICAL_FILES),
    }
    write_json(qc_dir / STAGE_FILE, stage)

    print("=== STEP 03 - MAIN FIGURES ===")
    for label in ("Figure 2", "Figure 3"):
        print(f"{label}: {stage['figures'][label]['stem']}")
    print("formats: png (600 dpi), pdf, svg")
    print("MAIN_FIGURE_STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
