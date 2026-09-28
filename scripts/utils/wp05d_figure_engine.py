#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WP-MORPH-05D  |  Frozen-result Figure Production (V1)

READ-ONLY reporting / visualisation stage.

Every plotted quantity is read directly from the frozen WP-MORPH-05C outputs.
Nothing is re-estimated, re-derived, re-weighted, re-ranked or tested.

  * no raw 50 m parquet, no WP05A window data
  * no correlation coefficient re-computation (WP03 / WP05B)
  * no Spearman rho / weighted Pearson r re-computation
  * no new statistical metric, no p-value, no confidence interval, no bootstrap,
    no significance test, no composite robustness score, no relationship ranking

Only presentation-level choices are made (marker size, line width, font size,
panel spacing, legend position, axis wording, figure size, tick formatting,
whitespace, annotation placement).

Development convenience: an optional ``--output-dir`` override exists purely so
that the layout can be dry-run outside the frozen output directory.  The
production output directory is OUTPUT_DIR below.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FormatStrFormatter, MultipleLocator  # noqa: E402

# Journal reproducibility package adaptation: keep interpreter caches out of
# the distributed tree even if this module is executed directly.
sys.dont_write_bytecode = True

# ---------------------------------------------------------------------------
# 1. Frozen source and output locations
# ---------------------------------------------------------------------------
#
# JOURNAL REPRODUCIBILITY PACKAGE ADAPTATION (presentation-neutral)
# -----------------------------------------------------------------
# The scientific logic of this module is copied verbatim from the frozen
# WP-MORPH-05D figure-production script (SHA256
# 3AC43986484D37658092E163605349911F907F478D37384CC6CFBEDD9930A4CF, retained in
# original_frozen_scripts/run_wp_morph05d_figures_v1.py).
#
# Exactly two operational changes were made: the two hard-coded absolute
# directories are replaced by directories derived from the package root, and a
# bytecode-cache guard was added above. No plotted value, row order, category
# order, colour limit, axis limit or aggregation is altered.

SOURCE_DIR = Path(__file__).resolve().parents[2] / "data" / "frozen_inputs" / "synthesis"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs_reproduced" / "figures"

F_SIGN = "01_directional_concordance.csv"
F_MAG = "02_exploration_validation_magnitude_summary.csv"
F_SENS = "03_scale_coverage_metric_sensitivity.csv"
F_PROF = "04_relationship_robustness_profile.csv"
F_QC = "qc_summary.json"
F_MANIFEST = "manifest.json"

ANALYTICAL_FILES = (F_SIGN, F_MAG, F_SENS, F_PROF)

SCRIPT_VERSION = "WP-MORPH-05D-FIGURE-PRODUCTION-V1"
WORK_PACKAGE = "WP-MORPH-05D"
REVISION = "PRESENTATION_ONLY_REVISION_V1"
REVISION_SCOPE = (
    "visualisation only: no frozen value, summary quantity, row order, relationship order, "
    "scale, selection, metric or analytical condition was changed, added, filtered or ranked"
)
PREVIOUS_VERSION_BACKUP = OUTPUT_DIR / "00_previous_version_backup"

# ---------------------------------------------------------------------------
# 2. Frozen category orders (never re-sorted, never re-ranked)
# ---------------------------------------------------------------------------

REL_ORDER = ("BUILDING_ROAD", "BUILDING_HEIGHT", "ROAD_HEIGHT")
REL_DISPLAY = {
    "BUILDING_ROAD": "Building\u2013road",
    "BUILDING_HEIGHT": "Building\u2013height",
    "ROAD_HEIGHT": "Road\u2013height",
}

PHASE_ORDER = ("EXPLORATION", "VALIDATION")
PHASE_DISPLAY = {"EXPLORATION": "Exploration", "VALIDATION": "Validation"}
PHASE_CITIES = {
    "EXPLORATION": ("P004", "P026", "P037"),
    "VALIDATION": ("P001", "P003", "P005"),
}

SCALE_ORDER = ("1km", "5km")
SCALE_DISPLAY = {"1km": "1 km", "5km": "5 km"}

SELECTION_ORDER = ("ALL", "COVERAGE_80")
SELECTION_DISPLAY = {"ALL": "All windows", "COVERAGE_80": "Coverage \u2265 80%"}
SELECTION_SHORT = {"ALL": "All", "COVERAGE_80": "Coverage \u2265 80%"}
SELECTION_COMPACT = {"ALL": "All", "COVERAGE_80": "Cov \u2265 80%"}

METRIC_ORDER = ("SPEARMAN_RHO", "WEIGHTED_PEARSON_R")
METRIC_DISPLAY = {
    "SPEARMAN_RHO": "Spearman rho",
    "WEIGHTED_PEARSON_R": "Weighted Pearson r",
}
METRIC_SHORT = {
    "SPEARMAN_RHO": "Spearman \u03c1",
    "WEIGHTED_PEARSON_R": "Weighted Pearson r",
}

# fixed eight analytical conditions, nested scale -> selection -> metric
CONDITIONS = tuple(
    (s, sel, m) for s in SCALE_ORDER for sel in SELECTION_ORDER for m in METRIC_ORDER
)
SCALE_GROUP_SIZE = len(SELECTION_ORDER) * len(METRIC_ORDER)  # four rows per scale

DELTA_DEFINITION = {
    "SCALE": "\u0394 = 5 km \u2212 1 km",
    "COVERAGE": "\u0394 = COVERAGE_80 \u2212 ALL",
    "METRIC": "\u0394 = weighted Pearson r \u2212 Spearman rho",
}

# ---------------------------------------------------------------------------
# 3. Global graphical style (Nature-like, restrained, print safe)
# ---------------------------------------------------------------------------

BLACK = "#1a1a1a"
DARK = "#333333"
GREY = "#9a9a9a"
LIGHT = "#dcdcdc"
FAINT = "#ececec"
SINGLE_HUE = "#2b6ca3"
NEUTRAL = "#333333"        # panel A directional markers (no categorical meaning)
WHISKER = "#c9c9c9"        # frozen city min-max whiskers (lighter than connectors)
CONNECTOR = "#8c8c8c"      # exploration-to-validation median connector (darker, slightly thicker)
CONNECTOR_SOFT = "#c2c2c2"  # Fig. S2 range connectors (lighter, markers stay dominant)

SEQ_CMAP = LinearSegmentedColormap.from_list(
    "wp05d_sequential",
    ["#f8fbfe", "#dfeaf5", "#b9d3e8", "#8ab3d7", "#548ec0", "#2b6ca3", "#12406e"],
)
DIV_CMAP = LinearSegmentedColormap.from_list(
    "wp05d_diverging",
    [
        "#12456e",
        "#3d7cb0",
        "#9dc3e0",
        "#e8f1f7",
        "#f7f7f7",
        "#f5d6cf",
        "#e0a08c",
        "#b85c4a",
        "#8f2f22",
    ],
)

