"""Dormancy windows of the wires that stay untouched through a whole section's chain of peak runs.
usage: python tasks/dqi/chain_windows.py circuit.kmx runs.json gaps.json out.json
"""
import sys, json
runs = json.load(open(sys.argv[2])); gaps = [set(g) for g in json.load(open(sys.argv[3]))]
n = len(runs); dorm = [set(r['dormant']) for r in runs]
chains = []; i = 0
while i < n:
    cand = set(dorm[i]); j = i
    while j + 1 < n:
        c2 = (cand - gaps[j]) & dorm[j + 1]
        if not c2 or runs[j + 1]['section'] != runs[i]['section']: break
        cand = c2; j += 1
    chains.append(dict(section=runs[i]['section'], start=runs[i]['start'], end=runs[j]['end'], wires=sorted(cand)))
    i = j + 1
allw = {w for c in chains for w in c['wires']}
lasttouch = {}; res = [dict(c, before={}, after={}) for c in chains]
with open(sys.argv[1]) as f:
    for ln, line in enumerate(f, 1):
        for c in res:
            if ln == c['start']:
                for w in c['wires']: c['before'][w] = lasttouch.get(w, 0)
        for x in line.split()[1:]:
            if x[0] == 'q':
                w = int(x[1:])
                if w in allw:
                    lasttouch[w] = ln
                    for c in res:
                        if ln > c['end'] and w in c['wires'] and w not in c['after']: c['after'][w] = ln
json.dump(res, open(sys.argv[4], 'w'))
for c in res:
    print(c['section'], c['start'], c['end'], [(w, c['before'][w], c['after'].get(w)) for w in c['wires']][:30])
