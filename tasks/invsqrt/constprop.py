"""Find Toffoli-like gates whose controls are constant / equal / complementary on all sampled shots.
Usage: constprop.py FILE [nbatches]"""
import sys, re; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; nb = int(sys.argv[2]) if len(sys.argv) > 2 else 4
c, hdr, body = load(path)
B = 8192
rng = np.random.default_rng(11)
xs_all = np.concatenate([np.arange(1, 8193), rng.integers(1, X_MAX + 1, B * (nb - 1))]).astype(np.uint64)
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
# indices of toffoli-like gates, with condition depth info
idx = []; depth = 0
for i, l in enumerate(body):
    t = l.split()[0]
    if t in ('CCX', 'CCZ', 'CSWAP'):
        idx.append((i, depth > 0 or ' if ' in l))
    depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
stats = {}
for bi in range(nb):
    xs = xs_all[bi * B:(bi + 1) * B]
    sim = km.Simulator(batch_size=B, debug_print=False, seed=100 + bi)
    sim.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
    prev = 0
    for (i, cond) in idx:
        if i > prev:
            sim.do(km.Circuit('\n'.join(body[prev:i]))); prev = i
        p = body[i].split()
        qs = [int(p[1][1:]), int(p[2][1:]), int(p[3][1:])]
        v = sim.read_across_shots(km.array([km.q(q) for q in qs]))
        s = stats.setdefault(i, np.zeros(8, dtype=np.int64))
        a, b, t = v[0], v[1], v[2]
        if p[0] == 'CSWAP':
            # control a; swap b,t: no-op if a always 0, or if b == t always
            s += [a.any(), (~a).any(), (b != t).any(), (a & (b != t)).any(), 0, 0, 0, 0]
        else:
            s += [a.any(), (~a).any(), b.any(), (~b).any(), (a != b).any(), (a == b).any(), (a & b).any(), 0]
    sim.do(km.Circuit('\n'.join(body[prev:])))
cands = []
for (i, cond) in idx:
    s = stats[i]; p = body[i].split()
    if p[0] == 'CSWAP':
        if not s[0] or not s[3]: cands.append((i, 'noop', body[i], cond))
        elif not s[1]: cands.append((i, 'always-swap', body[i], cond))
    else:
        if not s[6]: cands.append((i, 'never-fires', body[i], cond))
        elif not s[1]: cands.append((i, 'c1=1 -> 2q', body[i], cond))
        elif not s[3]: cands.append((i, 'c2=1 -> 2q', body[i], cond))
        elif not s[4]: cands.append((i, 'c1==c2 -> 2q', body[i], cond))
for cnd in cands: print(*cnd)
print('total toffoli-like', len(idx), 'candidates', len(cands))
