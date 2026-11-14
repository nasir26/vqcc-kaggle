"""Exhaustive search over monomial bank sets (ours): banks are address monomials x_i x_j (1 AND) and x_i x_j x_k
built on a pair bank (1 AND). For each set of NB banks, reverse-time free closure must reach all 17 outputs.
Usage: python tasks/invsqrt/cleanup_exh.py NB [include_slot0]"""
import sys, itertools, pickle
sys.path.insert(0, 'tasks/invsqrt')
from cleanup_opt import E, ADDR, OUT, Q
from concurrent.futures import ProcessPoolExecutor
X = [E[w] for w in sorted(ADDR, key=ADDR.get)]
import os, random as _r
if os.environ.get("BASIS_SEED"):
    _g = _r.Random(int(os.environ["BASIS_SEED"]))
    while True:
        M = [[_g.randrange(2) for _ in range(6)] for _ in range(6)]
        import numpy as _np
        if round(abs(_np.linalg.det(_np.array(M)))) % 2 == 1: break
    X = [X[0]] + [eval("^".join(["0"] + [f"X[{j+1}]" for j in range(6) if M[i][j]])) for i in range(6)]
NB = int(sys.argv[1]); VARS = range(0 if len(sys.argv) > 2 else 1, 7)
PAIRS = list(itertools.combinations(VARS, 2))

def feasible(banks):
    S = X + [b for b in banks]; outs = list(OUT)
    while outs:
        q = Q(S); hit = [o for o in outs if q.has(E[o])]
        if not hit: return False
        for o in hit: S.append(E[o]); outs.remove(o)
    return True

def mono(t):
    f = X[t[0]]
    for i in t[1:]: f &= X[i]
    return f

def job(qset):
    qset = list(qset); c = NB - len(qset); sols = []
    cub = sorted({tuple(sorted(set(p) | {k})) for p in qset for k in VARS if k not in p})
    for cs in itertools.combinations(cub, c):
        if feasible([mono(p) for p in qset] + [mono(t) for t in cs]): sols.append((qset, cs))
    return sols

if __name__ == '__main__':
    jobs = [qs for q in range(max(1, (NB + 1) // 2), NB + 1) for qs in itertools.combinations(PAIRS, q)]
    print('jobs', len(jobs), flush=True)
    sols = []
    with ProcessPoolExecutor(96) as ex:
        for r in ex.map(job, jobs, chunksize=4):
            if r:
                sols += r; print('SOLUTION', r[0], flush=True)
                if len(sols) > 20: break
    print("solutions", len(sols)); pickle.dump(dict(sols=sols, rows=(M if os.environ.get("BASIS_SEED") else None), seed=os.environ.get("BASIS_SEED")), open(f"data/work/inv_gen/cleanup_exh_{NB}_s{os.environ.get('BASIS_SEED','0')}.pkl", "wb"))
