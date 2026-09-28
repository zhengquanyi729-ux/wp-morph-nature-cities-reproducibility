# WP-MORPH-05C METHOD CONTRACT V1

**METHOD_CONTRACT_ID:** `WP-MORPH-05C-METHOD-V1`  
**Work package:** WP-MORPH-05C  
**Title:** Exploration–Validation Concordance Synthesis  
**Branch:** NONPRODUCTION / EXPLORATORY-VALIDATION  
**Contract status:** FROZEN BEFORE ANALYTICAL IMPLEMENTATION  
**Formal CANU production gates:** UNCHANGED

## 1. Purpose

WP-MORPH-05C is a read-only synthesis stage comparing the already frozen exploratory results from WP-MORPH-03 with the already frozen independent validation results from WP-MORPH-05B.

It must not discover new relationships, optimize statistical procedures, redefine validation success, or improve apparent replication.

It answers four descriptive questions:

1. **Directional reproducibility:** whether the positive WP03 relationships retain the same direction in independent WP05B validation cities.
2. **Magnitude concordance:** how Spearman rho and weighted Pearson r vary between exploration and validation.
3. **Robustness structure:** how coefficient magnitude varies with spatial scale, COVERAGE_80 selection, and correlation metric.
4. **Relationship-specific sensitivity:** whether BUILDING_ROAD, BUILDING_HEIGHT, and ROAD_HEIGHT show different sensitivity structures while retaining their frozen direction.

WP-MORPH-05C is a **descriptive concordance synthesis**, not a new confirmatory experiment.

## 2. Frozen analytical universe

- Exploratory cities: `P004`, `P026`, `P037`
- Validation cities: `P001`, `P003`, `P005`
- Spatial scales: `1km`, `5km`
- Selections: `ALL`, `COVERAGE_80`
- Relationships: `BUILDING_ROAD`, `BUILDING_HEIGHT`, `ROAD_HEIGHT`
- Metrics: `Spearman rho`, `weighted Pearson r`
- Minimum pairwise valid windows: `10`
- Expected direction for all three relationships: `POSITIVE`
- Ordinary p-values: `PROHIBITED`

No city, scale, selection, relationship, variable definition, weighting rule, missing-value rule, or minimum-window rule may be added, removed, or changed.

## 3. Permitted analytical inputs

### 3.1 WP-MORPH-03

Only frozen WP03 result-level tables containing already computed coefficients for:

- P004 / P026 / P037
- 1km / 5km
- ALL / COVERAGE_80
- BUILDING_ROAD / BUILDING_HEIGHT / ROAD_HEIGHT
- Spearman rho / weighted Pearson r

The exact WP03 source file(s), run path(s), file SHA256 values, and provenance must be registered before execution.

WP05C must not reconstruct WP03 coefficients from lower-level spatial data.

### 3.2 WP-MORPH-05B

Permitted frozen result files:

- `validation_correlations.csv`
- `validation_direction_checks.csv`
- `validation_summary_by_city.csv`
- `validation_hypothesis_summary.csv`

Frozen WP05B source run:

