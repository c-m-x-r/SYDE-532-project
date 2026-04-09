"""
run_paper.py

Faithful Python re-implementation of the original BehaviorSpace experiments
(SC_MDB_50, SC_CV_50, SC_PUNJAB_50) from Castilla-Rho et al. 2017.

Protocol mirrors the embedded BehaviorSpace XML exactly:
  1. SETUP-EXPERIMENT clears all globals via `ca` → S-params reset to 0
  2. 100-year hidden burn-in under lax conditions (M=0.1, F=0.1, S-params=0)
  3. reset-ticks (TS lists retain 100 burn-in entries, NOT cleared)
  4. Restore actual cultural params (S-enforcement-cost, S-reputation)
  5. 100-year measurement under scenario M/F
  6. Collect only TS[-100:] — the measurement period

Output ticks 0–99 are all under the enforcement scenario (no lax phase shown).
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
WORKER_DIR   = RESULTS_DIR / "workers_bs"

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

BURN_IN_YEARS    = 100   # hidden; matches `repeat 100 [go]` in BehaviorSpace setup
MEASURE_YEARS    = 100   # measurement period; matches `<timeLimit steps="100"/>`


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
    Worker: runs a sequential batch of (scenario, M, F, rep, seed) tasks.

    Protocol per run — mirrors the BehaviorSpace setup block exactly:
      1. Set S-enforcement-cost and S-reputation to their SCENARIO values BEFORE
         SETUP-EXPERIMENT (these are the `old-*` values that get saved, then
         SETUP-EXPERIMENT clears them to 0 via ca, then they are restored).
      2. SETUP-EXPERIMENT  →  clears all globals (S-params now 0)
      3. Set lax burn-in params (M=0.1, F=0.1, voluntary=0, etc.)
      4. Set economy
      5. Run BURN_IN_YEARS  →  TS lists accumulate 100 entries (S-params=0)
      6. reset-ticks / set year 0  (TS lists NOT cleared)
      7. Restore S-enforcement-cost, S-reputation to actual values
      8. Run MEASURE_YEARS  →  TS lists accumulate 100 more entries
      9. Collect TS lists (200 items); take last 100 = measurement period
    """
    worker_id, tasks, case_params = args
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

            # --- Steps 3–4: set burn-in params (lax, no cultural params) ---
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
            # S-enforcement-cost and S-reputation remain 0 (default after ca)

            # --- Step 5: hidden burn-in ---
            for _ in range(BURN_IN_YEARS):
                nl.command("go")
            # TS lists now have BURN_IN_YEARS entries each

            # --- Step 6: reset-ticks (does NOT clear TS lists) ---
            nl.command("reset-ticks")
            nl.command("set year 0")

            # --- Step 7: restore actual cultural + scenario params ---
            nl.command(f"set S-enforcement-cost {case_params['S-enforcement-cost']}")
            nl.command(f"set S-reputation {case_params['S-reputation']}")
            nl.command(f"set max-monitoring-capacity {M}")
            nl.command(f"set fine-magnitude {F}")
            # pumping-cap, voluntary-compliance, etc. already set above and unchanged

            # --- Step 8: measurement period ---
            for _ in range(MEASURE_YEARS):
                nl.command("go")
            # TS lists now have BURN_IN_YEARS + MEASURE_YEARS entries

            # --- Step 9: collect last MEASURE_YEARS entries (measurement period) ---
            ts = {}
            for m in METRICS:
                full_list = list(nl.report(m))
                # Take only the measurement period (last MEASURE_YEARS values)
                ts[m] = full_list[-MEASURE_YEARS:]

            run_num = SCENARIOS.index((scenario, M, F)) * n_reps + rep
            for yr in range(MEASURE_YEARS):
                row = {
                    "run":                     run_num,
                    "tick":                    yr,
                    "scenario":                scenario,
                    "max-monitoring-capacity": M,
                    "fine-magnitude":          F,
                    "S-enforcement-cost":      case_params["S-enforcement-cost"],
                    "S-reputation":            case_params["S-reputation"],
                    "pv-adoption-fraction":    0.0,
                }
                for m in METRICS:
                    row[m] = ts[m][yr] if yr < len(ts[m]) else float("nan")
                records.append(row)

        except Exception as e:
            print(f"[W{worker_id}] ERROR {scenario} rep{rep}: {e}", flush=True)

        if (i + 1) % 5 == 0 or (i + 1) == len(tasks):
            print(f"[W{worker_id}] {i+1}/{len(tasks)} done", flush=True)

    nl.kill_workspace()

    out = WORKER_DIR / f"worker_{worker_id}.csv"
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

    print(f"BehaviorSpace-faithful protocol")
    print(f"  Case:               {args.case}")
    print(f"  num-farmers:        {case_params['num-farmers']}")
    print(f"  economy:            {case_params['economy']}")
    print(f"  S-enforcement-cost: {case_params['S-enforcement-cost']}")
    print(f"  S-reputation:       {case_params['S-reputation']}")
    print(f"  Burn-in years:      {BURN_IN_YEARS} (hidden, S-params=0)")
    print(f"  Measurement years:  {MEASURE_YEARS} (all under scenario M/F)")
    print(f"  Reps per scenario:  {n_reps}")
    print(f"  Workers:            {n_workers}")

    tasks = []
    for scenario_idx, (scenario, M, F) in enumerate(SCENARIOS):
        for rep in range(n_reps):
            seed = scenario_idx * 1000 + rep
            tasks.append((scenario, M, F, rep, seed, n_reps))

    print(f"Tasks: {len(tasks)} runs | Workers: {n_workers}", flush=True)

    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    for f in WORKER_DIR.glob("worker_*.csv"):
        f.unlink()

    batches = [[] for _ in range(n_workers)]
    for i, task in enumerate(tasks):
        batches[i % n_workers].append(task)
    worker_args = [(i, b, case_params) for i, b in enumerate(batches) if b]

    t0 = time.time()
    ctx = mp.get_context("fork")
    try:
        with ctx.Pool(processes=n_workers) as pool:
            pool.map(run_batch, worker_args)
    except Exception as e:
        print(f"Pool error: {e}", flush=True)
        print("Collecting results from completed workers ...", flush=True)

    parts = sorted(WORKER_DIR.glob("worker_*.csv"))
    print(f"\nFound {len(parts)}/{n_workers} worker result files", flush=True)
    df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    df.to_csv(output_csv, index=False)

    elapsed = time.time() - t0
    n_runs = df["run"].nunique()
    print(f"Done: {n_runs} runs in {elapsed:.0f}s ({elapsed/n_runs:.1f}s/run) -> {output_csv}",
          flush=True)
    print(f"Plot:  .venv/bin/python plot_panels.py --bs {args.case}", flush=True)


if __name__ == "__main__":
    main()
