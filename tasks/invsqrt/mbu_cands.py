"""Find CCX a b t that clear t (t == a&b before, 0 after) -> replace with HMR t + CZ a b if m (saves 1 Toffoli)."""
import sys; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]
c, hdr, body = load(path)
B = 8192
rng = np.random.default_rng(12)
xs = np.concatenate([np.arange(1, 4097), rng.integers(1, X_MAX + 1, B - 4096)]).astype(np.uint64)
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
sim = km.Simulator(batch_size=B, debug_print=False, seed=5)
sim.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
prev = 0; depth = 0; n = 0
for i, l in enumerate(body):
    t = l.split()[0]
    if t == 'CCX' and depth == 0 and ' if ' not in l:
        if i > prev: sim.do(km.Circuit('\n'.join(body[prev:i]))); prev = i
        p = l.split(); qs = [int(p[k][1:]) for k in (1, 2, 3)]
        v = sim.read_across_shots(km.array([km.q(q) for q in qs]))
        a, b, tt = v
        if np.array_equal(tt, a & b):
            print('clears', i, l, 'a,b ever 1:', bool((a & b).any())); n += 1
    depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
print('candidates', n)
