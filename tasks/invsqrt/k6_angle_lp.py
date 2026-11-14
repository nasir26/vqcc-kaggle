"""Exact-model angle LP for the K=6 table circuit (ahoirg 4560ac0c lineage), ours.

The ring26 phase is sum_k angle_k * f_k(x) (+ fixed Clifford/T overflow terms), with the 33 Boolean features f_k
known exactly from tasks/invsqrt/syed_model.py. Maximise the official min margin m = min_x tol(x) - |err(x)| over
angle offsets on the 2^-64 grid (LP relaxation, cutting planes over x, scipy HiGHS), then round to the 2^-50 grid
the circuit uses and re-evaluate exactly on all 3,133,452 inputs.
Usage: python tasks/invsqrt/k6_angle_lp.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parent))
import syed_model as M  # noqa: E402

REPO = M.REPO
K6 = REPO / 'data/src_pull/nov13b/ahoirg_k6c_extracted'
d = json.loads((K6 / 'k6data.json').read_text())
a = json.loads((K6 / 'angles.json').read_text())
D = np.array(d['D'], dtype=np.int64)
C = 2 * D
U0 = []
for v in range(4096):
    rc = (v * (v + 1) // 2) & 7
    s = -1
    for i in range(3):
        s += (2 * ((rc >> i) & 1) - 1) * ((int(C[v]) + (1 << (11 - i))) >> (12 - i))
    U0.append(s)
ch = M.chart()
U = M.numerator_U(ch, C=C, U0=U0)
p, _ = M.divide(ch, U)
base_angles = list(a['angles_units50'])
ph0, r = M.ring26_phase50(p, ch['e'], angles=tuple(base_angles))
print('base', M.margin(ph0))
k = ch['e']
F = np.zeros((len(r), 33), dtype=np.float64)
for i in range(26):
    F[:, i] = (r >> i) & 1
for j in range(7):
    F[:, 26 + j] = ((r >> j) & 1) * (k > j)
target, tol = M.reference()
theta = ph0.astype(np.uint64) << np.uint64(14)
e0 = (theta - target).view(np.int64).astype(np.float64)
tolf = tol.astype(np.float64)
scale = 2.0**14  # work in units of 2^-50 for the variables
active = list(np.argsort(tolf - np.abs(e0))[:4000])
best = None
for it in range(30):
    idx = np.array(sorted(set(active)))
    Fa = F[idx] * scale
    # vars: delta_0..32 (units 2^-50), m ; maximise m:  e0 + F d <= tol - m ; -(e0 + F d) <= tol - m
    A1 = np.hstack([Fa, np.ones((len(idx), 1))])
    A2 = np.hstack([-Fa, np.ones((len(idx), 1))])
    b1 = tolf[idx] - e0[idx]
    b2 = tolf[idx] + e0[idx]
    res = linprog(np.r_[np.zeros(33), -1.0], A_ub=np.vstack([A1, A2]), b_ub=np.r_[b1, b2],
                  bounds=[(-2e4, 2e4)] * 33 + [(None, None)], method='highs')
    dlt = res.x[:33]
    err = e0 + F @ (dlt * scale)
    slack = tolf - np.abs(err)
    worst = np.argsort(slack)[:2000]
    print(it, 'LP m', -res.fun, 'true m', slack.min(), 'rows', len(idx))
    if slack.min() >= -res.fun - 1:
        best = dlt
        break
    active += list(worst)
best = dlt if best is None else best
# round to the 2^-50 grid, small local search on rounding
ang = [base_angles[i] + int(round(best[i])) for i in range(33)] + [0]
ph, _ = M.ring26_phase50(p, ch['e'], angles=tuple(ang))
m = M.margin(ph)
print('rounded', m, 'charge', M.rot_charge(m['min_margin'], 33), 'base charge', M.rot_charge(116291417, 33))
out = REPO / 'data/work/inv_gen/k6_lp_angles.json'
out.write_text(json.dumps(dict(angles_units50=ang, margin=m, base=base_angles)))
print('wrote', out)
