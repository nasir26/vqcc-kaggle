"""Check ANGLE_k loaders against the general contract of eq. (72): |a>|z> -> |a>|z XOR Delta_k(a)> for ANY z.

The official verifier only feeds the reachable z (the previous batch). This tool feeds uniformly random z with the
real kickmix simulator and counts addresses whose output is not z XOR Delta_k(a), whose workspace is dirty, or whose
phase is flipped. Delta_k(a) is taken from the reachable run (batch_k XOR batch_{k-1}).

Usage: python tools/loader_contract.py DFTHCSOS_DIR [--shots 4]
"""
import argparse, glob, pathlib, sys
import numpy as np
REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path += [str(REPO / 'data/comp/kickmix'), str(REPO / 'data/comp/verifiers/dfthcsos')]
import kickmix as km
from scoreinfra.circuits import register_layout


def run(sim, circ, layout, sel_bits, z, brot):
    sim.clear_for_shot()
    sim.write_across_shots(layout.selection, sel_bits)
    for j, word in enumerate(layout.words):
        sim.write_across_shots(word, ((z[:, j][None, :] >> np.arange(brot)[:, None]) & 1).astype(bool))
    sim.do(circ)
    pv = np.int64(1) << np.arange(brot, dtype=np.int64)
    out = np.stack([pv @ sim.read_across_shots(w).astype(np.int64) for w in layout.words], axis=1)
    work = [km.q(i) for i in range(circ.num_qubits) if i not in layout.public_qubits]
    dirty = sim.read_across_shots(km.array(work)).any(axis=0) if work else np.zeros(len(z), bool)
    flip = np.asarray(sim.read_phase_flipped_across_shots(), bool)
    return out, dirty, flip


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--shots', type=int, default=4)
    a = ap.parse_args()
    files = sorted(glob.glob(a.dir + '/angle_k_*.km[bx]'), key=lambda s: int(s.rsplit('_', 1)[1].split('.')[0]))
    circs = [km.Circuit.from_file(f) for f in files]
    layout = register_layout(circs); brot, J = layout.brot, layout.batch_size
    A = int(np.load(a.dir + '/submission.npz')['angle_words'].shape[0])
    addr = np.tile(np.arange(A), a.shots); n = len(addr)
    sel = ((addr[None, :] >> np.arange(len(layout.selection))[:, None]) & 1).astype(bool)
    sim = km.Simulator(batch_size=n, debug_print=False, seed=12345, counting_operations=False)
    sim.use_same_registers_as(circs[0])
    rng = np.random.default_rng(7)
    prev = np.zeros((n, J), np.int64)
    bad_total = 0
    for k, c in enumerate(circs):
        reach, d0, f0 = run(sim, c, layout, sel, prev, brot)
        delta = reach ^ prev
        z = rng.integers(0, 1 << brot, size=(n, J))
        out, d1, f1 = run(sim, c, layout, sel, z, brot)
        bad = (out != (z ^ delta)).any(axis=1) | d1 | f1
        bad_addr = len(set(addr[bad].tolist()))
        bad_total += bad_addr
        print(f'{pathlib.Path(files[k]).name}: reachable ok {not (d0.any() or f0.any())}; random z: {bad_addr}/{A} addresses violate eq. (72)')
        prev = reach
    print('GENERAL CONTRACT', 'PASS' if bad_total == 0 else 'FAIL')


if __name__ == '__main__':
    main()
