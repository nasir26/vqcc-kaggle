"""invsqrt candidate: QROM-seeded Newton-Raphson ("LUT-NR").

Same pipeline as the reference (nr_reference_circuit.py) except the initial guess:

    reference: 4-piece cubic Horner (3 truncated multiplies each way, 68 coefficient qubits)
    LUT-NR:    table lookup on the top `a` bits of x_norm -> (C0, C1); y0 = C0 - T(C1 * delta)
               with delta = the next `d` bits of x_norm (one truncated multiply each way).

The lookup is computed with init_lookup and cleared with del_lookup (measurement-based, a few
Toffolis), and C1 can be cleared right after the seed and re-looked-up for the uncompute
(`free_c1`), trading Toffolis for qubits. Normalize / Newton / de-normalize / phase stages are the
reference's own functions, so only the seed is new code.

`model()` is an exact integer replica of the circuit (seed + the reference's Newton arithmetic);
`tune_table()` picks each entry's C0 among C0* + k to minimise the final error over that entry's
inputs (entries partition x, so they are independent). All costs printed here are MODEL/STATIC
ESTIMATES; the official verifier decides.

Usage (WSL):
    python tasks/invsqrt/lut_nr.py data/comp OUT_DIR --a 7 --wc 17 --d 10 --square 28 --product 27 --result 28 [--free-c1]
    python tasks/invsqrt/lut_nr.py data/comp OUT_DIR ... --check 4096   # also simulate random x vs model
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import pathlib
import sys
from fractions import Fraction


@dataclasses.dataclass(frozen=True)
class Params:
    a: int = 7  # Address bits (top bits of x_norm, including the 2 integer bits of M).
    wc: int = 17  # Fractional bits of y0 (and C0).
    d: int = 10  # delta rows (x_norm bits below the address) used by the linear term.
    square: int = 28
    product: int = 27
    result: int = 28
    free_c1: bool = True  # Clear C1 after the seed; look it up again for the uncompute.
    n_p: int = 10

    @property
    def width(self) -> int:
        return 2 * self.n_p + 2

    @property
    def wc1(self) -> int:  # C1 in units of 2^-(wc - (a - 1)); c1 <= 1/2.
        return self.wc - self.a + 1

    @property
    def out_bits(self) -> int:
        return self.result + self.n_p + 1

    def rows(self) -> list[tuple[int, int]]:
        """(x_norm bit index, shift of C1) per delta row; shift >= wc1 rows contribute nothing."""
        out = []
        for r in range(self.d):
            i = self.width - self.a - 1 - r
            m = self.width - 2 - i  # delta bit weight 2^-m
            sh = m - (self.a - 1)
            if i < 0 or sh >= self.wc1:
                break
            out.append((i, sh))
        return out


def _np():
    import numpy as np
    return np


def normalize(p: Params, xs):
    np = _np()
    s = (p.width - (np.floor(np.log2(xs)).astype(np.int64) + 1)) // 2
    return xs << (2 * s), s


def seed(p: Params, x_norm, c0_table, c1_table):
    np = _np()
    addr = x_norm >> (p.width - p.a)
    y0 = c0_table[addr].copy()
    c1 = c1_table[addr]
    for i, sh in p.rows():
        y0 -= ((x_norm >> i) & 1) * (c1 >> sh)
    if ((y0 <= 0) | (y0 >= 2**p.wc)).any():
        raise OverflowError('y0 outside (0, 2^wc)')
    return y0


def newton(p: Params, x_norm, s, y0):
    """The reference's step 3 (fixed_point_model), verbatim arithmetic."""
    np = _np()
    width, wc, wsq, wz, wp = p.width, p.wc, p.square, p.product, p.result

    def bit(v, i):
        return (v >> i) & 1

    def product(rows, operand, out_bits, operand_bits, limit):
        acc = np.zeros_like(x_norm)
        for ctl, weight in rows:
            e = out_bits - operand_bits + weight
            acc += ctl * (operand << e if e >= 0 else operand >> -e)
        if (acc >= 2**limit).any():
            raise OverflowError('Intermediate register overflow.')
        return acc

    y = {k: bit(y0, wc - k) for k in range(1, wc + 1)}
    square = np.zeros_like(x_norm)
    for k in range(1, wc + 1):
        if 2 * k <= wsq:
            square += y[k] << (wsq - 2 * k)
        for l in range(k + 1, wc + 1):
            if k + l - 1 <= wsq:
                square += (y[k] & y[l]) << (wsq - (k + l - 1))
    m_rows = [(bit(x_norm, i), i - width + 2) for i in range(width)]
    z = product(m_rows, square, wz, wsq, wz + 2)
    correction = (3 << wz) - z
    pp = product([(y[k], -k) for k in range(1, wc + 1)], correction, wp, wz, wp + 1)
    return pp << s


