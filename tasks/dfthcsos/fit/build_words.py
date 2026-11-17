"""[ours] Turn a continuous DF-THC fit (U, w) at any shape into a full dfthcsos table and score it with the official
evaluate_words (no circuits yet).

Steps: two-body rows rounded to brot bits on the template's Givens tree (round_opt coordinate descent); offsets W
(R, C) chosen to minimise lambda_eff = sqrt(E_gap (2 Lambda - E_gap)) subject to E_gap >= floor, with the one-body
rows taken as exact eigenvectors of h1_prime (error_1 = 0 in the model); then the one-body rows are rounded the same
way and the official metrics are computed. Run tasks/dfthcsos/refit_W.py on the output to bring error_1 under the cap.

Usage: python tasks/dfthcsos/fit/build_words.py FIT.npz TEMPLATE_DIR OUT_DIR [--passes 3] [--brot 8]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
from scipy.optimize import minimize

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path += [str(REPO / 'data/comp/kickmix'), str(REPO / 'data/comp/verifiers'), str(REPO / 'tasks/dfthcsos'), str(REPO / 'tasks/dfthcsos/fit')]
from dfthcsos import verify as V  # noqa: E402
from dfthcsos.scoreinfra import dfthc_math as M  # noqa: E402
import round_opt as RO  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fit')
    ap.add_argument('template', type=pathlib.Path)
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--passes', type=int, default=3)
    ap.add_argument('--brot', type=int, default=8)
    ap.add_argument('--gap-margin', type=float, default=2e-5)
    a = ap.parse_args()
    from quantize import encode as _enc

    def tree_angles(Ut, e):
        return _enc(Ut, e) / np.pi

    f = np.load(a.fit)
    U = np.asarray(f['U'], np.float64)
    w = np.asarray(f['W'], np.float64)
    R, B, N = U.shape
    C = w.shape[2]
    t = dict(np.load(a.template / 'submission.npz'))
    edges = t['tree_edges']
    params = dict(U=U.astype(np.float32), W=w.astype(np.float32), H2_I=w.sum(1).astype(np.float32),
                  H1_I=t['H1_I'], Hsym_lower=t['Hsym_lower'])
    inputs = V.load_inputs(params)
    w = np.asarray(inputs.w, np.float64)
    ref = inputs.ref
    brot = a.brot

    tgt2 = U.reshape(-1, N) / np.linalg.norm(U.reshape(-1, N), axis=1, keepdims=True)
    two, err2 = RO.optimise_rows(M, tree_angles, tgt2, edges, brot, a.passes)
    print(f'two-body rows rounded: rms row error {np.sqrt(err2.mean()):.5f}', flush=True)
    vec = RO.decode(M, two, edges, brot)
    X = M.reconstruct_x(vec.reshape(R, B, N), w)
    X = np.tril(X) + np.swapaxes(np.tril(X, k=-1), -1, -2)

    eta = ref['electrons']
    tei = np.asarray(ref['tei'], np.float64)
    h1_thc = np.asarray(ref['oei'], np.float64) - 0.5 * np.einsum('prrq->pq', tei)
    S = np.asarray(inputs.S, np.float64)
    Amat = h1_thc - 0.5 * eta * S + inputs.beta_1 * np.eye(N)
    Xf = X.reshape(R * C, N, N)
    a_rc = np.abs(w).sum(1).ravel()
    s_rc = w.sum(1).ravel()
    const = ref['ecore'] - eta * inputs.beta_1
    E_up = inputs.energy_upper
    floor = V.E_GAP_FLOOR + a.gap_margin

    def parts(Wv):
        lam = np.linalg.eigvalsh(Amat - np.tensordot(Wv, Xf, axes=1))
        lam1 = np.abs(lam).sum()
        Lam = lam1 + 0.25 * np.sum((a_rc + np.abs(Wv + s_rc)) ** 2)
        gap = E_up - (const - (lam1 - lam.sum()) - 0.5 * np.sum(Wv ** 2))
        return Lam, gap

    def leff(Wv):
        Lam, gap = parts(Wv)
        return np.sqrt(max(gap, 1e-12) * (2 * Lam - gap))

    # start: W = -c sign(s), c from bisection so that the gap sits on the floor
    sg = -np.sign(s_rc)
    sg[sg == 0] = 1
    lo, hi = 0.0, 50.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if parts(mid * sg)[1] < floor:
            lo = mid
        else:
            hi = mid
    W0 = hi * sg
    print(f'start W: c {hi:.4f} lambda_eff {leff(W0):.5f} gap {parts(W0)[1]:.6f}', flush=True)
    res = minimize(leff, W0, method='SLSQP', constraints=[{'type': 'ineq', 'fun': lambda x: parts(x)[1] - floor}],
                   options={'maxiter': 400, 'ftol': 1e-12})
    W1 = res.x
    print(f'model W fit: lambda_eff {leff(W1):.5f} Lambda {parts(W1)[0]:.4f} gap {parts(W1)[1]:.6f} ({res.message})',
          flush=True)

    h1p = Amat - np.tensordot(W1, Xf, axes=1)
    _, eig = np.linalg.eigh(h1p)
    one, err1 = RO.optimise_rows(M, tree_angles, eig.T, edges, brot, a.passes)
    words = np.vstack([one, two]).astype(np.int64)

    a.out.mkdir(parents=True, exist_ok=True)
    out = dict(t)
    out.update(U=U.astype(t['U'].dtype), W=w.astype(t['W'].dtype),
               H2_I=(W1.reshape(R, C) + w.sum(1)).astype(t['H2_I'].dtype), angle_words=words, tree_edges=edges)
    np.savez(a.out / 'submission.npz', **out)
    m = V.evaluate_words(V.load_inputs(a.out / 'submission.npz'), words, edges, brot)
    print('official:', {k: (round(1e3 * m[k], 4) if k.startswith('error') else m[k])
                        for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff', 'gap_in_domain')}, flush=True)


if __name__ == '__main__':
    main()
