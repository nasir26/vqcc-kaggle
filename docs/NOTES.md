# NOTES — findings log

## 2026-10-27 — session 1 (Phase 0, partial)

**Environment**
- Windows 11, no git, no C++ compiler, no WSL. Anaconda install is broken
  (`DLLs/_ctypes.pyd`, `_socket.pyd` missing) — not used.
- Installed `uv` 0.13.6 (user scope, winget). Project venv `.venv`:
  Python 3.11.18, kaggle CLI 2.2.5, numpy, pybind11, setuptools.
- Kaggle auth: `KGAT_` token in `~/.kaggle/access_token` works. Default
  competition set via `kaggle config set -n competition`.
- `kaggle competitions pages … --content --page-name` flags are ignored when
  placed before `list`; `tools/fetch_pages.py` uses the API directly.

**Blockers**
- Data download → 403 until rules are accepted on the website.
- `kickmix/kickmix.so` is "built for the Kaggle notebook image" (Linux).
  The official verifier cannot run on native Windows with that binary.

**Facts learned**
- Verifiers are plain Python in `verifiers/{invsqrt,dqi,dfthcsos}/` and import
  kickmix. Each ships the generator script for its reference circuit
  (`nr_reference_circuit.py`, `dqi_reference_circuit.py`,
  `angle_k_reference_circuit.py`) — that's our Phase 1 starting point.
- dfthcsos starter kit is a separate dataset:
  `sohier/verifiable-circuit-compilation-starter-kit`.
- kickmix will move to PyPI; metric will migrate to that copy. Watch for
  version skew between dataset `.so` and PyPI.

**Paper read (arXiv:2610.23832v2, via summarising fetch — provisional)**
- Definitions folded into RULES.md §2a/2b. Λ/E_gap thresholds are floors.
- invsqrt baseline: normalise by leading-zero pairs → QROM + cubic poly seed
  → 1 Newton step → unary-controlled shift → Z_POW phasing → uncompute.
  Cross-check: (7988 − 7735)·4 ≈ 1012 T ≈ 37 rot × 27.3 T ⇒ ε ≈ 2⁻³⁹ per rot.
  Rotations are only ~3% of C; Toffolis dominate. Worst error 2^−25.07 vs
  tol 2^−24 ⇒ ~1 bit of slack the baseline leaves unspent.
- dqi baseline: synchronized EEA (Proos–Zalka) → Chien → Forney → phase →
  uncompute EEA. 63-Toffoli Karatsuba GF(2^12) mult, Itoh–Tsujii inversion.
  Q² weighting: −10% qubits ≈ −19% cost. R floor 1.19 at zero failures —
  accepting rare failures only pays if it buys large Q/T cuts.
- dfthcsos baseline: DFTHC + SOSSA block encoding, QROM lookups, Givens tree.

**WSL2 (decided: WSL2 + Ubuntu)**
- `wsl --install -d Ubuntu --no-launch` run elevated. CPU i5-8350U, firmware
  VT-x/SLAT enabled; Windows reports RebootPending → reboot required before
  WSL2 starts. After reboot: re-run install if distro not listed, then set up
  python3.11 venv + build-essential inside Ubuntu, repo under ~/vqcc or /mnt/c.

**Data + verifiers (rules accepted 2026-10-27)**
- Bundle downloaded/unzipped to data/comp (sizes match listing).
- Laptop: 7.9 GB RAM, 8 logical CPUs, 36 GB free. dqi verifier needs ~6 GB per
  worker → dqi cannot be verified locally. Decision (user): **hybrid** — WSL for
  invsqrt/dfthcsos/dev, private Kaggle notebooks for dqi + pre-submit checks.
- Verifier parallelism uses `fork`; on native Windows it would run serially.
- Metric: baseline_cost is the reference's cost *under the same secret salt*, so
  the harness scores candidate and reference under identical salts; reference
  ratio is 1.0 by construction. Meaningful reproduction check = documented
  costs (dfthcsos 3,355,599,588.3155365 at empty salt).
- MBU-conditioned Toffolis count only on shots where the measured bit is set
  (mean over shots) → measurement-based uncomputation is ~half price.
- dfthcsos: E_gap 3.9655 sits 1.3% above its floor 3.9149; Λ = 308 is 6× its
  floor. λ_eff ≈ √(2Λ·E_gap) → Λ is the classical lever, not E_gap.
  ANGLES = 85% of T_total; state-prep temp (544) dominates Q_total (730).

