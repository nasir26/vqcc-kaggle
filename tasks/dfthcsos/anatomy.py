"""Anatomy of the official dfthcsos baseline: Lambda split, precision headroom, (brot, J) cost model.

1. Metrics of the shipped 12-bit angle words (official evaluate_words), with Lambda split into its
   one-body part sum_j |lambda_j| and two-body part 1/4 sum (|w_B| + sum_b |w_b|)^2.
2. Precision sweep: the 12-bit words re-rounded to brot < 12 bits (an upper bound on the error a
   proper re-quantization from the float factorization would give).
3. Cost model over (brot, J) for the baseline's ordinary-QROM construction: each ANGLE_k circuit is
   a unary iteration over A = N + R*B addresses (A - 2 Toffolis, ceil(log2 A) - 1 ancillas), run
   forward and reverse, K = ceil((N-1)/J) circuits; heuristic part from the official
   heuristic_costs(). These T/Q are MODEL ESTIMATES (ANGLES Toffolis are not simulated here).

Usage (WSL, repo root): python tasks/dfthcsos/anatomy.py data/comp [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('--json', default=None)
    ap.add_argument('--brots', default='8,9,10,11,12')
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers']
    import numpy as np
    from dfthcsos import verify as V
    from dfthcsos.scoreinfra import dfthc_math as M

    npz_path = f'{args.data}/sample_submission/dfthcsos/submission.npz'
    inputs = V.load_inputs(npz_path)
    with np.load(npz_path, allow_pickle=False) as z:
        words12 = np.array(z['angle_words'], dtype=np.int64)
        tree = np.array(z['tree_edges'])
    R, B, C = inputs.w.shape
    N = inputs.num_orbitals
    A = N + R * B
    lam_h2 = M.lambda_h2(inputs.w, inputs.W)

    def metrics_at(brot: int) -> dict:
        words = words12 if brot == 12 else ((words12 + (1 << (11 - brot))) >> (12 - brot)) % (1 << brot)
        m = V.evaluate_words(inputs, words, tree, brot)
        m = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()}
        m['Lambda_h1'] = m['Lambda'] - lam_h2
        m['Lambda_h2'] = lam_h2
        m['passes_accuracy'] = bool(V.passes_accuracy(m))
        return m

    brots = [int(b) for b in args.brots.split(',')]
    sweep = {b: metrics_at(b) for b in brots}

    sel = math.ceil(math.log2(A))
    model = []
    for brot in brots:
        h = V.heuristic_costs(N, R, B, C, brot)
        lam_eff = sweep[brot]['lambda_eff']
        for J in range(1, N):
            angles_q = sel + J * brot + (sel - 1)
            if angles_q > V.QUBIT_CAP:
                break
            K = math.ceil((N - 1) / J)
            t_ang = 2 * K * (A - 2)
            T = t_ang + h['toffoli']
            Q = h['persistent_qubits'] + J * brot + max(h['temporary_qubits'], sel - 1)
            model.append({'brot': brot, 'J': J, 'K': K, 'angles_qubits': angles_q, 'T_angles': t_ang,
                          'T_heur': h['toffoli'], 'T': T, 'Q': Q, 'lambda_eff': lam_eff,
                          'accuracy_ok': sweep[brot]['passes_accuracy'],
                          'score_est': lam_eff * T * Q})
    best = sorted((r for r in model if r['accuracy_ok']), key=lambda r: r['score_est'])[:8]

    out = {'shape': {'R': R, 'B': B, 'C': C, 'N': N, 'A': A, 'selection_qubits': sel},
           'precision_sweep': sweep,
           'heuristic_at_12': V.heuristic_costs(N, R, B, C, 12),
           'model_best_feasible': best,
           'model_all': model}
    print(json.dumps({k: out[k] for k in ('shape', 'precision_sweep', 'heuristic_at_12', 'model_best_feasible')},
                     indent=2, default=float))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(out, f, indent=2, default=float)


if __name__ == '__main__':
    main()
