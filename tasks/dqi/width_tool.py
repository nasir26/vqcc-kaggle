"""Width-cut analysis on a dqi kmx circuit (uses affine_track.Tracker).

runs:  python tasks/dqi/width_tool.py runs circuit.kmx PEAK runs.json
       maximal runs of ops where the number of nonzero qubits is >= PEAK, with the wires that stay untouched
       (dormant) and nonzero through each run; also the global/section peaks and the work-wire peak.
rel:   python tasks/dqi/width_tool.py rel circuit.kmx runs.json rel.json
       at each run's pre point (before its first op) and post point (after its last op), find for every dormant
       wire a set of other live wires (+ constant, index 892) whose XOR equals it (1024-bit signatures).
"""
import sys, json, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from affine_track import Tracker

def lines(fin):
    with open(fin) as f:
        for ln, line in enumerate(f, 1):
            yield ln, line.split()

def cmd_runs(fin, PEAK, fout):
    T = Tracker(W=64)
    nz = 0; peak = 0; secpeak = collections.Counter(); workpeak = 0
    runs = []; inrun = False; touched = set(); runstart = 0
    for ln, p in lines(fin):
        if p and p[0] == 'APPEND_TO_REGISTER' and p[1][0] == 'q':
            T.step(p); nz += 1; continue
        qs = None
        if p and p[0] not in ('INFO_TAG', 'PUSH_CONDITION', 'POP_CONDITION', 'REGISTER', 'APPEND_TO_REGISTER'):
            qs0 = [int(x[1:]) for x in p[1:] if x[0] == 'q']
            before = sum(1 for x in set(qs0) if T.nonzero(x))
            qs = T.step(p)
            after = sum(1 for x in set(qs0) if T.nonzero(x))
            nz += after - before
        else:
            T.step(p); continue
        if inrun: touched.update(qs)
        if nz > peak: peak = nz
        if nz > secpeak[T.section]: secpeak[T.section] = nz
        if nz >= PEAK and not inrun:
            inrun = True; runstart = ln; touched = set(qs)
        elif nz < PEAK and inrun:
            inrun = False
            live = [i for i in range(892) if T.nonzero(i) and i not in touched]
            runs.append(dict(start=runstart, end=ln, section=T.section, dormant=live))
    json.dump(runs, open(fout, 'w'))
    print('peak', peak, 'sections', dict(secpeak))
    print('runs', len(runs), 'with dormant work wire', sum(1 for r in runs if any(d >= 840 for d in r['dormant'])),
          'with any dormant', sum(1 for r in runs if r['dormant']))

def cmd_rel(fin, frun, fout):
    runs = json.load(open(frun))
    T = Tracker(W=1024, seed=99)
    W = T.W; ONE = 1 << W
    pre = collections.defaultdict(list); post = collections.defaultdict(list)
    for k, r in enumerate(runs): pre[r['start']].append(k); post[r['end']].append(k)
    def relations(cands):
        live = [i for i in range(892) if T.nonzero(i)]
        order = [i for i in live if i not in cands] + [i for i in live if i in cands]
        basis = {}; out = {}
        vecs = [(ONE, 1 << 892)] + [(T.sig[i] | (T.cst[i] << W), 1 << i) for i in order]
        for v, c in vecs:
            while v:
                pb = v.bit_length() - 1
                if pb in basis: bv, bc = basis[pb]; v ^= bv; c ^= bc
                else: basis[pb] = (v, c); break
            if v == 0:
                for q in cands:
                    if q not in out and (c >> q) & 1:
                        out[q] = [j for j in range(893) if (c >> j) & 1 and j != q]
        return {str(q): out.get(q) for q in cands}
    res = [dict(start=r['start'], end=r['end'], section=r['section'], pre=None, post=None) for r in runs]
    last = max(r['end'] for r in runs)
    for ln, p in lines(fin):
        if ln > last: break
        if ln in pre:
            for k in pre[ln]:
                res[k]['pre'] = relations(set(runs[k]['dormant'])) if T.depth == 0 else 'cond'
        T.step(p)
        if ln in post:
            for k in post[ln]:
                res[k]['post'] = relations(set(runs[k]['dormant'])) if T.depth == 0 else 'cond'
    json.dump(res, open(fout, 'w'))
    ok = 0
    for r in res:
        if isinstance(r['pre'], dict) and isinstance(r['post'], dict):
            if any(r['pre'][q] is not None and r['post'].get(q) is not None for q in r['pre']): ok += 1
    print('runs', len(res), 'spillable (affine at both ends):', ok)

if __name__ == '__main__':
    if sys.argv[1] == 'runs': cmd_runs(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else: cmd_rel(sys.argv[2], sys.argv[3], sys.argv[4])
