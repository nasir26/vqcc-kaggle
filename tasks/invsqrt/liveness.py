"""Per-qubit liveness map: for each chunk of the kmx body, which qubits are nonzero in any sampled shot.
Prints a character map (rows = qubits, columns = chunks). Usage: liveness.py FILE [chunk_ops]"""
import sys, io, numpy as np
sys.path.append('/home/qacc/jsc_revision_2026/vqcc_kaggle/repo/data/comp/kickmix')
import kickmix as km
X_MAX = 3 * (2**10 - 2)**2
path = sys.argv[1]; chunk = int(sys.argv[2]) if len(sys.argv) > 2 else 250
c = km.Circuit.from_file(path); buf = io.BytesIO(); c.to_file(buf, format='kmx')
lines = buf.getvalue().decode().splitlines()
hdr = [l for l in lines if l.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
body = [l for l in lines if l and not l.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
chunks, cur, depth = [], [], 0
for l in body:
    cur.append(l); depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
    if depth == 0 and len(cur) >= chunk: chunks.append(cur); cur = []
if cur: chunks.append(cur)
B = 1024; rng = np.random.default_rng(1)
xs = np.concatenate([np.arange(1, 1025), rng.integers(1, X_MAX + 1, B)]).astype(np.uint64)
sims = []
for i in range(len(xs) // B):
    sim = km.Simulator(batch_size=B, debug_print=False, counting_operations=True, seed=9 + i)
    sl = xs[i*B:(i+1)*B]
    sim.write_across_shots(km.array([km.q(q) for q in xq]), ((sl[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
    sims.append(sim)
allq = km.array([km.q(i) for i in range(c.num_qubits)])
M = []
pos = 0; starts = []
for ch in chunks:
    part = km.Circuit('\n'.join(ch)); alive = np.zeros(c.num_qubits, dtype=bool)
    for sim in sims:
        sim.do(part); alive |= sim.read_across_shots(allq).any(axis=1)
    M.append(alive); starts.append(pos); pos += len(ch)
M = np.array(M).T
print('cols:', len(chunks), 'chunk', chunk)
print('     ' + ''.join(str((s // 1000) % 10) if i % 4 == 0 else ' ' for i, s in enumerate(starts)))
for q in range(c.num_qubits):
    print(f'q{q:<3d} ' + ''.join('#' if v else '.' for v in M[q]))
print('live ' + ''.join(chr(ord('0') + min(int(v) - 40, 40)) if v >= 40 else '_' for v in M.sum(0)))
