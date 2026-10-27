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

**Next**
- Pull vqcc-verify v1 output → record baseline costs → reboot for WSL →
  git init + first commit → Phase 1 anatomy.
- Candidate dqi circuits (~0.9 GB) must reach Kaggle as private dataset
  versions; consider generating dqi circuits *inside* the kernel instead.
