"""Tower-field GF(((2^3)^2)^2) arithmetic for GF(2^12), as bilinear rank-1 term lists.

Every step used by the circuits has the form  R ^= sum_k gamma_k (alpha_k . X)(beta_k . Y) + L(Z)
with alpha_k, beta_k GF(2) linear forms on the input registers' qubits and gamma_k a set of target
qubits. A rank-1 term costs one Toffoli (init_and + measurement-based del_and); linear parts and
basis changes are CNOTs. Terms with alpha_k == beta_k on the same register collapse to a linear
term (x . x = x over GF(2)).

Fields: GF(8) = GF(2)[t]/(t^3 + t + 1); GF(64) = GF(8)[u]/(u^2 + u + nu1);
GF(4096) = GF(64)[v]/(v^2 + v + nu2). Tower element bit layout: GF(64) = d0 | d1 << 3,
GF(4096) = a0 | a1 << 6. `iso` maps kickmix's polynomial-basis GF(2^12) (km.GF2Field(12)) to the
tower by sending alpha to a root of km's modulus; every derived term list is checked against
km.GF2Field on basis pairs (sufficient for bilinear maps) or exhaustively.
"""
from __future__ import annotations

import dataclasses
import itertools
from functools import lru_cache

T3 = 0b1011  # t^3 + t + 1


def mul8(a: int, b: int) -> int:
    r = 0
    for i in range(3):
        if (b >> i) & 1:
            r ^= a << i
    for i in (4, 3):
        if (r >> i) & 1:
            r ^= T3 << (i - 3)
    return r


def _trace8(x: int) -> int:
    return x ^ mul8(x, x) ^ mul8(mul8(x, x), mul8(x, x))


NU1 = next(x for x in range(1, 8) if _trace8(x) == 1)


def mul64(a: int, b: int) -> int:
    a0, a1, b0, b1 = a & 7, a >> 3, b & 7, b >> 3
    p11 = mul8(a1, b1)
    return (mul8(a0, b0) ^ mul8(NU1, p11)) | ((mul8(a0, b1) ^ mul8(a1, b0) ^ p11) << 3)


def _irreducible_over64(nu: int) -> bool:
    return all(mul64(y, y) ^ y ^ nu for y in range(64))


NU2 = next(x for x in range(1, 64) if _irreducible_over64(x))


def mul4096(a: int, b: int) -> int:
    a0, a1, b0, b1 = a & 63, a >> 6, b & 63, b >> 6
    p11 = mul64(a1, b1)
    return (mul64(a0, b0) ^ mul64(NU2, p11)) | ((mul64(a0, b1) ^ mul64(a1, b0) ^ p11) << 6)


def pow_t(mul, x: int, e: int, one: int = 1) -> int:
    r = one
    while e:
        if e & 1:
            r = mul(r, x)
        x = mul(x, x)
        e >>= 1
    return r


# ---------------------------------------------------------------------------
# GF(2) linear algebra on bit-vectors (python ints).


def mat_vec(cols: list[int], x: int) -> int:
    """Matrix given by its columns (ints) times bit-vector x."""
    r = 0
    for i, c in enumerate(cols):
        if (x >> i) & 1:
            r ^= c
    return r


def mat_inv(cols: list[int], n: int) -> list[int]:
    """Inverse of an n x n GF(2) matrix given by columns, returned as columns."""
    rows = [sum(((cols[j] >> i) & 1) << j for j in range(n)) | (1 << (n + i)) for i in range(n)]
    for c in range(n):
        piv = next(r for r in range(c, n) if (rows[r] >> c) & 1)
        rows[c], rows[piv] = rows[piv], rows[c]
        for r in range(n):
            if r != c and (rows[r] >> c) & 1:
                rows[r] ^= rows[c]
    inv_rows = [row >> n for row in rows]
    return [sum(((inv_rows[i] >> j) & 1) << i for i in range(n)) for j in range(n)]


def form_compose(form: int, cols: list[int]) -> int:
    """Row form f (on y = M x) as a form on x: (f . M x) = (f M) . x."""
    return sum((bin(form & c).count('1') & 1) << j for j, c in enumerate(cols))


