"""Simulation tests: TowerBuilder ops vs kickmix's own GF(2^12) ops (values, cleanup, phase).

Usage (WSL): python tasks/dqi/test_tower.py data/comp
"""
import os
import sys

sys.path += [f'{sys.argv[1]}/kickmix', os.path.dirname(__file__)]
import kickmix as km  # noqa: E402
import numpy as np  # noqa: E402
from tower_builder import TowerBuilder  # noqa: E402

N = 4096
GF = km.GF2Field(12)
rng = np.random.default_rng(1)


def bits(values, width=12):
    values = np.asarray(values, dtype=np.int64)
    return ((values[None, :] >> np.arange(width)[:, None]) & 1).astype(bool)


def ints(b):
    return (b.astype(np.int64) << np.arange(b.shape[0])[:, None]).sum(axis=0)


def run(build, inputs: dict, outputs: list[str]):
    """Build with `build(builder, regs)`, simulate, return (outputs, all_other_qubits_clean, phase_ok)."""
    raw = km.CircuitBuilder()
    b = TowerBuilder(raw)
    regs = {name: b.create_quantum_register(w, name=name) for name, (w, _) in inputs.items()}
    for name in outputs:
        if name not in regs:
            regs[name] = b.create_quantum_register(12, name=name)
    build(b, regs)
    c = raw.finish_circuit()
    sim = km.Simulator(batch_size=N, seed=7)
    sim.use_same_registers_as(c)
    for name, (w, vals) in inputs.items():
        sim.write_across_shots(regs[name], bits(vals, w))
    sim.do(c)
    named = {q for r in regs.values() for q in r}
    others = km.array([km.q(i) for i in range(c.num_qubits) if km.q(i) not in named])
    clean = (not len(others)) or not sim.read_across_shots(others).any()
    phase_ok = not sim.read_phase_flipped_across_shots().any()
    vals = {name: ints(sim.read_across_shots(regs[name])) for name in list(inputs) + outputs}
    st = c.operation_statistics()
    return vals, clean, phase_ok, st.num_toffoli_like, c.num_qubits


def check(label, ok):
    print(f'{"PASS" if ok else "FAIL"}  {label}')
    if not ok:
        global failures
        failures += 1


failures = 0
a_all = np.arange(N)
want_inv = np.array([GF.invert(int(x)) if x else 0 for x in a_all])

# Inverse: compute only.
vals, clean, ph, tof, q = run(lambda b, r: b.init_gf2_inverse_with_scaffold(r['a'], target=r['out'], field=GF),
                              {'a': (12, a_all)}, ['out'])
check(f'inverse value exhaustive (Toffolis {tof})', (vals['out'] == want_inv).all() and (vals['a'] == a_all).all())


def inv_roundtrip(b, r):
    out, sc = b.init_gf2_inverse_with_scaffold(r['a'], target=r['out'], field=GF)
    b.del_gf2_inverse_with_scaffold(r['a'], target=out, scaffold=sc, field=GF)
    b.free(sc)


vals, clean, ph, tof, q = run(inv_roundtrip, {'a': (12, a_all)}, ['out'])
check(f'inverse round trip clean/phase (Toffolis {tof}, qubits {q})',
      clean and ph and (vals['out'] == 0).all() and (vals['a'] == a_all).all())

# Multiply (uncontrolled and controlled), accumulating into a random target.
x, y, t0, ctl = rng.integers(0, N, N), rng.integers(0, N, N), rng.integers(0, N, N), rng.integers(0, 2, N)
want = t0 ^ np.array([GF.mul(int(p), int(q)) for p, q in zip(x, y)])
vals, clean, ph, tof, q = run(lambda b, r: b.ixor_gf2_mul(r['x'], r['y'], target=r['t'], field=GF),
                              {'x': (12, x), 'y': (12, y), 't': (12, t0)}, [])
check(f'mul value/clean/phase (Toffolis {tof})', (vals['t'] == want).all() and clean and ph)
want_c = np.where(ctl == 1, want, t0)
vals, clean, ph, tof, q = run(lambda b, r: b.ixor_gf2_mul(r['x'], r['y'], target=r['t'], field=GF, control=r['c'][0]),
                              {'x': (12, x), 'y': (12, y), 't': (12, t0), 'c': (1, ctl)}, [])
check(f'controlled mul value/clean/phase (Toffolis {tof})', (vals['t'] == want_c).all() and clean and ph)

# Division vs kickmix's own division (including zero divisors).
y0 = y.copy()
y0[:64] = 0


def km_div(b, r):
    ratio, sc = b._b.init_gf2_div_with_scaffold(r['x'], r['y'], target=r['out'], field=GF)


vals_km, *_ = run(km_div, {'x': (12, x), 'y': (12, y0)}, ['out'])
vals, clean, ph, tof, q = run(lambda b, r: b.init_gf2_div_with_scaffold(r['x'], r['y'], target=r['out'], field=GF),
                              {'x': (12, x), 'y': (12, y0)}, ['out'])
check(f'div value matches kickmix incl. zero divisor (Toffolis {tof})', (vals['out'] == vals_km['out']).all())


def div_roundtrip(b, r):
    ratio, sc = b.init_gf2_div_with_scaffold(r['x'], r['y'], target=r['out'], field=GF)
    b.del_gf2_div_with_scaffold(r['x'], r['y'], target=ratio, scaffold=sc, field=GF)
    b.free(sc)


vals, clean, ph, tof, q = run(div_roundtrip, {'x': (12, x), 'y': (12, y0)}, ['out'])
check(f'div round trip clean/phase (Toffolis {tof}, qubits {q})',
      clean and ph and (vals['out'] == 0).all() and (vals['x'] == x).all() and (vals['y'] == y0).all())

print('FAILURES', failures)
sys.exit(1 if failures else 0)
