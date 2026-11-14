"""Print Syed v12's own source ledger (per-component static T) after configure()."""
import os, sys, json, pathlib
ROOT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "controller_work" / "after_v3" / "integration_v7"))
os.chdir(ROOT)
import v7_pipeline as P
P.configure()
led = P.source_ledger()
print(json.dumps(led, indent=1, default=str)[:20000])
