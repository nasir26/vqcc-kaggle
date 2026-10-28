"""Emit an invsqrt candidate: the reference Newton-Raphson circuit at a chosen Precision.

Writes OUT_DIR/invsqrt.kmb and OUT_DIR/params.json (recorded in the ledger by harness/score.py).
Usage (WSL): python tasks/invsqrt/gen.py data/comp OUT_DIR --prec 12,17,28,27,28
"""
import argparse
import hashlib
import json
import math
import pathlib
import sys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('out_dir', type=pathlib.Path)
    ap.add_argument('--prec', required=True, help='delta,coef,square,product,result bits')
    ap.add_argument('--n-p', type=int, default=10)
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers']
    import numpy as np
    from invsqrt import nr_reference_circuit as nr

    prec = nr.Precision(*map(int, args.prec.split(',')))
    max_x = 3 * (2**args.n_p - 2)**2
    worst = float(nr.relative_error(args.n_p, prec, np.arange(1, max_x + 1)).max())
    if not worst < 2.0**-24:
        raise SystemExit(f'model worst relative error 2^{math.log2(worst):.3f} exceeds 2^-24')
    circuit = nr.build_nr_circuit(args.n_p, prec=prec)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    path = args.out_dir / 'invsqrt.kmb'
    circuit.to_file(str(path), format='kmb')
    params = {'generator': 'tasks/invsqrt/gen.py', 'algorithm': 'reference NR', 'precision': prec.__dict__,
              'model_worst_over_tol': worst / 2.0**-24}
    (args.out_dir / 'params.json').write_text(json.dumps(params, indent=2))
    print(json.dumps({'path': str(path), 'qubits': circuit.num_qubits,
                      'toffolis': circuit.operation_statistics().num_toffoli_like,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **params}))


if __name__ == '__main__':
    main()
