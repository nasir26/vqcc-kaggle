"""Kaggle GPU kernel: refit the FeMoCo76o113e DF-THC factorization with the starter kit's trainer.

Seeds from the provided baseline, keeps the competition's fixed symmetry shift (frozen) and the
verifier's floors as penalties (all inside starter_kit train_system), and trades factorization
error for a lower lambda_eff by raising epsilon_dfthc above the baseline's continuous error.
Outputs: /kaggle/working/<name>.npz (the starter's NPZ format, readable by the verifier).

Edit RUNS before pushing. Each run: (name, epochs, lr, rho, epsilon_dfthc).
"""
import glob
import json
import pathlib
import sys
import time

RUNS = [
    ('eps168_rho1e-4', 20000, 1e-4, 1e-4, 0.0168),
    ('eps168_rho1e-3', 20000, 1e-4, 1e-3, 0.0168),
]

trainer = next(pathlib.Path(p) for p in glob.glob(
    '/kaggle/input/**/starter_kit/starter/task1_factorization/train_df_thc_qaggle.py', recursive=True))
starter_kit = trainer.parents[2]
sys.path.insert(0, str(starter_kit))

import jax  # noqa: E402

print('jax', jax.__version__, 'devices', jax.devices(), flush=True)
from starter.task1_factorization import train_df_thc_qaggle as T  # noqa: E402

print('systems', list(T.SYSTEMS), 'fixed shifts', T.FIXED_SHIFTS_FILE, flush=True)
baseline = starter_kit / 'baselines' / 'FeMoCo76o113e_65_60_60_ep50000_seed0.npz'
summary = []
for name, epochs, lr, rho, eps in RUNS:
    t0 = time.time()
    out = f'/kaggle/working/{name}.npz'
    params, values = T.train_system('FeMoCo76o113e', epochs=epochs, lr=lr, rho=rho, epsilon_dfthc=eps,
                                    print_interval=1000, seed_solution_file=str(baseline), output_file=out)
    row = {'name': name, 'epochs': epochs, 'lr': lr, 'rho': rho, 'epsilon_dfthc': eps,
           'seconds': round(time.time() - t0),
           **{k: float(values[k]) for k in ('epsilon_fro', 'lambda_eff', 'Lambda', 'sos_gap') if k in values}}
    summary.append(row)
    print('RESULT', json.dumps(row), flush=True)
pathlib.Path('/kaggle/working/summary.json').write_text(json.dumps(summary, indent=2))
