"""Feasibility fit of a DF-THC two-body table at a new shape (R, B, C): how low can error_2 go?

error_2 = || sum_(rho c) X_rc (x) X_rc - G ||_F with G = tei + (S (x) I + I (x) S) / 2 (the verifier's definition),
X_rc = sum_b w[rho, b, c] u_rb u_rb^T, u rows normalised. Viewing G as a 5776 x 5776 matrix and x_k = vec(X_k):

    error_2^2 = ||G||^2 - 2 sum_k x_k^T G x_k + sum_(k, l) (x_k^T x_l)^2

so one evaluation is one (5776 x 5776) @ (5776 x RC) product. L-BFGS (scipy) on (U, w) with JAX gradients, float64.
Optional penalty mu * lambda_h2 surrogate (1/4 sum_rc (sum_b |w|)^2 smoothed) keeps the LCU norm in check.

This only tests whether a shape can reach the error gate; the offsets W, error_1, E_gap and 8-bit rounding come later.

Usage: python tasks/dfthcsos/fit/fit_shape.py --init NPZ --R 7 --C 50 --out OUT.npz [--iters 3000] [--mu 0]
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path += [str(REPO / 'data/comp/kickmix'), str(REPO / 'data/comp/verifiers'), str(pathlib.Path(__file__).parent)]

import jax  # noqa: E402

jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp  # noqa: E402
from scipy.optimize import minimize  # noqa: E402


def target_matrix():
    from dfthcsos import verify as V
    inputs = V.load_inputs(REPO / 'data/candidates/portfolio_v4/dfthcsos/submission.npz')
    tei = np.asarray(inputs.ref['tei'], np.float64)
    S = np.asarray(inputs.S, np.float64)
    N = tei.shape[0]
    G = tei.copy()
    d = np.arange(N)
    G[:, :, d, d] += 0.5 * S[:, :, None]
    G[d, d, :, :] += 0.5 * S[None, :, :]
    return G.reshape(N * N, N * N), N


def init_params(path, R, C, seed):
    z = np.load(path)
    U0 = np.asarray(z['U'], np.float64)  # (R0, B, N)
    w0 = np.asarray(z['W'], np.float64)  # (R0, B, C0) lowercase weights
    rng = np.random.default_rng(seed)
    R0, B, N = U0.shape
    C0 = w0.shape[2]
    # keep the R ranks with the largest weight mass
    mass = np.abs(w0).sum((1, 2))
    keep = np.sort(np.argsort(-mass)[:R]) if R <= R0 else np.arange(R0)
    U = U0[keep]
    w = w0[keep]
    if R > R0:
        extra = R - R0
        U = np.concatenate([U, rng.standard_normal((extra, B, N))])
        w = np.concatenate([w, 1e-3 * rng.standard_normal((extra, B, C0))])
    if C <= C0:
        w = w[:, :, :C]
    else:
        w = np.concatenate([w, 1e-3 * rng.standard_normal((w.shape[0], B, C - C0))], axis=2)
    return U, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--init', required=True)
    ap.add_argument('--R', type=int, required=True)
    ap.add_argument('--C', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--iters', type=int, default=3000)
    ap.add_argument('--mu', type=float, default=0.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--round-brot', type=int, default=0, help='round the init vectors to this many bits on the tree and freeze them')
    ap.add_argument('--edges', default=str(REPO / 'data/src_pull/maoxin_v22_out/x/dfthcsos/submission.npz'))
    a = ap.parse_args()

    Gm, N = target_matrix()
    G = jnp.asarray(Gm)
    G2 = float(np.sum(Gm * Gm))
    U, w = init_params(a.init, a.R, a.C, a.seed)
    R, B, _ = U.shape
    frozen = None
    if a.round_brot:
        import quantize as Qz
        edges = np.load(a.edges)['tree_edges']
        Un = (U / np.linalg.norm(U, axis=2, keepdims=True)).reshape(-1, N)
        th = Qz.encode(Un, edges)
        U = Qz.decode(Qz.to_words(th, a.round_brot), edges, a.round_brot).reshape(R, B, N)
        frozen = jnp.asarray(U)
        print(f'vectors rounded to {a.round_brot} bits and frozen', flush=True)
    C = w.shape[2]
    nU = U.size
    print(f'shape R {R} B {B} C {C}, params {U.size + w.size}', flush=True)

    def unpack(p):
        if frozen is not None:
            return frozen, p[nU:].reshape(R, B, C)
        return p[:nU].reshape(R, B, N), p[nU:].reshape(R, B, C)

    def xs(p):
        Uu, ww = unpack(p)
        u = Uu / jnp.linalg.norm(Uu, axis=2, keepdims=True)
        X = jnp.einsum('rbp,rbq,rbc->rcpq', u, u, ww)
        return X.reshape(R * C, N * N), ww

    def loss(p):
        Xf, ww = xs(p)
        GX = Xf @ G  # (K, N^2)
        quad = jnp.sum(GX * Xf)
        gram = Xf @ Xf.T
        e2sq = G2 - 2 * quad + jnp.sum(gram * gram)
        pen = 0.0
        if a.mu:
            l1 = jnp.sum(jnp.sqrt(ww * ww + 1e-12), axis=1)  # (R, C)
            pen = a.mu * 0.25 * jnp.sum(l1 ** 2)
        return e2sq * 1e6 + pen, e2sq

    vg = jax.jit(jax.value_and_grad(lambda p: loss(p)[0]))
    e2f = jax.jit(lambda p: loss(p)[1])
    p0 = np.concatenate([U.ravel(), w.ravel()])
    t0 = time.time()
    print(f'init error_2 {np.sqrt(max(float(e2f(p0)), 0)) * 1e3:.4f} mHa', flush=True)
    it = [0]

    def fun(p):
        v, g = vg(jnp.asarray(p))
        return float(v), np.asarray(g)

    def cb(p):
        it[0] += 1
        if it[0] % 50 == 0:
            e2 = np.sqrt(max(float(e2f(jnp.asarray(p))), 0)) * 1e3
            print(f'  iter {it[0]}: error_2 {e2:.4f} mHa  ({time.time() - t0:.0f}s)', flush=True)
            np.savez(a.out, U=unpack(p)[0], W=unpack(p)[1], error_2=e2)

    res = minimize(fun, p0, jac=True, method='L-BFGS-B', callback=cb,
                   options={'maxiter': a.iters, 'maxcor': 30, 'ftol': 0, 'gtol': 0})
    p = res.x
    e2 = np.sqrt(max(float(e2f(jnp.asarray(p))), 0)) * 1e3
    Uf, wf = unpack(p)
    lam_h2_l1 = 0.25 * np.sum(np.abs(wf).sum(1) ** 2)
    print(f'final error_2 {e2:.4f} mHa after {it[0]} iters, {time.time() - t0:.0f}s; '
          f'1/4 sum (sum_b |w|)^2 = {lam_h2_l1:.2f}; {res.message}', flush=True)
    np.savez(a.out, U=Uf, W=wf, error_2=e2)


if __name__ == '__main__':
    main()
