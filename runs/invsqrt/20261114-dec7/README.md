# invsqrt 64715b8c: dcde7078 with a 7-AND address decoder (2026-11-14)

sha256 64715b8c1ce5d01a51d86f51604a5ae630e4dbbeba62ad7cb0c04aa0b8811fe2 (invsqrt.kmb; invsqrt.kmx is the same circuit as text).

## Result (official scorer, harness/score.py, verifier unchanged)
| salt | ratio |
|---|---:|
| '' | 26.381944 |
| ec5a85af... | 26.381962 |
| 3dca7bf3... | 26.381949 |
| 9386e5a1... | 26.381957 |
| c866ff01... | 26.381935 |
| 282a99a8... | 26.381964 |
| 901ed458... | 26.381945 |
Base dcde7078: 26.366542 (salt ''). Gain: one Toffoli (1480.75 -> 1479.75 mean, static 1552 -> 1551), Q 46, 33 rotations,
1 T, margin unchanged (116,320,642 units of 2^-64; the 33 angles are byte-identical to dcde7078).

## What is ours
* The only change to dcde7078 is the block that rebuilds the six address bits from the 18 table wires (A0..A12, S1..S4, R)
  after the coefficient inverse (text lines 20561-20900 of dcde7078). The shipped block decodes in the order a5, a4, a0, a1, a3, a2
  with 1+1+2+2+1+1 = 8 ANDs. An exhaustive search over all decoding orders (tasks/invsqrt/decoder_resynth.py with two small C
  helpers: exact one-AND test over the whole affine span, two-AND test) shows the order a5, a4, a3, a1, a0, a2 needs 1+1+2+1+1+1 = 7.
  Each AND is written directly into the target wire (affine frames by CX on existing wires, no ancilla), so width is unchanged.
  The block is a pure CX/X/CCX permutation that produces the same six values and restores all 18 inputs, so no phase changes.
  The replacement block is decoder7_block.kmx.txt, the plans decoder7_plans.json.
* Proof tool tasks/invsqrt/prove_vs_model.py: Syed Asad Ali's exact symbolic checker (whole_text_symbolic.py, sha 5c8ac00c, unchanged,
  Apache-2.0) run with the circuit's 2^-64 phase modulus against OUR exact model (tasks/invsqrt/syed_model.py: ahoirg's K=6 table,
  digest 219d2f76 at their angles, plus dcde7078's 33 site angles). All 3,133,452 inputs, every HMR transcript, x restored,
  scratch zero: proof.log. The same proof passes on dcde7078 itself (proof_control_dcde7078.log, identical model digest fa8a899c).
  Negative controls fail as they should: one dropped CCX (scratch mismatch) and one rotation changed by 1 unit of 2^-64 (phase mismatch).

## Lineage (Apache-2.0)
Syed Asad Ali's v12 invsqrt generator -> Ali Haydar Ozdag (ahoirg) 64-row table build 4560ac0c -> angle refit dcde7078
(alexchilton v151, shipped by heliosli) -> this decoder change (ours).
