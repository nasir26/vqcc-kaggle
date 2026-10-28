"""Gradient-guided (AdaRound-style) rounding of the two-body Givens angles for dfthcsos.

error_2^2 = ||G0 + dG||^2 = ||G0||^2 + 2<G0, dG> + ||dG||^2. Nearest rounding leaves the first-order
term to chance; with a large factorization residual G0 (~16 mHa) it can be made negative. Per angle,
choose floor or ceil of the continuous word value cw to minimise  g * delta + kappa * delta^2,
where g = d(error_2^2)/d(word) at the continuous factorization and kappa = lam * median|g|
(lam -> infinity recovers nearest rounding). Each lam is scored with the official evaluate_words
(one-body rows re-derived from the rounded two-body vectors, as the starter kit does).

Gradient: G = sum_rc X_rc (x) X_rc - tei - shifts (as in dfthc_math.evaluate_dfthc_vectors);
dE/dX_rc = 4 G X_rc (G as an N^2 x N^2 matrix); dE/du_{rho b} = sum_c w_{rho b c} 2 (dE/dX_{rho c}) u;
dE/dword via central differences of the official Givens decoder.

Usage (WSL): python tasks/dfthcsos/round_grad.py data/comp FACTORIZATION.npz --brot 11 [--lams 0,0.5,1,2,4]
               [--save-best data/candidates/dfthcsos_words_grad_b11.npz]
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('factorization')
    ap.add_argument('--brot', type=int, default=11)
    ap.add_argument('--lams', default='0,0.25,0.5,1,2,4,1e9')
    ap.add_argument('--save-best', default=None)
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers', str(REPO / 'tasks/dfthcsos'),
                 str(REPO / 'data/starter/starter_kit/starter/task2_angles')]
    import numpy as np
    from dfthcsos import verify as V
    from dfthcsos.scoreinfra import dfthc_math as M
    import trees
    import whatif
    from round_opt import decode, nearest

    t0 = time.monotonic()
    inputs = V.load_inputs(args.factorization)
    with np.load(args.factorization, allow_pickle=False) as z:
        U = np.array(z['U'], dtype=np.float64)
    R, B, N = U.shape
    C = inputs.w.shape[2]
    w = np.asarray(inputs.w, np.float64)
    edges = trees.log_depth_tree_edges(N)
    brot = args.brot
    scale = 1 << (brot - 1)
    ref = inputs.ref
    tei = np.asarray(ref['tei'], np.float64)
    S = np.asarray(inputs.S, np.float64)
    h1_thc = np.asarray(ref['oei'], np.float64) - 0.5 * np.einsum('prrq->pq', tei)

    u = U.reshape(-1, N) / np.linalg.norm(U.reshape(-1, N), axis=1, keepdims=True)
    theta = trees.tree_angles(u, edges)  # theta/pi in [0, 2), continuous
    u = decode(M, theta * scale, edges, brot)  # exactly the continuous vectors the tree encodes

    # Residual tensor G at the continuous factorization, as an N^2 x N^2 matrix.
    X = M.reconstruct_x(u.reshape(R, B, N), w)  # (R, C, N, N), symmetric
    G = M.reconstruct_h2(X) - tei
    d = np.arange(N)
    G[:, :, d, d] -= 0.5 * S[:, :, None]
    G[d, d, :, :] -= 0.5 * S[None, :, :]
    e0 = float(np.linalg.norm(G))
    Gm = G.reshape(N * N, N * N)
    del G
    Xm = X.reshape(R * C, N * N).T  # (N^2, RC)
    D = (4.0 * (Gm @ Xm)).T.reshape(R, C, N, N)  # dE/dX_rc
    del Gm, Xm
    grad_u = 2.0 * np.einsum('rbc,rcpq,rbq->rbp', w, D, u.reshape(R, B, N), optimize=True).reshape(-1, N)
    del D
    print(json.dumps({'stage': 'gradient', 'error_2_continuous_mHa': 1e3 * e0,
                      'seconds': round(time.monotonic() - t0)}), flush=True)

    # d(error_2^2)/d(word) by central differences of the decoder (word units).
    cw = theta * scale
    g = np.zeros_like(cw)
    h = 1e-3
    for t in range(cw.shape[1]):
        plus, minus = cw.copy(), cw.copy()
        plus[:, t] += h
        minus[:, t] -= h
        du = (decode(M, plus, edges, brot) - decode(M, minus, edges, brot)) / (2 * h)
        g[:, t] = (grad_u * du).sum(axis=1)
    floor = np.floor(cw)
    d_f = floor - cw  # in (-1, 0]
    med = float(np.median(np.abs(g)))

    def one_body(two_words):
        vec = decode(M, two_words, edges, brot)
        Xr = M.reconstruct_x(vec.reshape(R, B, N), w)
        Xr = np.tril(Xr) + np.swapaxes(np.tril(Xr, k=-1), -1, -2)
        _, eig = np.linalg.eigh(M.build_h1_prime(h1_thc, inputs.S, inputs.beta_1, ref['electrons'], inputs.W, Xr))
        return nearest(trees.tree_angles(eig.T, edges), brot)

    model = whatif.model(R, B, C, brot)
    best = None
    for lam in map(float, args.lams.split(',')):
        kappa = lam * med
        cost_f = g * d_f + kappa * d_f**2
        cost_c = g * (d_f + 1) + kappa * (d_f + 1) ** 2
        two = (floor + (cost_c < cost_f)).astype(np.int64) % (1 << brot)
        words = np.vstack([one_body(two), two])
        m = V.evaluate_words(inputs, words, edges, brot)
        m = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()}
        ok = bool(V.passes_accuracy(m))
        est = m['lambda_eff'] * model['T'] * model['Q'] if ok else math.inf
        row = {'brot': brot, 'lam': lam, 'frac_non_nearest': float(((cost_c < cost_f) != (d_f < -0.5)).mean()),
               'error_1_mHa': 1e3 * m['error_1'], 'error_2_mHa': 1e3 * m['error_2'], 'lambda_eff': m['lambda_eff'],
               'E_gap': m['E_gap'], 'passes': ok, 'J': model['J'], 'ratio_estimate': whatif.BASE / est,
               'seconds': round(time.monotonic() - t0)}
        print(json.dumps(row), flush=True)
        if ok and (best is None or est < best[0]):
            best = (est, words, lam)
    if best and args.save_best:
        path = pathlib.Path(args.save_best)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, angle_words=best[1], tree_edges=edges, brot=brot, lam=best[2])
        print(json.dumps({'saved': str(path), 'lam': best[2], 'score_estimate': best[0]}))


if __name__ == '__main__':
    main()
