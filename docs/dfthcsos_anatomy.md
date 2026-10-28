# dfthcsos — anatomy of the reference submission

Sources: `verifiers/dfthcsos/{SCORING_README.md, verify.py, scoreinfra/*}`,
`example_submission/angle_k_reference_circuit.py`. Measured by
`tasks/dfthcsos/anatomy.py` (official `evaluate_words` + `heuristic_costs`) and
`tasks/dfthcsos/whatif.py`. Official cost (Kaggle, empty salt):
**λ_eff 49.301369 × T 93,237 × Q 730 = 3,355,599,588.3155**. The analytic
model below reproduces that number exactly for the reference construction.

## Structure

Factorization shape R, B, C = 65, 60, 60; N = 76 orbitals. A = N + R·B = 3,976
vector rows, each encoded as 75 Givens angles of brot = 12 bits on a log-depth
tree. ANGLE_k (K = ⌈75/J⌉ = 10 circuits, J = 8 words each) is a plain QROM:
segment-tree unary iteration over the 12-bit `selection` register (A − 2 =
3,974 Toffolis, 11 ancillas uncomputed by measurement); the words are XOR'd in
by CNOTs (free). Each circuit runs in U_T and again in U_T†.

## T_total = 93,237

| part | Toffolis | share | formula |
|---|---:|---:|---|
| ANGLES (10 × 3,974 × 2 passes) | 79,480 | **85.2%** | 2·K·(A − 2) |
| inner state prep (QROAM over R·C·B) | 9,461 | 10.1% | SpinFreeData_V1 |
| Givens rotations | 3,450 | 3.7% | 2(N − 1)(2·brot − 1) |
| outer state prep | 846 | 0.9% | SpinFreeData_V1 |

## Q_total = 730

| part | qubits | share |
|---|---:|---:|
| shared temporary = max(outer 370, inner **544**, angles 11) | 544 | **74.5%** |
| angle-word registers J·brot | 96 | 13.2% |
| outer persistent | 46 | 6.3% |
| inner persistent | 44 | 6.0% |

The inner-prep QROAM block size (and hence the 544 temp qubits) is chosen
*inside* the heuristic model from (R, B, C, brot); submissions influence it only
through the shape and brot. The ANGLE circuits use 119 of 128 allowed qubits
(12 selection + 96 words + 11 ancillas); their temp (11) is far below the
shared 544, so **ANGLE workspace up to the cap is free in Q_total**.

## λ_eff = 49.301 (score elasticity to Λ ≈ 0.50)

| quantity | value | note |
|---|---:|---|
| Λ | 308.456 | floor 49.0 |
| — one-body Σ\|λ_j\| | 12.880 | 4.2% |
| — two-body ¼Σ(\|w_B\| + Σ\|w_b\|)² | **295.576** | **95.8%**, independent of rounding |
| E_gap | 3.96548 | floor 3.914898 (only 1.3% above) |
| error_1 / error_2 | 3.19 / **18.64** mHa | limit 20 / 20 → error_2 has 7% headroom |

λ_eff² = E_gap(2Λ − E_gap), so d ln λ_eff / d ln Λ = Λ·E_gap/λ_eff² = 0.503 and
d ln λ_eff / d ln E_gap ≈ 0.5. E_gap can only fall 1.3% before its floor
(≤ 0.6% score gain); **Λ_h2 is the λ_eff lever**.

## Precision headroom (measured)

Naively re-rounding the shipped 12-bit words (`anatomy.py` precision sweep):

| brot | error_1 (mHa) | error_2 (mHa) | λ_eff | passes |
|---:|---:|---:|---:|---|
| 12 | 3.2 | 18.6 | 49.30 | yes |
| 11 | 221 | 51.7 | 50.29 | no |
| 10 | 242 | 59.4 | 50.46 | no |

The 70× jump in error_1 between 12 and 11 bits shows the shipped words were
quantized **rounding-aware** (error_1 at 12 bits is far below naive rounding).
So lower brot is only reachable through a rounding-aware re-quantization (and
probably a refit) from the float factorization, not by shifting words.
Rounding also raises E_gap (and λ_eff) through the one-body eigenvalues.

### Correct (rounding-aware) precision sweep — `tasks/dfthcsos/brot_sweep.py`

