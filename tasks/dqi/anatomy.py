"""Toffoli/qubit attribution for the official dqi reference decoder (dqi_reference_circuit.py).

Subtractive attribution: the reference is rebuilt with one subroutine of ProosAndZalkaDecoder
replaced by a no-op (each subroutine frees what it allocates, so the build stays valid), and the
difference from the full circuit's static Toffoli count is that subroutine's cost (both EEA
directions together). Qubits: full num_qubits, plus the peak when the subroutine is removed.

Usage (WSL, ~6 GB): python tasks/dqi/anatomy.py data/comp [--json out.json] [--parts a,b,...]
"""
from __future__ import annotations

import argparse
import json
import sys
import time

PARTS = {
    # name: (method, whole-stage?)
    'initial_shift': '_initial_shift_loop',
    'eea_total': '_synchronized_eea',
    'chien_forney': '_chien_search_and_forney_mbuc',
    'eea.update_flag': '_update_flag',
    'eea.multiply_and_add_or_sub': '_multiply_and_add_or_sub',
    'eea.shift_b_array_right': '_shift_b_array_right',
    'eea.update_metadata': '_update_metadata',
    'eea.swap_a_and_b': '_swap_a_and_b',
    'eea.update_halting_counter': '_update_halting_counter',
    'eea.counter_controls': ('_counter_controls', '_del_counter_controls'),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('--json', default=None)
    ap.add_argument('--parts', default=','.join(PARTS))
    args = ap.parse_args()
    sys.path += [f'{args.data}/kickmix', f'{args.data}/verifiers']
    import kickmix as km
    from dqi import dqi_reference_circuit as ref

    m, n, degree = 4095, 70, 12

    def build(decoder_cls) -> dict:
        t0 = time.monotonic()
        b = km.CircuitBuilder()
        syn = [b.create_quantum_register(degree, name=f'S{i}') for i in range(n)]
        mbuc = [b.create_classical_register(degree, name=f'E{j}') for j in range(m)]
        decoder_cls(n, km.GF2Field(degree)).build_syndrome_decoding_mbuc(
            b, syndromes=syn, error_mbuc=mbuc, n_iters=ref.default_n_iters(n))
        c = b.finish_circuit()
        st = c.operation_statistics()
        out = {'toffolis': st.num_toffoli_like, 'ccx': st.get('CCX', 0), 'ccz': st.get('CCZ', 0),
               'cswap': st.get('CSWAP', 0), 'qubits': c.num_qubits, 'ops': len(c),
               'build_s': round(time.monotonic() - t0, 1)}
        del c, b
        return out

    def noop_cls(methods):
        methods = (methods,) if isinstance(methods, str) else methods
        attrs = {}
        for meth in methods:
            if meth == '_counter_controls':
                # Must still hand back 4 control qubits; allocate them without gates.
                attrs[meth] = staticmethod(lambda builder, *a, **k: builder.alloc_qubits(4))
            elif meth == '_del_counter_controls':
                attrs[meth] = staticmethod(lambda builder, counter, is_c3, is_hc_zero, ctrl: builder.free(ctrl))
            else:
                attrs[meth] = lambda self, *a, **k: None
        return type('Ablated', (ref.ProosAndZalkaDecoder,), attrs)

    full = build(ref.ProosAndZalkaDecoder)
    print(json.dumps({'full': full}), flush=True)
    rows = {}
    for name in args.parts.split(','):
        ab = build(noop_cls(PARTS[name]))
        rows[name] = {'toffolis': full['toffolis'] - ab['toffolis'],
                      'share': (full['toffolis'] - ab['toffolis']) / full['toffolis'],
                      'cswap': full['cswap'] - ab['cswap'],
                      'qubits_without': ab['qubits']}
        print(json.dumps({name: rows[name]}), flush=True)

    # Static register layout of build_syndrome_decoding_mbuc.
    mm = n + 3
    logm = mm.bit_length() + 1
    layout = {'syndromes (reg_a[3:])': n * degree, 'reg_a[0:3]': 3 * degree, 'reg_b': mm * degree,
              'n_A,n_B,n_a,n_b,n_q': 5 * logm, 'flag+counter': 3,
              'halting_counter': ref.default_n_iters(n).bit_length()}
    layout['persistent_total'] = sum(layout.values())
    layout['peak_temporary'] = full['qubits'] - layout['persistent_total']
    out = {'full': full, 'parts': rows, 'layout': layout, 'n_iters': ref.default_n_iters(n)}
    print(json.dumps(out, indent=2))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(out, f, indent=2)


if __name__ == '__main__':
    main()
