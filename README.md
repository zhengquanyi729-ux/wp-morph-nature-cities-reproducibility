# WP-MORPH — journal reproducibility package

Self-contained reproducibility package for the **WP-MORPH** constrained
exploration–validation analysis of three pairwise urban morphology
relationships (building coverage, road density, conditional building height),
prepared for the *Nature Cities* manuscript submission.

**Release v1.1** — packaging/reproducibility corrections only
(`SCIENTIFIC_RESULTS_CHANGED = False`). The fixes applied in this release are
listed in `DETERMINISM_VERIFICATION.md` §5.

> This package reproduces the manuscript-level morphology validation analyses.
> It does not execute or authorize the formal CANU production pipeline.

---

## 1. Scientific purpose

The study separates three forms of evidence for the reproducibility of an
exploratory spatial relationship:

1. **Directional reproducibility** — does the relationship retain its
   prespecified direction in a separate city set?
2. **Magnitude concordance** — how far do coefficient magnitudes differ between
   the exploration and validation city sets?
3. **Robustness structure** — how does the coefficient respond to spatial scale,
   window-coverage restriction and correlation formulation, and is that
   response structure relationship-specific?

The analytical universe (cities, scales, selections, relationships, metrics,
weights, missing-value handling, minimum valid-window rule and direction
criterion) was frozen **before validation results were opened**. This package
exists so that an external verifier can check that claim against the frozen
inputs directly.

## 2. What can be reproduced

| Level | Scope | Status in this package |
| --- | --- | --- |
| **A — required paper reproduction** | Every manuscript number and all four figures, from frozen result-level inputs | Always available |
| **B — validation recomputation** | Independent recomputation of the validation coefficients from the frozen WP-MORPH-05A validation windows | Included (window files are small enough to distribute) |
| **C — optional raw-data rebuild** | Rebuilding the 50 m grid from upstream releases | Documented only; never executed by `run_all.py` |

Specifically, the package reproduces:

* `validation_correlations.csv`, `validation_direction_checks.csv`,
  `validation_summary_by_city.csv`, `validation_hypothesis_summary.csv`
  (Level B, recomputed from the frozen validation windows)
* `01_directional_concordance.csv`,
  `02_exploration_validation_magnitude_summary.csv`,
  `03_scale_coverage_metric_sensitivity.csv`,
  `04_relationship_robustness_profile.csv` (Level A)
* **Fig. 2** — directional reproducibility and magnitude concordance
* **Fig. 3** — relationship-specific robustness structure
* **Supplementary Fig. S1** — city-level signed sensitivity structure
* **Supplementary Fig. S2** — cross-city coefficient dispersion
* the publication **Source Data** tables for all four figures
* all manuscript numerical claims via automated regression checks

## 3. Folder structure

```
WP_MORPH_Nature_Cities_reproducibility_v1_1/
├── README.md                       this file
├── LICENSE.md
├── CITATION.cff
├── environment.yml                 conda environment definition
├── requirements-lock.txt           exact tested package versions
├── pyproject.toml
├── run_all.py                      ONE-COMMAND REPRODUCTION
├── run_all.bat / run_all.ps1       Windows convenience launchers
├── MANIFEST_SHA256.csv             digest of every distributed file
├── DATA_DICTIONARY.md              definition of every field
├── REPRODUCIBILITY.md              freeze chronology and level structure
├── METHODS_MAPPING.md              manuscript method -> code mapping
├── config/
│   ├── frozen_analysis_config.json frozen scientific universe
│   ├── expected_outputs.json       expected row counts, hashes, anchor values
│   ├── expected_hashes.json        SHA256 of every distributed input
│   └── WP-MORPH-05C_METHOD_CONTRACT_V1.md, WP-MORPH-05C_FREEZE_RECORD.txt
├── data/
│   ├── frozen_inputs/
│   │   ├── exploration/            WP-MORPH-03 frozen result
│   │   ├── validation/             WP-MORPH-05B frozen results
│   │   └── synthesis/              WP-MORPH-05C frozen outputs
│   ├── validation_windows/         WP-MORPH-05A frozen windows (Level B)
│   └── external_sources/README.md  upstream provenance (Level C)
├── scripts/                        00_preflight ... 06_verify_manuscript_numbers
│   └── utils/                      path-independent reproduction engines
├── original_frozen_scripts/        NON-RUNNABLE historical provenance
├── outputs_expected/               frozen reference tables, figures, QC
├── outputs_reproduced/             generated tables, figures, QC
├── tests/                          pytest suite
└── manuscript_mapping/             manuscript_result_map.csv, figure_source_map.csv
```

## 4. System requirements

* 64-bit Windows, macOS or Linux
* Python 3.11–3.13 (Python **3.12.14** was used for the verified run)
* ≈ 60 MB free disk space; no GPU, no geospatial stack, no network access
* `run_all.py` does **not** download anything

Only four third-party packages are required: `numpy`, `pandas`, `matplotlib`
and `pytest`. `scipy`, `pyarrow`, `geopandas`, `shapely`, `rasterio` and
`xarray` are deliberately **not** required — the reproduction pathway operates
entirely on frozen tabular inputs and performs no geospatial, sparse-array or
parquet I/O.

