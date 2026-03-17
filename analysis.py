"""
Analysis and plotting for Groundwater Commons Game BehaviorSpace output.

CSV format: one row per run, metrics as NetLogo list strings e.g. "[0.5 0.6 ...]"
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import ast
import re
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
FIGS_DIR = Path(__file__).parent / "figures"
FIGS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_nl_list(s):
    """Convert NetLogo list string '[0.1 0.2 ...]' to numpy array."""
    if not isinstance(s, str):
        return np.array([float(s)])
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        return np.array([float(x) for x in s[1:-1].split()])
    return np.array([float(s)])


def load_behaviorspace(csv_path):
    """
    Load a BehaviorSpace table CSV into a tidy DataFrame.
    Returns one row per (run, tick) with all parameters and metrics.
    """
    path = Path(csv_path)
    # Header is on row 6 (0-indexed row 5); rows 0-4 are metadata
    df_raw = pd.read_csv(path, skiprows=6, low_memory=False)
    df_raw.columns = df_raw.columns.str.strip().str.replace('"', '')

    all_metrics = [
        "TS-norm-strength", "TS-compliance", "TS-gini-wealth",
        "TS-decision-representative-farmer",
        "TS-drawdowns-mean", "TS-drawdowns-std",
        "TS-profits-mean", "TS-cummulative-wealth-median",
        "TS-total-breaches", "TS-boldness", "TS-vengefulness",
    ]
    metric_cols = [m for m in all_metrics if m in df_raw.columns]
    param_cols = [c for c in df_raw.columns if c not in metric_cols
                  and c not in ("[run number]", "steps", "[step]")]

    # Expand each run into per-tick rows
    records = []
    for _, row in df_raw.iterrows():
        run = row.get("[run number]", np.nan)
        ts_len = len(parse_nl_list(row[metric_cols[0]]))
        for t in range(ts_len):
            rec = {"run": run, "tick": t}
            for p in param_cols:
                rec[p] = row[p]
            for m in metric_cols:
                arr = parse_nl_list(row[m])
                rec[m] = arr[t] if t < len(arr) else np.nan
            records.append(rec)

    df = pd.DataFrame(records)
    # Clean up column names
    df.columns = df.columns.str.strip('"')
    return df


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------

SCENARIO_LABELS = {
    (0.1, 0.1): "mf",
    (0.5, 0.1): "Mf",
    (0.1, 0.9): "mF",
    (0.5, 0.9): "MF",
}

def label_scenarios(df):
    df = df.copy()
    df["scenario"] = df.apply(
        lambda r: SCENARIO_LABELS.get(
            (round(r["max-monitoring-capacity"], 1),
             round(r["fine-magnitude"], 1)), "other"
        ), axis=1
    )
    return df


# ---------------------------------------------------------------------------
# Plotting: Figure 5 style compliance trajectories
# ---------------------------------------------------------------------------

SCENARIO_COLORS = {"mf": "#888888", "Mf": "#2196F3", "mF": "#FF9800", "MF": "#4CAF50"}

REGULATION_YEAR = 50   # vertical line position in display
DISPLAY_SLICE   = (50, 150)  # which TS indices to show (last 50 burn-in + first 50 measurement)

ROW_METRICS = [
    ("TS-compliance",    "Compliance [%]",             (0, 1),    None),
    ("TS-total-breaches","Cumul. illegal extractions",  None,      None),
    ("TS-drawdowns-mean","Mean drawdown [m]",           None,      None),
    # row 4: two metrics on same axes
]

def _plot_scenario_band(ax, df, metric, ylim=None, scale=1.0, cumulative=False,
                        display_slice=None, regulation_year=None):
    lo, hi = display_slice if display_slice is not None else DISPLAY_SLICE
    reg    = regulation_year if regulation_year is not None else REGULATION_YEAR
    df = label_scenarios(df)
    for scenario in ["mf", "Mf", "mF", "MF"]:
        sub = df[(df["scenario"] == scenario) & (df["tick"] >= lo) & (df["tick"] < hi)].copy()
        if sub.empty:
            continue
        sub["year"] = sub["tick"] - lo        # re-index: 0 = start of display window

        if cumulative:
            # Cumulative sum per run within the display window, then aggregate
            sub = sub.sort_values(["run", "year"])
            sub[metric] = sub.groupby("run")[metric].cumsum()

        grouped = sub.groupby("year")[metric]
        mean = grouped.mean() * scale
        std  = grouped.std()  * scale
        color = SCENARIO_COLORS[scenario]
        ax.plot(mean.index, mean.values, label=scenario, color=color, linewidth=1.5)
        ax.fill_between(mean.index,
                        mean.values - std.values,
                        mean.values + std.values,
                        alpha=0.25, color=color)
    ax.axvline(reg, color="black", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlim(0, hi - lo)
    if ylim:
        ax.set_ylim(*ylim)
    ax.tick_params(labelsize=8)


def plot_figure5(case_dfs: dict, output_path=None, display_slice=None, regulation_year=None):
    """
    Reproduce Figure 5: 4-row × N-column grid.
    Rows: compliance | illegal extractions | drawdown | boldness+vengefulness
    display_slice and regulation_year override the module-level defaults.
    Use display_slice=(0,100), regulation_year=50 for the paper-protocol tidy CSV.
    """
    # Allow per-call overrides of the module-level constants
    _slice = display_slice if display_slice is not None else DISPLAY_SLICE
    _reg   = regulation_year if regulation_year is not None else REGULATION_YEAR
    n = len(case_dfs)
    fig, axes = plt.subplots(4, n, figsize=(5 * n, 12), sharex=True)
    if n == 1:
        axes = axes.reshape(4, 1)

    # scale for breach: ha × 9.5 ML/ha / 1000 GL/ML / 10000 ha = GL/10⁴ ha per year
    BREACH_SCALE = 9.5 / 1000 / 10000

    row_specs = [
        ("TS-compliance",    "Compliance [%]",                (0, 100), 100.0,        False),
        ("TS-total-breaches","Cumul. illegal extr. [GL/10⁴ha]", None,  BREACH_SCALE, True),
        ("TS-drawdowns-mean","Mean drawdown below\npre-dev. [m]", None, 1.0,          False),
    ]

    for col, (label, df) in enumerate(case_dfs.items()):
        # Rows 0–2
        for row, (metric, ylabel, ylim, scale, cumul) in enumerate(row_specs):
            ax = axes[row][col]
            if metric in df.columns:
                _plot_scenario_band(ax, df, metric, ylim=ylim, scale=scale,
                                    cumulative=cumul, display_slice=_slice,
                                    regulation_year=_reg)
            if col == 0:
                ax.set_ylabel(ylabel, fontsize=9)
            if row == 0:
                ax.set_title(label, fontsize=11)
            if row == 2:
                ax.set_xlabel("Years", fontsize=9)
                ax.invert_yaxis()   # 0 at top; more depletion = further down, matching paper

        # Row 3: boldness + vengefulness on same axes
        ax = axes[3][col]
        lo, hi = _slice
        df_s = label_scenarios(df)
        for scenario in ["mf", "Mf", "mF", "MF"]:
            sub = df_s[(df_s["scenario"] == scenario) &
                       (df_s["tick"] >= lo) & (df_s["tick"] < hi)].copy()
            if sub.empty:
                continue
            sub["year"] = sub["tick"] - lo
            color = SCENARIO_COLORS[scenario]
            for metric, ls in [("TS-boldness", "-"), ("TS-vengefulness", "--")]:
                if metric not in sub.columns:
                    continue
                g = sub.groupby("year")[metric]
                mean, std = g.mean(), g.std()
                ax.plot(mean.index, mean.values, linestyle=ls, color=color,
                        linewidth=1.2, label=f"{scenario} {metric.split('-')[1][:4]}")
                ax.fill_between(mean.index, mean.values - std, mean.values + std,
                                alpha=0.2, color=color)
        ax.axvline(_reg, color="black", linestyle="--", linewidth=1, alpha=0.7)
        ax.set_xlim(0, hi - lo)
        ax.set_xlabel("Years", fontsize=9)
        if col == 0:
            ax.set_ylabel("Boldness / Vengefulness", fontsize=9)
        ax.tick_params(labelsize=8)

    # Shared legend from first column compliance panel
    handles, labels = axes[0][0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper right", fontsize=8,
                   title="Scenario", bbox_to_anchor=(1.0, 0.98))

    # Column annotation: left = no regulation, right = regulation
    lo, hi = _slice
    for col in range(n):
        ax = axes[0][col]
        ax.text(_reg / 2, ax.get_ylim()[1] * 0.95,
                "No reg.", ha="center", va="top", fontsize=7, color="grey")
        ax.text(_reg + (hi - lo - _reg) / 2,
                ax.get_ylim()[1] * 0.95,
                "Regulation", ha="center", va="top", fontsize=7, color="grey")

    fig.suptitle("Hydro-social trajectories by enforcement scenario", fontsize=12, y=1.01)
    fig.tight_layout()

    path = output_path or FIGS_DIR / "figure5_reproduction.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved: {path}")
    return fig


# ---------------------------------------------------------------------------
# Filter to a specific case study's cultural parameters
# ---------------------------------------------------------------------------

# From paper: Grid/Group → S-enforcement-cost / S-reputation (approx mapping)
CASE_STUDY_PARAMS = {
    # S-enforcement-cost = Grid
    # S-reputation = 1 - Group  (paper formula: S = group^n × (1-grid)^m;
    #                             code formula: S = (1-S_rep)^n × (1-S_enf)^m
    #                             → S_rep = 1-group)
    "Australia":     {"S-enforcement-cost": 0.2, "S-reputation": 0.2},   # Grid=0.2, Group=0.8
    "USA":           {"S-enforcement-cost": 0.4, "S-reputation": 0.6},   # Grid=0.4, Group=0.4
    "Pakistan":      {"S-enforcement-cost": 0.8, "S-reputation": 0.6},   # Grid=0.8, Group=0.4
    "India":         {"S-enforcement-cost": 0.8, "S-reputation": 0.4},   # Grid=0.8, Group=0.6
}

def filter_case_study(df, case_study):
    params = CASE_STUDY_PARAMS[case_study]
    mask = pd.Series(True, index=df.index)
    for col, val in params.items():
        if col in df.columns:
            mask &= (df[col].astype(float).round(1) == round(val, 1))
    return df[mask]


# ---------------------------------------------------------------------------
# Tidy loader (for paper_protocol output — one row per run/year)
# ---------------------------------------------------------------------------

def load_tidy(csv_path):
    """Load paper-protocol tidy CSV (one row per run/year, no list parsing needed)."""
    return pd.read_csv(csv_path)


# ---------------------------------------------------------------------------
# PV comparison plot
# ---------------------------------------------------------------------------

PV_LEVEL_LABELS = {0.0: "No PV (0%)", 0.5: "50% PV", 1.0: "100% PV"}


def plot_pv_comparison(csv_path, output_path=None, display_slice=(0, 100), regulation_year=50):
    """
    For the freemarket case, plot compliance trajectories faceted by pv-adoption-fraction.
    Rows = compliance, drawdown, boldness/vengefulness.
    Columns = pv adoption level {0.0, 0.5, 1.0}.
    """
    df = load_tidy(csv_path)
    pv_levels = sorted(df["pv-adoption-fraction"].unique())
    n_cols = len(pv_levels)

    row_specs = [
        ("TS-compliance",    "Compliance [%]",           (0, 100), 100.0, False),
        ("TS-drawdowns-mean","Mean drawdown below\npre-dev. [m]", None,  1.0,   False),
    ]

    fig, axes = plt.subplots(3, n_cols, figsize=(5 * n_cols, 10), sharex=True)
    if n_cols == 1:
        axes = axes.reshape(3, 1)

    for col, pv_frac in enumerate(pv_levels):
        sub_df = df[df["pv-adoption-fraction"] == pv_frac]
        title = PV_LEVEL_LABELS.get(pv_frac, f"PV={pv_frac}")

        # Rows 0–1
        for row, (metric, ylabel, ylim, scale, cumul) in enumerate(row_specs):
            ax = axes[row][col]
            if metric in sub_df.columns:
                _plot_scenario_band(ax, sub_df, metric, ylim=ylim, scale=scale,
                                    cumulative=cumul, display_slice=display_slice,
                                    regulation_year=regulation_year)
            if col == 0:
                ax.set_ylabel(ylabel, fontsize=9)
            if row == 0:
                ax.set_title(title, fontsize=11)
            if row == 1:
                ax.invert_yaxis()

        # Row 2: boldness + vengefulness
        ax = axes[2][col]
        lo, hi = display_slice
        df_s = label_scenarios(sub_df)
        for scenario in ["mf", "Mf", "mF", "MF"]:
            s = df_s[(df_s["scenario"] == scenario) &
                     (df_s["tick"] >= lo) & (df_s["tick"] < hi)].copy()
            if s.empty:
                continue
            s["year"] = s["tick"] - lo
            color = SCENARIO_COLORS[scenario]
            for metric, ls in [("TS-boldness", "-"), ("TS-vengefulness", "--")]:
                if metric not in s.columns:
                    continue
                g = s.groupby("year")[metric]
                mean, std = g.mean(), g.std()
                ax.plot(mean.index, mean.values, linestyle=ls, color=color,
                        linewidth=1.2,
                        label=f"{scenario} {metric.split('-')[1][:4]}" if col == 0 else "")
                ax.fill_between(mean.index, mean.values - std, mean.values + std,
                                alpha=0.2, color=color)
        ax.axvline(regulation_year, color="black", linestyle="--", linewidth=1, alpha=0.7)
        ax.set_xlim(0, hi - lo)
        ax.set_xlabel("Years", fontsize=9)
        if col == 0:
            ax.set_ylabel("Boldness / Vengefulness", fontsize=9)
        ax.tick_params(labelsize=8)

    handles, labels_leg = axes[0][0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels_leg, loc="upper right", fontsize=8,
                   title="Scenario", bbox_to_anchor=(1.0, 0.98))

    fig.suptitle("Agrivoltaic technology floor: Free Market archetype", fontsize=12, y=1.01)
    fig.tight_layout()

    path = output_path or FIGS_DIR / "pv_comparison_freemarket.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved: {path}")
    return fig


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else RESULTS_DIR / "MDB_test.csv"

    print(f"Loading {csv_path}...")
    df = load_behaviorspace(csv_path)
    print(f"Loaded {len(df)} rows ({df['run'].nunique()} runs, {df['tick'].nunique()} ticks)")
    print(f"Columns: {list(df.columns)}")

    df_aus = filter_case_study(df, "Australia")
    print(f"Australia subset: {df_aus['run'].nunique()} runs")

    plot_figure5({"Australia (MDB)": df_aus})
    print("Done.")
