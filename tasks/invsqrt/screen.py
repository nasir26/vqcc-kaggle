"""Fast screen of an invsqrt circuit: official checks (x restored, clean scratch, phase within tol) on a subset of x
with several seeds, plus mean Toffolis / rotations and the minimum margin (units 2^-64 turn) on that subset.
Usage: screen.py FILE [n_random] [n_seeds] [workers]"""
import sys, math, io, hashlib, os
import numpy as np
sys.path.append('/home/qacc/jsc_revision_2026/vqcc_kaggle/repo/data/comp/kickmix')
sys.path.append('/home/qacc/jsc_revision_2026/vqcc_kaggle/repo/data/comp/verifiers')
import kickmix as km
from invsqrt import verify_submission_invsqrt as V
from concurrent.futures import ProcessPoolExecutor
X_MAX = 3 * (2**10 - 2)**2
spec = V.ProblemSpecInvSqrt.for_n_p(10)

def xs_for(n_random, seed=0):
    rng = np.random.default_rng(seed)
    hard = [161, 60, 2588411, X_MAX, X_MAX - 1]
    xs = np.concatenate([np.arange(1, 4097), np.array(hard), rng.integers(1, X_MAX + 1, n_random),
                         (2 ** np.arange(0, 22))[2 ** np.arange(0, 22) <= X_MAX], (2 ** np.arange(1, 22) - 1)[(2 ** np.arange(1, 22) - 1) <= X_MAX]])
    xs = np.unique(xs.astype(np.uint64))
    pad = (-len(xs)) % 256
    return np.concatenate([xs, xs[:pad]])

def run_batch(args):
    path, xs, seed = args
    c = km.Circuit.from_file(path)
    x_reg, scratch = V.validate_registers(c, spec)
    target, tol = V.reference_values(spec, xs)
    sim = km.Simulator(batch_size=len(xs), debug_print=False, counting_operations=True, seed=seed)
    sim.clear_for_shot(); sim.write_across_shots(x_reg, V.to_bits(xs, spec.width)); sim.do(c)
    okx = np.array_equal(V.from_bits(sim.read_across_shots(x_reg)), xs)
    dirty = sim.read_across_shots(scratch).any(axis=1).any() if len(scratch) else False
    theta = np.array([V.half_turns_to_units(sim.read_shot_phase(i)) for i in range(len(xs))], dtype=np.uint64)
    err = (theta - target).view(np.int64); used = np.abs(err).view(np.uint64)
    bad = int((used > tol).sum())
    margin = int((tol.astype(object) - used.astype(object)).min()) if True else 0
    ratio = float(np.max(used / np.maximum(tol, 1)))
    st = sim.operation_statistics()
    return okx, not dirty, bad, margin, ratio, st.num_toffoli_like, st.num_t_like, st.num_z_pow(min_clifford_hierarchy_level=4), len(xs)

def screen(path, n_random=20000, n_seeds=4, workers=16):
    xs = xs_for(n_random)
    chunks = np.array_split(xs, max(1, len(xs) // 2048))
    chunks = [ch[: (len(ch) // 256) * 256] if len(ch) >= 256 else ch for ch in chunks]
    tasks = [(path, ch, 1000 + 7919 * s + i) for s in range(n_seeds) for i, ch in enumerate(chunks)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(run_batch, tasks))
    okx = all(r[0] for r in res); clean = all(r[1] for r in res); bad = sum(r[2] for r in res)
    margin = min(r[3] for r in res); ratio = max(r[4] for r in res)
    n = sum(r[8] for r in res); tof = sum(r[5] for r in res) / n; t = sum(r[6] for r in res) / n; rot = sum(r[7] for r in res) / n
    c = km.Circuit.from_file(path)
    eps = math.pi * margin / 2**64 / rot if margin > 0 else float('nan')
    C = tof + (t + rot * (0.56 * math.log2(1 / eps) + 5.3)) / 4 if margin > 0 else float('nan')
    return dict(ok=okx and clean and bad == 0, okx=okx, clean=clean, bad=bad, margin=margin, worst=ratio, toff=tof, t=t,
                rot=rot, Q=c.num_qubits, C=C, cost=c.num_qubits * C, ratio=2076774.233715282 / (c.num_qubits * C))

if __name__ == '__main__':
    a = sys.argv
    r = screen(a[1], int(a[2]) if len(a) > 2 else 20000, int(a[3]) if len(a) > 3 else 4, int(a[4]) if len(a) > 4 else 16)
    print(r)
