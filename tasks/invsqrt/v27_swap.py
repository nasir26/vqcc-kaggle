"""True swap-one LPs (ours): phase = theta0 - a_i W_i + b g + sum_{k!=i} d_k W_k, with b = a_i + d (variant A) or
b = d (variant B, removal), g any candidate feature or its complement. Critical x-set first.
Usage: python tasks/invsqrt/v27_swap.py"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v27_lp_core as L  # noqa: E402

Z = np.load(L.V / 'cands.npz')
xc = Z['xc']
G = Z['vecs'].astype(np.float64)
Wc = L.W[xc]
ec = L.e0[xc]
tc = L.tol[xc]
ang = np.array(json.loads((L.V / 'efd_sites64.json').read_text())['angles64'], dtype=np.float64)
S = 1e6


def lpc(F, e):
    k = F.shape[1]
    Fa = F * S
    A = np.vstack([np.hstack([Fa, np.ones((len(F), 1))]), np.hstack([-Fa, np.ones((len(F), 1))])])
    r = linprog(np.r_[np.zeros(k), -1.0], A_ub=A, b_ub=np.r_[tc - e, tc + e],
                bounds=[(-2e5, 2e5)] * (k - 1) + [(-2e6, 2e6)] + [(None, None)], method='highs')
    return -r.fun if r.status == 0 else -1e30


def job(j):
    best = (-1e30, -1, -1, -1, j)
    for comp in (0, 1):
        g = G[j] if not comp else 1 - G[j]
        for i in range(33):
            Wi = Wc[:, i]
            base_e = ec - ang[i] * Wi
            keep = np.delete(Wc, i, axis=1)
            for var in (0, 1):
                if var == 1 and ang[i] > 5e11:
                    continue
                e = base_e + (ang[i] * g if var == 0 else 0)
                # quick reject: any row already beyond tol by more than the LP can move
                m = lpc(np.hstack([keep, g[:, None]]), e)
                best = max(best, (m, i, comp, var, j))
    return best


if __name__ == '__main__':
    with ProcessPoolExecutor(32) as ex:
        res = list(ex.map(job, range(len(G)), chunksize=4))
    res.sort(reverse=True)
    print('top swaps (margin, site, comp, variant, cand)', [(round(r[0]),) + r[1:] for r in res[:15]])
    np.save(L.V / 'swap_true.npy', np.array(res))
