# Methods-to-code mapping

Every manuscript method statement maps to an explicit, inspectable element of
this package. Nothing in the reproduction pathway introduces a method decision
that is not already frozen.

| Manuscript method element | Frozen rule | Implemented in | Config / provenance |
| --- | --- | --- | --- |
| 50 m urban grid aggregated to 1 km and 5 km windows | 1 km = 20 × 20 cells of 50 m; 5 km = 100 × 100 cells of 50 m | not recomputed — frozen windows distributed | `config/frozen_analysis_config.json` → `scale_definition` |
| Two window selections | `ALL` = every generated window; `COVERAGE_80` = `effective_area_fraction >= 0.80` | `scripts/utils/wp05b_engine.py` (`compute_validation_units`) | `config/frozen_analysis_config.json` → `selection_definition`, `coverage_80_threshold` |
| Three pairwise morphology relationships | `BUILDING_ROAD`, `BUILDING_HEIGHT`, `ROAD_HEIGHT` | `scripts/utils/wp05c_engine.py` (`PAIR_MAP`) | `config/frozen_analysis_config.json` → `relationship_mapping` |
| Frozen variable definitions | building coverage, road length density, conditional mean building height | inherited from frozen tables; never re-derived | `DATA_DICTIONARY.md` §2 |
| Weighted Pearson weights | `effective_area_m2` (building–road); `height_valid_area_m2` (height relationships) | `scripts/utils/wp05b_engine.py` (`PAIR_DEFINITIONS`) | `config/frozen_analysis_config.json` → `relationship_mapping` |
| Missing height remains missing | never replaced by zero; never imputed | pairwise-validity rule in `scripts/utils/wp05b_engine.py` | `config/frozen_analysis_config.json` → `missing_height_rule` |
| Spearman rho definition | Pearson correlation of average ranks | `scripts/utils/wp05b_engine.py` (`spearman_rho`) | `config/frozen_analysis_config.json` → `statistic_definitions` |
| Weighted Pearson r definition | weighted covariance / weighted SDs | `scripts/utils/wp05b_engine.py` (`weighted_pearson_r`) | `config/frozen_analysis_config.json` → `statistic_definitions` |
| Minimum pairwise valid windows | 10 | `scripts/utils/wp05b_engine.py` (`MIN_PAIRWISE_VALID_WINDOWS`) | `config/frozen_analysis_config.json` → `minimum_pairwise_valid_windows` |
| Direction classification order | `INSUFFICIENT_WINDOWS` → `SIGN_REVERSAL` → `SAME_SIGN` → `UNDEFINED` | `scripts/utils/wp05b_engine.py` (`classify_unit`) | `config/frozen_analysis_config.json` → `validation_classification_order` |
| Expected direction | `POSITIVE` for all three relationships | frozen WP-03 candidate table | `config/frozen_analysis_config.json` → `expected_sign` |
| 36 prespecified validation conditions | 3 cities × 2 scales × 2 selections × 3 relationships | `scripts/01_reproduce_validation.py`, `scripts/utils/wp05b_engine.py` | `config/expected_outputs.json` → `expected_validation_classification_counts` |
| Aggregation and relationship analysis separated | WP-05A never computed relationships | Level B recomputes relationships only in `scripts/01_reproduce_validation.py` | `REPRODUCIBILITY.md` §2 |
| Synthesis used frozen result-level inputs only | no raw 50 m reads, no window reads, no coefficient re-estimation | `scripts/02_reproduce_synthesis.py`, `scripts/utils/wp05c_engine.py` | `REPRODUCIBILITY.md` §4 |
| Magnitude summaries | n, median, Q1, Q3, min, max, range per relationship × scale × selection × metric | `scripts/utils/wp05c_engine.py` (`make_magnitude_summary`) | `config/frozen_analysis_config.json` → `synthesis_aggregates`, `quartile_method` |
| Quartiles | `pandas.Series.quantile(interpolation="linear")` | `scripts/utils/wp05c_engine.py` (`qlinear`) | `config/frozen_analysis_config.json` → `quartile_method` |
| Phase shift | `validation_median − exploration_median` | `scripts/utils/wp05c_engine.py` (`make_magnitude_summary`) | `config/frozen_analysis_config.json` → `synthesis_delta_definitions` |
| Scale / coverage / metric sensitivity | `5km − 1km`; `COVERAGE_80 − ALL`; `weighted Pearson r − Spearman rho`, with absolute versions | `scripts/utils/wp05c_engine.py` (`make_sensitivity`) | `config/frozen_analysis_config.json` → `synthesis_delta_definitions` |
| Cross-city range | `max(coefficient) − min(coefficient)` within a phase | `scripts/utils/wp05c_engine.py` (`cross_city_ranges`) | `DATA_DICTIONARY.md` §4 |
| No composite score, no ranking, no thresholds | prohibited | not implemented anywhere; asserted by `tests/test_synthesis_results.py` | `config/frozen_analysis_config.json` → `prohibited` |
| Figures | Fig. 2, Fig. 3, Supplementary Fig. S1, Supplementary Fig. S2 | `scripts/03_make_main_figures.py`, `scripts/04_make_supplementary_figures.py`, `scripts/utils/wp05d_figure_engine.py` | `config/expected_outputs.json` → `figure_outputs` |
| Formal CANU gates unchanged | not executed, not authorized | asserted in `run_all.py` report and every stage report | `config/frozen_analysis_config.json` → `formal_canu_*` |

## Statistical quantities deliberately not computed

| Not computed | Why |
| --- | --- |
| p-values / significance tests | Prohibited by the frozen method contract; the 36 validation conditions are repeated analytical conditions within three cities, not 36 independent replications. |
| Confidence intervals, standard errors, standard deviations shown as inference | The frozen outputs report medians, quartiles and min–max ranges only. |
| Composite robustness score / weighted robustness index | Prohibited post-hoc aggregation. |
| Relationship ranking | Prohibited; relationships are always shown in the fixed frozen order. |
| Alternative correlation estimators | No estimator was introduced after the freeze. |