def initial_table(p: Params):
    """Minimax-ish linear fit of 1/sqrt(M) per address interval [start, start + h)."""
    np = _np()
    n = 1 << p.a
    h = 2.0 ** (2 - p.a)
    c0 = np.zeros(n, dtype=np.int64)
    c1 = np.zeros(n, dtype=np.int64)
    for addr in range(n >> 2, n):  # top pair of x_norm != 00
        lo = addr * h
        f_lo, f_hi = lo ** -0.5, (lo + h) ** -0.5
        slope = (f_lo - f_hi) / h  # c1_real > 0; y = f_lo - slope * delta
        # Convex f: chord lies above f; max gap at the tangency point.
        t = (slope * 2) ** (-2 / 3)  # f'(t) = -slope -> t^(-3/2)/2 = slope
        gap = (f_lo - slope * (t - lo)) - t ** -0.5
        c0[addr] = min(round((f_lo - gap / 2) * 2**p.wc), 2**p.wc - 1)
        c1[addr] = round(slope * 2 ** (p.wc - (p.a - 1)))
    if (c1 >= 2**p.wc1).any():
        raise OverflowError('C1 does not fit wc1 bits')
    return c0, c1


def model(p: Params, xs, c0_table, c1_table):
    x_norm, s = normalize(p, xs)
    return newton(p, x_norm, s, seed(p, x_norm, c0_table, c1_table))


def rel_error(p: Params, xs, y1):
    np = _np()
    exact = 1 / np.sqrt(xs.astype(np.float64))
    return np.abs(y1 / 2.0**p.out_bits - exact) / exact


def tune_table(p: Params, xs, c0, c1, span: int = 6):
    """Per entry, choose C0 + k (|k| <= span) minimising that entry's worst final error."""
    np = _np()
    x_norm, s = normalize(p, xs)
    addr = x_norm >> (p.width - p.a)
    n = len(c0)
    best_err = np.full(n, np.inf)
    best_k = np.zeros(n, dtype=np.int64)
    for k in range(-span, span + 1):
        trial = np.clip(c0 + k, 1, 2**p.wc - 1)
        try:
            err = rel_error(p, xs, newton(p, x_norm, s, seed(p, x_norm, trial, c1)))
        except OverflowError:
            continue
        per = np.full(n, -np.inf)
        np.maximum.at(per, addr, err)
        better = per < best_err
        best_err[better], best_k[better] = per[better], k
    return np.clip(c0 + best_k, 1, 2**p.wc - 1)


def build(p: Params, c0_table, c1_table, *, compute_only: bool = False):
    import kickmix as km
    from invsqrt import nr_reference_circuit as nr

    b = km.CircuitBuilder()
    x = b.create_quantum_register(p.width, name='x')
    flags = b.alloc_qubits(p.n_p)
    c0 = b.alloc_qubits(p.wc)
    c1 = b.alloc_qubits(p.wc1)
    scratch = b.alloc_qubits(max(p.square, p.product + 2, p.result + 1, p.wc))
    addr = x[p.width - p.a:]
    table01 = [int(v0) | (int(v1) << p.wc) for v0, v1 in zip(c0_table, c1_table)]
    c1_list = [int(v) for v in c1_table]
    both = km.array(list(c0) + list(c1))

    def seed_rows(inverse: bool, c1):
        for i, sh in (reversed(p.rows()) if inverse else p.rows()):
            nr._add_row(b, inverse, x[i], [(c1[j], j - sh) for j in range(sh, p.wc1)], c0, scratch,
                        subtract=True)

    with b.mark('compute_y1'):
        nr._normalize(b, False, x, flags)
        b.init_lookup(table=table01, address=addr, target=both)
        seed_rows(False, c1)
        if p.free_c1:  # Hand C1's qubits back so the Newton registers reuse them.
            b.del_lookup(table=c1_list, address=addr, target=c1)
            b.free(c1)
        square, z = b.alloc_qubits(p.square), b.alloc_qubits(p.product + 2)
        y1 = b.alloc_qubits(p.out_bits)
        pp = y1[:len(y1) - len(flags)]
        nr._square(b, False, c0, square, scratch)
        nr._multiply_m(b, False, x, square, z, scratch)
        nr._correct(b, False, z)
        nr._multiply_y0(b, False, c0, z, pp, scratch)
        nr._denormalize(b, False, flags, y1)
    if compute_only:
        return b, y1
    nr._phase_by_bits(b, y1)
    with b.mark('uncompute_y1'):
        nr._denormalize(b, True, flags, y1)
        nr._multiply_y0(b, True, c0, z, pp, scratch)
        nr._correct(b, True, z)
        nr._multiply_m(b, True, x, square, z, scratch)
        nr._square(b, True, c0, square, scratch)
        b.free(y1)
        b.free(z)
        b.free(square)
        if p.free_c1:
            c1 = b.alloc_qubits(p.wc1)
            both = km.array(list(c0) + list(c1))
            b.init_lookup(table=c1_list, address=addr, target=c1)
        seed_rows(True, c1)
        b.del_lookup(table=table01, address=addr, target=both)
        nr._normalize(b, True, x, flags)
    b.free(scratch)
    b.free(c1)
    b.free(c0)
    b.free(flags)
    return b.finish_circuit()


