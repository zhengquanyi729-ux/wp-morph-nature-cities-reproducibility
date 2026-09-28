# Reproducibility and freeze chronology

> Release **v1.1**. This release is a packaging/reproducibility correction of
> v1.0 only: no scientific result, coefficient, city, scale, selection,
> relationship, metric, weight or threshold was changed. The fixes are listed in
> `DETERMINISM_VERIFICATION.md` §5.

## 1. What this package is

This is a **reproducibility packaging** deliverable. No new analysis was run
to produce it, and no frozen scientific result was changed. The package was
assembled by copying the required frozen inputs and provenance scripts into an
isolated directory and adding path-independent journal-facing drivers.

```
FORMAL_CANU_PRODUCTION_AUTHORIZED = False
FORMAL_CANU_GATES                = UNCHANGED
SCIENTIFIC_RESULTS_CHANGED       = False
NEW_ANALYSIS                     = False
```

## 2. Freeze chronology

| Stage | Work package | What happened | Cities |
| --- | --- | --- | --- |
| 1 | WP-MORPH-01/02/03 | Exploration: the frozen 50 m grid was aggregated to 1 km and 5 km windows and the complete set of three pairwise morphology relationships was quantified. | Exploration: `P004`, `P026`, `P037` |
| 2 | WP-MORPH-04H | Validation-city nomination and method freeze. Candidate cities were screened on identity information only (row counts, SHA-256). The validation cities, the analytical universe, the weighting rules, the missing-value rule, the minimum valid-window rule and the direction criterion were frozen **before** any validation relationship result was opened. | Nomination pool excludes `P004`, `P026`, `P037` |
| 3 | WP-MORPH-05A | Validation window aggregation produced the 1 km and 5 km morphology tables. This stage was prohibited from computing any cross-variable relationship. | `P001`, `P003`, `P005` |
| 4 | WP-MORPH-05B | Frozen relationship analysis applied to the frozen aggregation products. Raw city Parquet files were not accessed. | Validation: `P001`, `P003`, `P005` |
| 5 | WP-MORPH-05C | Read-only concordance synthesis of already frozen result-level exploration and validation tables. No coefficient was re-estimated. | — |
| 6 | WP-MORPH-05D | Presentation-only figure production from the frozen WP-MORPH-05C outputs. | — |

### Design separation

* Exploration generated candidate directional relationships.
* The method was **frozen before validation results were inspected** — i.e. the
  relationships, expected directions, scales, selections, metrics, weights,
  missing-value handling, minimum valid-window rule and direction
  classification were all fixed in advance.
* Validation results were **not** used to change any method.
* WP-MORPH-05C used **frozen result-level inputs only**.
* **No coefficient re-estimation** occurred in WP-MORPH-05C.
* **No p-values** were computed or used, at any stage.
* **No post-hoc replication threshold** was introduced.
* The study is described as *prespecified* / *frozen before validation results
  were opened*. It is **not** described as publicly preregistered, because no
  external public preregistration record exists.

## 3. Recorded identities

### Frozen scripts

| Artefact | SHA256 |
| --- | --- |
| WP-MORPH-05B script (`run_wp_morph05b.py`) | `78E955CCAAA819826C44CEE9E5971B32374DCC9C93559D927F13A1ED9B017A54` |
| WP-MORPH-05C method contract (`WP-MORPH-05C_METHOD_CONTRACT_V1.md`) | `936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3` |
| WP-MORPH-05C script (`run_wp_morph05c_synthesis_v1.py`) | `EA6A883787587A715486B2181ACFB518942003207A38A6CE8E660ED72DB51EDB` |
| WP-MORPH-05C manifest (`manifest.json`) | `4D698A85EA21EA2A8CD7E3697282B6EB67F1310EC7E19E0E5CAD55054A7968B4` |

The WP-MORPH-05B and WP-MORPH-05C quality-control records confirm that each
script hash was identical before and after the analysis
(`script_unchanged_during_analysis: true`,
`no_method_changed_after_results: true`).

### Frozen analytical inputs