**Harness**
- harness/metric_vendor.py: verbatim metric code (tools/vendor_metric.py).
- harness/score.py: metric-identical reading + verifier calls; per-salt
  reference cache (ledger/baseline_costs.json), ledger rows, run JSONs.
- Kaggle: private dataset spinwave/vqcc-harness (harness code) + private
  script kernel spinwave/vqcc-verify (kaggle/verify_kernel). v1 pushed
  2026-10-27 running the reference submission, empty salt.

**Baseline reproduced (official verifiers, empty salt) — Phase 0 DONE**

| task | env | Q | Toffolis/shot | cost | time |
|---|---|---|---|---|---|
| invsqrt | Kaggle | 260 | 7,735 (+1 T, 37 rot @ ε=1.53e-12 → C 7,987.59) | 2,076,774.2337 | 726 s |
| dqi | Kaggle | 1,893 | 5,725,108.38 (static max 5,725,461) | 24,439,463,583,672.93 | 184 s |
| dfthcsos | Kaggle | 730 | 93,237 | 3,355,599,588.3155375 | 74 s |
| dfthcsos | WSL | 730 | 93,237 | 3,355,599,588.3155365 | 171 s |

Geometric mean 1.0. Kaggle vs local dfthcsos differ by 1 ulp-level (3e-16
rel; numpy/BLAS build) → baseline cache keys now include env.
- invsqrt worst |err|/tol = 0.477 at x = 2,588,411: >half the phase budget unused.
- dqi: 0 failures, ε₊ = 8.66e-4, R = 1.19126; mean error weight 31.0 of t = 35;
  1,893 qubits = 840 syndrome + 1,053 workspace; 49,154 classical bits.
- dfthcsos: error_2 = 18.64 mHa vs 20 limit (7% headroom), error_1 = 3.19 mHa;
  ANGLE circuits 119 qubits (12 sel + 96 words + 11 temp) vs cap 128.

**Env**
- WSL2 Ubuntu 26.04.1 (user `dell`), ~3 GB RAM visible. kickmix.so needs
  CPython **3.13**, glibc ≥ 2.34. Venv /opt/vqcc/venv (py 3.13.18, numpy 2.5.4,
  scipy 1.18.1, pandas 3.1.0) via tools/wsl_setup.sh. Kaggle image: py 3.13.15.
- git lives in WSL only: `wsl -d Ubuntu -u dell -- git -C /mnt/c/Users/dell/Work/vqcc ...`.
- Run harness locally: `wsl -d Ubuntu -u dell -- bash -c "cd /mnt/c/Users/dell/Work/vqcc && /opt/vqcc/venv/bin/python harness/score.py SUBDIR --tasks ..."`.
- Kaggle dataset spinwave/vqcc-harness is at the pre-env-key score.py; re-upload
  (`kaggle datasets version`) before the next Kaggle run.

## 2026-10-27/28 — session 1 (Phase 1: anatomy)

- WSL memory raised to 6 GB (+8 GB swap) via %UserProfile%\.wslconfig.
- Fixed venv: interpreter now under /opt/vqcc/python (was in /root → exit 126
  for user dell).
- docs/invsqrt_anatomy.md: 88.5% of Toffolis are multiplications, half of all
  Toffolis are the mirror uncompute; 231/260 qubits are named registers live
  for the whole circuit; error 0.477 of tolerance.
- docs/dfthcsos_anatomy.md: ANGLES = 85% of T ∝ K·(N+R·B); inner-prep temp
  544 = 75% of Q (model-chosen); Λ_h2 = 96% of Λ. Model reproduces baseline
  score exactly. Shipped 12-bit words are rounding-aware (naive 11-bit
  re-rounding → error_1 221 mHa) — lower brot needs re-quantization.
- docs/dqi_anatomy.md: EEA sweep 50% of T (controlled 75-Toffoli GF mults on
  73 slots × 444 iterations), Chien inversions 22.5% (4,095 × 315), polynomial
  storage 92.5% of Q (workspace 1,053 = 55.6%). gf2_phase_by_product and
  constant multiplies are Clifford (0 Toffolis).
- Attribution method that works with kickmix (no per-mark stats API):
  rebuild stages alone on the reference's exact layout (invsqrt) or replace one
  subroutine by a no-op and diff (dqi).

**Next best bet**: invsqrt idea B (precision sweep on the exact
fixed_point_model; no simulation needed to screen) + idea A (MBU uncompute),
then dfthcsos refit after downloading the starter-kit trainer.
- Candidate dqi circuits (~0.9 GB) must reach Kaggle as private dataset
  versions; consider generating dqi circuits *inside* the kernel instead.
