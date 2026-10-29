"""Feasibility of fewer coefficient copies C at fixed angle words (fixed lookup circuits): minimum error_2.

The copies only carry weights; the ANGLE circuits load the N + R*B unit vectors, so dropping copies and refitting
the weights keeps every lookup circuit byte for byte. With the decoded vectors u fixed, X_(rho c) = U_rho^T diag(w)
U_rho is linear in the weights, and the verifier's two-body error is
    eps^2 = ||T||^2 - 2 sum_(rho c) w^T K_rho w + || Wbd^T A Wbd ||_F^2,
    T = tei + (S (x) I + I (x) S)/2 (pair-flattened), K_rho = M_rho^T T M_rho, A = M^T M = (u_b . u_b')^2,
where M_rho has columns vec(u_b u_b^T). This script checks that formula against the official evaluate_dfthc_vectors
on the starting factor, then greedily removes copies (smallest ||X|| first, one per group per round), refitting all
weights by L-BFGS on eps^2 after each round, and prints the minimum eps_2 reached at each C. lambda_eff, error_1 and
the gap floor are NOT optimized here (feasibility screen only).

usage: python tasks/dfthcsos/prune_copies.py DATA_DIR SUBMISSION_NPZ [--targets 56,52,48,44,40]
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('npz')
    ap.add_argument('--targets', default='56,52,48,44,40')
    ap.add_argument('--iters', type=int, default=400)
    a = ap.parse_args()
    sys.path += [f'{a.data}/kickmix', f'{a.data}/verifiers']
    from scipy.optimize import minimize
    from dfthcsos import verify as V
    from dfthcsos.scoreinfra import dfthc_math as M

    t0 = time.time()
    z = np.load(a.npz)
    inputs = V.load_inputs(a.npz)
    w0 = np.asarray(inputs.w, np.float64)                      # (R, B, C)
    R, B, C = w0.shape
    N = 76
    brot = int(z['brot'])
    words = np.asarray(z['angle_words'])
    vec = M.reconstruct_u_vectors(words / (1 << (brot - 1)), np.asarray(z['tree_edges']))
    vec /= np.linalg.norm(vec, axis=1, keepdims=True)
    U = vec[N:].reshape(R, B, N)
    ref = inputs.ref
    tei = np.asarray(ref['tei'], np.float64)
    S = np.asarray(inputs.S, np.float64)
    Tt = tei.copy()
    d = np.arange(N)
    Tt[:, :, d, d] += 0.5 * S[:, :, None]
    Tt[d, d, :, :] += 0.5 * S[None, :, :]
    Tm = Tt.reshape(N * N, N * N)
    nT2 = float(np.sum(Tm * Tm))
    Mcols = np.einsum('rbp,rbq->rbpq', U, U).reshape(R, B, N * N)   # vec(u u^T)
    K = np.stack([Mcols[r] @ (Tm @ Mcols[r].T) for r in range(R)])  # (R, B, B)
    Mall = Mcols.reshape(R * B, N * N)
    A = (Mall @ Mall.T)                                            # (RB, RB)
    del Tm, Tt, tei
    print(f'precompute {time.time() - t0:.0f} s', flush=True)

    def eps2_grad(wflat, mask):
        """eps^2 and its exact gradient; w (R, B, C), masked copies held at zero."""
        w = wflat.reshape(R, B, C) * mask[:, None, :]
        lin = np.einsum('rbc,rbd,rdc->', w, K, w)
        Wbd = np.zeros((R * B, R * C))
        for r in range(R):
            Wbd[r * B:(r + 1) * B, r * C:(r + 1) * C] = w[r]
        AW = A @ Wbd
        G = Wbd.T @ AW
        f = nT2 - 2 * lin + np.sum(G * G)
        gq = 4 * AW @ G                                            # d/dWbd of ||G||^2
        g = np.empty_like(w)
        for r in range(R):
            g[r] = gq[r * B:(r + 1) * B, r * C:(r + 1) * C] - 4 * K[r] @ w[r]
        g *= mask[:, None, :]
        return f, g.ravel()

    mask = np.ones((R, C))
    e_check = float(np.sqrt(max(eps2_grad(w0.ravel(), mask)[0], 0)))
    off = V.evaluate_words(inputs, words, np.asarray(z['tree_edges']), brot)
    print(f'start: formula eps_2 {1e3 * e_check:.4f} mHa, official error_2 {1e3 * off["error_2"]:.4f} mHa, '
          f'lambda_eff {off["lambda_eff"]:.4f}', flush=True)

    def refit(w, mask):
        r = minimize(eps2_grad, w.ravel(), args=(mask,), jac=True, method='L-BFGS-B',
                     options=dict(maxiter=a.iters, maxcor=30, ftol=1e-16, gtol=1e-12))
        return r.x.reshape(R, B, C) * mask[:, None, :], float(np.sqrt(max(r.fun, 0)))

    w = w0.copy()
    w, e = refit(w, mask)
    print(f'C={C}: refit (min eps_2) {1e3 * e:.4f} mHa  [{time.time() - t0:.0f} s]', flush=True)
    for target in map(int, a.targets.split(',')):
        while mask.sum(1).max() > target:
            wn = np.asarray(w)
            for r in range(R):
                live = np.where(mask[r] > 0)[0]
                if len(live) <= target:
                    continue
                norms = [float(np.sqrt(np.einsum('b,bd,d->', wn[r, :, c], A[r * B:(r + 1) * B, r * B:(r + 1) * B], wn[r, :, c])))
                         for c in live]
                mask[r, live[int(np.argmin(norms))]] = 0
            w, e = refit(w, mask)
        print(f'C={target}: min eps_2 {1e3 * e:.4f} mHa  [{time.time() - t0:.0f} s]', flush=True)


if __name__ == '__main__':
    main()
