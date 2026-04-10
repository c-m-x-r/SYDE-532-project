# Verification Plan: 50+50 Protocol Correction

## Overview

The corrected `run_paper.py` now implements the paper's actual protocol (50 years lax + 50 years enforcement = 100 total years, all visible) instead of the previous mismatched implementation (100 years hidden burn-in + 100 years measured).

This document outlines a step-by-step verification plan to confirm the corrected protocol reproduces the paper's results.

---

## Changes Made

### Code Changes
- **Lines 95–96**: `BURN_IN_YEARS = 50`, `MEASURE_YEARS = 50` (was 100 each)
- **Lines 102–103**: `DISPLAY_BURNIN = 50`, `DISPLAY_MEASURE = 50` (now displays all years, not a window)
- **Docstrings**: Updated to reflect 50+50 protocol (visible lax phase → enforcement response)
- **Slicing logic**: Simplified to use all 100 years instead of extracting a window

### Impact
- **Output file format**: Unchanged (still `bs_protocol_{case}.csv`)
- **Output columns**: Unchanged (still 100 rows per run; ticks 0–99)
- **Phase labels**: Ticks 0–49 = "burnin" (lax), ticks 50–99 = "enforcement"
- **Backward compatibility**: Old results files incompatible; must re-run

---

## Verification Strategy

### Phase 1: Quick Validation (10 minutes)

**Objective**: Confirm the protocol executes correctly without running full 100-replicate study.

**Steps**:

1. **Run India with minimal reps**:
   ```bash
   .venv/bin/python run_paper.py india --reps 5 --workers 2
   ```
   - Expected runtime: ~2–5 minutes
   - Generates: `results/bs_protocol_india.csv` with 5 × 4 scenarios = 20 runs (2000 data points)

2. **Verify output structure**:
   ```bash
   .venv/bin/python verify_protocol.py india --plot
   ```
   - Checks:
     ✓ Data spans ticks 0–99 (100 years total)
     ✓ Compliance at year 0 is 40–60% (before behavioral evolution)
     ✓ Phase split correct: ticks 0–49 = "burnin", ticks 50–99 = "enforcement"
     ✓ All 4 scenarios present (mf, Mf, mF, MF)
   - Generates: `results/verify_india.png` (4-panel plot)

3. **Visual inspection**:
   ```bash
   # On Windows: copy to accessible location
   cp results/verify_india.png /mnt/c/temp/
   
   # Then open in Explorer or view locally
   file:///c:/temp/verify_india.png
   ```
   - Expected pattern:
     ```
     [Tick 0]           [Tick 50]          [Tick 100]
     Compliance         Regulation      
     |←← Lax ←→|←← Enforcement →→|
     
     Compliance at t=0:  45–55% (random initial state)
     Lax phase (0–50):   Usually evolves downward (defection is profitable under M=10%, F=10%)
     Enforcement (50–100): Scenario-dependent
       - mf:   Minimal change (low monitoring, low fines)
       - Mf:   Increase (high monitoring, low fines)
       - mF:   Increase (low monitoring, high fines)
       - MF:   Strong increase (high monitoring, high fines)
     ```

4. **Compare to paper**:
   - Open Castilla-Rho et al. 2017 Figure 5 (India panel)
   - Expected:
     - All 4 scenario curves start at ~50% compliance at year 0
     - Lax phase shows compliance drift (usually down to ~30–40%)
     - Enforcement phase shows divergence (mf stays low, MF climbs high)
     - Overall shape: V-shaped (dips in lax phase, rises in enforcement phase)

---

### Phase 2: Full Validation (30–60 minutes per case)

**Objective**: Run full 100-replicate experiments and compare quantitatively against paper.

**Steps**:

1. **Run all case studies**:
   ```bash
   # India (630 farmers — slowest)
   .venv/bin/python run_paper.py india --reps 100 --workers 8
   
   # Pakistan (630 farmers)
   .venv/bin/python run_paper.py pakistan --reps 100 --workers 8
   
   # USA (50 farmers)
   .venv/bin/python run_paper.py usa --reps 100 --workers 8
   
   # Australia (10 farmers — fastest)
   .venv/bin/python run_paper.py australia --reps 100 --workers 8
   ```
   - Expected runtimes (8 workers):
     - Australia: ~5–10 min
     - USA: ~10–15 min
     - Pakistan: ~20–30 min
     - India: ~20–30 min

