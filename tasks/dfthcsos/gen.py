"""Assemble a dfthcsos candidate directory from an angle-word table.

Circuits: the official reference builder (example_submission/angle_k_reference_circuit.py, ordinary
QROM per batch) at the requested brot and J. submission.npz: the factorization arrays (U, W, H2_I,
H1_I, Hsym_lower) copied from FACTORIZATION.npz plus tree_edges from the words file.

Usage (WSL): python tasks/dfthcsos/gen.py data/comp FACTORIZATION.npz WORDS.npz OUT_DIR [--J 9]
J defaults to the largest batch that keeps every ANGLE_k within the 128-qubit cap.
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
    ap.add_argument('factorization')
    ap.add_argument('words')
    ap.add_argument('out_dir', type=pathlib.Path)
    ap.add_argument('--J', type=int, default=None)
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers']
    import numpy as np
    from dfthcsos import verify as V
    from dfthcsos.example_submission import angle_k_reference_circuit as akr

    with np.load(args.words, allow_pickle=False) as z:
        words, edges, brot = np.array(z['angle_words']), np.array(z['tree_edges']), int(z['brot'])
    with np.load(args.factorization, allow_pickle=False) as z:
        fac = {k: np.array(z[k]) for k in ('U', 'W', 'H2_I', 'H1_I', 'Hsym_lower')}
    rows = words.shape[0]
    sel = math.ceil(math.log2(rows))
    J = args.J or (V.QUBIT_CAP - sel - (sel - 1)) // brot
    circuits = akr.build_angle_k_family(words, brot, J)
    widest = max(c.num_qubits for c in circuits)
    if widest > V.QUBIT_CAP:
        raise SystemExit(f'ANGLE_k uses {widest} qubits > {V.QUBIT_CAP}')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    d = args.out_dir / 'dfthcsos'
    paths = akr.write_kmx_family(circuits, d, format='kmb', overwrite=True)
    np.savez(d / 'submission.npz', **fac, tree_edges=edges.astype(np.int64))
    params = {'generator': 'tasks/dfthcsos/gen.py', 'brot': brot, 'J': J, 'K': len(circuits),
              'angles_qubits_max': widest, 'factorization': args.factorization, 'words': args.words,
              'angles_toffoli_static_both_passes': 2 * sum(c.operation_statistics().num_toffoli_like for c in circuits)}
    (args.out_dir / 'params.json').write_text(json.dumps(params, indent=2))
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
    print(json.dumps({**params, 'circuits_sha256': h.hexdigest()}))


if __name__ == '__main__':
    main()
