"""
run_paper_protocol.py

Reproduces the Figure 5 paper protocol (Castilla-Rho et al. 2019):
  - Random initialisation, B and P ~ U[0,1]
  - 50 years under lax enforcement (M=10%, F=10%)
  - 50 years under scenario enforcement (mf / Mf / mF / MF)
  - 100 independent reps per scenario

Spawns one NetLogo instance per CPU core using multiprocessing fork.
Each worker runs a sequential batch of (scenario, rep) pairs.
"""

import os
import time
import multiprocessing as mp
import pandas as pd
from pathlib import Path

PROJECT_DIR  = Path(__file__).parent
MODEL_PATH   = str(PROJECT_DIR / "groundwater-commons/code/Groundwater_Commons_Game.nlogo")
NETLOGO_HOME = str(PROJECT_DIR / "NetLogo-6.4.0-64")
OUTPUT_CSV   = str(PROJECT_DIR / "results/paper_protocol_australia.csv")
WORKER_DIR   = PROJECT_DIR / "results" / "workers"

MAX_WORKERS  = 8   # 16 parallel JVMs hits OOM; 8 is safe

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
    """
    Worker function: runs a list of (scenario, M, F, rep, seed) tasks
    sequentially in a single NetLogo instance.
    """
    worker_id, tasks = args
    _patch_pynetlogo()
    import pynetlogo

    nl = pynetlogo.NetLogoLink(netlogo_home=NETLOGO_HOME, gui=False)
    nl.load_model(MODEL_PATH)
    nl.command("set social-model? true")   # must be on for social dynamics

    records = []
    for i, (scenario, M, F, rep, seed) in enumerate(tasks):
        try:
            nl.command(f"random-seed {seed}")
            nl.command("set num-farmers 10")
            nl.command("SETUP-EXPERIMENT")

            # Fixed params (same for all scenarios)
            nl.command("set pumping-cap 0.2")
            nl.command("set S-enforcement-cost 0.2")       # Grid = 0.2 (Australia)
            nl.command("set S-reputation 0.2")             # 1 - Group = 1 - 0.8 = 0.2 (Australia)
            nl.command("set voluntary-compliance-level 0")
            nl.command("set rule-breaker-level 0")
            nl.command("set metanorm? false")
            nl.command('set monitoring-style "flat"')
            nl.command('set enforcement-strategy "random"')
            nl.command("set graduated-sanctions? false")
            nl.command('set economy? "Australia: Cotton(S), Vetch(W)"')

            # 50 years lax regulation (first half of displayed period)
            nl.command("set max-monitoring-capacity 0.1")
            nl.command("set fine-magnitude 0.1")
            for _ in range(50):
                nl.command("go")

            # Switch to scenario enforcement (second half)
            nl.command(f"set max-monitoring-capacity {M}")
            nl.command(f"set fine-magnitude {F}")
            for _ in range(50):
                nl.command("go")

            # Collect TS lists (each has exactly 100 values)
            ts = {m: list(nl.report(m)) for m in METRICS}

            run_num = SCENARIOS.index((scenario, M, F)) * N_REPS + rep
            for yr in range(100):
                row = {
                    "run":                     run_num,
                    "tick":                    yr,
                    "scenario":                scenario,
                    "max-monitoring-capacity": M,
                    "fine-magnitude":          F,
                    "S-enforcement-cost":      0.2,
                    "S-reputation":            0.2,
                }
                for m in METRICS:
                    row[m] = ts[m][yr] if yr < len(ts[m]) else float("nan")
                records.append(row)

        except Exception as e:
            print(f"[W{worker_id}] ERROR {scenario} rep{rep}: {e}", flush=True)

        if (i + 1) % 5 == 0 or (i + 1) == len(tasks):
            print(f"[W{worker_id}] {i+1}/{len(tasks)} runs done", flush=True)

    nl.kill_workspace()

    # Save immediately — if another worker crashes, this data is preserved
    out = WORKER_DIR / f"worker_{worker_id}.csv"
    pd.DataFrame(records).to_csv(out, index=False)
    return records


def main():
    # Build full task list with deterministic seeds
    tasks = []
    for scenario_idx, (scenario, M, F) in enumerate(SCENARIOS):
        for rep in range(N_REPS):
            seed = scenario_idx * 1000 + rep
            tasks.append((scenario, M, F, rep, seed))

    n_workers = min(mp.cpu_count(), MAX_WORKERS)
    print(f"Tasks: {len(tasks)} runs | Workers: {n_workers} (capped at {MAX_WORKERS})", flush=True)
    print(f"~{len(tasks) // n_workers} runs per worker", flush=True)

    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    # Clear any stale worker files from a previous run
    for f in WORKER_DIR.glob("worker_*.csv"):
        f.unlink()

    # Distribute round-robin so each worker gets a mix of scenarios
    batches = [[] for _ in range(n_workers)]
    for i, task in enumerate(tasks):
        batches[i % n_workers].append(task)
    worker_args = [(i, b) for i, b in enumerate(batches) if b]

    t0 = time.time()
    ctx = mp.get_context("fork")
    try:
        with ctx.Pool(processes=n_workers) as pool:
            pool.map(run_batch, worker_args)
    except Exception as e:
        print(f"Pool error (likely a worker JVM crash): {e}", flush=True)
        print("Collecting results from worker files that completed ...", flush=True)

    # Aggregate all worker files that exist (crashed workers simply have no file)
    parts = sorted(WORKER_DIR.glob("worker_*.csv"))
    print(f"\nFound {len(parts)}/{n_workers} worker result files", flush=True)
    df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    df.to_csv(OUTPUT_CSV, index=False)

    elapsed = time.time() - t0
    n_runs = df["run"].nunique()
    print(f"Done: {n_runs} runs in {elapsed:.0f}s ({elapsed/n_runs:.1f}s/run) → {OUTPUT_CSV}",
          flush=True)


if __name__ == "__main__":
    main()
