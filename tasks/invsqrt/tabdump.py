import sys; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; L = int(sys.argv[2])
c, hdr, body = load(path)
rng = np.random.default_rng(3)
xs = np.concatenate([np.arange(1, 3000), rng.integers(1, X_MAX + 1, 13000)]).astype(np.int64)
xs = xs[: (len(xs) // 64) * 64]
sp = 21 - np.floor(np.log2(xs)).astype(np.int64)
M = xs << sp
sim, bits = run(hdr, body, xs.astype(np.uint64), c.num_qubits, upto=L)
for K in range(4, 9):
    addr = (M >> (21 - K)) & ((1 << K) - 1)
    for name, key in [('par', (sp % 2) * (1 << K) + addr), ('addr', addr)]:
        ok = []
        for q in range(c.num_qubits):
            v = bits[q].astype(np.int64)
            if not v.any(): continue
            o = np.argsort(key, kind='stable'); seg = np.split(v[o], np.flatnonzero(np.diff(key[o])) + 1)
            if all(s.min() == s.max() for s in seg): ok.append(q)
        print(K, name, len(ok), ok)
