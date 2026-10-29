#!/usr/bin/env bash
# Verify every staged public candidate (data/candidates/pub_<task>_<sha8>) once under the public salt.
# Usage: tools/verify_staged.sh [extra score.py args]   (log: data/logs/verify_staged.log)
cd "$(dirname "$0")/.."
for d in data/candidates/pub_*; do
  t=$(basename "$d" | cut -d_ -f2)
  src=$(python3 -c "import json;print(','.join(json.load(open('$d/params.json'))['sources']))")
  echo "=== $d ($src)"
  ../.venv/bin/python harness/score.py "$d" --tasks "$t" --max-workers 64 --note "public member $(basename $d) from $src" "$@" 2>&1 | grep '"task"'
done
echo ALL_DONE
