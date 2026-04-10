#!/usr/bin/env bash
# run_india_pakistan.sh
# Runs pakistan then india with 6 workers and 50 reps each.
# Designed to be launched after canada finishes, replacing the main script.

set -euo pipefail

PROJ=/home/mc/projects/nlogo
PY="$PROJ/.venv/bin/python"
SCRIPT="$PROJ/run_paper.py"
WORKERS=6
REPS=50
CASES=(pakistan india)

echo "========================================" >&2
echo "run_india_pakistan.sh started at $(date)" >&2
echo "Cases: ${CASES[*]}" >&2
echo "Workers: $WORKERS | Reps: $REPS" >&2
echo "========================================" >&2

cd "$PROJ"

for case in "${CASES[@]}"; do
    echo "" >&2
    echo ">>> STARTING $case at $(date)" >&2
    "$PY" "$SCRIPT" "$case" --workers "$WORKERS" --reps "$REPS"
    echo ">>> FINISHED $case at $(date)" >&2
done

echo "" >&2
echo "========================================" >&2
echo "PAKISTAN + INDIA DONE at $(date)" >&2
echo "========================================" >&2
