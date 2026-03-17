"""
run_paper_protocol_generic.py

Generalized Figure 5 paper protocol runner (Castilla-Rho et al. 2019).
Supports all case studies: Australia, USA, Pakistan, India, Canada.

Usage:
    .venv/bin/python run_paper_protocol_generic.py india
    .venv/bin/python run_paper_protocol_generic.py canada
"""

import os
import sys
import time
import multiprocessing as mp
import pandas as pd
from pathlib import Path

PROJECT_DIR  = Path(__file__).parent
MODEL_PATH   = str(PROJECT_DIR / "groundwater-commons/code/Groundwater_Commons_Game.nlogo")
NETLOGO_HOME = str(PROJECT_DIR / "NetLogo-6.4.0-64")
RESULTS_DIR  = PROJECT_DIR / "results"
WORKER_DIR   = RESULTS_DIR / "workers"

MAX_WORKERS  = 8   # 8 JVMs × ~1GB each = ~8GB RAM; 16 hits OOM

# --- Case study definitions ---
# S_reputation = 1 - Group;  S_enforcement_cost = Grid
CASE_STUDIES = {
    "australia": {
        "num-farmers": 10,
        "economy": "Australia: Cotton(S), Vetch(W)",
        "S-enforcement-cost": 0.2,
        "S-reputation": 0.2,       # 1 - 0.8
    },
    "usa": {
        "num-farmers": 50,
        "economy": "Central Valley: Almonds(S)",
        "S-enforcement-cost": 0.4,
        "S-reputation": 0.6,       # 1 - 0.4
    },
    "pakistan": {
        "num-farmers": 630,
        "economy": "Punjab: Rice(S), Wheat(W)",
        "S-enforcement-cost": 0.8,
        "S-reputation": 0.6,       # 1 - 0.4
    },
    "india": {
        "num-farmers": 630,
        "economy": "Punjab: Rice(S), Wheat(W)",
        "S-enforcement-cost": 0.8,
        "S-reputation": 0.4,       # 1 - 0.6
    },
    "canada": {
        "num-farmers": 50,          # Paskapoo region estimate
        "economy": "Canada: Canola(S), Wheat(W)",
        "S-enforcement-cost": 0.25,
        "S-reputation": 0.40,      # 1 - 0.60
    },
}

SCENARIOS = [
    ("mf",  0.1, 0.1),
    ("Mf",  0.5, 0.1),
    ("mF",  0.1, 0.9),
    ("MF",  0.5, 0.9),
]
N_REPS  = 100
METRICS = [
    "TS-compliance",
    "TS-boldness",
    "TS-vengefulness",
    "TS-drawdowns-mean",
    "TS-total-breaches",
]


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
    worker_id, tasks, case_params = args
    _patch_pynetlogo()
    import pynetlogo

    nl = pynetlogo.NetLogoLink(netlogo_home=NETLOGO_HOME, gui=False)
    nl.load_model(MODEL_PATH)
    nl.command("set social-model? true")

    records = []
    for i, (scenario, M, F, rep, seed) in enumerate(tasks):
        try:
            nl.command(f"random-seed {seed}")
            nl.command(f"set num-farmers {case_params['num-farmers']}")
            nl.command("SETUP-EXPERIMENT")

            # Fixed params
            nl.command(f"set pumping-cap 0.2")
            nl.command(f"set S-enforcement-cost {case_params['S-enforcement-cost']}")
            nl.command(f"set S-reputation {case_params['S-reputation']}")
            nl.command("set voluntary-compliance-level 0")
            nl.command("set rule-breaker-level 0")
            nl.command("set metanorm? false")
            nl.command('set monitoring-style "flat"')
            nl.command('set enforcement-strategy "random"')
            nl.command("set graduated-sanctions? false")
            nl.command(f'set economy? "{case_params["economy"]}"')

            # 50 years lax regulation
            nl.command("set max-monitoring-capacity 0.1")
            nl.command("set fine-magnitude 0.1")
            for _ in range(50):
                nl.command("go")

            # Switch to scenario enforcement
            nl.command(f"set max-monitoring-capacity {M}")
            nl.command(f"set fine-magnitude {F}")
            for _ in range(50):
                nl.command("go")

            # Collect TS lists (exactly 100 values)
            ts = {m: list(nl.report(m)) for m in METRICS}

            run_num = SCENARIOS.index((scenario, M, F)) * N_REPS + rep
            for yr in range(100):
                row = {
                    "run":                     run_num,
                    "tick":                    yr,
                    "scenario":                scenario,
                    "max-monitoring-capacity": M,
                    "fine-magnitude":          F,
                    "S-enforcement-cost":      case_params["S-enforcement-cost"],
                    "S-reputation":            case_params["S-reputation"],
                }
                for m in METRICS:
                    row[m] = ts[m][yr] if yr < len(ts[m]) else float("nan")
                records.append(row)

        except Exception as e:
            print(f"[W{worker_id}] ERROR {scenario} rep{rep}: {e}", flush=True)

        if (i + 1) % 5 == 0 or (i + 1) == len(tasks):
            print(f"[W{worker_id}] {i+1}/{len(tasks)} runs done", flush=True)

    nl.kill_workspace()

    out = WORKER_DIR / f"worker_{worker_id}.csv"
    pd.DataFrame(records).to_csv(out, index=False)
    return records


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <case_study>")
        print(f"Available: {', '.join(CASE_STUDIES.keys())}")
        sys.exit(1)

    case_name = sys.argv[1].lower()
    if case_name not in CASE_STUDIES:
        print(f"Unknown case study: {case_name}")
        print(f"Available: {', '.join(CASE_STUDIES.keys())}")
        sys.exit(1)

    case_params = CASE_STUDIES[case_name]
    output_csv = str(RESULTS_DIR / f"paper_protocol_{case_name}.csv")

    print(f"Case study: {case_name}")
    print(f"  num-farmers:        {case_params['num-farmers']}")
    print(f"  economy:            {case_params['economy']}")
    print(f"  S-enforcement-cost: {case_params['S-enforcement-cost']}")
    print(f"  S-reputation:       {case_params['S-reputation']}")

    # Build task list
    tasks = []
    for scenario_idx, (scenario, M, F) in enumerate(SCENARIOS):
        for rep in range(N_REPS):
            seed = scenario_idx * 1000 + rep
            tasks.append((scenario, M, F, rep, seed))

    n_workers = min(mp.cpu_count(), MAX_WORKERS)
    print(f"Tasks: {len(tasks)} runs | Workers: {n_workers}", flush=True)

    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    for f in WORKER_DIR.glob("worker_*.csv"):
        f.unlink()

    # Distribute round-robin
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


if __name__ == "__main__":
    main()
