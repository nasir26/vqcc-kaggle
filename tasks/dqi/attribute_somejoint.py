"""Attribute the Toffolis of somejoint's 897-qubit dqi decoder (public, Apache-2.0) to the functions that issue them.

Builds the decoder through a proxy CircuitBuilder that counts init_and / ccx / cswap calls by the innermost calling
function in the decoder sources, and by the field-arithmetic routine (mul_xor etc.) when one is on the stack.
No circuit file is written.

usage: python tasks/dqi/attribute_somejoint.py SOURCE_DIR DATA_DIR
"""
import collections
import importlib.util
import json
import sys
import time
import traceback

src, data = sys.argv[1], sys.argv[2]
sys.path.insert(0, f'{data}/kickmix')
import kickmix as km  # noqa: E402

sys.modules['circ'] = km
inner, field = collections.Counter(), collections.Counter()
FIELD = 'arithmetic/field.py'


class Proxy:
    def __init__(self, b):
        self._b = b

    def __getattr__(self, name):
        f = getattr(self._b, name)
        if name not in ('init_and', 'ccx', 'cswap'):
            return f

        def wrapped(*a, **k):
            st = [fr for fr in traceback.extract_stack()[:-1] if fr.filename.startswith(src)]
            if st:
                last = st[-1]
                inner[f'{last.filename[len(src):].lstrip("/")}:{last.name}'] += 1
                fs = [fr for fr in st if fr.filename.endswith(FIELD)]
                field[f'field.{fs[0].name}' if fs else 'outside field.py'] += 1
            return f(*a, **k)
        return wrapped


spec = importlib.util.spec_from_file_location('dut', f'{src}/exp/r-main/stream/decode.py')
m = importlib.util.module_from_spec(spec)
sys.modules['dut'] = m
spec.loader.exec_module(m)
raw = km.CircuitBuilder()
b = Proxy(raw)
S = [raw.alloc_qubits(12) for _ in range(70)]
E = [raw.alloc_bits(12) for _ in range(4095)]
t0 = time.time()
m.decode(b, S, E)
c = raw.finish_circuit()
tot = sum(inner.values())
print(json.dumps({'Q': c.num_qubits, 'T_static': c.operation_statistics().num_toffoli_like,
                  'counted_calls': tot, 'build_s': round(time.time() - t0)}))
print('--- by outermost field.py routine on the stack')
for k, v in field.most_common(20):
    print(f'{v:9d} {100 * v / tot:5.1f}%  {k}')
print('--- by innermost function')
for k, v in inner.most_common(25):
    print(f'{v:9d} {100 * v / tot:5.1f}%  {k}')
