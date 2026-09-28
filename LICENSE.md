# Licences

This package contains three legally distinct classes of material. They are
licensed separately and must not be conflated.

```
AUTHOR_METADATA_PENDING_BEFORE_PUBLIC_DEPOSIT
FINAL_DERIVED_DATA_LICENCE = PENDING_AUTHOR_CONFIRMATION
```

---

## 1. Code — MIT

All source code in this package (`run_all.py`, `run_all.bat`, `run_all.ps1`,
`scripts/`, `tests/`) is released under the MIT Licence. The MIT Licence
applies to the code only; it does not extend to any data file.

```
MIT License

Copyright (c) 2026 WP-MORPH authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 2. Derived analytical data — licence pending author confirmation

The frozen analytical products distributed in this package are:

* `data/frozen_inputs/**` — frozen WP-MORPH-03, WP-MORPH-05B and WP-MORPH-05C
  result tables;
* `data/validation_windows/**` — frozen WP-MORPH-05A aggregated 1 km and 5 km
  validation windows;
* `outputs_expected/**` — frozen reference tables and figures.

These are derivative products computed from third-party upstream data (see §3).
Because a derivative database may inherit obligations from its upstream
sources, **no licence is asserted here for these data files**. Their final
licence is

```
FINAL_DERIVED_DATA_LICENCE = PENDING_AUTHOR_CONFIRMATION
```

and must be stated explicitly by the corresponding author before public
deposit. Until then, they may be inspected and used to verify the associated
manuscript.

## 3. Upstream third-party sources — obligations that must be honoured

None of the upstream products below are redistributed in this package. They are
referenced, and the obligations they impose on derivative works are recorded
here.

### 3.1 Overture Buildings and Overture Roads, release `2026-08-19.0`

Publisher: Overture Maps Foundation. Citation as given in the associated
manuscript (reference 7):

> Overture Maps Foundation. *Overture Maps 2026-08-19.0 release notes and data
> documentation* (2026). Buildings and transportation themes used in the frozen
> morphology workflow.

Attribution and licence terms:

* Overture data is published by the Overture Maps Foundation with its own
  licence and attribution requirements, stated in the documentation shipped
  with the release.
* Any redistribution of a derivative database built from Overture Buildings or
  Overture Roads must carry the **attribution required by that release** and
  must not misrepresent the source.
* Required attribution must name the publisher (**Overture Maps Foundation**)
  and the exact frozen release tag (**`2026-08-19.0`**). The authoritative
  attribution wording and licence text are the ones distributed with the
  release itself; consult the release documentation before ANY public deposit
  and copy the required wording verbatim rather than paraphrasing it.
* Share-alike or equivalent obligations attaching to a derivative database
  under the applicable Overture licence terms have **not** been evaluated here
  and must be confirmed by the corresponding author before deposit. This is the
  main reason the derived-data licence in §2 is marked pending.

### 3.2 GlobalBuildingAtlas `GBA.Height`

Publisher: the GlobalBuildingAtlas authors. Citation as given in the associated
manuscript (reference 8):

> Zhu, X. X., Chen, S., Zhang, F., Shi, Y. & Wang, Y. GlobalBuildingAtlas: an
> open global and complete dataset of building polygons, heights and LoD1 3D
> models. *Earth System Science Data* **17**, 6647–6668 (2025).
> https://doi.org/10.5194/essd-17-6647-2025

**No licence is asserted for `GBA.Height` by this package.** The product's terms
of use are set by its publishers and must be read from the product's own
documentation. This package does not redistribute GBA raster data and makes no
statement about its licence. If the derived-data licence in §2 is to be
finalised, the corresponding author must confirm the applicable GBA terms
first.

## 4. Summary table

| Material | Licence | Status |
| --- | --- | --- |
| `run_all.py`, `run_all.bat`, `run_all.ps1`, `scripts/**`, `tests/**`, `pyproject.toml` | MIT | Final |
| Documentation (`README.md`, `REPRODUCIBILITY.md`, `DATA_DICTIONARY.md`, `METHODS_MAPPING.md`, `DETERMINISM_VERIFICATION.md`, `CITATION.cff`, `config/**` metadata) | MIT, unless otherwise stated | Final |
| `data/frozen_inputs/**`, `data/validation_windows/**`, `outputs_expected/**` | **Pending author confirmation** | `FINAL_DERIVED_DATA_LICENCE = PENDING_AUTHOR_CONFIRMATION` |
| Overture Buildings / Overture Roads `2026-08-19.0` | Third-party; not redistributed | Attribution and share-alike obligations **must be confirmed** |
| GlobalBuildingAtlas `GBA.Height` | Third-party; **no licence asserted here** | Terms must be read from the product documentation |

## 5. Outstanding items before public deposit

1. `AUTHOR_METADATA_PENDING_BEFORE_PUBLIC_DEPOSIT` — the author list, ORCIDs and
   affiliations must be added to `CITATION.cff`.
2. `FINAL_DERIVED_DATA_LICENCE = PENDING_AUTHOR_CONFIRMATION` — the licence for
   the derived analytical data must be stated.
3. The verbatim Overture attribution wording required by release
   `2026-08-19.0` must be copied into this file.
4. The applicable GlobalBuildingAtlas `GBA.Height` terms must be confirmed.
