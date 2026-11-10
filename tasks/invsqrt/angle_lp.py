"""Retune the rotation angles of an invsqrt circuit to maximise the verifier's phase margin.

The verifier prices each non-Clifford, non-T rotation at 0.56 log2(1/eps) + 5.3 T with
eps = pi * min_x(tol(x) - |error(x)|) / n_rot. The tracked phase is a sum of rotation angles over the rotations
that fire, so for a fixed circuit skeleton the error is affine in the angles:

    error(x) = e0(x) + sum_k d_k b_k(x),   b_k(x) = 1 if rotation k fires for input x.

Steps:
  extract  simulate every x once with the original angles and once with angle k shifted by 2^k units of 2^-64
           turns; the exact phase difference encodes all b_k(x). Repeated with a second seed to check that the
           firing pattern does not depend on measurement outcomes.
  lp       maximise m subject to |e0 + B d| <= tol - m over all x (cutting planes, HiGHS).
  write    emit the circuit with the retuned angles (exact dyadic decimals).

Usage: python tasks/invsqrt/angle_lp.py IN.kmb OUT_DIR [--seeds 1 2]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import multiprocessing as mp
import os
import pathlib
import sys
import time
from fractions import Fraction

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path += [str(REPO / 'data/comp/kickmix'), str(REPO / 'data/comp/verifiers')]
import kickmix as km  # noqa: E402
from invsqrt import verify_submission_invsqrt as V  # noqa: E402

SPEC = V.ProblemSpecInvSqrt.for_n_p(10)
UNIT = Fraction(1, 2**63)  # 2^-64 turns in half turns
BATCH = 256

_G: dict = {}


def parse(kmx: str):
    lines = kmx.split('\n')
    rot = []
    for i, ln in enumerate(lines):
        if ln.startswith('Z_POW '):
            _, q, a = ln.split()
            if V.z_pow_class(Fraction(a)) == 'rotation':
                rot.append(i)
    return lines, rot


def with_angles(lines, rot, angles):
    out = list(lines)
    for i, a in zip(rot, angles):
        q = lines[i].split()[1]
        out[i] = f'Z_POW {q} {dyadic_str(a)}'
    return '\n'.join(out)


def dyadic_str(f: Fraction) -> str:
    f = Fraction(f) % 2
    d = f.denominator
    assert d & (d - 1) == 0, 'angle must be dyadic'
    k = d.bit_length() - 1
    n = f.numerator * 5**k  # f = n / 10^k
    s = str(n).rjust(k + 1, '0')
    return (s[:-k] + '.' + s[-k:]).rstrip('0').rstrip('.') if k else s


def load(text: str, path: pathlib.Path) -> km.Circuit:
    path.write_text(text)
    return km.Circuit.from_file(str(path), format='kmx')


def _sim_chunk(task):
    which, start, stop, seed = task
    c = _G['circuits'][which]
    x_reg = _G['x_reg']
    sim = km.Simulator(batch_size=BATCH, debug_print=False, counting_operations=False, seed=seed)
    out = np.empty(stop - start, dtype=np.uint64)
    for s in range(start, stop, BATCH):
        xs = np.arange(s, s + BATCH, dtype=np.uint64) + np.uint64(1)
        n = int(min(BATCH, stop - s))
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, V.to_bits(xs, SPEC.width))
        sim.do(c)
        out[s - start:s - start + n] = [V.half_turns_to_units(sim.read_shot_phase(i)) for i in range(n)]
    return start, out


def simulate_all(which: int, seed: int) -> np.ndarray:
    n = SPEC.max_x
    step = BATCH * 64
    tasks = [(which, s, min(s + step, n), seed * 1_000_003 + s) for s in range(0, n, step)]
    theta = np.empty(n, dtype=np.uint64)
    with cf.ProcessPoolExecutor(max_workers=os.cpu_count(), mp_context=mp.get_context('fork')) as pool:
        for start, out in pool.map(_sim_chunk, tasks, chunksize=1):
            theta[start:start + len(out)] = out
    return theta


def lp(e0: np.ndarray, B: np.ndarray, tol: np.ndarray, rounds: int = 30):
    """max m s.t. -tol + m <= e0 + B d <= tol - m. Units 2^-64 turns, scaled by 1e-6 for conditioning."""
    from scipy.optimize import linprog
    sc = 1e-6
    e0f, tolf = e0.astype(np.float64) * sc, tol.astype(np.float64) * sc
    K = B.shape[1]
    Bf = B.astype(np.float64)
    marg0 = tolf - np.abs(e0f)
    act = np.unique(np.concatenate([np.argsort(marg0)[:20000],
                                    np.random.default_rng(0).choice(len(e0f), 20000, replace=False)]))
    d = np.zeros(K)
    for r in range(rounds):
        A, b = Bf[act], e0f[act]
        # vars [d (K), m]; minimise -m
        Aub = np.vstack([np.hstack([A, np.ones((len(act), 1))]),
                         np.hstack([-A, np.ones((len(act), 1))])])
        bub = np.concatenate([tolf[act] - b, tolf[act] + b])
        res = linprog(np.r_[np.zeros(K), -1.0], A_ub=Aub, b_ub=bub,
                      bounds=[(None, None)] * K + [(None, None)], method='highs')
        assert res.status == 0, res.message
        d, m = res.x[:K], res.x[K]
        marg = tolf - np.abs(e0f + Bf @ d)
        worst = marg.min()
        print(f'  round {r}: active {len(act)}, lp m {m / sc:.4e}, true min margin {worst / sc:.4e}', flush=True)
        if worst >= m - abs(m) * 1e-9:
            break
        new = np.argsort(marg)[:20000]
        act = np.unique(np.concatenate([act, new]))
    return d / sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out_dir')
    ap.add_argument('--seeds', type=int, nargs='+', default=[1, 2])
    a = ap.parse_args()
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / 'tmp.kmx'
    km.Circuit.from_file(a.inp).to_file(str(tmp), format='kmx')
    lines, rot = parse(tmp.read_text())
    angles = [Fraction(lines[i].split()[2]) for i in rot]
    K = len(rot)
    print(f'{K} rotations')
    base = load('\n'.join(lines), tmp)
    pert_angles = [ang + UNIT * 2**k for k, ang in enumerate(angles)]
    pert = load(with_angles(lines, rot, pert_angles), out / 'pert.kmx')
    x_reg, _ = V.validate_registers(base, SPEC)
    _G.update(circuits=[base, pert], x_reg=x_reg)

    target, tol = V.reference_values(SPEC, np.arange(1, SPEC.max_x + 1, dtype=np.uint64))
    Bs, e0s = [], []
    for seed in a.seeds:
        t = time.time()
        th0 = simulate_all(0, seed)
        th1 = simulate_all(1, seed)
        diff = (th1 - th0).astype(np.uint64)
        assert int(diff.max()) < 2**K, 'perturbation decode overflow'
        B = ((diff[:, None] >> np.arange(K, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8)
        e0 = (th0 - target).view(np.int64)
        print(f'seed {seed}: {time.time() - t:.0f}s, min margin {int((tol.astype(np.int64) - np.abs(e0)).min()):d} units, '
              f'fire rates {B.mean(0).round(3).tolist()}', flush=True)
        Bs.append(B)
        e0s.append(e0)
    for B, e0 in zip(Bs[1:], e0s[1:]):
        print('pattern identical across seeds:', np.array_equal(B, Bs[0]), ' e0 identical:', np.array_equal(e0, e0s[0]))
    B = Bs[0]
    e0 = e0s[0]
    np.savez_compressed(out / 'profile.npz', B=B, e0=e0)

    tol_i = tol.astype(np.int64)
    m0 = int((tol_i - np.abs(e0)).min())
    d = lp(e0, B, tol_i)
    di = np.round(d).astype(np.int64)
    e1 = e0 + B.astype(np.int64) @ di
    m1 = int((tol_i - np.abs(e1)).min())
    print(f'margin {m0} -> {m1} units ({m1 / m0:.3f}x); eps gain {np.log2(m1 / m0):.3f} bits; '
          f'Toffoli-eq saved ~{K * 0.56 * np.log2(m1 / m0) / 4:.2f}')
    new_angles = [ang + UNIT * int(x) for ang, x in zip(angles, di)]
    text = with_angles(lines, rot, new_angles)
    (out / 'invsqrt.kmx').write_text(text)
    km.Circuit.from_file(str(out / 'invsqrt.kmx'), format='kmx').to_file(str(out / 'invsqrt.kmb'), format='kmb')
    np.save(out / 'delta_units.npy', di)
    print('wrote', out / 'invsqrt.kmb')


if __name__ == '__main__':
    main()
