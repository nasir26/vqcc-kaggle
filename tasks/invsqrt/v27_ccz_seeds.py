"""Seeds payable by ONE CCZ (ours): s in V0 with s = a b c + q, q in Q(U), a,b,c in span(U); for each pair (a,b) the
c-condition is linear. Then two-seed plans: s1 at U1, s2 at U2 = closure(U1 + s1), closure(U2 + s2) == V0."""
import itertools, sys
sys.path.insert(0, '.')
import v27_idx_model as M

FULL = M.FULL


def forms(U):
    B = list(M.span(list(U)).values())
    out = set()
    for m in range(1, 1 << len(B)):
        v = 0
        for i in range(len(B)):
            if m >> i & 1: v ^= B[i]
        if v not in (0, FULL): out.add(v)
    return sorted(out), B


def solve_combo(target, vecs):
    """find subset of vecs xoring to target (vecs list of ints); return mask or None"""
    piv = {}
    for i, v in enumerate(vecs):
        m = 1 << i
        while v:
            h = v.bit_length() - 1
            if h in piv: v ^= piv[h][0]; m ^= piv[h][1]
            else: piv[h] = (v, m); break
    x = target; m = 0
    while x:
        h = x.bit_length() - 1
        if h not in piv: return None
        x ^= piv[h][0]; m ^= piv[h][1]
    return m


def payable_seeds(U, V0):
    """all seed vectors s (mod span U) in V0 with s = a b c + q, q in Q(U), a,b,c forms over U (joint echelon of
    Q(U) and V0 tracking V0 components). Returns dict key->(s, a, b, abc)."""
    Qp = M.Qs(U)
    J = {}
    for x in Qp.values():
        J[x.bit_length() - 1] = (x, 0)
    for j, v in enumerate(V0):
        x, m = v, 1 << j
        while x:
            h = x.bit_length() - 1
            if h in J: x ^= J[h][0]; m ^= J[h][1]
            else: J[h] = (x, m); break
    pU = M.span(list(U) + [FULL])
    F, B = forms(U)
    res = {}
    seen = set()
    for a, b in itertools.combinations(F, 2):
        ab = a & b
        if ab in seen: continue
        seen.add(ab)
        for c in F:
            x = ab & c
            if not M.red(Qp, x): continue  # abc in Q(U): nothing new
            m = 0
            while x:
                h = x.bit_length() - 1
                if h in J: x ^= J[h][0]; m ^= J[h][1]
                else: break
            if x: continue
            s = 0
            for j in range(len(V0)):
                if m >> j & 1: s ^= V0[j]
            key = M.red(pU, s)
            if key and key not in res: res[key] = (s, a, b, ab & c)
    return res


if __name__ == '__main__':
    for w in (1, 0):
        V0, U1 = M.setup(w)
        P1 = payable_seeds(U1, V0)
        print('with q21' if w else 'no q21', 'one-CCZ payable first seeds (mod U1):', len(P1), flush=True)
        found = []
        for key, (s1, a, b, c) in P1.items():
            U2 = M.closure(U1 + [s1], V0)
            if len(U2) == len(V0): found.append(('single', s1)); continue
            P2 = payable_seeds(U2, V0)
            for k2, (s2, a2, b2, c2) in P2.items():
                if len(M.closure(U2 + [s2], V0)) == len(V0):
                    found.append((s1, a, b, c, s2, a2, b2, c2)); break
            if found: break
        print('   two-CCZ plan found:', bool(found), flush=True)
        if found:
            import pickle; pickle.dump(found, open(f'../../data/work/inv_gen/v27/ccz_plan_{w}.pkl', 'wb'))