@lru_cache(maxsize=None)
def iso(modulus: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """(std -> tower columns, tower -> std columns) for km's polynomial basis with `modulus`."""
    deg = modulus.bit_length() - 1

    def poly_at(x: int) -> int:
        r = 0
        for i in range(deg, -1, -1):
            r = mul4096(r, x) ^ ((modulus >> i) & 1)
        return r

    root = next(x for x in range(2, 4096) if poly_at(x) == 0)
    cols = [pow_t(mul4096, root, i) for i in range(deg)]
    return tuple(cols), tuple(mat_inv(cols, deg))


# ---------------------------------------------------------------------------
# Rank-1 term lists.


@dataclasses.dataclass(frozen=True)
class Term:
    alpha: int  # form on X (bit i <-> X qubit i)
    beta: int  # form on Y
    gamma: int  # target bits


def _karatsuba3() -> list[tuple[int, int]]:
    """(alpha, beta) pairs of the 6-product Karatsuba for 3-coefficient polynomials."""
    singles = [1, 2, 4]
    pairs = [0b011, 0b101, 0b110]
    return [(s, s) for s in singles] + [(p, p) for p in pairs]


def _lift(pairs: list[tuple[int, int]], width: int) -> list[tuple[int, int]]:
    """Karatsuba over a degree-2 extension: products on (lo), (hi), (lo + hi) blocks."""
    out = []
    for a, b in pairs:
        out += [(a, b), (a << width, b << width), (a | a << width, b | b << width)]
    return out


def solve_gamma(pairs: list[tuple[int, int]], bilinear, n_x: int, n_y: int, n_out: int) -> list[Term]:
    """Find gamma_k so that sum_k gamma_k (alpha_k . x)(beta_k . y) == bilinear(x, y) on basis pairs."""
    k = len(pairs)
    eqs = []  # (row over k unknowns, rhs over n_out bits)
    for i, j in itertools.product(range(n_x), range(n_y)):
        row = sum((((a >> i) & 1) & ((b >> j) & 1)) << t for t, (a, b) in enumerate(pairs))
        eqs.append([row, bilinear(1 << i, 1 << j)])
    # Gaussian elimination, rhs carried as an int of n_out bits.
    pivots = []
    r = 0
    for c in range(k):
        piv = next((q for q in range(r, len(eqs)) if (eqs[q][0] >> c) & 1), None)
        if piv is None:
            continue
        eqs[r], eqs[piv] = eqs[piv], eqs[r]
        for q in range(len(eqs)):
            if q != r and (eqs[q][0] >> c) & 1:
                eqs[q][0] ^= eqs[r][0]
                eqs[q][1] ^= eqs[r][1]
        pivots.append(c)
        r += 1
    if any(row == 0 and rhs for row, rhs in eqs[r:]):
        raise ValueError('term set cannot express the bilinear map')
    gamma = [0] * k
    for q, c in enumerate(pivots):
        gamma[c] = eqs[q][1]
    terms = [Term(a, b, g) for (a, b), g in zip(pairs, gamma) if g]
    for i, j in itertools.product(range(n_x), range(n_y)):  # re-check
        acc = 0
        for t in terms:
            if (t.alpha >> i) & 1 and (t.beta >> j) & 1:
                acc ^= t.gamma
        assert acc == bilinear(1 << i, 1 << j)
    return terms


def mul_terms_std(modulus: int) -> list[Term]:
    """54 rank-1 terms for target ^= lhs * rhs in km's polynomial basis."""
    to_t, to_s = iso(modulus)
    tower_pairs = _lift(_lift(_karatsuba3(), 3), 6)
    tower_terms = solve_gamma(tower_pairs, mul4096, 12, 12, 12)
    return [Term(form_compose(t.alpha, list(to_t)), form_compose(t.beta, list(to_t)), mat_vec(list(to_s), t.gamma))
            for t in tower_terms]


def compose_x(terms: list[Term], cols: list[int]) -> list[Term]:
    return [Term(form_compose(t.alpha, cols), form_compose(t.beta, cols), t.gamma) for t in terms]


@dataclasses.dataclass(frozen=True)
class Step:
    """target ^= sum terms (X, Y) + linear(Z): `x`, `y`, `z` name registers; linear maps Z -> target."""
    target: str
    x: str
    y: str
    terms: tuple[Term, ...]
    z: str | None = None
    linear: tuple[int, ...] = ()  # columns: Z bit j -> target bits linear[j]


def inverse_steps(modulus: int) -> list[Step]:
    """Steps computing out = in^-1 (km polynomial basis in/out; tower-coordinate scaffold).

    Registers: 'in' (12, std), 'D' (6) = N(a), 'E' (3) = N(D), 'F' (3) = E^-1, 'G' (6) = D^-1,
    'out' (12, std). 0 maps to 0.
    """
    to_t, to_s = iso(modulus)
    k3 = _karatsuba3()
    k6 = _lift(k3, 3)
    sq8 = [mul8(1 << i, 1 << i) for i in range(3)]  # squaring GF(8) is linear
    sq64 = [mul64(1 << i, 1 << i) for i in range(6)]

    def lin_cols(f, n_in):
        return tuple(f(1 << j) for j in range(n_in))

    # D = a0 (a0 + a1) + nu2 a1^2, bilinear in (a, a) with a in tower coords.
    def d_bil(x, y):
        return mul64(x & 63, (y & 63) ^ (y >> 6))
    d_pairs = [(a, b | b << 6) for a, b in k6]  # alpha on a0 block, beta on (a0 + a1)
    d_terms = solve_gamma(d_pairs, d_bil, 12, 12, 6)
    d_lin = lin_cols(lambda x: mul64(NU2, mat_vec(sq64, x >> 6)), 12)
    # E = d0 (d0 + d1) + nu1 d1^2.
    e_pairs = [(a, b | b << 3) for a, b in k3]
    e_terms = solve_gamma(e_pairs, lambda x, y: mul8(x & 7, (y & 7) ^ (y >> 3)), 6, 6, 3)
    e_lin = lin_cols(lambda x: mul8(NU1, mat_vec(sq8, x >> 3)), 6)
    # F = E^6 = E^2 * E^4 (both linear in E).
    sq4 = [mat_vec(sq8, mat_vec(sq8, 1 << i)) for i in range(3)]
    f_pairs = [(form_compose(a, sq8), form_compose(b, sq4)) for a, b in k3]
    f_terms = solve_gamma(f_pairs, lambda x, y: mul8(mat_vec(sq8, x), mat_vec(sq4, y)), 3, 3, 3)
    # G = (d1 F) u + (d0 + d1) F: bilinear in (D, F).
    g_pairs = [(a << 3, b) for a, b in k3] + [(a | a << 3, b) for a, b in k3]
    g_terms = solve_gamma(g_pairs, lambda x, y: mul8((x & 7) ^ (x >> 3), y) | (mul8(x >> 3, y) << 3), 6, 3, 6)
    # out = (a1 G) v + (a0 + a1) G: bilinear in (a, G), then to std basis.
    o_pairs = [(a << 6, b) for a, b in k6] + [(a | a << 6, b) for a, b in k6]
    o_terms = solve_gamma(o_pairs, lambda x, y: mul64((x & 63) ^ (x >> 6), y) | (mul64(x >> 6, y) << 6), 12, 6, 12)

    t_cols = list(to_t)
    d_terms_std = compose_x([Term(t.alpha, t.beta, t.gamma) for t in d_terms], t_cols)
    d_terms_std = [Term(t.alpha, form_compose(dt.beta, t_cols), t.gamma) for t, dt in zip(d_terms_std, d_terms)]
    d_lin_std = tuple(mat_vec(list(d_lin), c) for c in t_cols)
    o_terms_std = [Term(form_compose(t.alpha, t_cols), t.beta, mat_vec(list(to_s), t.gamma)) for t in o_terms]
    return [
        Step('D', 'in', 'in', tuple(d_terms_std), 'in', d_lin_std),
        Step('E', 'D', 'D', tuple(e_terms), 'D', e_lin),
        Step('F', 'E', 'E', tuple(f_terms)),
        Step('G', 'D', 'F', tuple(g_terms)),
        Step('out', 'in', 'G', tuple(o_terms_std)),
    ]


REG_WIDTH = {'in': 12, 'D': 6, 'E': 3, 'F': 3, 'G': 6, 'out': 12}


def eval_steps(steps: list[Step], x: int) -> dict[str, int]:
    regs = {'in': x}
    for s in steps:
        acc = 0
        for t in s.terms:
            if (bin(t.alpha & regs[s.x]).count('1') & 1) and (bin(t.beta & regs[s.y]).count('1') & 1):
                acc ^= t.gamma
        if s.z is not None:
            acc ^= mat_vec(list(s.linear), regs[s.z])
        regs[s.target] = acc
    return regs


def toffoli_count(steps_or_terms) -> int:
    """Rank-1 terms that need a Toffoli (alpha == beta on the same register collapses to linear)."""
    if steps_or_terms and isinstance(steps_or_terms[0], Term):
        return len(steps_or_terms)
    return sum(sum(1 for t in s.terms if not (s.x == s.y and t.alpha == t.beta)) for s in steps_or_terms)


def self_test(modulus: int, km_field) -> dict:
    """Check mul terms on all basis pairs and the inverse chain on all 4096 inputs against kickmix."""
    terms = mul_terms_std(modulus)
    for i, j in itertools.product(range(12), range(12)):
        acc = 0
        for t in terms:
            if (t.alpha >> i) & 1 and (t.beta >> j) & 1:
                acc ^= t.gamma
        assert acc == km_field.mul(1 << i, 1 << j), (i, j)
    steps = inverse_steps(modulus)
    for x in range(4096):
        want = km_field.invert(x) if x else 0
        assert eval_steps(steps, x)['out'] == want, x
    return {'nu1': NU1, 'nu2': NU2, 'mul_toffolis': toffoli_count(terms),
            'inverse_toffolis': toffoli_count(steps),
            'inverse_steps': {s.target: toffoli_count([s]) for s in steps}}


if __name__ == '__main__':
    import json
    import sys
    sys.path.append(f'{sys.argv[1]}/kickmix')
    import kickmix as km
    f = km.GF2Field(12)
    print(json.dumps({'modulus': f.modulus, **self_test(f.modulus, f)}))
