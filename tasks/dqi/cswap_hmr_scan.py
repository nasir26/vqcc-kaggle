"""Find CSWAP(c,a,b) whose targets a and b are each next touched by HMR (and CCX whose target is next HMR'd).
usage: python tasks/dqi/cswap_hmr_scan.py circuit.kmx
"""
import sys, collections
pend = {}   # qubit -> (line, kind, partner)
res = collections.Counter(); hits = []
depth = 0
with open(sys.argv[1]) as f:
    for ln, line in enumerate(f, 1):
        p = line.split()
        if not p: continue
        op = p[0]
        if op == 'PUSH_CONDITION': depth += 1; continue
        if op == 'POP_CONDITION': depth -= 1; continue
        if op in ('INFO_TAG', 'REGISTER', 'APPEND_TO_REGISTER') or op.startswith('BIT_'): continue
        qs = [x for x in p[1:] if x[0] == 'q']
        for x in qs:
            if x in pend:
                l0, kind, other = pend.pop(x)
                ok = op == 'HMR'
                res[(kind, ok)] += 1
                if kind == 'cswap' and ok: hits.append((l0, x))
        if op == 'CSWAP' and depth == 0 and ' if ' not in line:
            c, a, b = qs; pend[a] = (ln, 'cswap', b); pend[b] = (ln, 'cswap', a)
        elif op == 'CCX' and depth == 0 and ' if ' not in line:
            pend[qs[2]] = (ln, 'ccx', None)
cnt = collections.Counter(l for l, x in hits)
print(dict(res)); print('cswap with both targets next HMR:', sum(1 for v in cnt.values() if v == 2))
print(sorted(l for l, v in cnt.items() if v == 2)[:60])
