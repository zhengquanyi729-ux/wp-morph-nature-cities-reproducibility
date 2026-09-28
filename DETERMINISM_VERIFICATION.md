# Clean-environment, cross-platform and determinism verification

This record documents the verifications that were actually executed before this
package release was declared ready. It is evidence, not a plan.

Package release: **v1.1** (supersedes v1.0). See §5 for the changes.

---

## 1. Historical clean-environment verification

Both documented installation routes were exercised end to end from scratch, with
the package content finalised and `outputs_reproduced/` deleted beforehand:

| Route | Commands | Result |
| --- | --- | --- |
| conda | `conda env create -f environment.yml` then `conda run --no-capture-output -n wp-morph-repro python run_all.py`, `conda run --no-capture-output -n wp-morph-repro python -m pytest -q` | `run_all.py` exit 0, `JOURNAL_VERIFICATION_PACKAGE_READY = True`, pytest 100 % pass |
| pip only | `python -m venv .venv`, `python -m pip install -r requirements-lock.txt`, then `python run_all.py`, `pytest -q` | `run_all.py` exit 0, `JOURNAL_VERIFICATION_PACKAGE_READY = True`, pytest 100 % pass |

This historical statement is recorded here deliberately. `run_all.py` does **not**
infer a clean-environment install from the fact that modules import; during a
verification run it reports only `CURRENT_RUNTIME_ENVIRONMENT` and
`PINNED_ENVIRONMENT_MATCH` for the interpreter that is actually running.

### Verified environment inventory

Interpreter: CPython 3.12.14 (64-bit).

```
numpy==2.4.6      pandas==3.0.5     matplotlib==3.11.1  pytest==9.1.1
pillow==12.3.0    contourpy==1.4.0  cycler==0.12.1      fonttools==4.66.0
kiwisolver==1.5.1 packaging==26.3   pluggy==1.6.0       pygments==2.21.0
pyparsing==3.3.3  python-dateutil==2.9.0.post0          six==1.17.0
tzdata==2026.4    iniconfig==2.3.0  colorama==0.4.6
```

`scipy` and `pyarrow` are **not** installed and not required; nothing in
`run_all.py`, `scripts/` or `tests/` imports them.

---

## 2. Cross-platform frozen CSV byte identity

### 2.1 The defect found by the independent Linux audit

The v1.0 writer used `pandas.to_csv` without an explicit line terminator. pandas'
default terminator is `os.linesep`, so on Linux the reproduced CSV files used LF
while the frozen files use CRLF, and the frozen SHA256 comparisons failed even
though every value, schema and row order reproduced exactly.

### 2.2 The correction

`scripts/utils/tables.py` now pins the frozen CSV dialect explicitly:

```python
CSV_ENCODING = "utf-8-sig"
CSV_FLOAT_FORMAT = "%.12g"
CSV_LINE_TERMINATOR = "\r\n"

df.to_csv(
    target,
    index=False,
    encoding=CSV_ENCODING,
    float_format=CSV_FLOAT_FORMAT,
    lineterminator=CSV_LINE_TERMINATOR,
)
```

No analytical calculation was touched. `tests/test_cross_platform_csv.py`
enforces three things:

1. the writer really does pin the terminator, and no runnable file calls
   `to_csv` without an explicit terminator;
2. all eight frozen tables are pure CRLF on disk (no mixed line endings);
3. all eight tables reproduce **byte-identically to the frozen files** when the
   writer is exercised with `os.linesep` set to the Windows value (`"\r\n"`)
   *and* with `os.linesep` set to the Linux value (`"\n"`), and the two outputs
   are identical to each other.

### 2.3 Why the Linux condition is simulated rather than run natively

No native Linux runtime was available on the packaging machine: no WSL
distribution is installed (`wsl --list --verbose` reports no installed
distribution) and no container runtime is present. Installing a distribution
would require enabling a Windows optional feature and a reboot, which was not
performed because it would change the machine outside the scope of this task.

The Linux condition is therefore reproduced faithfully in
`tests/test_cross_platform_csv.py` by setting `os.linesep = "\n"` — the exact
value pandas consults on Linux — before the frozen writer is exercised for all
eight tables. pandas opens output files with `newline=""` and writes the
configured terminator literally, so with the terminator pinned the output is
independent of `os.linesep`; that independence is asserted directly by
`test_output_does_not_depend_on_os_linesep`.

**Residual limitation:** a native Linux execution of `python run_all.py` has not
been performed. On any Linux host, the verification is
`python run_all.py && pytest -q`, and it must report
`CROSS_PLATFORM_CSV_IDENTITY = PASS` with the same eight frozen SHA256 values,
because the writer no longer consults `os.linesep`. This limitation is stated
here rather than glossed over.

---

## 3. Determinism across delete-and-rerun

Sequence performed on the verified interpreter, with the package content final:

