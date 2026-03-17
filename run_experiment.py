"""
Run targeted BehaviorSpace-style experiments via pyNetLogo.

Advantages over headless CLI for targeted runs:
- Warm JVM (no per-run startup cost)
- Python control of parameters
- Results directly in pandas

Usage:
  .venv/bin/python run_experiment.py
"""

import pynetlogo
import pynetlogo.core as _core
import os
import pandas as pd
import numpy as np
from pathlib import Path
from itertools import product

# --- JVM setup (asm-4.0.jar conflict workaround) ---
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

NETLOGO_HOME = str(Path(__file__).parent / "NetLogo-6.4.0-64")
MODEL_PATH   = str(Path(__file__).parent / "groundwater-commons/code/Groundwater_Commons_Game.nlogo")
RESULTS_DIR  = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def parse_nl_list(s):
    """Convert NetLogo list string to numpy array."""
    s = str(s).strip()
    if s.startswith("[") and s.endswith("]"):
        return np.array([float(x) for x in s[1:-1].split()])
    return np.array([float(s)])


def run_validation(case_study: str, n_reps: int = 50):
    """
    Run the 4 mf/Mf/mF/MF enforcement scenarios for a given case study.
    Reproduces Figure 5 from Castilla-Rho et al. 2019.

    Cultural parameters (Group=S-reputation, Grid≈S-enforcement-cost):
      Australia: S-reputation=0.8, S-enforcement-cost=0.2
      USA:       S-reputation=0.4, S-enforcement-cost=0.4
      Pakistan:  S-reputation=0.4, S-enforcement-cost=0.8
      India:     S-reputation=0.6, S-enforcement-cost=0.8
    """
    CASE_PARAMS = {
        "Australia": {"economy": "Australia: Cotton(S), Vetch(W)",
                      "S-reputation": 0.8, "S-enforcement-cost": 0.2,
                      "num-farmers": 10},
        "USA":       {"economy": "Central Valley: Almonds(S)",
                      "S-reputation": 0.4, "S-enforcement-cost": 0.4,
                      "num-farmers": 50},
        "Pakistan":  {"economy": "Punjab: Rice(S), Wheat(W)",
                      "S-reputation": 0.4, "S-enforcement-cost": 0.8,
                      "num-farmers": 50},
        "India":     {"economy": "Punjab: Rice(S), Wheat(W)",
                      "S-reputation": 0.6, "S-enforcement-cost": 0.8,
                      "num-farmers": 50},
    }

    if case_study not in CASE_PARAMS:
        raise ValueError(f"Unknown case study: {case_study}. Choose from {list(CASE_PARAMS)}")

    cp = CASE_PARAMS[case_study]

    # 4 enforcement scenarios: mf, Mf, mF, MF
    scenarios = {
        "mf": {"max-monitoring-capacity": 0.1, "fine-magnitude": 0.1},
        "Mf": {"max-monitoring-capacity": 0.5, "fine-magnitude": 0.1},
        "mF": {"max-monitoring-capacity": 0.1, "fine-magnitude": 0.9},
        "MF": {"max-monitoring-capacity": 0.5, "fine-magnitude": 0.9},
    }

    METRICS = [
        "TS-compliance", "TS-boldness", "TS-vengefulness",
        "TS-norm-strength", "TS-drawdowns-mean", "TS-total-breaches",
    ]

    nl = pynetlogo.NetLogoLink(netlogo_home=NETLOGO_HOME, gui=False)
    nl.load_model(MODEL_PATH)
    print(f"Model loaded. Running {case_study}: {n_reps} reps × 4 scenarios...")

    records = []
    total = n_reps * len(scenarios)
    done = 0

    for scenario_name, scenario_params in scenarios.items():
        for rep in range(n_reps):
            # --- Burn-in (match embedded experiment setup) ---
            nl.command(f"set num-farmers {cp['num-farmers']}")
            nl.command("SETUP-EXPERIMENT")

            # Burn-in params
            nl.command("set pumping-cap 0.2")
            nl.command("set max-monitoring-capacity 0.1")
            nl.command("set fine-magnitude 0.1")
            nl.command("set voluntary-compliance-level 0")
            nl.command("set rule-breaker-level 0")
            nl.command("set metanorm? false")
            nl.command('set monitoring-style "flat"')
            nl.command('set enforcement-strategy "random"')
            nl.command("set graduated-sanctions? false")
            nl.command(f'set economy? "{cp["economy"]}"')
            nl.command("repeat 100 [go]")
            nl.command("reset-ticks")
            nl.command("set year 0")

            # Experiment params
            nl.command(f"set S-reputation {cp['S-reputation']}")
            nl.command(f"set S-enforcement-cost {cp['S-enforcement-cost']}")
            nl.command(f"set max-monitoring-capacity {scenario_params['max-monitoring-capacity']}")
            nl.command(f"set fine-magnitude {scenario_params['fine-magnitude']}")
            nl.command("update-voluntary-compliance")
            nl.command("update-rule-breakers")

            # Run 100 measurement ticks
            nl.command("repeat 100 [go]")

            # Collect metrics
            rec = {"case_study": case_study, "scenario": scenario_name, "rep": rep}
            for m in METRICS:
                arr = parse_nl_list(nl.report(m))
                rec[m] = arr  # store full time series
            records.append(rec)

            done += 1
            if done % 10 == 0:
                print(f"  {done}/{total} runs complete")

    nl.kill_workspace()
    print(f"Done. {total} runs completed.")

    # Expand to per-tick rows
    rows = []
    for rec in records:
        n_ticks = len(rec[METRICS[0]])
        for t in range(n_ticks):
            row = {k: v for k, v in rec.items() if k not in METRICS}
            row["tick"] = t
            for m in METRICS:
                row[m] = rec[m][t]
            rows.append(row)

    df = pd.DataFrame(rows)
    out = RESULTS_DIR / f"validation_{case_study.lower()}.csv"
    df.to_csv(out, index=False)
    print(f"Saved: {out}")
    return df


if __name__ == "__main__":
    import sys
    case = sys.argv[1] if len(sys.argv) > 1 else "Australia"
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    run_validation(case, reps)
