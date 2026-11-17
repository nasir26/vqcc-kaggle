"""Subspace cleanup model (ours): V0 = span of live wires at cleanup entry (vectors over sampled x), Uend = span of
the wires that stay live. Reverse closure: U <- U + (Q(U) cap V0); seeds = arbitrary vectors of V0 paid by CCZ.
Reports the closure dimension with and without the decoder product q21."""
import itertools, sys
sys.path.insert(0, '.')
import v27_cleanup_full as F

FULL = F.FULL


def reduce(p, x):
    while x:
        h = x.bit_length() - 1
        if h not in p: return x
        x ^= p[h]
    return 0


def basis(vs):
    p = {}
    for x in vs:
        x = reduce(p, x)
        if x: p[x.bit_length() - 1] = x
    return list(p.values())


def Qspan(U):
    s = F.Span(); s.add(FULL)
    for u in U: s.add(u)
    for u, v in itertools.combinations(U, 2): s.add(u & v)
    return s.p


def intersect(Qp, V0):
    """vectors of span(V0) lying in span(Qp): kernel of residuals."""
    rows = []  # (residual, combo)
    piv = {}
    out = []
    for v in V0:
        r = v; comb = v
        while r:
            h = r.bit_length() - 1
            if h in Qp: r ^= Qp[h]
            elif h in piv: r ^= piv[h][0]; comb ^= piv[h][1]
            else: piv[h] = (r, comb); break
        if not r: out.append(comb)
    return out


def closure(U0, V0):
    U = basis(U0 + [FULL])
    while True:
        add = intersect(Qspan(U), V0)
        nb = basis(U + add)
        if len(nb) == len(U): return U
        U = nb


if __name__ == '__main__':
    vec = F.vec
    static = [vec[q] for q in F.STATIC]
    for name, outs in (('with q21', F.OUTS), ('without q21', [q for q in F.OUTS if q != 21])):
        V0 = basis(static + [vec[q] for q in outs] + [FULL])
        U = closure(static, V0)
        print(name, 'dim V0', len(V0), 'dim Uend', len(basis(static + [FULL])), 'closure dim', len(U), '-> seeds needed >=', len(V0) - len(U) and 1)
        print('   quotient dim after closure', len(V0) - len(U))
