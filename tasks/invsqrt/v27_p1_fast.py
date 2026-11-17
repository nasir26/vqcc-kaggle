"""Fast exact test (ours): for a kept decoder product P, does ONE cleanup seed, payable by ONE CCZ (a b c with a,b,c
forms over the live span U1), close the cleanup? Canonical quotients by fully reduced echelons.
Usage: v27_p1_fast.py N_SAMPLES [validate]"""
import itertools, pickle, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '.')
import v27_idx_model as M
import v27_p1_probe as PR

FULL = M.FULL


def rref(vs):
    rows = {}
    for x in vs:
        for p in sorted(rows, reverse=True):
            if x >> p & 1: x ^= rows[p]
        if x:
            p = x.bit_length() - 1
            for q in list(rows):
                if rows[q] >> p & 1: rows[q] ^= x
            rows[p] = x
    return rows


def cred(rows, x):
    for p, r in rows.items():
        if x >> p & 1: x ^= r
    return x


def forms(U):
    B = list(M.span(list(U)).values()); out = set()
    for m in range(1, 1 << len(B)):
        v = 0
        for i in range(len(B)):
            if m >> i & 1: v ^= B[i]
        if v not in (0, FULL): out.add(v)
    return sorted(out), B


def analyse(P, V0b):
    V0 = list(M.span(V0b + [P]).values())
    U1 = M.closure(M.ADDR + [P], V0)
    Qr = rref(list(M.Qs(U1).values()))
    Rv = [cred(Qr, v) for v in V0]
    # W basis with coordinates
    W = {}
    coords = {}
    k = 0
    for v in Rv:
        x = v; c = 0
        for p in sorted(W, reverse=True):
            if x >> p & 1: x ^= W[p][0]; c ^= W[p][1]
        if x:
            W[x.bit_length() - 1] = (x, c ^ (1 << k)); k += 1
    def wcoord(y):
        c = 0
        for p in sorted(W, reverse=True):
            if y >> p & 1: y ^= W[p][0]; c ^= W[p][1]
        return c if y == 0 else None
    # payable residues (as W coordinates; W coordinate = combination of W basis vectors)
    F, B = forms(U1)
    pay = set(); seen = set()
    for a, b in itertools.combinations(F, 2):
        ab = a & b
        if ab in seen: continue
        seen.add(ab)
        ys = [cred(Qr, ab & u) for u in B]
        for m in range(1, 1 << len(B)):
            y = 0
            for i in range(len(B)):
                if m >> i & 1: y ^= ys[i]
            if y:
                c = wcoord(y)
                if c is not None: pay.add(c)
    # closing seeds: enumerate quotient V0 / U1, keep those whose W-coordinate is payable
    pU = M.span(U1); Qb = list(M.span([M.red(pU, v) for v in V0 if M.red(pU, v)]).values())
    hits = []
    for m in range(1, 1 << len(Qb)):
        s = 0
        for i in range(len(Qb)):
            if m >> i & 1: s ^= Qb[i]
        c = wcoord(cred(Qr, s))
        if c is None or c not in pay: continue
        if len(M.closure(U1 + [s], V0)) == len(V0):
            hits.append(s); break
    return len(pay), hits


def job(seed):
    PR.rng.seed(seed)
    P = PR.rform() & PR.rform()
    if PR.DC.inspan(PR.pU, P): return None
    npay, hits = analyse(P, PR.V0b)
    return seed, P, npay, hits


if __name__ == '__main__':
    if 'validate' in sys.argv:
        q21 = M.E['q21']
        print('q21: payable residues, one-seed hits:', analyse(q21, PR.V0b)[0], len(analyse(q21, PR.V0b)[1]))
        sys.exit()
    n = int(sys.argv[1]); found = []
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(job, range(1000, 1000 + n)):
            if r and r[3]:
                found.append(r); print('HIT', r[0], 'payable', r[2], flush=True)
    print('samples', n, 'hits', len(found))
    pickle.dump(found, open('../../data/work/inv_gen/v27/p1_fast_hits.pkl', 'wb'))
