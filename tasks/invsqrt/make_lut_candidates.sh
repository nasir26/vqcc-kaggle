#!/usr/bin/env bash
# Generate the LUT-NR candidates queued for official verification (WSL, repo root).
set -euo pipefail
PY=/opt/vqcc/venv/bin/python
common=(--a 7 --wc 16 --d 7 --square 27 --product 27 --check 2048)
$PY tasks/invsqrt/lut_nr.py data/comp data/candidates/invsqrt_lut_best "${common[@]}" --result 27
$PY tasks/invsqrt/lut_nr.py data/comp data/candidates/invsqrt_lut_safe "${common[@]}" --result 28