FS_PANEL = 11.0
FS_TITLE = 9.5
FS_AXIS = 9.0
FS_TICK = 8.0
FS_LEGEND = 8.0
FS_ANNOT = 8.0


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "font.size": FS_AXIS,
            "axes.titlesize": FS_TITLE,
            "axes.labelsize": FS_AXIS,
            "xtick.labelsize": FS_TICK,
            "ytick.labelsize": FS_TICK,
            "legend.fontsize": FS_LEGEND,
            "axes.linewidth": 0.8,
            "axes.edgecolor": BLACK,
            "axes.labelcolor": BLACK,
            "text.color": BLACK,
            "xtick.color": BLACK,
            "ytick.color": BLACK,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "xtick.minor.width": 0.6,
            "ytick.minor.width": 0.6,
            "xtick.major.size": 2.6,
            "ytick.major.size": 2.6,
            "xtick.minor.size": 1.6,
            "ytick.minor.size": 1.6,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "lines.linewidth": 0.9,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.edgecolor": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "legend.frameon": False,
            "figure.dpi": 150,
        }
    )


# ---------------------------------------------------------------------------
# 4. Small helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest().upper()


def _fig(width_mm: float, height_mm: float):
    return plt.figure(figsize=(width_mm / 25.4, height_mm / 25.4), facecolor="white")


def _rect(x_mm, y_mm, w_mm, h_mm, W, H):
    """Axes rectangle in figure fractions from millimetre coordinates (y from bottom)."""
    return [x_mm / W, y_mm / H, w_mm / W, h_mm / H]


def _text_above(
    ax, text, dy_pt, dx_pt=0.0, fontsize=FS_ANNOT, weight="normal", color=None
):
    """Text anchored just above the top-left corner of the axes (offset in points)."""
    ax.annotate(
        text,
        xy=(0.0, 1.0),
        xycoords="axes fraction",
        xytext=(dx_pt, dy_pt),
        textcoords="offset points",
        fontsize=fontsize,
        fontweight=weight,
        color=color if color is not None else BLACK,
        ha="left",
        va="bottom",
        clip_on=False,
        annotation_clip=False,
    )


def _panel_label(ax, letter, title=None, dy_pt=2.5, title_gap_pt=10.0):
    _text_above(ax, letter, dy_pt, fontsize=FS_PANEL, weight="bold")
    if title:
        _text_above(
            ax, title, dy_pt - 1.0, dx_pt=title_gap_pt, fontsize=FS_TITLE
        )


def _whisker(ax, low, high, y, color=WHISKER, cap=0.05, lw=0.55):
    ax.plot([low, high], [y, y], color=color, lw=lw, zorder=1, solid_capstyle="butt")
    ax.plot([low, low], [y - cap, y + cap], color=color, lw=lw, zorder=1)
    ax.plot([high, high], [y - cap, y + cap], color=color, lw=lw, zorder=1)


def _conditional_tick_label(scale, selection, metric):
    return f"{SELECTION_SHORT[selection]} \u00b7 {METRIC_SHORT[metric]}"


def _fmt(value, digits=3):
    return f"{value:.{digits}f}"


def _text_colour_on(seq_cmap, fraction):
    """Black or white annotation text depending on the background luminance."""
    r, g, b, _ = seq_cmap(min(max(fraction, 0.0), 1.0))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#ffffff" if luminance < 0.52 else BLACK


def save_figure(fig, stem: str, output_dir: Path):
    paths = {}
    for ext in ("png", "pdf", "svg"):
        path = output_dir / f"{stem}.{ext}"
        fig.savefig(path, dpi=600, facecolor="white", edgecolor="none")
        paths[ext] = path
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# 5. WP05C preflight (hard gate, executed before any figure is drawn)
# ---------------------------------------------------------------------------


def run_preflight() -> dict:
    print("WP-MORPH-05D FIGURE PRODUCTION V1")
    print()
    print("SOURCE:")
    print("WP-MORPH-05C frozen outputs only")
    print()
    print("NEW_ANALYSIS_ALLOWED:")
    print("False")
    print()
    print("--- WP05C SOURCE PREFLIGHT ---")
    print(f"SOURCE_DIR: {SOURCE_DIR}")

    qc_path = SOURCE_DIR / F_QC
    manifest_path = SOURCE_DIR / F_MANIFEST

    checks = []
    checks.append(("qc_summary.json present", qc_path.is_file(), str(qc_path)))
    checks.append(("manifest.json present", manifest_path.is_file(), str(manifest_path)))

    if not (qc_path.is_file() and manifest_path.is_file()):
        for label, ok, detail in checks:
            print(f"{'PASS' if ok else 'FAIL'}  {label}  ({detail})")
        print("WP05C_SOURCE_QC: FAIL")
        print("WP-MORPH-05D STOPPED BEFORE FIGURE PRODUCTION")
        sys.exit(1)

    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    required = [
        ("overall_qc == PASS", qc.get("overall_qc"), "PASS"),
        ("input_identity_qc == PASS", qc.get("input_identity_qc"), "PASS"),
        ("same_sign_units == 36", qc.get("same_sign_units"), 36),
        ("sign_reversal_units == 0", qc.get("sign_reversal_units"), 0),
        ("coefficients_reestimated == false", qc.get("coefficients_reestimated"), False),
        ("p_values_computed == false", qc.get("p_values_computed"), False),
        (
            "no_method_changed_after_results == true",
            qc.get("no_method_changed_after_results"),
            True,
        ),
    ]
    for label, actual, expected in required:
        checks.append(
            (
                label,
                actual == expected and type(actual) is type(expected),
                f"observed: {actual!r}",
            )
        )

    manifest_hashes = {
        entry["file_name"]: entry["sha256"].upper()
        for entry in manifest.get("generated_outputs", [])
    }
    for name in ANALYTICAL_FILES:
        path = SOURCE_DIR / name
        present = path.is_file()
        digest = sha256_file(path) if present else ""
        expected = manifest_hashes.get(name)
        checks.append((f"frozen input present: {name}", present, ""))
        checks.append(
            (f"frozen input sha256 match: {name}", digest == expected, f"{digest[:16]}...")
        )

    all_ok = True
    for label, ok, detail in checks:
        all_ok = all_ok and bool(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))

    if not all_ok:
        print("WP05C_SOURCE_QC: FAIL")
        print("WP-MORPH-05D STOPPED BEFORE FIGURE PRODUCTION")
        sys.exit(1)

    print("WP05C_SOURCE_QC: PASS")
    print()
    return {"qc": qc, "manifest": manifest}


# ---------------------------------------------------------------------------
# 6. Frozen inputs
# ---------------------------------------------------------------------------


REQUIRED_COLUMNS = {
    F_SIGN: (
        "relationship",
        "validation_unit_count",
        "same_sign_count",
        "sign_reversal_count",
    ),
    F_MAG: (
        "relationship",
        "scale",
        "selection",
        "metric",
        "exploration_median",
        "exploration_min",
        "exploration_max",
        "validation_median",
        "validation_min",
        "validation_max",
        "exploration_range",
        "validation_range",
    ),
    F_SENS: (
        "phase",
        "city_id",
        "relationship",
        "dimension",
        "conditioning_scale_or_selection",
        "metric",
        "signed_delta",
    ),
    F_PROF: (
        "phase",
        "relationship",
        "median_abs_scale_delta",
        "median_abs_coverage_delta",
        "median_abs_metric_delta",
    ),
}


