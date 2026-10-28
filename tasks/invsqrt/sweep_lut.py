"""Coordinate-descent search over LUT-NR Params using the exact model + static circuit costs.

Every row (feasible or not) is appended to a CSV checkpoint; a rerun skips params already in it.
Costs are MODEL/STATIC ESTIMATES. Usage (WSL):
    python tasks/invsqrt/sweep_lut.py data/comp [--out data/search/invsqrt_lut.csv] [--span 3]
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import math
import os
import sys
import time

FIELDS = ('a', 'wc', 'd', 'square', 'product', 'result')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('--out', default='data/search/invsqrt_lut.csv')
    ap.add_argument('--span', type=int, default=3)
    ap.add_argument('--start', default='7,17,10,28,27,28')
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers', os.path.dirname(__file__)]
    import numpy as np
    import lut_nr as L

    xs = np.arange(1, 3 * (2**10 - 2)**2 + 1, dtype=np.int64)
    sqrt_x = np.sqrt(xs.astype(np.float64))
    cols = [*FIELDS, 'free_c1', 'feasible', 'reason', 'worst_over_tol', 'qubits', 'toffolis_static', 'C',
            'cost_static_estimate', 'seconds']
    done: dict[tuple, float] = {}
    if os.path.exists(args.out):
        with open(args.out) as f:
            for r in csv.DictReader(f):
                key = tuple(int(r[k]) for k in FIELDS) + (r['free_c1'] == 'True',)
                done[key] = float(r['cost_static_estimate']) if r['feasible'] == 'True' else math.inf
    fh = open(args.out, 'a', newline='')
    w = csv.DictWriter(fh, fieldnames=cols)
    if not done:
        w.writeheader()

    def cost(key: tuple) -> float:
        if key in done:
            return done[key]
        t0 = time.monotonic()
        p = L.Params(*key[:6], free_c1=key[6])
        row = dict(zip(FIELDS, key[:6]), free_c1=key[6], feasible=False, reason='')
        try:
            c0, c1 = L.initial_table(p)
            c0 = L.tune_table(p, xs, c0, c1, span=args.span)
            rel = L.rel_error(p, xs, L.model(p, xs, c0, c1))
            margin = float(((2.0**-24 - rel) / sqrt_x).min())
            row['worst_over_tol'] = float(rel.max() / 2.0**-24)
            if margin <= 0:
                row['reason'] = 'tolerance exceeded'
            else:
                row.update(feasible=True, **{k: v for k, v in L.static_cost(p, L.build(p, c0, c1), margin).items()
                                             if k in cols})
        except (OverflowError, ValueError, IndexError) as err:
            row['reason'] = f'{type(err).__name__}: {err}'
        row['seconds'] = round(time.monotonic() - t0, 1)
        w.writerow(row)
        fh.flush()
        done[key] = row['cost_static_estimate'] if row['feasible'] else math.inf
        print(json.dumps({k: row.get(k) for k in cols}), flush=True)
        return done[key]

    best = tuple(map(int, args.start.split(','))) + (True,)
    best_cost = cost(best)
    improved = True
    while improved:
        improved = False
        moves = [(i, s) for i in range(6) for s in (-1, -2, +1)] + [(6, None)]
        for i, s in moves:
            cand = list(best)
            if i == 6:
                cand[6] = not cand[6]
            else:
                cand[i] += s
                if cand[i] < 2:
                    continue
            cand = tuple(cand)
            c = cost(cand)
            if c < best_cost:
                best, best_cost, improved = cand, c, True
                print('IMPROVED', best, best_cost, flush=True)
    print('BEST', dict(zip((*FIELDS, 'free_c1'), best)), 'cost_static_estimate', best_cost, flush=True)


if __name__ == '__main__':
    main()
