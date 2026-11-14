"""Quick multiplicative-complexity estimate for the K=6 table loader outputs (ours): beam search over AND gates
L1*L2 (L affine over address bits and earlier ANDs), scored by the rank of the 17 outputs modulo the XOR span.
No width limit (a lower-effort relaxation of the real loader problem). Usage: loader_mc.py BEAM SAMPLES"""
import json, sys, random
d = json.load(open('data/src_pull/nov13b/ahoirg_k6c_extracted/k6data.json'))
def comp(x): return sum(((x >> (2 * i)) & 1) << i for i in range(64))
OUTS = [comp(int(t, 16)) for t in d['cert_first']['output_truths']]
FULL = (1 << 64) - 1
X = [sum(1 << a for a in range(64) if a >> s & 1) for s in range(6)]
BEAM, NS = int(sys.argv[1]), int(sys.argv[2])
def basis(vs):
    p = {}
    for v in vs:
        x = v
        while x:
            h = x.bit_length() - 1
            if h in p: x ^= p[h]
            else: p[h] = x; break
    return p
def red(p, x):
    while x:
        h = x.bit_length() - 1
        if h not in p: return x
        x ^= p[h]
    return 0
def missing(G):
    p = basis(G); q = {}
    r = 0
    for o in OUTS:
        x = red(p, o); x = red(q, x)
        if x: q[x.bit_length() - 1] = x; r += 1
    return r
rng = random.Random(1)
start = [FULL] + X
beam = [(missing(start), start)]
for step in range(1, 40):
    nxt = []
    for m, G in beam:
        seen = set()
        for _ in range(NS):
            a = 0; b = 0
            while a in (0, FULL) or b in (0, FULL):
                a = 0; b = 0
                for g in G:
                    if rng.random() < 0.3: a ^= g
                    if rng.random() < 0.3: b ^= g
            p = a & b
            if p in seen: continue
            seen.add(p); nxt.append((missing(G + [p]), G + [p]))
    nxt.sort(key=lambda t: t[0]); uniq = {}
    for t in nxt: uniq.setdefault(t[0] * 10**6 + len(uniq), t)
    beam = nxt[:BEAM]
    print(step, beam[0][0], flush=True)
    if beam[0][0] == 0: print('ANDS', step); break
