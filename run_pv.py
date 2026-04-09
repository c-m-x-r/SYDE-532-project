"""
run_pv.py — Agrivoltaic PV extension experiment, 8 parallel workers.

Case study: Free Market archetype (generic cash crop, S-enf-cost=0.35, S-rep=0.65).

Protocol (shared seeds across PV levels so yr 0-24 is identical):
  yr  0-24: lax (M=0.1, F=0.1), no PV
  yr 25:    PV adoption event (SETUP-PV with --pv-fracs levels)
  yr 25-49: lax, with PV
  yr 50-99: enforcement scenario, with PV

Output: results/pv_freemarket.csv

Usage:
    .venv/bin/python run_pv.py
    .venv/bin/python run_pv.py --pv-fracs 0.0 0.25 0.5 0.75 1.0
    .venv/bin/python run_pv.py --water-reduction 0.25 --income-bonus 350
    .venv/bin/python run_pv.py --reps 50 --workers 4
"""
import argparse
import os
import time
import multiprocessing as mp
import pandas as pd
from pathlib import Path

PROJECT_DIR  = Path(__file__).parent
MODEL_PATH   = str(PROJECT_DIR / "model/Groundwater_Commons_Game.nlogo")
NETLOGO_HOME = str(PROJECT_DIR / "NetLogo-6.4.0-64")
RESULTS_DIR  = PROJECT_DIR / "results"
WORKER_DIR   = RESULTS_DIR / "workers_pv"

# --- Free Market case study (fixed) ---
CASE_PARAMS = {
    "num-farmers":        50,
    "economy":            "Free Market: Generic Cash Crop(S+W)",
    "S-enforcement-cost": 0.35,   # Grid = 0.35 (moderate hierarchy)
    "S-reputation":       0.65,   # 1 - Group = 1 - 0.35 (individualistic)
}

# --- Experiment structure (fixed) ---
SCENARIOS = [
    ("mf", 0.1, 0.1),
    ("Mf", 0.5, 0.1),
    ("mF", 0.1, 0.9),
    ("MF", 0.5, 0.9),
]
METRICS = [
    "TS-compliance",
    "TS-boldness",
    "TS-vengefulness",
    "TS-drawdowns-mean",
    "TS-total-breaches",
]

# --- PV parameter defaults (overridable via CLI) ---
PV_FRACS_DEFAULT      = [0.0, 0.5, 1.0]   # adoption fractions to sweep
PV_WATER_RED_DEFAULT  = 0.30               # fractional IWA reduction from panel shading
PV_INCOME_BONUS_DEFAULT = 400              # $/ha/season solar income (conservative)

# --- Timeline defaults ---
PV_ADOPT_YEAR_DEFAULT = 25    # year PV panels are installed
REG_YEAR_DEFAULT      = 50    # year enforcement switches from lax to scenario
TOTAL_YEARS           = 100   # total simulation length (fixed)

MAX_WORKERS_DEFAULT   = 8
N_REPS_DEFAULT        = 100


def _patch_pynetlogo():
    import pynetlogo.core as _core
    def _find_jars(path):
        jars = []
        for root, _, files in os.walk(path):
            for f in files:
                if f == "asm-4.0.jar":
                    continue
                if f == "NetLogo.jar":
                    jars.insert(0, os.path.join(root, f))
                elif f.endswith(".jar"):
                    jars.append(os.path.join(root, f))
        return jars
    _core.find_jars = _find_jars