`C:\china_meld\experiments\wp_morph05b_nonproduction\run_20260927_175641_020702\`

### 3.3 Integrity-only inputs

Frozen manifests, QC summaries, method contracts, hashes, and provenance metadata may be read solely for identity and provenance checks.

## 4. Explicitly prohibited inputs

WP05C must not read or derive analytical coefficients from:

- raw 50m Parquet
- WP05A validation window tables
- raw grid cells
- original morphology datasets
- alternative candidate cities
- alternative scales
- alternative COVERAGE thresholds
- alternative variable definitions

No correlation coefficient may be recomputed from raw or window-level observations.

## 5. Frozen relationship definitions

| Relationship | X | Y | Weighted Pearson weight |
|---|---|---|---|
| BUILDING_ROAD | building_coverage_mean | road_density_mean_km_per_km2 | effective_area_m2 |
| BUILDING_HEIGHT | building_coverage_mean | height_conditional_mean_m | height_valid_area_m2 |
| ROAD_HEIGHT | road_density_mean_km_per_km2 | height_conditional_mean_m | height_valid_area_m2 |

## 6. Directional reproducibility

WP05C inherits the frozen WP05B direction logic and does not redefine it.

Current frozen WP05B directional result:

- validation units = 36
- SAME_SIGN = 36
- SIGN_REVERSAL = 0
- INSUFFICIENT_WINDOWS = 0
- UNDEFINED = 0

Descriptive quantity:

`directional_reproducibility_fraction = SAME_SIGN / eligible_validation_units`

No p-value, confidence interval, permutation test, or new direction gate is allowed.

## 7. Magnitude concordance

No post-result threshold may define a coefficient as replicated, failed, stable, unstable, acceptable, or unacceptable.

For each:

`relationship × scale × selection × metric`

summarize exploration and validation separately using:

- n_cities
- median
- Q1
- Q3
- minimum
- maximum
- range = maximum - minimum

Then compute:

`median_shift = validation_median - exploration_median`

`absolute_median_shift = abs(validation_median - exploration_median)`

These are descriptive quantities only.

## 8. Cross-city magnitude consistency

For each:

`phase × relationship × scale × selection × metric`

compute:

`cross_city_range = maximum coefficient - minimum coefficient`

Relationship-level summaries may report:

- median cross-city range
- maximum cross-city range

No numerical cutoff defines consistent versus inconsistent.

## 9. Scale sensitivity

Within city, while holding relationship, selection, and metric fixed:

`scale_delta = coefficient_5km - coefficient_1km`

`absolute_scale_delta = abs(scale_delta)`

For each:

`phase × relationship × selection × metric`

report:

- n
- median scale_delta
- median absolute_scale_delta
- minimum scale_delta
- maximum scale_delta
- maximum absolute_scale_delta

No significance test or scale-effect threshold is allowed.

## 10. COVERAGE_80 sensitivity

Within city, while holding relationship, scale, and metric fixed:

`coverage_delta = coefficient_COVERAGE_80 - coefficient_ALL`

`absolute_coverage_delta = abs(coverage_delta)`

For each:

`phase × relationship × scale × metric`

report:

- n
- median coverage_delta
- median absolute_coverage_delta
- minimum coverage_delta
- maximum coverage_delta
- maximum absolute_coverage_delta

Frozen threshold remains:

`effective_area_fraction >= 0.80`

No alternative coverage threshold may be tested.

## 11. Metric / weighting sensitivity

For each:

`phase × city × relationship × scale × selection`

compute:

`metric_delta = weighted_Pearson_r - Spearman_rho`

`absolute_metric_delta = abs(metric_delta)`

For each:

`phase × relationship`

report:

- median metric_delta
- median absolute_metric_delta
- minimum metric_delta
- maximum metric_delta
- maximum absolute_metric_delta

This dimension must be called **metric / weighting sensitivity**, not pure weighting sensitivity, because the two measures differ in both correlation formulation and weighting structure.

No additional correlation estimator may be introduced.

## 12. Relationship-specific robustness profile

For each relationship, descriptive outputs may include:

- SAME_SIGN count / eligible count
- median and absolute exploration–validation median shift
- median and maximum cross-city range
- median and maximum absolute scale delta
- median and maximum absolute coverage delta
- median and maximum absolute metric delta

These quantities must **not** be combined into:

- overall robustness score
- weighted robustness index
- ranking
- winner
- best relationship
- worst relationship

## 13. Exploration–validation pattern concordance

WP05C may compare whether sensitivity patterns seen in exploration are also present in validation, using only the predefined quantities in Sections 9–11.

No additional pattern metric may be created after viewing WP05C outputs.

Pattern concordance remains descriptive and is not a new validation-success gate.

## 14. Known WP03 caveats

Previously documented WP03 caveats remain visible.

The known attenuation of BUILDING_HEIGHT at 5km under COVERAGE_80 in P004 may be compared descriptively with frozen validation results.

It must not be retrospectively redefined as a separately preregistered secondary hypothesis unless frozen pre-validation documentation demonstrates that status.

## 15. Missing and undefined values

WP05C inherits validity decisions from frozen source stages.

It must not:

- replace missing coefficients with zero
- impute coefficients
- relax the minimum-window rule
- change missing-value handling
- recompute coefficients

If an inherited coefficient is undefined, any derived delta requiring it is also undefined.

## 16. Inferential restrictions

WP05C is descriptive. Prohibited:

- ordinary correlation p-values
- tests treating spatial windows as independent observations
- t-tests
- ANOVA
- Mann–Whitney tests
- Wilcoxon tests
- bootstrap significance claims
- permutation significance claims
- confidence intervals used as replication gates
- multiple-testing correction
- post-hoc significance screening

WP05C makes no causal claim.

## 17. No post-result analytical flexibility

After this contract is frozen, implementation must not change:

- cities
- relationships
- scales
- selections
- metrics
- weights
- coefficient definitions
- delta definitions
- summary statistics
- aggregation dimensions
- missing-value treatment
- direction classification
- reporting universe

All three relationships, both scales, both selections, both metrics, and all six frozen cities remain reportable.

## 18. Required analytical outputs

### 18.1 `01_directional_concordance.csv`

Minimum fields:

- relationship
- expected_sign
- exploration_city_count
- validation_city_count
- validation_unit_count
- same_sign_count
- sign_reversal_count
- insufficient_count
- undefined_count
- directional_reproducibility_fraction

### 18.2 `02_exploration_validation_magnitude_summary.csv`

One row per:

`relationship × scale × selection × metric`

Minimum fields:

- relationship
- scale
- selection
- metric
- exploration_n
- exploration_median
- exploration_q1
- exploration_q3
- exploration_min
- exploration_max
- exploration_range
- validation_n
- validation_median
- validation_q1
- validation_q3
- validation_min
- validation_max
- validation_range
- median_shift
- absolute_median_shift

### 18.3 `03_scale_coverage_metric_sensitivity.csv`

Minimum conceptual fields:

- phase
- city
- relationship
- dimension
- conditioning_scale_or_selection
- metric
- coefficient_a
- coefficient_b
- signed_delta
- absolute_delta

`dimension` is restricted to:

- SCALE
- COVERAGE
- METRIC

### 18.4 `04_relationship_robustness_profile.csv`

One row per:

`phase × relationship`

Minimum fields:

- phase
- relationship
- directional_same_sign_count
- directional_eligible_count
- median_cross_city_range
- max_cross_city_range
- median_abs_scale_delta
- max_abs_scale_delta
- median_abs_coverage_delta
- max_abs_coverage_delta
- median_abs_metric_delta
- max_abs_metric_delta

No total score or ranking column is allowed.

## 19. Required integrity outputs

WP05C must also produce:

- `method_contract.json`
- `qc_summary.json`
- `manifest.json`

Manifest input identity should record, where available:

- source work package
- source run
- file path
- file name
- SHA256
- file size

## 20. Pre-result implementation freeze

Before complete synthesis execution:

`METHOD_CONTRACT_ID = WP-MORPH-05C-METHOD-V1`

The final implementation script must record:

`SCRIPT_SHA256_BEFORE_SYNTHESIS`

and verify after execution:

`SCRIPT_SHA256_AFTER_SYNTHESIS == SCRIPT_SHA256_BEFORE_SYNTHESIS`

If code is changed after results are inspected, that execution cannot be represented as the original frozen WP05C run. Any correction requires an explicitly versioned run and documented reason.

## 21. Required QC assertions

A completed WP05C run must explicitly assert:

- RAW_50M_DATA_READ = False
- WP05A_WINDOW_DATA_READ = False
- COEFFICIENTS_REESTIMATED = False
- EXPLORATION_CITIES_CHANGED = False
- VALIDATION_CITIES_CHANGED = False
- SCALES_CHANGED = False
- SELECTIONS_CHANGED = False
- RELATIONSHIPS_CHANGED = False
- METRICS_CHANGED = False
- WEIGHTS_CHANGED = False
- P_VALUES_COMPUTED = False
- POSTHOC_SUCCESS_THRESHOLD_USED = False
- COMPOSITE_ROBUSTNESS_SCORE_COMPUTED = False
- RELATIONSHIP_RANKING_COMPUTED = False
- FORMAL_CANU_PRODUCTION_AUTHORIZED = False
- FORMAL_CANU_GATES = UNCHANGED

## 22. Permitted interpretation

WP05C may support conclusions regarding:

- directional reproducibility
- descriptive magnitude concordance
- cross-city coefficient dispersion
- scale dependence
- COVERAGE_80 dependence
- metric / weighting dependence
- relationship-specific robustness structure

It must not support claims of:

- causality
- statistical independence
- conventional statistical significance
- universal effect size
- perfect magnitude replication
- scale invariance
- complete robustness to coverage definition
- an objectively best relationship

## 23. Interpretation hierarchy

1. **Direction:** primary independent-validation result.
2. **Magnitude:** continuous descriptive property; exact equality is not required.
3. **Robustness structure:** scale, coverage, and metric variation are substantive information rather than automatic validation failure.
4. **Relationship specificity:** different morphology relationships may have different sensitivity profiles while retaining the same frozen direction.

## 24. Core scientific framing

The preregistered urban-morphology relationships are evaluated first for independent directional reproducibility and then for the structure of their coefficient variation. Stability is not defined as numerical identity across cities, scales, selections, or metrics. WP05C therefore distinguishes reproducible direction from relationship-specific magnitude sensitivity to spatial aggregation, coverage restriction, and correlation formulation.

## 25. Freeze statement

Once accepted as `WP-MORPH-05C-METHOD-V1`, Sections 1–24 may not be modified in response to WP05C numerical outputs.

Any later analysis not explicitly defined here must be labeled as a separate exploratory work package and must not be retroactively incorporated into WP-MORPH-05C.

**END OF METHOD CONTRACT**
