"""Exact-formula sweep of dfthcsos shapes (R, B, C, brot, J): which shapes could beat the best public T x Q.

Heuristic state-preparation and Givens costs come from the official verifier (dfthcsos.verify.heuristic_costs).
Lookup (ANGLE) costs are an ESTIMATE calibrated on the best public circuits (SomeJoint (8,143,60), brot 8, J 5:
8,366 Toffolis over both passes for K = 15 circuits and 1,220 addresses), scaled linearly in addresses and K:
  T_ang = 2 * K * c * (N + R B),  c = 8366 / (2 * 15 * 1220).
Angle-circuit temporaries are estimated as 128 - selection - J * brot (assumed to fit under the cap). lambda_eff is
held at the public 48.61 (it cannot drop below ~46.8 with the fixed shift); feasibility of 20 mHa at the shape is not
checked here (measured floor: R C >= 290 at 20 mHa). Output: the 25 best estimated ratios.

usage: python tasks/dfthcsos/shape_sweep.py DATA_DIR
"""
import itertools
import math
import sys

sys.path += [f'{sys.argv[1]}/kickmix', f'{sys.argv[1]}/verifiers']
from dfthcsos import verify as V  # noqa: E402

N, LAM, BASE = 76, 48.6138, 3355599588.3155365
c = 8366 / (2 * 15 * 1220)
rows = []
for R, B, C, brot, J in itertools.product(range(1, 41), range(8, 400, 1), (8, 12, 16, 20, 24, 30, 36, 40, 46, 50, 55, 60, 64),
                                         (7, 8, 9, 10), range(3, 8)):
    if R * C < 290:
        continue
    A = N + R * B
    sel = math.ceil(math.log2(A))
    if sel + J * brot > 120:
        continue
    try:
        h = V.heuristic_costs(N, R, B, C, brot)
    except Exception:
        continue
    K = math.ceil((N - 1) / J)
    T = h['toffoli'] + 2 * K * c * A
    Q = h['persistent_qubits'] + J * brot + max(h['temporary_qubits'], 128 - sel - J * brot)
    score = LAM * T * Q
    rows.append((BASE / score, R, B, C, brot, J, round(T), Q, h['toffoli'], h['temporary_qubits'], A))
rows.sort(reverse=True)
ref = [r for r in rows if r[1:6] == (8, 143, 60, 8, 5)]
print('reference (8,143,60,8,5):', ref[0] if ref else 'n/a')
print('ratio  R   B   C brot J      T    Q  T_heur temp  addr')
for r in rows[:25]:
    print(f'{r[0]:6.2f} {r[1]:3d} {r[2]:3d} {r[3]:3d} {r[4]:3d} {r[5]:2d} {r[6]:6d} {r[7]:4d} {r[8]:6d} {r[9]:4d} {r[10]:5d}')