The starter kit's encoding recomputes the one-body rows as eigenvectors of
h1′ built from the *rounded* two-body vectors; naive re-rounding (above) skips
that. Rebuilt on the official verifier functions, it **reproduces the shipped
12-bit words exactly** (identical metrics):

| brot | error_1 (mHa) | error_2 (mHa) | λ_eff | passes | J | ratio est. (if it passed) |
|---:|---:|---:|---:|---|---:|---:|
| 12 | 3.2 | 18.6 | 49.301 | yes | 8 | 1.00 |
| 11 | 6.5 | 25.0 | 49.319 | no | 9 | 1.09 |
| 10 | 14.0 | 40.0 | 49.622 | no | 10 | 1.20 |

Modelling error_2² = e₀² + r²·4^(12−brot): **factorization error e₀ ≈ 16.0
mHa, 12-bit rounding r ≈ 9.7 mHa.** Consequences:
- At brot 12, e₀ may grow only to √(400 − 93) ≈ 17.5 mHa → R·B reduction by
  retraining has ~1.5 mHa of room — little.
- brot 11 needs e₀² + 4r² ≤ 400: with e₀ = 16 that requires r ≤ 6.0 mHa
  (−38% rounding error) → **optimized (non-nearest) rounding** is the enabler.
- Any shape reduction must be paid for by smarter rounding first.

## Cost model what-ifs (λ_eff held at 49.30 — **estimates**)

Max J under the cap is ⌊(128 − 12 − 11)/brot⌋.

| change | J | K | T | Q | ratio |
|---|---:|---:|---:|---:|---:|
| baseline (brot 12) | 8 | 10 | 93,237 | 730 | 1.00 |
| brot 11 | 9 | 9 | 84,989 | 733 | 1.09 |
| brot 10 | 10 | 8 | 76,741 | 734 | 1.21 |
| brot 9 | 11 | 7 | 68,493 | 733 | 1.36 |
| B 60 → 45 | 8 | 10 | 73,617 | 730 | 1.27 |
| B 60 → 30 | 8 | 10 | 53,700 | 695 | 1.82 |
| R 65 → 50 | 8 | 10 | 73,254 | 729 | 1.27 |
| C 60 → 30 | 8 | 10 | 88,874 | 727 | 1.05 |
| (R,B,C) = (50,45,45) | 8 | 10 | 56,451 | 729 | 1.65 |

## Top 3 cost sinks

1. **ANGLES unary iteration — 85% of T**, ∝ K·(N + R·B). Reachable via R·B
   (factorization rank) and K (brot ↔ J under the 128 cap).
2. **Shared temporary workspace — 75% of Q** (inner-prep QROAM, 544). Not
   directly controllable; moves weakly with shape (B 30 → 511).
3. **Λ_h2 = 296 of 308** → λ_eff ∝ Λ^0.5. Untouched by circuits; needs a
   Λ-aware refit.

## Hypotheses for Phase 2 (estimates)

| idea | expected ratio | risk |
|---|---|---|
| A. Refit at smaller R·B (and C) within 20 mHa, re-quantized rounding-aware | 1.2–1.8× | error_2 already 18.6 mHa at R·B = 3,900; accuracy may force R·B up |
| B. Rounding-aware quantization at brot 10–11 → J = 9–10 | 1.09–1.21× | error_1/error_2 budget; jointly with A |
| C. Λ-regularized refit (penalize ¼Σ(\|w_B\|+Σ\|w_b\|)²) at fixed accuracy | Λ −20% → ~1.12× | interacts with E_gap (W enters E_SOS); E_gap floor |
| D. Exploit QROM `_break_early`: order rows / choose tree so ANGLE deltas repeat across address blocks | small (≤ 5%?) | needs structure in the angles |
| E. Select-swap QROAM inside the 128 cap | **rejected analytically**: λ = 2 needs another J·brot qubits → J ≤ 4 → K = 19; ≈ 2·(A/2 + 2·48) per circuit × 19 ≫ 79,480 | |

Classical refits (A–C) need the starter-kit trainer (`starter_kit/dfthc/df_thc_sga.py`,
dataset `sohier/verifiable-circuit-compilation-starter-kit`, not yet downloaded).
Verification is local: ~3 min in WSL per candidate.