def load_inputs():
    sign = pd.read_csv(SOURCE_DIR / F_SIGN)
    mag = pd.read_csv(SOURCE_DIR / F_MAG)
    sens = pd.read_csv(SOURCE_DIR / F_SENS)
    prof = pd.read_csv(SOURCE_DIR / F_PROF)

    for frame, name in ((sign, F_SIGN), (mag, F_MAG), (sens, F_SENS), (prof, F_PROF)):
        missing = [c for c in REQUIRED_COLUMNS[name] if c not in frame.columns]
        if missing:
            raise RuntimeError(f"frozen input {name} lacks required columns: {missing}")
        block = frame[list(REQUIRED_COLUMNS[name])]
        if block.isna().any().any():
            bad = sorted(block.columns[block.isna().any()].tolist())
            raise RuntimeError(f"missing value in plotted columns of {name}: {bad}")
    return sign, mag, sens, prof


def magnitude_row(mag: pd.DataFrame, relationship, scale, selection, metric) -> pd.Series:
    hit = mag[
        (mag["relationship"] == relationship)
        & (mag["scale"] == scale)
        & (mag["selection"] == selection)
        & (mag["metric"] == metric)
    ]
    if len(hit) != 1:
        raise RuntimeError(
            "expected exactly one frozen row for "
            f"{relationship}/{scale}/{selection}/{metric}, found {len(hit)}"
        )
    return hit.iloc[0]


def shared_xlim(mag: pd.DataFrame):
    """Common frozen coefficient range for Figure 1 panels B-D (identical for all three)."""
    low = float(mag[["exploration_min", "validation_min"]].to_numpy().min())
    high = float(mag[["exploration_max", "validation_max"]].to_numpy().max())
    lo = min(0.0, np.floor(low * 10.0) / 10.0)
    hi = max(0.9, np.ceil(high * 10.0) / 10.0)
    return lo, hi


# ---------------------------------------------------------------------------
# 7. Figure 1 - directional reproducibility and magnitude concordance
# ---------------------------------------------------------------------------


def draw_panel_a(ax, sign: pd.DataFrame):
    table = sign.set_index("relationship")
    rows = list(REL_ORDER)
    ys = list(range(len(rows)))[::-1]

    n_units = int(table.loc[rows[0], "validation_unit_count"])
    ax.axvline(n_units, color=FAINT, lw=0.9, zorder=0)

    total_same = 0
    total_units = 0
    for y, rel in zip(ys, rows):
        record = table.loc[rel]
        units = int(record["validation_unit_count"])
        same = int(record["same_sign_count"])
        reversals = int(record["sign_reversal_count"])
        if reversals != 0:
            raise RuntimeError(
                "frozen WP05C directional concordance reports a sign reversal"
            )
        total_same += same
        total_units += units
        ax.plot([0, units], [y, y], color=LIGHT, lw=1.2, solid_capstyle="round", zorder=1)
        ax.plot([units], [y], marker="o", ms=3.6, mfc=NEUTRAL, mec=NEUTRAL, zorder=3)
        ax.text(
            units + 0.35,
            y,
            f"{same} / {units}",
            va="center",
            ha="left",
            fontsize=FS_TICK,
            clip_on=False,
        )

    ax.set_yticks(ys)
    ax.set_yticklabels([REL_DISPLAY[r] for r in rows])
    ax.set_ylim(-0.62, len(rows) - 0.38)
    ax.set_xlim(-0.2, float(n_units) + 0.2)
    ax.set_xticks(list(range(0, n_units + 1, 2)))
    ax.set_xlabel("Validation units retaining expected direction", labelpad=2.5)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)

    return total_same, total_units


