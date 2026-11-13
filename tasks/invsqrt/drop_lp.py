"""For each rotation k: remove it (its phase contribution is subtracted from e0) and re-solve the margin LP over the
remaining angles. Prints the best achievable margin (units 2^-64 turns). Uses profile.npz from angle_lp.py."""
import sys, os, re, pathlib
from fractions import Fraction
import numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path += [str(REPO / 'data/comp/kickmix'), str(REPO / 'data/comp/verifiers')]
from invsqrt import verify_submission_invsqrt as V
import angle_lp as A
prof, kmx = sys.argv[1], sys.argv[2]
d = np.load(prof); B = d['B']; e0 = d['e0']
spec = V.ProblemSpecInvSqrt.for_n_p(10)
_, tol = V.reference_values(spec, np.arange(1, spec.max_x + 1, dtype=np.uint64)); tol = tol.astype(np.int64)
lines, rot = A.parse(open(kmx).read())
ang = [Fraction(lines[i].split()[2]) for i in rot]
units = [int(a * 2**63) for a in ang]   # half-turns -> 2^-64 turn units
def one(k):
    keep = [j for j in range(B.shape[1]) if j != k]
    e = e0 - units[k] * B[:, k].astype(np.int64)
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        dd = A.lp(e, B[:, keep], tol, rounds=40)
    di = np.round(dd).astype(np.int64)
    e1 = e + B[:, keep].astype(np.int64) @ di
    return k, int((tol - np.abs(e1)).min())
ks = [int(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else list(range(B.shape[1]))
with ProcessPoolExecutor(int(os.environ.get('NW', '8'))) as ex:
    for k, m in ex.map(one, ks):
        print('drop', k, 'margin', m, flush=True)
