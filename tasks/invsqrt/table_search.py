"""Exact per-segment search of coefficient tables in the circuit's own form (ours):
    D(v) = A - sum_j b_j(v) * c_j(S),   c_top = S,  c_j = (S + 2^(t-1-j)) >> (t-j)   (the K=6 rows, generalised)
using the per-v slack table from table_feas.py (exact, since each v's phase depends only on D(v)).
Usage: python tasks/invsqrt/table_search.py K ROW_BITS...   e.g.  6 0 1 2 3 4 5   |  5 1 2 3 4 5 6
Prints the best minimum slack per segment and overall, and saves the table to data/work/inv_gen/table_K<K>_<rows>.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import syed_model as M  # noqa: E402

K = int(sys.argv[1])
ROWS = [int(a) for a in sys.argv[2:]]
SL = np.load(M.REPO / 'data/work/inv_gen/feas_slack.npy')
W = (SL.shape[1] - 1) // 2
D6 = np.array(json.loads((M.REPO / 'data/src_pull/nov13b/ahoirg_k6c_extracted/k6data.json').read_text())['D'], dtype=np.int64)
n = 4096 >> K
t = max(ROWS)
NEG = -(1 << 62)


def coeffs(S):
    return {j: (S if j == t else (S + (1 << (t - 1 - j))) >> (t - j)) for j in ROWS}


best_all = []
table = []
for seg in range(1 << K):
    vs = np.arange(seg * n, (seg + 1) * n)
    lo = vs - vs[0]
    bits = {j: (lo >> j) & 1 for j in ROWS}
    best = (NEG, None, None)
    slope_guess = (D6[vs[0]] - D6[vs[-1]]) * (1 << t) / max(1, (n - 1))
    for S in range(max(1, int(slope_guess * 0.7)), int(slope_guess * 1.3) + 3):
        c = coeffs(S)
        sub = sum(bits[j] * c[j] for j in ROWS)
        # A chosen so that D stays inside the window: scan around the D6 intercept
        base = D6[vs] + sub  # A needed to hit D6 exactly at each v
        for A in range(int(base.min()) - 3, int(base.max()) + 4):
            idx = A - sub - D6[vs] + W
            if idx.min() < 0 or idx.max() > 2 * W:
                continue
            m = SL[vs, idx].min()
            if m > best[0]:
                best = (int(m), A, S)
    best_all.append(best[0])
    table.append([best[1], best[2]])
print(f'K={K} rows={ROWS}: overall min slack {min(best_all)}; worst segments',
      sorted(range(len(best_all)), key=lambda i: best_all[i])[:5], 'S max', max(s for _, s in table if s is not None))
out = M.REPO / f'data/work/inv_gen/table_K{K}_{"".join(map(str, ROWS))}.json'
out.write_text(json.dumps(dict(K=K, rows=ROWS, table=table, seg_slack=best_all)))
