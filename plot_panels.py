"""
plot_panels.py

Generate multi-panel Figure 5 reproduction + Canada extension + PV comparison.

Usage:
    .venv/bin/python plot_panels.py                        # all available cases
    .venv/bin/python plot_panels.py australia india        # specific panels
    .venv/bin/python plot_panels.py --pv-compare freemarket  # PV sweep comparison
"""

import sys
from pathlib import Path
from analysis import load_tidy, plot_figure5, plot_pv_comparison

RESULTS_DIR = Path(__file__).parent / "results"
FIGS_DIR = Path(__file__).parent / "figures"

PANEL_LABELS = {
    "australia":  "Australia (MDB)",
    "usa":        "USA (Central Valley)",
    "pakistan":   "Pakistan (Punjab)",
    "india":      "India (Punjab)",
    "canada":     "Canada (Paskapoo)",
    "freemarket": "Free Market (Generic)",
}


def main():
    args = sys.argv[1:]

    # PV comparison mode
    if args and args[0] == "--pv-compare":
        case_names = args[1:] if len(args) > 1 else ["freemarket"]
        for name in case_names:
            csv = RESULTS_DIR / f"paper_protocol_{name}.csv"
            if not csv.exists():
                print(f"Not found: {csv}")
                continue
            out = FIGS_DIR / f"pv_comparison_{name}.png"
            FIGS_DIR.mkdir(exist_ok=True)
            plot_pv_comparison(str(csv), output_path=out,
                               display_slice=(0, 100), regulation_year=50)
        return

    # Standard Figure 5 mode
    # Prefix: --bs uses BehaviorSpace-faithful protocol output (bs_protocol_*.csv);
    # default uses our paper_protocol_*.csv.
    use_bs = "--bs" in args
    args = [a for a in args if a != "--bs"]

    # --dir <subdir>: look in results/<subdir>/ instead of results/
    results_dir = RESULTS_DIR
    if "--dir" in args:
        idx = args.index("--dir")
        subdir = args[idx + 1]
        results_dir = RESULTS_DIR / subdir
        args = args[:idx] + args[idx + 2:]

    prefix = "bs_protocol" if use_bs else "paper_protocol"
    # BehaviorSpace protocol output contains 50 burn-in years (ticks 0-49,
    # S-params=0, lax M/F — all scenarios identical) followed by 50 enforcement
    # years (ticks 50-99).  Regulation line at tick 50 matches Figure 5.
    display_slice   = (0, 100)
    regulation_year = 50

    requested = [a.lower() for a in args] if args else None

    case_dfs = {}
    for name, label in PANEL_LABELS.items():
        if requested and name not in requested:
            continue
        csv = results_dir / f"{prefix}_{name}.csv"
        if csv.exists():
            df = load_tidy(str(csv))
            # For multi-PV runs, default to pv=0 slice for the main figure
            if "pv-adoption-fraction" in df.columns:
                df = df[df["pv-adoption-fraction"] == 0.0]
            case_dfs[label] = df
            print(f"Loaded {name}: {case_dfs[label]['run'].nunique()} runs")
        else:
            print(f"Skipping {name}: {csv} not found")

    if not case_dfs:
        print("No data found!")
        sys.exit(1)

    FIGS_DIR.mkdir(exist_ok=True)
    dir_tag = f"{results_dir.name}_" if results_dir != RESULTS_DIR else ""
    tag = dir_tag + ("bs_" if use_bs else "") + ("_".join(requested) if requested else "all")
    out = FIGS_DIR / f"figure5_{tag}.png"
    plot_figure5(case_dfs, output_path=out, display_slice=display_slice,
                 regulation_year=regulation_year)


if __name__ == "__main__":
    main()
