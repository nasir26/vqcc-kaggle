"""Scan a kmx circuit for Toffoli pairs sharing an unchanged control pair that can be merged without ancilla.

CCX(a,b,t1) at line i and CCX(a,b,t2) at line j>i, with a,b unmodified in between, t1 != t2, and:
  mode H (hoist): t2 not read (control/swap/phase/measure) in (i,j)  -> do CX(t1,t2) CCX CX(t1,t2) at i, drop j
  mode D (defer): t1 not read in (i,j)                               -> drop i, do CX(t2,t1) CCX CX(t2,t1) at j
CCZ(a,b,x) at j with CCX(a,b,t) at i, a,b,x unmodified in (i,j): CZ(t,x) CCX CZ(t,x) at i, drop j (mode Z).
Only unconditioned gates outside PUSH_CONDITION scopes are considered.
usage: python tasks/dqi/pair_scan.py circuit.kmx out.tsv
"""
import sys, collections
fin, fout = sys.argv[1], sys.argv[2]
NQ = 2000
ver = [0] * NQ        # value-modification version
lastread = [-1] * NQ  # last line where the qubit was read / phase-touched / measured
lastmod = [-1] * NQ
prev = {}             # key -> list of (line, target, kind)
depth = 0
cand = []
stats = collections.Counter()
def qi(s): return int(s[1:])
with open(fin) as f:
    for ln, line in enumerate(f, 1):
        p = line.split()
        if not p: continue
        op = p[0]
        if op == 'PUSH_CONDITION': depth += 1; continue
        if op == 'POP_CONDITION': depth -= 1; continue
        if op in ('APPEND_TO_REGISTER', 'REGISTER', 'INFO_TAG') or op.startswith('BIT_'): continue
        cond = depth > 0 or (len(p) > 2 and p[-2] == 'if')
        qs = [qi(x) for x in p[1:] if x[0] == 'q']
        if op == 'CCX':
            a, b, t = qs
            if not cond:
                key = (min(a, b), max(a, b), ver[a], ver[b])
                for (i, t1, kind) in prev.get(key, ()):
                    if kind != 'CCX' or t1 == t: continue
                    if t1 in (a, b) or t in (a, b): continue
                    stats['ccx_pairs'] += 1
                    h = lastread[t] < i
                    d = lastread[t1] < i and lastmod[t1] <= i  # t1 untouched after i (except maybe xor)
                    d = lastread[t1] < i
                    if h or d:
                        cand.append((i, ln, a, b, t1, t, 'H' if h else 'D'))
                        stats['H' if h else 'D'] += 1
                        break
                prev.setdefault(key, []).append((ln, t, 'CCX'))
            lastread[a] = lastread[b] = ln
            ver[t] += 1; lastmod[t] = ln
        elif op == 'CCZ':
            a, b, x = qs
            if not cond:
                for (u, v, w) in ((a, b, x), (a, x, b), (b, x, a)):
                    key = (min(u, v), max(u, v), ver[u], ver[v])
                    hit = False
                    for (i, t1, kind) in prev.get(key, ()):
                        if kind != 'CCX' or t1 in (u, v, w): continue
                        if lastmod[w] < i:
                            cand.append((i, ln, u, v, t1, w, 'Z')); stats['Z'] += 1; hit = True; break
                    if hit: break
            for q in qs: lastread[q] = ln
        elif op == 'CX':
            c, t = qs
            lastread[c] = ln; ver[t] += 1; lastmod[t] = ln
        elif op == 'X':
            ver[qs[0]] += 1; lastmod[qs[0]] = ln
        elif op in ('CZ', 'Z'):
            for q in qs: lastread[q] = ln
        elif op in ('SWAP', 'CSWAP', 'HMR', 'R'):
            for q in qs: lastread[q] = ln; ver[q] += 1; lastmod[q] = ln
        else:
            for q in qs: lastread[q] = ln; ver[q] += 1; lastmod[q] = ln
with open(fout, 'w') as g:
    for c in cand: g.write('\t'.join(map(str, c)) + '\n')
print(dict(stats), len(cand))
