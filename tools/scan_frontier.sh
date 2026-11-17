#!/usr/bin/env bash
# Scan the public frontier: download outputs of recently run competition notebooks (and recently updated
# datasets that ship circuits), stage every new task member, score new members with the official verifiers
# (salt '' + 2 random salts) and print the best member per task next to the current portfolio (v4).
# Nothing is submitted. Usage (repo root): tools/scan_frontier.sh [PAGES]
set -euo pipefail
cd "$(dirname "$0")/.."
K=../.venv/bin/kaggle; PY=../.venv/bin/python
C=google-verifiable-quantum-circuit-compilation
OUT=data/public_out2; DS=data/public_ds; CAND=data/cand2; LOG=data/logs/s2
mkdir -p $OUT $DS $CAND $LOG
pages=${1:-2}

# 1. notebooks: newest runs, then best voted; re-download only when lastRunTime changed
lst=$( { for srt in dateRun voteCount; do
           tok=""; for p in $(seq 1 $pages); do
             $K kernels list --competition $C --sort-by $srt --page-size 100 ${tok:+--page-token $tok} 2>/dev/null \
               | awk 'NR>2 && NF>4 {print $1, $(NF-2)"_"$(NF-1)}'; done; done; } | sort -u -k1,1)
while read -r r last; do
  [ -z "$r" ] && continue
  o="$OUT/${r/\//__}"; stamp="$o/.ran"
  [ -f "$stamp" ] && [ "$(cat $stamp)" = "$last" ] && continue
  rm -rf "$o"; mkdir -p "$o"
  timeout 900 $K kernels output "$r" -p "$o" -q >/dev/null 2>&1 || true
  echo "$last" > "$stamp"
done <<< "$lst"

# 2. datasets that look like circuit portfolios, updated recently
for d in $($K datasets list -s vqcc --sort-by updated --page-size 40 2>/dev/null | awk 'NR>2{print $1}'); do
  o="$DS/${d/\//__}"; [ -d "$o" ] && continue
  mkdir -p "$o"; timeout 900 $K datasets download "$d" -p "$o" --unzip -q >/dev/null 2>&1 || true
done
# Datasets that ship loose members: wrap them as submission.zip under OUT so scan_public sees them.
for o in $DS/*/; do
  n=$(basename $o); z="$OUT/ds__$n/submission.zip"; [ -f "$z" ] && continue
  sub=$(find "$o" -name 'invsqrt.km?' -o -name 'dqi.km?' -o -name 'angle_k_0.km?' | head -1) || true
  [ -z "$sub" ] && continue
  root=$(dirname "$sub"); [ "$(basename "$root")" = dfthcsos ] && root=$(dirname "$root")
  mkdir -p "$OUT/ds__$n"; tmp=$(mktemp -d)
  [ -f "$root/invsqrt.kmb" ] && cp "$root/invsqrt.kmb" $tmp/; [ -f "$root/dqi.kmb" ] && cp "$root/dqi.kmb" $tmp/
  if [ -d "$root/dfthcsos" ]; then cp -r "$root/dfthcsos" $tmp/
  elif ls "$root"/angle_k_0.km? >/dev/null 2>&1; then mkdir $tmp/dfthcsos; cp "$root"/angle_k_*.km? "$root"/submission.npz $tmp/dfthcsos/ 2>/dev/null || true; fi
  za=$(realpath -m "$z"); (cd $tmp && zip -q -r "$za" .); rm -rf $tmp
done

# 3. stage and score new members only
$PY -I tools/scan_public.py --root $OUT --out $CAND > $LOG/scan_latest.jsonl
for d in $CAND/pub_*; do
  n=$(basename $d); t=$(echo $n | cut -d_ -f2)
  [ -s "$LOG/$n.jsonl" ] && continue
  $PY harness/score.py $d --tasks $t --random-salts 2 --note "frontier scan $n" > $LOG/$n.jsonl 2> $LOG/$n.err || true
done

# 4. report
$PY -I - "$LOG" <<'EOF'
import json, pathlib, sys
log = pathlib.Path(sys.argv[1]); best = {}
cur = {'invsqrt': 27.765339, 'dqi': 70.408690, 'dfthcsos': 11.388691}  # portfolio_v12 (dqi = 20-salt geo mean)
for f in log.glob('pub_*.jsonl'):
    rs = [json.loads(l) for l in f.read_text().splitlines() if '"task"' in l]
    if not rs: continue
    ok = all(r['pass'] for r in rs); t = rs[0]['task']; m = min(r['ratio'] for r in rs) if ok else 0
    if ok and m > best.get(t, (0, ''))[0]: best[t] = (m, f.stem)
gm_cur = (cur['invsqrt'] * cur['dqi'] * cur['dfthcsos']) ** (1/3)
new = {t: max(cur[t], best.get(t, (0,))[0]) for t in cur}
gm_new = (new['invsqrt'] * new['dqi'] * new['dfthcsos']) ** (1/3)
for t in cur:
    b = best.get(t, (0, '-'))
    print(f"{t:9s} current {cur[t]:.6f}  best public (worst salt) {b[0]:.6f} {b[1]}{'  <-- BETTER' if b[0] > cur[t] * (1 + 1e-7) else ''}")
print(f'GM current {gm_cur:.5f}  achievable {gm_new:.5f}')
EOF
