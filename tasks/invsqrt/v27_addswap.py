"""Add-one and swap-one feature LPs on the critical x-set (ours). Usage: python tasks/invsqrt/v27_addswap.py"""
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
S = 1e6


def lpc(F):
    k = F.shape[1]
    Fa = F * S
    A = np.vstack([np.hstack([Fa, np.ones((len(F), 1))]), np.hstack([-Fa, np.ones((len(F), 1))])])
    r = linprog(np.r_[np.zeros(k), -1.0], A_ub=A, b_ub=np.r_[tc - ec, tc + ec],
                bounds=[(-2e5, 2e5)] * k + [(None, None)], method='highs')
    return -r.fun


def add_one(j):
    out = []
    for comp in (0, 1):
        g = G[j] if not comp else 1 - G[j]
        out.append((lpc(np.hstack([Wc, g[:, None]])), j, comp))
    return out


def swap_one(args):
    j, comp = args
    g = G[j] if not comp else 1 - G[j]
    best = (-1e30, -1)
    for i in range(33):
        F = Wc.copy()
        F[:, i] = g
        best = max(best, (lpc(F), i))
    return best + (j, comp)


if __name__ == '__main__':
    base = lpc(Wc)
    print('base LP on critical set', base, flush=True)
    with ProcessPoolExecutor(32) as ex:
        res = [r for part in ex.map(add_one, range(len(G)), chunksize=8) for r in part]
    res.sort(reverse=True)
    print('top add-one', [(round(m), j, c) for m, j, c in res[:10]], flush=True)
    top = [(j, c) for m, j, c in res[:200] if m > base * 1.001]
    with ProcessPoolExecutor(32) as ex:
        sw = list(ex.map(swap_one, top))
    sw.sort(reverse=True)
    print('top swap', [(round(m), i, j, c) for m, i, j, c in sw[:15]], flush=True)
    np.save(L.V / 'swap_res.npy', np.array([(m, i, j, c) for m, i, j, c in sw]))
