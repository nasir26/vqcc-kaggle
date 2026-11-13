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

## 2026-10-28 — public notebooks (decision: study and build on them)

Public LB top 26.14; ≥ 12 teams at 23.7–26.1. Public notebooks publish
verified 21–22.7 portfolios. User chose to reproduce the best verified public
one through our harness and improve from there.

**External sources used (record per guardrail):**
- somejoint/quantum-circuits-22-67-local-gm-full-xor-chem (Agniv Banerjee /
  SomeJoint), states Apache-2.0. Output `submission.zip` downloaded unchanged
  to data/public_out/somejoint_22-67 (manifest SHA-256s checked). Its members:
  invsqrt = busyaprime v8 (dataset busyaprime/33-qcc-v8-members, Apache-2.0),
  dqi = heliosli v10 (notebook heliosli/the-dataset-is-now-public-now-enjoy,
  Apache-2.0), chemistry = SomeJoint team (dataset
  somejoint/qcc-our-chemistry-b143-c60-xor2). Long credit chains in the notebook.
- Pulled source (read-only, not executed) in data/public/: alexchilton 22.57,
  busyaprime 22.34, lightningv08 Bezout-Schur, ahmedberatozer DF-THC group
  compression, rudrabhaskar direct polynomial phasing.

Their claimed (official-verifier, default seed) numbers:
| task | Q | mean Toffolis | ratio |
|---|---:|---:|---:|
| invsqrt | 63 | 1,334.5 (static 1,402) | 20.23 (worst err 0.9993 tol) |
| dqi | 889 | 440,564 | 58.92 |
| dfthcsos | 430 | 16,366 (λ_eff 48.764; R8 B143 C60, 8-bit words, 15 five-word lookups) | 9.78 |

**Our reproduction of the public 22.67 (harness, empty salt):** dfthcsos
9.778170 (cost 343,172,572.78) and invsqrt 20.228799 (cost 102,664.24) — exact
match, local WSL. dqi pending on Kaggle v3 (job public_somejoint_2267_dqi.json).

**Superseded own work:**
- invsqrt LUT-NR: officially verified 1.7444 (3 salts, Kaggle) — public 63-qubit
  circuit is 20.23.
- dqi tower-field GF (mul 54, inv 77): public Schur decoder (jday96314/QuantumAI
  on GitHub, rebuilt by alexchilton) already runs on a **42-AND** GF(2¹²)
  multiplier and a tower inverse. Only lever there: a < 42-AND multiplier.
- dfthcsos GPU refit of the 65/60/60 baseline (kernel spinwave/vqcc-dfthc-train v1,
  2×GPU, ~100 ms/epoch): failed — eps 16.8/rho 1e-4 → λ_eff 50.86 (worse);
  rho 1e-3 → λ_eff 49.03 at ε_fro 19.9 mHa (no rounding room); epoch-0 error
  197 mHa (seed/frozen-shift mismatch) and late divergence (122 mHa at ep 19,990).
  Obsolete anyway vs the public R8 B143 factor.

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

## 2026-10-29 — session on the new host (Ubuntu 20.04, 256 cores, 503 GB)

- Runtime: host glibc 2.31 < kickmix.so's GLIBC_2.34/GLIBCXX_3.4.32. `tools/host_runtime.sh` unpacks Ubuntu
  24.04 libc6 2.39 + libstdc++6 14 into ../rt/lib and patches a private CPython 3.13.18 (interpreter + RPATH),
  so fork and spawn workers both load the official kickmix.so. All three reference costs reproduce exactly
  (dfthcsos 3355599588.3155365, invsqrt 2076774.233715282, dqi 24439463583672.93); full run ~100 s (dqi local).
- Frontier refresh: LB top 26.14113 (Breaking1800, unchanged since 10-28 04:40); ranks 3-7 at 24.56-24.92.
  Public composites: somejoint 22.75 (897Q dqi), busyaprime 22.72, heliosli v12 22.70.
