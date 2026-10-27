# RULES digest — google-verifiable-quantum-circuit-compilation

Source: Kaggle competition pages fetched 2026-10-27 via `tools/fetch_pages.py`
(raw copies in `data/pages/`, gitignored). Quotes are verbatim; my notes are
marked **[note]**. Where a page defers to the verifier source, the item is
marked **[PENDING verifier]** until `verifiers/` is downloaded and read.

## 1. Score

> $$\text{Score} = \left( \prod_{b=1}^{3} \frac{\text{cost}_b^{\text{ref}}}{\text{cost}_b} \right)^{1/3}$$

The reference submission (`sample_submission/`) "scores 1.0".
Official metric notebook: https://www.kaggle.com/code/metric/google-quantum-ai-metric
"Scoring takes roughly 45 minutes."

## 2. Per-task cost (Evaluation page, verbatim)

| Task | Cost |
|:---|:---|
| `invsqrt` | \( Q \times C \), where \( C = \text{Toffolis} + \text{T gates} / 4 \) |
| `dqi` | \( R(\epsilon_{+}) \times Q^{2} \times T \), where \( R(\epsilon) = \frac{\ln 2}{-\ln\left(\frac{1}{2} + 2\sqrt{\epsilon}\right)} \) |
| `dfthcsos` | \( \lambda_{\text{eff}} \times T \times Q \), where \( \lambda_{\text{eff}} = \sqrt{E_{\text{gap}}\left(2\Lambda - E_{\text{gap}}\right)} \) |

> where \( Q \) is the qubit count and \( T \) the Toffoli count, both per shot.
> For `dqi`, \( \epsilon_{+} \) is an upper confidence bound on the decoder's
> failure rate. For `dfthcsos`, \( T \) and \( Q \) cover the whole block
> encoding, not just the submitted ANGLE circuits, and any ANGLE circuit wider
> than 128 qubits is rejected.

**[note]** Q enters linearly for invsqrt and dfthcsos but **quadratically** for dqi.
**[note]** R(ε) → 1 as ε → 0 and diverges as 2√ε → 1/2 (ε → 1/16).
### 2a. Definitions from the paper (arXiv:2610.23832v2) — **[CONFIRM in verifier]**

Extracted via a summarising fetch of the HTML paper; treat as provisional
until matched line-by-line against `verifiers/*.py`.

- **invsqrt rotation pricing.** Clifford Z_POW angles free; T-type angles 1 T;
  each of the n_rot finer rotations costs
  T_rot = 0.56·log₂(1/ε) + 5.3, with
  ε = π·min_x(tol(x) − |error(x)|) / n_rot (margin split evenly), tol(x) = 2⁻²⁴/√x.
  **[note]** So the unused error margin buys cheaper rotations: precision slack
  is itself a cost lever.
- **dqi ε₊.** One-sided Clopper–Pearson upper bound with δ = 2⁻¹²⁸,
  N = 102,400: Σ_{j≤k} C(N,j) ε₊^j (1−ε₊)^{N−j} = δ, k = observed failures.
  k = 0 ⇒ ε₊ ≈ 88.7/N ≈ 8.7×10⁻⁴ ⇒ R ≈ 1.19 (floor on R). ε₊ ≥ 1/16 ⇒ no score.
