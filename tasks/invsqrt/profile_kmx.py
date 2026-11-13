"""Time profile of an invsqrt circuit: per chunk of the kmx body, mean executed Toffolis, live qubits
(nonzero in any shot after the chunk), Z_POW count. Usage: profile_kmx.py FILE [chunk_ops]"""
import sys, io, numpy as np
sys.path.append('/home/qacc/jsc_revision_2026/vqcc_kaggle/repo/data/comp/kickmix')
import kickmix as km
X_MAX = 3 * (2**10 - 2)**2

def load_lines(path):
    c = km.Circuit.from_file(path)
    buf = io.BytesIO(); c.to_file(buf, format='kmx')
    return c, buf.getvalue().decode().splitlines()

def chunks_of(body, chunk_ops):
    out, cur, depth = [], [], 0
    for i, l in enumerate(body):
        cur.append((i, l))
        depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
        brk = depth == 0 and (len(cur) >= chunk_ops or l.startswith('Z_POW'))
        if brk:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def main():
    path = sys.argv[1]; chunk_ops = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    c, lines = load_lines(path)
    hdr = [l for l in lines if l.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    body = [l for l in lines if l and not l.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
    B = 1024
    rng = np.random.default_rng(0)
    xs = np.concatenate([np.arange(1, 1025), rng.integers(1, X_MAX + 1, 3 * B)]).astype(np.uint64)
    sims = []
    for i in range(len(xs) // B):
        sim = km.Simulator(batch_size=B, debug_print=False, counting_operations=True, seed=5 + i)
        sl = xs[i*B:(i+1)*B]
        sim.write_across_shots(km.array([km.q(q) for q in xq]), ((sl[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
        sims.append(sim)
    allq = km.array([km.q(i) for i in range(c.num_qubits)])
    tot = 0
    for ch in chunks_of(body, chunk_ops):
        part = km.Circuit('\n'.join(l for _, l in ch)); t = 0
        alive = np.zeros(c.num_qubits, dtype=bool)
        for sim in sims:
            sim.clear_operation_statistics(); sim.do(part)
            t += int(sim.operation_statistics().num_toffoli_like)
            alive |= sim.read_across_shots(allq).any(axis=1)
        t /= len(xs); tot += t
        nz = sum(l.startswith('Z_POW') for _, l in ch)
        st = sum(l.split()[0] in ('CCX', 'CCZ', 'CSWAP') for _, l in ch)
        print(f'{ch[0][0]:6d}-{ch[-1][0]:6d} toff {t:7.2f} static {st:4d} cum {tot:8.2f} live {int(alive.sum()):3d} zpow {nz} '
              + ('' if nz == 0 else ' '.join(l for _, l in ch if l.startswith('Z_POW'))))
main()