def static_cost(p: Params, circuit, margin_turns: float) -> dict:
    from invsqrt import verify_submission_invsqrt as v
    st = circuit.operation_statistics()
    classes = [v.z_pow_class(Fraction(2) ** (j - p.out_bits + 1)) for j in range(p.out_bits)]
    n_rot, n_t = classes.count('rotation'), classes.count('t')
    eps = math.pi * margin_turns / n_rot
    t_total = n_t + n_rot * v.rotation_t_count(eps)
    c = st.num_toffoli_like + t_total / 4
    return {'qubits': circuit.num_qubits, 'toffolis_static': st.num_toffoli_like, 'n_rot': n_rot,
            'rot_eps': eps, 'C': c, 'cost_static_estimate': circuit.num_qubits * c}


def simulate_check(p: Params, circuit, xs_sample, y1_model) -> int:
    """Run sampled x through km.Simulator; compare the tracked phase with the model's y1."""
    import kickmix as km
    np = _np()
    from invsqrt import verify_submission_invsqrt as v
    batch = len(xs_sample)
    sim = km.Simulator(batch_size=batch, seed=12345)
    x_reg = km.array(list(circuit.register_data['x']))
    sim.write_across_shots(x_reg, v.to_bits(xs_sample.astype(np.uint64), p.width))
    sim.do(circuit)
    bad = 0
    for i in range(batch):
        got = Fraction(sim.read_shot_phase(i)) / 2 % 1  # half turns -> turns
        want = Fraction(int(y1_model[i]), 2**p.out_bits) % 1
        bad += got != want
    restored = (v.from_bits(sim.read_across_shots(x_reg)) == xs_sample.astype(np.uint64)).all()
    return bad + (0 if restored else batch)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('out_dir', type=pathlib.Path, nargs='?')
    for f in dataclasses.fields(Params):
        if f.type == 'bool' or isinstance(f.default, bool):
            ap.add_argument(f'--{f.name.replace("_", "-")}', action='store_true', default=f.default)
            ap.add_argument(f'--no-{f.name.replace("_", "-")}', dest=f.name, action='store_false')
        else:
            ap.add_argument(f'--{f.name.replace("_", "-")}', type=int, default=f.default)
    ap.add_argument('--check', type=int, default=0, help='simulate this many random x against the model')
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers']
    np = _np()

    p = Params(**{f.name: getattr(args, f.name) for f in dataclasses.fields(Params)})
    max_x = 3 * (2**p.n_p - 2)**2
    xs = np.arange(1, max_x + 1, dtype=np.int64)
    c0, c1 = initial_table(p)
    c0 = tune_table(p, xs, c0, c1)
    y1 = model(p, xs, c0, c1)
    rel = rel_error(p, xs, y1)
    tol = 2.0**-24
    margin = float(((tol - rel) / np.sqrt(xs.astype(np.float64))).min())
    report = {'params': dataclasses.asdict(p), 'worst_over_tol': float(rel.max() / tol),
              'worst_x': int(rel.argmax() + 1), 'margin_turns': margin}
    if margin <= 0:
        print(json.dumps({**report, 'feasible': False}))
        return
    circuit = build(p, c0, c1)
    report.update(feasible=True, **static_cost(p, circuit, margin))
    if args.check:
        rng = np.random.default_rng(0)
        sample = np.sort(np.concatenate([rng.integers(1, max_x + 1, args.check - 4), [1, 2, max_x - 1, max_x]]))
        report['sim_mismatches'] = simulate_check(p, circuit, sample, y1[sample - 1])
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        path = args.out_dir / 'invsqrt.kmb'
        circuit.to_file(str(path), format='kmb')
        (args.out_dir / 'params.json').write_text(json.dumps(
            {'generator': 'tasks/invsqrt/lut_nr.py', **report}, indent=2, default=float))
        report['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(report, default=float))


if __name__ == '__main__':
    main()
