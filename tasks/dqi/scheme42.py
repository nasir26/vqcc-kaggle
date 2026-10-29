"""Rank-42 bilinear scheme for GF(2^12) multiplication in kickmix's polynomial basis (modulus 4179), own code.

GF(2^12) = GF(8)[t]/(minimal polynomial of a primitive element theta over GF(8)): x = sum_j x_j theta^j, j < 4.
x * y = z(theta) with z = x(t) y(t) of degree <= 6, fixed by its values at 6 points of GF(8) and its leading
coefficient (the point at infinity): 7 products in GF(8), each 6 ANDs on 3-bit linear forms. The output vectors
are solved by Gaussian elimination (tower.solve_gamma) and the scheme is checked on all basis pairs.
Writes the scheme as "a,b,c" hex triples for `flipgraph ... -i FILE`.

usage: python tasks/dqi/scheme42.py OUT.txt
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tower  # noqa: E402

MOD = 4179
N = 12


def mul(a, b, mod=MOD, n=N):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if a >> n:
            a ^= mod
    return r


def power(a, e):
    r = 1
    while e:
        if e & 1:
            r = mul(r, a)
        a = mul(a, a)
        e >>= 1
    return r


def main():
    sub = [g for g in range(1 << N) if power(g, 8) == g]
    assert len(sub) == 8
    g8 = next(g for g in sub if mul(mul(g, g), g) ^ g ^ 1 == 0)        # root of t^3 + t + 1, as tower.mul8 uses
    emb = [1, g8, mul(g8, g8)]
    theta = next(t for t in range(2, 1 << N) if all(power(t, 4095 // p) != 1 for p in (3, 5, 7, 13)))
    cols = [mul(emb[i], power(theta, j)) for j in range(4) for i in range(3)]   # coordinate i + 3 j -> element
    inv = tower.mat_inv(cols, 12)                                        # element bits -> coordinates

    def eval_cols(p):
        """Columns of the GF(2)-linear map coordinates -> x(p) in GF(8) (p None: leading coefficient)."""
        out = []
        for bit in range(12):
            i, j = bit % 3, bit // 3
            if p is None:
                out.append((1 << i) if j == 3 else 0)
            else:
                pj = 1
                for _ in range(j):
                    pj = tower.mul8(pj, p)
                out.append(tower.mul8(1 << i, pj))
        return out

    pairs = []
    for p in [1, 2, 3, 4, 5, 6, None]:
        ec = eval_cols(p)
        for m3 in (1, 2, 4, 3, 5, 6):
            form_coords = sum((bin(m3 & ec[bit]).count('1') & 1) << bit for bit in range(12))
            form = tower.form_compose(form_coords, list(inv))
            pairs.append((form, form))
    terms = tower.solve_gamma(pairs, mul, 12, 12, 12)
    for i in range(12):
        for j in range(12):
            acc = 0
            for t in terms:
                if (t.alpha >> i) & 1 and (t.beta >> j) & 1:
                    acc ^= t.gamma
            assert acc == mul(1 << i, 1 << j)
    pathlib.Path(sys.argv[1]).write_text(' '.join(f'{t.alpha:x},{t.beta:x},{t.gamma:x}' for t in terms) + '\n')
    print(f'rank {len(terms)} scheme verified on all basis pairs, written to {sys.argv[1]}')


if __name__ == '__main__':
    main()
