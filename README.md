# Groundwater Commons Game — Reproduction & Extension

Python infrastructure for running and analysing the **Groundwater Commons Game** agent-based model (Castilla-Rho et al. 2019), implemented in NetLogo 6.x.

Reproduces Figure 5 from the paper and extends the model with a Canada (Paskapoo Formation) case study.

## Requirements

- NetLogo 6.4.0 installed at `NetLogo-6.4.0-64/` (not included — download separately)
- Python 3.10+, managed with [uv](https://github.com/astral-sh/uv)

```bash
uv sync
```

> **Note:** pyNetLogo 0.5.2 conflicts with `asm-4.0.jar` bundled in the NetLogo 6.4.0 vid extension. All runners monkey-patch `pynetlogo.core.find_jars` to exclude it automatically.

## Model

`groundwater-commons/code/Groundwater_Commons_Game.nlogo` — the original model with two compatibility patches applied:

- Version string updated from `NetLogo 5.3.1` → `NetLogo 6.4.0`
- Three lines using NetLogo 5 anonymous variable syntax (`?`) rewritten for NetLogo 6

## Running simulations

### Paper protocol (Figure 5)

Runs 400 simulations (4 scenarios × 100 reps) using the protocol described in the paper: 50 years of lax regulation followed by 50 years of the target enforcement scenario.

```bash
.venv/bin/python run_paper_protocol_generic.py <case_study>
```

Available case studies: `australia`, `usa`, `pakistan`, `india`, `canada`

Output: `results/paper_protocol_<case>.csv` — tidy CSV, one row per (run, year).

RAM: 8 parallel JVMs (~8 GB). Reduce `MAX_WORKERS` in the script if needed.

### Approximate runtimes

| Case study | Farmers | ~Time (8 workers) |
|---|---|---|
| Australia | 10 | ~20 min |
| USA / Canada | 50 | ~1–2 hr |
| India / Pakistan | 630 | several hours |

## Plotting

```bash
# All available case studies
.venv/bin/python plot_panels.py

# Specific panels
.venv/bin/python plot_panels.py australia india canada
```

Output: `figures/figure5_<tag>.png`

## Cultural parameter mapping

The paper's Grid/Group cultural dimensions map to model parameters as follows. The formula `S = group^n × (1−grid)^m` in the paper corresponds to `S = (1−S_reputation)^n × (1−S_enforcement_cost)^m` in the code, so **S_reputation = 1 − Group**.

| Case study | Grid | Group | S-enforcement-cost | S-reputation | Farmers |
|---|---|---|---|---|---|
| Australia | 0.2 | 0.8 | 0.2 | 0.2 | 10 |
| USA | 0.4 | 0.4 | 0.4 | 0.6 | 50 |
| Pakistan | 0.8 | 0.4 | 0.8 | 0.6 | 630 |
| India | 0.8 | 0.6 | 0.8 | 0.4 | 630 |
| Canada | 0.25 | 0.60 | 0.25 | 0.40 | 50 |

Canada parameters are provisional (WVS Wave 7 estimates for Alberta); treat as prospective scenario analysis.

## File layout

```
├── groundwater-commons/
│   └── code/Groundwater_Commons_Game.nlogo   # patched model
├── experiments/
│   └── validate_australia.xml                # BehaviorSpace experiment
├── run_paper_protocol_generic.py  # main runner (all case studies)
├── run_paper_protocol.py          # original Australia-only runner
├── run_experiment.py              # BehaviorSpace-based alternative runner
├── analysis.py                    # CSV parsing + Figure 5 plotting functions
├── plot_panels.py                 # multi-panel figure generator
├── run.py                         # standalone pyNetLogo setup / scratch
├── main.py                        # entry point / scratch
├── desertification-toy.nlogo      # toy desertification model
└── pyproject.toml                 # Python dependencies
```

## Reference

Castilla-Rho, J.C., Rojas, R., Renard, P., Mariethoz, G., Bhatt, S. (2019). *Social tipping points in global groundwater management.* Nature Human Behaviour. https://doi.org/10.1038/s41562-019-0554-0
