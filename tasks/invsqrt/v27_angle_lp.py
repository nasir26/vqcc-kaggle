"""Exact angle LP for the 44-qubit invsqrt (ours). theta(x) = C(x) + sum_i a_i W_i(x) (mod 2^64), with the per-site
features W measured by perturbation (W_efd.npy). Maximise min_x tol(x) - |theta(x) - target(x)| over integer angle
offsets by cutting planes (scipy HiGHS), then evaluate exactly in int64.
Usage: python tasks/invsqrt/v27_angle_lp.py  -> data/work/inv_gen/v27/lp_angles64.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v27_angles as A  # noqa: E402
import sim_phase as SP  # noqa: E402

V = A.V27
W = np.load(V / 'W_efd.npy').astype(np.int64)
th0 = np.load(V / 'theta_efd.npy')
_, rot = A.sites(V / 'efd.kmx')
base = np.array([u for u, _, _ in rot], dtype=object)
target, tol = SP.V.reference_values(SP.SPEC, np.arange(1, SP.SPEC.max_x + 1, dtype=np.uint64))
e0 = (th0 - target).view(np.int64)
tol = tol.astype(np.int64)


def exact_margin(delta):
    d = np.array([int(v) for v in delta], dtype=np.int64)
    err = e0 + W @ d
    return int((tol - np.abs(err)).min()), err


m0, _ = exact_margin(np.zeros(33))
print('base margin', m0, flush=True)
Wf = W.astype(np.float64)
e0f = e0.astype(np.float64)
tolf = tol.astype(np.float64)
slack = tolf - np.abs(e0f)
active = set(np.argsort(slack)[:5000].tolist())
S = 1e6  # variable scale
for it in range(60):
    idx = np.array(sorted(active))
    Fa = Wf[idx] * S
    A1 = np.hstack([Fa, np.ones((len(idx), 1))])
    A2 = np.hstack([-Fa, np.ones((len(idx), 1))])
    res = linprog(np.r_[np.zeros(33), -1.0], A_ub=np.vstack([A1, A2]),
                  b_ub=np.r_[tolf[idx] - e0f[idx], tolf[idx] + e0f[idx]],
                  bounds=[(-1e5, 1e5)] * 33 + [(None, None)], method='highs')
    dl = res.x[:33] * S
    err = e0f + Wf @ dl
    sl = tolf - np.abs(err)
    print(it, 'LP', round(-res.fun), 'true', round(sl.min()), 'rows', len(idx), flush=True)
    if sl.min() >= -res.fun - 2:
        break
    active |= set(np.argsort(sl)[:3000].tolist())
dint = [int(round(v)) for v in dl]
m1, err = exact_margin(dint)
print('rounded exact margin', m1, 'gain', m1 / m0)
out = dict(angles64=[int(b + d) % (1 << 64) for b, d in zip(base, dint)], delta=dint, margin=m1, base_margin=m0)
(V / 'lp_angles64.json').write_text(json.dumps(out))
