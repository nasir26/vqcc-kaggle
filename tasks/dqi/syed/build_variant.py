"""Build a variant of Syed Asad Ali's v12 dqi decoder (Apache-2.0) with:
  * Ertugrul Ozer's extractor cutoff wrapper (j_min raised on P.First3.emit_prefix), CUT (default 18);
  * optional patch modules (ours) applied to the live module objects after configure();
  * areebbb's product-retention rewrite (241 products on the unmodified decoder) unless --no-retain.
usage: build_variant.py ROOT OUT.kmb [--cut 18] [--patch mod.py ...] [--no-retain] [--maxq 889]
"""
import argparse, hashlib, importlib.util, os, pathlib, sys, time
ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("out")
ap.add_argument("--cut", type=int, default=18)
ap.add_argument("--patch", nargs="*", default=[])
ap.add_argument("--no-retain", action="store_true")
ap.add_argument("--maxq", type=int, default=889)
a = ap.parse_args()
HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(a.root).resolve(); OUT = pathlib.Path(a.out).resolve(); OUT.parent.mkdir(parents=True, exist_ok=True)
patches = [pathlib.Path(p).resolve() for p in a.patch]
sys.path.insert(0, str(ROOT / "controller_work" / "after_v3" / "integration_v7"))
os.chdir(ROOT)
T0 = time.time()
import v7_pipeline as P
P.configure()
for p in patches:
    spec = importlib.util.spec_from_file_location(p.stem, p); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); m.apply(P); print("patched", p.name, flush=True)
if a.cut != 15:
    _orig = P.First3.emit_prefix
    def _cut(builder, words, carry, *, j_min=15, **kw):
        return _orig(builder, words, carry, j_min=a.cut, **kw)
    P.First3.emit_prefix = _cut
import kickmix as km
b = km.CircuitBuilder(); b.set_max_qubits(a.maxq)
S = [b.create_quantum_register(12, f"S{i}") for i in range(70)]
E = [b.create_classical_register(12, f"E{i}") for i in range(4095)]
P.emit(b, S, E, j_min=15, scan_positions=4095, stage=lambda m: None)
assert b.num_allocated_qubits == 840, b.num_allocated_qubits
c = b.finish_circuit(); NQ, NB, T = c.num_qubits, c.num_bits, c.operation_statistics().num_toffoli_like
print(f"built: Q {NQ}, static T {T}, {time.time()-T0:.0f}s", flush=True)
if a.no_retain:
    c.to_file(str(OUT), format="kmb")
else:
    sys.path.insert(0, str(HERE)); import retain_areebbb as retain
    kmx = str(OUT) + ".tmp.kmx"; kmx2 = str(OUT) + ".ret.kmx"
    c.to_file(kmx, format="kmx"); del c
    occ, idle, n = retain.scan(kmx, retain.read_registers(kmx))
    repl, post, st = retain.plan(occ, idle, first_new_bit=NB + 100008, n_lines=n, extra=[], max_hops=0)
    print("retention:", dict(st), flush=True)
    del occ, idle
    retain.rewrite(kmx, kmx2, repl, post)
    cr = km.Circuit.from_file(kmx2, format="kmx"); cr.to_file(str(OUT), format="kmb")
    T2 = cr.operation_statistics().num_toffoli_like
    assert cr.num_qubits == NQ and T - T2 == st["toffolis_saved"]
    print(f"retained: Q {cr.num_qubits}, static T {T2}", flush=True)
    os.remove(kmx); os.remove(kmx2)
h = hashlib.sha256(OUT.read_bytes()).hexdigest()
print(f"WROTE {OUT} sha256 {h} total {time.time()-T0:.0f}s", flush=True)
