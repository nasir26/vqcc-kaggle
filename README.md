# Verifiable Quantum Circuit Compilation (Kaggle): scoring harness, submissions and studies

Work for the Kaggle competition
[Google Quantum AI: Verifiable Quantum Circuit Compilation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation)
(paper: arXiv:2610.23832). Author: Nasir Ali.

The repository holds a scoring harness that reproduces the Kaggle metric exactly, the scripts that rebuild every
submission from public sources, and the studies of each task (cost anatomy, a flip graph search for GF(2^n)
multipliers, chemistry shape and copy studies). The findings log is `docs/NOTES.md`; the competition rules digest
is `docs/RULES.md`.

## Submissions

| Version | Date | invsqrt | dqi | dfthcsos | Local GM, salt '' | Public LB |
|---|---|---|---|---|---|---|
| v1 | 2026-10-29 | 20.291057 | 59.183589 | 9.836619 | 22.77459 | 22.77459 |
| v2 | 2026-10-29 | 20.291057 | 59.183589 | 9.850574 | 22.78536 | see `docs/NOTES.md` |

Every member is a public Apache-2.0 circuit, verified here with the official verifiers:

* invsqrt `e623b659`: output of the notebooks of busyaprime, kirilltym and leoprovorov.
* dqi `c300b06e`: the SomeJoint team's 897-qubit decoder (notebook `somejoint/quantum-circuits-22-75-local-gm-897-qubit-dqi`
  and others that ship it).
* dfthcsos, v1 `ee1619fc`: kirilltym's exact gauge (`kirilltym/quantum-circuits-exact-gauge-5-word-qrom`).
* dfthcsos, v2: `open_circuits_v33` circuits with `open_circuits_v34` weights from the dataset
  `dmitriigluzdov/vqcc-femoco-public-factorization`.

`manifests/portfolio_v*.sha256` pin every member byte for byte; `manifests/submissions.sha256` pins the uploaded
zips, which are also attached to the GitHub release `submissions-2026-10-29` in case a public source changes.

## Reproduce

1. **Python runtime.** The official `kickmix.so` needs glibc 2.34 or newer. On such a host a Python 3.13 venv in
   `../.venv` (one level above the repo) with `numpy==2.5.4 scipy==1.18.1 pandas==3.1.0 kaggle==2.2.5` is enough.
   On an older host (e.g. Ubuntu 20.04), with `W` the folder that contains this repo:
   ```
   python3 -m venv $W/.tools && $W/.tools/bin/pip install uv patchelf && $W/.tools/bin/uv python install 3.13
   tools/host_runtime.sh $W      # user level glibc 2.39 + libstdc++ 14 runtime, patched CPython, then $W/.venv
   ```
2. **Downloads** (about 3.7 GB; needs a Kaggle token in `~/.kaggle/access_token` and the competition joined):
   `tools/fetch_all.sh`. It fetches the competition data, the vendored metric, starter kit files, the public
   notebook outputs and the public chemistry dataset into `data/` (git ignored: competition data must not be
   redistributed).
3. **Rebuild the submissions:** `tools/build_portfolios.sh`. Stages every public member, assembles
   `data/candidates/portfolio_v1` and `portfolio_v2`, checks them against the manifests and writes the zips to
   `submissions/`.
4. **Score:** `../.venv/bin/python harness/score.py data/candidates/portfolio_v2 --random-salts 8`. Prints one JSON
   line per (salt, task) and appends to the ledger in `ledger/`. Salt '' reproduces the public leaderboard value.
5. **Upload** under the file name `submission.zip`:
   `kaggle competitions submit -c google-verifiable-quantum-circuit-compilation -f submission.zip -m "..."`.
   The CLI returned HTTP 400 for other file names. The metric rejects hardlinked files, so stage real copies.

## Layout

| Path | Contents |
|---|---|
| `harness/score.py` | Metric identical scoring (official verifiers, per salt reference costs, ledger) |
| `tools/` | Runtime, downloads, staging (`scan_public.py`, `stage_glz.py`), portfolio build, verification loops |
| `tasks/invsqrt/` | Cost anatomy, precision sweep, LUT seeded Newton generator |
| `tasks/dqi/` | Anatomy, tower field arithmetic, rank 42 GF(2^12) scheme (`scheme42.py`), flip graph searches (`flipgraph.c`, `flipsym.c`), stage and live qubit attribution of the public decoder |
| `tasks/dfthcsos/` | Anatomy, rounding studies, shape sweeps, copy pruning at fixed angle words |
| `kaggle/` | Kaggle kernel and dataset specs used for official verification runs |
| `ledger/` | Append only record of every scored run |
| `manifests/` | sha256 of every submitted member and zip |
| `results/` | Outputs of the searches (`results/dqi/fg*`, `fs12`, `scheme42.txt`) and verification logs |

Build the searches with `gcc -O3 -march=native -o flipgraph tasks/dqi/flipgraph.c` (and the same for `flipsym.c`).

## Licences

Code in this repository: Apache-2.0 (see `LICENSE`). The public circuits that the build scripts download remain
under their authors' Apache-2.0 licences; the sources are named above and in each staged `params.json`. Competition
data, starter kit files and the Kaggle metric are not included and are downloaded by `tools/fetch_all.sh`.
