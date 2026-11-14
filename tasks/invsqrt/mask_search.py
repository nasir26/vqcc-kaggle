"""Free table edits (ours): XOR masks on loaded table outputs cost only X gates (applied after the load, undone before the
decoder/cleanup). Effective table A' = A ^ mA, S' = S ^ mS. Per-v exact slack from table_feas.py; coefficient form
D = A + S - (S >> 6) - sum_j b_j c_j(S). Reports masks that raise the minimum slack (fixed dcde/K6 angles).
Usage: python tasks/invsqrt/mask_search.py"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import syed_model as M  # noqa: E402
SL = np.load(M.REPO / 'data/work/inv_gen/feas_slack.npy'); W = (SL.shape[1] - 1) // 2
d = json.loads((M.REPO / 'data/src_pull/nov13b/ahoirg_k6c_extracted/k6data.json').read_text())
D6 = np.array(d['D']); T = np.array(d['table']); v = np.arange(4096); seg = v >> 6; lo = v & 63
def Dof(A, S):
    A = A[seg]; S = S[seg]
    sub = sum(((lo >> j) & 1) * (((S + (1 << (4 - j))) >> (5 - j)) if j < 5 else S) for j in range(6))
    return A + S - (S >> 6) - sub
assert np.array_equal(Dof(T[:, 0], T[:, 1]), D6)
def score(D):
    idx = D - D6 + W
    if idx.min() < 0 or idx.max() > 2 * W: return -(1 << 62)
    return int(SL[v, idx].min())
base = score(D6); print('base', base)
res = []
for mA in range(1 << 10):
    for mS in range(8):
        A = T[:, 0] ^ mA; S = T[:, 1] ^ (mS << 1)
        s = score(Dof(A, S))
        if s >= base: res.append((s, mA, mS))
res.sort(reverse=True); print(res[:15])
