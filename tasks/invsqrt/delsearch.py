"""Single-gate deletion search: delete each Toffoli-like gate in turn, screen, report passing deletions with cost."""
import sys, os, io, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from screen import screen, km
src = sys.argv[1]; out = sys.argv[2]; nr = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
c = km.Circuit.from_file(src); buf = io.BytesIO(); c.to_file(buf, format='kmx')
lines = buf.getvalue().decode().splitlines()
base = screen(src, nr, 2, 32)
print('base', base, flush=True)
os.makedirs(out, exist_ok=True)
idx = [i for i, l in enumerate(lines) if l.split()[0] in ('CCX', 'CCZ', 'CSWAP')]
res = []
for k, i in enumerate(idx):
    cand = lines[:i] + lines[i + 1:]
    p = f'{out}/cand.kmx'
    open(p, 'w').write('\n'.join(cand) + '\n')
    try:
        r = screen(p, nr, 2, 32)
    except Exception as e:
        continue
    if r['ok']:
        res.append((i, lines[i], r['cost'], r['toff'], r['margin']))
        print('PASS', i, lines[i], r['cost'], r['toff'], r['margin'], flush=True)
    if k % 100 == 0: print('progress', k, len(idx), flush=True)
json.dump(res, open(f'{out}/passing.json', 'w'))
