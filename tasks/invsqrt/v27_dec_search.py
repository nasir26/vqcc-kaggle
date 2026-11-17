"""One-AND decodability of each efd84ca5 address bit given any subset of already-decoded bits (ours).
Uses oneand128 (exhaustive over L in the span). Prints the minimal AND count over all 720 orders."""
import itertools, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, '.')
import v27_dec_compare as DC

H = '/tmp/claude-1011/-home-qacc-jsc-revision-2026/252d475f-0b17-45d4-be26-4edc4a122a3f/scratchpad/oneand128'
ent, ext, nq, blk = DC.tabs('../../data/work/inv_gen/v27/efd.kmx', 17882, 18181)
changed = [q for q in ext if ent.get(q) != ext.get(q)]
inputs = {q: v for q, v in ent.items() if v is not None}  # superset: old contents of target wires too (lower bound)
targets = {q: ext[q] for q in changed if q != 21}
q21 = ext[21]
coord = [sum(1 << a for a in range(128) if a >> s & 1) for s in range(7)]
print('inputs', sorted(inputs), 'targets', {q: [s for s in range(7) if v == coord[s]] for q, v in targets.items()})
# describe q21
pairs = [(i, j) for i in range(7) for j in range(i, 7)]
print('q21 is a coord product:', [(i, j) for i, j in pairs if (coord[i] & coord[j]) == q21])
hx = lambda v: f'{v >> 64:x}:{v & ((1 << 64) - 1):x}'


def test(args):
    t, sub, with21 = args
    av = list(inputs.values()) + [targets[s] for s in sub] + ([q21] if with21 else [])
    out = subprocess.run([H, hx(targets[t])] + [hx(v) for v in av], capture_output=True, text=True).stdout
    if 'affine' in out: return args, 0
    return args, (1 if 'one-AND solutions: 0' not in out else 2)


T = sorted(targets)
jobs = [(t, sub, w) for w in (0, 1) for t in T for k in range(6) for sub in itertools.combinations([u for u in T if u != t], k)]
with ThreadPoolExecutor(32) as ex:
    R = dict(ex.map(test, jobs))
for w in (0, 1):
    best = None
    for order in itertools.permutations(T):
        c = sum(R[(t, tuple(sorted(order[:i])), w)] for i, t in enumerate(order))
        if best is None or c < best[0]: best = (c, order)
    print('with q21 available' if w else 'without q21', 'min ANDs (>=, 2 means "needs >= 2")', best)
json.dump({f'{t}|{sub}|{w}': c for (t, sub, w), c in R.items()}, open('../../data/work/inv_gen/v27/dec_oneand.json', 'w'))
