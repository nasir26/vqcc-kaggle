"""Exhaustive single-seed search in the subspace cleanup model (ours)."""
import sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '.')
import v27_cleanup_space as S, v27_cleanup_full as F

vec = F.vec
static = [vec[q] for q in F.STATIC]
OUTS = F.OUTS if 'no21' not in sys.argv else [q for q in F.OUTS if q != 21]
V0 = S.basis(static + [vec[q] for q in OUTS] + [F.FULL])
U1 = S.closure(static, V0)
pU = {x.bit_length() - 1: x for x in U1}
Q = [S.reduce(pU, v) for v in V0]
Qb = S.basis([x for x in Q if x])  # quotient representatives
d = len(Qb)


def job(m):
    w = 0
    for i in range(d):
        if m >> i & 1: w ^= Qb[i]
    U = S.closure(U1 + [w], V0)
    return len(U), m


if __name__ == '__main__':
    print('quotient dim', d, flush=True)
    if 'check' in sys.argv:
        print('efd seeds q16,q17 close:', len(S.closure(U1 + [vec[16], vec[17]], V0)), 'of', len(V0))
        sys.exit()
    best = (0, 0)
    with ProcessPoolExecutor(32) as ex:
        for n, m in ex.map(job, range(1, 1 << d), chunksize=64):
            if n > best[0]: best = (n, m); print('best so far', n, 'of', len(V0), flush=True)
    print('single seed best closure dim', best[0], 'of', len(V0))
