# Upstream data sources

This package reproduces the manuscript from **frozen processed analytical
inputs**. It does not require, does not download and does not redistribute the
upstream raw data. This file records provenance, citations, acquisition routes
and attribution obligations so that the frozen analytical inputs can be traced
back to their sources and, if required, rebuilt (optional Level C).

---

## 1. Frozen source releases

| Role | Product | Frozen release | Citation | Attribution obligation |
| --- | --- | --- | --- | --- |
| Building footprints (`building_coverage_mean`) | Overture Buildings | `2026-08-19.0` | Reference 7, below | Yes — must be carried by any redistribution of derived data |
| Roads (`road_density_mean_km_per_km2`) | Overture Roads (transportation theme) | `2026-08-19.0` | Reference 7, below | Yes — must be carried by any redistribution of derived data |
| Building height (`height_conditional_mean_m`) | GlobalBuildingAtlas `GBA.Height` | `GBA.Height` raster product | Reference 8, below | Terms set by the product's publishers; see §4 |

These are the releases actually used to construct the frozen analytical inputs.
**Do not silently substitute a newer release.** Reproducing the frozen chain
requires the same releases.

---

## 2. Overture Maps Foundation — Buildings and Roads, release `2026-08-19.0`

**Citation (manuscript reference 7):**

> Overture Maps Foundation. *Overture Maps 2026-08-19.0 release notes and data
> documentation* (2026). Buildings and transportation themes used in the frozen
> morphology workflow.

**Publisher and landing pages:**

* Overture Maps Foundation — <https://overturemaps.org>
* Release downloads and release notes — <https://overturemaps.org/download/>
* Data documentation and schema reference — <https://docs.overturemaps.org/>
* Organisation and tooling on GitHub — <https://github.com/OvertureMaps>

**Acquisition:** the frozen release is obtained from the Overture Maps public
release channels under the release tag `2026-08-19.0`. The documentation linked
above states the current distribution channels (public cloud object storage and
the published download tooling) and the exact release-tag naming scheme. Use the
documented channel rather than a mirror.

**Required attribution text:**

Any redistribution of data derived from Overture Buildings or Overture Roads
**must carry the attribution required by that release**, naming the publisher
and the frozen release tag. The authoritative wording is the one shipped with
the release itself. Copy it verbatim; do not paraphrase. The elements that must
appear are:

```
Overture Maps Foundation — Overture Buildings and Overture Roads,
release 2026-08-19.0
```

**Licence terms:** Overture data is published by the Overture Maps Foundation
under its own licence and attribution requirements, stated in the release
documentation linked above. Whether the applicable terms impose share-alike or
equivalent obligations on a derivative database has **not** been evaluated by
this package and must be confirmed by the corresponding author before any public
deposit of the derived analytical data. See `LICENSE.md` §3.1.

---

## 3. GlobalBuildingAtlas — `GBA.Height`

**Citation (manuscript reference 8):**

> Zhu, X. X., Chen, S., Zhang, F., Shi, Y. & Wang, Y. GlobalBuildingAtlas: an
> open global and complete dataset of building polygons, heights and LoD1 3D
> models. *Earth System Science Data* **17**, 6647–6668 (2025).
> <https://doi.org/10.5194/essd-17-6647-2025>

**Product:** the `GBA.Height` raster product, tiled by 1° × 1° geographic
blocks. Height support determines which 50 m cells carry valid building height;
cells without valid support remain missing throughout the analysis.

**Acquisition:** obtain the `GBA.Height` tiles covering the study cities from the
distribution channel stated in the product's own documentation and in the
publication above. The study used the tiles intersecting each city's frozen
analysis mask.

**Licence terms:** the terms of use of `GBA.Height` are set by its publishers.
**This package asserts no licence for `GBA.Height`,** does not redistribute any
GBA raster data, and does not claim that any particular licence applies. The
applicable terms must be read from the product's own documentation and
confirmed by the corresponding author before the derived-data licence is
finalised. See `LICENSE.md` §3.2.

---

## 4. Raw variables required for a full rebuild (optional Level C)

The 50 m analysis grid is built from the following per-cell quantities:

* building footprint covered area (m²) and building coverage fraction
* road length (m) and road length density (km km⁻²)
* building-height support area and height support fraction of built-overlap
* cell geolocation on the 50 m analysis grid
* the frozen per-city analysis mask used for boundary intersections

Aggregated to the 1 km (20 × 20 cells of 50 m) and 5 km (100 × 100 cells of
50 m) analysis windows, these produce the per-window columns documented in
`../../DATA_DICTIONARY.md`.

## 5. Rebuild procedure (optional, never run by `python run_all.py`)

1. Acquire the Overture Buildings and Overture Roads releases tagged
   `2026-08-19.0` for the study cities.
2. Acquire the GlobalBuildingAtlas `GBA.Height` tiles covering those cities.
3. Regenerate the 50 m morphological grid using the frozen variable
   definitions, then aggregate to the 1 km and 5 km windows.

The raw archives are orders of magnitude larger than the frozen analytical
inputs, so the normal reproduction command never downloads them. Steps 1–3 are
optional and are **not** required to reproduce any manuscript number or figure.

## 6. Redistribution limits

The upstream products remain subject to their own licences and terms of use and
are therefore referenced rather than bundled. The frozen derived inputs
distributed in `data/frozen_inputs/` and `data/validation_windows/` are
derivative analytical products; their licence is currently recorded as
`FINAL_DERIVED_DATA_LICENCE = PENDING_AUTHOR_CONFIRMATION` in `LICENSE.md` §2
and must be stated before public deposit.
