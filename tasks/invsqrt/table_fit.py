"""Given feas_slack.npy (table_feas.py), find for K address bits the largest margin m such that every segment of
4096/2^K root values admits a linear (or quadratic, --deg 2) coefficient D(v) inside the per-v feasible set (ours).
Rounding: a real fit f rounds into [lo, hi] iff f in [lo - 0.5, hi + 0.5) (a real-valued fit that rounds to a feasible integer).
Usage: python tasks/invsqrt/table_fit.py K [deg]
"""
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parent))
import syed_model as M  # noqa: E402

S = np.load(M.REPO / 'data/work/inv_gen/feas_slack.npy')
W = (S.shape[1] - 1) // 2
K = int(sys.argv[1])
deg = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def intervals(m):
    ok = S >= m
    lo = np.full(4096, np.nan)
    hi = np.full(4096, np.nan)
    for v in range(4096):
        idx = np.flatnonzero(ok[v])
        if len(idx):
            lo[v], hi[v] = idx[0] - W, idx[-1] - W
            if idx[-1] - idx[0] + 1 != len(idx):
                pass  # non-contiguous; the hull is a relaxation
    return lo, hi


def seg_ok(lo, hi, vs):
    if np.isnan(lo[vs]).any():
        return False
    l = (vs - vs[0]).astype(float)
    X = np.vstack([l ** i for i in range(deg + 1)]).T
    A = np.vstack([X, -X])
    b = np.r_[hi[vs] + 0.49, -(lo[vs] - 0.49)]
    r = linprog(np.zeros(deg + 1), A_ub=A, b_ub=b, bounds=[(None, None)] * (deg + 1), method='highs')
    return r.status == 0


def feasible(m):
    lo, hi = intervals(m)
    n = 4096 >> K
    bad = [s for s in range(1 << K) if not seg_ok(lo, hi, np.arange(s * n, (s + 1) * n))]
    return bad


lo_m, hi_m = 0, 600_000_000
print('m=0 bad segments:', len(feasible(0)))
for _ in range(22):
    mid = (lo_m + hi_m) // 2
    if feasible(mid):
        hi_m = mid
    else:
        lo_m = mid
print(f'K={K} deg={deg}: max margin with fixed K6 angles ~ {lo_m}')