2. **Generate all verification plots**:
   ```bash
   for case in australia usa pakistan india; do
     .venv/bin/python verify_protocol.py $case --plot
   done
   ```
   - Outputs: `results/verify_{australia,usa,pakistan,india}.png`

3. **Quantitative comparison**:
   Create a comparison table:
   ```
   | Case | Compliance at t=0 | Lax drift | Enforcement response |
   |------|-------------------|-----------|----------------------|
   | Paper (India)    | ~50%  | → ~35%    | Scenario-dependent  |
   | Code (India)     | ?     | ?         | ?                   |
   | Match?           | ✓/✗   | ✓/✗      | ✓/✗                 |
   ```

---

## Acceptance Criteria

**The protocol is verified correct if ALL of the following hold**:

1. ✅ **Compliance baseline** (year 0):
   - All case studies: 40–60% compliance
   - Paper shows: ~50% compliance across all cases
   - Tolerance: ±10pp due to stochasticity

2. ✅ **Lax phase evolution** (years 0–50):
   - Compliance drifts, usually downward (defection is profitable)
   - Range of final compliance: 25–45%
   - Paper shows: Similar downward drift

3. ✅ **Enforcement response** (years 50–100):
   - mf scenario: Minimal change (+0–5pp)
   - Mf scenario: Moderate increase (+10–20pp)
   - mF scenario: Moderate increase (+10–20pp)
   - MF scenario: Strong increase (+15–30pp)
   - Paper shows: Similar ordering and magnitudes

4. ✅ **Case-study differences**:
   - **India/Pakistan** (high Grid=0.8):
     - Strong response in enforcement phase
     - Mf/MF scenarios show dramatic compliance gains (30–40pp)
   - **Australia/USA** (low/medium Grid):
     - Weaker response
     - Mf/MF scenarios show moderate gains (10–20pp)
   - Paper shows: These same patterns

5. ✅ **Output file integrity**:
   - Each case: 4 scenarios × 100 reps × 100 ticks = 40,000 rows
   - Phase column: Correct split at tick 50
   - No missing data in METRICS columns

6. ✅ **Visual match**:
   - Generated plots (verify_{case}.png) match paper's Figure 5 shape
   - Mean curves align; confidence bands overlap with paper's published bands

---

## What to Check If Verification Fails

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Compliance still starts at 20–30% at t=0 | Hidden burn-in not removed | Check that BURN_IN_YEARS is 50, not 100; may need to clear `results/` and re-run |
| Lax and enforcement phases not split correctly | Phase labeling broken | Check line 211: should use tick < 50 for "burnin" label |
| Only 50 ticks per run instead of 100 | Slicing logic wrong | Check lines 199–203: `lax_slice` and `enforcement_slice` should each be length 50 |
| Compliance doesn't change between scenarios | S-params not being restored | Check line 181–182: verify S-enforcement-cost and S-reputation are set to actual values before MEASURE phase |

---

## Timeline

| Step | Time | Cumulative |
|------|------|------------|
| Run India (5 reps) | 3 min | 3 min |
| Verify + plot | 1 min | 4 min |
| Visual inspection | 5 min | 9 min |
| **Phase 1 done** | — | **~10 min** |
| Run all cases (100 reps) | 60 min | 70 min |
| Generate all plots | 5 min | 75 min |
| Quantitative analysis | 10 min | 85 min |
| **Phase 2 done** | — | **~85 min** |

---

## Verification Checklist

- [ ] Phase 1 verification passed (quick check with India, 5 reps)
- [ ] Compliance at t=0 is 40–60% for India
- [ ] verify_india.png shows correct structure (regulation line at year 50)
- [ ] Lax phase shows downward drift; enforcement phase shows scenario divergence
- [ ] Compliance curves visually match paper's Figure 5
- [ ] Phase 2: Run full 100-rep experiments for all cases
- [ ] All 4 cases pass quantitative checks (table above)
- [ ] Confidence bands align with paper's published results
- [ ] Output CSV files are valid (40,000 rows each case)
- [ ] Ready to use corrected protocol for analysis/publication

---

## Next Steps After Verification

Once verified:
1. **Update analysis.py** to work with corrected protocol
2. **Update plot_panels.py** to correctly label years (0–100 with regulation line at 50)
3. **Re-run all downstream analyses** (figure generation, etc.)
4. **Document the correction** in project README and paper (if publishing results)
5. **Archive old results** (from 100+100 protocol) to avoid confusion

