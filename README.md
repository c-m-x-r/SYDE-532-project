# Groundwater Commons Game — Extended

Python runners and analysis for the **Groundwater Commons Game** (Castilla-Rho et al. 2017), extended with a Canada case study and agrivoltaic (PV) technology experiment.

## Upstream model

**The Groundwater Commons Game** v1.2.0  
Castilla-Rho, J. C., Rojas, R., Andersen, M. S., Holley, C. & Mariethoz, G.  
*Social tipping points in global groundwater management.*  
Nature Human Behaviour 1, 640–649 (2017).  
https://www.comses.net/codebases/5634/releases/1.2.0/  
License: GPL-3.0

## Requirements

- **NetLogo 6.4.0** installed at `NetLogo-6.4.0-64/` (not tracked — download from https://ccl.northwestern.edu/netlogo/6.4.0/)
- **Python 3.10+** via [uv](https://github.com/astral-sh/uv)

```bash
uv sync
```

> **asm conflict:** pyNetLogo 0.5.2 conflicts with `asm-4.0.jar` bundled in NetLogo 6.4.0's vid extension. All runners monkey-patch `pynetlogo.core.find_jars` to exclude it automatically — no manual action needed.

## Model

`model/Groundwater_Commons_Game.nlogo` — the upstream model with the following changes applied:

| Change | Type |
|---|---|
| Version string `NetLogo 5.3.1` → `NetLogo 6.4.0` | Compatibility |
| Three lines using NetLogo 5 `?` anonymous syntax rewritten for NetLogo 6 | Compatibility |
| Canada economy: Canola (summer), Wheat (winter) | Extension |
| Free Market economy: generic cash crop (summer + winter) | Extension |
| Agrivoltaic PV globals (`pv-adoption-fraction`, `pv-water-reduction`, `pv-income-bonus`) | Extension |
| `has-pv?` farmer variable + `SETUP-PV` procedure | Extension |
| PV-adjusted effective IWA and solar income in E-score calculations | Extension |

The upstream unmodified model is at `model/upstream/` for reference. The embedded BehaviorSpace XML is unchanged from upstream.

## Runners

### run_paper.py — paper reproduction (Figure 5)

Faithfully implements the original BehaviorSpace protocol:

```
SETUP-EXPERIMENT          # ca clears all globals → S-params = 0
set lax burn-in params    # M=0.1, F=0.1; S-enf-cost and S-rep remain 0
repeat 100 [go]           # hidden burn-in (not recorded)
reset-ticks               # TS lists retain 100 burn-in entries
set actual S-params       # S-enforcement-cost, S-reputation now active
set scenario M, F
repeat 100 [go]           # measurement period
collect TS[-100:]         # last 100 entries = measurement period only
```

All 100 output ticks are under the enforcement scenario (no lax phase in output).

```
usage: run_paper.py [-h] [--reps REPS] [--workers WORKERS]
                    {australia,usa,pakistan,india,canada}

positional arguments:
  {australia,usa,pakistan,india,canada}

options:
  --reps REPS        Repetitions per enforcement scenario (default: 100, paper used 50)
  --workers WORKERS  Parallel JVM workers, ~1 GB RAM each (default: 8)
```

```bash
.venv/bin/python run_paper.py india
.venv/bin/python run_paper.py australia --reps 50
.venv/bin/python run_paper.py pakistan --workers 4
```

Output: `results/bs_protocol_<case>.csv`

Plot: `.venv/bin/python plot_panels.py --bs <case>`

---

### run_pv.py — agrivoltaic technology experiment

Free Market archetype, sweeps PV adoption fractions with shared seeds so yr 0–adopt_year is identical across PV levels.

```
yr  0 – adopt_year-1:   lax (M=0.1, F=0.1), no PV
yr  adopt_year:         PV adoption event (SETUP-PV)
yr  adopt_year – reg_year-1: lax, with PV
yr  reg_year – 99:      enforcement scenario, with PV
```

```
usage: run_pv.py [-h] [--pv-fracs F [F ...]] [--water-reduction R]
                 [--income-bonus B] [--adopt-year Y] [--reg-year Y]
                 [--reps REPS] [--workers WORKERS]

PV parameters:
  --pv-fracs F [F ...]  Adoption fractions to sweep (default: 0.0 0.5 1.0)
  --water-reduction R   Fractional IWA reduction from panel shading (default: 0.30)
  --income-bonus B      Solar income $/ha/season of installed panel area (default: 400)

Timeline:
  --adopt-year Y        Year panels are installed, 0-indexed (default: 25)
  --reg-year Y          Year enforcement switches from lax to scenario (default: 50)

Compute:
  --reps REPS           Reps per (scenario, PV level) combination (default: 100)
  --workers WORKERS     Parallel JVM workers, ~1 GB RAM each (default: 8)
```

```bash
# Default run (3 PV levels × 4 scenarios × 100 reps)
.venv/bin/python run_pv.py

# Custom PV sweep with different physical parameters
.venv/bin/python run_pv.py --pv-fracs 0.0 0.25 0.5 0.75 1.0 --water-reduction 0.25 --income-bonus 350

# Earlier adoption, later enforcement
.venv/bin/python run_pv.py --adopt-year 10 --reg-year 60

# Quick test
.venv/bin/python run_pv.py --reps 10 --workers 2
```

Output: `results/pv_freemarket.csv`

---

## Plotting

```bash
# Figure 5 — one or more case studies
.venv/bin/python plot_panels.py --bs australia india

# All available cases (auto-discovers results/bs_protocol_*.csv)
.venv/bin/python plot_panels.py --bs

# PV comparison panels
.venv/bin/python plot_panels.py --pv-compare freemarket
```

Output: `figures/`

---

## Cultural parameter mapping

The paper formula `S = group^n × (1−grid)^m` maps to model parameters as:

```
S_reputation       = 1 − Group     (NOT Group directly)
S_enforcement_cost = Grid
```

| Case | Grid | Group | S-enforcement-cost | S-reputation | Farmers |
|---|---|---|---|---|---|
| Australia (MDB) | 0.20 | 0.80 | 0.20 | 0.20 | 10 |
| USA (Central Valley) | 0.40 | 0.40 | 0.40 | 0.60 | 50 |
| Pakistan (Punjab) | 0.80 | 0.40 | 0.80 | 0.60 | 630 |
| India (Punjab) | 0.80 | 0.60 | 0.80 | 0.40 | 630 |
| Canada (Paskapoo) | 0.30 | 0.39 | 0.30 | 0.61 | 50 |

Canada parameters derived from WVS Wave 7 (n=4018, Alberta).

---

## Approximate runtimes (8 workers)

| Case | Farmers | run_paper.py (100 reps) |
|---|---|---|
| Australia | 10 | ~40 min |
| USA / Canada | 50 | ~2–3 hr |
| India / Pakistan | 630 | ~8–12 hr |

`run_pv.py` default (3 PV levels × 4 scenarios × 100 reps, 50 farmers): ~6–8 hr.

---

## Layout

```
model/
  Groundwater_Commons_Game.nlogo   # extended model (NetLogo 6.4.0)
  upstream/
    Groundwater_Commons_Game.nlogo # original unmodified (reference)
run_paper.py      # Figure 5 reproduction — faithful BehaviorSpace protocol
run_pv.py         # agrivoltaic PV experiment
analysis.py       # loaders + Figure 5 plotting functions
plot_panels.py    # multi-panel figure CLI
data/
  NSW_survey_analysis.R
  grid_group_WVS6_analysis.R
docs/
  SI.pdf          # Castilla-Rho 2017 supplementary information
pyproject.toml
UPSTREAM.cff      # upstream model attribution
```
