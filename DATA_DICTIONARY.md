# Data dictionary

This dictionary defines every field used by the reproducibility scripts. Field
names are identical across the frozen files, the reproduced files and the
Source Data tables.

---

## 1. Identifier and design fields

| Field | Type | Definition |
| --- | --- | --- |
| `city_id` | string | Frozen anonymised city identifier. Exploration: `P004`, `P026`, `P037`. Validation: `P001`, `P003`, `P005`. |
| `city_name` | string | Descriptive city label carried as a record label only. It is never used in any computation, filtering or ordering. |
| `scale` | string | Spatial aggregation scale of the analysis window: `1km` or `5km`. |
| `selection` | string | Window selection rule: `ALL` or `COVERAGE_80`. |
| `relationship` / `pair_id` | string | One of the three frozen pairwise relationships: `BUILDING_ROAD`, `BUILDING_HEIGHT`, `ROAD_HEIGHT`. |
| `variable_x` | string | x variable of the relationship. |
| `variable_y` | string | y variable of the relationship. |
| `metric` | string | `SPEARMAN_RHO` or `WEIGHTED_PEARSON_R`. |
| `phase` | string | `EXPLORATION` (cities `P004`, `P026`, `P037`) or `VALIDATION` (cities `P001`, `P003`, `P005`). |
| `expected_sign` | string | Frozen expected direction of the relationship. `POSITIVE` for all three relationships. |
| `status` | string | Frozen WP-MORPH-03 record status (`DESCRIPTIVE_OK`). Descriptive only; no threshold is implied. |

---

## 2. Window-level fields (`data/validation_windows/validation_windows_{1km,5km}.csv`)

| Field | Unit | Definition |
| --- | --- | --- |
| `block_cells` | cells | Side length of the aggregation window in 50 m cells (20 for `1km`, 100 for `5km`). |
| `window_row`, `window_col` | index | Position of the window in the frozen city window grid. |
| `cell_count` | cells | Number of 50 m cells that contributed to the window. |
| `nominal_window_size_m` | m | Nominal window side: 1000 for `1km`, 5000 for `5km`. |
| `nominal_window_area_m2` | m² | Nominal window area: 1 000 000 for `1km`, 25 000 000 for `5km`. |
| `effective_area_m2` | m² | Area of the window actually supported by data (50 m cells × 2500 m²). |
| `effective_area_fraction` | ratio | `effective_area_m2 / nominal_window_area_m2`. |
| `coverage_80` | boolean | `True` when `effective_area_fraction >= 0.80`. Defines the `COVERAGE_80` selection. |
| `building_covered_area_m2` | m² | Building footprint area inside the window. |
| `building_coverage_mean` | ratio | Mean building coverage over the window's contributing cells. |
| `road_length_m` | m | Total road centre-line length inside the window. |
| `road_density_mean_km_per_km2` | km km⁻² | Road length density over the window's contributing area. |
| `height_valid_area_m2` | m² | Building footprint area inside the window that also carries valid GlobalBuildingAtlas height support. Used as the weighted-Pearson weight for the two height relationships. |
| `height_valid_area_fraction_of_effective` | ratio | `height_valid_area_m2 / effective_area_m2`. |
| `height_valid_cell_count` | cells | Number of 50 m cells with valid building-height support. |
| `height_conditional_mean_m` | m | Mean building height conditional on valid height support. Cells without valid height support remain **missing**; missing height is never replaced by zero. |
| `valid_pair_windows` (WP03) / `n_pairwise_valid_windows` (WP05B) | count | Number of selected windows with finite values for both variables of the relationship. |
| `n_total_windows` | count | Number of selected windows before applying the pairwise-validity rule. |
| `n_weighted_valid_windows` | count | Number of pairwise-valid windows that additionally carry a finite, strictly positive weight. |
| `valid_effective_area_m2` | m² | Sum of `effective_area_m2` over the pairwise-valid windows. |
| `weighted_pearson_weight_sum_m2` | m² | Sum of the relationship weight over the weighted-valid windows. |

---

## 3. Coefficient and classification fields

| Field | Definition |
| --- | --- |
| `spearman_rho` | Spearman rho: Pearson correlation of the average ranks of x and y over the pairwise-valid windows. Ties use average ranks. No p-value is computed. |
| `weighted_pearson_r` | Weighted Pearson r: weighted covariance divided by the weighted standard deviations of x and y, using the frozen relationship weight. No p-value is computed. |
| `spearman_direction`, `weighted_pearson_direction` | Sign of the corresponding coefficient: `POSITIVE`, `NEGATIVE`, or blank when the coefficient is undefined. |
| `coefficient_direction_agreement` | `True` when both coefficients are defined and share the same sign; blank otherwise. |
| `classification` | Frozen unit classification. See the ordered rule below. |
| `any_sign_reversal` | `True` only when `classification == SIGN_REVERSAL`. |
| `p_value_computed` | Always `False`. No p-value is computed anywhere in this package. |

### Classification rule (evaluated in this exact order)

```
if n_pairwise_valid_windows < 10:            -> INSUFFICIENT_WINDOWS
else if either defined coefficient < 0:      -> SIGN_REVERSAL
else if Spearman rho > 0 AND weighted Pearson r > 0: -> SAME_SIGN
else                                         -> UNDEFINED
```

The minimum pairwise-valid-window rule is 10. The expected sign is `POSITIVE`
for all three frozen relationships.

---

## 4. Synthesis fields

