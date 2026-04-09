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

## Protocol

### run_paper.py — paper reproduction (Figure 5)

Faithfully implements the original BehaviorSpace protocol:

```
SETUP-EXPERIMENT          # ca clears all globals → S-params = 0
set lax params            # M=0.1, F=0.1; S-enf-cost and S-rep remain 0
repeat 100 [go]           # hidden burn-in (not recorded)
reset-ticks               # TS lists retain 100 burn-in entries
set actual S-params       # S-enforcement-cost, S-reputation now active
set scenario M, F
repeat 100 [go]           # measurement period
collect TS[-100:]         # last 100 entries = measurement period only
```

All 100 output years are under the enforcement scenario (no lax phase in output). Regulation onset is at year 0.

```bash
.venv/bin/python run_paper.py india
.venv/bin/python run_paper.py australia
.venv/bin/python run_paper.py pakistan
.venv/bin/python run_paper.py usa
.venv/bin/python run_paper.py canada
```

Output: `results/bs_protocol_<case>.csv`

### run_pv.py — agrivoltaic technology experiment

Free Market archetype, three PV adoption levels (0%, 50%, 100%). Shared seeds so yr 0–24 is identical across PV levels and the yr-25 bifurcation is cleanly attributable to PV adoption.

```
yr  0-24: lax (M=0.1, F=0.1), no PV
yr 25:    PV adoption event (SETUP-PV)
yr 25-49: lax, with PV
yr 50-99: enforcement scenario, with PV
```

```bash
.venv/bin/python run_pv.py
```

Output: `results/pv_freemarket.csv`

## Plotting

```bash
# Figure 5 — paper protocol results
.venv/bin/python plot_panels.py --bs australia india

# All available cases
.venv/bin/python plot_panels.py --bs

# PV comparison
.venv/bin/python plot_panels.py --pv-compare freemarket
```

Output: `figures/`

## Cultural parameter mapping

The paper formula `S = group^n × (1−grid)^m` maps to code parameters as:

```
S_reputation    = 1 − Group     (NOT Group directly)
S_enforcement_cost = Grid
```

| Case | Grid | Group | S-enforcement-cost | S-reputation | Farmers |
|---|---|---|---|---|---|
| Australia (MDB) | 0.2 | 0.8 | 0.2 | 0.2 | 10 |
| USA (Central Valley) | 0.4 | 0.4 | 0.4 | 0.6 | 50 |
| Pakistan (Punjab) | 0.8 | 0.4 | 0.8 | 0.6 | 630 |
| India (Punjab) | 0.8 | 0.6 | 0.8 | 0.4 | 630 |
| Canada (Paskapoo) | 0.30 | 0.39 | 0.30 | 0.61 | 50 |

Canada parameters are empirically derived from WVS Wave 7 (n=4018, Alberta).

## Approximate runtimes (8 workers)

| Case | Farmers | run_paper.py |
|---|---|---|
| Australia | 10 | ~40 min (100yr burn-in × 100 reps) |
| USA / Canada | 50 | ~2–3 hr |
| India / Pakistan | 630 | ~8–12 hr |

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