| Artefact | SHA256 | Size (bytes) |
| --- | --- | --- |
| WP-03 `pairwise_relations.csv` (exploration) | `34AD797084524C5FC471877B4A8B7011B54FAAECF0DA58ECCF07D9655C922920` | 7059 |
| WP-05B `validation_correlations.csv` | `B0A2CCCB5B42DAEED12B51CDC129F681FC05946B3C42A11065E97CC10E35E75B` | 7380 |
| WP-05B `validation_direction_checks.csv` | `15E31E50CAAB5F6A786209BBBB8C1249EB4AB8F39E00601038046946CEE880E3` | 4794 |
| WP-05B `validation_summary_by_city.csv` | `2280D081A347AC1053872A2C167940E37DA4471E2B2D3326A7734FC53AD92B1F` | 948 |
| WP-05B `validation_hypothesis_summary.csv` | `9CB157A722913EBD88ED7D3103E38DBE704BCA816338613944C92D3ABCCEF7C5` | 809 |
| WP-05C `01_directional_concordance.csv` | `6DF36B770F23A2F49445156B5F7D881AECEF6B2B48239856F96098DBAC48EFC2` | 332 |
| WP-05C `02_exploration_validation_magnitude_summary.csv` | `648F7B5412DA4DEC94C22D41A71E0CA194444E838B54C50E447CB2E318FBD98C` | 6487 |
| WP-05C `03_scale_coverage_metric_sensitivity.csv` | `8012B2B3CAD38E4AAA19A9DA91E49F362A77BC023646AFBCE5BDC6402A0CD082` | 31844 |
| WP-05C `04_relationship_robustness_profile.csv` | `6ED93EF7528BE61924E1421E26BD77A83ECE54C3DFF4A6C41536B42AA2D7A494` | 1168 |

All nine values were verified directly against the distributed frozen files
before packaging. The expected WP-05C magnitude-summary hash was verified
against the frozen file and matched exactly; no expected hash was adjusted.

## 4. Reproduction levels

### Level A — required paper reproduction

`scripts/02_reproduce_synthesis.py` recomputes the four frozen WP-MORPH-05C
synthesis tables from the frozen result-level exploration and validation
tables. This level reproduces every number and figure reported in the
manuscript, and it always works from the frozen inputs bundled in this package.

### Level B — validation recomputation

`scripts/01_reproduce_validation.py` independently recomputes the WP-MORPH-05B
validation coefficients from the five frozen WP-MORPH-05A validation-window
products, then compares the result with the frozen WP-MORPH-05B tables.

The frozen WP-MORPH-05A window files are small enough to distribute
(`validation_windows_1km.csv` ≈ 1.47 MiB, `validation_windows_5km.csv` ≈ 89 KiB),
so Level B is **included**. Raw 50 m source data are not required.

If the window files were ever absent, the level would report
`NOT_INCLUDED_WITH_REASON` and Level A would still reproduce every manuscript
number and figure.

### Level C — optional raw-data rebuild

The upstream 50 m grid depends on multi-gigabyte to multi-terabyte public
products (Overture Buildings, Overture Roads, GlobalBuildingAtlas
`GBA.Height`). These are **not** bundled and are **never** downloaded by
`python run_all.py`. `data/external_sources/README.md` documents the frozen
source releases, the required raw variables and the acquisition route. Level C
is optional and is not required to reproduce the manuscript.

## 5. Provenance gaps (reported, not repaired)

Two items requested during packaging could not be satisfied exactly as
specified. Both are reported here rather than silently substituted.

### 5.1 `WP-MORPH-05C_IMPLEMENTATION_SPEC_V1.json` — NOT FOUND

The implementation-specification identifier `WP-MORPH-05C-IMPLEMENTATION-V1`
is recorded inside the frozen WP-MORPH-05C artefacts
(`data/frozen_inputs/synthesis/method_contract.json`,
`data/frozen_inputs/synthesis/qc_summary.json`,
`data/frozen_inputs/synthesis/manifest.json`), but **no standalone
implementation-specification file exists** in the frozen project tree, in the
author's document archive, or elsewhere on the packaging machine. An exhaustive
filename search over the project root, the document archive and the working
drive returned no match.

Consequently the file is **not distributed**. No substitute was invented and
no expected hash was adjusted. What *is* distributed for WP-MORPH-05C provenance
is:

| Distributed artefact | SHA256 |
| --- | --- |
| `config/WP-MORPH-05C_METHOD_CONTRACT_V1.md` | `936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3` |
| `config/WP-MORPH-05C_FREEZE_RECORD.txt` | `299C11980737EAD0ED1126E3CF9C20D2CB61660FAA9A30EAB4CC7F6B7D29914E` |
| `data/frozen_inputs/synthesis/method_contract.json` | `09CF4CD8D1D5D7F4557FF953ECFF90B62C6EC1707B5452FBBD3653EC168AFA02` |
| `data/frozen_inputs/synthesis/manifest.json` | `4D698A85EA21EA2A8CD7E3697282B6EB67F1310EC7E19E0E5CAD55054A7968B4` |
| `data/frozen_inputs/synthesis/qc_summary.json` | `1D7A140497B6ABF9A02D07CA170BDF71F637A7593647CC6661D27BE33C6FDF43` |