- **dfthcsos.** Λ = ‖h⁽¹⁾′‖₁(Schatten) + ¼Σ_ℓ(|w_ℓB| + Σ_b|w_ℓb|)² (Eq. 56/87).
  Verifier uses E_gap = E_upper − E_SOS, E_upper = −22140.27335 Ha,
  E_SOS = −ηβ₁ − (‖h⁽¹⁾′‖₁ − Tr h⁽¹⁾′) − ½Σ|W^(ρc)|² (Eq. 57). Need 0 < E_gap < 2Λ.
  Accuracy: ε₁ = ‖h̃⁽¹⁾′ − h⁽¹⁾′‖_F ≤ 20 mHa and ε₂ = ‖ΣX⊗X − h⁽²⁾ − 𝒯(S₀)‖_F ≤ 20 mHa.
  Q_tot = persistent (state-prep registers + J·b_rot angle words) + max temporary
  workspace over {Outer, Inner, Angle_k}. T_tot = simulated Toffolis of all
  Angle_k over forward + reverse traversal + heuristic C_out, C_in + Givens
  rotations at (2b_t − 1) Toffolis each. K = ⌈(N−1)/J⌉ circuits, N = 76;
  Angle_k XORs ϑ^[k] ⊕ ϑ^[k−1] into the angle register (self-inverse).
- **Q definition.** invsqrt: "the circuit's total qubit count"; dqi: syndrome
  (840) + workspace. Peak-live vs. total-allocated still **[PENDING verifier]**.

### 2c. CONFIRMED from verifier source (data/comp/verifiers/, 2026-10-27)

Supersedes §2a where they differ.

- **Q = `circuit.num_qubits`** for invsqrt and dqi (all qubits the circuit
  declares, not peak-live). dfthcsos uses Q_total (below).
- **Toffolis = mean Toffoli-like (CCX, CCZ, CSWAP) executed per shot**, counted
  by `km.Simulator(counting_operations=True)`; a gate conditioned on a measured
  bit counts only on shots where the bit is set. So MBU-conditioned fixups are
  paid at ~50%, not 100%.
- **invsqrt**: 64 shots × every x ∈ [1, 3,133,452] (200.5M shots). Seed =
  SHA-256 of canonical .kmb (+ secret salt on Kaggle). Phase compared in units
  of 2⁻⁶⁴ turns; tol(x) = floor(r ≫ 25), r = isqrt(⌊2¹³⁰/x⌋). Z_POW classes:
  multiple of ½ half-turn → Clifford (free); of ¼ → T (1 T); else rotation at
  0.56·log₂(1/ε)+5.3 T, ε = π·min_margin/n_rot (min over all shots). Registers:
  exactly one register `x` (22 qubits); everything else is scratch → |0⟩.
- **dqi**: registers exactly S0..S69 (12 qubits each, `km.q`) and E0..E4094
  (12 classical bits each, `km.b`). **Z_POW forbidden.** Failures =
  value errors (syndrome not restored or dirty ancilla) + phase errors.
  ε₊ = one-sided Clopper–Pearson, δ = 2⁻¹²⁸, N = 102,400. k = 0 ⇒
  ε₊ = −expm1(ln δ / N). Reject if ε₊ ≥ 1/16. Score = R(ε₊)·Q²·T.
  Error weight k ∈ {0..35} drawn ∝ w_k² (DQI principal eigenvector, r = 2016),
  so the test distribution is NOT uniform over weights — mean weight is reported
  by the verifier. Default 4 workers; **~6 GB RAM per worker** for the reference.
- **dfthcsos** (SCORING_README.md): score = λ_eff·T_total·Q_total.
  T_total = ANGLES Toffolis (forward + reverse, simulated) + outer + inner
  state-prep (heuristic SpinFreeData_V1, χ = 10) + 2(N−1)(2·brot−1).
  Q_total = outer_persistent + inner_persistent + J·brot
  + max(outer_temp, inner_temp, angles_temp).
  Rejects: any ANGLE_k > 128 qubits; error_1 or error_2 > 20 mHa (of the
  quantized words); not 0 < E_gap < 2Λ; Λ ≤ 49.0; E_gap ≤ 3.914898 (strict).
  `selection` must be exactly ⌈log₂(76 + R·B)⌉ qubits; one `word_j` register
  per word, width = brot (this is how precision is declared). No Z_POW.
  S, β₁ fixed to baseline's (`fixed_shifts.npz`); submitted H1_I, Hsym_lower
  ignored. Pickles rejected. 64 shots per address.

