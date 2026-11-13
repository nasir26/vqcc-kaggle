# Plan (2026-11-13), for approval before Phase B

## Where we are
v6 = 27.11056 public, rank 58. Every member is public (Syed Asad Ali, areebbb, ozertuu, prvsiyan, maoxin123).
Gold (rank 15) is 27.573 (+5.2% on the product of ratios); the leader 29.909 needs +34.3%.
The brief assumed Gu et al.'s dqi is the floor. It is not: the public frontier is about 5x better on dqi, so
"port Gu" (Phase B step 3) is dropped. Our base generators are Syed's v12 builders, which rebuild byte for byte here.

## Ranked directions (gain on the leaderboard score / engineering days; estimates, not promises)

| # | direction | ours? | est. score gain | days | gain/day |
|---|---|---|---:|---:|---:|
| 1 | dqi stage anatomy of Syed v12 at Q=889, then T cuts in the generator (scan, multiplies, key equation) | [ours] on [syed] | +0.3 to 1.3% | 3 | high |
| 2 | invsqrt: fewer/cheaper rotations (33 rotations = 13% of C) via margin and output layout in Syed's generator, proved on all 3.1M inputs | [ours] on [syed] | +0.3 to 1.0% | 2-3 | high |
| 3 | chemistry: norm-penalised refit at R7 C58 (16.6 mHa, norm 152 vs 130.5 target) then coded-word loaders for that shape | [ours] | up to +1.0% | 4-5 | medium |
| 4 | dqi qubits: move scratch into spare syndrome words (889 -> 870) | [ours]/[gu] idea | +0.6% if 19 qubits | 4-6 | medium |
| 5 | invsqrt qubits 46 -> 44 by a further qubit-for-Toffoli trade | [ours] on [syed] | +1.4% if free, likely +0.5% net | 4-6 | medium |
| 6 | general-contract (eq. 72) loader generator near maoxin's counts | [ours] | 0 now; +4.9% vs the legal fallback if hosts enforce eq. 72 | 4-5 | insurance |
| 7 | evaluator-guided search loop over generator knobs (OpenEvolve style) | [ours] | unknown, multiplies 1-5 | 3 to set up | later |
| 8 | dqi field arithmetic in a tower basis GF((2^6)^2) | [ours] | depends on step 1 | 5+ | after 1 |
| 9 | invsqrt different table (degree/segments) regenerated from base | [ours] | unknown | 5+ | after 2 |
| 10 | dqi decision decoding during uncompute instead of stored bits | [gu][ecdsa] | depends on step 1 | 5+ | after 1 |

Honest expectation: directions 1 to 5 together might give +2 to +4%, which is at or near gold (27.5 to 28.2).
The leader's +34% is not reachable with these; it needs a structural idea on dqi or chemistry that no public source
shows. Step 1's anatomy is what tells us whether such an idea exists in dqi.

## First week, if approved
Days 1-2: dqi anatomy (per stage T and live qubits) and invsqrt rotation study, each ending in a measured candidate.
Days 3-4: best of those through the official verifier on salt '' + 6 salts; first submission candidate with one [ours] change.
Days 5-7: chemistry refit (direction 3) in the background; direction 4 or 5 depending on the anatomy.

## Decisions I need from you
1. Loader contract (eq. 72): keep the reachable-state chemistry the whole top of the board uses (my recommendation),
   and build the legal generator (direction 6) only as insurance? Or switch now to the legal fallback (score about 25.8)?
   Asking the hosts publicly on the forum is your call.
2. Compute: may I run multi-hour jobs (fits, full-domain proofs, 7-salt dqi checks) without asking each time?
3. Order: start with directions 1 and 2 in parallel, as above?
