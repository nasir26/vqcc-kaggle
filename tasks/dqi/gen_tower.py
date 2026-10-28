"""dqi candidate: the reference Proos-Zalka decoder built through TowerBuilder (tower-field GF ops).

Usage (WSL or Kaggle): python tasks/dqi/gen_tower.py DATA_DIR [OUT_DIR] [--no-mul] [--no-inverse]
Prints static stats (Toffolis = static upper bound; the verifier's per-shot mean is <= this).
"""
import argparse
import hashlib
import json
import os
import pathlib
import sys
import time


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('out_dir', nargs='?', type=pathlib.Path)
    ap.add_argument('--no-mul', action='store_true')
    ap.add_argument('--no-inverse', action='store_true')
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers', os.path.dirname(os.path.abspath(__file__))]
    import kickmix as km
    from dqi import dqi_reference_circuit as ref
    from tower_builder import TowerBuilder

    m, n, degree = 4095, 70, 12
    t0 = time.monotonic()
    raw = km.CircuitBuilder()
    b = TowerBuilder(raw, replace_mul=not args.no_mul, replace_inverse=not args.no_inverse)
    syn = [b.create_quantum_register(degree, name=f'S{i}') for i in range(n)]
    mbuc = [b.create_classical_register(degree, name=f'E{j}') for j in range(m)]
    ref.ProosAndZalkaDecoder(n, km.GF2Field(degree)).build_syndrome_decoding_mbuc(
        b, syndromes=syn, error_mbuc=mbuc, n_iters=ref.default_n_iters(n))
    c = raw.finish_circuit()
    st = c.operation_statistics()
    q, tof = c.num_qubits, st.num_toffoli_like
    report = {'generator': 'tasks/dqi/gen_tower.py', 'replace_mul': not args.no_mul,
              'replace_inverse': not args.no_inverse, 'qubits': q, 'num_bits': c.num_bits,
              'toffolis_static': tof, 'ops': len(c), 'build_s': round(time.monotonic() - t0, 1),
              'cost_static_estimate_R1.19126': 1.1912604648115832 * q * q * tof,
              'ratio_estimate': 24439463583672.93 / (1.1912604648115832 * q * q * tof)}
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        path = args.out_dir / 'dqi.kmb'
        c.to_file(str(path), format='kmb')
        (args.out_dir / 'params.json').write_text(json.dumps(report, indent=2))
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 24), b''):
                h.update(chunk)
        report['sha256'] = h.hexdigest()
        report['bytes'] = path.stat().st_size
    print(json.dumps(report))


if __name__ == '__main__':
    main()