- `tools/scan_public.py` staged 13 distinct public task members from 12 notebook outputs; all PASS in our
  harness (salt ''), matching their published numbers. Best per task: invsqrt e623b659 20.291057
  (busyaprime/kirilltym/leoprovorov), dqi c300b06e 59.183589 (somejoint 897Q and others), dfthcsos ee1619fc
  9.836619 (kirilltym exact gauge). Sources: Kaggle notebook outputs, Apache-2.0 per competition rules.
- portfolio_v1 = those three: PASS on salt '' + 5 random salts; GM 22.7746 (dqi 0 failures, 2 salts) or 22.7398
  (dqi 1 failure, 4 salts). Packaged as submissions/2026-10-29_v1.zip, awaiting human approval to upload.
- dfthcsos analysis: E_gap is already at its floor in public entries, so lambda_eff ~ sqrt(2 E_gap Lambda);
  Lambda = lam_h1 + lam_h2, lam_h2 = 291.7 on the best public factor. Replacing sum|w_b| by the nuclear norm of
  each X_rc (best possible re-representation of the same X) only saves 4.2%: real gains need a new
  factorization (CPU optimisation on this host; no GPU).
- Submitted v1 to Kaggle 2026-10-29 (user approved): submissions/2026-10-29_v1.zip, sha e6f49334...
- somejoint's 22.75 notebook embeds the full generator of the 897-qubit dqi decoder (Apache-2.0, `SOURCES` dict;
  extracted as text to data/public/somejoint__.../src). Its GF(2^12) multiplier `tensor(12)` is evaluation/
  interpolation over GF(8) (degree 4, 7 points incl. infinity, 6-AND GF(8) products): rank 42, symmetric masks.
  Running that external code on this host is blocked by the permission system until the user allows it.
- tasks/dqi/flipgraph.c: own flip-graph search (Kauers–Moosbauer) for GF(2^n) multiplication schemes; every
  improvement verified against the full tensor. Validation: GF(2^4) reaches 9 (optimum), GF(2^6) reaches the
  known optimum 15 in 14 of 64 long walks. Launched GF(2^12), modulus 4179, target <= 41, 200 seeds x 3 h
  (results/dqi/fg12/). Value if found: every multiplier in the decoder is 42 ANDs, so rank r gives about
  (42 - r)/42 of the multiplier's share of dqi Toffolis (share still to be measured).
