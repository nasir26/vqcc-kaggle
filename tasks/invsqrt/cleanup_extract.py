"""Extract the table-cleanup obligations of the 64715b8c text (ours).
Region = text lines [L0, L1] (1-based). At region entry, every live wire that is a function of the 7-bit table
address idx = v >> 5 is tabulated over the 128 idx values. Inside the region, each conditional block's phase
(Z / CZ / NEG under PUSH_CONDITION if b) is accumulated as a function of idx per classical-bit version.
Output: data/work/inv_gen/cleanup.json"""
import sys, json, numpy as np
sys.path.insert(0, 'data/work/inv_gen/b0/invsqrt_build.pP3Dk2/tree/tools'); sys.path.insert(0, 'tasks/invsqrt')
import kmsim, syed_model as M
KMX, L0, L1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
text = open(KMX).read(); lines = text.splitlines(); ops, regs = kmsim.parse(text); ln = [o[4] for o in ops]
i0 = ln.index(L0); i1 = ln.index(L1)
ch = M.chart(); idx_all = (ch['v'] >> 5)
rng = np.random.default_rng(9); pos = np.sort(rng.choice(np.arange(M.MAX_X), 8192, replace=False))
xs = (pos + 1).astype(np.uint64); idx = idx_all[pos]
assert len(set(idx.tolist())) == 128
s = kmsim.Sim(ops, regs['x'], xs=xs, seed=4)
for i in range(i0): s.step(i)
def bits(v): return np.unpackbits(v.view(np.uint8), bitorder='little')[:s.n].astype(np.int64)
def tab(vals):
    t = [None] * 128
    for a, b in zip(idx, vals):
        if t[a] is None: t[a] = int(b)
        elif t[a] != int(b): return None
    return sum(b << a for a, b in enumerate(t) if b)
entry = {}
for w, v in s.state.items():
    if w.startswith('q'):
        tt = tab(bits(v))
        if tt is not None and bits(v).any(): entry[w] = tt
# walk the region symbolically over idx: wire -> truth (128-bit int) ; non-address wires untouched expected
state = dict(entry); FULL = (1 << 128) - 1
cond = []; version = {}; obligations = {}; hmr = []; ccx = []
def val(w): return state.get(w, 0)
for i in range(i0, i1 + 1):
    kind, args, c, ang, lno = ops[i][:5]
    if kind == 'PUSH_CONDITION': cond.append(args[0] if args else c); continue
    if kind == 'POP_CONDITION': cond.pop(); continue
    cb = [x for x in cond + ([c] if c else [])]
    if kind in ('Z', 'CZ', 'NEG', 'CCZ'):
        f = FULL
        for w in args: f &= val(w)
        assert len(cb) <= 1, (lno, cb)
        key = 'uncond' if not cb else f'{cb[0]}@{version.get(cb[0], 0)}'
        obligations[key] = obligations.get(key, 0) ^ f
        continue
    assert not cb, (lno, lines[lno - 1])
    if kind == 'CX': state[args[1]] = val(args[1]) ^ val(args[0])
    elif kind == 'X': state[args[0]] = val(args[0]) ^ FULL
    elif kind == 'CCX': state[args[2]] = val(args[2]) ^ (val(args[0]) & val(args[1])); ccx.append((lno, args))
    elif kind == 'SWAP': state[args[0]], state[args[1]] = val(args[1]), val(args[0])
    elif kind == 'HMR':
        b = args[1]; version[b] = version.get(b, 0) + 1
        hmr.append(dict(line=lno, wire=args[0], bit=f'{b}@{version[b]}', value=str(val(args[0])))); state[args[0]] = 0
    else: raise AssertionError((kind, lno))
# HMR debt: bit b@k must be paid with phase = wire value at HMR. Check consistency for in-region HMRs.
bad = [h for h in hmr if obligations.get(h['bit'], 0) != int(h['value'])]
print('entry address wires', len(entry), 'HMRs', len(hmr), 'CCX', len(ccx), 'obligation keys', len(obligations), 'in-region HMR mismatches', len(bad))
pre = {k: str(v) for k, v in obligations.items() if k not in {h['bit'] for h in hmr}}
print('pre-region bits paid here:', len(pre), 'uncond' in pre)
final = {w: str(v) for w, v in state.items() if v}
json.dump(dict(entry={k: str(v) for k, v in entry.items()}, hmr=hmr, pre=pre, final=final, L0=L0, L1=L1,
               ccx=[l for l, _ in ccx]), open('data/work/inv_gen/cleanup.json', 'w'))
