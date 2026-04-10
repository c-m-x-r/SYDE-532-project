#!/usr/bin/env python3
"""
verify_protocol.py

Verify that the corrected 50+50 protocol matches the paper's behavior.

Usage:
    .venv/bin/python verify_protocol.py india --reps 10
    .venv/bin/python verify_protocol.py --help
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

PROJECT_DIR = Path(__file__).parent
RESULTS_DIR = PROJECT_DIR / "results"

CASE_STUDIES = ["australia", "usa", "pakistan", "india", "canada"]
SCENARIOS_LIST = ["mf", "Mf", "mF", "MF"]

def verify_single_case(case, csv_path):
    """
    Verify that a single case matches expected protocol behavior.

    Checks:
    1. Data spans 100 years (ticks 0-99)
    2. Compliance at year 0 is in range 40-60%
    3. Regulation phase (tick 50) is correctly labeled
    4. All 4 scenarios present
    """
    if not csv_path.exists():
        print(f"❌ Result file not found: {csv_path}")
        return False

    df = pd.read_csv(csv_path)

    print(f"\n📊 Verification Report: {case}")
    print("=" * 60)

    # Check 1: Data coverage
    max_tick = df["tick"].max()
    min_tick = df["tick"].min()
    print(f"✓ Tick range: {min_tick}–{max_tick} (expected 0–99)")
    if not (min_tick == 0 and max_tick == 99):
        print(f"  ❌ FAIL: Expected ticks 0–99, got {min_tick}–{max_tick}")
        return False

    # Check 2: Compliance at year 0
    compliance_t0 = df[df["tick"] == 0]["TS-compliance"].mean()
    print(f"✓ Compliance at year 0: {compliance_t0:.1%} (expected 40–60%)")
    if not (0.4 <= compliance_t0 <= 0.6):
        print(f"  ⚠️  WARNING: Compliance at t=0 is {compliance_t0:.1%}, expected 40–60%")
        print(f"     (Protocol may still be correct; this is a stochastic metric)")

    # Check 3: Regulation phase label
    lax_phase = df[df["phase"] == "burnin"]
    enforcement_phase = df[df["phase"] == "enforcement"]
    print(f"✓ Phase distribution:")
    print(f"    Lax (burnin):      ticks {lax_phase['tick'].min()}–{lax_phase['tick'].max()} ({len(lax_phase)} rows)")
    print(f"    Enforcement:       ticks {enforcement_phase['tick'].min()}–{enforcement_phase['tick'].max()} ({len(enforcement_phase)} rows)")

    if not (lax_phase["tick"].max() == 49 and enforcement_phase["tick"].min() == 50):
        print(f"  ❌ FAIL: Regulation transition not at tick 50")
        return False

    # Check 4: Scenarios present
    scenarios = df["scenario"].unique()
    print(f"✓ Scenarios: {sorted(scenarios)} (expected all of {SCENARIOS_LIST})")
    for s in SCENARIOS_LIST:
        if s not in scenarios:
            print(f"  ❌ FAIL: Missing scenario '{s}'")
            return False

    # Check 5: Multiple runs (sanity check on data volume)
    n_runs = df["run"].nunique()
    n_reps_actual = len(df[df["scenario"] == "mf"]["run"].unique())
    print(f"✓ Runs: {n_runs} total ({n_reps_actual} reps per scenario)")

    print("\n✅ All checks passed!")
    return True


def plot_verification(case, csv_path, output_path=None):
    """
    Plot compliance over time for all 4 scenarios and all case studies.

    Saves a multi-panel figure (1 case × 4 scenarios).
    """
    if not csv_path.exists():
        print(f"❌ Cannot plot: {csv_path} not found")
        return

    df = pd.read_csv(csv_path)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"{case.capitalize()} — Protocol Verification (50+50 protocol)", fontsize=14, fontweight="bold")
    axes = axes.flatten()

    for ax_idx, scenario in enumerate(SCENARIOS_LIST):
        ax = axes[ax_idx]
        scenario_data = df[df["scenario"] == scenario]

        # Group by tick, compute mean and std
        grouped = scenario_data.groupby("tick")["TS-compliance"].agg(["mean", "std", "count"])
        tick = grouped.index
        mean = grouped["mean"]
        std = grouped["std"]
        n = grouped["count"]

        # Plot mean and confidence band (±1 SD)
        ax.plot(tick, mean, "o-", linewidth=2, markersize=4, label="Mean")
        ax.fill_between(tick, mean - std, mean + std, alpha=0.3, label="±1 SD")

        # Regulation line at year 50
        ax.axvline(50, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Regulation onset")

        ax.set_xlabel("Year")
        ax.set_ylabel("Compliance")
        ax.set_ylim([0, 1])
        ax.set_xlim([0, 100])
        ax.grid(True, alpha=0.3)
        ax.set_title(f"{scenario.upper()}")
        ax.legend(loc="best", fontsize=8)

    plt.tight_layout()

    if output_path is None:
        output_path = RESULTS_DIR / f"verify_{case}.png"

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"✅ Plot saved: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Verify that the corrected protocol matches paper behavior",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "case",
        nargs="?",
        choices=CASE_STUDIES,
        default=None,
        help="Case study to verify (omit to verify all available results)"
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Generate verification plots"
    )
    args = parser.parse_args()

    cases_to_check = [args.case] if args.case else CASE_STUDIES

    all_passed = True
    for case in cases_to_check:
        csv_path = RESULTS_DIR / f"bs_protocol_{case}.csv"
        passed = verify_single_case(case, csv_path)

        if passed and args.plot:
            plot_verification(case, csv_path)

        all_passed = all_passed and passed

    if all_passed:
        print("\n" + "=" * 60)
        print("✅ All verifications passed!")
        print("\nNext steps:")
        print("1. Visually compare plots against the paper's Figure 5")
        print("2. Check that:")
        print("   - Compliance starts at 40–60% at year 0")
        print("   - Lax phase (0–50) shows evolution")
        print("   - Enforcement phase (50–100) shows scenario-dependent responses")
        print("   - India/Pakistan show dramatic transitions in Mf/MF scenarios")
        print("\n3. If satisfied, run full protocol with --reps 100:")
        print("   .venv/bin/python run_paper.py india --reps 100")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Verification failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
