"""Symbolic extraction of an ANGLE_k loader into (cache monomials, products, linear part) over formal atoms.

Every qubit holds a GF(2) linear combination of atoms (python int bitmask over atom ids):
  atom 0 = constant 1, atoms 1..n_sel = selection bits, then the incoming word bits z (J*brot), then one atom per
  Toffoli result (cache monomial or product), in circuit order.
CX t ^= c, X adds the constant, SWAP swaps, CCX on a fresh |0> target creates a cache atom, CCX on a live target
creates a product atom p = form(a) * form(b) XORed into the target. HMR/R/CZ (measurement uncompute) are skipped.

The loader's function is then  delta_j = form(word_j at end) - z_j , a combination of atoms. Products whose forms
contain earlier product atoms are flagged (nested), since they are not trilinear over the base atoms.

Usage: python tasks/dfthcsos/loader/extract.py LOADER.kmb NPZ k  (checks against the table, prints statistics)
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path += [str(REPO / 'data/comp/kickmix'), str(pathlib.Path(__file__).parent)]
QRE = re.compile(r'\bq(\d+)\b')


def load_ops(path):
    import kickmix as km
    import tempfile
    c = km.Circuit.from_file(str(path))
    with tempfile.NamedTemporaryFile('w+', suffix='.kmx', delete=False) as f:
        tmp = f.name
    c.to_file(tmp, format='kmx')
    lines = pathlib.Path(tmp).read_text().split('\n')
    pathlib.Path(tmp).unlink()
    regs = {}
    cur = []
    for l in lines:
        if l.startswith('APPEND_TO_REGISTER'):
            cur.append(int(l.split()[1][1:]))
        elif l.startswith('REGISTER'):
            name = l.split('"')[1]
            regs[name] = cur
            cur = []
    ops = [l for l in lines if l and not l.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    return regs, ops, c.num_qubits


def extract(path):
    regs, ops, nq = load_ops(path)
    sel = regs['selection']
    words = [regs[f'word_{j}'] for j in range(len([r for r in regs if r.startswith('word_')]))]
    brot = len(words[0])
    zq = [q for w in words for q in w]
    atoms = ['1'] + [f's{i}' for i in range(len(sel))] + [f'z{i}' for i in range(len(zq))]
    state = {q: 0 for q in range(nq)}
    for i, q in enumerate(sel):
        state[q] = 1 << (1 + i)
    for i, q in enumerate(zq):
        state[q] = 1 << (1 + len(sel) + i)
    nbase = len(atoms)
    cache, products = [], []  # (atom id, form_a, form_b)  /  (atom id, form_a, form_b, target qubit)
    nested = 0
    for l in ops:
        parts = l.split()
        op = parts[0]
        if ' if ' in l or op in ('HMR', 'R', 'CZ', 'Z', 'CCZ', 'PUSH_CONDITION', 'POP_CONDITION', 'NEG'):
            if op == 'R':
                state[int(parts[1][1:])] = 0
            continue
        qs = list(map(int, QRE.findall(l)))
        if op == 'CX':
            state[qs[1]] ^= state[qs[0]]
        elif op == 'X':
            state[qs[0]] ^= 1
        elif op == 'SWAP':
            state[qs[0]], state[qs[1]] = state[qs[1]], state[qs[0]]
        elif op == 'CCX':
            a, b, t = state[qs[0]], state[qs[1]], state[qs[2]]
            aid = len(atoms)
            if t == 0 and qs[2] not in zq:
                atoms.append(f'c{len(cache)}')
                cache.append((aid, a, b))
            else:
                atoms.append(f'p{len(products)}')
                products.append((aid, a, b, qs[2]))
                if (a | b) >> (nbase + len(cache)) and any(((a | b) >> pa[0]) & 1 for pa in products[:-1]):
                    nested += 1
            state[qs[2]] ^= 1 << aid
        else:
            raise ValueError(f'unhandled op {l}')
    out = [state[q] ^ (1 << (1 + len(sel) + i)) for i, q in enumerate(zq)]
    return dict(atoms=atoms, nbase=nbase, cache=cache, products=products, out=out, sel=sel, zq=zq, brot=brot,
                J=len(words), nested=nested)


def evaluate(ex, A, z_bits):
    """Value of every atom on addresses 0..A-1 (bool arrays). z_bits (A, J*brot) incoming words."""
    nsel = len(ex['sel'])
    vals = [np.ones(A, bool)]
    a = np.arange(A)
    vals += [((a >> i) & 1).astype(bool) for i in range(nsel)]
    vals += [z_bits[:, i].astype(bool) for i in range(z_bits.shape[1])]

    def form(m):
        v = np.zeros(A, bool)
        i = 0
        while m:
            if m & 1:
                v ^= vals[i]
            m >>= 1
            i += 1
        return v
    events = sorted([(c[0], c[1], c[2]) for c in ex['cache']] + [(p[0], p[1], p[2]) for p in ex['products']])
    for aid, fa, fb in events:
        assert aid == len(vals)
        vals.append(form(fa) & form(fb))
    return np.array([form(m) for m in ex['out']]).T, vals


def main():
    import tensor as Tn
    path, npz, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
    ex = extract(path)
    w = np.load(npz)['angle_words']
    J, brot = ex['J'], ex['brot']
    B = Tn.batches(w, J, brot)
    D = Tn.deltas(w, J, brot)
    z = B[k - 1] if k > 0 else np.zeros_like(B[0])
    got, _ = evaluate(ex, w.shape[0], z)
    ok = np.array_equal(got.astype(np.uint8), D[k])
    print(f'k {k}: cache {len(ex["cache"])}, products {len(ex["products"])}, nested {ex["nested"]}, '
          f'reproduces delta table: {ok}, mismatching bits {int((got.astype(np.uint8) != D[k]).sum())}')


if __name__ == '__main__':
    main()
