"""
run_paper.py
Re-implementation of the paper's protocol (Castilla-Rho et al. 2017).

Protocol (matching Figure 5 exactly):
  1. SETUP-EXPERIMENT initializes farmers with random B,P ∈ [0,1]
  2. 50-year lax management (M=10%, F=10%, S-params=0) where agents evolve strategy
  3. reset-ticks (TS lists retain 50 lax entries, NOT cleared; year reset to 0) ## what is this?
  4. Activate enforcement: restore S-enforcement-cost, S-reputation, set M/F/scenario
  5. 50-year enforcement measurement under scenario M/F
  6. Collect all 100 years: ticks 0–49 = lax baseline, ticks 50–99 = enforcement response

Output displays full 100-year evolution (years 0–100 with regulation line at year 50).
Plot with: .venv/bin/python plot_panels.py --bs <case>

Usage:
    .venv/bin/python run_paper.py india
    .venv/bin/python run_paper.py australia
    .venv/bin/python run_paper.py pakistan
    .venv/bin/python run_paper.py usa
    .venv/bin/python run_paper.py canada
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
# WORKER_DIR is set per-case in main() to avoid collisions when two cases run in parallel

MAX_WORKERS  = 8

# --- Case study definitions (matching original BehaviorSpace experiments) ---
# S_reputation = 1 - Group;  S_enforcement_cost = Grid
CASE_STUDIES = {
    "australia": {
        "num-farmers": 10,
        "economy": "Australia: Cotton(S), Vetch(W)",
        "S-enforcement-cost": 0.2,
        "S-reputation": 0.2,       # 1 - Group(0.8)
    },
    "usa": {
        "num-farmers": 50,
        "economy": "Central Valley: Almonds(S)",
        "S-enforcement-cost": 0.4,
        "S-reputation": 0.6,       # 1 - Group(0.4)
    },
    "pakistan": {
        "num-farmers": 630,
        "economy": "Punjab: Rice(S), Wheat(W)",
        "S-enforcement-cost": 0.8,
        "S-reputation": 0.6,       # 1 - Group(0.4)
    },
    "india": {
        "num-farmers": 630,
        "economy": "Punjab: Rice(S), Wheat(W)",
        "S-enforcement-cost": 0.8,
        "S-reputation": 0.4,       # 1 - Group(0.6)
    },
    "canada": {
        "num-farmers": 50,
        "economy": "Canada: Canola(S), Wheat(W)",
        "S-enforcement-cost": 0.30,
        "S-reputation": 0.61,      # 1 - Group(0.39), WVS Wave 7
    },
}

# Scenarios: (label, max-monitoring-capacity, fine-magnitude)
# Paper sweeps M in {0.1, 0.5} and F in {0.1, 0.9} → 4 combinations
SCENARIOS = [
    ("mf",  0.1, 0.1),
    ("Mf",  0.5, 0.1),
    ("mF",  0.1, 0.9),
    ("MF",  0.5, 0.9),
]

N_REPS_DEFAULT = 100   # original paper used 50

METRICS = [
    "TS-compliance",
    "TS-boldness",
    "TS-vengefulness",
    "TS-drawdowns-mean",
    "TS-total-breaches",
]

BURN_IN_YEARS    = 50    # 50-year lax period; agents visible from random initialization
MEASURE_YEARS    = 50    # 50-year enforcement measurement period

# Output includes all years from both phases.
# Figure 5: ticks 0–49 = lax baseline (S-params=0, M=10%, F=10%)
#           ticks 50–99 = enforcement response (S-params active, M/F/scenario vary)
# Regulation line drawn at tick 50.
DISPLAY_BURNIN   = 50    # Display all 50 lax years (agents visible from random init)
DISPLAY_MEASURE  = 50    # Display all 50 enforcement years


def _patch_pynetlogo():
    """Exclude asm-4.0.jar from the classpath to avoid ASM version conflict."""
    import pynetlogo.core as _core
    def _find_jars_patched(path):
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
    _core.find_jars = _find_jars_patched


def run_batch(args):
    """
    Worker: runs a sequential batch of (scenario, M, F, rep, seed, n_reps) tasks.

    Protocol per run — matches the paper's protocol (Castilla-Rho et al. 2017):
      1. SETUP-EXPERIMENT clears all globals via ca, initializes farmers with random B,P
      2. Set lax management params (M=0.1, F=0.1, S-params=0, voluntary=0, etc.)
      3. Set economy
      4. Run BURN_IN_YEARS (50) under lax conditions  →  TS lists accumulate 50 entries
      5. reset-ticks / set year 0  (TS lists NOT cleared)
      6. Restore actual S-enforcement-cost and S-reputation values
      7. Update M and F to enforcement scenario values
      8. Run MEASURE_YEARS (50) under enforcement  →  TS lists accumulate 50 more entries
      9. Collect TS lists (100 items total): [0:50] = lax, [50:100] = enforcement response
    """
    worker_id, tasks, case_params, worker_dir = args
    _patch_pynetlogo()
    import pynetlogo

    nl = pynetlogo.NetLogoLink(netlogo_home=NETLOGO_HOME, gui=False)
    nl.load_model(MODEL_PATH)
    nl.command("set social-model? true")

    records = []
    for i, (scenario, M, F, rep, seed, n_reps) in enumerate(tasks):
        try:
            nl.command(f"random-seed {seed}")

            # --- SETUP-EXPERIMENT clears all globals via ca ---
            nl.command(f"set num-farmers {case_params['num-farmers']}")
            nl.command("SETUP-EXPERIMENT")
            # After this: S-enforcement-cost=0, S-reputation=0 (cleared by ca)

            # --- Lax phase params (S-params remain 0 after ca, matching BehaviorSpace) ---
            nl.command("set pumping-cap 0.2")
            nl.command("set max-monitoring-capacity 0.1")
            nl.command("set fine-magnitude 0.1")
            nl.command("set voluntary-compliance-level 0")
            nl.command("set rule-breaker-level 0")
            nl.command("set metanorm? false")
            nl.command('set monitoring-style "flat"')
            nl.command('set enforcement-strategy "random"')
            nl.command("set graduated-sanctions? false")
            nl.command(f'set economy? "{case_params["economy"]}"')
            # S-enforcement-cost and S-reputation remain 0 (cleared by ca in SETUP-EXPERIMENT)

            # --- Phase 1: 50-year lax period ---
            for _ in range(BURN_IN_YEARS):
                nl.command("go")

            # --- Transition: activate enforcement scenario and cultural params ---
            nl.command("reset-ticks")
            nl.command("set year 0")
            nl.command(f"set S-enforcement-cost {case_params['S-enforcement-cost']}")
            nl.command(f"set S-reputation {case_params['S-reputation']}")
            nl.command(f"set max-monitoring-capacity {M}")
            nl.command(f"set fine-magnitude {F}")
            nl.command('set enforcement-strategy "risk-based"')

            # --- Phase 2: 50-year enforcement measurement ---
            for _ in range(MEASURE_YEARS):
                nl.command("go")

            # --- Step 9: collect output window ---
            # Full TS list: indices 0..BURN_IN_YEARS-1  = lax phase (visible from random init)
            #               indices BURN_IN_YEARS..end   = enforcement phase response
            # Output: all DISPLAY_BURNIN lax years + all DISPLAY_MEASURE enforcement years.
            # Total length = 100 years; regulation transition at tick 50.
            ts = {}
            for m in METRICS:
                full_list = list(nl.report(m))
                lax_slice        = full_list[0 : BURN_IN_YEARS]
                enforcement_slice = full_list[BURN_IN_YEARS : BURN_IN_YEARS + MEASURE_YEARS]
                ts[m] = lax_slice + enforcement_slice   # length = 50 + 50 = 100

            run_num = SCENARIOS.index((scenario, M, F)) * n_reps + rep
            n_ticks = DISPLAY_BURNIN + DISPLAY_MEASURE
            for yr in range(n_ticks):
                row = {
                    "run":                     run_num,
                    "tick":                    yr,
                    "phase":                   "burnin" if yr < DISPLAY_BURNIN else "enforcement",
                    "scenario":                scenario,
                    "max-monitoring-capacity": M,
                    "fine-magnitude":          F,
                    "S-enforcement-cost":      case_params["S-enforcement-cost"],
                    "S-reputation":            case_params["S-reputation"],
                    "pv-adoption-fraction":    0.0,
                    "num-farmers":             case_params["num-farmers"],
                }
                for m in METRICS:
                    row[m] = ts[m][yr] if yr < len(ts[m]) else float("nan")
                records.append(row)

        except Exception as e:
            print(f"[W{worker_id}] ERROR {scenario} rep{rep}: {e}", flush=True)

        if (i + 1) % 5 == 0 or (i + 1) == len(tasks):
            print(f"[W{worker_id}] {i+1}/{len(tasks)} done", flush=True)

    nl.kill_workspace()

    out = worker_dir / f"worker_{worker_id}.csv"
    pd.DataFrame(records).to_csv(out, index=False)
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Reproduce Figure 5 (Castilla-Rho et al. 2017) — faithful BehaviorSpace protocol.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "case",
        choices=list(CASE_STUDIES.keys()),
        help="Case study to run",
    )
    parser.add_argument(
        "--reps", type=int, default=N_REPS_DEFAULT,
        help="Repetitions per enforcement scenario (paper used 50)",
    )
    parser.add_argument(
        "--workers", type=int, default=MAX_WORKERS,
        help="Parallel JVM workers (each uses ~1 GB RAM)",
    )
    args = parser.parse_args()

    case_params = CASE_STUDIES[args.case]
    n_reps      = args.reps
    n_workers   = min(args.workers, mp.cpu_count())
    output_csv  = str(RESULTS_DIR / f"bs_protocol_{args.case}.csv")
    worker_dir  = RESULTS_DIR / f"workers_bs_{args.case}"

    print(f"Paper protocol (Castilla-Rho et al. 2017 Figure 5)")
    print(f"  Case:               {args.case}")
    print(f"  num-farmers:        {case_params['num-farmers']}")
    print(f"  economy:            {case_params['economy']}")
    print(f"  S-enforcement-cost: {case_params['S-enforcement-cost']}")
    print(f"  S-reputation:       {case_params['S-reputation']}")
    print(f"  Lax phase:          {BURN_IN_YEARS} years (M=10%, F=10%, S=0, agents visible)")
    print(f"  Enforcement phase:  {MEASURE_YEARS} years (M/F/S vary by scenario)")
    print(f"  Output:             {DISPLAY_BURNIN} + {DISPLAY_MEASURE} = 100 years (regulation line at year 50)")
    print(f"  Reps per scenario:  {n_reps}")
    print(f"  Workers:            {n_workers}")

    tasks = []
    for scenario_idx, (scenario, M, F) in enumerate(SCENARIOS):
        for rep in range(n_reps):
            seed = scenario_idx * 1000 + rep
            tasks.append((scenario, M, F, rep, seed, n_reps))

    print(f"Tasks: {len(tasks)} runs | Workers: {n_workers}", flush=True)

    worker_dir.mkdir(parents=True, exist_ok=True)
    for f in worker_dir.glob("worker_*.csv"):
        f.unlink(missing_ok=True)

    batches = [[] for _ in range(n_workers)]
    for i, task in enumerate(tasks):
        batches[i % n_workers].append(task)
    worker_args = [(i, b, case_params, worker_dir) for i, b in enumerate(batches) if b]

    t0 = time.time()
    ctx = mp.get_context("fork")
    try:
        with ctx.Pool(processes=n_workers) as pool:
            pool.map(run_batch, worker_args)
    except Exception as e:
        print(f"Pool error: {e}", flush=True)
        print("Collecting results from completed workers ...", flush=True)

    parts = sorted(worker_dir.glob("worker_*.csv"))
    print(f"\nFound {len(parts)}/{n_workers} worker result files", flush=True)
    df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    df.to_csv(output_csv, index=False)

    output_pkl = str(RESULTS_DIR / f"bs_protocol_{args.case}.pkl")
    df.to_pickle(output_pkl)

    elapsed = time.time() - t0
    n_runs = df["run"].nunique()
    print(f"Done: {n_runs} runs in {elapsed:.0f}s ({elapsed/n_runs:.1f}s/run)", flush=True)
    print(f"  CSV: {output_csv}", flush=True)
    print(f"  PKL: {output_pkl}", flush=True)
    print(f"Plot:  .venv/bin/python plot_panels.py --bs {args.case}", flush=True)


if __name__ == "__main__":
    main()
