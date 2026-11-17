"""Probe alternative kept decoder products P1 = L*h (L,h forms over decoder inputs, P1 outside span(inputs+targets)):
free cleanup closure from span(address) + P1, and single-seed search for the best (ours)."""
import random, sys
sys.path.insert(0, '.')
import v27_idx_model as M, v27_dec_compare as DC

ent, ext, nq, blk = DC.tabs('../../data/work/inv_gen/v27/efd.kmx', 17882, 18181)
changed = [q for q in ext if ent.get(q) != ext.get(q)]
inp = [v for q, v in ent.items() if v is not None]
T = [ext[q] for q in changed if q != 21]
FULL = M.FULL
B = list(DC.span(inp + [FULL]).values())
pU = DC.span(B + T)
outs = [w for w in M.OUTS if w != 'q21']
V0b = [FULL] + M.ADDR + [M.E[w] for w in outs]
rng = random.Random(1)


def rform():
    v = 0
    while v in (0, FULL):
        v = 0
        for b in B:
            if rng.random() < 0.5: v ^= b
    return v


def single_seed_best(U1, V0):
    pu = M.span(U1); Qb = list(M.span([M.red(pu, v) for v in V0 if M.red(pu, v)]).values())
    best = 0
    for m in range(1, 1 << len(Qb)):
        w = 0
        for i in range(len(Qb)):
            if m >> i & 1: w ^= Qb[i]
        n = len(M.closure(U1 + [w], V0))
        if n == len(V0): return n
        best = max(best, n)
    return best


res = []
q21 = M.E['q21']
for it in range(int(sys.argv[1]) if __name__ == "__main__" else 0):
    P = rform() & rform()
    if not DC.inspan(pU, P) is False and DC.inspan(pU, P):
        continue
    V0 = list(M.span(V0b + [P]).values())
    U1 = M.closure(M.ADDR + [P], V0)
    res.append((len(U1) - 9, P))
if __name__ == '__main__':
    res.sort(key=lambda r: -r[0])
    V0q = list(M.span(V0b + [q21]).values())
    print('q21 free extra dims:', len(M.closure(M.ADDR + [q21], V0q)) - 9)
    from collections import Counter
    print('probe free extra dims distribution:', Counter(r[0] for r in res))
    for k, P in res[:int(sys.argv[2])]:
        V0 = list(M.span(V0b + [P]).values())
        U1 = M.closure(M.ADDR + [P], V0)
        print('P with', k, 'extra free dims: single seed best', single_seed_best(U1, V0), 'of', len(V0), flush=True)
