"""At given cuts, test whether target functions of x lie in the GF(2) span of the qubit values (+1)."""
import sys; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
def gf2_in_span(A, t):
    # A: (k, n) rows = vectors; t: (n,) ; returns True if t in rowspan(A)
    M = np.concatenate([A, t[None]], 0).astype(np.uint8)
    r0 = gf2_rank(A); r1 = gf2_rank(M)
    return r1 == r0
def gf2_rank(A):
    A = A.copy().astype(np.uint8); r = 0; rows, cols = A.shape
    for c in range(cols):
        piv = np.flatnonzero(A[r:, c]) if r < rows else []
        if len(piv) == 0: continue
        p = r + piv[0]; A[[r, p]] = A[[p, r]]
        nz = np.flatnonzero(A[:, c]); nz = nz[nz != r]
        A[nz] ^= A[r]
        r += 1
        if r == rows: break
    return r
if __name__ != '__main__': raise SystemExit
path = sys.argv[1]; cuts = [int(v) for v in sys.argv[2].split(',')]
c, hdr, body = load(path)
rng = np.random.default_rng(7)
xs = np.concatenate([rng.integers(1, X_MAX + 1, 1500), np.arange(1, 501)]).astype(np.int64)
sp = 21 - np.floor(np.log2(xs)).astype(np.int64); M = xs << sp
targets = {f'M{i}': (M >> i) & 1 for i in range(14, 21)}
targets['par'] = sp & 1
for k in range(1, 5): targets[f'sbit{k}'] = (sp >> k) & 1
for L in cuts:
    sim, bits = run(hdr, body, xs.astype(np.uint64), c.num_qubits, upto=L)
    A = np.concatenate([bits.astype(np.uint8), np.ones((1, len(xs)), np.uint8)], 0)
    res = {k: gf2_in_span(A, v.astype(np.uint8)) for k, v in targets.items()}
    print(L, 'rank', gf2_rank(A), ' '.join(f'{k}:{int(v)}' for k, v in res.items()))
