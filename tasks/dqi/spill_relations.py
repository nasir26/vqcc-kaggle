"""Pass B of the width cut: find affine spill relations for dormant wires at peak-run boundaries.

Tracks every wire's value as an affine form over atoms with wide (1024-bit) random signatures, so a GF(2)
linear relation among live wires found by elimination is real with overwhelming probability. At each run's
'pre' point (before its first op) and 'post' point (after its last op) it computes, for each dormant
candidate wire, a set of other live wires (plus optional constant) whose XOR equals it.
usage: python tasks/dqi/spill_relations.py circuit.kmx runs.json out.json [max_runs]
"""
import sys, json, random, collections
fin, frun, fout = sys.argv[1], sys.argv[2], sys.argv[3]
runs = json.load(open(frun))
if len(sys.argv) > 4: runs = runs[:int(sys.argv[4])]
W = 1024
rng = random.Random(99)
def R(): return rng.getrandbits(W) | 1
NQ, NB = 4096, 400000
sig = [0] * NQ; cst = [0] * NQ; bsig = [0] * NB; bcst = [0] * NB
patoms = {}
def prodsig(sa, ca, sb, cb):
    if sa == 0: return (sb if ca else 0), ca & cb
    if sb == 0: return (sa if cb else 0), ca & cb
    if sa == sb: return (sa if (1 ^ ca ^ cb) else 0), ca & cb
    u, v, _ = sorted((sa, sb, sa ^ sb)); Wd = u ^ v
    P = patoms.get((u, v))
    if P is None: P = patoms[(u, v)] = R()
    s = P; pair = {sa, sb}
    if pair == {u, Wd}: s ^= u
    elif pair == {v, Wd}: s ^= v
    if cb: s ^= sa
    if ca: s ^= sb
    return s, ca & cb
pre = collections.defaultdict(list); post = collections.defaultdict(list)
for k, r in enumerate(runs):
    pre[r['start']].append(k); post[r['end']].append(k)
ONE = 1 << W
def relations(cands):
    """For each candidate wire, return list of wires (and 'one') whose XOR equals it, or None."""
    live = [i for i in range(892) if sig[i] or cst[i]]
    basis = {}   # pivot bit -> (vec, combo)
    out = {}
    order = [i for i in live if i not in cands] + [i for i in live if i in cands]
    vecs = [(ONE, 1 << 892)]  # constant pseudo-wire index 892
    vecs += [(sig[i] | (cst[i] << W), 1 << i) for i in order]
    for v, c in vecs:
        while v:
            pb = v.bit_length() - 1
            if pb in basis:
                bv, bc = basis[pb]; v ^= bv; c ^= bc
            else:
                basis[pb] = (v, c); break
        if v == 0:
            # relation: combo c XORs to zero
            for q in cands:
                if q not in out and (c >> q) & 1:
                    out[q] = [j for j in range(893) if (c >> j) & 1 and j != q]
    return {q: out.get(q) for q in cands}
res = [dict(start=r['start'], end=r['end'], section=r['section'], pre=None, post=None) for r in runs]
depth = 0
def q(x): return int(x[1:])
lastline = max(r['end'] for r in runs) if runs else 0
with open(fin) as f:
    for ln, line in enumerate(f, 1):
        if ln > lastline: break
        if ln in pre:
            for k in pre[ln]:
                c = [d for d in runs[k]['dormant']]
                res[k]['pre'] = relations(set(c)) if depth == 0 else 'cond'
        p = line.split()
        if p:
            op = p[0]
            if op == 'INFO_TAG' or op == 'REGISTER': pass
            elif op == 'PUSH_CONDITION': depth += 1
            elif op == 'POP_CONDITION': depth -= 1
            elif op == 'APPEND_TO_REGISTER':
                x = p[1]
                if x[0] == 'q': sig[q(x)] = R(); cst[q(x)] = 0
                else: bsig[int(x[1:])] = R()
            else:
                ifb = None
                if len(p) > 2 and p[-2] == 'if': ifb = int(p[-1][1:]); p = p[:-2]
                if op.startswith('BIT_'):
                    b = int(p[1][1:])
                    if depth: bsig[b] = R(); bcst[b] = 0
                    elif op == 'BIT_STORE0': bsig[b] = 0; bcst[b] = 0
                    elif op == 'BIT_STORE1': bsig[b] = 0; bcst[b] = 1
                    elif op == 'BIT_INVERT':
                        if ifb is None: bcst[b] ^= 1
                        else: bsig[b] ^= bsig[ifb]; bcst[b] ^= bcst[ifb]
                    else: bsig[b] = R(); bcst[b] = 0
                elif op in ('Z', 'CZ', 'CCZ', 'NEG'): pass
                else:
                    qs = [q(x) for x in p[1:] if x[0] == 'q']
                    if op == 'CX':
                        c, t = qs
                        if depth: sig[t] = R(); cst[t] = 0
                        elif ifb is not None:
                            s, cc = prodsig(sig[c], cst[c], bsig[ifb], bcst[ifb]); sig[t] ^= s; cst[t] ^= cc
                        else: sig[t] ^= sig[c]; cst[t] ^= cst[c]
                    elif op == 'X':
                        t = qs[0]
                        if depth: sig[t] = R(); cst[t] = 0
                        elif ifb is not None: sig[t] ^= bsig[ifb]; cst[t] ^= bcst[ifb]
                        else: cst[t] ^= 1
                    elif op == 'CCX':
                        a, b, t = qs
                        if depth or ifb is not None: sig[t] = R(); cst[t] = 0
                        else:
                            s, cc = prodsig(sig[a], cst[a], sig[b], cst[b]); sig[t] ^= s; cst[t] ^= cc
                    elif op == 'CSWAP':
                        c, a, b = qs
                        if depth or ifb is not None: sig[a] = R(); sig[b] = R(); cst[a] = cst[b] = 0
                        else:
                            s, cc = prodsig(sig[c], cst[c], sig[a] ^ sig[b], cst[a] ^ cst[b])
                            sig[a] ^= s; cst[a] ^= cc; sig[b] ^= s; cst[b] ^= cc
                    elif op == 'SWAP':
                        a, b = qs; sig[a], sig[b] = sig[b], sig[a]; cst[a], cst[b] = cst[b], cst[a]
                    elif op in ('HMR', 'R'):
                        t = qs[0]; sig[t] = 0; cst[t] = 0
                        if op == 'HMR': bsig[int(p[2][1:])] = R()
        if ln in post:
            for k in post[ln]:
                c = [d for d in runs[k]['dormant']]
                res[k]['post'] = relations(set(c)) if depth == 0 else 'cond'
json.dump(res, open(fout, 'w'))
ok = 0
for r in res:
    if isinstance(r['pre'], dict) and isinstance(r['post'], dict):
        both = [q for q in r['pre'] if r['pre'][q] is not None and r['post'].get(q) is not None]
        if both: ok += 1
print('runs', len(res), 'with a spillable dormant wire (affine at both ends):', ok)
