# Anatomy of Syed Asad Ali's v12 invsqrt (321aff83) and ahoirg's K=6 fork (4560ac0c), measured 2026-11-13/14

Tools (ours): tasks/invsqrt/syed_profile_build.py (instrumented re-run of build_variant.build; every Toffoli-like builder
call attributed to its Python call stack and aligned 1:1 with the emitted text's exact gate probabilities),
tasks/invsqrt/syed_prof_report.py, tasks/invsqrt/syed_model.py (standalone integer model; reproduces the frozen oracle
digest 8bd482a8 and margin 124,370,688 exactly, and ahoirg's K=6 digest 219d2f76 and margin 116,291,417 exactly),
tasks/invsqrt/k6_angle_lp.py. Data: data/work/inv_gen/prof_raw.json.

## The math (whole_model.py, Syed)
x -> e = shift exponent (4 flags, 0..10), n = x * 4^e in [2^20, 2^22); Q = isqrt(16 n) (v = Q - 4096, 12 bits),
d = 2Q + 1, h = (64 n - d^2) // 64 (10-bit residual). C(v) = piecewise-linear table (128 rows of 32 v values: 13-bit
intercept A, 6-bit slope S; ahoirg: 64 rows of 64, 13-bit A, 7-bit S), seed U0(v) from C and the low 3 root bits,
U = U0 - F/2 with F = signed-digit C*(2q-1023)/256, so the numerator is 2^40 (1 + U/2^27). Non-restoring division
by d, 27 quotient rows (j = 9..35; rows j >= 28 use a truncated divisor) gives p ~ 2^37/sqrt(n). The 26-bit word is
routed cyclically by e (ring26) and each slot gets one refitted rotation.
Error at e = 0: numerator approximation -0.90..+0.64 tol (mostly the missing quadratic term in h at small n),
division truncation +-2.15 units of 2^-37 (0.27..0.46 tol). The angle LP spends small-x slack to equalise the absolute
margin over e = 0..3.

## Per-stage expected Toffolis, raw generator text (1519.57; pipeline + post pass take 8 off -> 1511.57)
| stage | Toffoli | live peak | generator / patch function |
|---|---:|---:|---|
| normalization forward | 51 | 37 | patch_fwd_narrow:forward |
| root forward | 96 | 39 | root192:forward (last_step 85, convert_high 11) |
| first table load | 56 | 46 | patch_ld_first20_56b8 (certificate loader) |
| first coefficient | 44 | 46 | patch_coef2_q46 > patch_coefdisp:coefficient_forward (41) + H3/H4 prep 3 |
| metadata retire | 1 | 38 | lifecycle |
| seed | 11 | 45 | lifecycle:seed_forward |
| product forward | 104 | 46 | patch_proddisp:product_forward |
| divider forward | 270 | 46 | divider:compute_divider: initialize_u12 13, 13 feed rows x (1 feed carry + 12 add), 11 late rows 100 |
| phase endpoint | 113 (+33 rot, 4 T) | 46 | w2core_e2:raw_endpoint: 64 CSWAP routing (32 + 32), features 13, e_forward 12, f_round_trip 13, other 11 |
| divider inverse | 321 | 46 | patch_hret_sat_s15k7a: inverse rows ~15.5 each (12 add + 1 repay + 2 phase-borrow at p=1/2 + 1.5 feed), restore_sat 7, restore 6 |
| second table load | 71 | 46 | patch_second46_c19_70nb1 > q46_loaders |
| second coefficient | 44 | 46 | patch_coef2_q46:second_forward |
| product inverse + seed cleanup | 133 | 46 | patch_h2ret > patch_seedinv (120 incl. 34 conditional), seed 10, H2 rebuild 3 |
| coefficient inverse | 39 | 46 | native_transfer:coefficient_inverse 36 + 3 |
| root decoder | 18 | 46 | decoder (T2 replay) |
| table cleanup | 6.32 | 43 | paid_R_cleanup_q48:cleanup_joint18 (30 conditional) |
| root inverse | 96 | 39 | root192:inverse |
| normalization inverse | 43.25 | 30 | normalization9475:inverse (15 gates conditional) |
Live qubits reach 46 in almost every arithmetic block (364 of 1128 allocations happen at 46: divider rows 130,
inverse rows 67, product 83, coefficients 58, endpoint 15). A 45-qubit build needs every one of them narrowed.

## Rotations (33) and margin
26 slot rotations base_i0..i25 at about 2^-36 .. 2^-11 turns (refitted around powers of two) + 7 overflow features
j0..j6 (AND of slot j with [e > j], about 2^-10 .. 2^-4 turns); j7 is a T, j8, j9 Clifford, global one angle 0.
33 = number of absolute bit positions 2^-36..2^-4 that are not T/Clifford; the ring size N moves rotations between
slots and overflow features but cannot change the total (N + (33 - N)). Each rotation ~28 T = 7.0 Toffoli-eq.
Margin 124,370,688 units (0.20 of tol at max x), binding at x = 228663 (e = 2); LP optimum per the authors.
Perfect arithmetic would raise the margin at most ~5x, i.e. at most ~10.7 Toffoli-eq.

## ahoirg K=6 fork (4560ac0c, 1480.75 Toffoli, margin 116,291,417)
Their marks (gen.log): first table 27 (vs 56), first coefficient 58 (vs 44), second table 30 (vs 71), second
coefficient 57 (vs 44), coefficient inverse 60 (vs 39), decoder 9 (vs 18), cleanup 8; loaders + decoder + cleanup 72
vs 151 ANDs, coefficient arithmetic +49 (6 slope rows of 7 bits on an 8-bit window), net -27.8 raw, -30.8 final.
Their loader certificates come from a private synthesiser (synth.cpp, not published). Our exact model reproduces
their digest and margin; the continuous LP optimum of the 33 angles on their table is 116,320,644 (+0.025 %),
so dcde7078's refit (+0.04 % margin on the verifier) is at the angle optimum: no angle gain left.
