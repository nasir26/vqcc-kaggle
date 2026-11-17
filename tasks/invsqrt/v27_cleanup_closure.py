"""Reverse-time free-erasure closure for the efd84ca5 table cleanup (ours). Uses cleanup_opt's Q-span model on the
entry functions extracted by cleanup_extract.py (data/work/inv_gen/cleanup.json = efd region 18183..19526)."""
import sys
sys.path.insert(0, 'tasks/invsqrt')
from cleanup_opt import E, ADDR, OUT, Q

X = [E[w] for w in sorted(ADDR, key=ADDR.get)]


def closure(seed_wires):
    S = X + [E[w] for w in seed_wires]
    got = list(seed_wires)
    outs = [o for o in OUT if o not in seed_wires]
    while True:
        q = Q(S)
        hit = [o for o in outs if q.has(E[o])]
        if not hit:
            return got, outs
        for o in hit:
            S.append(E[o]); outs.remove(o); got.append(o)


if __name__ == '__main__':
    print('outputs', OUT)
    g, rest = closure([]); print('closure from X:', g, 'stuck', len(rest))
    g, rest = closure(['q21']); print('closure from X+q21:', len(g), 'stuck', rest)
    for o in OUT:
        if o == 'q21':
            continue
        g, rest = closure(['q21', o])
        if len(rest) == 0:
            print('one extra seed closes all:', o)
