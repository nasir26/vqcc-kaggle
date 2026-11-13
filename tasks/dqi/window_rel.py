"""For uncovered peak runs, look for an affine restore relation anywhere in the dormancy window after the run.

Pass 1 (cheap): next touch line of every dormant wire after each run's end. Pass 2 (1024-bit tracker): at up to
NPTS checkpoints in [end, max next touch), test which still-untouched dormant wires lie in the span of the other
live wires. A hit means the wire can be HMR-erased before the run and CX-restored at that checkpoint (0 T).
usage: python tasks/dqi/window_rel.py circuit.kmx runs.json rel.json section out.json [NPTS]
"""
import sys, json, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from affine_track import Tracker
fin, frun, frel, sec, fout = sys.argv[1:6]
NPTS = int(sys.argv[6]) if len(sys.argv) > 6 else 8
runs = json.load(open(frun)); rel = json.load(open(frel))
def covered(x):
    return isinstance(x['post'], dict) and any(v is not None for v in x['post'].values())
todo = [k for k, r in enumerate(runs) if r['section'] == sec and not covered(rel[k])]
print('uncovered runs in', sec, len(todo), flush=True)
first, last = min(runs[k]['end'] for k in todo), 0
pend = collections.defaultdict(list)  # wire -> runs waiting for next touch
nxt = {k: {} for k in todo}
starts = collections.defaultdict(list)
for k in todo: starts[runs[k]['end']].append(k)
with open(fin) as f:
    for ln, line in enumerate(f, 1):
        if ln > first:
            p = line.split()
            for x in p[1:]:
                if x[0] == 'q':
                    w = int(x[1:])
                    if w in pend:
                        for k in pend.pop(w): nxt[k][w] = ln
        if ln in starts:
            for k in starts[ln]:
                for w in runs[k]['dormant']: pend[w].append(k)
        if ln > first and not pend and ln > max(runs[k]['end'] for k in todo): break
checks = collections.defaultdict(list)
for k in todo:
    e = runs[k]['end']; m = max(nxt[k].values()) if nxt[k] else e + 1
    span = m - e
    pts = sorted(set([e] + [e + int(span * (i / NPTS) ** 2) for i in range(1, NPTS)]))
    for t in pts: checks[t].append(k)
last = max(checks)
T = Tracker(W=1024, seed=99); W = T.W; ONE = 1 << W
found = {}
def nullrel(cands):
    live = [i for i in range(892) if T.nonzero(i)]
    order = [i for i in live if i not in cands] + [i for i in live if i in cands]
    basis = {}; out = {}
    for v, c in [(ONE, 1 << 892)] + [(T.sig[i] | (T.cst[i] << W), 1 << i) for i in order]:
        while v:
            pb = v.bit_length() - 1
            if pb in basis: bv, bc = basis[pb]; v ^= bv; c ^= bc
            else: basis[pb] = (v, c); break
        if v == 0:
            for q in cands:
                if q not in out and (c >> q) & 1: out[q] = [j for j in range(893) if (c >> j) & 1 and j != q]
    return out
with open(fin) as f:
    for ln, line in enumerate(f, 1):
        if ln > last: break
        T.step(line.split())
        if ln in checks and T.depth == 0:
            for k in checks[ln]:
                if k in found: continue
                c = {w for w, t in nxt[k].items() if t > ln}
                if not c: continue
                r = nullrel(c)
                if r:
                    q = min(r, key=lambda x: len(r[x])); found[k] = dict(line=ln, q=q, rel=r[q])
json.dump({str(k): v for k, v in found.items()}, open(fout, 'w'))
print('found', len(found), 'of', len(todo))
