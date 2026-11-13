"""At given cuts, find live qubits that equal a 2-input nonlinear function (AND-type, incl. negations, XOR'd with a
linear combination is not tested) of two other live qubits, or a MAJ of three."""
import sys; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; cuts = [int(v) for v in sys.argv[2].split(',')]
c, hdr, body = load(path)
rng = np.random.default_rng(9)
xs = np.concatenate([rng.integers(1, X_MAX + 1, 3000), np.arange(1, 1001)]).astype(np.uint64)
for L in cuts:
    sim, bits = run(hdr, body, xs, c.num_qubits, upto=L)
    live = [q for q in range(c.num_qubits) if bits[q].any() and not bits[q].all()]
    V = bits.astype(bool)
    found = []
    for q in live:
        t = V[q]
        hit = None
        for i in live:
            if i == q or hit: continue
            for j in live:
                if j <= i or j == q: continue
                a, b = V[i], V[j]
                for na in (0, 1):
                    for nb in (0, 1):
                        f = (a ^ bool(na)) & (b ^ bool(nb))
                        if np.array_equal(t, f) or np.array_equal(t, ~f): hit = (i, j, na, nb); break
                    if hit: break
                if hit: break
        if hit: found.append((q, hit))
    print('cut', L, 'live', len(live), 'quadratic-redundant:', found)
