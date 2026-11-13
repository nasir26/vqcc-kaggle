"""Helpers: run a prefix of a kmx body on a batch of x and return all qubit values."""
import sys, io, numpy as np
sys.path.append('/home/qacc/jsc_revision_2026/vqcc_kaggle/repo/data/comp/kickmix')
import kickmix as km
X_MAX = 3 * (2**10 - 2)**2

def load(path):
    c = km.Circuit.from_file(path); buf = io.BytesIO(); c.to_file(buf, format='kmx')
    lines = buf.getvalue().decode().splitlines()
    hdr = [l for l in lines if l.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    body = [l for l in lines if l and not l.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    return c, hdr, body

def run(hdr, body, xs, nq, upto=None, seed=1):
    xs = np.asarray(xs, dtype=np.uint64)
    sim = km.Simulator(batch_size=len(xs), debug_print=False, counting_operations=True, seed=seed)
    xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
    sim.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
    part = body if upto is None else body[:upto]
    sim.do(km.Circuit('\n'.join(part)))
    bits = sim.read_across_shots(km.array([km.q(i) for i in range(nq)]))
    return sim, bits