def draw_magnitude_panel(ax, mag: pd.DataFrame, relationship: str, xlim, letter: str):
    ys = list(range(len(CONDITIONS)))[::-1]
    offset = 0.16

    ax.axhline(
        (len(CONDITIONS) - SCALE_GROUP_SIZE) - 0.5, color=FAINT, lw=0.9, zorder=0
    )

    for y, (scale, selection, metric) in zip(ys, CONDITIONS):
        record = magnitude_row(mag, relationship, scale, selection, metric)
        e_lo, e_hi = float(record["exploration_min"]), float(record["exploration_max"])
        v_lo, v_hi = float(record["validation_min"]), float(record["validation_max"])
        e_med = float(record["exploration_median"])
        v_med = float(record["validation_median"])

        y_e, y_v = y + offset, y - offset
        _whisker(ax, e_lo, e_hi, y_e)
        _whisker(ax, v_lo, v_hi, y_v)
        ax.plot([e_med, v_med], [y_e, y_v], color=CONNECTOR, lw=1.0, zorder=2)
        ax.plot(
            [e_med], [y_e], marker="o", ms=3.3, mfc="white", mec=BLACK, mew=0.8, zorder=3
        )
        ax.plot([v_med], [y_v], marker="s", ms=3.0, mfc=BLACK, mec=BLACK, zorder=3)

    ax.set_yticks(ys)
    ax.set_yticklabels([_conditional_tick_label(*c) for c in CONDITIONS])
    ax.set_ylim(-0.62, len(CONDITIONS) - 0.38)
    ax.set_xlim(*xlim)
    ax.xaxis.set_major_locator(MultipleLocator(0.2))
    ax.xaxis.set_minor_locator(MultipleLocator(0.1))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.set_xlabel("Correlation coefficient", labelpad=2.5)
    ax.tick_params(axis="y", length=0)

    for group, scale in enumerate(SCALE_ORDER):
        centre = float(ys[group * SCALE_GROUP_SIZE + SCALE_GROUP_SIZE // 2 - 1])
        ax.text(
            -0.435,
            centre,
            SCALE_DISPLAY[scale],
            transform=ax.get_yaxis_transform(),
            rotation=90,
            va="center",
            ha="center",
            fontsize=FS_TICK,
            color=DARK,
        )

    _panel_label(ax, letter, REL_DISPLAY[relationship])


def make_figure1(sign, mag, output_dir: Path):
    xlim = shared_xlim(mag)
    W, H = 180.0, 164.0
    fig = _fig(W, H)

    ax_a = fig.add_axes(_rect(56.0, 134.0, 103.0, 17.0, W, H))
    ax_b = fig.add_axes(_rect(56.0, 95.0, 118.0, 23.0, W, H))
    ax_c = fig.add_axes(_rect(56.0, 58.0, 118.0, 23.0, W, H))
    ax_d = fig.add_axes(_rect(56.0, 21.0, 118.0, 23.0, W, H))

    same, units = draw_panel_a(ax_a, sign)
    _panel_label(
        ax_a,
        "A",
        "Independent directional reproducibility",
        dy_pt=12.0,
        title_gap_pt=10.5,
    )
    _text_above(
        ax_a,
        f"{same}/{units} preregistered validation units retained the expected positive "
        "direction (0 sign reversals).",
        dy_pt=2.4,
        color=DARK,
    )

    draw_magnitude_panel(ax_b, mag, "BUILDING_ROAD", xlim, "B")
    draw_magnitude_panel(ax_c, mag, "BUILDING_HEIGHT", xlim, "C")
    draw_magnitude_panel(ax_d, mag, "ROAD_HEIGHT", xlim, "D")

    handles = [
        Line2D(
            [],
            [],
            marker="o",
            ms=3.3,
            mfc="white",
            mec=BLACK,
            mew=0.8,
            ls="none",
            label="Exploration median (P004, P026, P037)",
        ),
        Line2D(
            [],
            [],
            marker="s",
            ms=3.0,
            mfc=BLACK,
            mec=BLACK,
            ls="none",
            label="Validation median (P001, P003, P005)",
        ),
        Line2D(
            [],
            [],
            color=WHISKER,
            lw=0.7,
            label="Frozen city min\u2013max",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.010),
        ncol=3,
        handletextpad=0.5,
        columnspacing=1.6,
        fontsize=FS_LEGEND,
    )

    paths = save_figure(fig, "Fig_main_1_direction_magnitude", output_dir)
    entries = [
        {
            "figure": "Figure 1",
            "panel": "A",
            "source_file": F_SIGN,
            "source_columns": [
                "relationship",
                "validation_unit_count",
                "same_sign_count",
                "sign_reversal_count",
            ],
            "row_filter": (
                "all rows; relationship order BUILDING_ROAD, BUILDING_HEIGHT, ROAD_HEIGHT"
            ),
            "row_count_used": int(len(sign)),
            "any_new_metric_computed": False,
        }
    ]
    for letter, rel in zip(("B", "C", "D"), REL_ORDER):
        entries.append(
            {
                "figure": "Figure 1",
                "panel": letter,
                "source_file": F_MAG,
                "source_columns": [
                    "relationship",
                    "scale",
                    "selection",
                    "metric",
                    "exploration_median",
                    "exploration_min",
                    "exploration_max",
                    "validation_median",
                    "validation_min",
                    "validation_max",
                ],
                "row_filter": (
                    f"relationship == {rel} (8 of 24 rows; fixed scale/selection/metric order)"
                ),
                "row_count_used": int((mag["relationship"] == rel).sum()),
                "any_new_metric_computed": False,
            }
        )
    return paths, entries


# ---------------------------------------------------------------------------
# 8. Figure 2 - relationship-specific robustness structure
# ---------------------------------------------------------------------------


PROFILE_COLUMNS = (
    ("median_abs_scale_delta", "Scale"),
    ("median_abs_coverage_delta", "Coverage"),
    ("median_abs_metric_delta", "Metric / weighting"),
)


def profile_matrix(prof: pd.DataFrame, phase: str):
    matrix = np.zeros((len(REL_ORDER), len(PROFILE_COLUMNS)))
    for i, rel in enumerate(REL_ORDER):
        hit = prof[(prof["phase"] == phase) & (prof["relationship"] == rel)]
        if len(hit) != 1:
            raise RuntimeError(f"expected exactly one frozen profile row for {phase}/{rel}")
        for j, (column, _) in enumerate(PROFILE_COLUMNS):
            matrix[i, j] = float(hit.iloc[0][column])
    return matrix


def make_figure2(prof, output_dir: Path):
    matrices = {phase: profile_matrix(prof, phase) for phase in PHASE_ORDER}
    vmax = float(max(m.max() for m in matrices.values()))
    vmin = 0.0

    W, H = 180.0, 54.0
    fig = _fig(W, H)
    ax_e = fig.add_axes(_rect(30.0, 9.0, 56.0, 31.0, W, H))
    ax_v = fig.add_axes(_rect(94.0, 9.0, 56.0, 31.0, W, H))
    cax = fig.add_axes(_rect(157.0, 9.0, 5.0, 31.0, W, H))

    heat = None
    for ax, phase, letter in ((ax_e, "EXPLORATION", "a"), (ax_v, "VALIDATION", "b")):
        matrix = matrices[phase]
        heat = ax.imshow(
            matrix,
            cmap=SEQ_CMAP,
            vmin=vmin,
            vmax=vmax,
            origin="upper",
            aspect="auto",
            interpolation="nearest",
        )
        ax.set_xticks(np.arange(len(PROFILE_COLUMNS)))
        ax.set_xticklabels([label for _, label in PROFILE_COLUMNS])
        ax.xaxis.set_ticks_position("top")
        ax.tick_params(axis="x", which="both", length=0, pad=3)
        ax.set_yticks(np.arange(len(REL_ORDER)))
        ax.set_yticklabels([REL_DISPLAY[r] for r in REL_ORDER] if letter == "a" else [])
        ax.tick_params(axis="y", which="both", length=0)
        ax.set_xticks(np.arange(-0.5, len(PROFILE_COLUMNS), 1.0), minor=True)
        ax.set_yticks(np.arange(-0.5, len(REL_ORDER), 1.0), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.2)
        for spine in ax.spines.values():
            spine.set_visible(False)

        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = float(matrix[i, j])
                ax.text(
                    j,
                    i,
                    _fmt(value, 3),
                    ha="center",
                    va="center",
                    fontsize=FS_TICK,
                    color=_text_colour_on(SEQ_CMAP, (value - vmin) / (vmax - vmin)),
                )

        _panel_label(
            ax, letter, PHASE_DISPLAY[phase], dy_pt=18.0, title_gap_pt=8.0
        )

    cbar = fig.colorbar(heat, cax=cax)
    cbar.set_label("Median |\u0394 coefficient|", labelpad=4, fontsize=FS_AXIS)
    cbar.ax.tick_params(labelsize=FS_TICK, length=2.2, width=0.7)
    cbar.outline.set_linewidth(0.7)
    cbar.ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))

    paths = save_figure(fig, "Fig_main_2_robustness_structure", output_dir)
    entries = []
    for phase in PHASE_ORDER:
        entries.append(
            {
                "figure": "Figure 2",
                "panel": PHASE_DISPLAY[phase],
                "source_file": F_PROF,
                "source_columns": [
                    "phase",
                    "relationship",
                    "median_abs_scale_delta",
                    "median_abs_coverage_delta",
                    "median_abs_metric_delta",
                ],
                "row_filter": f"phase == {phase} (3 of 6 rows; relationship order fixed)",
                "row_count_used": int((prof["phase"] == phase).sum()),
                "any_new_metric_computed": False,
            }
        )
    presentation = {
        "colour_scale": "single-hue sequential, shared vmin/vmax across both panels",
        "vmin": vmin,
        "vmax": vmax,
        "note": "presentation parameter only; no statistic recomputed",
    }
    return paths, entries, presentation


# ---------------------------------------------------------------------------
# 9. Supplementary Figure S1 - full city-level sensitivity structure
# ---------------------------------------------------------------------------