### 5.2 Two different `WP-MORPH-05C_method_contract.json` files exist

The author's document archive holds a `WP-MORPH-05C_method_contract.json` with
SHA256 `70ED2B04F158F5EE4FB490D26E8CCD532D6CEBA4B5B9ED14CAD164CB7A87F02A`.
This is **not** the frozen WP-MORPH-05C artefact.

The copy distributed here is the one written by the frozen run itself and
recorded in the frozen WP-MORPH-05C manifest:

| File | SHA256 | Status |
| --- | --- | --- |
| `data/frozen_inputs/synthesis/method_contract.json` (distributed) | `09CF4CD8D1D5D7F4557FF953ECFF90B62C6EC1707B5452FBBD3653EC168AFA02` | frozen run artefact — used and verified by the figure preflight |
| archive copy | `70ED2B04F158F5EE4FB490D26E8CCD532D6CEBA4B5B9ED14CAD164CB7A87F02A` | not a frozen artefact — not distributed |

The distributed `method_contract.json` records
`method_contract_sha256 = 936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3`,
which matches the distributed method-contract document byte for byte. The
internal consistency of the frozen chain is therefore intact.

### 5.3 No expected-hash discrepancy occurred

Every expected hash supplied with the packaging task was checked directly
against the frozen file. In particular the WP-MORPH-05C magnitude-summary file
`02_exploration_validation_magnitude_summary.csv` matched the expected
`648F7B5412DA4DEC94C22D41A71E0CA194444E838B54C50E447CB2E318FBD98C` exactly.
No expected value needed to be corrected, and none was.

### 5.4 City-name metadata corrected in this release

Release v1.0 of this package carried two incorrect city-name labels. They were
record-label metadata only and never entered any computation, but they were
wrong and are corrected here.

Corrected frozen labels for the two affected cities:

| City ID | Frozen label |
| --- | --- |
| `P026` | Luoyang |
| `P037` | Xining |

The v1.0 labels for these two cities were erroneous. Two stale strings were
involved, and neither of them names a city in the frozen analytical universe:
one is the label of a city that falls outside the frozen universe entirely,
and the other is not used by any city in this study.

The correction is corroborated by two independent, author-controlled sources:

1. the frozen canonical city roster produced by the validation-city nomination
   chain (`canonical_city_roster.csv`, adjudicated
   `canonical_roster: VERIFIED`), which supplies the frozen label for every
   city identifier used here, including Luoyang for `P026` and Xining for
   `P037`;
2. the manuscript Methods, which state that exploratory analysis was conducted
   in **Shenzhen, Luoyang and Xining**.

No city identifier, and no analytical file, was touched: only the `city_names`
metadata block of `config/frozen_analysis_config.json` changed.
`scripts/00_preflight.py` now hard-checks the mapping, and
`tests/test_city_metadata.py` fails if a stale v1.0 label reappears next to an
exploration city identifier anywhere in the distributed package.

## 6. Determinism

* All frozen result tables are recomputed byte-identically: the reproduced
  `validation_correlations.csv`, `validation_direction_checks.csv`,
  `validation_summary_by_city.csv`, `validation_hypothesis_summary.csv`,
  `01_directional_concordance.csv`,
  `02_exploration_validation_magnitude_summary.csv`,
  `03_scale_coverage_metric_sensitivity.csv` and
  `04_relationship_robustness_profile.csv` all match the frozen files at the
  byte level.
* CSV output uses the frozen dialect: UTF-8 with BOM, no index column,
  `%.12g` float formatting and an **explicitly pinned CRLF line terminator**.
  Pinning the terminator matters: pandas otherwise defaults to `os.linesep`,
  which produces LF on Linux and would break byte-level identity with the frozen
  files even though every value reproduces. The eight core tables are therefore
  byte-identical to the frozen files on both Windows and Linux.
* Figures are regenerated with deterministic ordering. Because PNG/PDF/SVG
  binaries embed renderer metadata and text rasterisation can differ between
  interpreter builds, figure reproduction is verified at the level of the
  plotted data: every plotted value equals the frozen analytical output.

## 7. What this package does not do

* It does not change any scientific result.
* It does not add or remove cities, scales, selections, relationships or
  metrics.
* It does not change variable definitions, missing-value handling, weights or
  the minimum valid-window rule.
* It does not add p-values, significance tests, robustness scores or
  relationship rankings.
* It does not modify the original frozen project files.
* It does not execute or authorize formal CANU production, and it does not
  change any formal CANU gate.

> This package reproduces the manuscript-level morphology validation analyses.
> It does not execute or authorize the formal CANU production pipeline.
