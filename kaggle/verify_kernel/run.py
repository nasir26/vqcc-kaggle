"""Kaggle script kernel: run harness/score.py on candidate submissions inside the official image.

Inputs (all private): dataset spinwave/vqcc-harness (harness/*.py + baseline_costs.json) and dataset
spinwave/vqcc-candidates (candidate submission dirs + job.json). Without job.json the reference
submission is scored (baseline reproduction). Outputs land in /kaggle/working/vqcc/ledger.

job.json: {"jobs": [{"submission": "invsqrt_lut_best", "tasks": ["invsqrt"], "random_salts": 2,
                     "note": "..."}]}
"submission" is a directory name inside the candidates dataset, or "REFERENCE".
A job may instead carry "generate": ["tasks/dqi/gen_tower.py", "--flag", ...]: the script (shipped in
the harness dataset under tasks/) is run as `python SCRIPT DATA_DIR OUT_DIR ARGS...` with OUT_DIR in
/tmp (large circuits never land in /kaggle/working), and OUT_DIR is scored.
"""
import glob
import json
import os
import pathlib
import shutil
import subprocess
import sys

SLUG = 'google-verifiable-quantum-circuit-compilation'
REFERENCE = f'/kaggle/input/competitions/{SLUG}/sample_submission'


def find_dir_with(name: str) -> pathlib.Path | None:
    hits = glob.glob(f'/kaggle/input/**/{name}', recursive=True)
    return pathlib.Path(hits[0]).parent if hits else None


harness_src = next(pathlib.Path(p).parent for p in glob.glob('/kaggle/input/**/score.py', recursive=True)
                   if (pathlib.Path(p).parent / 'metric_vendor.py').exists())
work = pathlib.Path('/kaggle/working/vqcc')
shutil.copytree(harness_src, work / 'harness', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('tasks'))
tasks_src = next((pathlib.Path(p) for p in glob.glob('/kaggle/input/**/tasks', recursive=True)
                  if pathlib.Path(p).is_dir()), None)
DATA_DIR = f'/kaggle/input/competitions/{SLUG}'
(work / 'ledger').mkdir(parents=True, exist_ok=True)
if (harness_src / 'baseline_costs.json').exists():
    shutil.copy(harness_src / 'baseline_costs.json', work / 'ledger' / 'baseline_costs.json')

cand_root = find_dir_with('job.json')
jobs = (json.loads((cand_root / 'job.json').read_text())['jobs'] if cand_root else
        [{'submission': 'REFERENCE', 'tasks': ['invsqrt', 'dqi', 'dfthcsos'], 'random_salts': 0,
          'note': 'kaggle baseline reproduction'}])
print('python', sys.version.split()[0], '| cpus', os.cpu_count(), '| harness', harness_src,
      '| candidates', cand_root, flush=True)

status = 0
for job in jobs:
    if 'generate' in job:
        sub = f"/tmp/cand/{job['submission']}"
        gen = [sys.executable, str(tasks_src.parent / job['generate'][0]), DATA_DIR, sub, *job['generate'][1:]]
        print('$', ' '.join(gen), flush=True)
        if subprocess.run(gen, cwd=work).returncode:
            status = 1
            continue
    elif job['submission'] == 'REFERENCE':
        sub = REFERENCE
    else:
        sub = str(cand_root / job['submission'])
    cmd = [sys.executable, str(work / 'harness' / 'score.py'), sub, '--tasks', *job['tasks'],
           '--salt', '', '--random-salts', str(job.get('random_salts', 0)), '--note', job.get('note', '')]
    print('$', ' '.join(cmd), flush=True)
    status |= subprocess.run(cmd, cwd=work).returncode
sys.exit(status)