def sensitivity_column_spec(dimension: str):
    """Frozen column layout inside one S1 block (two header levels, fixed order)."""
    if dimension == "SCALE":
        columns = [(sel, m) for m in METRIC_ORDER for sel in SELECTION_ORDER]
        headers = [
            (0.5, METRIC_SHORT["SPEARMAN_RHO"]),
            (2.5, METRIC_SHORT["WEIGHTED_PEARSON_R"]),
        ]
        sub = [SELECTION_COMPACT[c[0]] for c in columns]
        return columns, headers, sub
    if dimension == "COVERAGE":
        columns = [(s, m) for m in METRIC_ORDER for s in SCALE_ORDER]
        headers = [
            (0.5, METRIC_SHORT["SPEARMAN_RHO"]),
            (2.5, METRIC_SHORT["WEIGHTED_PEARSON_R"]),
        ]
        sub = [SCALE_DISPLAY[c[0]] for c in columns]
        return columns, headers, sub
    if dimension == "METRIC":
        columns = [
            (f"{s}|{sel}", "SPEARMAN_VS_WEIGHTED_PEARSON")
            for s in SCALE_ORDER
            for sel in SELECTION_ORDER
        ]
        headers = [(0.5, SCALE_DISPLAY["1km"]), (2.5, SCALE_DISPLAY["5km"])]
        sub = [SELECTION_COMPACT[c[0].split("|")[1]] for c in columns]
        return columns, headers, sub
    raise ValueError(dimension)


S1_BLOCKS = (
    ("SCALE", "Scale sensitivity"),
    ("COVERAGE", "Coverage sensitivity"),
    ("METRIC", "Metric / weighting sensitivity"),
)


def sensitivity_matrix(sens: pd.DataFrame, phase: str, dimension: str):
    """Nine rows (three cities x three relationships, fixed order) x four fixed columns."""
    columns, _, _ = sensitivity_column_spec(dimension)
    relation_rows = [(city, rel) for city in PHASE_CITIES[phase] for rel in REL_ORDER]
    matrix = np.full((len(relation_rows), len(columns)), np.nan)
    for i, (city, rel) in enumerate(relation_rows):
        for j, (conditioning, metric) in enumerate(columns):
            hit = sens[
                (sens["phase"] == phase)
                & (sens["city_id"] == city)
                & (sens["relationship"] == rel)
                & (sens["dimension"] == dimension)
                & (sens["conditioning_scale_or_selection"] == conditioning)
                & (sens["metric"] == metric)
            ]
            if len(hit) != 1:
                raise RuntimeError(
                    "expected exactly one frozen sensitivity row for "
                    f"{phase}/{city}/{rel}/{dimension}/{conditioning}/{metric}, "
                    f"found {len(hit)}"
                )
            matrix[i, j] = float(hit.iloc[0]["signed_delta"])
    if np.isnan(matrix).any():
        raise RuntimeError("unresolved sensitivity cell")
    return matrix


def make_figure_s1(sens, output_dir: Path):
    # widened so that both phases can carry their own independent city x relationship labels
    W = 214.0
    n_rows = len(PHASE_CITIES["EXPLORATION"]) * len(REL_ORDER)  # 9 city x relationship rows
    row_h = 4.4
    body_h = row_h * n_rows
    header_h = 20.0
    block_gap = 16.0
    top_margin = 8.0
    bottom_margin = 10.0
    H = (
        top_margin
        + len(S1_BLOCKS) * (header_h + body_h)
        + (len(S1_BLOCKS) - 1) * block_gap
        + bottom_margin
    )

    fig = _fig(W, H)
    x_label = 0.0
    x_expl, panel_w = 31.0, 62.0
    x_valid = x_expl + panel_w + 34.0  # the gap holds the Validation row labels
    x_cbar, cbar_w = x_valid + panel_w + 7.0, 5.0

    y_top = H - top_margin
    entries = []
    scale_limits = {}

    for letter, (dimension, title) in zip("ABC", S1_BLOCKS):
        columns, headers, sub_labels = sensitivity_column_spec(dimension)
        matrices = {
            phase: sensitivity_matrix(sens, phase, dimension) for phase in PHASE_ORDER
        }
        limit = float(
            np.abs(np.concatenate([m.ravel() for m in matrices.values()])).max()
        )
        scale_limits[dimension] = limit

        fig.text(
            x_label / W,
            (y_top - 0.5) / H,
            f"{letter}  {title}",
            fontsize=FS_TITLE,
            ha="left",
            va="top",
        )
        fig.text(
            (W - 2.0) / W,
            (y_top - 0.5) / H,
            DELTA_DEFINITION[dimension],
            fontsize=FS_ANNOT,
            color=DARK,
            ha="right",
            va="top",
        )

        body_top = y_top - header_h
        heat = None
        for phase, x0 in (("EXPLORATION", x_expl), ("VALIDATION", x_valid)):
            ax = fig.add_axes(_rect(x0, body_top - body_h, panel_w, body_h, W, H))
            matrix = matrices[phase]
            heat = ax.imshow(
                matrix,
                cmap=DIV_CMAP,
                vmin=-limit,
                vmax=limit,
                origin="upper",
                aspect="auto",
                interpolation="nearest",
            )
            ax.set_xticks(np.arange(len(columns)))
            ax.set_xticklabels([])
            ax.tick_params(
                axis="x", which="both", length=0, labeltop=False, labelbottom=False
            )
            ax.set_yticks(np.arange(n_rows))
            ax.set_yticklabels(
                [
                    f"{city}  {REL_DISPLAY[rel]}"
                    for city in PHASE_CITIES[phase]
                    for rel in REL_ORDER
                ]
            )
            ax.tick_params(axis="y", which="both", length=0, pad=2.0)
            ax.set_xticks(np.arange(-0.5, len(columns), 1.0), minor=True)
            ax.set_yticks(np.arange(-0.5, n_rows, 1.0), minor=True)
            ax.grid(which="minor", color="white", linewidth=0.8)
            for boundary in range(len(REL_ORDER), n_rows, len(REL_ORDER)):
                ax.axhline(boundary - 0.5, color="white", linewidth=1.6, zorder=2)
            for spine in ax.spines.values():
                spine.set_visible(False)

            for j, label in enumerate(sub_labels):
                ax.text(
                    j,
                    1.045,
                    label,
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="bottom",
                    fontsize=FS_TICK - 1.0,
                    color=DARK,
                    clip_on=False,
                )
            for x_centre, label in headers:
                ax.text(
                    x_centre,
                    1.175,
                    label,
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="bottom",
                    fontsize=FS_TICK - 0.5,
                    color=BLACK,
                    clip_on=False,
                )
            ax.text(
                (len(columns) - 1) / 2.0,
                1.30,
                PHASE_DISPLAY[phase],
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=FS_TICK,
                fontweight="bold",
                clip_on=False,
            )

        cax = fig.add_axes(_rect(x_cbar, body_top - body_h, cbar_w, body_h, W, H))
        cbar = fig.colorbar(heat, cax=cax)
        cbar.set_label("Signed \u0394 coefficient", labelpad=3, fontsize=FS_TICK + 0.5)
        cbar.ax.tick_params(labelsize=FS_TICK - 1.0, length=2.0, width=0.7)
        cbar.outline.set_linewidth(0.7)
        cbar.ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))

        entries.append(
            {
                "figure": "Supplementary Figure S1",
                "panel": letter,
                "source_file": F_SENS,
                "source_columns": [
                    "phase",
                    "city_id",
                    "relationship",
                    "dimension",
                    "conditioning_scale_or_selection",
                    "metric",
                    "signed_delta",
                ],
                "row_filter": (
                    f"dimension == {dimension}; fixed city order "
                    f"(Exploration {', '.join(PHASE_CITIES['EXPLORATION'])}; "
                    f"Validation {', '.join(PHASE_CITIES['VALIDATION'])}); "
                    "fixed relationship order"
                ),
                "row_count_used": int((sens["dimension"] == dimension).sum()),
                "any_new_metric_computed": False,
            }
        )
        y_top = body_top - body_h - block_gap

    paths = save_figure(fig, "Fig_S1_city_level_sensitivity", output_dir)
    return paths, entries, scale_limits


