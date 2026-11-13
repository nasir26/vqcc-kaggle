"""Exact-zero liveness of a kmx circuit using affine XOR signatures (64-bit random atoms).

A qubit is free when its value is the zero affine form (sig 0, const 0). Products, conditioned writes and
CSWAP outputs become new atoms (conservative: a product that later cancels algebraically is still caught,
since XOR of equal atom signatures cancels). Reports the peak number of nonzero qubits overall and per
top-level section, plus how many sampled lines sit at the peak.
usage: python tasks/dqi/liveness.py circuit.kmx [runs_out.json PEAK]
With runs_out, also records maximal runs at nz>=PEAK and the wires untouched (dormant) through each run.
"""
import sys, random, collections
fin = sys.argv[1]
rng = random.Random(7)
def R(): return rng.getrandbits(64) | 1
NQ, NB = 4096, 400000
sig = [0] * NQ; cst = [0] * NQ; bsig = [0] * NB; bcst = [0] * NB
patoms = {}
def prodsig(sa, ca, sb, cb):
    if sa == 0: return (sb if ca else 0), ca & cb
    if sb == 0: return (sa if cb else 0), ca & cb
    if sa == sb: return (sa if (1 ^ ca ^ cb) else 0), ca & cb
    u, v, _ = sorted((sa, sb, sa ^ sb)); W = u ^ v
    P = patoms.get((u, v))
    if P is None: P = patoms[(u, v)] = R()
    s = P; pair = {sa, sb}
    if pair == {u, W}: s ^= u
    elif pair == {v, W}: s ^= v
    if cb: s ^= sa
    if ca: s ^= sb
    return s, ca & cb
SECS = {'mask_projection', 'initial', 'extract', 'synthesis', 'convert', 'scan', 'unconvert', 'unsynthesis',
        'unextract', 'uninitial', 'restore_masks'}
nz = 0; peak = 0; peakline = 0; section = '-'; secpeak = collections.Counter(); atpeak = collections.Counter()
samples = collections.Counter(); depth = 0
import json
RUNOUT = sys.argv[2] if len(sys.argv) > 2 else None
PEAKV = int(sys.argv[3]) if len(sys.argv) > 3 else 892
runs = []; inrun = False; touched = set(); runstart = 0
def q(x): return int(x[1:])
with open(fin) as f:
    for ln, line in enumerate(f, 1):
        p = line.split()
        if not p: continue
        op = p[0]
        if op == 'INFO_TAG':
            t = p[1].strip('"')
            if t.startswith('@enter:') and t[7:] in SECS: section = t[7:]
            continue
        if op == 'PUSH_CONDITION': depth += 1; continue
        if op == 'POP_CONDITION': depth -= 1; continue
        if op == 'REGISTER': continue
        if op == 'APPEND_TO_REGISTER':
            x = p[1]
            if x[0] == 'q':
                i = q(x); sig[i] = R(); cst[i] = 0; nz += 1
            else: bsig[int(x[1:])] = R()
            continue
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
            continue
        qs = [q(x) for x in p[1:] if x[0] == 'q']
        if op in ('Z', 'CZ', 'CCZ', 'NEG'): continue
        before = sum(1 for x in set(qs) if sig[x] or cst[x])
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
        else:
            print('unknown', op); 
            for x in qs: sig[x] = R()
        after = sum(1 for x in set(qs) if sig[x] or cst[x])
        if inrun: touched.update(qs)
        nz += after - before
        if RUNOUT:
            if nz >= PEAKV and not inrun:
                inrun = True; runstart = ln; touched = set(qs)
            elif nz < PEAKV and inrun:
                inrun = False
                live = [i for i in range(892) if (sig[i] or cst[i]) and i not in touched]
                runs.append(dict(start=runstart, end=ln, section=section, dormant=live))
        if nz > peak: peak = nz; peakline = ln
        if nz > secpeak[section]: secpeak[section] = nz
        if ln % 997 == 0: samples[nz] += 1
        if nz >= 885: atpeak[(section, nz)] += 1
print('peak', peak, 'line', peakline)
if RUNOUT:
    json.dump(runs, open(RUNOUT, 'w'))
    print('runs', len(runs), 'with dormant work wire', sum(1 for r in runs if any(d >= 840 for d in r['dormant'])))
print('section peaks', dict(secpeak))
print('sample hist (top)', sorted(samples.items())[-15:])
print('lines with nz>=885 by section', sorted(atpeak.items()))
