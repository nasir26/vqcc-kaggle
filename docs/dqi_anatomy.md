# dqi — anatomy of the reference decoder

Source: `verifiers/dqi/dqi_reference_circuit.py` (official generator).
Measured by `tasks/dqi/anatomy.py` (subtractive attribution: rebuild with one
subroutine replaced by a no-op; parts sum to the full static count) and
`tasks/dqi/unit_costs.py` (primitives on fresh registers). Build: 28 s,
1.76 GB RSS in WSL. Raw numbers: `data/anatomy/dqi.json`.
Official cost (Kaggle, empty salt): **R 1.19126 × Q² 1,893² × T 5,725,108.4 =
2.4439×10¹³**; 0 failures in 102,400 shots, mean error weight 31.05 (t = 35).

Cost elasticities: ∂ln cost/∂ln Q = **2**, ∂ln cost/∂ln T = 1. A 1% qubit cut
is worth a 2% Toffoli cut.

## Algorithm (reference, arXiv:2510.10967)

RS(4095, 4025) over GF(2¹²), n = 70 syndromes, t = 35.
1. **initial_shift** — left-align the syndrome polynomial (69 controlled
   lane rotations).
2. **forward EEA** — synchronized (Proos–Zalka-style) extended Euclid,
   n_iters = 3(n + 1) + 9 = **222** data-oblivious iterations. Each iteration
   executes *every* sub-step circuit (update_flag, multiply_and_add_or_sub,
   shift_b, update_metadata, swap_a_and_b) under one-hot controls c0..c3 from a
   2-bit counter; only one sub-step is logically active.
3. **chien_forney** — for each of 4,095 positions: evaluate σ, σ′, ω by XOR
   sums (Clifford), step multipliers by constants (Clifford), σ′⁻¹ via
   Itoh–Tsujii, Forney phase via `gf2_phase_by_product` (Clifford), uncompute;
   whole step conditioned on the classical bit E_j ≠ 0.
4. **reverse EEA**, uncompute initial shift.

## Unit costs (kickmix primitives, 12-bit)

| primitive | Toffolis | ancilla |
|---|---:|---:|
| ixor_gf2_mul (Karatsuba) | 63 | 0 |
| ixor_gf2_mul, controlled | 75 | 12 |
| init + del gf2_div_with_scaffold | 378 (= 6 × 63) | 72 |
| init + del gf2_inverse_with_scaffold | 315 (= 5 × 63) | 60 |
| gf2_phase_by_product (classical mask) | **0** (bilinear → CZ) | 0 |
| gf2_imul by constant | 0 (linear) | 0 |
| cswap 12-bit | 12 | 0 |
| flip_if_equal(reg, 0) | 12 | 12 |

## Toffoli budget (static 5,725,461; mean per shot 5,725,108)

| part | Toffolis | share | per-unit |
|---|---:|---:|---|
| **EEA sweep_positions** (controlled GF mults + CSWAPs over 73 slots) | ≈ 2,873,900 | **50.2%** | 6,473 per iteration × 444 |
| **Chien/Forney** | 1,444,737 | **25.2%** | 352.8 per position × 4,095 (inverse 315 = 89%) |
| EEA shift_b_array_right | 474,752 | 8.3% | 1,069 per iteration (CSWAP chain) |
| EEA swap_a_and_b | 396,492 | 6.9% | 893 per iteration (CSWAP of both 73-slot arrays) |
| EEA quotient divisions (2 per iteration) | ≈ 346,300 | 6.0% | 780 per iteration |
| EEA update_flag | 65,712 | 1.1% | comparators |
| initial_shift (both) | 61,824 | 1.1% | |
| EEA update_metadata + halting + counters + misc | ≈ 55,700 | 1.0% | |

EEA total 4,218,900 (73.7%) = forward + reverse, symmetric. Mean vs static
differ by 353 = one skipped Forney step per shot (P(E_j = 0) = 1/4096).
No measurement-conditioned Toffolis anywhere else: **every Toffoli is paid on
every shot.**

## Qubit budget (Q = 1,893)

| register | qubits | share |
|---|---:|---:|
| syndromes S0..S69 (= reg_a[3:73]) | 840 | 44.4% |
| reg_b (73 slots × 12) | 876 | 46.3% |
| reg_a[0:3] (3 extra slots) | 36 | 1.9% |
| degree/metadata registers n_A, n_B, n_a, n_b, n_q (8 bits each) | 40 | 2.1% |
| flag, counter, halting_counter | 11 | 0.6% |
| **persistent** | **1,803** | 95.2% |
| peak temporary (in multiply_and_add_or_sub: division scaffold 72 + q_i 12 + controls) | 90 | 4.8% |

Polynomial storage (2 × 73 × 12 = 1,752) is 92.5% of Q. The 840 syndrome
qubits are part of the I/O contract and must exist; everything else (1,053
qubits = 55.6% of Q) is workspace.

## Top 3 cost sinks

1. **EEA sweep — 50% of T.** A controlled 75-Toffoli GF multiply on (almost)
   every one of 73 slots in each of 444 iterations, regardless of the actual
   polynomial degrees at that iteration.
2. **Polynomial workspace — 1,053 workspace qubits (55.6% of Q), Q enters
   squared.** reg_b (876) + 3 padding slots in reg_a (36) + 90 peak temp.
3. **Chien/Forney inversions — 22.5% of T** (4,095 × 315). Every position
   computes σ′(x_j)⁻¹ although only ≤ 35 positions are roots of σ.

## Hypotheses for Phase 2 (estimates, not results)

| idea | mechanism | est. ΔT | est. ΔQ | est. Δcost |
|---|---|---:|---:|---:|
| A. Tighten sweep ranges per iteration by **classical reachability analysis** (which slots can be non-zero / be multiplied at iteration `it` over all inputs of weight ≤ 35) | skip provably idle slot multiplies | −10…−30% | 0 | −10…−30% |
| B. Hoist the control out of the slot multiply: AND q_i with the threshold control once per contiguous run, then uncontrolled 63-Toffoli multiplies | 75 → 63 per slot + 12 per run | −6…−8% | ±0 | −6…−8% |
| C. Cheaper GF(2¹²) inversion for Chien: tower field GF((2⁶)²) or GF((2⁴)³) — basis changes are linear (free CNOTs); subfield inversion + 3 multiplies | 315 → ~200–250 | −4…−6% | −12…−24 temp | −5…−7% |
| D. Drop the 3 padding slots / shrink m = n + 3 where the EEA invariant allows | | −1…−3% | −36…−72 | −5…−9% |
| E. Smaller division scaffold (inverse + in-place multiply, or MBU of the scaffold) at the peak | | ~0 | −12…−30 | −1.3…−3% |
| F. Merge swap_a_and_b into role-alternating indexing (swap only metadata, alternate which array each sub-step treats as A) | | −4…−7% | 0 | −4…−7% |
| G. Accept rare failures (drop support for corner cases): k = 10 failures/102,400 → R 1.19 → 1.23 (+3%) | only pays if it buys > 3% | | | conditional |
| H. Different decoder (Berlekamp–Massey with in-place σ/B) | storage ≈ 2 × 36 × 12 instead of 876 + 36? needs analysis of reversibility overhead | ? | potentially −400…−800 | **up to 1.5–2.5×** — high effort |

Dev loop: build 28 s, 1.76 GB locally (fine in WSL); **verification only on
Kaggle** (~3 min with 4 workers; ~0.9 GB circuit upload per candidate as a
private dataset version, or generate inside the kernel from our generator
code to avoid the upload).