# ---------------------------------------------------------------------------
# 10. Supplementary Figure S2 - cross-city coefficient dispersion
# ---------------------------------------------------------------------------


def draw_dispersion_panel(ax, mag: pd.DataFrame, relationship: str, letter: str, xlim):
    ys = list(range(len(CONDITIONS)))[::-1]
    offset = 0.17

    ax.axhline(
        (len(CONDITIONS) - SCALE_GROUP_SIZE) - 0.5, color=FAINT, lw=0.9, zorder=0
    )

    for y, (scale, selection, metric) in zip(ys, CONDITIONS):
        record = magnitude_row(mag, relationship, scale, selection, metric)
        e = float(record["exploration_range"])
        v = float(record["validation_range"])
        y_e, y_v = y + offset, y - offset
        ax.plot([e, v], [y_e, y_v], color=CONNECTOR_SOFT, lw=0.7, zorder=2)
        ax.plot([e], [y_e], marker="o", ms=3.3, mfc="white", mec=BLACK, mew=0.8, zorder=3)
        ax.plot([v], [y_v], marker="s", ms=3.0, mfc=BLACK, mec=BLACK, zorder=3)

    ax.set_yticks(ys)
    ax.set_yticklabels([_conditional_tick_label(*c) for c in CONDITIONS])
    ax.set_ylim(-0.62, len(CONDITIONS) - 0.38)
    ax.set_xlim(*xlim)
    ax.xaxis.set_major_locator(MultipleLocator(0.1))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.set_xlabel("Cross-city coefficient range (max \u2212 min)", labelpad=2.5)
    ax.tick_params(axis="y", length=0)

    for group, scale in enumerate(SCALE_ORDER):
        centre = float(ys[group * SCALE_GROUP_SIZE + SCALE_GROUP_SIZE // 2 - 1])
        ax.text(
            -0.435,
            centre,
            SCALE_DISPLAY[scale],
            transform=ax.get_yaxis_transform(),
            rotation=90,
            va="center",
            ha="center",
            fontsize=FS_TICK,
            color=DARK,
        )

    _panel_label(ax, letter, REL_DISPLAY[relationship])


def make_figure_s2(mag, output_dir: Path):
    high = float(mag[["exploration_range", "validation_range"]].to_numpy().max())
    xlim = (0.0, float(np.ceil(high * 10.0) / 10.0))

    W, H = 180.0, 152.0
    fig = _fig(W, H)
    rects = ((56.0, 113.0), (56.0, 68.0), (56.0, 23.0))
    for (x0, y0), letter, rel in zip(rects, "ABC", REL_ORDER):
        ax = fig.add_axes(_rect(x0, y0, 118.0, 22.0, W, H))
        draw_dispersion_panel(ax, mag, rel, letter, xlim)

    handles = [
        Line2D(
            [],
            [],
            marker="o",
            ms=3.3,
            mfc="white",
            mec=BLACK,
            mew=0.8,
            ls="none",
            label="Exploration range (P004, P026, P037)",
        ),
        Line2D(
            [],
            [],
            marker="s",
            ms=3.0,
            mfc=BLACK,
            mec=BLACK,
            ls="none",
            label="Validation range (P001, P003, P005)",
        ),
        Line2D([], [], color=CONNECTOR_SOFT, lw=0.9, label="Same analytical condition"),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.012),
        ncol=3,
        handletextpad=0.5,
        columnspacing=1.6,
        fontsize=FS_LEGEND,
    )

    paths = save_figure(fig, "Fig_S2_cross_city_dispersion", output_dir)
    entries = []
    for letter, rel in zip("ABC", REL_ORDER):
        entries.append(
            {
                "figure": "Supplementary Figure S2",
                "panel": letter,
                "source_file": F_MAG,
                "source_columns": [
                    "relationship",
                    "scale",
                    "selection",
                    "metric",
                    "exploration_range",
                    "validation_range",
                ],
                "row_filter": (
                    f"relationship == {rel} (8 of 24 rows; fixed scale/selection/metric order)"
                ),
                "row_count_used": int((mag["relationship"] == rel).sum()),
                "any_new_metric_computed": False,
            }
        )
    presentation = {
        "x_axis_limits": [xlim[0], xlim[1]],
        "note": "presentation parameter only; frozen ranges used as-is",
    }
    return paths, entries, presentation


# ---------------------------------------------------------------------------
# 11. Captions, audit, QC, manifest
# ---------------------------------------------------------------------------


def write_captions(output_dir: Path, xlim, fig2_vmax, s1_limits) -> Path:
    expl = ", ".join(PHASE_CITIES["EXPLORATION"])
    valid = ", ".join(PHASE_CITIES["VALIDATION"])
    source_files = (
        "`01_directional_concordance.csv`, `02_exploration_validation_magnitude_summary.csv`, "
        "`03_scale_coverage_metric_sensitivity.csv`, `04_relationship_robustness_profile.csv`"
    )
    text = f"""# WP-MORPH-05D figure captions

All values shown in these figures are frozen WP-MORPH-05C outputs: {source_files}.
No coefficient was re-estimated, no correlation was recomputed, and no statistical
test, p-value, confidence interval or composite robustness score is reported. No
relationship, city, scale, selection or metric was removed, and no relationship was
ranked.

Exploration phase = cities {expl}. Validation phase = cities {valid}.
Window selections: ALL = all windows; COVERAGE_80 = Coverage \u2265 80%.
Metrics / weighting formulations: Spearman rho and weighted Pearson r.
Spatial scales: 1 km and 5 km. Relationship order in every panel is
Building\u2013road, Building\u2013height, Road\u2013height.

---

## Figure 1 | Independent directional reproducibility and magnitude concordance

Panel A: preregistered validation units that retained the expected positive direction,
counted separately for each relationship. Each relationship retained the expected
positive direction in all 12 of its validation units (12 / 12 per relationship;
36 / 36 units overall) with 0 sign reversals. Source: 01_directional_concordance.csv.

Panels B-D: frozen exploration and validation correlation coefficients for
Building\u2013road (B), Building\u2013height (C) and Road\u2013height (D). Each row is one of the
eight analytical conditions defined by spatial scale (1 km, 5 km), window selection
(ALL, COVERAGE_80) and metric / weighting formulation (Spearman rho, weighted Pearson
r); rows are grouped by scale. Open circles are Exploration medians (cities {expl}) and
filled squares are Validation medians (cities {valid}); the thin line joins the two
medians of the same analytical condition, and grey whiskers span the frozen city
minimum\u2013maximum coefficient of that phase. No standard deviation, standard error,
confidence interval or significance value is computed or shown.
Source: 02_exploration_validation_magnitude_summary.csv.

Panels B-D share one common x-axis (correlation coefficient, {xlim[0]:.1f}-{xlim[1]:.1f}).
Coefficient magnitudes are not numerically identical between phases, and the magnitude
difference between phases differs between relationships and analytical conditions.

---

## Figure 2 | Relationship-specific robustness structure

Frozen median absolute coefficient change observed within each relationship when one
analytical dimension is varied, shown for Exploration (a, cities {expl}) and Validation
(b, cities {valid}). Source: 04_relationship_robustness_profile.csv.

Columns are the three sensitivity dimensions. Scale = median |\u0394 coefficient| across
{DELTA_DEFINITION['SCALE']}. Coverage = median |\u0394 coefficient| across
{DELTA_DEFINITION['COVERAGE']}. Metric / weighting = median |\u0394 coefficient| across
{DELTA_DEFINITION['METRIC']}. Cell values are printed as frozen in the source file to
three decimal places.

Both panels use identical colour limits (0 to {fig2_vmax:.3f}) and one shared sequential
colour scale, so Exploration and Validation can be compared directly. Plotted quantity:
median absolute coefficient change; identical colour scale in both panels. No robustness
threshold, no stable / unstable boundary, no ranking and no composite score is defined.
Across the frozen values, median absolute change associated with scale is generally
larger than that associated with coverage; the metric / weighting dimension is
comparatively large for Building\u2013height in both phases, and Road\u2013height shows
comparatively high median scale sensitivity in both phases.

---

## Supplementary Figure S1 | Full city-level sensitivity structure

Signed frozen deltas for every city \u00d7 relationship combination, shown separately for the
three sensitivity dimensions: A Scale sensitivity ({DELTA_DEFINITION['SCALE']}),
B Coverage sensitivity ({DELTA_DEFINITION['COVERAGE']}), C Metric / weighting
sensitivity ({DELTA_DEFINITION['METRIC']}). Source: 03_scale_coverage_metric_sensitivity.csv
(column signed_delta).

Within each block the Exploration matrix (cities {expl}) and the Validation matrix
(cities {valid}) are displayed side by side. Rows are city \u00d7 relationship in fixed order
(Building\u2013road, Building\u2013height, Road\u2013height), and each matrix carries its own
phase-specific row labels, so the Validation rows are labelled with the Validation cities
({valid}) and never share the Exploration labels. Columns are the four fixed
conditioning / metric combinations of that dimension and carry a three-level header with
exactly one label per bottom-level column: the phase (Exploration, Validation), then the
metric / weighting formulation (Spearman rho, weighted Pearson r) or the spatial scale
(1 km, 5 km), then the remaining conditioning factor (All = all windows; Cov = window
selection Coverage \u2265 80%, i.e. COVERAGE_80).

Colour is a diverging scale centred on zero that encodes the direction of change only
(negative delta versus positive delta); it does not encode quality or robustness. Each
block applies one symmetric limit to both phases (Scale \u00b1{s1_limits['SCALE']:.3f};
Coverage \u00b1{s1_limits['COVERAGE']:.3f}; Metric / weighting \u00b1{s1_limits['METRIC']:.3f}).
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

Panels are A Building\u2013road, B Building\u2013height, C Road\u2013height. Open circles are
Exploration ranges (cities {expl}) and filled squares are Validation ranges (cities
{valid}); the thin line joins the two ranges of the same analytical condition. Only the
frozen range columns are plotted (range = maximum minus minimum of the three cities); no
standard deviation, variance, coefficient of variation or interquartile dispersion is
computed.
"""
    path = output_dir / "figure_captions.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_data_audit(entries, output_dir: Path, source_run: Path) -> Path:
    audit = {
        "work_package": WORK_PACKAGE,
        "stage": "FROZEN_RESULT_FIGURE_PRODUCTION",
        "script_version": SCRIPT_VERSION,
        "revision": REVISION,
        "revision_scope": REVISION_SCOPE,
        "source_run": str(source_run),
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "any_new_metric_computed_all_false": all(
            entry["any_new_metric_computed"] is False for entry in entries
        ),
        "entries": entries,
    }
    path = output_dir / "figure_data_audit.json"
    path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def previous_version_info() -> dict:
    """Read-only provenance record of the superseded figure set, when preserved."""
    directory = PREVIOUS_VERSION_BACKUP
    if not directory.is_dir():
        return {"path": str(directory), "present": False, "files": {}}
    files = {
        path.name: sha256_file(path)
        for path in sorted(directory.iterdir())
        if path.is_file()
    }
    return {
        "path": str(directory),
        "present": True,
        "file_count": len(files),
        "files": files,
    }


def write_qc(
    output_dir: Path,
    qc_source: dict,
    sha_before: str,
    sha_after: str,
    figure_files: dict,
    source_hashes: dict,
) -> Path:
    qc = {
        "work_package": WORK_PACKAGE,
        "stage": "FROZEN_RESULT_FIGURE_PRODUCTION",
        "script_version": SCRIPT_VERSION,
        "revision": REVISION,
        "revision_scope": REVISION_SCOPE,
        "presentation_only_changes": [
            "Figure 1: min-max whiskers lightened and thinned below the median connector line weight",
            "Figure 1: Panel A directional markers changed from blue to neutral dark grey (no categorical meaning)",
            "Figure 2: interpretation sentence removed from the figure body and moved into the caption",
            "Figure S1: three-level hierarchical column headers, widened canvas, larger block spacing, group separator",
            "Figure S1: Exploration and Validation matrices each carry their own phase-specific "
            "city x relationship row labels (no shared exploration-only label column)",
            "Figure S1: explanatory paragraph removed from the figure body and moved into the caption",
            "Figure S2: range connector lines lightened; markers unchanged",
        ],
        "previous_version": previous_version_info(),
        "source_run": str(SOURCE_DIR),
        "source_work_package": qc_source.get("work_package"),
        "source_overall_qc": qc_source.get("overall_qc"),
        "source_input_identity_qc": qc_source.get("input_identity_qc"),
        "source_sha256_verified_against_manifest": source_hashes,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "RAW_50M_DATA_READ": False,
        "WP05A_WINDOW_DATA_READ": False,
        "CORRELATIONS_RECOMPUTED": False,
        "NEW_STATISTICAL_METRIC_COMPUTED": False,
        "P_VALUES_COMPUTED": False,
        "SIGNIFICANCE_TESTING_USED": False,
        "CITY_REMOVED": False,
        "RELATIONSHIP_REMOVED": False,
        "SCALE_REMOVED": False,
        "SELECTION_REMOVED": False,
        "METRIC_REMOVED": False,
        "RELATIONSHIP_RANKING_CREATED": False,
        "ROBUSTNESS_SCORE_CREATED": False,
        "FIGURE_DATA_SOURCE_ONLY_WP05C": True,
        "FORMAL_CANU_PRODUCTION_AUTHORIZED": False,
        "FORMAL_CANU_GATES": "UNCHANGED",
        "SCRIPT_SHA256_BEFORE_FIGURES": sha_before,
        "SCRIPT_SHA256_AFTER_FIGURES": sha_after,
        "NO_SCRIPT_CHANGED_AFTER_FIGURES": sha_before == sha_after,
        "FIGURES_GENERATED": len(figure_files),
        "FIGURE_FILES": {
            stem: {ext: str(path) for ext, path in paths.items()}
            for stem, paths in figure_files.items()
        },
        "FIGURE_QC": "PASS" if sha_before == sha_after else "FAIL",
    }
    path = output_dir / "figure_qc.json"
    path.write_text(json.dumps(qc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_manifest(
    output_dir: Path,
    produced_paths,
    script_path: Path,
    sha_before: str,
    sha_after: str,
    source_hashes: dict,
    figure_qc_value: str,
) -> Path:
    manifest = {
        "work_package": WORK_PACKAGE,
        "title": "Frozen-result Figure Production",
        "status": "NONPRODUCTION_FIGURE_PRODUCTION",
        "script_version": SCRIPT_VERSION,
        "revision": REVISION,
        "revision_scope": REVISION_SCOPE,
        "previous_version": previous_version_info(),
        "script_path": str(script_path),
        "script_sha256_before_figures": sha_before,
        "script_sha256_after_figures": sha_after,
        "output_dir": str(output_dir),
        "source_run": str(SOURCE_DIR),
        "source_work_package": "WP-MORPH-05C",
        "frozen_inputs": [
            {"file_name": name, "path": str(SOURCE_DIR / name), "sha256": digest}
            for name, digest in source_hashes.items()
        ],
        "generated_outputs": [
            {
                "role": f"WP05D_OUTPUT_{path.name}",
                "path": str(path),
                "file_name": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in produced_paths
        ],
        "figure_qc": figure_qc_value,
        "formal_canu_production_authorized": False,
        "formal_canu_gates": "UNCHANGED",
    }
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 12. Main
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="WP-MORPH-05D frozen-result figure production"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="development-only override of the production output directory",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    script_path = Path(__file__).resolve()

    preflight = run_preflight()

    output_dir.mkdir(parents=True, exist_ok=True)
    apply_style()

    sha_before = sha256_file(script_path)
    print("SCRIPT_SHA256_BEFORE_FIGURES:")
    print(sha_before)
    print()

    sign, mag, sens, prof = load_inputs()

    figure_files = {}

    fig1_paths, audit_entries = make_figure1(sign, mag, output_dir)
    figure_files["Fig_main_1_direction_magnitude"] = fig1_paths

    fig2_paths, fig2_entries, fig2_params = make_figure2(prof, output_dir)
    figure_files["Fig_main_2_robustness_structure"] = fig2_paths
    audit_entries.extend(fig2_entries)

    s1_paths, s1_entries, s1_limits = make_figure_s1(sens, output_dir)
    figure_files["Fig_S1_city_level_sensitivity"] = s1_paths
    audit_entries.extend(s1_entries)

    s2_paths, s2_entries, s2_params = make_figure_s2(mag, output_dir)
    figure_files["Fig_S2_cross_city_dispersion"] = s2_paths
    audit_entries.extend(s2_entries)

    audit_entries.extend(
        [
            {
                "figure": "Figure 2",
                "panel": "shared colour scale",
                "source_file": F_PROF,
                "source_columns": [
                    "median_abs_scale_delta",
                    "median_abs_coverage_delta",
                    "median_abs_metric_delta",
                ],
                "row_filter": "both phases (6 of 6 rows)",
                "row_count_used": int(len(prof)),
                "any_new_metric_computed": False,
                "presentation_parameters": fig2_params,
            },
            {
                "figure": "Supplementary Figure S2",
                "panel": "x-axis limits",
                "source_file": F_MAG,
                "source_columns": ["exploration_range", "validation_range"],
                "row_filter": "all 24 analytical conditions across the three relationships",
                "row_count_used": int(len(mag)),
                "any_new_metric_computed": False,
                "presentation_parameters": s2_params,
            },
        ]
    )

    manifest_source = preflight["manifest"]
    source_hashes = {name: sha256_file(SOURCE_DIR / name) for name in ANALYTICAL_FILES}
    for name, digest in source_hashes.items():
        expected = next(
            (
                entry["sha256"].upper()
                for entry in manifest_source.get("generated_outputs", [])
                if entry["file_name"] == name
            ),
            None,
        )
        if expected is not None and expected != digest:
            raise RuntimeError(f"frozen input changed during figure production: {name}")

    audit_path = write_data_audit(audit_entries, output_dir, SOURCE_DIR)
    captions_path = write_captions(
        output_dir, shared_xlim(mag), fig2_params["vmax"], s1_limits
    )

    sha_after = sha256_file(script_path)

    produced_paths = []
    for paths in figure_files.values():
        produced_paths.extend(paths[ext] for ext in ("png", "pdf", "svg"))
    produced_paths.extend([audit_path, captions_path])

    qc_path = write_qc(
        output_dir, preflight["qc"], sha_before, sha_after, figure_files, source_hashes
    )
    qc_value = json.loads(qc_path.read_text(encoding="utf-8"))["FIGURE_QC"]
    produced_paths.append(qc_path)

    manifest_path = write_manifest(
        output_dir, produced_paths, script_path, sha_before, sha_after, source_hashes, qc_value
    )

    print("=== WP-MORPH-05D FIGURE PRODUCTION COMPLETED ===")
    print()
    print("WP05C_SOURCE_QC: PASS")
    print(f"FIGURE_QC: {qc_value}")
    print()
    print("FIGURES_GENERATED:")
    print(len(figure_files))
    print()
    print("CORRELATIONS_RECOMPUTED:")
    print("False")
    print()
    print("NEW_STATISTICAL_METRIC_COMPUTED:")
    print("False")
    print()
    print("P_VALUES_COMPUTED:")
    print("False")
    print()
    print("RELATIONSHIP_RANKING_CREATED:")
    print("False")
    print()
    print("SCRIPT_SHA256_BEFORE_FIGURES:")
    print(sha_before)
    print()
    print("SCRIPT_SHA256_AFTER_FIGURES:")
    print(sha_after)
    print()
    print("NO_SCRIPT_CHANGED_AFTER_FIGURES:")
    print(sha_before == sha_after)
    print()
    print("FORMAL_CANU_PRODUCTION_AUTHORIZED:")
    print("False")
    print()
    print("FORMAL_CANU_GATES:")
    print("UNCHANGED")
    print()
    print("OUTPUT_DIR:")
    print(str(output_dir))
    print()
    print(f"(manifest: {manifest_path})")
    print()
    print("REVISION:")
    print(REVISION)
    print()
    print("PRESENTATION_ONLY:")
    print("True")

    return 0 if qc_value == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
