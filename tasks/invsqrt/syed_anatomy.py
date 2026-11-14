"""Per-stage anatomy of a Syed-lineage invsqrt kmx (ours): exact expected Toffolis per instruction range,
live-qubit peak per range, and the Z_POW list. Uses the lineage's own exact_expectation (classical guards).
Usage: syed_anatomy.py TREE KMX [BUILD_JSON]"""
import sys, json, re
from pathlib import Path
from fractions import Fraction
tree = Path(sys.argv[1]); kmx = Path(sys.argv[2])
sys.path.insert(0, str(tree / 'work/c10/narrow/checkpoint002/cleanroom/baseline_stage97/tests'))
sys.path.insert(0, str(tree / 'work/c10/narrow/checkpoint002/cleanroom/baseline_stage97/engine'))
from fourier_resource_expectation import exact_expectation
from branch_prover import Program
text = kmx.read_text()
rep = exact_expectation(text, include_gates=True)
prog = Program(text)
ops = prog.operations
prob = {}
for g in rep['charged_gates']:
    prob[g['instruction']] = (g['category'], Fraction(g['probability']))
# live qubits: a qubit is live from first touch after being zero... approximate by alloc via first/last use per
# "lifetime" segments split at HMR/R (wire returns to 0). Track: live after first non-measure use until HMR/R.
live = set(); peak = []
for i, op in enumerate(ops):
    qs = [a for a in op.arguments if isinstance(a, str) and a.startswith('q')]
    if op.kind in ('HMR', 'R'):
        live.add(qs[0]); peak.append(len(live)); live.discard(qs[0]); continue
    for q in qs: live.add(q)
    peak.append(len(live))
json.dump(dict(prob={k: [v[0], str(v[1])] for k, v in prob.items()}, peak=peak,
               kinds=[op.kind for op in ops]), open(sys.argv[3] if len(sys.argv) > 3 else '/dev/null', 'w'))
print('total', rep['mean_numeric'], 'ops', len(ops))
