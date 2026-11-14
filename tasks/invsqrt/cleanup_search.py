"""Beam search for the cheapest table cleanup (ours). See cleanup_opt.py for the model.
State: live non-address items (outputs and banks). Free moves: erase an item that lies in Q(X + other live items).
Paid move: add a bank u*v (u, v single live wires, or a live wire times the xor of two live wires). Goal: nothing live.
Usage: python tasks/invsqrt/cleanup_search.py [beam]"""
import sys, itertools, random
sys.path.insert(0, 'tasks/invsqrt')
from cleanup_opt import E, ADDR, OUT, Q, FULL
X = [E[w] for w in ADDR]
BEAM = int(sys.argv[1]) if len(sys.argv) > 1 else 40

def free_erase(items):
    items = list(items); order = []
    changed = True
    while changed:
        changed = False
        for i, (name, f) in enumerate(items):
            rest = X + [g for j, (n, g) in enumerate(items) if j != i]
            if Q(rest).has(f):
                order.append(name); items.pop(i); changed = True; break
    return items, order

def cands(items):
    pool = [(f'x{s}', E[w]) for w, s in ADDR.items()] + items
    out = {}
    for (a, u), (b, v) in itertools.combinations(pool, 2):
        out[f'({a}*{b})'] = u & v
    for (a, u), (b, v), (c, w) in itertools.combinations(pool, 3):
        for (p, pu), (q1, qv), (r, rw) in (((a, u), (b, v), (c, w)), ((b, v), (a, u), (c, w)), ((c, w), (a, u), (b, v))):
            out[f'({p}*({q1}+{r}))'] = pu & (qv ^ rw)
    return out

start, order0 = free_erase([(w, E[w]) for w in OUT])
print('free start: stuck', [n for n, _ in start])
beam = [(0, start, order0)]
best = None
for depth in range(1, 9):
    nxt = []
    for cost, items, order in beam:
        cs = cands(items)
        scored = []
        for name, f in cs.items():
            if f == 0 or f == FULL: continue
            it2, ord2 = free_erase(items + [(name, f)])
            scored.append((len(it2), name, it2, ord2))
        scored.sort(key=lambda t: t[0])
        for n_left, name, it2, ord2 in scored[:BEAM]:
            nxt.append((cost + 1, it2, order + [('BANK', name)] + ord2))
            if n_left == 0 and (best is None or cost + 1 < best[0]):
                best = (cost + 1, order + [('BANK', name)] + ord2)
    if best: break
    # dedupe by remaining set
    seen = {}; 
    for c, it, o in sorted(nxt, key=lambda t: len(t[1])):
        key = tuple(sorted(f for _, f in it))
        if key not in seen: seen[key] = (c, it, o)
    beam = list(seen.values())[:BEAM]
    print('depth', depth, 'best remaining', min(len(b[1]) for b in beam), flush=True)
print('BEST', best)
