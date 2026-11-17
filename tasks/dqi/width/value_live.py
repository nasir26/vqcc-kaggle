"""[ours] Value liveness of a dqi .kmb/.kmx: simulate the verifier's own shot distribution chunk by chunk and record,
at every chunk boundary, which qubits are nonzero in any sampled shot. Uses the official verifier's sampler and
the kickmix simulator only (nothing is modified).
usage: value_live.py FILE.kmx CHUNK_LINES OUT.npz [--shots 1024] [--seed 7]"""
import sys, argparse, numpy as np, time
R = '/home/qacc/jsc_revision_2026/vqcc_kaggle/repo/data/comp'
sys.path[:0] = [R + '/kickmix', R + '/verifiers']
import kickmix as km
from dqi import verify_submission_dqi as V
ap = argparse.ArgumentParser(); ap.add_argument('kmx'); ap.add_argument('chunk', type=int); ap.add_argument('out')
ap.add_argument('--shots', type=int, default=1024); ap.add_argument('--seed', type=int, default=7)
a = ap.parse_args()
t0 = time.time()
full = km.Circuit.from_file(a.kmx, format='kmx')
spec = V.ProblemSpecDQI.benchmark_instance()
sq, mb, anc = V.validate_registers(full, spec)
NQ = full.num_qubits
tables = V.FieldTables(km.GF2Field(spec.degree))
wp = V.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
rng = np.random.default_rng(a.seed)
syn, mbuc, ph = V.sample_shots(spec, tables, rng, a.shots, wp)
sim = km.Simulator(batch_size=a.shots, debug_print=False, counting_operations=True, seed=a.seed + 1)
sim.use_same_registers_as(full)
inp = V.to_bits(syn, spec.degree)
sim.write_across_shots(km.array(sq), inp); sim.write_across_shots(km.array(mb), V.to_bits(mbuc, spec.degree))
del full
allq = km.array([km.q(i) for i in range(NQ)])
masks, ends, tof = [], [], []
cur = []; depth = 0; n = 0
def flush():
    global cur
    if not cur: return
    sim.do(km.Circuit('\n'.join(cur)))
    v = sim.read_across_shots(allq)
    masks.append(v.any(axis=1)); ends.append(n); cur = []
with open(a.kmx) as f:
    for line in f:
        if line.startswith(('APPEND_TO_REGISTER', 'REGISTER')): continue
        n += 1; cur.append(line.rstrip('\n'))
        if line.startswith('PUSH_CONDITION'): depth += 1
        elif line.startswith('POP_CONDITION'): depth -= 1
        if depth == 0 and len(cur) >= a.chunk: flush()
flush()
M = np.array(masks)
final_junk = sim.read_across_shots(anc).any()
diff = (sim.read_across_shots(km.array(sq)) ^ inp).any(axis=0).sum()
print(f'chunks {len(M)} lines {n} max nonzero {M.sum(1).max()} of {NQ}; value-errs {diff}; junk {final_junk}; {time.time()-t0:.0f}s')
np.savez_compressed(a.out, M=M, ends=np.array(ends))
