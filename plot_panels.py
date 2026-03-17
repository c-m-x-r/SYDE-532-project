"""
plot_panels.py

Generate multi-panel Figure 5 reproduction + Canada extension.

Usage:
    .venv/bin/python plot_panels.py                  # all available
    .venv/bin/python plot_panels.py australia india   # specific panels
"""

import sys
from pathlib import Path
from analysis import load_tidy, plot_figure5

RESULTS_DIR = Path(__file__).parent / "results"
FIGS_DIR = Path(__file__).parent / "figures"

PANEL_LABELS = {
    "australia": "Australia (MDB)",
    "usa":       "USA (Central Valley)",
    "pakistan":   "Pakistan (Punjab)",
    "india":     "India (Punjab)",
    "canada":    "Canada (Paskapoo)",
}


def main():
    requested = [a.lower() for a in sys.argv[1:]] if len(sys.argv) > 1 else None

    case_dfs = {}
    for name, label in PANEL_LABELS.items():
        if requested and name not in requested:
            continue
        csv = RESULTS_DIR / f"paper_protocol_{name}.csv"
        if csv.exists():
            case_dfs[label] = load_tidy(str(csv))
            print(f"Loaded {name}: {case_dfs[label]['run'].nunique()} runs")
        else:
            print(f"Skipping {name}: {csv} not found")

    if not case_dfs:
        print("No data found!")
        sys.exit(1)

    tag = "_".join(requested) if requested else "all"
    out = FIGS_DIR / f"figure5_{tag}.png"
    plot_figure5(case_dfs, output_path=out, display_slice=(0, 100), regulation_year=50)


if __name__ == "__main__":
    main()
