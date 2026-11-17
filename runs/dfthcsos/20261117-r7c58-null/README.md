# R7 chemistry shape (7,143,C): measured null, 2026-11-17

Question: can a rank R=7 DF-THC table (1,077 angle addresses instead of 1,220) beat the public frontier chemistry
c4391ffc (ratio 11.388691; lambda_eff 46.9217, T 14,706 = 8,044 angle + 6,662 heuristic, Q 427; shape (8,143,44),
brot 8, J 5; error_1 = error_2 = 20.000 mHa, E_gap on its floor 3.914898)?

## Projection [ours] (official heuristic_costs; angle loaders scaled linearly in addresses, which matches our planner's
block model: products and cache Toffolis both count the 16-address high blocks)
| shape | heuristic T | projected T | projected ratio |
|---|---:|---:|---:|
| (8,143,44) frontier | 6,662 | 14,706 | 11.389 |
| (7,143,58) | 7,193 | 14,294 | 11.717 |
| (7,143,54) | 6,918 | 14,019 | 11.947 |
| (7,143,50) | 6,643 | 13,744 | 12.186 |
lambda_eff barely moves with the shape or the norm: Lambda_h2 with offsets ~ 1/4 sum W^2 is pinned by the E_gap floor
(frontier: lambda_h2 270.117 vs 1/4 sum W^2 270.0; pure 1/4 sum(sum_b|w|)^2 is 130.596), so the norm penalty (mu) is moot.

## Measurements [ours]
* Continuous fits, mu 0, warm start from r7_c58_mu0.5 (tasks/dfthcsos/fit/fit_shape.py), stopped at ~1,700 iterations:
  C46 27.35, C50 22.11, C52 20.00, C54 18.46 mHa (still falling slowly). Best R7 point: C58 mu0.5, 16.44 mHa.
* 8-bit rounding of the C58 16.44 mHa fit on the frontier tree (our build_words.py: coordinate-descent rounding, offsets
  W fitted to the gap floor, one-body rows from h1_prime): official evaluate_words error_2 184.45 mHa, error_1 54.98 mHa.
* Weights-only refit at those frozen 8-bit vectors (fit_shape --round-brot 8): 184.4 -> 119.7 mHa at 400 iterations, flat.
* Planner scale test (scale_test.py, our plan_core on the frontier k=1 delta): A=1220 best 219 products.

## Why it fails
8-bit integerisation adds about 14-17 mHa of noise in quadrature for a fresh fit (public ledger
manwithacat/vqcc-chemistry-negative-results, Apache-2.0: NR-0236 tried exactly (7,143,50) by group merge, 19.1 mHa
continuous, killed; NR-0153/0177 Lera's recipe noise 14.2-15.6 mHa; NR-0215/0216/0212 rounding-aware training nulls).
So an R7 table needs a continuous fit <= ~13.5 mHa at C <= 54 to land under 20 mHa; our R7 fits sit at 16.4 (C58) to
18.5 (C54). Even C58 would round to about sqrt(16.44^2 + 14.6^2) = 22 mHa. No candidate was built; no circuits.

Reopen if: an integeriser with rounding noise <= ~10 mHa on fresh fits appears, or an R7 continuous fit <= 13.5 mHa at C <= 54.
