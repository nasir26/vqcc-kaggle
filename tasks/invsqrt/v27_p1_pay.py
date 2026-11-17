"""For sampled kept products P (decoder first product candidates): is there a single cleanup seed payable by ONE CCZ
that closes the cleanup? (ours). Usage: v27_p1_pay.py N_SAMPLES"""
import pickle, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '.')
import v27_p1_probe as PR
import v27_idx_model as M
import v27_ccz_seeds as CS


def job(seed):
    PR.rng.seed(seed)
    P = PR.rform() & PR.rform()
    if PR.DC.inspan(PR.pU, P):
        return None
    V0 = list(M.span(PR.V0b + [P]).values())
    U1 = M.closure(M.ADDR + [P], V0)
    pay = CS.payable_seeds(U1, V0)
    for key, (s, a, b, c) in pay.items():
        if len(M.closure(U1 + [s], V0)) == len(V0):
            return (seed, P, s, a, b, c, len(pay))
    return (seed, P, None, None, None, None, len(pay))


if __name__ == '__main__':
    n = int(sys.argv[1]); hits = []
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(job, range(n)):
            if r is None: continue
            if r[2] is not None:
                hits.append(r); print('HIT seed', r[0], 'payable seeds', r[6], flush=True)
    print('samples', n, 'hits', len(hits))
    pickle.dump(hits, open('../../data/work/inv_gen/v27/p1_hits.pkl', 'wb'))