- v1 public LB score 22.77459 (2026-10-29): equals our local salt-'' value with dqi at 0 failures, so the harness predicts the LB exactly.
- Literature/forum sweep 2026-10-29 (forum threads saved in data/forum/, via KaggleApi.competition_list_topic_messages):
  * arXiv 2502.15882 (spectrum amplification, DFTHC): FeMoco-76 at (R,B,C) = (15,57,19), Lambda 179.7, lambda_eff 43.65,
    but eps_fro 82.5 mHa (4x the competition's 20 mHa gate): not transferable.
  * Forum 753633: with the verifier's fixed S, beta_1, lambda_eff >= 46.79 for any factorization (public 48.70):
    chemistry gains must come from T x Q. Forum 753185 (+manwithacat): Eckart-Young floor R*C >= 290 at 20 mHa;
    brot 7 and re-rounding fail; 72.3% of a BM decoder's Toffolis are 42-AND GF multiplies; invsqrt is precision-
    saturated everywhere (rotations cannot be cheapened); 63 -> 62 qubits closed by manwithacat.
  * arXiv 2610.22367 (Gu et al.): BM decoder ~440k Toffolis but ~1,837 qubits: worse than the public 897Q.
- dmitriigluzdov/vqcc-femoco-public-factorization (Apache-2.0, 194 MB): factorizations (65x60x30, 32x60x30,
  THC (1,496,384) lambda_eff 47.86, mrmeows R4 refits) plus circuit generator sources and archived circuit sets.
  All 12 chemistry sets verified (salt ''): best v33 circuits + v34 weights = 9.850574 (vs our 9.836619).
- Automorphism angle: tasks/dqi/flipsym.c searches Frobenius-invariant schemes in a normal basis (Frobenius =
  cyclic coordinate shift), every move applied per orbit. GF(2^6): reaches the optimum 15 in 90 s under groups of
  order 2, 3 and 6 (plain flip graph: 14/64 runs in 180 s). GF(2^12): 48 walks x groups of order 2,3,4,6,12,
  3 h, target <= 41 (results/dqi/fs12/). Plain flip graph from the rank-42 scheme found nothing below 42.
- dqi attribution (tasks/dqi/attribute_somejoint.py, user allowed running the public generator): somejoint 897Q,
  T_static 444,667, 480,015 AND-type calls. GF(2^12) tensor(12) multipliers (rank 42): field.mul_xor0 37.5% +
  field.mul_xor 2.7% (+ part of noscratch.rankone_xor 10.0%). GF(2^24) multiplier mul99 (degree 6 over GF(16),
  11 points x 9 = rank 99): 25.4%. zero_hold 9.2%, phase_classical_parity 5.9%. So one AND less in the 12-bit table
  is worth ~1% of dqi T, one less in the 24-bit table ~0.26%. mul_xor0 assumes symmetric masks (same form on x and
  y); a general scheme needs separate pivots (mechanical change).
- Chemistry shapes from the Gluzdov dataset, exact heuristic part (verifier formulas): THC (1,496,384) brot 10:
  572 addresses but T_h 11,010 and temp 640; (32,60,30) brot 10: T_h 6,411, temp 542; R4 (4,303/333,128) brot 8:
  T_h 13.7-14.7k. Current best (8,143,60) brot 8: T_h 7,930, temp 304 (+ lookups 8,366). None beats it as is.
- Exact dqi failure exchange rate (Clopper-Pearson, delta 2^-128, N 102,400; matches forum values): each
  tolerated failure costs k=1 +0.46%, k=2 +0.85%, k=5 +1.83%, k=10 +3.17%, k=20 +5.33%, k=50 +10.25% of dqi
  cost; one failure ~ 2 qubits ~ 2,000 Toffolis. Q floor is 840 (syndrome), public is 897: at most 57 workspace
  qubits (Q^2: <= 1.14x) are left, so dqi gains must mainly come from T. "Budget for the typical case" (Gu et al.)
  pays only where it removes > ~1,400 Toffolis or ~1.4 qubits per tolerated failure.
- Multiplier search status (stopped 2026-10-29 11:20): plain flip graph from our verified rank-42 scheme, 200
  walks x ~1 h: nothing below 42. Frobenius-symmetric flip graph from the trivial normal-basis scheme, 240 walks x
  ~1.5 h: stalled at ranks 114-132. A symmetric start scheme near 42 (or a much stronger walk) would be needed;
  parked as low expected value (rank 41 = ~1% of dqi T).
- dqi zero_hold (9.2%) = the Chien scan's 12-bit zero test (11 ANDs x ~4,025 calls); not prunable: a test on fewer
  bits gives ~4,060 x 2^-k false positives per shot.
- Copy pruning at fixed angle words (tasks/dfthcsos/prune_copies.py; exact eps_2 formula matches the official
  verifier to 1e-4 mHa): min eps_2 over all weights C=60 19.767, C=56 21.70, C=52 24.91, C=48 30.78, C=44 38.19,
  C=40 48.70 mHa. Infeasible: the public factor is error-saturated (0.23 mHa slack). Fewer copies needs new vectors,
  i.e. new lookup circuits, and the forum reports capacity limits there. Closed.
- Triage of the user's two planning documents (kickmix attack plan, literature map) against the
  verified public frontier: invsqrt ideas A-E already realised (63Q table circuit, margin 0.9993); dqi in-place
  solver (Q 897 vs floor 840), CZ-folded phase (field.phase_product is Clifford) and tower inverses are already in the
  public decoder; additive-FFT root search would replace CNOT-only Chien updates by 42-AND multiplies (worse); chem
  QAT, tree reordering and Lambda regularisation measured null publicly (forum 753185/753633); per-edge precision is
  not representable in the cost formula (one brot). Still open: lower-rank GF(2^12)/GF(2^24) multipliers, rare-event
  reserve sizing [4.8] for any new dqi design, structural dqi redesign.
- dqi stage breakdown (somejoint 897Q, AND-type calls, attribute_somejoint.py with b.mark tracking): extract ~64k,
  unextract ~166k (2.6x: the reverse measures out each chain's D and repairs its phase by replaying the scalar
  steps forward and back), synthesis 33k / unsynthesis 54k, convert 56k / unconvert 58k, scan 44k.
  Live workspace above the 840 syndrome qubits peaks at 57 in extract, convert, unconvert, unsynthesis and
  unextract (scan 30, synthesis 49). Holding D instead of replaying would carry it through convert (at the peak):
  base chain 12 qubits (~12k T-eq at ~990 T per qubit) vs ~2.9k replay; external groups 24 qubits (~24k) vs
  3.2k-6.3k replay. Replay is the right trade; lever closed (consistent with forum 753185).
- portfolio_v2 = v1 invsqrt + dqi, chemistry glz_open_circuits_v33_w34 (dmitriigluzdov dataset, Apache-2.0). PASS on
  salt '' + 8 random salts: GM 22.78536 on 7 salts, 22.75058 and 22.72115 on two (dqi failures). Note: the metric
  rejects hardlinked files (st_nlink > 1), so candidate dirs must hold real copies. The CLI returned 400 for a zip not
  named submission.zip; upload via data/upload/submission.zip with -c works.
- Submitted v2 to Kaggle 2026-10-29 (user said "continue the submission"): submissions/2026-10-29_v2.zip, sha
  46f7855e..., ref 57766121.
- v2 public LB score 22.78536 (2026-10-29): equals the local salt-'' value, as for v1.
- 2026-11-10 v3 = public frontier (invsqrt 5061b3bb 21.9677, dqi ddb3a087 65.2264, dfthcsos marculera c44 11.2189),
  public LB 25.23786 = local; rank 183/2745 (33-way tie at 25.23786), silver line (top 5%) 25.2478 at that time.
- invsqrt angle LP (tasks/invsqrt/angle_lp.py): firing pattern of all 41 rotations extracted exactly for every x in
  one perturbed run (angle k + 2^k units of 2^-64 turns), seed independent. Margin-maximising LP over the 41 angles
  returns the shipped margin (58,597,850 units) exactly: the public angles are already minimax optimal, with
  hundreds of x at the minimum (equioscillation). Dropping a rotation and refitting the rest is infeasible even for
  the smallest angle (k=15: best margin -6.0e7 units). Rotation cost is closed for this skeleton.
- dqi conservative liveness (dead after R/HMR, SWAP exchanges status, CX/CCX with a dead control is a no-op): peak
  892 = num_qubits, reached in ~8% of sampled points. No relabelling gain.
- dfthcsos W refit at fixed words and w (tasks/dfthcsos/refit_W.py, verifier formulas reproduced exactly): SLSQP over
  the 352 offsets W with error_1 <= 19.9 mHa gives lambda_eff 46.923535 -> 46.923355 (0.0004%). E_gap already sits
  at its floor (3.915005 vs 3.914898), so the error_1 slack (11.26 of 20 mHa) buys nothing. Chemistry gains need new
  loader circuits (T x Q). Closed for weights.
- tools/scan_frontier.sh: re-runnable public frontier scan (new notebook outputs by lastRunTime, vqcc datasets),
  stages with scan_public.py into data/cand2, scores only new members, prints best per task against portfolio_v3.
- 2026-11-11 frontier scan (207 members, 2 malformed dfthcsos skipped): invsqrt 64b39a7d 22.1255 (alexchilton,
  manwithacat notebooks) and dfthcsos 22b1be2a 11.2332 (maoxin123 notebook) beat v3 on every salt; dqi unchanged.
  portfolio_v4 = those two + v3 dqi, all tasks pass on salt '' + 6 random salts, GM 25.30892 on salt '', worst salt
  25.23761. The worst salts come from dqi ddb3a087 itself (64.93 and 64.68 on 3 of 7 salts), so the dqi member is not
  salt stable after all; v4 is above v3 on every salt because the dqi file is identical. submissions/2026-11-11_v4.zip
  sha cbf86a8d... Leaderboard before upload: Spinwave rank 318/2772, silver (top 5%, rank 138) 25.29376, bronze
  (rank 277) 25.23800, top 29.301.
- v4 uploaded 2026-11-11 (ref 58236400): public LB 25.30892 = local salt ''. Rank after scoring 331/2831; the frontier
  moved during the day: silver (rank 141) 25.34355, bronze (rank 283) 25.31236, gold (rank 15) 26.79893, top 29.301.
- 2026-11-12 v5 = maoxin123 v22 public portfolio (invsqrt 9c708f7b 22.1984, dqi eae396ba 65.4275, chemistry table
  f21b8a87 + maoxin123 4089-Toffoli loaders 11.2893): local GM 25.40483 on 6 of 7 salts (25.33323 on one dqi-failure
  salt), submissions/2026-11-12_v5.zip sha 22a3015b..., Kaggle ref 58263457, public LB 25.40482.
- Deep pass on the problem statement (arXiv 2610.23832). Hosts committed SHA-256 of internal best runs. DQI target is
  only the phase (-1)^(c.bin(e(s))); c is classical, conditioned gates count only when they fire.
- Chemistry loader anatomy (maoxin v22): per loader 75 cache Toffolis (69 high-address monomials + 6 low x gauge-bit
  monomials) + ~193 products CCX(acc126, acc127 -> word bit) with CNOT fan-out; uncompute HMR+CZ. Reads incoming word
  bits (reachable-state contract, forum 757522 unanswered). The clean tensor T[bit, low monomial, high block] is
  random-like (density 0.5, slice ranks ~35/40); counting bound with free word-bit features ~150 products.
- Chemistry shape model (official heuristic_costs + loader cost scaled by R*B): B in [129, 256] is the 303-temp-qubit
  band (B < 129 jumps to 574). Small B (4..31) would halve Q but is infeasible: rank-b truncated double factorization
  leaves 7-11 Ha error for any K (the leading leaves are full rank). Eckart-Young full-rank leaves: K 290 19.9 mHa, 350
  7.6, 500 1.3. brot 7: naive rounding 392-440 mHa, weights-only refit stalls at 228 mHa: closed. R=7 needs C ~58,
  gain ~1% only. Promising: B = 129 (fewer addresses), (8,143,40) and (7,129,40..44): model 0.87-0.94.
- Own fit tool tasks/dfthcsos/fit/fit_shape.py (JAX f64, L-BFGS, error_2 via ||G||^2 - 2 x'Gx + sum (x'x)^2, 0.2-0.6
  s/iter) and quantize.py (tree encoder, verified round trip). Fits from the f21b table: (8,143,40) 20.70 mHa and
  (7,143,58) 20.67 mHa after ~5000 iterations, still falling slowly; usable needs ~18.5 continuous.
