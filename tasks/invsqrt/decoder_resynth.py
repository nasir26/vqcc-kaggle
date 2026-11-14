"""Decoder AND resynthesis for the K=6 address decoder of 4560ac0c/dcde7078 (ours).
Each address bit t must be written onto its target wire from the 18 table wires (+ already decoded bits):
    t = g + L1*h1 (+ L2*h2),  g, L, h affine over the available wires.
Exhaustive one-AND search (C helper oneand) and a two-AND search (twoand) give the order a5, a4, a3, a1, a0, a2 with
1+1+2+1+1+1 = 7 ANDs (the shipped decoder uses 8). Emits the replacement kmx block (CX frames + CCX into the target).
Usage: python tasks/invsqrt/decoder_resynth.py OUT_BLOCK.txt"""
import json, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
H = Path('/tmp/claude-1011/-home-qacc-jsc-revision-2026/252d475f-0b17-45d4-be26-4edc4a122a3f/scratchpad/oneand')
D = json.loads((REPO / 'data/work/inv_gen/dc/dec_tt.json').read_text())
TT = {k: int(v) for k, v in D['tt'].items()}
VARS = D['vars']; TG = D['targets']
FULL = (1 << 64) - 1
ORDER = ['q21', 'q42', 'q10', 'q8', 'q45', 'q34']        # a5, a4, a3, a1, a0, a2 (ahoirg names)
for t in ORDER: assert t in TG

def basis_of(names):
    vecs = [(TT.get(n, TT.get("T:" + n)), {n}) for n in names] + [(FULL, {'1'})]
    piv = {}; basis = []
    for v, s in vecs:
        x, xs = v, set(s)
        while x:
            h = x.bit_length() - 1
            if h in piv: x ^= piv[h][0]; xs ^= piv[h][1]
            else: piv[h] = (x, xs); basis.append((v, s)); break
    return basis

def solve(target, cols):
    """cols: list of (vector, label). Find subset XOR == target. Returns list of labels or None."""
    piv = {}
    for v, lab in cols:
        x, s = v, {lab}
        while x:
            h = x.bit_length() - 1
            if h in piv: x ^= piv[h][0]; s ^= piv[h][1]
            else: piv[h] = (x, s); break
    x, s = target, set()
    while x:
        h = x.bit_length() - 1
        if h not in piv: return None
        x ^= piv[h][0]; s ^= piv[h][1]
    return s

def combo(basis, mask):
    v = 0; s = set()
    for i, (bv, bs) in enumerate(basis):
        if mask >> i & 1: v ^= bv; s ^= bs
    return v, s

plans = []
avail = list(VARS)
for t in ORDER:
    basis = basis_of(avail)
    tv = TT['T:' + t]
    args = [str(tv)] + [str(TT.get(n, TT.get("T:" + n))) for n in avail]
    out = subprocess.run([str(H / 'oneand')] + args, capture_output=True, text=True).stdout
    prods = None
    if 'one-AND solutions: 0' not in out and 'L1 mask' in out:
        m = int(out.split('L1 mask ')[1].split()[0], 16)
        prods = [combo(basis, m)]
    else:
        r = len(basis); npairs = r * (r + 1) // 2
        out2 = subprocess.run([str(H / 'twoand'), '0', str(npairs), str(tv)] + [str(TT.get(n, TT.get("T:" + n))) for n in avail],
                              capture_output=True, text=True).stdout
        assert 'FOUND' in out2, out2
        a = int(out2.split('a=')[1].split()[0]); b = int(out2.split('b=')[1].split()[0]); m = int(out2.split('m=')[1], 16)
        L1 = combo(basis, (1 << a) | ((1 << b) if b != a else 0))
        prods = [L1, combo(basis, m)]
    # solve t = g + sum L_k * h_k
    cols = [(bv, ('g', i)) for i, (bv, bs) in enumerate(basis)]
    for k, (Lv, Ls) in enumerate(prods):
        cols += [(Lv & bv, ('h%d' % k, i)) for i, (bv, bs) in enumerate(basis)]
    sol = solve(tv, cols)
    assert sol is not None
    g = combo(basis, sum(1 << i for kind, i in sol if kind == 'g'))
    hs = [combo(basis, sum(1 << i for kind, i in sol if kind == 'h%d' % k)) for k in range(len(prods))]
    chk = g[0]
    for (Lv, _), (hv, _) in zip(prods, hs): chk ^= Lv & hv
    assert chk == tv
    plans.append(dict(target=t, g=sorted(g[1]), prods=[(sorted(L[1]), sorted(h[1])) for L, h in zip(prods, hs)]))
    avail.append(t)
    print(t, 'ANDs', len(prods), flush=True)
print('total ANDs', sum(len(p['prods']) for p in plans))

def emit(plans):
    out = []
    for p in plans:
        t = p['target']
        for Ls, Hs in p['prods']:
            L = set(Ls); Hh = set(Hs)
            Lc = '1' in L; L.discard('1'); Hc = '1' in Hh; Hh.discard('1')
            assert L and Hh
            pv = sorted(L)[0]
            frameL = [w for w in sorted(L) if w != pv]
            # current value of pv after forming L: L (+const). express H over current wires
            if pv in Hh:
                Hh ^= {pv}; Hh ^= set(frameL); Hh ^= {pv}  # x_pv = cur_pv + rest_L (+Lc)
                if Lc: Hc = not Hc
                # note: cur_pv appears in Hh as pv
            cand = sorted(Hh - {pv}) or None
            assert cand, 'H collapses onto L'
            qv = cand[0]
            frameH = [w for w in sorted(Hh) if w != qv]
            ops = [f'CX {w} {pv}' for w in frameL] + ([f'X {pv}'] if Lc else [])
            ops += [f'CX {w} {qv}' for w in frameH] + ([f'X {qv}'] if Hc else [])
            out += ops + [f'CCX {pv} {qv} {t}'] + list(reversed(ops))
        G = set(p['g']); gc = '1' in G; G.discard('1')
        out += [f'CX {w} {t}' for w in sorted(G)] + ([f'X {t}'] if gc else [])
    return out

blk = emit(plans)
Path(sys.argv[1]).write_text('\n'.join(blk) + '\n')
json.dump(plans, open(str(sys.argv[1]) + '.plans.json', 'w'), indent=1)
print('block ops', len(blk), 'CCX', sum(l.startswith('CCX') for l in blk))
