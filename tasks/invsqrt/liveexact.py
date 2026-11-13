import sys; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; step = int(sys.argv[2]) if len(sys.argv) > 2 else 10
c, hdr, body = load(path)
rng = np.random.default_rng(9)
xs = np.concatenate([rng.integers(1, X_MAX + 1, 3072), np.arange(1, 1025)]).astype(np.uint64)
sim = km.Simulator(batch_size=len(xs), debug_print=False, seed=3)
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
sim.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
allq = km.array([km.q(i) for i in range(c.num_qubits)])
prev = 0; depth = 0; out = []
for p in range(len(body) + 1):
    if (p % step == 0 and depth == 0) or p == len(body):
        if p > prev: sim.do(km.Circuit('\n'.join(body[prev:p]))); prev = p
        out.append((p, int(sim.read_across_shots(allq).any(axis=1).sum())))
    if p < len(body):
        l = body[p]; depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
np.save(sys.argv[3], np.array(out))
o = np.array(out)
for thr in (62, 61, 60, 59, 58):
    m = o[:, 1] >= thr
    # intervals
    iv = []; st = None
    for (p, v), mm in zip(o, m):
        if mm and st is None: st = p
        if not mm and st is not None: iv.append((st, p)); st = None
    if st is not None: iv.append((st, o[-1, 0]))
    print(thr, 'points', int(m.sum()), 'intervals', len(iv), iv[:40])
