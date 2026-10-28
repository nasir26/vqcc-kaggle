"""Model what-ifs for dfthcsos (ordinary-QROM ANGLE_k, max J under the 128-qubit cap).

Score ratios vs the baseline hold lambda_eff FIXED at the baseline value, so they isolate the
T x Q effect of (brot, R, B, C); a real candidate must be re-evaluated for accuracy and lambda_eff.
Usage (WSL): python tasks/dfthcsos/whatif.py data/comp
"""
import math
import sys

N, LAM, BASE = 76, 49.30136925057438, 3355599588.3155365


def model(R, B, C, brot):
    from dfthcsos import verify as V  # caller puts verifiers/ on sys.path
    h = V.heuristic_costs(N, R, B, C, brot)
    A = N + R * B
    sel = math.ceil(math.log2(A))
    J = min(N - 1, (V.QUBIT_CAP - sel - (sel - 1)) // brot)
    K = math.ceil((N - 1) / J)
    T = 2 * K * (A - 2) + h['toffoli']
    Q = h['persistent_qubits'] + J * brot + max(h['temporary_qubits'], sel - 1)
    return dict(R=R, B=B, C=C, brot=brot, J=J, K=K, A=A, T=T, Q=Q, inner_T=h['inner_state_prep_toffoli'],
                temp=h['temporary_qubits'], ratio_at_fixed_lambda=round(BASE / (LAM * T * Q), 4))


if __name__ == '__main__':
    sys.path += [f'{sys.argv[1]}/kickmix', f'{sys.argv[1]}/verifiers']
    print('-- brot (R,B,C = 65,60,60)')
    for brot in (9, 10, 11, 12, 13):
        print(model(65, 60, 60, brot))
    print('-- shape (brot 12)')
    for R, B, C in ((65, 45, 60), (65, 30, 60), (50, 60, 60), (65, 60, 40), (65, 60, 30), (50, 45, 45)):
        print(model(R, B, C, 12))
