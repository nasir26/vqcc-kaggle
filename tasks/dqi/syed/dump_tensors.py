"""Dump the live multiplication tensors of Syed v12 (in his bases) as hex a,b,c triples."""
import os, sys, pathlib
ROOT = pathlib.Path(sys.argv[1]).resolve(); OUTD = pathlib.Path(sys.argv[2]).resolve(); OUTD.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "controller_work" / "after_v3" / "integration_v7")); os.chdir(ROOT)
import v7_pipeline as P
P.configure()
import gf24_arithmetic as G, field_tensor as FT
t24 = G.tensor24(); t12 = FT.multiplication_tensor()
for name, t in (("t24", t24), ("t12", t12)):
    print(name, len(t), t[0])
    open(OUTD / f"{name}.txt", "w").write(" ".join(f"{a:x},{b:x},{c:x}" for a, b, c in t) + "\n")
mods = {n: m.__file__ for n, m in sys.modules.items() if m and getattr(m, "__file__", None) and str(ROOT) in m.__file__ and "tensor" in n}
print(mods)
