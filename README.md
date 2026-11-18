> **Note (2026-11-09):** the code, data and reproduction scripts of this work are now maintained in [nasir26/vqcc-circuit-compilation](https://github.com/nasir26/vqcc-circuit-compilation) (currently private, to be published after review). This repository stays as it is for reference.

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
| v2 | 2026-10-29 | 20.291057 | 59.183589 | 9.850574 | 22.78536 | 22.78536 |
| v3 | 2026-11-10 | 21.967709 | 65.226367 | 11.218890 | 25.23787 | 25.23786 |
| v4 | 2026-11-11 | 22.125506 | 65.226367 | 11.233227 | 25.30892 | 25.30892 |
| v5 | 2026-11-12 | 22.198355 | 65.427517 | 11.289304 | 25.40483 | 25.40482 |
| v6 | 2026-11-13 | 25.906979 | 67.847839 | 11.336077 | 27.11056 | 27.11056 |
| v7 | 2026-11-13 | 26.366501 | 67.847839 | 11.361049 | 27.28992 | 27.28993 |
| v8 | 2026-11-14 | 26.366542 | 67.847839 | 11.369874 | 27.29700 | 27.29700 |
| v9 | 2026-11-14 | 26.412805 | 67.847839 | 11.369874 | 27.31296 | 27.31296 |
| v10 | 2026-11-14 | 26.412805 | 67.847839 | 11.375515 | 27.31747 | 27.31748 |
| v11 | 2026-11-17 | 27.765339 | 70.432290 | 11.388691 | 28.13517 | 28.09222 |
| v12 | 2026-11-17 | 27.765339 | 70.501000 | 11.388691 | 28.10134 | 28.14429 |
| v13 | 2026-11-17 | 27.853387 | 70.500950 | 11.388728 | 28.13105 | 28.17405 |
| v14 | 2026-11-18 | 27.879537 | 70.551340 | 11.388728 | 28.18959 | 28.18957 |

Every member is a public Apache-2.0 circuit, verified here with the official verifiers:

* invsqrt `e623b659`: output of the notebooks of busyaprime, kirilltym and leoprovorov.
* dqi `c300b06e`: the SomeJoint team's 897-qubit decoder (notebook `somejoint/quantum-circuits-22-75-local-gm-897-qubit-dqi`
  and others that ship it).
* v3 invsqrt `5061b3bb`: shipped by gengsr, alexchilton, heliosli, maoxin123 and rdaccel notebooks (Apache-2.0).
* v3 dqi `ddb3a087`: shipped by gengsr, kirilltym, atakanaldemir, alexchilton, maoxin123, ozertuu, rdaccel notebooks.
* v3 dfthcsos: marculera dataset `marculera/dfthc-c44-build` (Apache-2.0), DF-THC (8, 143, 44), 427 qubits, 14,928 Toffolis.
* v4 invsqrt `64b39a7d`: shipped by the alexchilton (`24-94-lb-verified-three-task-portfolio`) and manwithacat
  (`vqcc-hedge-wizardry-notebook`) notebooks (Apache-2.0).
* v4 dfthcsos `22b1be2a`: shipped by the maoxin123 notebook `lb-25-303-combined-invsqrt-refit-chem` (Apache-2.0).
* v5: the maoxin123 v22 public portfolio (Apache-2.0): invsqrt `9c708f7b` (Asterios Panoras splice on the
  manwithacat HW-25 circuit), dqi `eae396ba` (SomeJoint decoder with Atakan's GF64 inverse character patch),
  dfthcsos table `f21b8a87` (prvsiyan refit lineage) with maoxin123 v22 loaders (4,089 Toffolis per pass).
* v6 (all Apache-2.0 notebook outputs, 2026-11-13): invsqrt `321aff83` (shipped by areebbb, ozertuu,
  kirilltym, maoxin123 v25 and prvsiyan notebooks), dqi `821bf8d1` (areebbb `qai-fewer-toffolis-same-qubits-lb-27-08903`),
  dfthcsos `f90d6c66` (prvsiyan `verifier-guided-quantum-circuit-optimization`).
* v7: invsqrt `4560ac0c` (ahoirg `qcc-submit-verify-and-package`, Apache-2.0), dqi as v6, dfthcsos `b9dbe922`
  (atakanaldemir `quantum-circuits-iso-gap-dqi-h5`, Apache-2.0/CC0).
* v8: invsqrt `dcde7078` (alexchilton v151 angle refit of ahoirg's 64-row circuit, shipped by heliosli) and dfthcsos
  `434822f8` (heliosli), Apache-2.0.
* v14: public invsqrt `db1404e0` (leotang09 / maoxin123 lineage), dqi `940c4516` (evgendvorkin notebook; 20 salt
  geo mean 70.4744, worst 70.2287, both above 39bddea7), chemistry as v13. Public 28.18957, rank 269.
* v13: public invsqrt `9a78a646` (alexchilton / atakanaldemir shared products and controlled refits lineage),
  dqi `39bddea7` as v12, chemistry `889999b0` (leotang09 T7421). Public 28.17405, rank 210, unique score.
* v12: v11 with dqi `39bddea7` (sources manwithacat hedge wizardry, maoxin123 notebooks). Chosen by a 20 salt test:
  geometric mean 70.4087 against 70.4016 for 80ee0183, and its worst salt (70.1786) beats 80ee0183's known public
  salt value (70.110). Public salt drew the no fail case.
* v11: all public members: invsqrt `efd84ca5` (maoxin123 44 qubit lineage), dqi `80ee0183` (Syed v13 lineage with
  GF24 closings), chemistry `c4391ffc` (maoxin123 4,022 Toffoli loaders). Our invsqrt shaves do not port: efd84ca5
  already has a 7 AND decoder and a 4 AND cleanup. Measured nulls this round: dqi width floor
  (runs/dqi/20261117-0901-width-floor) and R7 chemistry (runs/dfthcsos/20261117-r7c58-null).
* v10: our invsqrt and dqi as v9; chemistry `58ae6c0d`, an unchanged public reproduction from the notebooks
  `atakanaldemir/qcc-gap-3-residue-repair-and-c43-native-compiler` and
  `mizeroluckygall/quantum-circuits-4033-chemistry-refit-guide` (Kaggle Apache-2.0); same reachable-state loader
  kind as v9 (tools/loader_contract.py: general contract FAIL, reachable PASS).
* v9: **our invsqrt `240ae447`**: dcde7078 with our address decoder (7 ANDs instead of 8, exhaustive search over
  decode orders) and our table cleanup (6 product banks instead of 8, exhaustive bank search in a changed GF(2)
  basis), proved exact on all 3,133,452 inputs and HMR transcripts (runs/invsqrt/20261114-clean6). Chemistry and dqi as v8.
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
