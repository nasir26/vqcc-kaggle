"""Two-seed search without the q21 product (ours): seed1 over all quotient vectors reaching the best single-seed
closure, seed2 exhaustive."""
import sys
from concurrent.futures import ProcessPoolExecutor
sys.argv.append('no21')
sys.path.insert(0, '.')
import v27_seed_search as SS
S = SS.S


def vecof(m):
    w = 0
    for i in range(SS.d):
        if m >> i & 1: w ^= SS.Qb[i]
    return w


def job1(m):
    return len(S.closure(SS.U1 + [vecof(m)], SS.V0)), m


def job2(args):
    m1, m2 = args
    return len(S.closure(SS.U1 + [vecof(m1), vecof(m2)], SS.V0)), m1, m2


if __name__ == '__main__':
    with ProcessPoolExecutor(32) as ex:
        r1 = list(ex.map(job1, range(1, 1 << SS.d), chunksize=64))
        top = max(n for n, _ in r1)
        seeds1 = [m for n, m in r1 if n == top]
        print('seed1 candidates at', top, ':', len(seeds1), flush=True)
        best = 0
        for m1 in seeds1[:40]:
            for n, a, b in ex.map(job2, [(m1, m2) for m2 in range(1, 1 << SS.d) if m2 != m1], chunksize=64):
                if n > best: best = n; print('best', n, 'of', len(SS.V0), flush=True)
                if n == len(SS.V0): print('CLOSES', a, b, flush=True); sys.exit()
    print('two seeds (greedy seed1) best', best, 'of', len(SS.V0))
