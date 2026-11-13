"""Width cut: insert affine spills (CX-only erase/restore of dormant wires around peak runs) and relabel qubits.

usage: python tasks/dqi/width_cut.py circuit.kmx spills.json out.kmx [NSLOTS]
spills.json: list of {"pre": line, "post": line, "q": wire, "rel_pre": [...], "rel_post": [...]}; relation entries
are wire indices, 892 meaning the constant 1 (an X). Before line `pre` the wire is XORed with its relation (erased);
after line `post` it is XORed with the post relation (restored).
Pass 1 builds the modified op stream's lifetimes (affine tracker: a wire is free when its value is the zero form);
pass 2 assigns physical slots (pinned: input and output lifetimes of the 840 syndrome wires keep their index),
pass 3 writes the relabeled kmx. Fails loudly if NSLOTS (default 891) slots do not suffice.
"""
import sys, json, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from affine_track import Tracker
fin, fsp, fout = sys.argv[1], sys.argv[2], sys.argv[3]
NS = int(sys.argv[4]) if len(sys.argv) > 4 else 891
spills = json.load(open(fsp))
before_ins = collections.defaultdict(list); after_ins = collections.defaultdict(list)
for s in spills:
    for w in s['rel_pre']: before_ins[s['pre']].append(('X q%d' % s['q']) if w == 892 else ('CX q%d q%d' % (w, s['q'])))
    for w in s['rel_post']: after_ins[s['post']].append(('X q%d' % s['q']) if w == 892 else ('CX q%d q%d' % (w, s['q'])))

def stream():
    with open(fin) as f:
        for ln, line in enumerate(f, 1):
            for x in before_ins.get(ln, ()): yield x
            yield line.rstrip('\n')
            for x in after_ins.get(ln, ()): yield x

META = ('INFO_TAG', 'PUSH_CONDITION', 'POP_CONDITION', 'REGISTER', 'APPEND_TO_REGISTER')
# pass 1: lifetimes
T = Tracker(W=64, seed=5)
born = {}           # wire -> op index of birth of the current lifetime
life = []           # (wire, birth, death)  death = op index after which it is free; None = alive at end
k = 0
nzmax = 0; nz = 0
for line in stream():
    p = line.split()
    if not p: continue
    if p[0] == 'APPEND_TO_REGISTER' and p[1][0] == 'q':
        T.step(p); w = int(p[1][1:]); born[w] = -1; nz += 1; continue
    if p[0] in META or p[0].startswith('BIT_'):
        T.step(p); continue
    qs = sorted(set(int(x[1:]) for x in p[1:] if x[0] == 'q'))
    bz = {w: T.nonzero(w) for w in qs}
    T.step(p)
    for w in qs:
        a = T.nonzero(w)
        if a and not bz[w]: born[w] = k; nz += 1
        elif bz[w] and not a: life.append((w, born.pop(w), k)); nz -= 1
    nzmax = max(nzmax, nz)
    k += 1
for w, b in born.items(): life.append((w, b, None))
print('ops', k, 'lifetimes', len(life), 'max nonzero', nzmax, flush=True)
if nzmax > NS: sys.exit('peak %d exceeds %d slots' % (nzmax, NS))
# pass 2: slot assignment
pin = {}
for i, (w, b, d) in enumerate(life):
    if w < 840 and (b == -1 or d is None): pin[i] = w
births = collections.defaultdict(list); deaths = collections.defaultdict(list)
for i, (w, b, d) in enumerate(life):
    births[b].append(i)
    if d is not None: deaths[d].append(i)
pinned_starts = collections.defaultdict(list)   # slot -> sorted birth times of pinned lifetimes
for i, s in pin.items(): pinned_starts[s].append(life[i][0 + 1])
for s in pinned_starts: pinned_starts[s].sort()
nextpin_idx = collections.defaultdict(int)
INF = 1 << 62
def next_pin(s, now):
    lst = pinned_starts.get(s)
    if not lst: return INF
    j = nextpin_idx[s]
    while j < len(lst) and lst[j] < now: j += 1
    nextpin_idx[s] = j
    return lst[j] if j < len(lst) else INF
slot_of = {}
free = set(range(NS))
for i in births[-1]:
    s = pin[i]; slot_of[i] = s; free.discard(s)
# event times for births/deaths; temporary refs resolved in pass 3 using the free set replay
assign_fail = 0
times = sorted(set(t for t in births if t >= 0) | set(deaths))
births_at = births
for t in times:
    for i in births_at.get(t, ()):
        if i in pin:
            s = pin[i]
            if s not in free: sys.exit('pinned slot %d busy at op %d' % (s, t))
            free.discard(s); slot_of[i] = s
        else:
            d = life[i][2]; d = INF - 1 if d is None else d
            best = None; bnp = INF + 1
            for s in free:
                npv = next_pin(s, t)
                if npv > d and npv < bnp: best, bnp = s, npv
            if best is None: sys.exit('no slot for lifetime %r at op %d' % (life[i], t))
            free.discard(best); slot_of[i] = best
    for i in deaths.get(t, ()):
        free.add(slot_of[i])
print('assigned', len(slot_of), flush=True)
# pass 3: emit. Track current slot of each wire; temporary refs (zero wire, not born) use any free slot.
cur = {}
for i in births[-1]: cur[life[i][0]] = slot_of[i]
bq = collections.defaultdict(list)   # op index -> list of (wire, lifetime idx) born
for i, (w, b, d) in enumerate(life):
    if b >= 0: bq[b].append((w, i))
dq = collections.defaultdict(list)
for i, (w, b, d) in enumerate(life):
    if d is not None: dq[d].append(w)
free = set(range(NS)) - set(cur.values())
k = 0; temps = 0
with open(fout, 'w') as g:
    for line in stream():
        p = line.split()
        if not p: continue
        if p[0] in META or p[0].startswith('BIT_'):
            g.write(line + '\n'); continue
        for w, i in bq.get(k, ()):
            cur[w] = slot_of[i]; free.discard(slot_of[i])
        qs = [int(x[1:]) for x in p[1:] if x[0] == 'q']
        tmp = {}
        for w in qs:
            if w not in cur and w not in tmp:
                s = min(free); free.discard(s); tmp[w] = s; temps += 1
        out = [p[0]]
        for x in p[1:]:
            if x[0] == 'q':
                w = int(x[1:]); out.append('q%d' % (cur[w] if w in cur else tmp[w]))
            else: out.append(x)
        g.write(' '.join(out) + '\n')
        for w in dq.get(k, ()):
            free.add(cur.pop(w))
        for w, s in tmp.items(): free.add(s)
        k += 1
print('written', fout, 'temps', temps)
