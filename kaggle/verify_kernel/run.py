"""Kaggle script kernel: run harness/score.py on a submission inside the official image.

The harness comes from the private dataset spinwave/vqcc-harness; the competition data (kickmix.so,
verifiers/, sample_submission/) from the competition mount. Outputs land in /kaggle/working/vqcc/ledger.
Edit SUBMISSION / EXTRA_ARGS before pushing (tools/kaggle_verify.ps1 does this).
"""
import glob
import os
import pathlib
import shutil
import subprocess
import sys

SLUG = 'google-verifiable-quantum-circuit-compilation'
SUBMISSION = f'/kaggle/input/competitions/{SLUG}/sample_submission'
EXTRA_ARGS = ['--note', 'kaggle baseline reproduction']

harness_src = next(pathlib.Path(p).parent for p in glob.glob('/kaggle/input/**/score.py', recursive=True)
                   if (pathlib.Path(p).parent / 'metric_vendor.py').exists())
work = pathlib.Path('/kaggle/working/vqcc')
shutil.copytree(harness_src, work / 'harness', dirs_exist_ok=True)
(work / 'ledger').mkdir(parents=True, exist_ok=True)

print('python', sys.version.split()[0], '| cpus', os.cpu_count(), '| harness', harness_src, flush=True)
print('submission', SUBMISSION, sorted(os.listdir(SUBMISSION)), flush=True)
cmd = [sys.executable, str(work / 'harness' / 'score.py'), SUBMISSION, *EXTRA_ARGS]
print('$', ' '.join(cmd), flush=True)
sys.exit(subprocess.run(cmd, cwd=work).returncode)
