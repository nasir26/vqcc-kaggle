"""Candidate rotation features for the 44-qubit invsqrt (ours): the value of every wire at every depth-0 point, on a
critical x-set, deduplicated; HMR-independence checked with two simulator seeds. Writes cands.npz.
Usage: python tasks/invsqrt/v27_cands.py"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v27_lp_core as L  # noqa: E402
from kmxsim import km, load  # noqa: E402

V = L.V
c, hdr, body = load(str(V / 'efd.kmx'))
sl = L.tol - np.abs(L.e0)
rng = np.random.default_rng(3)
xc = np.unique(np.r_[np.argsort(sl)[:3072], rng.integers(0, len(sl), 1024)])[:4096]
xs = (xc + 1).astype(np.uint64)
N = len(xs)
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
allq = km.array([km.q(i) for i in range(c.num_qubits)])
sims = []
for seed in (3, 99):
    s = km.Simulator(batch_size=N, debug_print=False, seed=seed)
    s.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
    sims.append(s)
seen = {}
vecs = []
where = []
prev = 0
depth = 0
for p in range(len(body) + 1):
    if depth == 0 and p > prev:
        seg = km.Circuit('\n'.join(body[prev:p]))
        for s in sims:
            s.do(seg)
        prev = p
        a = sims[0].read_across_shots(allq)
        b = sims[1].read_across_shots(allq)
        for q in range(c.num_qubits):
            if not np.array_equal(a[q], b[q]):
                continue
            v = a[q]
            if v.all() or not v.any():
                continue
            if v[0]:
                v = ~v  # canonical up to complement (X conjugation is free)
            k = np.packbits(v).tobytes()
            if k not in seen:
                seen[k] = len(vecs)
                vecs.append(v.copy())
                where.append((p, q))
    if p < len(body):
        l = body[p]
        depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
np.savez(V / 'cands.npz', xc=xc, vecs=np.array(vecs), where=np.array(where))
print('unique candidate features', len(vecs))
