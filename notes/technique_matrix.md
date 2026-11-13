# Technique matrix (2026-11-13). Impact = estimated change in the leaderboard score from v6 (27.11).
Source key: [paper] competition paper hint, [gu] arXiv:2610.22367, [syed] Syed v12 builders, [ecdsa] ECDSA.Fail / record-and-replay, [ours] new here.

| technique | invsqrt | dqi | dfthcsos |
|---|---|---|---|
| phase-only recovery via trace with Psi = 1/sigma' mod sigma [gu] | n/a | check if Syed's scan already avoids per-position inversion; if not, large T cut | n/a |
| work in place over the syndrome / spare syndrome words as workspace [gu] | n/a | qubits: each one is 0.225% of dqi (0.075% score); 889 -> 870 would be about +0.6% score | n/a |
| failure budget, cutoffs from the input law [gu][syed][ozer] | n/a | already used (cutoff 18); little left, adds draw risk | n/a |
| product retention / idle hosts [areebbb] | needs a qubit | already applied (241) | 0 found |
| fewer or cheaper rotations: margin, single stream, Clifford angles [paper][ours] | 33 rotations are 13% of C; each one about 0.4% of invsqrt | n/a | n/a |
| qubit-for-Toffoli trade [syed] | 46 qubits: 1 qubit = 2.2% of invsqrt (0.7% score) | 1 qubit = 860 Toffolis | Q_tot 427 |
| lower polynomial degree / more segments, truncation tuned by exhaustive check [paper][ours] | regenerate base with a different table; full-domain prover exists in Syed's tools | n/a | n/a |
| cheaper GF(2^12) multiply / tower-field basis [paper][gu] | n/a | depends on how many multiplies remain at 889 qubits | n/a |
| conditional routing instead of conditional arithmetic; decode decisions during uncompute [gu][ecdsa] | maybe in uncompute | key-equation stage | n/a |
| norm-penalised refit (lambda_eff) at new shapes [ours] | n/a | n/a | R7 C58 at 16.6 mHa, norm 152 vs 130.5 needed; up to about 3% chemistry (1% score) |
| quantisation-aware fit at lower brot [paper] | n/a | n/a | earlier tests closed brot 7 (228+ mHa); low value |
| general-contract loader generator [ours] | n/a | n/a | insurance: if eq. (72) is enforced, best public legal member is 9.79 (score 25.82); a legal loader near maoxin's counts would recover most of it |
