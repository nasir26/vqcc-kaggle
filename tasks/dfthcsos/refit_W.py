"""Refit the free offsets W (R, C) of a dfthcsos submission at fixed angle words and fixed w.

At fixed words and w, X^(rho c) and error_2 are fixed. W enters h1_prime = A - sum W X (eigenvalues lambda_j and
error_1), Lambda (|W + sum_b w|) and E_SOS (-1/2 sum W^2). Minimise lambda_eff subject to error_1 <= cap, using the
verifier's formulas (scoreinfra.dfthc_math), then re-evaluate with the official evaluate_words.

Usage: python tasks/dfthcsos/refit_W.py IN_DIR OUT_DIR [--cap 0.0199]
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment, minimize

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path += [str(REPO / 'data/comp/kickmix'), str(REPO / 'data/comp/verifiers')]
from dfthcsos import verify as V  # noqa: E402
from dfthcsos.scoreinfra import dfthc_math as M  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp', type=pathlib.Path)
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--cap', type=float, default=0.0199)
    a = ap.parse_args()
    npz = a.inp / 'submission.npz'
    inputs = V.load_inputs(npz)
    z = dict(np.load(npz))
    words = np.asarray(z['angle_words'], np.int64)
    edges = z['tree_edges']
    brot = int(z['brot']) if 'brot' in z else 8
    base = V.evaluate_words(inputs, words, edges, brot)
    print('official before:', {k: base[k] for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')})

    ref = inputs.ref
    w = np.asarray(inputs.w, np.float64)
    W0 = np.asarray(inputs.W, np.float64)
    S = np.asarray(inputs.S, np.float64)
    beta_1 = float(inputs.beta_1)
    eta = ref['electrons']
    N = ref['oei'].shape[0]
    u_all = M.reconstruct_u_vectors(words / 2 ** (brot - 1), edges)
    u_all /= np.linalg.norm(u_all, axis=1, keepdims=True)
    V1, ub = M.split_u_vectors(u_all, w)
    X = M.reconstruct_x(ub, w)
    X = np.tril(X) + np.swapaxes(np.tril(X, k=-1), -1, -2)
    tei = np.asarray(ref['tei'], np.float64)
    h1_thc = np.asarray(ref['oei'], np.float64) - 0.5 * np.einsum('prrq->pq', tei)
    A = h1_thc - 0.5 * eta * S + beta_1 * np.eye(N)
    R, C = W0.shape
    Xf = X.reshape(R * C, N, N)
    a_rc = np.abs(w).sum(1).ravel()
    s_rc = w.sum(1).ravel()
    const = ref['ecore'] - eta * beta_1
    E_up = inputs.energy_upper

    def parts(Wv):
        h1p = A - np.tensordot(Wv, Xf, axes=1)
        lam, vec = np.linalg.eigh(h1p)
        ov = np.abs(V1 @ vec)
        qi, ii = linear_sum_assignment(-ov)
        ml = np.empty_like(lam)
        ml[qi] = lam[ii]
        e1 = np.linalg.norm(np.einsum('j,jp,jq->pq', ml, V1, V1) - h1p)
        lam1 = np.abs(lam).sum()
        Lam = lam1 + 0.25 * np.sum((a_rc + np.abs(Wv + s_rc)) ** 2)
        esos = const - (lam1 - lam.sum()) - 0.5 * np.sum(Wv ** 2)
        gap = E_up - esos
        return np.sqrt(gap * (2 * Lam - gap)), e1, Lam, gap

    W0v = W0.ravel()
    f0, e10, L0, g0 = parts(W0v)
    print(f'model before: lambda_eff {f0:.6f} error_1 {e10 * 1e3:.4f} mHa Lambda {L0:.4f} gap {g0:.6f}')
    scale = 1.0
    res = minimize(lambda x: parts(W0v + x * scale)[0], np.zeros_like(W0v), method='SLSQP',
                   constraints=[{'type': 'ineq', 'fun': lambda x: a.cap - parts(W0v + x * scale)[1]},
                                {'type': 'ineq', 'fun': lambda x: parts(W0v + x * scale)[3] - V.E_GAP_FLOOR - 1e-6}],
                   options={'maxiter': 300, 'ftol': 1e-12, 'disp': True})
    W1v = W0v + res.x * scale
    f1, e11, L1, g1 = parts(W1v)
    print(f'model after:  lambda_eff {f1:.6f} error_1 {e11 * 1e3:.4f} mHa Lambda {L1:.4f} gap {g1:.6f} '
          f'({(f0 / f1 - 1) * 100:.4f}% better)')

    a.out.mkdir(parents=True, exist_ok=True)
    for p in a.inp.iterdir():
        if p.name != 'submission.npz':
            shutil.copy2(p, a.out / p.name)
    z['H2_I'] = (W1v.reshape(W0.shape) + w.sum(1)).astype(z['H2_I'].dtype)  # H2_I stores W + sum_b w
    np.savez(a.out / 'submission.npz', **z)
    after = V.evaluate_words(V.load_inputs(a.out / 'submission.npz'), words, edges, brot)
    print('official after:', {k: after[k] for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')})
    print(f"official lambda_eff gain {(base['lambda_eff'] / after['lambda_eff'] - 1) * 100:.4f}%")


if __name__ == '__main__':
    main()