- Public general-contract loader compiler found: dataset tayutiphetmee/vqcc-cl-chemloader-c18zzzg (anfq.py ANF +
  paired products, build_q.py FIN.npz -> loaders); running it needs user permission (external code). Starter kit
  trainer is in data/starter.
- Public general-contract loader compiler (tayutiphetmee anfq, user allowed running it): loader k0 346 Toffolis vs
  maoxin's 292 (reachable-state loaders read incoming word bits). Not competitive; the reachable-state design is the
  one to beat.
- tasks/dfthcsos/loader/extract.py: exact symbolic extraction of a loader into cache monomials + products over atoms
  (const, selection, incoming word bits, cache, products); reproduces k0, k1, k5 delta tables bit for bit (k13/k14
  differ only on gauge top bits: the circuit loads a gauge-equivalent table). maoxin products: every factor
  distinct, fan-out ~18-20 of 40 outputs (dense basis change), k14 has nested products (uses updated word bits).
  A formal flip graph has no shared factors to start from; a better loader needs a joint span-coverage search.
- Fits after ~8000 L-BFGS iterations: (7,143,58) 19.60 mHa (first shape below 20 continuous), (8,143,40) 20.22,
  (7,143,54) 20.84, (6,143,70) 24.78. Block-exact weight step (fit_als.py) is slower than plain L-BFGS: the vectors
  are the bottleneck, not the weights.

