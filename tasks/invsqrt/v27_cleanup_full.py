"""Cleanup closure over ALL live wires (ours): functions are bit vectors over sampled x, Q(S) = span{1, u, u v}.
Region entry = efd kmx line 18183. Outputs = the 17 wires erased in the efd cleanup."""
import itertools, sys
import numpy as np
sys.path.insert(0, '.')
import v27_dec_compare as DC
from kmxsim import km, load

OUTS = [7, 8, 13, 16, 17, 18, 19, 20, 21, 26, 27, 28, 30, 31, 33, 35, 43]
c, hdr, body = load('../../data/work/inv_gen/v27/efd.kmx'); nh = len(hdr)
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
sim = km.Simulator(batch_size=len(DC.xs), debug_print=False, seed=4)
sim.write_across_shots(km.array([km.q(q) for q in xq]), ((DC.xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
allq = km.array([km.q(i) for i in range(44)])
sim.do(km.Circuit('\n'.join(body[:18183 - 1 - nh])))
st = sim.read_across_shots(allq)
live = [q for q in range(44) if st[q].any()]
vec = {q: int.from_bytes(np.packbits(st[q]).tobytes(), 'big') for q in live}
N = st.shape[1]; FULL = (1 << N) - 1
STATIC = [q for q in live if q not in OUTS]
print('live', len(live), 'static', STATIC)


class Span:
    def __init__(self): self.p = {}
    def add(self, x):
        while x:
            h = x.bit_length() - 1
            if h in self.p: x ^= self.p[h]
            else: self.p[h] = x; return True
        return False
    def has(self, x):
        while x:
            h = x.bit_length() - 1
            if h not in self.p: return False
            x ^= self.p[h]
        return True


def Q(fs):
    s = Span(); s.add(FULL)
    for u in fs: s.add(u)
    for u, v in itertools.combinations(fs, 2): s.add(u & v)
    return s


def clos(seeds, outs=OUTS):
    S = [vec[q] for q in STATIC] + [vec[q] for q in seeds]
    rest = [o for o in outs if o not in seeds]; order = []
    while True:
        qq = Q(S); hit = [o for o in rest if qq.has(vec[o])]
        if not hit: return rest, order
        for o in hit: S.append(vec[o]); rest.remove(o); order.append(o)


if __name__ == '__main__':
    r, o = clos([]); print('no seeds: stuck', r, 'free order', o)
    for k in (1, 2):
        ok = [p for p in itertools.combinations([q for q in OUTS], k) if not clos(list(p))[0]]
        print(k, 'seeds close:', ok[:20], len(ok))
    outs_no21 = [q for q in OUTS if q != 21]
    for k in (1, 2):
        ok = [p for p in itertools.combinations(outs_no21, k) if not clos(list(p), outs_no21)[0]]
        print('without q21 wire:', k, 'seeds close:', ok[:20], len(ok))
