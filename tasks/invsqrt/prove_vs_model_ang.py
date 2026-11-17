"""Variant of prove_vs_model.py with the site angles from $ANG64 and the model written to $MODEL64 (ours).
Full-domain exact proof of an invsqrt kmx/kmb against OUR exact model (ours; uses Syed Asad Ali's Apache-2.0
symbolic checker whole_text_symbolic.prove_native_chunk unchanged, with its phase modulus set to the circuit's 2^64).

Model: ahoirg's K=6 table in tasks/invsqrt/syed_model.py (digest 219d2f76 at the 4560ac0c angles) with the 33 site
angles of dcde7078 on the 2^-64 grid:  phase64 = (phase50_k6 << 14) + sum_site (angle64_dc - angle50_k6 << 14) f_site.
Checks for every x in [1, 3133452] and every HMR transcript: x restored, scratch zero, resets clean, no HMR-dependent
fractional phase, phase == model exactly. Then reports the exact official min margin of the model.
Usage: python tasks/invsqrt/prove_vs_model.py CIRCUIT [workers]
"""
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import syed_model as M  # noqa: E402

TREE = M.REPO / 'data/work/inv_gen/b0/invsqrt_build.pP3Dk2/tree'
sys.path.insert(0, str(TREE / 'work/c10/narrow/checkpoint002/cleanroom/baseline_stage97/engine'))
sys.path.insert(0, str(TREE / 'work/c10/narrow/native/candidate01'))
sys.path.append(str(M.REPO / 'data/comp/kickmix'))
K6 = M.REPO / 'data/src_pull/nov13b/ahoirg_k6c_extracted'
# site angles of dcde7078 in units 2^-64 turn (site order base_i0..25, overflow_j0..6); read from its Z_POW lines
import os
DC64 = json.loads(Path(os.environ['ANG64']).read_text())['angles64']
MODEL_OUT = Path(os.environ['MODEL64'])
CHECKER_SHA = '5c8ac00c902d6d202bf2cb1cde47a8014047482876e356a0741c11c85e171220'


def model64():
    import table_feas as TF
    ang50 = json.loads((K6 / 'angles.json').read_text())['angles_units50']
    ch = M.chart()
    C = 2 * TF.D6
    U = M.numerator_U(ch, C=C, U0=TF.seed(C))
    p, _ = M.divide(ch, U)
    ph50, r = M.ring26_phase50(p, ch['e'], angles=tuple(ang50))
    assert hashlib.sha256(ph50.astype('<u8').tobytes()).hexdigest() == '219d2f764664c989ec87608f5843001b42cc1f1efd4e2a433705a82a450dade7'
    k = ch['e']
    out = ph50.astype(np.uint64) << np.uint64(14)
    for i in range(33):
        f = ((r >> i) & 1) if i < 26 else ((r >> (i - 26)) & 1) * (k > (i - 26))
        delta = (int(DC64[i]) - (int(ang50[i]) << 14)) % (1 << 64)
        out = out + f.astype(np.uint64) * np.uint64(delta)
    return out


_G = {}


def _init(path):
    import importlib.util
    import kickmix as km
    from branch_prover import Program, generated_text
    p = TREE / 'work/c10/narrow/native/candidate01/whole_text_symbolic.py'
    assert hashlib.sha256(p.read_bytes()).hexdigest() == CHECKER_SHA
    spec = importlib.util.spec_from_file_location('wts64', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CANDIDATE_MODULUS = 1 << 64
    text = Path(path).read_text() if str(path).endswith('.kmx') else generated_text(km.Circuit.from_file(str(path)))
    _G.update(mod=mod, prog=Program(text), want=np.load(MODEL_OUT))


def _chunk(se):
    s, e = se
    mod = _G['mod']
    out = []
    pend = [(s, e)]
    while pend:
        a, b = pend.pop()
        xs = np.arange(a, b, dtype=np.uint64)
        try:
            rec = mod.prove_native_chunk(_G['prog'], xs, _G['want'][a - 1:b - 1])
            out.append((a, b, rec['status'], rec['HMR_variables']))
        except mod.SymbolicLimitError:
            m = (a + b) // 2
            pend += [(a, m), (m, b)]
    return out


def main():
    path = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 32
    t0 = time.time()
    want = model64()
    MODEL_OUT.parent.mkdir(exist_ok=True, parents=True)
    np.save(MODEL_OUT, want)
    target, tol = M.reference()
    err = (want - target).view(np.int64)
    used = np.abs(err)
    slack = tol.astype(np.int64) - used
    marg = int(slack.min())
    chunks = [(s, min(s + 65536, M.MAX_X + 1)) for s in range(1, M.MAX_X + 1, 65536)]
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(path,)) as ex:
        res = [r for part in ex.map(_chunk, chunks) for r in part]
    covered = sum(b - a for a, b, _, _ in res)
    ok = covered == M.MAX_X and all(st.startswith('PROVED_EXACT') for _, _, st, _ in res)
    rep = dict(circuit=path, circuit_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
               status='PASS_EXACT_ALL_INPUTS_ALL_HMR_TRANSCRIPTS_VS_OUR_MODEL' if ok else 'FAIL', proved_inputs=covered,
               chunks=len(res), model64_sha256=hashlib.sha256(want.astype('<u8').tobytes()).hexdigest(),
               model_min_margin_units64=marg, model_argmin_x=int(np.argmin(slack)) + 1,
               checker_sha256=CHECKER_SHA, checker_modulus='2^64', seconds=round(time.time() - t0, 1))
    print(json.dumps(rep, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
