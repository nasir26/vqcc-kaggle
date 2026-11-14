"""Reverse-time cleanup search (ours). Reading the cleanup backwards, the live set S grows from the 7 address wires:
an output o can be (un-)erased for free iff o in Q(S); a bank costs one AND and is a product L1*L2 of affine forms over
S. Free additions are monotone, so closure is greedy-optimal; banks are chosen by beam search.
Goal: every output in S. Usage: python tasks/invsqrt/cleanup_rev.py [beam] [maxbanks]"""
import sys, itertools
sys.path.insert(0, 'tasks/invsqrt')
from cleanup_opt import E, ADDR, OUT, Q, FULL, Span, PRE
X = [E[w] for w in sorted(ADDR, key=ADDR.get)]
BEAM = int(sys.argv[1]) if len(sys.argv) > 1 else 20
MAXB = int(sys.argv[2]) if len(sys.argv) > 2 else 8
AFFX = []
for m in range(1, 256):
    f = FULL if m & 128 else 0
    for i in range(7):
        if m >> i & 1: f ^= X[i]
    AFFX.append(f)
AFFX = list(dict.fromkeys(AFFX))

def closure(S, outs):
    S = list(S); outs = list(outs); added = []
    while True:
        q = Q(S); hit = [o for o in outs if q.has(E[o])]
        if not hit: return S, outs, added
        for o in hit: S.append(E[o]); outs.remove(o); added.append(o)

def forms(S):
    extra = S[7:]
    fs = list(AFFX)
    for s in extra:
        fs.append(s); fs += [s ^ x for x in X]; fs.append(s ^ FULL)
    return list(dict.fromkeys(fs))

S0, outs0, add0 = closure(X, OUT)
beam = [(S0, outs0, [('free', add0)])]
for depth in range(1, MAXB + 1):
    nxt = []
    for S, outs, hist in beam:
        q0 = Q(S); fs = forms(S); seen = set(); scored = []
        for a, b in itertools.combinations_with_replacement(range(len(fs)), 2):
            p = fs[a] & fs[b]
            if p in seen or p in S or p == 0: continue
            seen.add(p)
            q = Q(S + [p]); n = sum(q.has(E[o]) for o in outs)
            scored.append((n, q.dim(), p, (a, b)))
        scored.sort(key=lambda t: (-t[0], -t[1]))
        for n, dm, p, ab in scored[:BEAM]:
            S2, o2, ad = closure(S + [p], outs)
            nxt.append((S2, o2, hist + [('bank', p, ab), ('free', ad)]))
    nxt.sort(key=lambda t: len(t[1]))
    uniq = {}; 
    for t in nxt:
        k = tuple(sorted(t[1])) + (len(t[0]),)
        uniq.setdefault(k, t)
    beam = list(uniq.values())[:BEAM]
    print('banks', depth, 'min outputs left', len(beam[0][1]), beam[0][1], flush=True)
    if not beam[0][1]:
        print('SOLVED with', depth, 'banks'); import pickle; pickle.dump(beam[0], open('data/work/inv_gen/cleanup_rev_sol.pkl', 'wb')); break
