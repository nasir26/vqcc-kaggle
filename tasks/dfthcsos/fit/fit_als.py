"""Block-exact weight updates + L-BFGS vector steps for a DF-THC two-body fit.

For rank rho with vectors u_b, its squares X_c = sum_b w_bc u_b u_b^T live in S = span{vec(u_b u_b^T)} (B dims).
With E = G - sum_(rho' != rho) sum_c x x^T and an orthonormal basis Qb of S (P^T = Qb Rm, P rows vec(u u^T)):

    min_w || E - sum_c x_c x_c^T ||  =  || E_perp ||  +  min_(Z psd, rank <= C) || Qb^T E Qb - Z ||

so Z = top-C positive eigen part of Qb^T E Qb (exact), x_c = Qb sqrt(lam_c) v_c, w_c = Rm^-1 sqrt(lam_c) v_c.
Sweeps over rho give the optimal weights for the current vectors; then a few L-BFGS steps move all (U, w) jointly.

Usage: python tasks/dfthcsos/fit/fit_als.py --init NPZ --R 8 --C 40 --out OUT.npz [--rounds 30] [--lbfgs 100]
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fit_shape import REPO, init_params, target_matrix  # noqa: E402

import jax  # noqa: E402

jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp  # noqa: E402
from scipy.optimize import minimize  # noqa: E402


def squares(U, w):
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    R, B, N = u.shape
    P = np.einsum('rbp,rbq->rbpq', u, u).reshape(R, B, N * N)
    return P, np.einsum('rbk,rbc->rck', P, w)  # P (R,B,N^2), X (R,C,N^2)


def e2(Gm, G2, X):
    Xf = X.reshape(-1, X.shape[-1])
    g = Xf @ Xf.T
    return np.sqrt(max(G2 - 2 * np.sum((Xf @ Gm) * Xf) + np.sum(g * g), 0)) * 1e3


def sweep(Gm, U, w):
    R, B, _ = U.shape
    C = w.shape[2]
    P, X = squares(U, w)
    for r in range(R):
        Qb, Rm = np.linalg.qr(P[r].T)  # (N^2, B), (B, B)
        others = np.concatenate([X[:r], X[r + 1:]]).reshape(-1, X.shape[-1])  # (K', N^2)
        GQ = Gm @ Qb  # (N^2, B)
        M = Qb.T @ GQ - (Qb.T @ others.T) @ (others @ Qb)
        M = 0.5 * (M + M.T)
        lam, V = np.linalg.eigh(M)
        idx = np.argsort(-lam)[:C]
        lam = np.clip(lam[idx], 0, None)
        Y = V[:, idx] * np.sqrt(lam)  # (B, C) coordinates in Qb
        w[r] = np.linalg.solve(Rm, Y)
        X[r] = (Qb @ Y).T
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--init', required=True)
    ap.add_argument('--R', type=int, required=True)
    ap.add_argument('--C', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--rounds', type=int, default=30)
    ap.add_argument('--lbfgs', type=int, default=100)
    a = ap.parse_args()
    Gm, N = target_matrix()
    G2 = float(np.sum(Gm * Gm))
    U, w = init_params(a.init, a.R, a.C, 0)
    U = np.array(U, np.float64)
    w = np.array(w, np.float64)
    R, B, _ = U.shape
    C = w.shape[2]
    G = jnp.asarray(Gm)
    nU = U.size
    t0 = time.time()
    print(f'shape R {R} B {B} C {C}; init error_2 {e2(Gm, G2, squares(U, w)[1]):.4f} mHa', flush=True)

    def loss(p):
        Uu = p[:nU].reshape(R, B, N)
        ww = p[nU:].reshape(R, B, C)
        u = Uu / jnp.linalg.norm(Uu, axis=2, keepdims=True)
        Xf = jnp.einsum('rbp,rbq,rbc->rcpq', u, u, ww).reshape(R * C, N * N)
        gram = Xf @ Xf.T
        return (G2 - 2 * jnp.sum((Xf @ G) * Xf) + jnp.sum(gram * gram)) * 1e6

    vg = jax.jit(jax.value_and_grad(loss))
    best = None
    for rd in range(a.rounds):
        w = sweep(Gm, U, w)
        ew = e2(Gm, G2, squares(U, w)[1])
        p0 = np.concatenate([U.ravel(), w.ravel()])
        res = minimize(lambda p: tuple(np.asarray(x) for x in vg(jnp.asarray(p))), p0, jac=True, method='L-BFGS-B',
                       options={'maxiter': a.lbfgs, 'maxcor': 30, 'ftol': 0, 'gtol': 0})
        U = res.x[:nU].reshape(R, B, N)
        w = res.x[nU:].reshape(R, B, C)
        el = e2(Gm, G2, squares(U, w)[1])
        print(f'round {rd}: after exact w {ew:.4f} mHa, after {a.lbfgs} L-BFGS {el:.4f} mHa ({time.time() - t0:.0f}s)',
              flush=True)
        if best is None or el < best:
            best = el
            np.savez(a.out, U=U, W=w, error_2=el)
    print(f'best error_2 {best:.4f} mHa', flush=True)


if __name__ == '__main__':
    main()
