"""Toffoli / ancilla / HMR unit costs of primitives considered for invsqrt redesigns.

Usage (WSL): python tasks/invsqrt/unit_costs.py data/comp
"""
import json
import random
import sys

sys.path += [f'{sys.argv[1]}/kickmix']
import kickmix as km  # noqa: E402


def measure(name, n_addr_or_width, body):
    b = km.CircuitBuilder()
    declared = body(b)
    c = b.finish_circuit()
    st = c.operation_statistics()
    return name, {'toffolis': st.num_toffoli_like, 'ancilla': c.num_qubits - declared, 'hmr': st.get('HMR', 0)}


def lookup(addr_bits, width, uncompute):
    def body(b):
        a = b.create_quantum_register(addr_bits, name='a')
        t = b.create_quantum_register(width, name='t')
        table = [random.getrandbits(width) for _ in range(1 << addr_bits)]
        b.init_lookup(table=table, address=a, target=t)
        if uncompute:
            b.del_lookup(table=table, address=a, target=t)
        return addr_bits + width
    return body


def add_row_ref(width):
    def body(b):
        ctl = b.create_quantum_register(1, name='c')[0]
        src = b.create_quantum_register(width, name='s')
        tgt = b.create_quantum_register(width, name='t')
        scratch = b.alloc_qubits(width)
        b.init_and(ctl, src, scratch)
        b.iadd(scratch, target=tgt)
        b.del_and(ctl, src, scratch)
        b.free(scratch)
        return 1 + 2 * width
    return body


def add_controlled(width):
    def body(b):
        ctl = b.create_quantum_register(1, name='c')[0]
        src = b.create_quantum_register(width, name='s')
        tgt = b.create_quantum_register(width, name='t')
        b.iadd(src, target=tgt, control=ctl)
        return 1 + 2 * width
    return body


def add_plain(width):
    def body(b):
        src = b.create_quantum_register(width, name='s')
        tgt = b.create_quantum_register(width, name='t')
        b.iadd(src, target=tgt)
        return 2 * width
    return body


random.seed(0)
rows = {}
for addr in (5, 6, 7):
    rows.update([measure(f'init_lookup {1 << addr}x27', addr, lookup(addr, 27, False)),
                 measure(f'init+del_lookup {1 << addr}x27', addr, lookup(addr, 27, True))])
for w in (20, 28):
    rows.update([measure(f'AND-row + iadd + MBU ({w})', w, add_row_ref(w)),
                 measure(f'iadd controlled ({w})', w, add_controlled(w)),
                 measure(f'iadd plain ({w})', w, add_plain(w))])
print(json.dumps(rows, indent=2))
