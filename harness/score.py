"""Score a submission directory with the official verifiers, exactly as the Kaggle metric does.

A submission directory has the layout of the zip: invsqrt.km[xb], dqi.km[xb] and dfthcsos/
(angle_k_*.km[xb] + submission.npz). Files are read and validated with the metric's own code
(harness/metric_vendor.py, vendored verbatim), and each task is verified by calling the same
verifier entry point with the same arguments as `generate_standard_submission`.

The leaderboard's baseline_cost is the *reference submission's* cost under the split's secret salt,
so ratio = cost_ref(salt) / cost(salt) is computed under the same salt here. Reference costs are
cached per (task, salt, reference sha256) in ledger/baseline_costs.json.

Usage (run from the repo root; data defaults to data/comp, or the Kaggle mount when present):
    python harness/score.py SUBMISSION_DIR [--tasks invsqrt dqi dfthcsos]
        [--salt S ...] [--random-salts N] [--stress K] [--note TEXT]

--salt '' (the default) gives publicly reproducible seeds. --random-salts N adds N fresh 32-char
salts (robustness: fresh HMR/R outcomes and, for dqi, fresh test errors). --stress K multiplies
shots (invsqrt shots_per_x, dqi num_shots, dfthcsos shots_per_address) by K; stress costs are not
official (dqi's eps_plus depends on N), so their ratio column is left empty.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import math
import pathlib
import secrets
import stat
import subprocess
import sys
import time
from typing import Any, Callable

REPO = pathlib.Path(__file__).resolve().parent.parent
SLUG = 'google-verifiable-quantum-circuit-compilation'
KAGGLE_DATA = pathlib.Path('/kaggle/input/competitions') / SLUG
TASKS = ('invsqrt', 'dqi', 'dfthcsos')
LEDGER_FIELDS = ['timestamp_utc', 'task', 'git_sha', 'params_json', 'qubits', 'toffolis', 't_gates', 'cost',
                 'ref_cost', 'ratio', 'verifier_pass', 'seeds', 'shots', 'circuit_sha256', 'notes']


def setup_paths(data_dir: pathlib.Path) -> None:
    """Put kickmix/ and verifiers/ from the competition data on sys.path, as the metric does."""
    for sub in ('kickmix', 'verifiers'):
        path = str(data_dir / sub)
        if path not in sys.path:
            sys.path.append(path)
    sys.path.insert(0, str(REPO / 'harness'))


def git_sha() -> str:
    try:
        out = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture_output=True, text=True)
        dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO, capture_output=True, text=True).stdout
        return out.stdout.strip() + ('-dirty' if dirty.strip() else '') if out.returncode == 0 else 'nogit'
    except OSError:
        return 'nogit'


def file_sha256(paths: list[pathlib.Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
    return h.hexdigest()


class Submission:
    """A submission directory, read and validated with the metric's code.

    File discovery happens up front (as the metric does); circuits are parsed lazily per task and
    released with `release(task)`, so a dqi run never holds two ~1 GB circuits at once.
    """

    def __init__(self, root: pathlib.Path, tasks: tuple[str, ...]):
        import metric_vendor as mv

        self.root = root.resolve()
        self._circuits: dict[str, Any] = {}
        self.files: dict[str, list[pathlib.Path]] = {}
        self._sha: dict[str, str] = {}
        if 'invsqrt' in tasks:
            self.files['invsqrt'] = [mv.find_one(self.root, 'invsqrt.km[xb]', 'invsqrt.kmx or invsqrt.kmb')]
        if 'dqi' in tasks:
            self.files['dqi'] = [mv.find_one(self.root, 'dqi.km[xb]', 'dqi.kmx or dqi.kmb')]
        if 'dfthcsos' in tasks:
            d = mv.find_one(self.root, 'dfthcsos', 'dfthcsos directory', is_dir=True)
            angle = {p.stem: p for p in d.glob('angle_k_*.km[xb]')}
            stems = [f'angle_k_{k}' for k in range(len(angle))]
            if not stems or sorted(angle) != sorted(stems):
                raise mv.ParticipantVisibleError('dfthcsos/ must hold angle_k_0 ... angle_k_<n-1>, each once.')
            self.files['dfthcsos'] = [angle[s] for s in stems] + [
                mv.find_one(d, 'submission.npz', 'dfthcsos/submission.npz')]

    def _read(self, path: pathlib.Path, reader: Callable, spec: Any) -> Any:
        import metric_vendor as mv
        st = path.lstat()  # Same guards as the metric's `read`.
        if not stat.S_ISREG(st.st_mode) or st.st_nlink > 1 or not path.resolve().is_relative_to(self.root):
            raise mv.ParticipantVisibleError(f'{path} must be a regular file.')
        return reader(path, spec)

    def circuit(self, task: str) -> Any:
        if task in self._circuits:
            return self._circuits[task]
        import metric_vendor as mv
        from dfthcsos import verify as dfthcsos_verify
        from dfthcsos.scoreinfra.reference import ORBITALS
        from dqi import verify_submission_dqi as vdqi

        if task == 'invsqrt':
            value = self._read(self.files[task][0], mv.read_circuit, 1)
        elif task == 'dqi':
            spec = vdqi.ProblemSpecDQI.benchmark_instance()
            value = self._read(self.files[task][0], mv.read_circuit, spec.n + spec.m)
        else:
            *angle_paths, npz_path = self.files[task]
            circuits = [self._read(p, mv.read_circuit, dfthcsos_verify.QUBIT_CAP) for p in angle_paths]
            npz_spec = {
                'U': ('f', ('R', 'B', ORBITALS)),
                'W': ('f', ('R', 'B', 'C')),
                'H2_I': ('f', ('R', 'C')),
                'H1_I': ('f', ()),
                'Hsym_lower': ('f', (ORBITALS * (ORBITALS + 1) // 2,)),
                'tree_edges': ('iu', (ORBITALS - 1, 2)),
            }
            npz = self._read(npz_path, mv.read_npz, npz_spec)
            tree = npz.pop('tree_edges')
            value = (circuits, npz, tree)
        self._circuits[task] = value
        return value

    def release(self, task: str) -> None:
        self._circuits.pop(task, None)

    def sha(self, task: str) -> str:
        if task not in self._sha:
            self._sha[task] = file_sha256(self.files[task])
        return self._sha[task]


def run_verifier(task: str, sub: Submission, salt: str, stress: int, max_workers: int | None) -> dict[str, Any]:
    """Call the task's verifier exactly as the metric's `verifications` dict does (stress=1)."""
    from dfthcsos import verify as dfthcsos_verify
    from dqi import verify_submission_dqi as vdqi
    from invsqrt import verify_submission_invsqrt as vinv

    if task == 'invsqrt':
        spec = vinv.ProblemSpecInvSqrt.for_n_p(10, shots_per_x=vinv.DEFAULT_SHOTS_PER_X * stress)
        return vinv.verify(sub.circuit('invsqrt'), spec, salt=salt, max_workers=max_workers)
    if task == 'dqi':
        spec = vdqi.ProblemSpecDQI.benchmark_instance(num_shots=vdqi.DEFAULT_NUM_SHOTS * stress)
        return vdqi.verify(sub.circuit('dqi'), spec, salt=salt, max_workers=max_workers)
    circuits, npz, tree = sub.circuit('dfthcsos')
    return dfthcsos_verify.verify(circuits, npz, tree, salt=salt,
                                  shots_per_address=dfthcsos_verify.SHOTS_PER_ADDRESS * stress)


def ledger_row(task: str, result: dict[str, Any] | None, error: str | None, sub: Submission, salt: str,
               ref_cost: float | None, params: str, note: str, stress: int) -> dict[str, Any]:
    r = result or {}
    cost = r.get('score')
    ratio = ref_cost / cost if (cost and ref_cost and stress == 1) else ''
    notes = '; '.join(x for x in [note, f'stress x{stress}' if stress != 1 else '', f'ERROR: {error}' if error else ''] if x)
    return {
        'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        'task': task,
        'git_sha': git_sha(),
        'params_json': params,
        'qubits': r.get('num_qubits', ''),
        'toffolis': r.get('toffoli_count', ''),
        't_gates': r.get('t_count', ''),
        'cost': cost if cost is not None else '',
        'ref_cost': ref_cost if ref_cost is not None else '',
        'ratio': ratio,
        'verifier_pass': 'PASS' if result else 'FAIL',
        'seeds': f'salt={salt!r}',
        'shots': r.get('verified_shots', ''),
        'circuit_sha256': r.get('circuit_sha256') or r.get('submission_sha256') or sub.sha(task),
        'notes': notes,
    }


def append_ledger(path: pathlib.Path, row: dict[str, Any]) -> None:
    new = not path.exists() or path.stat().st_size == 0
    with path.open('a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('submission', type=pathlib.Path)
    ap.add_argument('--tasks', nargs='+', choices=TASKS, default=list(TASKS))
    ap.add_argument('--data', type=pathlib.Path, default=None, help='competition data dir (default: Kaggle mount or data/comp)')
    ap.add_argument('--reference', type=pathlib.Path, default=None, help='reference submission (default: DATA/sample_submission)')
    ap.add_argument('--salt', action='append', default=None)
    ap.add_argument('--random-salts', type=int, default=0)
    ap.add_argument('--stress', type=int, default=1)
    ap.add_argument('--max-workers', type=int, default=None)
    ap.add_argument('--ledger', type=pathlib.Path, default=REPO / 'ledger' / 'results.csv')
    ap.add_argument('--baseline-cache', type=pathlib.Path, default=REPO / 'ledger' / 'baseline_costs.json')
    ap.add_argument('--runs-dir', type=pathlib.Path, default=REPO / 'ledger' / 'runs')
    ap.add_argument('--note', default='')
    args = ap.parse_args()

    data = args.data or (KAGGLE_DATA if KAGGLE_DATA.exists() else REPO / 'data' / 'comp')
    setup_paths(data)
    reference_dir = args.reference or data / 'sample_submission'
    salts = (args.salt if args.salt is not None else ['']) + [secrets.token_hex(16) for _ in range(args.random_salts)]
    tasks = tuple(args.tasks)

    cand = Submission(args.submission, tasks)
    ref = Submission(reference_dir, tasks)
    params_path = args.submission / 'params.json'
    params = json.dumps(json.loads(params_path.read_text()), sort_keys=True) if params_path.exists() else ''
    cache = json.loads(args.baseline_cache.read_text()) if args.baseline_cache.exists() else {}
    args.runs_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, dict[str, Any]] = {}
    for salt in salts:
        for task in tasks:
            # Environment in the key: Kaggle's image and local numpy differ in the last ulp of dfthcsos.
            env = 'kaggle' if KAGGLE_DATA.exists() else 'local'
            key = f'{env}|{task}|{salt}|{ref.sha(task)}|stress{args.stress}'
            same = cand.sha(task) == ref.sha(task)
            t0 = time.monotonic()
            try:
                result, error = run_verifier(task, cand, salt, args.stress, args.max_workers), None
            except (AssertionError, ValueError, RuntimeError, KeyError) as err:  # The metric's failure set.
                result, error = None, f'{type(err).__name__}: {err}'
            seconds = time.monotonic() - t0
            if not same:
                cand.release(task)  # Never hold candidate and reference circuits at once.
            if result and same:
                cache[key] = result['score']  # Candidate is the reference: its cost is the baseline.
            if result and key not in cache:
                cache[key] = run_verifier(task, ref, salt, args.stress, args.max_workers)['score']
                ref.release(task)
            args.baseline_cache.write_text(json.dumps(cache, indent=2, sort_keys=True))
            row = ledger_row(task, result, error, cand, salt, cache.get(key), params, args.note, args.stress)
            append_ledger(args.ledger, row)
            stamp = row['timestamp_utc'].replace(':', '')
            (args.runs_dir / f'{stamp}_{task}.json').write_text(
                json.dumps({'salt': salt, 'seconds': seconds, 'error': error, 'result': result}, indent=2, default=str))
            summary.setdefault(salt, {})[task] = {'pass': bool(result), 'cost': row['cost'], 'ref_cost': row['ref_cost'],
                                                  'ratio': row['ratio'], 'seconds': round(seconds, 1), 'error': error}
            print(json.dumps({'salt': salt, 'task': task, **summary[salt][task]}), flush=True)

    for salt, per_task in summary.items():
        ratios = [v['ratio'] for v in per_task.values()]
        complete = set(per_task) == set(TASKS) and all(v['pass'] for v in per_task.values()) and all(ratios)
        geo = math.prod(ratios) ** (1 / len(ratios)) if complete else None
        print(json.dumps({'salt': salt, 'geometric_mean': geo,
                          'note': None if complete else 'needs all 3 tasks passing at stress 1'}))


if __name__ == '__main__':
    main()