def run_batch(args):
    worker_id, tasks, pv_cfg = args
    _patch_pynetlogo()
    import pynetlogo

    nl = pynetlogo.NetLogoLink(netlogo_home=NETLOGO_HOME, gui=False)
    nl.load_model(MODEL_PATH)
    nl.command("set social-model? true")

    records = []
    for i, (scenario, M, F, pv_frac, rep, seed) in enumerate(tasks):
        try:
            nl.command(f"random-seed {seed}")
            nl.command(f"set num-farmers {CASE_PARAMS['num-farmers']}")
            nl.command("SETUP-EXPERIMENT")

            # All params after SETUP-EXPERIMENT (ca resets globals to 0)
            nl.command("set pumping-cap 0.2")
            nl.command(f"set S-enforcement-cost {CASE_PARAMS['S-enforcement-cost']}")
            nl.command(f"set S-reputation {CASE_PARAMS['S-reputation']}")
            nl.command("set voluntary-compliance-level 0")
            nl.command("set rule-breaker-level 0")
            nl.command("set metanorm? false")
            nl.command('set monitoring-style "flat"')
            nl.command('set enforcement-strategy "random"')
            nl.command("set graduated-sanctions? false")
            nl.command(f'set economy? "{CASE_PARAMS["economy"]}"')
            nl.command(f"set pv-water-reduction {pv_cfg['water_reduction']}")
            nl.command(f"set pv-income-bonus {pv_cfg['income_bonus']}")
            nl.command("set pv-adoption-fraction 0.0")
            nl.command("SETUP-PV")

            # Phase 1: lax, no PV (yr 0 – adopt_year-1)
            nl.command("set max-monitoring-capacity 0.1")
            nl.command("set fine-magnitude 0.1")
            for _ in range(pv_cfg['adopt_year']):
                nl.command("go")

            # PV adoption event
            nl.command(f"set pv-adoption-fraction {pv_frac}")
            nl.command("SETUP-PV")

            # Phase 2: lax, with PV (adopt_year – reg_year-1)
            for _ in range(pv_cfg['reg_year'] - pv_cfg['adopt_year']):
                nl.command("go")

            # Phase 3: enforcement scenario (reg_year – total_years-1)
            nl.command(f"set max-monitoring-capacity {M}")
            nl.command(f"set fine-magnitude {F}")
            for _ in range(TOTAL_YEARS - pv_cfg['reg_year']):
                nl.command("go")

            ts = {m: list(nl.report(m)) for m in METRICS}
            for yr in range(TOTAL_YEARS):
                row = {
                    "scenario":           scenario,
                    "M":                  M,
                    "F":                  F,
                    "pv":                 pv_frac,
                    "rep":                rep,
                    "yr":                 yr,
                    "S-enforcement-cost": CASE_PARAMS["S-enforcement-cost"],
                    "S-reputation":       CASE_PARAMS["S-reputation"],
                    "water-reduction":    pv_cfg["water_reduction"],
                    "income-bonus":       pv_cfg["income_bonus"],
                    "adopt-year":         pv_cfg["adopt_year"],
                    "reg-year":           pv_cfg["reg_year"],
                }
                for m in METRICS:
                    row[m] = ts[m][yr] if yr < len(ts[m]) else float("nan")
                records.append(row)

        except Exception as e:
            print(f"[W{worker_id}] ERROR {scenario} pv={pv_frac} rep{rep}: {e}", flush=True)

        if (i + 1) % 10 == 0 or (i + 1) == len(tasks):
            print(f"[W{worker_id}] {i+1}/{len(tasks)} done", flush=True)

    nl.kill_workspace()
    out = WORKER_DIR / f"worker_{worker_id}.csv"
    pd.DataFrame(records).to_csv(out, index=False)
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Agrivoltaic PV extension — Free Market archetype sweep.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # PV parameters
    pv = parser.add_argument_group("PV parameters")
    pv.add_argument(
        "--pv-fracs", type=float, nargs="+", default=PV_FRACS_DEFAULT,
        metavar="F",
        help="PV adoption fractions to sweep (0=none, 1=all farmers)",
    )
    pv.add_argument(
        "--water-reduction", type=float, default=PV_WATER_RED_DEFAULT,
        metavar="R",
        help="Fractional reduction in irrigation water applied (IWA) from panel shading",
    )
    pv.add_argument(
        "--income-bonus", type=float, default=PV_INCOME_BONUS_DEFAULT,
        metavar="B",
        help="Solar income added per ha of installed panel area per season ($/ha)",
    )

    # Timeline parameters
    tl = parser.add_argument_group("Timeline")
    tl.add_argument(
        "--adopt-year", type=int, default=PV_ADOPT_YEAR_DEFAULT,
        metavar="Y",
        help="Year at which PV panels are installed (0-indexed)",
    )
    tl.add_argument(
        "--reg-year", type=int, default=REG_YEAR_DEFAULT,
        metavar="Y",
        help="Year enforcement switches from lax (M=0.1, F=0.1) to scenario values",
    )

    # Compute parameters
    cp = parser.add_argument_group("Compute")
    cp.add_argument(
        "--reps", type=int, default=N_REPS_DEFAULT,
        help="Repetitions per (scenario, PV level) combination",
    )
    cp.add_argument(
        "--workers", type=int, default=MAX_WORKERS_DEFAULT,
        help="Parallel JVM workers (each uses ~1 GB RAM)",
    )

    args = parser.parse_args()

    if args.adopt_year >= args.reg_year:
        parser.error(f"--adopt-year ({args.adopt_year}) must be < --reg-year ({args.reg_year})")
    if args.reg_year >= TOTAL_YEARS:
        parser.error(f"--reg-year ({args.reg_year}) must be < {TOTAL_YEARS}")

    pv_cfg = {
        "water_reduction": args.water_reduction,
        "income_bonus":    args.income_bonus,
        "adopt_year":      args.adopt_year,
        "reg_year":        args.reg_year,
    }
    n_reps    = args.reps
    n_workers = min(args.workers, mp.cpu_count())
    output_csv = str(RESULTS_DIR / "pv_freemarket.csv")

    print(f"Agrivoltaic PV experiment — Free Market archetype")
    print(f"  PV adoption fractions: {args.pv_fracs}")
    print(f"  Water reduction:       {args.water_reduction:.0%} IWA reduction")
    print(f"  Solar income bonus:    ${args.income_bonus:.0f}/ha/season")
    print(f"  PV adoption year:      {args.adopt_year}")
    print(f"  Regulation year:       {args.reg_year}")
    print(f"  Reps per combination:  {n_reps}")
    print(f"  Workers:               {n_workers}")

    # Build task list — identical seed across pv_frac so yr 0-adopt_year is identical
    tasks = []
    for pv_frac in args.pv_fracs:
        for sc_idx, (scenario, M, F) in enumerate(SCENARIOS):
            for rep in range(n_reps):
                seed = sc_idx * 1000 + rep
                tasks.append((scenario, M, F, pv_frac, rep, seed))

    print(f"Total tasks: {len(tasks)} | Workers: {n_workers}", flush=True)

    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    for f in WORKER_DIR.glob("worker_*.csv"):
        f.unlink()

    batches = [[] for _ in range(n_workers)]
    for i, task in enumerate(tasks):
        batches[i % n_workers].append(task)
    worker_args = [(i, b, pv_cfg) for i, b in enumerate(batches) if b]

    t0 = time.time()
    ctx = mp.get_context("fork")
    try:
        with ctx.Pool(processes=n_workers) as pool:
            pool.map(run_batch, worker_args)
    except Exception as e:
        print(f"Pool error: {e}", flush=True)
        print("Collecting from completed workers ...", flush=True)

    parts = sorted(WORKER_DIR.glob("worker_*.csv"))
    print(f"\nFound {len(parts)}/{n_workers} worker files", flush=True)
    df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    df.to_csv(output_csv, index=False)

    elapsed = time.time() - t0
    n_runs = df[["scenario", "pv", "rep"]].drop_duplicates().shape[0]
    print(f"Done: {n_runs} runs in {elapsed:.0f}s ({elapsed/n_runs:.1f}s/run) -> {output_csv}")

    late = df[df["yr"] >= 80]
    print("\n=== Mean compliance yr 80-99 ===")
    print((late.groupby(["pv", "scenario"])["TS-compliance"].mean()
              .unstack("scenario") * 100).round(1).to_string())
    print("\n=== Mean drawdown yr 80-99 (m) ===")
    print(late.groupby(["pv", "scenario"])["TS-drawdowns-mean"].mean()
              .unstack("scenario").round(2).to_string())


if __name__ == "__main__":
    main()
