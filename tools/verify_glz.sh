#!/usr/bin/env bash
# Verify staged dmitriigluzdov dataset chemistry sets (data/candidates/glz_*) under the public salt.
cd "$(dirname "$0")/.."
for d in data/candidates/glz_*; do
  echo "=== $d"; ../.venv/bin/python harness/score.py "$d" --tasks dfthcsos --max-workers 32 --note "public member $(basename $d)" 2>&1 | grep '"task"'
done; echo ALL_DONE
