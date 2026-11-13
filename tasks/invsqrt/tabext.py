import sys; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; L = int(sys.argv[2])
c, hdr, body = load(path)
# one representative x per (parity, a7): x = M >> sp with sp in {0,1}; use large x with low bits 0 / random
rows = []
for par in (0, 1):
    for a in range(128):
        M = (1 << 21) | (a << 14) | 0x1555
        sp = 2 + par   # shift 2 or 3 => x = M >> sp
        rows.append(M >> sp)
xs = np.array(rows * 4, dtype=np.uint64)
sim, bits = run(hdr, body, xs, c.num_qubits, upto=L)
B = bits[:, :256].astype(int)
np.save('/tmp/claude-1011/-home-qacc-jsc-revision-2026/252d475f-0b17-45d4-be26-4edc4a122a3f/scratchpad/tab7180.npy', B)
for q in range(c.num_qubits):
    v = B[q]
    if not v.any(): continue
    t0 = int(np.abs(np.diff(v[:128])).sum()); t1 = int(np.abs(np.diff(v[128:])).sum())
    print(f'q{q}: trans e0 {t0:3d} e1 {t1:3d}  ', ''.join(map(str, v[:128:2])), '|', ''.join(map(str, v[128::2])))