## 2026-11-12 — invsqrt track: anatomy of 9c708f7b and measured nulls (no gain)

Member under study: data/candidates/portfolio_v5/invsqrt.kmb (9c708f7b, 22.198355 salt '', 22.19836-22.19837 on 7 salts
in ledger). Scratch: data/work/invsqrt_track/. New tools in tasks/invsqrt/: screen.py (official checks + exact cost on
~100k shots x 4 seeds in ~1 s, reproduces margin 58,597,851 and ratio 22.199), profile_kmx.py, liveness.py,
liveexact.py, decomp.py, probe_rot.py, linspan.py, quadred.py, constprop.py, mbu_cands.py, delsearch.py, cuts.py,
fingerprint.py, drop_lp.py, kmxsim.py.
- Cost: C = 1213.73 mean Toffolis + 295.1 (41 rotations x 28.76 T, eps 2.43e-13, + 1 T) = 1508.9; Q 62.
- Mean Toffolis by phase: normalize 63 (20 prefix ANDs + 44 CSWAPs whose controls are XORs of thermometer bits),
  ANF lookup 167 (256 entries, 40 outputs), stage-1 phase mux 58 (15 rotations on K0-high, 6..9 bits), lookup inverse
  and misc 39, forward arithmetic 334 (late coefficient decoder ~90, Horner ~27, 12 signed-digit rows ~176, other ~41),
  stage-2 phase mux 76 (26 rotations), reverse arithmetic 405 (14 rows ~264 incl. conditional CCZ repairs), unlookup
  16, denormalize 54 (48 CSWAPs). Second half 449 vs mirror estimate 453: no reverse excess once the cheap MBU unlookup
  is counted.