### 2d. Official baseline numbers

| Task | Source | Q | Toffolis | other | cost |
|---|---|---|---|---|---|
| dfthcsos | SCORING_README (verifier) | 730 | 93,237 | λ_eff = 49.301369 | **3,355,599,588.3155365** |
| invsqrt | paper, unverified | 260 | 7,735 | C = 7,988 | ≈ 2.08×10⁶ |
| dqi | paper, unverified | ≈ 1,893 | ≈ 5.73×10⁶ | R ≥ 1.19 | ≈ 2.4×10¹³ |

dfthcsos breakdown: ANGLES 79,480 Toffolis (10 circuits × 3,974 × 2 passes,
85% of T_total); heuristic 846 + 9,461 + 3,450 = 13,757. Q: 186 persistent
(90 state-prep + J·brot = 8·12 = 96) + 544 shared temp (state prep dominates;
ANGLE circuits are 119 qubits). Λ = 308.456, E_gap = 3.96548.

### 2b. Reference numbers from the paper — **[estimates until harness reproduces]**

| Task | Q | Toffolis | other | cost |
|---|---|---|---|---|
| invsqrt (np=10) | 260 | 7,735 | 1 T + 37 rotations → C = 7,988 | ≈ 2.08×10⁶ |
| dqi | ≈ 1,893 | ≈ 5,725,461 | R ≥ 1.19 | ≈ 2.4×10¹³ (derived, k=0) |
| dfthcsos | — | — | not stated | — |

## 3. Task contracts (Data page, verbatim)

**invsqrt** — "Map |x⟩|0⟩ ↦ e^{2πi/√x}|x⟩|0⟩ for every x from 1 to 3,133,452,
held in a 22-qubit register named `x`. Each input is tested 64 times, and every
phase must be within 2^{-24}/√x turns. Cost: qubits × Toffoli-equivalents
(Toffolis plus T gates / 4, with rotations priced in T gates)."

**dqi** — "A reversible decoder for the Reed–Solomon code RS(4095, 4025) over
GF(2^12). Given error syndromes in registers `S0` to `S69` and a classical
record M in `E0` to `E4094`, it restores the syndromes and applies the phase
(−1)^{Σ_j popcount(e_j ∧ M_j)} for the error e. It is tested on 102,400 shots;
failures are allowed but raise the cost. Cost: R(ε₊) × Q² × T, with R a
repetition factor that grows with the failure rate (paper Eq. (43))."
**[note]** n−k = 70 syndromes → t = 35 correctable symbol errors.

**dfthcsos** — "Circuits that load the Givens-rotation angles of a factorized
FeMoCo Hamiltonian, one batch of J angles per circuit, plus the factorization
and rotation tree in `submission.npz`. A submission is rejected if any circuit
uses more than 128 qubits, if the encoded Hamiltonian is more than 20 mHa from
the reference, or if the LCU normalization Λ ≤ 49.0 or E_gap ≤ 3.914898 Ha.
Cost: λ_eff × T_total × Q_total over the whole block encoding (paper Eq. (44)).
The full contract is in verifiers/dfthcsos/SCORING_README.md."
**[RESOLVED by paper §III.3.7]** Λ > 49.0 Ha and E_gap > 3.914898 Ha are
strict *floors*, not a typo: they block degenerate factorizations that shrink
λ_eff artificially. Confirm in verify.py.

General: "A verifier simulates your circuit with kickmix on many inputs and
checks every shot: inputs restored, scratch qubits back to |0⟩, and the right
phase. Measurement-based uncomputation is allowed. Tests are seeded from your
submission's hash plus a secret salt, so any change to a circuit gets fresh
tests (paper §II.C)." The verifiers in `verifiers/` "are the authoritative
specification".

## 4. Submission format (Evaluation page, verbatim)

