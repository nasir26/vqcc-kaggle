"""Table-cleanup optimiser (ours). Functions over the 128 table addresses as 128-bit ints.
Q(S) = span{1, u, u*v : u, v in S} (S = live wire functions; CX frames make any affine combos available, and
products of affine combos expand into this span). A debt f is free to pay iff f in Q(S). An output wire o can be
erased (HMR + payment) iff o in Q(S without o). CCX w ^= u*v costs one AND.
Usage: python tasks/invsqrt/cleanup_opt.py"""
import json, itertools, random
d = json.load(open('data/work/inv_gen/cleanup.json'))
E = {k: int(v) for k, v in d['entry'].items()}
FULL = (1 << 128) - 1
coord = [sum(1 << a for a in range(128) if a >> s & 1) for s in range(7)]
ADDR = {w: s for w, v in E.items() for s in range(7) if v == coord[s]}
OUT = [w for w in E if w not in ADDR]
PRE = [int(v) for v in d['pre'].values()]

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
    def dim(self): return len(self.p)

def Q(funcs):
    s = Span(); s.add(FULL)
    fl = list(funcs)
    for u in fl: s.add(u)
    for u, v in itertools.combinations(fl, 2): s.add(u & v)
    return s

if __name__ == '__main__':
    X = [E[w] for w in ADDR]
    allq = Q(X + [E[w] for w in OUT]); print('dim Q(all live)', allq.dim(), 'pre debts in Q(all):', sum(allq.has(p) for p in PRE), '/', len(PRE))
    qx = Q(X); print('dim Q(X)', qx.dim(), 'pre debts in Q(X):', sum(qx.has(p) for p in PRE), 'outputs in Q(X):', sum(qx.has(E[w]) for w in OUT))
    # greedy free erasure
    for trial in range(200):
        live = list(OUT); random.shuffle(live); order = []
        progress = True
        while progress:
            progress = False
            for w in list(live):
                rest = X + [E[o] for o in live if o != w]
                if Q(rest).has(E[w]): live.remove(w); order.append(w); progress = True; break
        if trial == 0 or len(live) < best[0]: best = (len(live), order, live)
    print('greedy: stuck outputs', best[0], 'stuck', best[2])
