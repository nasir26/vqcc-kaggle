"""Instrumented re-run of Syed's build_variant.build (ours): every Toffoli-like builder call is attributed to its
Python call stack (module stem:function) with the live-qubit count at that moment; then aligned 1:1 with the
Toffoli-like ops of the emitted text to get each gate's exact expected execution probability.

Usage (from a relocated build tree): python syed_profile_build.py TREE OUT.json [extra patch ...]
Patches are read from TREE/patches/PATCH_ORDER.txt, extra patches appended.
"""
import json
import sys
import traceback
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

TREE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
EXTRA = sys.argv[3:]
sys.path.insert(0, str(TREE / 'tools'))
sys.path.insert(0, str(TREE / 'work/c10/narrow/arithmetic_round2/native/candidate10'))
import build_variant as bv  # noqa: E402
import arithmetic_variant  # noqa: E402,F401
import kickmix  # noqa: E402

REAL = kickmix.CircuitBuilder
TOFF = ('ccx', 'ccz', 'cswap')
RECORDS = []
STATE = dict(cond=0, peak=0)


def _stack():
    out = []
    for fr in traceback.extract_stack()[:-3]:
        p = Path(fr.filename)
        if 'syed_profile_build' in p.name or p.name in ('build_variant.py',):
            continue
        out.append(f'{p.stem}:{fr.name}')
    return out


class Proxy:
    def __init__(self, *a, **k):
        object.__setattr__(self, '_b', REAL(*a, **k))

    def __getattr__(self, name):
        attr = getattr(self._b, name)
        if not callable(attr):
            return attr
        b = self._b

        def call(*a, **k):
            if name in TOFF:
                RECORDS.append(dict(kind=name, stack=_stack(), live=b.num_allocated_qubits, cond=STATE['cond']))
            if name == 'push_condition':
                STATE['cond'] += 1
            if name == 'pop_condition':
                STATE['cond'] -= 1
            r = attr(*a, **k)
            if name in ('alloc_qubits',):
                RECORDS.append(dict(kind='alloc', stack=_stack(), live=b.num_allocated_qubits, cond=STATE['cond']))
            return r
        return call


kickmix.CircuitBuilder = Proxy
order = [l.split() for l in (TREE / 'patches/PATCH_ORDER.txt').read_text().splitlines() if l.strip()]
paths = [TREE / 'patches' / n for k, n in order if k == 'patch'] + [Path(p) for p in EXTRA]
patch = bv.PatchSet([bv.load_patch(p) for p in paths])
Q = int([n for k, n in order if k == 'Q'][0])
ctx, circuit, text, cuts, owner_trace, layout = bv.build(patch, Q)
sys.path.insert(0, str(TREE / 'work/c10/narrow/checkpoint002/cleanroom/baseline_stage97/tests'))
from fourier_resource_expectation import exact_expectation  # noqa: E402
rep = exact_expectation(text, include_gates=True)
gates = [g for g in rep['charged_gates'] if g['category'] == 'toffoli_like']
tof = [r for r in RECORDS if r['kind'] in TOFF]
print('builder toffoli calls', len(tof), 'text toffoli ops', len(gates), 'mean', rep['mean_numeric'])
assert len(tof) == len(gates)
for r, g in zip(tof, gates):
    r['p'] = g['probability']
    r['instr'] = g['instruction']
OUT.write_text(json.dumps(dict(records=RECORDS, cuts=[{k: c[k] for k in ('name', 'live_qubits', 'peak_so_far',
                                                                       'instruction_cut', 'cumulative_expected')}
                                                      for c in cuts], mean=rep['mean_numeric'],
                               zpow=[(i, str(op)) for i, op in enumerate(text.splitlines()) if op.startswith('Z_POW')])))
print('wrote', OUT)
