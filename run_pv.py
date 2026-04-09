"""
run_pv.py — Agrivoltaic PV extension experiment, n=100, 8 parallel workers.

Protocol (shared seeds across PV levels so yr 0-24 is identical):
  yr  0-24: lax (M=0.1, F=0.1), no PV
  yr 25:    PV adoption event (SETUP-PV with pv_frac)
  yr 25-49: lax, with PV
  yr 50-99: enforcement scenario, with PV

Output: results/pv_freemarket.csv

Usage:
    .venv/bin/python run_pv.py
"""
import os, sys, time, multiprocessing as mp
import pandas as pd
from pathlib import Path

PROJECT_DIR  = Path(__file__).parent
MODEL_PATH   = str(PROJECT_DIR / "model/Groundwater_Commons_Game.nlogo")
NETLOGO_HOME = str(PROJECT_DIR / "NetLogo-6.4.0-64")
RESULTS_DIR  = PROJECT_DIR / "results"
WORKER_DIR   = RESULTS_DIR / "workers_pv"

MAX_WORKERS     = 8
N_REPS          = 100
PV_FRACS        = [0.0, 0.5, 1.0]
PV_WATER_RED    = 0.30
PV_INCOME_BONUS = 400
PV_ADOPT_YEAR   = 25
REG_YEAR        = 50
TOTAL_YEARS     = 100

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

CASE_PARAMS = {
    "num-farmers":        50,
    "economy":            "Free Market: Generic Cash Crop(S+W)",
    "S-enforcement-cost": 0.35,
    "S-reputation":       0.65,
}


def _patch_pynetlogo():
    import pynetlogo.core as _core
    def _find_jars(path):
        jars = []
        for root, _, files in os.walk(path):
            for f in files:
                if f == "asm-4.0.jar": continue
                if f == "NetLogo.jar": jars.insert(0, os.path.join(root, f))
                elif f.endswith(".jar"): jars.append(os.path.join(root, f))
        return jars
    _core.find_jars = _find_jars


def run_batch(args):
    worker_id, tasks = args
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

            # All params after SETUP-EXPERIMENT (ca resets globals)
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
            nl.command(f"set pv-water-reduction {PV_WATER_RED}")
            nl.command(f"set pv-income-bonus {PV_INCOME_BONUS}")
            nl.command("set pv-adoption-fraction 0.0")
            nl.command("SETUP-PV")

            # Phase 1: lax, no PV
            nl.command("set max-monitoring-capacity 0.1")
            nl.command("set fine-magnitude 0.1")
            for _ in range(PV_ADOPT_YEAR):
                nl.command("go")

            # PV adoption event
            nl.command(f"set pv-adoption-fraction {pv_frac}")
            nl.command("SETUP-PV")

            # Phase 2: lax, with PV
            for _ in range(REG_YEAR - PV_ADOPT_YEAR):
                nl.command("go")

            # Phase 3: scenario enforcement
            nl.command(f"set max-monitoring-capacity {M}")
            nl.command(f"set fine-magnitude {F}")
            for _ in range(TOTAL_YEARS - REG_YEAR):
                nl.command("go")

            ts = {m: list(nl.report(m)) for m in METRICS}
            for yr in range(TOTAL_YEARS):
                row = {
                    "scenario": scenario, "M": M, "F": F,
                    "pv": pv_frac, "rep": rep, "yr": yr,
                    "S-enforcement-cost": CASE_PARAMS["S-enforcement-cost"],
                    "S-reputation":       CASE_PARAMS["S-reputation"],
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
    output_csv = str(RESULTS_DIR / "pv_freemarket.csv")
    print(f"Option B sweep: {len(PV_FRACS)} PV levels × {len(SCENARIOS)} scenarios × {N_REPS} reps")
    print(f"PV adoption at yr {PV_ADOPT_YEAR}, enforcement at yr {REG_YEAR}")
    print(f"Workers: {MAX_WORKERS}")

    # Build task list — same seed for all pv_frac
    tasks = []
    for pv_frac in PV_FRACS:
        for sc_idx, (scenario, M, F) in enumerate(SCENARIOS):
            for rep in range(N_REPS):
                seed = sc_idx * 1000 + rep   # identical across pv_frac
                tasks.append((scenario, M, F, pv_frac, rep, seed))

    n_workers = min(mp.cpu_count(), MAX_WORKERS)
    print(f"Total tasks: {len(tasks)} | Workers: {n_workers}", flush=True)

    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    for f in WORKER_DIR.glob("worker_*.csv"):
        f.unlink()

    # Round-robin distribution
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
        print(f"Pool error: {e}", flush=True)
        print("Collecting from completed workers ...", flush=True)

    parts = sorted(WORKER_DIR.glob("worker_*.csv"))
    print(f"\nFound {len(parts)}/{n_workers} worker files", flush=True)
    df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    df.to_csv(output_csv, index=False)

    elapsed = time.time() - t0
    n_runs = df[["scenario","pv","rep"]].drop_duplicates().shape[0]
    print(f"Done: {n_runs} runs in {elapsed:.0f}s ({elapsed/n_runs:.1f}s/run) → {output_csv}")

    late = df[df["yr"] >= 80]
    print("\n=== Mean compliance yr 80-99 ===")
    print((late.groupby(["pv","scenario"])["TS-compliance"].mean()
              .unstack("scenario") * 100).round(1).to_string())
    print("\n=== Mean drawdown yr 80-99 ===")
    print(late.groupby(["pv","scenario"])["TS-drawdowns-mean"].mean()
              .unstack("scenario").round(2).to_string())


if __name__ == "__main__":
    main()
