"""Cleanup subspace model in the 128-point table-index space (ours). Functions = 128-bit ints over idx.
V0 = span(1, 7 address bits, outputs); U1 = span(1, address bits) (+ q21 when kept)."""
import itertools, json, sys
sys.path.insert(0, '.')
d = json.load(open('../../data/work/inv_gen/v27/cleanup_efd.json'))
E = {k: int(v) for k, v in d['entry'].items()}
FULL = (1 << 128) - 1
coord = [sum(1 << a for a in range(128) if a >> s & 1) for s in range(7)]
ADDR = [coord[s] for s in range(7)]
OUTS = [w for w, v in E.items() if v not in ADDR]


def red(p, x):
    while x:
        h = x.bit_length() - 1
        if h not in p: return x
        x ^= p[h]
    return 0


def span(vs):
    p = {}
    for x in vs:
        x = red(p, x)
        if x: p[x.bit_length() - 1] = x
    return p


def Qs(U):
    U = list(U)
    return span([FULL] + U + [u & v for u, v in itertools.combinations(U, 2)])


def inter(Qp, V):
    piv = {}; out = []
    for v in V:
        r = v; comb = v
        while r:
            h = r.bit_length() - 1
            if h in Qp: r ^= Qp[h]
            elif h in piv: r ^= piv[h][0]; comb ^= piv[h][1]
            else: piv[h] = (r, comb); break
        if not r: out.append(comb)
    return out


def closure(U, V):
    U = list(span(list(U) + [FULL]).values())
    while True:
        nb = list(span(U + inter(Qs(U), V)).values())
        if len(nb) == len(U): return U
        U = nb


def setup(with21):
    outs = [w for w in OUTS if with21 or w != 'q21']
    V0 = list(span([FULL] + ADDR + [E[w] for w in outs]).values())
    U1 = closure(ADDR, V0)
    return V0, U1


if __name__ == '__main__':
    for w in (1, 0):
        V0, U1 = setup(w)
        pU = span(U1); Qb = list(span([red(pU, v) for v in V0 if red(pU, v)]).values())
        print('with q21' if w else 'no q21', 'dim V0', len(V0), 'U1', len(U1), 'quotient', len(Qb))
