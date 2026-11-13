"""Classify every qubit at checkpoints: zero / normalized-x bit / function of (shift, top-k mantissa bits) / other."""
import sys; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; cuts = [int(v) for v in sys.argv[2].split(',')]; K = int(sys.argv[3]) if len(sys.argv) > 3 else 7
c, hdr, body = load(path)
rng = np.random.default_rng(3)
xs = np.concatenate([np.arange(1, 3000), rng.integers(1, X_MAX + 1, 9000)]).astype(np.int64)
xs = xs[: (len(xs) // 64) * 64]
sp = 21 - np.floor(np.log2(xs)).astype(np.int64)          # single-bit shift so the top bit sits at 21
M = xs << sp
addr = (M >> (21 - K)) & ((1 << K) - 1)                       # K bits under the leading one
key = sp * (1 << K) + addr
for L in cuts:
    sim, bits = run(hdr, body, xs.astype(np.uint64), c.num_qubits, upto=L)
    out = []
    for q in range(c.num_qubits):
        v = bits[q].astype(np.int64)
        if not v.any(): out.append('.'); continue
        m = [i for i in range(22) if np.array_equal(v, (M >> i) & 1)]
        if m: out.append(f'M{m[0]}'); continue
        if np.array_equal(v, (xs >> q) & 1) and q < 22: out.append(f'x{q}'); continue
        # function of key?
        order = np.argsort(key, kind='stable'); ks = key[order]; vs = v[order]
        brk = np.flatnonzero(np.diff(ks)) + 1
        seg = np.split(vs, brk)
        if all(s.min() == s.max() for s in seg):
            # function of addr only?
            o2 = np.argsort(addr, kind='stable'); seg2 = np.split(v[o2], np.flatnonzero(np.diff(addr[o2])) + 1)
            out.append('A' if all(s.min() == s.max() for s in seg2) else ('S' if all(len(np.unique(v[sp == t])) == 1 for t in np.unique(sp)) else 'T'))
        else:
            out.append('?')
    print(f'cut {L:6d}:', ' '.join(f'{q}:{o}' for q, o in enumerate(out)))
