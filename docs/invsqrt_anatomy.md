# invsqrt — anatomy of the reference circuit

Source: `verifiers/invsqrt/nr_reference_circuit.py` (official generator).
Measured by `tasks/invsqrt/anatomy.py` (each stage rebuilt alone on the
reference's exact register layout; stage sum = full circuit, 7,735 Toffolis).
Official cost (Kaggle, empty salt): **Q = 260, C = 7,987.59, cost = 2,076,774.23**.
Raw numbers: `data/anatomy/invsqrt.json`.

## Algorithm (reference)

1. **normalize** — count leading zero *pairs* s into 10 unary flags; shift x
   in place (controlled rotations = CSWAP chains) so M = x·2^(2s)/2^20 ∈ [1,4).
2. **select_interval / load_coefficients** — 3 AND bits pick one of 4 cubic
   pieces; coefficients XOR'd in by a Clifford network (0 Toffolis).
3. **horner** — y0 = c0 − T(δ(c1 − T(δ(c2 − T(δ c3))))) with column-truncated
   shift-and-add multipliers (`_add_row`: AND row into scratch → add → MBU of ANDs).
4. **Newton step** — square = T(y0²) → z = T(M·square) → z = 3 − z →
   p = T(y0·z) → **denormalize** y1 = p·2^s (unary-controlled rotations).
5. **phase_by_bits** — one Z_POW per bit of y1 (40 bits).
6. **uncompute** — exact mirror of 1–4.

## Toffoli budget (per shot; mean = static, i.e. no measurement-conditioned Toffolis)

| stage | compute | uncompute | total | share of 7,735 |
|---|---:|---:|---:|---:|
| horner (3 truncated mults, 17-bit) | 1,071 | 1,071 | 2,142 | 27.7% |
| multiply_m (22×28 → 30 bits) | 1,043 | 1,043 | 2,086 | 27.0% |
| multiply_y0 (17×30 → 30 bits) | 867 | 867 | 1,734 | 22.4% |
| square (17² → 28 bits) | 442 | 442 | 884 | 11.4% |
| denormalize (10 controlled rotations of 31-bit lane; CSWAP) | 300 | 300 | 600 | 7.8% |
| normalize (10 controlled rotations + 10 AND) | 120 | 110 | 230 | 3.0% |
| correct (3 − z, 30-bit add) | 28 | 28 | 56 | 0.7% |
| select_interval | 3 | 0 | 3 | 0.0% |
| **total** | **3,874** | **3,861** | **7,735** | |

Plus phase: 40 Z_POW = 2 Clifford + 1 T + **37 rotations** at
ε = 1.529e−12 → 27.28 T each → 1,009.4 T → **252.3 Toffoli-eq (3.2% of C)**.

## Qubit budget (Q = `num_qubits` = highest id + 1)

| register | qubits |
|---|---:|
| x (input) | 22 |
| y1 (output, 29 + 10 + 1) | 40 |
| c0..c3 (coefficients / Horner intermediates) | 68 |
| square | 28 |
| z | 30 |
| scratch (AND rows) | 30 |
| flags (unary s) | 10 |
| selectors | 3 |
| **registers** | **231** |
| adder ancillas at peak (`correct`; ~28 in multiplies) | 29 |
| **Q** | **260** |

All registers are allocated up front and live for the whole circuit, so the
peak is reached in the Newton step while **all 4 coefficient registers
(68 qubits) are still live** although only c0 = y0 is used after Horner.

## Error budget

- Tolerance: |err(x)| ≤ 2⁻²⁴/√x turns, i.e. relative error ≤ 2⁻²⁴ = 5.96e−8.
- Reference worst relative error **2.843e−8 = 2^−25.07** at x = 2,588,411
  → **0.477 of tolerance used**; > 1 bit of slack left unspent.
- That leftover margin (min over x of tol(x) − |err(x)| = 1.80e−11 turns) is
  what the verifier hands to rotation synthesis: ε = π·margin/37.
- Rotation cost is only logarithmic in the margin: halving the margin costs
  +0.56 T per rotation (+5.2 Toffoli-eq total). **Spending slack on narrower
  arithmetic is worth far more than keeping it for rotations.**

## Top 3 cost sinks (cost = Q × C, so a 1% cut in Q or C is worth the same)

1. **Multiplications: 6,846 Toffolis = 88.5% of Toffolis (85.7% of C).**
   Half of it (3,423) is the mirror uncomputation.
2. **Live register footprint: 231 of 260 qubits are named registers**, held
   for the whole circuit; 68 of them (c0..c3) and 58 (square, z) are dead
   weight during parts of the schedule.
3. **Controlled shifts: 830 Toffolis (10.7%)** — denormalize (600) is a
   31-bit-lane controlled rotation per flag, applied on the 40-bit y1.

Rotations (3.2% of C) and the 3 − z correction are minor.

## Hypotheses for Phase 2 (estimates, not results)

| idea | mechanism | est. ΔC | est. ΔQ | est. Δcost |
|---|---|---:|---:|---:|
| A. Measurement-based uncomputation of the Newton/Horner chain where the phase fixup is cheaper than the mirror | replaces Toffoli-for-Toffoli uncompute; conditioned fixups pay ~½ (counted only on shots with bit = 1) | −15…−40% | 0 | −15…−40% |
| B. Spend the 1-bit slack: shrink widths (coef 17→16, square/product 28→27, result 29→28, delta 14→13) | multiplier cost ~ product of widths | −5…−8% | −4…−6 | −7…−10% |
| C. Free Horner intermediates (c1..c3) before the Newton step, re-derive for uncompute | trade Toffolis for qubits | +10…+18% | −51 (−20%) | −5…−10% (only with A) |
| D. Cheaper de-normalization: rotate only the lanes whose bits reach the phase step, or shift by binary s (log₂ stages) instead of 10 unary stages | 600 CSWAPs → ~150–300 | −4…−6% | −0…−10 | −4…−8% |
| D′. (rejected analytically) fold 2^s into the phase step | needs ~300 flag-controlled rotations (each a Toffoli + a rotation) | ≫ +0 | | worse |
| E. Better seed (more pieces / quadratic + 2 NR steps, or a small QROM) | trade Horner for NR iterations | ? | ? | needs model sweep |

A and C interact (C needs cheap uncompute to pay off). B is pure parameter
search on `Precision` via the exact `fixed_point_model` (no simulation needed
until a candidate is chosen). All estimates must be confirmed by the official
verifier (`harness/score.py`, ~12 min locally per full verification).
