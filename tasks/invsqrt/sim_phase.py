"""Exact per-x phase of an invsqrt circuit by the official simulator (ours).

Runs every x in [1, max_x] for `shots` independent HMR transcripts with the same kickmix calls as the verifier
(x restored and scratch clean are asserted), and returns theta[x-1] in units of 2^-64 turns. Raises if any x gets
different phases on different shots (HMR-dependent phase).
Usage: python tasks/invsqrt/sim_phase.py CIRCUIT OUT.npy [shots] [seed]
"""
import concurrent.futures
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path += [str(REPO / 'data/comp/kickmix'), str(REPO / 'data/comp/verifiers')]
import kickmix as km  # noqa: E402
from invsqrt import verify_submission_invsqrt as V  # noqa: E402

SPEC = V.ProblemSpecInvSqrt.for_n_p(V.N_P)
B = 256
_C = {}


def load(path):
    return km.Circuit.from_file(str(path))


def run(task):
    start, stop, seed = task
    circ, x_reg, scratch = _C['c'], _C['x'], _C['s']
    sim = km.Simulator(batch_size=B, debug_print=False, counting_operations=False, seed=seed)
    out = np.zeros(stop - start, dtype=np.uint64)
    for a in range(start, stop, B):
        xs = (np.arange(a, a + B, dtype=np.uint64) % np.uint64(SPEC.max_x)) + np.uint64(1)
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, V.to_bits(xs, SPEC.width))
        sim.do(circ)
        assert np.array_equal(V.from_bits(sim.read_across_shots(x_reg)), xs)
        if len(scratch):
            assert not sim.read_across_shots(scratch).any()
        th = np.array([V.half_turns_to_units(sim.read_shot_phase(i)) for i in range(B)], dtype=np.uint64)
        n = min(B, stop - a)
        out[a - start:a - start + n] = th[:n]
    return start, out


def phase_table(path, shots=2, seed=1, workers=None):
    circ = load(path)
    x_reg, scratch = V.validate_registers(circ, SPEC)
    _C.update(c=circ, x=x_reg, s=scratch)
    total = SPEC.max_x
    per = 65536
    res = None
    for s in range(shots):
        tasks = [(a, min(a + per, total), seed * 1000003 + s * 7919 + a) for a in range(0, total, per)]
        th = np.zeros(total, dtype=np.uint64)
        with concurrent.futures.ProcessPoolExecutor(workers, mp_context=mp.get_context('fork')) as ex:
            for a, o in ex.map(run, tasks):
                th[a:a + len(o)] = o
        if res is None:
            res = th
        elif not np.array_equal(res, th):
            bad = np.flatnonzero(res != th)
            raise AssertionError(f'HMR-dependent phase at {len(bad)} x, first x={bad[0] + 1}')
    return res


if __name__ == '__main__':
    shots = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    th = phase_table(sys.argv[1], shots, seed)
    np.save(sys.argv[2], th)
    target, tol = V.reference_values(SPEC, np.arange(1, SPEC.max_x + 1, dtype=np.uint64))
    err = (th - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    assert (used <= tol).all(), 'tolerance violated'
    sl = (tol - used).astype(np.int64)
    print('min_margin', int(sl.min()), 'argmin_x', int(sl.argmin()) + 1)
