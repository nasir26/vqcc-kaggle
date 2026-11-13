import sys, hashlib; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; step = int(sys.argv[2])
c, hdr, body = load(path)
rng = np.random.default_rng(5)
xs = np.concatenate([np.arange(1, 1025), rng.integers(1, X_MAX + 1, 3072)]).astype(np.uint64)
sim = km.Simulator(batch_size=len(xs), debug_print=False, seed=3)
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
sim.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
allq = km.array([km.q(i) for i in range(c.num_qubits)])
prev = 0; depth = 0; fps = {}; pos = []
for p in range(len(body) + 1):
    if p % step == 0 and depth == 0:
        if p > prev: sim.do(km.Circuit('\n'.join(body[prev:p]))); prev = p
        st = sim.read_across_shots(allq)
        # canonical: set of qubit rows as bytes, order-insensitive (wire permutation allowed)
        rows = sorted(np.packbits(st, axis=1).tobytes()[i*len(xs)//8:(i+1)*len(xs)//8] for i in range(c.num_qubits))
        h = hashlib.sha1(b''.join(rows)).hexdigest()[:10]
        hx = hashlib.sha1(np.packbits(st).tobytes()).hexdigest()[:10]
        fps.setdefault(h, []).append(p)
    if p < len(body):
        l = body[p]; depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
for h, ps in fps.items():
    if len(ps) > 1 and ps[-1] - ps[0] > 2 * step: print(h, ps[:3], '...', ps[-3:], len(ps))