| Step | Action | Result |
| --- | --- | --- |
| A | Fresh interpreter and environment created (CPython 3.12.14) | created |
| B | Only the package-pinned dependencies installed | succeeded |
| C | Working directory set to the package root | ok |
| D | `python run_all.py` | exit code 0, `JOURNAL_VERIFICATION_PACKAGE_READY = True` |
| E | `pytest -q` | 100 % pass, 0 failed |
| F | `outputs_reproduced/` entirely deleted | removed |
| G | `python run_all.py` again, from scratch | exit code 0 |
| H | Every produced file re-hashed and compared with the first run | see below |

Artifact stability between the two runs:

| Artifact class | Run-to-run stability |
| --- | --- |
| All reproduced CSV tables in `outputs_reproduced/tables/` | byte-identical |
| All four 600 dpi PNG figures | byte-identical |
| PDF and SVG figures | content identical; bytes differ (embedded creation date / renderer identifiers) |
| `qc/reproduction_report.json` | differs only in the recorded runtime |
| figure QC records and the figure manifest | differ only in embedded generation timestamps |

Figure reproducibility is therefore asserted on **plotted values**, which are
verified exactly in `tests/test_figure_data.py`.

---

## 4. Distribution integrity

| Property | How it is verified | Result |
| --- | --- | --- |
| The manifest describes the distributed package | `scripts/utils/verify_manifest.py`, first step of `run_all.py`, and `tests/test_distribution_manifest.py` | PASS |
| The manifest is not rewritten by `run_all.py` | hash of `MANIFEST_SHA256.csv` captured before and after the run and compared | unchanged |
| Only `outputs_reproduced/` is written | hash snapshot of every distributed file before and after the run; reported as `modified_distributed_files` | empty |
| The distributed traceability map is static | `scripts/06_verify_manuscript_numbers.py` writes `outputs_reproduced/qc/manuscript_result_map_reproduced.csv` and compares it with `manuscript_mapping/manuscript_result_map.csv` | byte-identical |

`scripts/utils/build_manifest.py` remains in the package as a **packaging
utility only**: it is documented as "run only before final archive creation" and
is never invoked by `run_all.py`.

---

## 5. Changes in v1.1 relative to v1.0

1. **Cross-platform CSV byte reproduction.** The frozen CSV writer now pins
   `lineterminator="\r\n"`, so the eight core tables are byte-identical on
   Windows and Linux.
2. **City-name metadata corrected.** The frozen roster is
   `P001 Beijing, P003 Guangzhou, P004 Shenzhen, P005 Wuhan, P026 Luoyang,
   P037 Xining`, as verified against the frozen canonical city roster and the
   manuscript Methods (`REPRODUCIBILITY.md` §5.4). `00_preflight.py` now
   hard-checks this mapping, and `tests/test_city_metadata.py` fails if a stale
   v1.0 label reappears next to an exploration city identifier anywhere in the
   distributed package.
3. **Final-status logic corrected.** `JOURNAL_VERIFICATION_PACKAGE_READY` now
   requires every gate (manifest, preflight, Level A, Level B, figures, Source
   Data, manuscript numbers, pytest, absolute-path check, runtime environment,
   36/36 direction, zero test failures, manifest immutability and
   write-confinement). The fields `CLEAN_ENVIRONMENT_INSTALL` and
   `README_COMMANDS_TESTED` were removed because `run_all.py` cannot verify
   them; the historical fact is recorded in §1.
4. **Immutable distribution manifest.** `run_all.py` only verifies
   `MANIFEST_SHA256.csv`; regeneration moved to the documented packaging utility.
5. **Reproduction no longer rewrites distributed content.**
   `manuscript_mapping/manuscript_result_map.csv` is static; the reproduced map
   is compared against it inside `outputs_reproduced/`.
6. **Honest QC reporting.** `ABSOLUTE_PATH_CHECK` now comes from a dedicated
   `pytest tests/test_no_absolute_paths.py` run with its own exit status, not
   from the aggregate pytest result.
7. **Metadata cleaned.** `CITATION.cff` carries the real manuscript title and
   the explicit marker `AUTHOR_METADATA_PENDING_BEFORE_PUBLIC_DEPOSIT` instead
   of placeholders; `LICENSE.md` keeps MIT limited to code and records upstream
   licence dependencies, Overture attribution obligations and the absence of
   any asserted `GBA.Height` licence; `data/external_sources/README.md` now
   carries the manuscript's own source citations, landing pages and attribution
   text.
8. **Dependencies simplified.** `scipy` and `pyarrow` were removed from
   `requirements-lock.txt`, `environment.yml`, `pyproject.toml`, the README and
   the runtime version check. The clean-environment reproduction still passes.
9. **Data dictionary clarified.** `DATA_DICTIONARY.md` states explicitly that
   the sensitivity schema uses `dimension` and that no separate `delta_type`
   field exists.

## 6. Reproduction of the audit fixes

