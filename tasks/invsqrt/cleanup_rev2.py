"""Reverse-time cleanup search, rank-guided (ours). Banks: products of two affine address forms, or of a bank and an
affine address form. Score = number of outputs still unreachable after free closure, then the missing rank of the
outputs over Q(S). Usage: python tasks/invsqrt/cleanup_rev2.py BEAM MAXBANKS"""
import sys, itertools, pickle
sys.path.insert(0, 'tasks/invsqrt')
from cleanup_opt import E, ADDR, OUT, Q, FULL, Span
from concurrent.futures import ProcessPoolExecutor
X = [E[w] for w in sorted(ADDR, key=ADDR.get)]
BEAM, MAXB = int(sys.argv[1]), int(sys.argv[2])
AFF = list(dict.fromkeys([(FULL if m & 128 else 0) ^ eval('^'.join(['0'] + [f'X[{i}]' for i in range(7) if m >> i & 1])) for m in range(1, 256)]))

def closure(S, outs):
    S = list(S); outs = list(outs)
    while True:
        q = Q(S); hit = [o for o in outs if q.has(E[o])]
        if not hit: return S, outs, q
        for o in hit: S.append(E[o]); outs.remove(o)

def missing(q, outs):
    s = Span(); s.p = dict(q.p); r = 0
    for o in outs: r += s.add(E[o])
    return r

def score(args):
    S, outs, p = args
    S2, o2, q = closure(S + [p], outs)
    return (len(o2), missing(q, o2)), p

def cands(S, banks):
    out = set()
    for a, b in itertools.combinations_with_replacement(AFF, 2): out.add(a & b)
    for bk in banks:
        for a in AFF: out.add(bk & a)
    out.discard(0); return [p for p in out if p not in S]

if __name__ == '__main__':
    S0, o0, q0 = closure(X, OUT)
    beam = [((len(o0), missing(q0, o0)), S0, o0, [])]
    with ProcessPoolExecutor(64) as ex:
        for depth in range(1, MAXB + 1):
            nxt = []
            for sc, S, outs, banks in beam:
                cs = cands(S, banks)
                res = list(ex.map(score, [(S, outs, p) for p in cs], chunksize=64))
                res.sort(key=lambda t: t[0])
                for s2, p in res[:BEAM]:
                    S2, o2, _ = closure(S + [p], outs)
                    nxt.append((s2, S2, o2, banks + [p]))
            nxt.sort(key=lambda t: t[0])
            uniq = {}
            for t in nxt: uniq.setdefault(frozenset(t[3]), t)
            beam = list(uniq.values())[:BEAM]
            print('banks', depth, 'best score', beam[0][0], flush=True)
            if beam[0][0][0] == 0:
                print('SOLVED', depth); pickle.dump(beam[0][3], open('data/work/inv_gen/cleanup_banks.pkl', 'wb')); break