| Field | Definition |
| --- | --- |
| `exploration_n`, `validation_n` | Number of frozen city coefficients summarised in that phase (always 3). |
| `exploration_median`, `validation_median` | Median coefficient of the three frozen cities of that phase. |
| `exploration_q1`, `exploration_q3`, `validation_q1`, `validation_q3` | Lower and upper quartiles, computed with `pandas.Series.quantile(interpolation="linear")`. |
| `exploration_min`, `exploration_max`, `validation_min`, `validation_max` | Minimum and maximum frozen city coefficient of that phase. |
| `exploration_range`, `validation_range` | Cross-city range, `max(coefficient) - min(coefficient)`, within that phase. |
| `median_shift` | `validation_median - exploration_median`. |
| `absolute_median_shift` | `abs(validation_median - exploration_median)`. |
| `dimension` | Sensitivity dimension: `SCALE`, `COVERAGE` or `METRIC`. |

The distributed sensitivity schema uses `dimension` (SCALE/COVERAGE/METRIC);
no separate `delta_type` field is present.
| `conditioning_scale_or_selection` | The factor held fixed while the dimension is varied. For `SCALE` it is the window selection; for `COVERAGE` it is the scale; for `METRIC` it is `"<scale>\|<selection>"`. |
| `comparison_a`, `comparison_b` | The two levels being compared; the delta is always `coefficient_b - coefficient_a`. |
| `coefficient_a`, `coefficient_b` | Frozen coefficients of the two compared levels. |
| `signed_delta` | `coefficient_b - coefficient_a`. |
| `absolute_delta` | `abs(signed_delta)`. |
| `median_cross_city_range`, `max_cross_city_range` | Median and maximum of the eight cross-city ranges (2 scales × 2 selections × 2 metrics) of a phase and relationship. |
| `median_abs_scale_delta`, `max_abs_scale_delta` | Median and maximum of the twelve scale deltas (`5km − 1km`) of a phase and relationship. |
| `median_abs_coverage_delta`, `max_abs_coverage_delta` | Median and maximum of the twelve coverage deltas (`COVERAGE_80 − ALL`) of a phase and relationship. |
| `median_abs_metric_delta`, `max_abs_metric_delta` | Median and maximum of the twelve metric/weighting deltas (`weighted Pearson r − Spearman rho`) of a phase and relationship. |
| `directional_same_sign_count` | Validation: number of `SAME_SIGN` units for that relationship. Exploration: intentionally blank — no retrospective exploration sign classification is created. |
| `directional_eligible_count` | Validation: `SAME_SIGN + SIGN_REVERSAL + UNDEFINED` units. Exploration: intentionally blank. |

### Delta definitions

```
scale_delta            = coefficient_5km          - coefficient_1km
coverage_delta         = coefficient_COVERAGE_80  - coefficient_ALL
metric_weighting_delta = weighted_Pearson_r       - Spearman_rho
```

Absolute versions of all three deltas are retained alongside the signed deltas.

---

## 5. Analytic universe definitions

### `ALL`

`ALL` retains **every** frozen analysis window of that city and scale. No
completeness threshold is applied. `n_total_windows` for `ALL` equals the
number of generated windows of that city and scale.

### `COVERAGE_80`

`COVERAGE_80` retains only windows satisfying

```
effective_area_fraction >= 0.80
```

i.e. windows whose data-supported effective area represents at least 80 % of
the nominal window area. The threshold is frozen at `0.80` and is the only
coverage threshold in the package.

### `1km`

A 1 km analysis window is a **20 × 20** block of 50 m cells
(`20 × 50 m = 1000 m`), nominal area 1 000 000 m².

### `5km`

A 5 km analysis window is a **100 × 100** block of 50 m cells
(`100 × 50 m = 5000 m`), nominal area 25 000 000 m².

---

## 6. Relationship mapping and weights

| Relationship | x variable | y variable | Weighted-Pearson weight |
| --- | --- | --- | --- |
| `BUILDING_ROAD` | `building_coverage_mean` | `road_density_mean_km_per_km2` | `effective_area_m2` |
| `BUILDING_HEIGHT` | `building_coverage_mean` | `height_conditional_mean_m` | `height_valid_area_m2` |
| `ROAD_HEIGHT` | `road_density_mean_km_per_km2` | `height_conditional_mean_m` | `height_valid_area_m2` |

### Missing-height handling

A window without valid building-height support keeps a **missing** height
value. Missing height is never replaced by zero, never imputed, and never
re-weighted. Windows with missing height are excluded pairwise from the
height relationships through the pairwise-validity rule, while the
building–road relationship continues to use all windows with finite building
coverage and road density.

---

## 7. Figure source fields

| Field | Definition |
| --- | --- |
| `figure_panel` | In the Source Data table for Fig. 2: `a` for the directional-count panel and `b-d` for the magnitude panels. |
| `validation_unit_count` | Number of frozen validation units of that relationship (always 12). |
| `same_sign_count`, `sign_reversal_count`, `insufficient_count`, `undefined_count` | Counts of the four classification outcomes for that relationship. |
| `directional_reproducibility_fraction` | `same_sign_count / (same_sign_count + sign_reversal_count + undefined_count)`. Descriptive only; it is not a success threshold. |

---

## 8. Fields intentionally absent

The following quantities do **not** exist anywhere in the package, by design:

* p-values, significance tests, confidence intervals, standard errors
* composite robustness scores, weighted robustness indices
* relationship rankings
* post-hoc success thresholds or stable/unstable boundaries
* alternative correlation estimators introduced after the freeze
