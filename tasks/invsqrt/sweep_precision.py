"""Screen nr_reference_circuit.Precision settings with the exact fixed-point model (no simulation).

For each Precision, `fixed_point_model` (an exact replica of the circuit's arithmetic) gives the
phase error at every x in [1, max_x]; the verifier's rotation eps follows from the smallest margin
min_x (tol(x) - |err(x)|). Q and Toffolis come from a static build (the reference structure has no
measurement-conditioned Toffolis, so static = per-shot mean). Cost = Q * (T + T_gates / 4) exactly
as the verifier computes it -- but these are MODEL ESTIMATES until the official verifier passes.

Search: coordinate descent from the reference Precision (each field +-1, accept the best cost),
then an exhaustive +-1 neighbourhood of the optimum. Rows are appended to a CSV checkpoint.

Usage (WSL): python tasks/invsqrt/sweep_precision.py data/comp [--out data/search/invsqrt_precision.csv]
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import itertools
import math
import os
import sys
import time
from fractions import Fraction

FIELDS = ('delta_bits', 'coef_bits', 'square_bits', 'product_bits', 'result_bits')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('--out', default='data/search/invsqrt_precision.csv')
    ap.add_argument('--n-p', type=int, default=10)
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers']
    import numpy as np
    from invsqrt import nr_reference_circuit as nr
    from invsqrt import verify_submission_invsqrt as v

    n_p = args.n_p
    max_x = 3 * (2**n_p - 2)**2
    xs = np.arange(1, max_x + 1)
    sqrt_x = np.sqrt(xs.astype(np.float64))
    tol_rel = 2.0**-24
    cache: dict[tuple, dict] = {}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    new_file = not os.path.exists(args.out)
    fh = open(args.out, 'a', newline='')
    writer = csv.DictWriter(fh, fieldnames=[*FIELDS, 'feasible', 'reason', 'worst_over_tol', 'margin_turns',
                                            'qubits', 'toffolis', 'n_rot', 'rot_eps', 't_total', 'C', 'cost',
                                            'seconds'])
    if new_file:
        writer.writeheader()

    def evaluate(p: tuple) -> dict:
        if p in cache:
            return cache[p]
        t0 = time.monotonic()
        prec = nr.Precision(*p)
        row = dict(zip(FIELDS, p), feasible=False, reason='')
        try:
            rel = nr.relative_error(n_p, prec, xs)
        except (OverflowError, ValueError) as err:
            row['reason'] = f'{type(err).__name__}: {err}'
        else:
            margin = float(((tol_rel - rel) / sqrt_x).min())  # turns; verifier's min_x(tol - |err|)
            row['worst_over_tol'] = float(rel.max() / tol_rel)
            row['margin_turns'] = margin
            if margin <= 0:
                row['reason'] = 'tolerance exceeded'
            else:
                circuit = nr.build_nr_circuit(n_p, prec=prec)
                st = circuit.operation_statistics()
                out_bits = prec.output_bits(n_p)
                classes = [v.z_pow_class(Fraction(2) ** (j - out_bits + 1)) for j in range(out_bits)]
                n_rot, n_t = classes.count('rotation'), classes.count('t')
                eps = math.pi * margin / n_rot
                t_total = n_t + n_rot * v.rotation_t_count(eps)
                c = st.num_toffoli_like + t_total / 4
                row.update(feasible=True, qubits=circuit.num_qubits, toffolis=st.num_toffoli_like,
                           n_rot=n_rot, rot_eps=eps, t_total=t_total, C=c, cost=circuit.num_qubits * c)
        row['seconds'] = round(time.monotonic() - t0, 1)
        writer.writerow(row)
        fh.flush()
        cache[p] = row
        print({k: row.get(k) for k in (*FIELDS, 'feasible', 'worst_over_tol', 'qubits', 'toffolis', 'cost',
                                       'reason')}, flush=True)
        return row

    def cost(p):
        r = evaluate(p)
        return r['cost'] if r['feasible'] else math.inf

    base = dataclasses.astuple(nr.Precision())
    best, best_cost = base, cost(base)
    improved = True
    while improved:  # Coordinate descent, steps of +-1 then -2 on each field.
        improved = False
        for i, step in itertools.product(range(len(FIELDS)), (-1, -2, +1)):
            cand = list(best)
            cand[i] += step
            cand = tuple(cand)
            if min(cand) < 2:
                continue
            c = cost(cand)
            if c < best_cost:
                best, best_cost, improved = cand, c, True
    for delta in itertools.product((-1, 0, 1), repeat=len(FIELDS)):  # Exhaustive +-1 neighbourhood.
        cand = tuple(b + d for b, d in zip(best, delta))
        c = cost(cand)
        if c < best_cost:
            best, best_cost = cand, c
    print('BEST', dict(zip(FIELDS, best)), 'cost', best_cost, 'baseline', cost(base),
          'ratio', cost(base) / best_cost, flush=True)


if __name__ == '__main__':
    main()
