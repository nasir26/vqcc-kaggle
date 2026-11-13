"""Affine-signature scan for reusable AND products in a kmx circuit (no ancilla needed).

Every qubit/bit value is tracked as an affine GF(2) form over atoms (inputs, measurement outcomes, product atoms)
using random 64-bit XOR signatures. A product of two linear forms is keyed by the 2-dim subspace they span, so the
same AND (up to affine terms) is recognised wherever it recurs. For a Toffoli-like consumer at line j whose product
was produced by a real CCX/CSWAP at line i (unconditioned), the consumer can be replaced by Cliffords when:
  H: consumer CCX(a,b,t2): t2 is not read (control/swap/phase/measure) in (i, j) and t2 is not a control at i.
     At i insert CX(t1,t2) before and after the producer, at j XOR the affine difference with CX/X.
  Z: consumer CCZ(x,y,w): w unmodified in [i, j]. At i insert CZ(t1,w) around the producer, fix the affine
     difference at j with CZ/Z.
Writes the candidate list (one per consumer, latest producer) as TSV.
usage: python tasks/dqi/product_scan.py circuit.kmx out.tsv [first_line last_line]
"""
import sys, random, collections
fin, fout = sys.argv[1], sys.argv[2]
rng = random.Random(12345)
def R(): return rng.getrandbits(64) | 1
NQ, NB = 4096, 400000
sig = [0] * NQ; cst = [0] * NQ
bsig = [0] * NB; bcst = [0] * NB
lastread = [-1] * NQ; lastmod = [-1] * NQ
patoms = {}
def patom(key):
    v = patoms.get(key)
    if v is None: v = patoms[key] = R()
    return v
prod = {}   # subspace key -> [t1, line, end, val_sig, val_c]
holding = collections.defaultdict(list)
gaps = collections.Counter()
stats = collections.Counter()
cands = []
depth = 0
def form_product(sa, ca, sb, cb):
    """Return (kind, value_sig, value_const, key, info). kind 'aff' if affine."""
    if sa == 0:
        return 'aff', (sb if ca else 0), (ca & cb), None
    if sb == 0:
        return 'aff', (sa if cb else 0), (ca & cb), None
    if sa == sb:
        lin = 1 ^ ca ^ cb
        return 'aff', (sa if lin else 0), (ca & cb), None
    w = sa ^ sb
    u, v, _ = sorted((sa, sb, w))
    # canonical: P = U*V with U<V the two smallest of the subspace's nonzero forms
    P = patom((u, v))
    # X*Y (distinct, both in {U,V,W}) = P ^ (U if {X,Y}=={U,W}) ^ (V if {X,Y}=={V,W})
    pair = {sa, sb}
    s = P
    W = u ^ v
    if pair == {u, W}: s ^= u
    elif pair == {v, W}: s ^= v
    # (A0^ca)(B0^cb) = A0B0 ^ cb A0 ^ ca B0 ^ ca cb
    if cb: s ^= sa
    if ca: s ^= sb
    return 'prod', s, ca & cb, (u, v)
def q(x): return int(x[1:])
def inval(t, ln):
    for kk in holding.pop(t, ()):
        h = prod.get(kk)
        if h is not None and h[0] == t and h[2] is None: h[2] = ln
