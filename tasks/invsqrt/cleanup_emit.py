"""Emit a new table cleanup (ours) from a monomial bank set found by cleanup_exh.py and splice it into the circuit.
Forward schedule: pay the 30 pending table debts with all outputs live; erase outputs in the reverse of the
reverse-time closure order, creating banks lazily on erased-output wires; erase banks last. Every payment is the
exact quadratic expansion over the live wires (Z / CZ / NEG under the outcome bit).
Banks may be monomials in transformed address forms y_i = xor of address wires (BASIS pickle from cleanup_exh.py with
BASIS_SEED); each y is formed on a pivot address wire by CX frames around its CCX and undone right after.
Usage: python tasks/invsqrt/cleanup_emit.py IN.kmx L0 L1 SOLUTION_INDEX OUT.kmx PICKLE"""
import sys, itertools, pickle, json
sys.path.insert(0, 'tasks/invsqrt')
from cleanup_opt import E, ADDR, OUT, Q, FULL
IN, L0, L1, SI, OUTF = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
PK = pickle.load(open(sys.argv[6], 'rb'))
d = json.load(open('data/work/inv_gen/cleanup.json'))
AW = sorted(ADDR, key=ADDR.get); X0 = [E[w] for w in AW]
ROWS = PK['rows'] or [[int(i == j) for j in range(6)] for i in range(6)]
YW = [[0]] + [[j + 1 for j in range(6) if ROWS[i][j]] for i in range(6)]   # y_i as list of address indices
X = [X0[0]] + [eval('^'.join(['0'] + [f'X0[{j}]' for j in YW[i]])) for i in range(1, 7)]
qset, cs = PK['sols'][SI]
def mono(t):
    f = X[t[0]]
    for i in t[1:]: f &= X[i]
    return f
def frame(i, avoid):
    """(pivot wire, CX ops) forming y_i on an address wire not in avoid."""
    ws = YW[i]; piv = [j for j in ws if AW[j] not in avoid][0]
    return AW[piv], [f'CX {AW[j]} {AW[piv]}' for j in ws if j != piv]
banks = [('pair', tuple(p), mono(p)) for p in qset] + [('cub', tuple(t), mono(t)) for t in cs]

def expand(f, live):
    """f as c + sum l_i w_i + sum q_ij w_i w_j over live [(wire, func)]; returns (c, lin, quad) or None."""
    cols = [((FULL), ('1',))] + [(fn, (w,)) for w, fn in live] + [(a[1] & b[1], (a[0], b[0])) for a, b in itertools.combinations(live, 2)]
    piv = {}
    for v, lab in cols:
        x, s = v, {lab}
        while x:
            h = x.bit_length() - 1
            if h in piv: x ^= piv[h][0]; s ^= piv[h][1]
            else: piv[h] = (x, s); break
    x, s = f, set()
    while x:
        h = x.bit_length() - 1
        if h not in piv: return None
        x ^= piv[h][0]; s ^= piv[h][1]
    return s

def pay(bit, f, live, out):
    s = expand(f, live); assert s is not None, bit
    body = []
    for lab in sorted(s, key=lambda t: (len(t), t)):
        if lab == ('1',): out.append(f'NEG if {bit}')
        elif len(lab) == 1: body.append(f'Z {lab[0]}')
        else: body.append(f'CZ {lab[0]} {lab[1]}')
    if body: out += [f'PUSH_CONDITION if {bit}'] + body + ['POP_CONDITION']

# reverse closure order
S = X + [b[2] for b in banks]; outs = list(OUT); rounds = []
while outs:
    q = Q(S); hit = [o for o in outs if q.has(E[o])]; assert hit
    rounds.append(hit); S += [E[o] for o in hit]; outs = [o for o in outs if o not in hit]
erase_order = [o for r in reversed(rounds) for o in r]
out = []
live = [(w, E[w]) for w in AW] + [(o, E[o]) for o in OUT]
for k, v in d['pre'].items(): pay(k.split('@')[0], int(v), live, out)
free = []; made = []; pending = list(banks)
def need(o):
    rest = [t for t in live if t[0] != o]
    return expand(E[o] if o in E else dict(live)[o], rest) is None
for o in erase_order:
    while True:
        rest = [t for t in live if t[0] != o]
        if expand(E[o], rest) is not None: break
        # create next bank whose parents exist
        for b in pending:
            if b[0] == 'pair' or any(tuple(sorted(p)) in [m[1] for m in made] for p in itertools.combinations(b[1], 2)): break
        else: raise AssertionError('no creatable bank')
        assert free, ('width: no free wire for bank', o)
        w = free.pop(0)
        if b[0] == 'pair':
            u, fu = frame(b[1][0], set())
            T = set(YW[b[1][1]]); pu = AW.index(u)
            if pu in T: src = ((T - {pu}) ^ (set(YW[b[1][0]]) - {pu})) | {pu}
            else: src = T
            cand = sorted(j for j in src if j != pu); assert cand
            v = AW[cand[0]]; fv = [f'CX {AW[j]} {v}' for j in sorted(src) if j != cand[0]]
        else:
            par = [m for m in made if set(m[1]) < set(b[1])][0]; u, fu = par[3], []
            v, fv = frame((set(b[1]) - set(par[1])).pop(), set())
        out += fu + fv + [f'CCX {u} {v} {w}'] + list(reversed(fv)) + list(reversed(fu)); made.append((b[0], b[1], b[2], w)); pending.remove(b); live.append((w, b[2]))
    out.append(f'HMR {o} b49'); live = [t for t in live if t[0] != o]; pay('b49', E[o], live, out); free.append(o)
for m in reversed(made):
    w = m[3]; out.append(f'HMR {w} b49'); live = [t for t in live if t[0] != w]; pay('b49', m[2], live, out)
lines = open(IN).read().splitlines()
new = lines[:L0 - 1] + out + lines[L1:]
open(OUTF, 'w').write('\n'.join(new) + '\n')
print('banks', len(made), 'CCX in new region', sum(l.startswith('CCX') for l in out), 'ops', len(out))