> You must submit a zip archive containing the following files:
>  - `invsqrt.kmb` or `invsqrt.kmx`
>  - `dqi.kmb` or `dqi.kmx`
>  - a folder named `dfthcsos` containing the circuits `angle_k_0`, `angle_k_1`,
>    … `angle_k_<n-1>`, numbered from 0 with no gaps, each as `.kmb` or `.kmx`,
>    plus `submission.npz` holding the factorization (`U`, `W`, `H2_I`, `H1_I`,
>    `Hsym_lower`) and the Givens tree (`tree_edges`).

Upload dialog (seen 2026-10-27): "Your submission should be named submission.zip."

**Metric notebook (`metric/google-quantum-ai-metric`, vendored in
harness/metric_vendor.py) — confirmed:**
- Each leaderboard split has its own secret `seed_salt` (≥ 32 chars) and a
  `baseline_cost` = **the reference submission's cost under that salt**.
  Score per split = geomean over tasks of baseline_cost / cost.
- Every task is verified once per split, in random order; **any failure on any
  split raises → the whole submission errors.**
- Allowed instructions only: X, CX, CCX, Z, CZ, CCZ, Z_POW, NEG, SWAP, CSWAP, R,
  HMR, BIT_INVERT, BIT_STORE0, BIT_STORE1, PUSH_CONDITION, POP_CONDITION,
  INFO_TAG, DEBUG_PRINT. (DEBUG_PRINT ids still count toward num_qubits.)
- Qubit and bit ids < 2³⁰/1536 = 699,050. Max registers: invsqrt 1, dqi
  n + m = 4,165, each ANGLE_k ≤ 128. Every register must be named.
- submission.npz: format-1.0 .npy members, plain numeric dtypes, little-endian,
  shapes U (R,B,76), W (R,B,C), H2_I (R,C), H1_I (), Hsym_lower (2926,),
  tree_edges (75,2) int; total ≤ 2²⁶ bytes. No links/special files in the zip.
- Kaggle mount: `/kaggle/input/competitions/<slug>/`. Image pinned
  `gcr.io/kaggle-images/python@sha256:81b1e7c4…cd84a`.

Reference sizes: dqi.kmb ≈ 886 MB, invsqrt.kmb ≈ 0.58 MB, 10 angle circuits
≈ 1.7–2.0 MB each, submission.npz ≈ 4.5 MB. **[PENDING]** max upload size not
stated on any page.

## 5. Limits and timeline

- 5 submissions/day; up to 2 Final Submissions.
- Team size ≤ 5; mergers allowed by team leader, subject to submission-count cap.
- Start 2026-10-22. Milestone prize snapshot **2026-11-20** 23:59 UTC
  (needs public notebook). Longest-leader window ends 2027-01-04.
  Entry + team-merger deadline 2027-01-13. Final submission **2027-01-20**.

## 6. Code, data and licensing

- Winner license: Apache 2.0 (submission + generating source code).
- Data access and use: Apache 2.0, but **Data Security**: "You agree not to
  transmit, duplicate, publish, redistribute or otherwise provide or make
  available the Competition Data to any party not participating in the
  Competition." → competition files stay gitignored, never pushed.
- **No private sharing** of code/data outside the team; public forum sharing OK.
- External data/tools allowed if publicly available at no cost to others
  ("Reasonableness Standard"). AutoML tools allowed with valid license.
- Winners must deliver reproducible code + documentation of the environment.
- Prizes: leaderboard top 6; $10k milestone; $10k longest leader; $10k per
  task for best single-task score among *selected* submissions. Additional
  prizes require public notebooks/datasets.

## 7. Open questions

1. ~~dfthcsos Λ / E_gap inequality direction~~ — floors (paper).
2. Q peak-live vs. allocated; confirm §2a formulas in verifier code.
3. Public vs private leaderboard split for a deterministic-verifier metric:
   the rules mention public/private test sets — presumably different secret
   salts. **[PENDING]** confirm from metric notebook.
