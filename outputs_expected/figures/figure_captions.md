# WP-MORPH-05D figure captions

All values shown in these figures are frozen WP-MORPH-05C outputs: `01_directional_concordance.csv`, `02_exploration_validation_magnitude_summary.csv`, `03_scale_coverage_metric_sensitivity.csv`, `04_relationship_robustness_profile.csv`.
No coefficient was re-estimated, no correlation was recomputed, and no statistical
test, p-value, confidence interval or composite robustness score is reported. No
relationship, city, scale, selection or metric was removed, and no relationship was
ranked.

Exploration phase = cities P004, P026, P037. Validation phase = cities P001, P003, P005.
Window selections: ALL = all windows; COVERAGE_80 = Coverage ≥ 80%.
Metrics / weighting formulations: Spearman rho and weighted Pearson r.
Spatial scales: 1 km and 5 km. Relationship order in every panel is
Building–road, Building–height, Road–height.

---

## Figure 1 | Independent directional reproducibility and magnitude concordance

Panel A: preregistered validation units that retained the expected positive direction,
counted separately for each relationship. Each relationship retained the expected
positive direction in all 12 of its validation units (12 / 12 per relationship;
36 / 36 units overall) with 0 sign reversals. Source: 01_directional_concordance.csv.

Panels B-D: frozen exploration and validation correlation coefficients for
Building–road (B), Building–height (C) and Road–height (D). Each row is one of the
eight analytical conditions defined by spatial scale (1 km, 5 km), window selection
(ALL, COVERAGE_80) and metric / weighting formulation (Spearman rho, weighted Pearson
r); rows are grouped by scale. Open circles are Exploration medians (cities P004, P026, P037) and
filled squares are Validation medians (cities P001, P003, P005); the thin line joins the two
medians of the same analytical condition, and grey whiskers span the frozen city
minimum–maximum coefficient of that phase. No standard deviation, standard error,
confidence interval or significance value is computed or shown.
Source: 02_exploration_validation_magnitude_summary.csv.

Panels B-D share one common x-axis (correlation coefficient, 0.0-0.9).
Coefficient magnitudes are not numerically identical between phases, and the magnitude
difference between phases differs between relationships and analytical conditions.

---

## Figure 2 | Relationship-specific robustness structure

Frozen median absolute coefficient change observed within each relationship when one
analytical dimension is varied, shown for Exploration (a, cities P004, P026, P037) and Validation
(b, cities P001, P003, P005). Source: 04_relationship_robustness_profile.csv.

Columns are the three sensitivity dimensions. Scale = median |Δ coefficient| across
Δ = 5 km − 1 km. Coverage = median |Δ coefficient| across
Δ = COVERAGE_80 − ALL. Metric / weighting = median |Δ coefficient| across
Δ = weighted Pearson r − Spearman rho. Cell values are printed as frozen in the source file to
three decimal places.

Both panels use identical colour limits (0 to 0.237) and one shared sequential
colour scale, so Exploration and Validation can be compared directly. Plotted quantity:
median absolute coefficient change; identical colour scale in both panels. No robustness
threshold, no stable / unstable boundary, no ranking and no composite score is defined.
Across the frozen values, median absolute change associated with scale is generally
larger than that associated with coverage; the metric / weighting dimension is
comparatively large for Building–height in both phases, and Road–height shows
comparatively high median scale sensitivity in both phases.

---

## Supplementary Figure S1 | Full city-level sensitivity structure

Signed frozen deltas for every city × relationship combination, shown separately for the
three sensitivity dimensions: A Scale sensitivity (Δ = 5 km − 1 km),
B Coverage sensitivity (Δ = COVERAGE_80 − ALL), C Metric / weighting
sensitivity (Δ = weighted Pearson r − Spearman rho). Source: 03_scale_coverage_metric_sensitivity.csv
(column signed_delta).

Within each block the Exploration matrix (cities P004, P026, P037) and the Validation matrix
(cities P001, P003, P005) are displayed side by side. Rows are city × relationship in fixed order
(Building–road, Building–height, Road–height), and each matrix carries its own
phase-specific row labels, so the Validation rows are labelled with the Validation cities
(P001, P003, P005) and never share the Exploration labels. Columns are the four fixed
conditioning / metric combinations of that dimension and carry a three-level header with
exactly one label per bottom-level column: the phase (Exploration, Validation), then the
metric / weighting formulation (Spearman rho, weighted Pearson r) or the spatial scale
(1 km, 5 km), then the remaining conditioning factor (All = all windows; Cov = window
selection Coverage ≥ 80%, i.e. COVERAGE_80).

Colour is a diverging scale centred on zero that encodes the direction of change only
(negative delta versus positive delta); it does not encode quality or robustness. Each
block applies one symmetric limit to both phases (Scale ±0.374;
Coverage ±0.331; Metric / weighting ±0.375).
Values are plotted without quantile clipping and without truncation of extremes.
No ranking and no significance annotation is used.

---

## Supplementary Figure S2 | Cross-city coefficient dispersion

Frozen cross-city coefficient range (maximum minus minimum coefficient among the three
cities of a phase) for each of the eight analytical conditions defined by spatial scale
(1 km, 5 km), window selection (ALL, COVERAGE_80) and metric / weighting formulation
(Spearman rho, weighted Pearson r), in fixed order and grouped by scale. Source:
02_exploration_validation_magnitude_summary.csv (columns exploration_range and
validation_range).

Panels are A Building–road, B Building–height, C Road–height. Open circles are
Exploration ranges (cities P004, P026, P037) and filled squares are Validation ranges (cities
P001, P003, P005); the thin line joins the two ranges of the same analytical condition. Only the
frozen range columns are plotted (range = maximum minus minimum of the three cities); no
standard deviation, variance, coefficient of variation or interquartile dispersion is
computed.