## 5. Installation

Using conda:

```bash
conda env create -f environment.yml
conda activate wp-morph-repro
```

Conda supplies the Python 3.12 interpreter and `pip`; the analysis stack is
then installed from the exact tested pins in `requirements-lock.txt`, so this
environment is byte-for-byte the same package set as the verified pip route.

Using pip only (this is the route used for the verified clean-environment run):

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate on macOS/Linux
python -m pip install -r requirements-lock.txt
```

Both routes produce the identical pinned package set (Python 3.12.14,
numpy 2.4.6, pandas 3.0.5, matplotlib 3.11.1, pytest 9.1.1 and their pinned
transitive dependencies).

## 6. Quick reproduction

```bash
python run_all.py
```

On Windows you may alternatively double-click `run_all.bat` or run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_all.ps1
```

`run_all.py` returns exit code 0 only when every gate passes, and it never
hides an error.

## 7. Tests

```bash
pytest -q
```

The suite covers frozen input identity, validation results, synthesis results,
figure source data, cross-platform CSV byte identity, package immutability
during a run, city-metadata consistency and the absence of absolute paths in
runnable files.

## 8. Expected runtime

The complete `python run_all.py` run was measured at **10.0–10.8 s** across the
verified runs on a single Windows workstation (Python 3.12.14, 64-bit).
`pytest -q` adds under a second when the outputs already exist. Both are
dominated by figure rendering at 600 dpi.

## 9. Expected outputs

```
outputs_reproduced/
├── tables/    validation_* and 01–04 synthesis tables, four Source Data tables
├── figures/   Fig_main_1, Fig_main_2, Fig_S1, Fig_S2 each as PNG/PDF/SVG
└── qc/        manifest verification, preflight, level A, level B, figure,
               source-data and manuscript reports, the reproduced manuscript
               traceability map, figure provenance records, and
               reproduction_report.json
```

`run_all.py` writes **only** inside `outputs_reproduced/`. It verifies
`MANIFEST_SHA256.csv` but never rewrites it, and it never rewrites
`manuscript_mapping/manuscript_result_map.csv`; instead it writes
`outputs_reproduced/qc/manuscript_result_map_reproduced.csv` and compares the
two.

The headline machine-readable result is
`outputs_reproduced/qc/reproduction_report.json`, which must report
`overall_status = "PASS"`, `directional_same_sign = 36`,
`scientific_results_changed = false` and
`formal_canu_production_authorized = false`.

## 10. Exact expected high-level result

**36 / 36 validation conditions retain the expected positive direction.**

All three relationships (`BUILDING_ROAD`, `BUILDING_HEIGHT`, `ROAD_HEIGHT`)
produce 12 of 12 `SAME_SIGN` conditions across two scales and two window
selections, with 0 sign reversals, 0 insufficient-window conditions and 0
undefined coefficient combinations.

## 11. Exploration, validation and frozen synthesis

| | Exploration phase | Validation phase | Frozen synthesis |
| --- | --- | --- | --- |
| Cities | `P004`, `P026`, `P037` | `P001`, `P003`, `P005` | uses both, unchanged |
| Role | generates candidate directional relationships | tests whether those directions survive in a separate city set | compares the two frozen result sets |
| Produced by | WP-MORPH-03 | WP-MORPH-05A → WP-MORPH-05B | WP-MORPH-05C |
| Coefficients | 36 exploration units | 36 validation units | never re-estimated |
| Used in this package | frozen input to Level A | recomputed in Level B, frozen input to Level A | recomputed in Level A |

The synthesis stage is descriptive: it aggregates already frozen coefficients
(medians, quartiles, minimum, maximum, ranges and signed/absolute deltas). It
performs no re-estimation, no inferential testing and no ranking.

## 12. Data provenance

The 50 m morphology grid was derived from Overture Buildings
(release `2026-08-19.0`), Overture Roads (release `2026-08-19.0`) and
GlobalBuildingAtlas `GBA.Height`. Those upstream archives are large and remain
governed by their own licences, so they are referenced rather than bundled; see
`data/external_sources/README.md`. The frozen derived analytical inputs needed
for Levels A and B are bundled and hash-verified.

## 13. Limitations

* The robustness analysis covers two scales, two window selections and two
  correlation formulations. Results describe reproducibility **within this
  frozen analytical universe**, not invariance under every possible spatial
  support or method.
* The 36 validation conditions are repeated analytical conditions within three
  cities. They are not 36 statistically independent city-level replications,
  and no inferential claim is attached to them.
* Figure rendering is regenerated with the tested library versions; plotted
  values are verified to be identical to the frozen analytical outputs, while
  pixel-level bytes may differ because of text rasterisation and embedded
  renderer metadata.
* The upstream raw 50 m data are not redistributed, so Level C is documented
  rather than executable here.

## 14. Authoritative statement

> This package reproduces the manuscript-level morphology validation analyses.
> It does not execute or authorize the formal CANU production pipeline.

```
SCIENTIFIC_RESULTS_CHANGED        = False
NEW_ANALYSIS                      = False
FORMAL_CANU_PRODUCTION_AUTHORIZED = False
FORMAL_CANU_GATES                 = UNCHANGED
```