with open(fin) as f:
    for ln, line in enumerate(f, 1):
        p = line.split()
        if not p: continue
        op = p[0]
        if op == 'PUSH_CONDITION': depth += 1; continue
        if op == 'POP_CONDITION': depth -= 1; continue
        if op in ('APPEND_TO_REGISTER', 'REGISTER', 'INFO_TAG'): 
            if op == 'APPEND_TO_REGISTER':
                x = p[1]
                if x[0] == 'q': sig[q(x)] = R(); cst[q(x)] = 0
                else: bsig[int(x[1:])] = R(); bcst[int(x[1:])] = 0
            continue
        ifb = None
        if len(p) > 2 and p[-2] == 'if':
            ifb = int(p[-1][1:]); p = p[:-2]
        if op.startswith('BIT_'):
            b = int(p[1][1:])
            if depth: bsig[b] = R(); bcst[b] = 0; continue
            if op == 'BIT_STORE0': bsig[b] = 0; bcst[b] = 0
            elif op == 'BIT_STORE1': bsig[b] = 0; bcst[b] = 1
            elif op == 'BIT_INVERT':
                if ifb is None: bcst[b] ^= 1
                else: bsig[b] ^= bsig[ifb]; bcst[b] ^= bcst[ifb]
            else: bsig[b] = R(); bcst[b] = 0
            continue
        qs = [q(x) for x in p[1:] if x[0] == 'q']
        cond = depth > 0 or ifb is not None
        if op == 'CX':
            c, t = qs; lastread[c] = ln; lastmod[t] = ln; inval(t, ln)
            if depth: sig[t] = R(); cst[t] = 0; stats['opaque'] += 1
            elif ifb is not None:
                k, s, cc, key = form_product(sig[c], cst[c], bsig[ifb], bcst[ifb])
                sig[t] ^= s; cst[t] ^= cc
            else: sig[t] ^= sig[c]; cst[t] ^= cst[c]
        elif op == 'X':
            t = qs[0]; lastmod[t] = ln; inval(t, ln)
            if depth: sig[t] = R(); cst[t] = 0
            elif ifb is not None: sig[t] ^= bsig[ifb]; cst[t] ^= bcst[ifb]
            else: cst[t] ^= 1
        elif op == 'CCX':
            a, b, t = qs
            k, s, cc, key = form_product(sig[a], cst[a], sig[b], cst[b])
            for kk in holding.pop(t, ()):
                h = prod.get(kk)
                if h is not None and h[0] == t and h[2] is None: h[2] = ln
            if cond:
                stats['ccx_cond'] += 1
                lastread[a] = lastread[b] = ln; lastmod[t] = ln
                sig[t] = R(); cst[t] = 0
                continue
            if k == 'aff':
                stats['ccx_affine'] += 1; cands.append((ln, ln, 'A', a, b, t, -1, ''))
            else:
                h = prod.get(key)
                ok = False
                if h is not None:
                    t1, i, end, vs, vc = h
                    stats['ccx_match'] += 1
                    e = ln if end is None else end
                    d = vs ^ s
                    span = d in (0, sig[a], sig[b], sig[a] ^ sig[b])
                    if t1 == t: stats['same_t'] += 1
                    elif not span: stats['nospan'] += 1
                    elif lastread[t] < e:
                        ok = True; stats['H'] += 1
                        cands.append((max(i, lastread[t]), ln, 'H', a, b, t, t1, i))
                    else:
                        gaps[min(9, len(str(lastread[t] - e)))] += 1
                if not ok:
                    old = sig[t]
                    if old in (0, sig[a], sig[b], sig[a] ^ sig[b]):
                        prod[key] = [t, ln, None, old ^ s, cst[t] ^ cc]
                        holding[t].append(key)
            lastread[a] = lastread[b] = ln; lastmod[t] = ln
            sig[t] ^= s; cst[t] ^= cc
        elif op == 'CSWAP':
            c, a, b = qs
            for x in qs: lastread[x] = ln
            lastmod[a] = lastmod[b] = ln; inval(a, ln); inval(b, ln)
            if cond:
                sig[a] = R(); sig[b] = R(); cst[a] = cst[b] = 0; continue
            k, s, cc, key = form_product(sig[c], cst[c], sig[a] ^ sig[b], cst[a] ^ cst[b])
            if k != 'aff':
                stats['cswap'] += 1
            sig[a] ^= s; cst[a] ^= cc; sig[b] ^= s; cst[b] ^= cc
        elif op == 'CCZ':
            if not cond:
                done = False
                for (x, y, w) in ((qs[0], qs[1], qs[2]), (qs[0], qs[2], qs[1]), (qs[1], qs[2], qs[0])):
                    k, s, cc, key = form_product(sig[x], cst[x], sig[y], cst[y])
                    if k == 'aff':
                        stats['ccz_affine'] += 1; cands.append((ln, ln, 'AZ', x, y, w, -1, '')); done = True; break
                    hit = prod.get(key)
                    if hit is not None:
                        t1, i, end, vs, vc = hit
                        if lastmod[w] < i and w != t1 and (vs ^ s) in (0, sig[x], sig[y], sig[x] ^ sig[y]):
                            stats['Z'] += 1; cands.append((i, ln, 'Z', x, y, w, t1, '')); done = True; break
            for x in qs: lastread[x] = ln
        elif op in ('CZ', 'Z'):
            for x in qs: lastread[x] = ln
        elif op == 'SWAP':
            a, b = qs
            sig[a], sig[b] = sig[b], sig[a]; cst[a], cst[b] = cst[b], cst[a]; inval(a, ln); inval(b, ln)
            lastread[a] = lastread[b] = lastmod[a] = lastmod[b] = ln
        elif op == 'HMR':
            t = qs[0]; bb = int(p[2][1:])
            lastread[t] = lastmod[t] = ln; sig[t] = 0; cst[t] = 0; inval(t, ln)
            bsig[bb] = R(); bcst[bb] = 0
        elif op == 'R':
            t = qs[0]; lastread[t] = lastmod[t] = ln; sig[t] = 0; cst[t] = 0; inval(t, ln)
        elif op == 'NEG':
            pass
        else:
            stats['unknown_' + op] += 1
            for x in qs: lastread[x] = lastmod[x] = ln; sig[x] = R(); cst[x] = 0
with open(fout, 'w') as g:
    for c in cands: g.write('\t'.join(map(str, c)) + '\n')
print(dict(stats), len(cands)); print(sorted(gaps.items()))
