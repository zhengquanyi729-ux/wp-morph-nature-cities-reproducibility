# original_frozen_scripts — NON-RUNNABLE HISTORICAL PROVENANCE

> **These files are non-runnable provenance copies.**
>
> They are the exact script versions that produced the frozen results, kept
> only so that a verifier can inspect what was executed and confirm the
> recorded script identities. They contain historical absolute paths
> (`C:\china_meld\...`) and reference upstream project files that are **not**
> distributed with this package. Running them is neither required nor
> supported.
>
> The runnable, path-independent, journal-facing equivalents live in
> `scripts/` and are driven by `run_all.py`.

| File | SHA256 | Role |
| --- | --- | --- |
| `run_wp_morph03.py` | `06160D33D307BE7698C97419A77A60B8DD5DF2C863AC106EC84E24CDBB3F728F` | Exploratory pairwise relationship quantification (WP-MORPH-03) |
| `run_wp_morph04h.py` | `29D07025007CD0826BA633048EB195275FEBDB6DF3B2B6A38B62E8762724D36E` | Validation-city nomination and method freeze (WP-MORPH-04H) |
| `run_wp_morph05a.py` | `5B8255E3C5BA1EDA5904A6D227C61788CE0536F65BB453E551874AECCBCB5806` | Validation window aggregation (WP-MORPH-05A) |
| `run_wp_morph05b.py` | `78E955CCAAA819826C44CEE9E5971B32374DCC9C93559D927F13A1ED9B017A54` | Frozen validation relationship analysis (WP-MORPH-05B) |
| `run_wp_morph05c_input_preflight_v1.py` | `EFAA84ADD32BC27921A2E5A7296B5DD4186D2009588F38939A6D86DB2DDBEC29` | WP-MORPH-05C input-registration preflight |
| `run_wp_morph05c_synthesis_v1.py` | `EA6A883787587A715486B2181ACFB518942003207A38A6CE8E660ED72DB51EDB` | Concordance synthesis (WP-MORPH-05C) |
| `run_wp_morph05d_figures_v1.py` | `3AC43986484D37658092E163605349911F907F478D37384CC6CFBEDD9930A4CF` | Figure production (WP-MORPH-05D) |

## How the runnable package relates to these copies

| Frozen script | Runnable journal-facing equivalent | Relationship |
| --- | --- | --- |
| `run_wp_morph05b.py` | `scripts/utils/wp05b_engine.py` | Faithful reimplementation; identical mathematics and classification rules; all paths derived from the package root |
| `run_wp_morph05c_synthesis_v1.py` | `scripts/utils/wp05c_engine.py` | Faithful reimplementation; identical synthesis rules; reads frozen result-level inputs only |
| `run_wp_morph05d_figures_v1.py` | `scripts/utils/wp05d_figure_engine.py` | Verbatim scientific logic; the only changes are the two hard-coded directories (replaced with package-relative paths) and a bytecode-cache guard |
| `run_wp_morph03.py`, `run_wp_morph04h.py`, `run_wp_morph05a.py`, `run_wp_morph05c_input_preflight_v1.py` | not required | Provided for provenance only; their outputs are distributed as frozen inputs |
