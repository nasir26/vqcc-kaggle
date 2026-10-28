"""Toffoli / ancilla unit costs of the kickmix GF(2^b) and integer primitives the dqi decoder uses.

Each primitive is built alone on fresh 12-bit registers; Toffolis = CCX + CCZ + CSWAP (static),
ancilla = num_qubits - declared register qubits.
Usage (WSL): python tasks/dqi/unit_costs.py data/comp
"""
import json
import sys

sys.path += [f'{sys.argv[1]}/kickmix']
import kickmix as km  # noqa: E402

D = 12
gf = km.GF2Field(D)


def cost(name, body, nregs=2, extra=0):
    b = km.CircuitBuilder()
    regs = [b.create_quantum_register(D, name=f'r{i}') for i in range(nregs)]
    ctl = b.create_quantum_register(1, name='c')[0] if extra else None
    body(b, regs, ctl)
    c = b.finish_circuit()
    declared = nregs * D + (1 if extra else 0)
    st = c.operation_statistics()
    return name, {'toffolis': st.num_toffoli_like, 'cswap': st.get('CSWAP', 0), 'ancilla': c.num_qubits - declared,
                  'hmr': st.get('HMR', 0)}


def div_roundtrip(b, r, _):
    t, s = b.init_gf2_div_with_scaffold(r[0], r[1], field=gf)
    b.del_gf2_div_with_scaffold(r[0], r[1], target=t, scaffold=s, field=gf)
    b.free(s + t)


def inv_roundtrip(b, r, _):
    t, s = b.init_gf2_inverse_with_scaffold(r[0], field=gf)
    b.del_gf2_inverse_with_scaffold(r[0], target=t, scaffold=s, field=gf)
    b.free(s + t)


def mul_roundtrip(b, r, _):
    t = b.init_gf2_mul(r[0], r[1], field=gf)
    b.del_gf2_mul(r[0], r[1], target=t, field=gf)
    b.free(t)


rows = dict([
    cost('ixor_gf2_mul', lambda b, r, c: b.ixor_gf2_mul(r[0], r[1], target=r[2], field=gf), nregs=3),
    cost('ixor_gf2_mul controlled', lambda b, r, c: b.ixor_gf2_mul(r[0], r[1], target=r[2], field=gf, control=c), nregs=3, extra=1),
    cost('init+del gf2_mul', mul_roundtrip),
    cost('init+del gf2_div_with_scaffold', div_roundtrip),
    cost('init+del gf2_inverse_with_scaffold', inv_roundtrip, nregs=1),
    cost('gf2_phase_by_product (mask = classical reg)',
         lambda b, r, c: b.gf2_phase_by_product(r[0], r[1], mask=b.create_classical_register(D, name='mask'), field=gf)),
    cost('gf2_imul by constant', lambda b, r, c: b.gf2_imul(gf.primitive_element, target=r[0], field=gf), nregs=1),
    cost('gf2_iadd register controlled', lambda b, r, c: b.gf2_iadd(r[0], target=r[1], field=gf, control=c), extra=1),
    cost('cswap 12-bit', lambda b, r, c: b.cswap(c, r[0], r[1]), extra=1),
    cost('flip_if_equal(reg, 0)', lambda b, r, c: b.flip_if_equal(r[0], 0, target=c), nregs=1, extra=1),
    cost('init_and 12 (reg x ctl)', lambda b, r, c: (b.init_and(c, r[0], r[1]), b.del_and(c, r[0], r[1])), extra=1),
])
print(json.dumps(rows, indent=2))
