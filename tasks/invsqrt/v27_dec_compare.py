"""Compare the address-decoder inputs of efd84ca5 with dcde7078 (ours): truth tables over the 7-bit table index
idx = v >> 5 of every wire at decoder entry/exit, and GF(2) span comparison."""
import sys
import numpy as np
sys.path.insert(0, '.')
from kmxsim import km, load, X_MAX
import syed_model as M

ch = M.chart(); IDX = (ch['v'] >> 5)
rng = np.random.default_rng(9)
pos = np.sort(rng.choice(np.arange(M.MAX_X), 8192, replace=False))
xs = (pos + 1).astype(np.uint64); idx = IDX[pos]


def tabs(path, L0, L1):
    c, hdr, body = load(path)
    nh = len(hdr)
    i0, i1 = L0 - 1 - nh, L1 - nh
    xq = [int(l.split()[1][1:]) for l in hdr if l.startswith('APPEND')]
    sim = km.Simulator(batch_size=len(xs), debug_print=False, seed=4)
    sim.write_across_shots(km.array([km.q(q) for q in xq]), ((xs[None, :] >> np.arange(22, dtype=np.uint64)[:, None]) & 1) == 1)
    allq = km.array([km.q(i) for i in range(c.num_qubits)])
    sim.do(km.Circuit('\n'.join(body[:i0]))); a = sim.read_across_shots(allq)
    sim.do(km.Circuit('\n'.join(body[i0:i1]))); b = sim.read_across_shots(allq)

    def tab(v):
        t = [None] * 128
        for k, bit in zip(idx, v):
            if t[k] is None: t[k] = int(bit)
            elif t[k] != int(bit): return None
        return sum(bb << k for k, bb in enumerate(t) if bb)
    ent = {q: tab(a[q]) for q in range(c.num_qubits) if a[q].any()}
    ext = {q: tab(b[q]) for q in range(c.num_qubits) if b[q].any()}
    return ent, ext, c.num_qubits, body[i0:i1]


def span(vs):
    p = {}
    for x in vs:
        while x:
            h = x.bit_length() - 1
            if h in p: x ^= p[h]
            else: p[h] = x; break
    return p


def inspan(p, x):
    while x:
        h = x.bit_length() - 1
        if h not in p: return False
        x ^= p[h]
    return True


FULL = (1 << 128) - 1
if __name__ == '__main__':
    R = {}
    for name, path, L0, L1 in [('dc', '../../data/work/inv_gen/dc/dc.kmx', 20584, 20923),
                               ('efd', '../../data/work/inv_gen/v27/efd.kmx', 17882, 18181)]:
        ent, ext, nq, blk = tabs(path, L0, L1)
        ch_ = [q for q in ext if ent.get(q) != ext.get(q)]
        fun_in = {q: v for q, v in ent.items() if v is not None}
        print(name, 'live in', len(ent), 'idx-functions in', len(fun_in), 'changed wires', ch_,
              'CCX', sum(l.startswith('CCX') for l in blk))
        R[name] = (fun_in, {q: ext[q] for q in ch_}, ent)
    coord = [sum(1 << a for a in range(128) if a >> s & 1) for s in range(7)]
    for name in R:
        fin, outs, _ = R[name]
        sp = span(list(fin.values()) + [FULL])
        print(name, 'dim span(inputs+1)', len(sp), 'address bits in span:', [s for s in range(7) if inspan(sp, coord[s])],
              'outputs are coords:', {q: [s for s in range(7) if v == coord[s]] for q, v in outs.items() if v is not None})
    a = span(list(R['dc'][0].values()) + [FULL]); b = span(list(R['efd'][0].values()) + [FULL])
    print('efd inputs in span(dc inputs):', sum(inspan(a, v) for v in R['efd'][0].values()), '/', len(R['efd'][0]))
    print('dc inputs in span(efd inputs):', sum(inspan(b, v) for v in R['dc'][0].values()), '/', len(R['dc'][0]))