- Qubits: 62 = 22 x + 40 table outputs on [1620, 7450]; also 62 at stage 1, at [9275, 10845], at stage 2 [16520,
  16730] and in ~40 short carry spikes in both arithmetic passes; forward multiply is 53-58 between spikes. R's low bits
  (q32-q39, q49, q53) sit idle 15,000-21,000. No live qubit is a GF(2)-linear or 2-input-AND function of the others at
  any plateau cut, no control is constant, no CCX clears a/b-known target (all on 8k-32k sampled shots).
- Margin: equioscillation at exactly 58,597,850 units across even shifts sp = 0..14; large-x arithmetic uses 0.92 of
  tol (per-segment offsets +-0.30, in-segment noise std 0.24 tol), so perfect arithmetic would save only ~19.5
  Toffoli-eq. Rare rotations: k=14/40 fire only for x <= 255, 13/39 for x <= 1023, still each costs a full rotation.
- Two-stream accounting: each stream pays ~10 positions of shift padding, so 41 = 33 + 8 for any split of K0 between
  streams; only a single stream (33 rotations, about -84 Toffoli-eq incl. stage-1 mux) saves, and it needs K0-high
  (9 bits) parked from the lookup to stage 2, i.e. +9 wires across three 62-wide regions. Not buildable on this layout.
- Single-gate deletion search (1375 Toffoli-like gates, screen with 2 seeds): only 19 rarely executed nested-condition
  CCZ repairs pass, total mean saving < 0.01 Toffoli; infnitycoder2009's public "edit search" output d701f267 fails
  (652 bad shots) — their 501-x one-seed check was too weak. No newer public invsqrt beats 9c708f7b (pulled 13
  notebooks + 6 datasets on 2026-11-12; best others 6c6a734d, a15b0d73, 3132ecab 93Q).
- Not tried/blocked: rebuilding the lineage from scratch (my best paper estimate with kickmix init_lookup and plain
  Gidney rows is ~100 Toffolis worse before any novelty), pair normalization (saves ~40 but needs a new table and
  arithmetic), lookup split for Q (needs every 62 region fixed at once).
