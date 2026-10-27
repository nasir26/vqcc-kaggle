"""Per-stage cost breakdown of the official invsqrt reference circuit (nr_reference_circuit.py).

Each stage of the reference is a static function of the register layout, so it is rebuilt alone on
a fresh CircuitBuilder with the reference's exact allocation; its Toffoli count and qubit count
(registers + the stage's own temporary ancillas) are read from the resulting circuit. The sum over
stages is checked against the full reference circuit.

Usage (WSL, repo root): python tasks/invsqrt/anatomy.py data/comp [--json out.json]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from fractions import Fraction

STAGES = ['normalize', 'select_interval', 'load_coefficients', 'horner', 'square', 'multiply_m',
          'correct', 'multiply_y0', 'denormalize']


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data', help='competition data dir (holds kickmix/ and verifiers/)')
    ap.add_argument('--n-p', type=int, default=10)
    ap.add_argument('--json', default=None)
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers']
    import kickmix as km
    import numpy as np
    from invsqrt import nr_reference_circuit as nr
    from invsqrt import verify_submission_invsqrt as v

    n_p, prec = args.n_p, nr.Precision()
    width, out_bits = 2 * n_p + 2, prec.output_bits(n_p)
    sizes = {'x': width, 'y1': out_bits, 'flags': n_p, 'selectors': 3,
             **{f'c{j}': prec.coef_bits for j in range(4)}, 'square': prec.square_bits,
             'z': prec.product_bits + 2,
             'scratch': max(prec.square_bits, prec.product_bits + 2, prec.result_bits + 1)}

    def layout(b: km.CircuitBuilder):
        """Allocate exactly as build_nr_circuit does (same order, same sizes)."""
        x = b.create_quantum_register(width, name='x')
        y1, flags, sel = b.alloc_qubits(out_bits), b.alloc_qubits(n_p), b.alloc_qubits(3)
        coefs = [b.alloc_qubits(prec.coef_bits) for _ in range(4)]
        square, z = b.alloc_qubits(prec.square_bits), b.alloc_qubits(prec.product_bits + 2)
        scratch = b.alloc_qubits(sizes['scratch'])
        return x, flags, sel, coefs, square, z, y1, scratch

    def stage_call(name, b, inverse, regs):
        x, flags, sel, coefs, square, z, y1, scratch = regs
        y0, p = coefs[0], y1[:len(y1) - len(flags)]
        calls = {
            'normalize': lambda: nr._normalize(b, inverse, x, flags),
            'select_interval': lambda: nr._select_interval(b, inverse, x, sel),
            'load_coefficients': lambda: nr._load_coefficients(b, prec, x, sel, coefs),
            'horner': lambda: nr._horner(b, inverse, prec, x, sel, coefs, scratch),
            'square': lambda: nr._square(b, inverse, y0, square, scratch),
            'multiply_m': lambda: nr._multiply_m(b, inverse, x, square, z, scratch),
            'correct': lambda: nr._correct(b, inverse, z),
            'multiply_y0': lambda: nr._multiply_y0(b, inverse, y0, z, p, scratch),
            'denormalize': lambda: nr._denormalize(b, inverse, flags, y1),
        }
        calls[name]()

    base_qubits = sum(sizes.values())
    rows = []
    for inverse in (False, True):
        for name in (reversed(STAGES) if inverse else STAGES):
            b = km.CircuitBuilder()
            stage_call(name, b, inverse, layout(b))
            c = b.finish_circuit()
            st = c.operation_statistics()
            rows.append({'stage': ('un:' if inverse else '') + name, 'toffolis': st.num_toffoli_like,
                         'ccx': st.get('CCX', 0), 'ccz': st.get('CCZ', 0), 'cswap': st.get('CSWAP', 0),
                         'hmr': st.get('HMR', 0), 'qubits': c.num_qubits,
                         'temp_ancilla': c.num_qubits - base_qubits})

    # Phase stage: classify Z_POW exponents exactly as the verifier does.
    exps = [Fraction(2) ** (j - out_bits + 1) for j in range(out_bits)]
    classes = [v.z_pow_class(e) for e in exps]
    n_rot = classes.count('rotation')

    full = nr.build_nr_circuit(n_p, prec=prec)
    fs = full.operation_statistics()
    total_stage = sum(r['toffolis'] for r in rows)

    # Error budget from the reference's own fixed-point model (exact replica of the circuit).
    max_x = 3 * (2**n_p - 2)**2
    xs = np.arange(1, max_x + 1)
    rel = nr.relative_error(n_p, prec, xs)
    worst = float(rel.max())
    tol = 2.0**-24
    eps = math.pi * (tol - worst) / n_rot  # Verifier: eps = pi * min_x(tol(x) - |err(x)|) / n_rot, in turns*pi;
    # min over x of tol(x)-|err(x)| in turns is (tol - rel(x)) / sqrt(x); its argmin need not be the worst x.
    margin_turns = float(((tol - rel) / np.sqrt(xs)).min())
    eps_exact = math.pi * margin_turns / n_rot
    t_rot = v.rotation_t_count(eps_exact)

    out = {
        'registers': sizes, 'register_qubits': base_qubits,
        'full': {'qubits': full.num_qubits, 'toffolis': fs.num_toffoli_like, 'num_ops': len(full)},
        'stage_toffoli_sum': total_stage,
        'stages': rows,
        'phase': {'bits': out_bits, 'clifford': classes.count('clifford'), 't': classes.count('t'),
                  'rotations': n_rot, 'eps': eps_exact, 't_per_rotation': t_rot,
                  'rotation_t_total': n_rot * t_rot, 'rotation_toffoli_eq': n_rot * t_rot / 4},
        'error': {'worst_rel': worst, 'worst_rel_log2': math.log2(worst), 'worst_over_tol': worst / tol,
                  'worst_x': int(rel.argmax() + 1), 'min_margin_turns': margin_turns},
    }
    print(json.dumps(out, indent=2))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(out, f, indent=2)


if __name__ == '__main__':
    main()
