"""Feasibility of smaller coefficient tables (ours), with the exact model as reference.

For each root value v and each coefficient offset delta in [-W, W] around the K=6 coefficient D6(v), evaluate the
exact phase of every input with that v (fixed K=6 angles) and record the minimum slack. This gives, per v, the set of
D values that keep every input inside tolerance with slack >= m. A table with fewer rows is feasible at margin m only
if a per-segment linear function (intercept + slope * low bits, rounded) fits inside all those intervals.
Usage: python tasks/invsqrt/table_feas.py [W]   -> data/work/inv_gen/feas_slack.npy  (shape 4096 x (2W+1))
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import syed_model as M  # noqa: E402

K6 = M.REPO / 'data/src_pull/nov13b/ahoirg_k6c_extracted'
D6 = np.array(json.loads((K6 / 'k6data.json').read_text())['D'], dtype=np.int64)
ANG = tuple(json.loads((K6 / 'angles.json').read_text())['angles_units50'])


def seed(C):
    v = np.arange(4096)
    rc = (v * (v + 1) // 2) & 7
    s = -np.ones(4096, dtype=np.int64)
    for i in range(3):
        s += (2 * ((rc >> i) & 1) - 1) * ((C + (1 << (11 - i))) >> (12 - i))
    return s


def slack_for(D, ch, target, tol, quad=None):
    C = 2 * D
    U = M.numerator_U(ch, C=C, U0=seed(C))
    if quad is not None:
        U = U + quad
    p, _ = M.divide(ch, U)
    ph, _ = M.ring26_phase50(p, ch['e'], angles=ANG)
    theta = ph.astype(np.uint64) << np.uint64(14)
    err = (theta - target).view(np.int64)
    return tol.astype(np.int64) - np.abs(err)


if __name__ == '__main__':
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    ch = M.chart()
    target, tol = M.reference()
    v = ch['v']
    out = np.zeros((4096, 2 * W + 1), dtype=np.int64)
    for j, dl in enumerate(range(-W, W + 1)):
        try:
            sl = slack_for(D6 + dl, ch, target, tol)
        except AssertionError:
            out[:, j] = -1 << 62
            continue
        mins = np.full(4096, 1 << 62, dtype=np.int64)
        np.minimum.at(mins, v, sl)
        out[:, j] = mins
        print(dl, int(mins.min()), flush=True)
    np.save(M.REPO / 'data/work/inv_gen/feas_slack.npy', out)
