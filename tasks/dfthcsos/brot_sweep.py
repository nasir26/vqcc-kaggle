"""Rounding-aware angle encoding of a factorization at several brot, scored by the official metrics.

Pipeline (the starter kit's task2 encode.py, rebuilt on the competition verifier's own functions):
two-body rows = tree angles of the float U rounded to brot bits; X from the *decoded* two-body
vectors; one-body rows = eigenvectors of h1_prime(X) on the same tree and rounding. Metrics via
dfthcsos.verify.evaluate_words; the score column uses the T x Q model of tasks/dfthcsos/whatif.py
(max J under the cap) and is an ESTIMATE until circuits are built and verified.

Usage (WSL): python tasks/dfthcsos/brot_sweep.py data/comp FACTORIZATION.npz [--brots 9,10,11,12] [--tree log_depth|path]
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]


def encode(V, M, inputs, U, edges, brot: int, rounding: str = 'nearest'):
    import numpy as np
    sys.path.insert(0, str(REPO / 'data/starter/starter_kit/starter/task2_angles'))
    from trees import tree_angles

    def to_words(theta_over_pi):
        scaled = np.mod(theta_over_pi, 2.0) * (1 << (brot - 1))
        scaled = scaled + 0.5 if rounding == 'nearest' else scaled
        return np.floor(scaled).astype(np.int64) % (1 << brot)

    R, B, N = U.shape
    two = to_words(tree_angles(U.reshape(-1, N), edges))
    vec = M.reconstruct_u_vectors(two / (1 << (brot - 1)), edges)
    vec /= np.linalg.norm(vec, axis=1, keepdims=True)
    X = M.reconstruct_x(vec.reshape(R, B, N), inputs.w)
    X = np.tril(X) + np.swapaxes(np.tril(X, k=-1), -1, -2)
    ref = inputs.ref
    h1_thc = np.asarray(ref['oei'], np.float64) - 0.5 * np.einsum('prrq->pq', np.asarray(ref['tei'], np.float64))
    h1p = M.build_h1_prime(h1_thc, inputs.S, inputs.beta_1, ref['electrons'], inputs.W, X)
    _, eig = np.linalg.eigh(h1p)
    one = to_words(tree_angles(eig.T, edges))
    return np.vstack([one, two])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('factorization')
    ap.add_argument('--brots', default='9,10,11,12,13')
    ap.add_argument('--tree', default='log_depth', choices=('log_depth', 'path'))
    ap.add_argument('--rounding', default='nearest', choices=('nearest', 'floor'))
    ap.add_argument('--json', default=None)
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers', str(REPO / 'tasks/dfthcsos'),
                 str(REPO / 'data/starter/starter_kit/starter/task2_angles')]
    import numpy as np
    from dfthcsos import verify as V
    from dfthcsos.scoreinfra import dfthc_math as M
    import trees
    import whatif

    inputs = V.load_inputs(args.factorization)
    with np.load(args.factorization, allow_pickle=False) as z:
        U = np.array(z['U'], dtype=np.float64)
    R, B, N = U.shape
    C = inputs.w.shape[2]
    edges = (trees.log_depth_tree_edges if args.tree == 'log_depth' else trees.path_tree_edges)(N)
    rows = []
    for brot in map(int, args.brots.split(',')):
        words = encode(V, M, inputs, U, edges, brot, args.rounding)
        m = V.evaluate_words(inputs, words, edges, brot)
        m = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()}
        ok = bool(V.passes_accuracy(m))
        model = whatif.model(R, B, C, brot)
        est = m['lambda_eff'] * model['T'] * model['Q'] if ok else math.inf
        row = {'brot': brot, 'tree': args.tree, **m, 'passes': ok, 'J': model['J'], 'T': model['T'],
               'Q': model['Q'], 'score_estimate': est, 'ratio_estimate': whatif.BASE / est}
        rows.append(row)
        print(json.dumps(row, default=float), flush=True)
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rows, indent=2, default=float))


if __name__ == '__main__':
    main()
