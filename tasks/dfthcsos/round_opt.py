"""Optimized (non-nearest) angle rounding for dfthcsos, scored with the official metrics.

Nearest rounding of each Givens angle does not minimise the decoded vector's error: rotation errors
compound along the tree. Here every row's brot-bit words are improved by coordinate descent
(+-1 on one angle at a time, all rows vectorised) on ||decode(words) - u||^2, starting from nearest
rounding of u and of -u (both give the same u u^T; the better start is kept). Two-body rows first;
the one-body rows are then the eigenvectors of h1_prime built from the *optimised decoded* two-body
vectors (the starter kit's rounding-aware rule), optimised the same way.

Metrics come from dfthcsos.verify.evaluate_words; score/ratio use tasks/dfthcsos/whatif.py's exact
T x Q model with max J under the cap -- ESTIMATES until circuits are built and verified.

Usage (WSL): python tasks/dfthcsos/round_opt.py data/comp FACTORIZATION.npz --brots 11,12 [--passes 3]
                [--save-words data/candidates/dfthcsos_words_b11.npz]
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]


def decode(M, words, edges, brot):
    import numpy as np
    v = M.reconstruct_u_vectors(words / (1 << (brot - 1)), edges)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def nearest(theta_over_pi, brot):
    import numpy as np
    return np.floor(np.mod(theta_over_pi, 2.0) * (1 << (brot - 1)) + 0.5).astype(np.int64) % (1 << brot)


def optimise_rows(M, tree_angles, targets, edges, brot, passes):
    """Per-row coordinate descent on ||decode - target||^2 over {u, -u} starts."""
    import numpy as np
    mod = 1 << brot
    best_words, best_err = None, None
    for sign in (1.0, -1.0):
        tgt = sign * targets
        words = nearest(tree_angles(tgt, edges), brot)
        err = ((decode(M, words, edges, brot) - tgt) ** 2).sum(axis=1)
        for _ in range(passes):
            changed = 0
            for t in range(words.shape[1]):
                for step in (-1, 1):
                    cand = words.copy()
                    cand[:, t] = (cand[:, t] + step) % mod
                    e = ((decode(M, cand, edges, brot) - tgt) ** 2).sum(axis=1)
                    better = e < err
                    if better.any():
                        words[better, t] = cand[better, t]
                        err[better] = e[better]
                        changed += int(better.sum())
            if not changed:
                break
        if best_words is None:
            best_words, best_err = words, err
        else:
            take = err < best_err
            best_words[take], best_err[take] = words[take], err[take]
    return best_words, best_err


def encode(V, M, inputs, U, edges, brot, passes, optimise=True):
    import numpy as np
    from trees import tree_angles
    R, B, N = U.shape
    tgt2 = U.reshape(-1, N) / np.linalg.norm(U.reshape(-1, N), axis=1, keepdims=True)
    if optimise:
        two, err2 = optimise_rows(M, tree_angles, tgt2, edges, brot, passes)
    else:
        two = nearest(tree_angles(tgt2, edges), brot)
        err2 = ((decode(M, two, edges, brot) - tgt2) ** 2).sum(axis=1)
    vec = decode(M, two, edges, brot)
    X = M.reconstruct_x(vec.reshape(R, B, N), inputs.w)
    X = np.tril(X) + np.swapaxes(np.tril(X, k=-1), -1, -2)
    ref = inputs.ref
    h1_thc = np.asarray(ref['oei'], np.float64) - 0.5 * np.einsum('prrq->pq', np.asarray(ref['tei'], np.float64))
    _, eig = np.linalg.eigh(M.build_h1_prime(h1_thc, inputs.S, inputs.beta_1, ref['electrons'], inputs.W, X))
    tgt1 = eig.T
    if optimise:
        one, err1 = optimise_rows(M, tree_angles, tgt1, edges, brot, passes)
    else:
        one = nearest(tree_angles(tgt1, edges), brot)
        err1 = ((decode(M, one, edges, brot) - tgt1) ** 2).sum(axis=1)
    return np.vstack([one, two]), float(np.sqrt(err2.mean())), float(np.sqrt(err1.mean()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('factorization')
    ap.add_argument('--brots', default='11,12')
    ap.add_argument('--passes', type=int, default=3)
    ap.add_argument('--tree', default='log_depth', choices=('log_depth', 'path'))
    ap.add_argument('--save-words', default=None, help='npz path; {brot} is substituted')
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
    for brot in map(int, args.brots.split(',')):
        for optimise in (False, True):
            t0 = time.monotonic()
            words, rms2, rms1 = encode(V, M, inputs, U, edges, brot, args.passes, optimise)
            m = V.evaluate_words(inputs, words, edges, brot)
            m = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()}
            ok = bool(V.passes_accuracy(m))
            model = whatif.model(R, B, C, brot)
            est = m['lambda_eff'] * model['T'] * model['Q'] if ok else math.inf
            print(json.dumps({'brot': brot, 'optimised': optimise, 'tree': args.tree,
                              'rms_vec_err_two': rms2, 'rms_vec_err_one': rms1,
                              'error_1_mHa': 1e3 * m['error_1'], 'error_2_mHa': 1e3 * m['error_2'],
                              'Lambda': m['Lambda'], 'E_gap': m['E_gap'], 'lambda_eff': m['lambda_eff'],
                              'passes': ok, 'J': model['J'], 'score_estimate': est,
                              'ratio_estimate': whatif.BASE / est, 'seconds': round(time.monotonic() - t0)}),
                  flush=True)
            if optimise and args.save_words:
                path = pathlib.Path(args.save_words.format(brot=brot))
                path.parent.mkdir(parents=True, exist_ok=True)
                np.savez(path, angle_words=words, tree_edges=edges, brot=brot)


if __name__ == '__main__':
    main()
