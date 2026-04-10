#!/usr/bin/env bash
# run_all_cases.sh
# Runs all 5 case studies sequentially using 3 workers each.
# Designed to be launched in the background via nohup.
# Log is written to results/run_all.log (stdout/stderr redirected by caller).

set -euo pipefail

PROJ=/home/mc/projects/nlogo
PY="$PROJ/.venv/bin/python"
SCRIPT="$PROJ/run_paper.py"
WORKERS=5
CASES=(australia usa canada pakistan india)

echo "========================================" >&2
echo "run_all_cases.sh started at $(date)" >&2
echo "Cases: ${CASES[*]}" >&2
echo "Workers per case: $WORKERS" >&2
echo "========================================" >&2

cd "$PROJ"

for case in "${CASES[@]}"; do
    echo "" >&2
    echo ">>> STARTING $case at $(date)" >&2
    "$PY" "$SCRIPT" "$case" --workers "$WORKERS"
    echo ">>> FINISHED $case at $(date)" >&2
done

echo "" >&2
echo "========================================" >&2
echo "ALL CASES DONE at $(date)" >&2
echo "========================================" >&2
