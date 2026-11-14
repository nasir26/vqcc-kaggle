"""Per-function anatomy of Syed Asad Ali's v12 dqi generator (ours: instrumentation only).

Builds the decoder through a proxy CircuitBuilder that counts every Toffoli-like primitive (ccx, ccz, cswap,
init_and; broadcast over arrays) by the chain of generator-source frames that issued it, and samples the
allocated-qubit count at every builder call. No circuit file is written. Totals are checked against the
finished circuit's num_toffoli_like.

usage: python anatomy.py ROOT OUT.json [CUT]
"""
import collections, json, os, pathlib, sys, time
ROOT = pathlib.Path(sys.argv[1]).resolve(); OUT = str(pathlib.Path(sys.argv[2]).resolve()); CUT = int(sys.argv[3]) if len(sys.argv) > 3 else 15
sys.path.insert(0, str(ROOT / "controller_work" / "after_v3" / "integration_v7"))
os.chdir(ROOT)
import v7_pipeline as P
P.configure()
if CUT != 15:
    _orig = P.First3.emit_prefix
    def _cut(builder, words, carry, *, j_min=15, **kw):
        return _orig(builder, words, carry, j_min=CUT, **kw)
    P.First3.emit_prefix = _cut
import kickmix as km
R = str(ROOT) + "/"
TOFF = {"ccx", "ccz", "cswap", "init_and"}
chain = collections.Counter(); qpeak = {}; stage_T = collections.Counter(); stage_peak = {}
cur_stage = ["(start)"]; stages = []
raw = km.CircuitBuilder(); raw.set_max_qubits(889)

def nlen(x):
    if isinstance(x, (km.q, bool, km.b)): return 1
    try: return len(x)
    except TypeError: return 1

def isq(x):
    if isinstance(x, km.q): return True
    if isinstance(x, (km.b, bool, int)): return False
    try: return all(isinstance(e, km.q) for e in x)
    except TypeError: return False

def quantum_count(args):
    if not all(isq(x) for x in args): return 0
    return max(nlen(x) for x in args)

def frames():
    f = sys._getframe(2); out = []
    while f is not None:
        fn = f.f_code.co_filename
        if fn.startswith(R) and not fn.endswith("anatomy.py"):
            out.append(f"{pathlib.Path(fn).stem}.{f.f_code.co_name}")
        f = f.f_back
    return tuple(reversed(out))

class Proxy:
    def __init__(self, b): self._b = b
    def __getattr__(self, name):
        f = getattr(self._b, name)
        if not callable(f): return f
        def w(*a, **k):
            r = f(*a, **k)
            nq = self._b.num_allocated_qubits
            st = cur_stage[0]
            if nq > stage_peak.get(st, 0): stage_peak[st] = nq
            if name in TOFF:
                args = list(a) + list(k.values())
                n = quantum_count(args)
                key = frames()
                chain[key] += n; stage_T[st] += n
                if nq > qpeak.get(key, 0): qpeak[key] = nq
            elif name in ("alloc_qubits",):
                key = frames()
                if nq > qpeak.get(key, 0): qpeak[key] = nq
            return r
        return w
    @property
    def num_allocated_qubits(self): return self._b.num_allocated_qubits

b = Proxy(raw)
S = [raw.create_quantum_register(12, f"S{i}") for i in range(70)]
E = [raw.create_classical_register(12, f"E{i}") for i in range(4095)]
t0 = time.time()
def stage(m):
    name = m if isinstance(m, str) else str(m.get("stage", m)) if isinstance(m, dict) else str(m)
    stages.append(dict(stage=name, T_in_stage=stage_T[cur_stage[0]], peak_Q=stage_peak.get(cur_stage[0], 0), allocated=raw.num_allocated_qubits))
    cur_stage[0] = "after:" + name
P.emit(b, S, E, j_min=15, scan_positions=4095, stage=stage)
c = raw.finish_circuit(); st = c.operation_statistics()
tot = sum(chain.values())
res = dict(Q=c.num_qubits, T_static=st.num_toffoli_like, counted=tot, build_s=round(time.time() - t0), cut=CUT,
           stages=stages,
           chains=[dict(chain=list(k), T=v, peakQ=qpeak.get(k)) for k, v in chain.most_common()],
           alloc_peaks=[dict(chain=list(k), peakQ=v) for k, v in qpeak.items() if k not in chain])
json.dump(res, open(OUT, "w"), indent=0)
print(json.dumps({k: res[k] for k in ("Q", "T_static", "counted", "build_s")}))
