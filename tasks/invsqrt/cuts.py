"""Find clean cuts (empty condition stack, no classical bit written before and read after) and fingerprint the
qubit state there over a sample of x. Pairs of cuts with equal states delimit phase-only blocks."""
import sys, re, hashlib; sys.path.insert(0, '.')
import numpy as np
from kmxsim import *
path = sys.argv[1]; step = int(sys.argv[2]) if len(sys.argv) > 2 else 50
c, hdr, body = load(path)
n = len(body)
# classical bit write/read positions
first_read_after = {}
writes = {}; reads = {}
for i, l in enumerate(body):
    for b in re.findall(r'\bb(\d+)\b', l):
        b = int(b)
        tok = l.split()[0]
        is_write = (tok in ('HMR',) and l.split()[2] == f'b{b}') or tok.startswith('BIT_STORE') and l.split()[1] == f'b{b}' or tok == 'BIT_INVERT' and l.split()[1] == f'b{b}'
        if is_write: writes.setdefault(b, []).append(i)
        if not (tok == 'HMR') and (' if ' in l or tok in ('PUSH_CONDITION',) or tok.startswith('BIT_')):
            reads.setdefault(b, []).append(i)
# cut at position p (before body[p]) is clean if depth 0 and for all bits: no (write < p and read >= p) with that write being the live value
depth = 0; clean = []
for p in range(n + 1):
    if p % step == 0 and depth == 0:
        ok = True
        for b, ws in writes.items():
            w_before = [w for w in ws if w < p]
            if not w_before: continue
            rs = [r for r in reads.get(b, []) if r >= p]
            ws_after = [w for w in ws if w >= p]
            if rs and (not ws_after or min(rs) <= min(ws_after)):
                ok = False; break
        if ok: clean.append(p)
    if p < n:
        l = body[p]; depth += l.startswith('PUSH_CONDITION') - l.startswith('POP_CONDITION')
print('clean cuts', len(clean))
rng = np.random.default_rng(5)
xs = np.concatenate([np.arange(1, 1025), rng.integers(1, X_MAX + 1, 3072)]).astype(np.uint64)
sim = km.Simulator(batch_size=len(xs), debug_print=False, seed=3)
xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
sim.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
allq = km.array([km.q(i) for i in range(c.num_qubits)])
prev = 0; fps = {}
for p in clean:
    if p > prev: sim.do(km.Circuit('\n'.join(body[prev:p]))); prev = p
    st = sim.read_across_shots(allq)
    h = hashlib.sha1(np.packbits(st).tobytes()).hexdigest()[:10]
    fps.setdefault(h, []).append(p)
    live = int(st.any(axis=1).sum())
    print(p, h, live)
print('repeated states:')
for h, ps in fps.items():
    if len(ps) > 1 and ps[-1] - ps[0] > 200: print(h, ps[0], ps[-1], len(ps))