```
CITY_METADATA_CORRECTED = True
CROSS_PLATFORM_CSV_IDENTITY = PASS
DISTRIBUTION_MANIFEST_IMMUTABLE_DURING_RUN = True
RUN_ALL_MODIFIES_ONLY_OUTPUTS_REPRODUCED = True
SCIENTIFIC_RESULTS_CHANGED = False
```

---

## 7. Verification results — Windows, CPython 3.12.14 (pinned environment)

Package content final; `outputs_reproduced/` deleted before the run.

### 7.1 `python run_all.py`

```
FROZEN_INPUT_IDENTITY = PASS
CURRENT_RUNTIME_ENVIRONMENT = PASS
PINNED_ENVIRONMENT_MATCH = PASS
LEVEL_A_PAPER_REPRODUCTION = PASS
LEVEL_B_VALIDATION_RECOMPUTATION = PASS
DIRECTIONAL_VALIDATION = 36 / 36 SAME_SIGN
MANUSCRIPT_NUMERICAL_CHECKS = PASS
FIGURE_REPRODUCTION = PASS
SOURCE_DATA_EXPORT = PASS
PYTEST = PASS
DISTRIBUTION_MANIFEST = PASS
ABSOLUTE_PATH_CHECK = PASS

SCIENTIFIC_RESULTS_CHANGED = False
NEW_ANALYSIS = False
FORMAL_CANU_PRODUCTION_AUTHORIZED = False
FORMAL_CANU_GATES = UNCHANGED

JOURNAL_VERIFICATION_PACKAGE_READY = True

DISTRIBUTION_MANIFEST_IMMUTABLE_DURING_RUN = True
RUN_ALL_MODIFIES_ONLY_OUTPUTS_REPRODUCED = True
NEW_INTERPRETER_CACHES_OUTSIDE_OUTPUTS = 0
```

Exit code 0. Total runtime ≈ 21–22 s on the reference workstation. The
authoritative digest of `MANIFEST_SHA256.csv` is reported in the release
delivery notes rather than quoted here, because this file is itself distributed
content: quoting a digest of a manifest that lists this file would make the
record self-referential and could never be exact.

### 7.2 `pytest -q` (standalone, as documented in the README)

```
73 passed
```

0 failed, 0 errors.

### 7.3 Byte identity of the eight core reproduced tables

Every one of the eight tables matched the frozen file byte for byte, i.e. the
frozen SHA256 values themselves:

| Reproduced table | SHA256 | vs frozen |
| --- | --- | --- |
| `validation_correlations.csv` | `B0A2CCCB5B42DAEED12B51CDC129F681FC05946B3C42A11065E97CC10E35E75B` | byte-identical |
| `validation_direction_checks.csv` | `15E31E50CAAB5F6A786209BBBB8C1249EB4AB8F39E00601038046946CEE880E3` | byte-identical |
| `validation_summary_by_city.csv` | `2280D081A347AC1053872A2C167940E37DA4471E2B2D3326A7734FC53AD92B1F` | byte-identical |
| `validation_hypothesis_summary.csv` | `9CB157A722913EBD88ED7D3103E38DBE704BCA816338613944C92D3ABCCEF7C5` | byte-identical |
| `01_directional_concordance.csv` | `6DF36B770F23A2F49445156B5F7D881AECEF6B2B48239856F96098DBAC48EFC2` | byte-identical |
| `02_exploration_validation_magnitude_summary.csv` | `648F7B5412DA4DEC94C22D41A71E0CA194444E838B54C50E447CB2E318FBD98C` | byte-identical |
| `03_scale_coverage_metric_sensitivity.csv` | `8012B2B3CAD38E4AAA19A9DA91E49F362A77BC023646AFBCE5BDC6402A0CD082` | byte-identical |
| `04_relationship_robustness_profile.csv` | `6ED93EF7528BE61924E1421E26BD77A83ECE54C3DFF4A6C41536B42AA2D7A494` | byte-identical |

### 7.4 Cross-platform evidence

Two independent checks were executed on Windows:

1. **In-process** (`tests/test_cross_platform_csv.py`, 6 tests, all passing):
   the writer is exercised for all eight tables with `os.linesep` set to the
   Windows value and to the Linux value; both runs are byte-identical to the
   frozen files, and to each other.
2. **Script-entry-point emulation**: the real stage entry points
   (`scripts/01_reproduce_validation.py`, `scripts/02_reproduce_synthesis.py`)
   were executed with `os.linesep` forced to `"\n"`. Result:
   `LINUX_LINESEP_EMULATION_CSV_IDENTITY = PASS` — all eight tables
   byte-identical to the frozen files.

**Native Linux execution status: NOT EXECUTED on this machine.** No WSL
distribution is installed and no container runtime is available, and enabling
them would require changing the machine's Windows features and rebooting. This
is stated plainly rather than presented as a Linux run. On a Linux host the
verification is `python run_all.py && pytest -q`; it must reproduce the same
eight frozen SHA256 values, because the writer no longer consults `os.linesep`.