- 2026-11-12/13 chemistry loader track (no gain shipped; portfolio_v5 dfthcsos unchanged, 11.289304):
  * Exact dual model of the maoxin v22 loaders (data/work/chem_track/redund.py): mixed ANF part of D_k = 35 output bits
    (bit 7 = bit 6 xor a per-word low-monomial helper, helpers s0s1,s0s2,s1s2,s0s3,s1s3 carried in the top bits) x 15
    low monomials x 75 complete hi monomials. Products = pairs of rank-one features low (x) f sharing the fan-out f;
    feasibility = Y (75-dim hi span) inside U = span of features. Verified on k1/k5/k8: Y in U, dim U = 2r, zero
    redundant products (every product is needed; single or few-product replacement is impossible generically).
  * Counting bounds: block model (5 groups of 3, relation-cut feature spaces, cross pairing) ~205-207 products on uncoded
    loaders; maoxin has 212 (k0-3) and 189-193 on bit-0-coded loaders, i.e. within ~3% of its model. Unrestricted lows
    (full model) count bound ~183-185, but no constructive algorithm: greedy capture needs dim U > 415, local/flip moves
    have no shared factors (dense lows and hi forms). Incoming word bits (z) are uncorrelated with B_k (|corr| <= 0.18).
  * Public Apache-2.0 round32 compiler (dmitriigluzdov dataset open_circuits_v41/source, vendored in
    tasks/dfthcsos/loader/vendor_round32/) on our k1: (4,4,4,3) hyperplane layouts 224 products, five 3-groups 219
    (pairing dies at >17 relations per group: c_A + c_B <= 34 forces sum of feature dims >= 440). Below maoxin's 212: no.
  * Gauge: per row only global sign (word 0 + 128) plus zero-subtree words (1.5%) at fixed form; the 4-form gauge is
    already spent on helpers. No zero-weight rows.
  * Shape check (official heuristic_costs + loader scaling): (7,143,58) is 0.9705 of current cost at equal lambda_eff,
    (8,143,40) 0.9798. But r7_c58_c (16.51 mHa) has 1/4 sum(sum_b|w|)^2 = 252.7 vs 130.5 for the current table: lambda
    would rise far more than 3%; needs a norm-penalised continuation (started mu 0.5 / 1.5, data/work/chem_track/fit/).
- Phase 2 (2026-11-13), single stream / Q / table, all measured nulls (tools tasks/invsqrt/v1span.py, anf_union.py):
  * Free wires: in every 62-wide region the only untouched non-x wire is q23 (a shift flag) on the lookup plateau
    [1644, 7474] and on the five long address-cleanup blocks [9779, 10829]; stage 2 and the carry spikes have 25-35
    untouched wires, so they are not the binding regions.
  * K0-high (stage-1) bits are GF(2)-linear in the live wires only up to cut ~9300 (5-7 of 7-8 bits at sp 0/1) and
    in none at 10870, 12550, 14400 or 16380: the address cleanup consumes them. A single stream must therefore copy
    ~8 bits out before 9300 and park them through [9779, 10829], where nothing is free: Q >= 70 on this layout,
    i.e. about 70 x 1425 = 99.8k (ratio ~20.8) vs 93.6k. Erasing R's low bits (idle 15k-21k) does not reach that
    window; Horner reordering does not touch the lookup or address-cleanup regions.
  * Q 62 -> 58: impossible without a new lookup (40 outputs + 22 x on [1644, 7474] with one idle wire).
  * Table synthesis: the 47 nonconstant outputs at cut 7180 need all 247 degree>=2 monomials in plain ANF, unchanged
    by 400 random linear input maps; the public XAG's 167 ANDs is far below naive synthesis, so beating it needs a
    real multi-output XAG/SAT minimiser (not attempted). A different normalisation (pairs) changes the table and the
    whole arithmetic, i.e. a full new generator, estimated ~100 Toffolis worse than the lineage before novelties.

## 2026-11-12/13 — dqi track: attribution of eae396ba and three mechanical levers (all closed, no candidate)

- Section profile of eae396ba (tasks/dqi/phase_profile.py, static Toffoli-like): extract 58,742, synthesis 31,635,
  convert 60,663, scan 44,275 (inside PUSH_CONDITION), unconvert 62,534, unsynthesis 40,429, unextract 103,035; total
  401,313 static, 394,089 mean. The old "unextract 166k vs extract 64k" figure was the 897Q somejoint build (AND calls);
  on eae the reverse excess is 44.3k (unextract) + 8.8k (unsynthesis) + 1.9k (unconvert). The current lineage already
  uses the one-pass "companion" scalar return (R copy of N), so the remaining n_only_99 replay is the Thiele prefix
  continuant at each group's own point (iwanttorungemma9b evidence, sections 5 and 10: structural).
