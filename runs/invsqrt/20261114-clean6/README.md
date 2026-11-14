# invsqrt 240ae447: 64715b8c (dec7) with a 6-AND table cleanup (2026-11-14)

sha256 240ae44788e93cd1629056243f1a6dae61dd3791e3fec64661f7a9e7d035201f. Mean Toffolis 1477.75 (dec7 1479.75, dcde7078 1480.75),
static 1549, Q 46, 33 rotations, 1 T, angles byte-identical to dcde7078, margin 116,320,642 unchanged.

Official scorer (score.log): '' 26.412805; random salts 26.412832, 26.412823, 26.412794, 26.412818, 26.412822, 26.412823.

## What is ours
The table cleanup (text lines 20871-22360 of 64715b8c: pays 30 pending loader debts, erases 17 table outputs) used 8
unconditional pair/triple-product ANDs ("banks") on address-bit monomials. Our model of the cleanup
(tasks/invsqrt/cleanup_extract.py, cleanup_opt.py): every obligation is a function of the 7-bit table address; a payment is free
iff it lies in Q(S) = span{1, u, u v : u, v live wires}; read backwards in time, the live set only grows, so free erasures are
greedy-optimal and only the bank set has to be searched. tasks/invsqrt/cleanup_exh.py enumerates bank sets exhaustively (pair
monomials + triples built on a pair bank) in a chosen basis of the address bits:
* original basis: 7 banks feasible, 6 infeasible (all sets; also with slot 0);
* random GF(2) bases of the six address bits: 6 banks feasible (basis seed 2, cleanup_exh_6_s2.pkl); 5 banks infeasible in 400 bases.
tasks/invsqrt/cleanup_emit.py writes the new region: pay the 30 debts first (all outputs live), erase outputs in the reverse of the
closure order with banks created lazily on freed output wires (no extra width), erase banks last; every payment is the exact
quadratic expansion over live wires; affine bank factors are formed by CX frames around each CCX.

## Proof
proof.log: tasks/invsqrt/prove_vs_model.py (Syed Asad Ali's exact checker, unchanged, modulus 2^64, against our model with
dcde7078's angles): PASS on all 3,133,452 inputs and every HMR transcript, x restored, scratch zero.

Lineage: Syed Asad Ali (generator) -> ahoirg (K=6 table, 4560ac0c) -> dcde7078 angles -> ours: dec7 decoder + this cleanup.
