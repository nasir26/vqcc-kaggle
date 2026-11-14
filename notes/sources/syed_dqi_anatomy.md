# Syed Asad Ali v12 dqi decoder: anatomy (measured 2026-11-14)

Base: Syed Asad Ali's v12 builder (Apache-2.0), data/src_pull/syed_v12/src_dqi/dqi_source, entry
integration_v7/v7_pipeline.emit. Instrumentation is ours: tasks/dqi/syed/anatomy.py builds the decoder through a
proxy CircuitBuilder and charges every Toffoli-like primitive (ccx, ccz, cswap, init_and whose operands are all
qubits; classical-bit controls compile to conditioned Cliffords) to the chain of generator frames that issued it.
The count matches the finished circuit exactly: 384,003 of 384,003 static Toffoli-like gates (cutoff 15, no
retention). Raw data: runs/dqi/anatomy/syed_v12_cut15.json, breakdown.txt.

## What the decoder does

1. Mask gauge (classical, 0 T). The 4,095 classical phase masks are sheared so that 70 selected words absorb the
   syndrome-weight gauge (mask_gauge_blocked, adaptive_gauge64).
2. Public CRT view (Clifford). The 70 GF(2^12) syndromes are mapped in place to 35 residues mod the quadratics
   q_i = x^2 + x + kappa_i, each a GF(2^24) word ("heads", 840 qubits = the syndrome register).
3. Extractor (raw_query_extractor via first3_retained_norm_adapter). A continued fraction in CRT form: each new
   residue Y_i is run through all earlier quotient heads, (n,d) -> ((d + P_l(alpha_i) n)/q_l(alpha_i), n), one
   rank-99 GF(2^24) product per (i, l) pair, then a deferred inverse and a normalising product. The rolling tail
   controller handles degree drops for slots i >= j_min (Ozer's cutoff raises j_min).
4. Synthesis (fused_crt_synthesis). Rebuilds the locator D (deg 35) and evaluator N from the 34 quotients with
   12-bit products in an evaluation view.
5. Outer / Forney preimage (transpose_handoff_outer -> transpose14_core). A half-Euclid on the even/odd parts
   A, B of D that turns N into K with K = N * Psi, Psi ~ 1/D' mod D (the Gu et al. phase-only idea), so that the
   phase at a root a is a linear function of K(a).
6. Projective finish (projective_finish_infinity3). 16 quadratic CRT blocks and a 3-word jet at infinity.
7. Scan (adaptive_gauge64 -> zero_mask_scan.point_cell). Additive-FFT evaluation of D and K at the 4,095 points
   (Clifford); per point a 12-bit zero test of D(a) with phase on Tr(mask * K(a)): 11 Toffolis if the classical
   mask is nonzero, 0 otherwise (4,026 tested points).
8. Every stage is then uncomputed in reverse (closings); scratch is released by HMR and classical-controlled
   CZ/CCZ (0 T).

## Per-stage static Toffolis and live-qubit peak

| stage | generator function | static T | share | peak Q |
|---|---|---:|---:|---:|
| extractor prefix | first3_retained_norm_adapter.emit_prefix (raw_query_extractor) | 73,122 | 19.0% | 889 |
| synthesis prefix | fused_crt_synthesis.emit_prefix | 27,846 | 7.3% | 889 |
| outer prefix (Forney preimage) | transpose_handoff_outer.emit_prefix -> transpose14_core.emit | 56,736 (+298 border) | 14.9% | 889 |
| finish prefix | projective_finish_infinity3.emit_prefix | 1,752 | 0.5% | 889 |
| scan | adaptive_gauge64.emit_scan -> zero_mask_scan.point_cell | 44,286 | 11.5% | 875 |
| finish return (keeps inverse) | projective_finish_infinity3.emit_closing_keep_inverse | 6,077 | 1.6% | 889 |
| outer return | finish_outer_seam.outer_closing_with_inverse -> transpose14_core.emit | 57,642 (+284) | 15.1% | 889 |
| synthesis return | fused_crt_synthesis.emit_closing | 37,230 | 9.7% | 889 |
| extractor return | first3_retained_norm_adapter.emit_closing | 78,389 | 20.4% | 889 |
| seed / gauge / misc | scalar_seed_padded etc. | 177 | 0.0% | 889 |
| **total** | | **384,003** | | **889** |

Q = 840 syndrome qubits (35 heads x 24, used in place throughout) + 49 workspace (24-bit carry, 24 helpers of
the deferred inverses and products, tail and flag wires). Every stage except the scan reaches 889; the scan
peaks at 875.

## By primitive

| leaf | static T | share | note |
|---|---:|---:|---|
| field_tensor.accumulate_product | 310,836 | 80.9% | all field multipliers |
|   of which GF(2^24) rank-99 (modular_quadratic_direct.product) | 136,224 | 35.5% | 1,376 products |
|     extractor query steps (prefix + return) | 117,216 | 30.5% | 592 + 592 products |
|     nested-norm inverses, finish, divisions | 19,008 | 4.9% | 192 products |
|   of which GF(2^12) rank-42 (tower_inverse.xor_product, synthesis, traces) | 174,612 | 45.5% | about 4,150 products |
| scan10.point_cell (12-bit zero test) | 40,260 | 10.5% | 11 per tested point (+ 4,026 cell overhead elsewhere in the scan) |
| narrow_field130._selected_parity_ccz | 6,714 | 1.7% | inverse phase CCZ |
| transpose14_core.swap_low, rotate (cswap) | 7,104 | 1.8% | degree-drop routing in the half-Euclid |
| everything else | about 19,000 | 5% | toggles, tail controllers, small inverses |

## What this says about the candidate levers

* Scan versus Gu et al.'s 23 per position: Syed's scan is already at 11 per tested point, which is the
  multiplicative-complexity floor for (-1)^([x=0] L(v)) with 12-bit x (AND of 13 linear forms needs 12 ANDs, the
  last one is a CZ). No gain left there.
* Multiplier bases: 81% of the circuit is bilinear multipliers. One rank less is worth 1,376 T (0.36% of dqi) for
  GF(2^24) and about 4,150 T (1.08%) for GF(2^12). Rank 99 = 11 GF(16) points x 9 and rank 42 = 7 GF(8) points
  x 6. Every textbook decomposition (GF(4)^12, GF(8)^8, GF(16)^6, GF(64)^4) lands on 99 and 42 again, so a gain
  needs a non-composed scheme (flip-graph search, see RESEARCH_LOG).
* Key-equation work: 1,184 quantum-by-quantum GF(2^24) products in the O(n^2) continued fraction, plus 1,258
  12-bit products in synthesis. Berlekamp-Massey would need about 3,700 12-bit products forward alone, so the
  CRT continued fraction is already about 2x cheaper.
* Failure budget: the input law puts P(w=35) = 2.8%, P(w=34) = 9.2%, so high weights cannot be dropped; the only
  cheap failure budget is at low weight, which Ozer's cutoff already uses (each cutoff step about 116 T; step 19
  would cost 0.35 expected shots).
* Qubits: 889 is reached in every stage but the scan; one qubit less needs simultaneous width changes in the
  extractor, synthesis, outer and finish.
