"""Affine-dependency scan of live wires (ours): at checkpoints, is any live wire an affine GF(2) function of the
other live wires (sampled inputs, random HMR)? Such a wire could be CX-erased and restored, giving a free lane
for a held product. Uses Syed Asad Ali's kmsim (Apache-2.0) bit-sliced simulator.
Usage: dep_scan.py KMX [every] [n]"""
import sys, numpy as np
sys.path.insert(0, 'data/work/inv_gen/b0/invsqrt_build.pP3Dk2/tree/tools')
import kmsim
text = open(sys.argv[1]).read(); every = int(sys.argv[2]) if len(sys.argv) > 2 else 25; n = int(sys.argv[3]) if len(sys.argv) > 3 else 4096
ops, regs = kmsim.parse(text)
rng = np.random.default_rng(5); xs = np.sort(rng.choice(np.arange(1, 3133453, dtype=np.uint64), n, replace=False))
sim = kmsim.Sim(ops, regs['x'], xs=xs, seed=11)
def rank(vecs):
    rows = [int.from_bytes(v.tobytes(), 'little') for v in vecs]; basis = {}; r = 0
    for x in rows:
        while x:
            h = x.bit_length() - 1
            if h in basis: x ^= basis[h]
            else: basis[h] = x; r += 1; break
    return r
hits = []
for i in range(len(ops)):
    sim.step(i)
    if i % every == 0:
        live = [w for w, v in sim.state.items() if w.startswith('q') and v.any()]
        if len(live) >= 45:
            rk = rank([sim.ones] + [sim.state[w] for w in live])
            if rk < len(live) + 1: hits.append((i, len(live), len(live) + 1 - rk))
print('checkpoints with dependency (op, live, deficiency):', len(hits)); print(hits[:40])
