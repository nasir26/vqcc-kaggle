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
inner, field, stage = collections.Counter(), collections.Counter(), collections.Counter()
STACK = []
LIVE = [0]
peak = collections.defaultdict(int)
low = {}
FIELD = 'arithmetic/field.py'


class Proxy:
    def __init__(self, b):
        self._b = b

    def __getattr__(self, name):
        f = getattr(self._b, name)
        if name == 'mark':
            import contextlib

            @contextlib.contextmanager
            def marked(label, *a, **k):
                STACK.append(label)
                with f(label, *a, **k):
                    yield
                STACK.pop()
            return marked
        if name in ('alloc_qubits', 'free'):
            def counted(*a, **k):
                r = f(*a, **k)
                if name == 'alloc_qubits':
                    LIVE[0] += int(a[0]) if a else int(k.get('n', 1))
                else:
                    x = a[0]
                    try:
                        n = sum(1 for q in x if isinstance(q, km.q))
                    except TypeError:
                        n = 1 if isinstance(x, km.q) else 0
                    LIVE[0] -= n
                lab = '/'.join(STACK[:1]) or '(no mark)'
                peak[lab] = max(peak[lab], LIVE[0])
                low[lab] = min(low.get(lab, LIVE[0]), LIVE[0])
                return r
            return counted
        if name not in ('init_and', 'ccx', 'cswap'):
            return f

        def wrapped(*a, **k):
            st = [fr for fr in traceback.extract_stack()[:-1] if fr.filename.startswith(src)]
            stage['/'.join(STACK) or '(no mark)'] += 1
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
print('--- by decoder stage (b.mark)')
for k, v in stage.most_common(30):
    print(f'{v:9d} {100 * v / tot:5.1f}%  {k}')
print('--- live qubits (excluding the 840 syndrome qubits) per top-level stage: min .. peak')
for k in peak:
    print(f'{k:20s} {low[k]:5d} .. {peak[k]:5d}')
print('--- by outermost field.py routine on the stack')
for k, v in field.most_common(20):
    print(f'{v:9d} {100 * v / tot:5.1f}%  {k}')
print('--- by innermost function')
for k, v in inner.most_common(25):
    print(f'{v:9d} {100 * v / tot:5.1f}%  {k}')
