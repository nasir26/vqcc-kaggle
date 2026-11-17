"""Shared exact data and LP for the 44-qubit invsqrt (ours)."""
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sim_phase as SP  # noqa: E402

V = Path(__file__).resolve().parents[2] / 'data/work/inv_gen/v27'
W = np.load(V / 'W_efd.npy').astype(np.float64)
th0 = np.load(V / 'theta_efd.npy')
target, tol_u = SP.V.reference_values(SP.SPEC, np.arange(1, SP.SPEC.max_x + 1, dtype=np.uint64))
e0 = (th0 - target).view(np.int64).astype(np.float64)
tol = tol_u.astype(np.int64).astype(np.float64)


def cost(m, n_rot, tof=1459.3748802688297, t_base=2.499900279707492, q=44):
    eps = math.pi * m / 2**64 / n_rot
    t = t_base + n_rot * (0.56 * math.log2(1 / eps) + 5.3)
    return q * (tof + t / 4)


def lp(F, rows=None, iters=60, init=4000, bound=2e5, S=1e6, verbose=False):
    """Maximise min tol - |e0 + F d| over d (columns of F in units 2^-64). F: (N, k) float. Returns (m_true, d)."""
    k = F.shape[1]
    sl = tol - np.abs(e0)
    active = set(np.argsort(sl)[:init].tolist()) if rows is None else set(rows)
    for it in range(iters):
        idx = np.array(sorted(active))
        Fa = F[idx] * S
        A1 = np.hstack([Fa, np.ones((len(idx), 1))])
        A2 = np.hstack([-Fa, np.ones((len(idx), 1))])
        res = linprog(np.r_[np.zeros(k), -1.0], A_ub=np.vstack([A1, A2]),
                      b_ub=np.r_[tol[idx] - e0[idx], tol[idx] + e0[idx]],
                      bounds=[(-bound, bound)] * k + [(None, None)], method='highs')
        d = res.x[:k] * S
        sl = tol - np.abs(e0 + F @ d)
        if verbose:
            print(it, -res.fun, sl.min(), len(idx), flush=True)
        if sl.min() >= -res.fun - 2:
            return sl.min(), d
        active |= set(np.argsort(sl)[:2000].tolist())
    return sl.min(), d