- L-register MBU idea (measure L at the start of the reverse chain, turn its products into CZ phases) is invalid:
  N and L are syndrome words updated in place, so measuring them destroys input data that must be restored.
- Exact-zero liveness (tasks/dqi/affine_track.py, width_tool.py; affine forms over atoms with subspace-keyed product
  atoms): peak 892 in extract, synthesis, convert, unconvert, unsynthesis, unextract (scan 891); 913 maximal peak runs.
- Product reuse without ancilla (tasks/dqi/pair_scan.py, product_scan.py, product_scan2.py): 0 syntactic same-control
  pairs; 4,357 semantic AND matches but 0 usable (the second target is always read inside the window; holder-based
  variant 962 matches, gaps 1e3 to 1e5 lines). CSWAP with both targets next HMR'd: 0 left (already rewritten).
- Width cut by affine spill (erase a dormant wire, CX-restore it later; HMR erase with Z repayment means only the
  restore relation is needed): 1024-bit relation search at run boundaries finds an affine restore for 301 of 913 runs
  (extract 5/99, convert 56/164, unconvert 112/316, unsynthesis 32/100, unextract 96/233); searching 8 checkpoints in
  each dormancy window after the run adds 0 of the 612 remaining. One dormant wire spans each section's whole chain
  of runs, but those are pure data words with no redundant copy, so they cannot be restored. Covering 612 runs with
  quadratic restores costs at least ~600 T (Sol-A: up to 6 products per extract run) against 883 T per qubit: closed.
- Frontier rescan 2026-11-12 15:51: no public dqi better than eae396ba. LB 2026-11-12 10:27: silver (rank 145) 25.40784,
  we are 25.40482 (rank 275, plateau): silver needs only about +0.036 % on dqi (~140 mean T) if nothing else moves.
- Phase 2 (2026-11-13), unsynthesis fold division: in eae unsynthesis there are 36 inverse12 scopes. Per absorb site
  (e.g. lines 52.30M-52.43M, 1,090 T) the division is 99 (x*conj(y), deferred mask) + ~75 (norm + 12-bit inverse) +
  25 + 2x42 (half scalings by N^-1) + the inverse-phase repayment, about 290-310 T; the remaining ~780 T is the
  O(i) polynomial work (42 T per coefficient). Every piece is at a known optimal rank (99, 42, 58), and the
  "12-bit ratio 129 T" figure has no published construction (it is the Gemma lead's unverified estimate). No cheaper
  division was found, so nothing was spliced.

## 2026-11-13 v6 (public 27.11056, rank 58 of 2954)
- The public frontier jumped overnight to a 27.002 plateau. Our three own tracks (dqi, invsqrt, chemistry loaders) found no gain over v5 (see their sections above); the frontier scan had died with the session restart, so the jump was caught late from a leaderboard screenshot.
- Best new public members, official verifier salt '': invsqrt 321aff83 25.906979 (all new notebooks), dqi 821bf8d1 67.847839 (areebbb; c60beda8 67.829, cc0d7d25 67.787, 7cbe8ecf 67.749), dfthcsos f90d6c66 11.336077 (prvsiyan; 6b52ae43 11.335901, 6418ec8e 11.312180).
- portfolio_v6 passes salt '' plus 6 random salts: GM 27.11056 on 5 of 7, 27.069 and 27.034 on two dqi failure salts. Zip submissions/2026-11-13_v6.zip sha c648c743..., ref 58298046, public 27.11056 = local salt ''.
- Kaggle evaluation time: 24 min (submitted 06:07:48 UTC, complete by 06:32:18). Logged in ledger/kaggle_timing.csv; deadline 2027-01-20 23:59 UTC.
- After v6: silver cutoff (rank 147) 27.09017, bronze (295) 27.03707, gold (15) 27.57302, top 29.90871.
- R7 C58 norm penalised fits: mu 0.5 16.44 mHa / norm 168.7, mu 1.5 16.61 / 152.0 (current table 130.5); mu 3 and mu 5 running.
