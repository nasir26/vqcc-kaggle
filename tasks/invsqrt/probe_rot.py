"""Probe the bit under every Z_POW of an invsqrt circuit: copies it into a fresh qubit right before the rotation."""
import sys, numpy as np
sys.path.insert(0, '.')
from kmxsim import *
from fractions import Fraction

def probe(path, xs, seed=1):
    c, hdr, body = load(path)
    nq = c.num_qubits; out = []; angles = []
    for l in body:
        if l.startswith('Z_POW'):
            p = l.split(); q = p[1]
            out.append(f'CX {q} q{nq + len(angles)}'); angles.append((q, Fraction(p[2]) if '/' in p[2] else Fraction(p[2])))
        out.append(l)
    nP = len(angles)
    sim, bits = run(hdr, out, xs, nq + nP, seed=seed)
    return angles, bits[nq:nq + nP]

if __name__ == '__main__':
    rng = np.random.default_rng(0)
    xs = np.concatenate([np.arange(1, 2049), rng.integers(1, X_MAX, 2048)])
    angles, P = probe(sys.argv[1], xs)
    for i, (q, a) in enumerate(angles):
        print(i, q, float(a), P[i, :2048].mean(), P[i, 2048:].mean())
