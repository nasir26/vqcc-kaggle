# Research log

## 2026-11-13
- Metric confirmed from the hosts' scoring code (notes/metric.md): geometric mean of ref/cost; 1% on any task is 0.33% on the score. Gold needs +5.2% on the product of ratios, the leader +34.3%.
- Loader contract: tools/loader_contract.py (ours) feeds random incoming words with the real simulator. Hosts' reference loaders PASS eq. (72); v6, maoxin v22, all pub_dfthcsos members and glz v23+ FAIL (they only work on reachable states); glz open circuits v21, v22, v26-v28 PASS. Best legal public chemistry 9.79 vs 11.336.
- Gu et al. repo cloned; their dqi (442k T, 1,837 Q) is about 5x worse than the public frontier on R*Q^2*T; coulomb and fe2s2 use different contracts.
- Syed Asad Ali v12 builders (Apache-2.0) reproduce byte for byte here: dqi 7cbe8ecf in 154 s, invsqrt 321aff83 in 75 s with the full-domain exact proof. These are our base generators.
- Gu dqi reproduced with their evaluator (uv run tools/eval.py dqi-reed-solomon): 442,397 Toffoli, 1,837 peak qubits, 7 wrong signs in 100,000 shots (budget 100), verdict OK. Matches the paper.
- Not yet read in full: Gu SI, Khattar et al. arXiv:2510.10967 (51-Toffoli multiplier), hardware RS decoder literature, Low et al. Table 3, kickmix builder library source (not in the competition files; Qualtran path to find).

## 2026-11-14 invsqrt generator track (Syed v12 base, then ahoirg K=6)
- Fresh rebuild of 321aff83 byte for byte (data/work/inv_gen/b0). Instrumented build (tasks/invsqrt/syed_profile_build.py, ours) gives the
  per-stage table in notes/sources/syed_invsqrt_anatomy.md: divider 270 fwd + 321 inv, endpoint 113 (64 CSWAP), root 96+96,
  product 104+133, tables 56+71, coefficients 44+44+39; 46 live qubits in nearly every block.
- Standalone exact model (tasks/invsqrt/syed_model.py, ours) reproduces the frozen oracle digest 8bd482a8 / margin 124,370,688 and ahoirg's
  K=6 digest 219d2f76 / margin 116,291,417. Error budget at e=0: numerator -0.90..0.64 tol, division +-0.27..0.46 tol, so dropping a
  quotient row (needs <0.57 tol numerator error) is not possible without a quadratic term.
- 4560ac0c (ahoirg) = 64-row coefficient table, own loader certificates (27 + 29 ANDs vs 56 + 70), 7-bit slope rows, angle LP; dcde7078 =
  same skeleton with a slightly better angle refit (+0.025 % margin). Our K=6 angle LP: continuous optimum 116,320,644, i.e. no angle gain.
- Running ahoirg's published driver/fork code locally was refused twice by the session's permission classifier (third-party code), so no
  K=6 tree was built here and no candidate beyond 26.366542 exists yet. Next step needs that permission or our own re-implementation of
  their fork (model json swap + pin cascade + their patch_k6.py).

## 2026-11-14 (later) smaller table and quadratic correction: measured dead ends (exact model)
- Coefficient form recovered from ahoirg's data: D(v) = A - sum_j b_j(v) c_j(S), c_top = S, c_j = (S + 2^(t-1-j)) >> (t-j) (constant absorbed in A).
- Per-v slack table (tasks/invsqrt/table_feas.py, ours): each v's phase depends only on D(v); feasible D sets are only 2 to 7 integers wide.
  Exact per-segment search (tasks/invsqrt/table_search.py, ours) reproduces K=6 at exactly 116,291,417 (control).
- 32-row table (K=5), circuit form, fixed K=6 angles: 7 rows min slack -566,201,936 (fails, segments 0-3, small v); 6 rows -8.3e9; K=6 with 5 rows
  -6.5e8. A piecewise-linear 32-row table cannot pass; only a per-segment quadratic would (real-valued fit), which needs a new multiply.
  Cost side also negative: one more slope row and a wider window cost about +48 Toffolis over the three coefficient passes vs about -30 from loaders.
- Quadratic correction in h: even a perfect numerator lets the last quotient row go with margin 3.16e8, but the last row is the narrowest
  (k = 9, 2-bit add): dropping it saves about 6 to 8 Toffolis + 1 rotation (about 13 to 15 Toffoli-eq), while the h^2 term (up to 12 units of 2^-27,
  times a v-dependent coefficient) costs at least about 40 Toffolis forward + uncompute. Using it for margin instead: at most 2.7x, i.e. about 6.6
  Toffoli-eq. Both closed.
- The remaining shaves (decoder resynthesis, coefficient inverse, affine rerun) are each about 1 to 3 Toffolis (0.06 to 0.18 % on invsqrt) and need
  a K=6 build tree, i.e. a clean-room re-implementation of ahoirg's patch_k6.py (loader certificate interpreter, slope frames, decoder, cleanup),
  estimated 1 to 2 days. Not started pending a decision.

## 2026-11-14 (dqi generator track on Syed v12)
- Reproduction: tasks/dqi/syed/build_variant.py (Syed v12 source copy in data/work/dqi_gen/root + Ozer cutoff 18 wrapper + areebbb retention, vendored as tasks/dqi/syed/retain_areebbb.py) rebuilds 821bf8d1 byte for byte (static 383,655 -> 383,414, 241 retained, 412 s). Official scorer salt '': ratio 67.8478388, 54 s per salt here.
- Anatomy (ours, tasks/dqi/syed/anatomy.py, exact: 384,003 of 384,003 static T attributed): notes/sources/syed_dqi_anatomy.md. Extractor 39.4%, outer/Forney preimage 30.0%, synthesis 17.0%, scan 11.5%, finish 2.1%. 80.9% of all T is bilinear field products: 1,376 GF(2^24) rank-99 products (35.5%; 1,184 of them are the extractor's query steps) and about 4,150 GF(2^12) rank-42 products (45.5%). Every stage but the scan peaks at 889 (scan 875), at about 99 distinct call sites.
- Nulls by analysis: scan is 11 T per tested point = multiplicative-complexity floor (Gu's 23 is far above); every composed decomposition of GF(2^24) (GF(4)^12, GF(8)^8, GF(16)^6, GF(64)^4, elliptic Chudnovsky over F2) gives >= 99, and of GF(2^12) gives >= 42; high error weights are common (P(w=35)=2.8%) so no high-weight failure budget; incremental-convergent extractor (2 products per slot instead of i) needs about 1,700 qubits.

## 2026-11-14 invsqrt direct edits on dcde7078: first gain (+1 Toffoli)
- prove_vs_model.py (ours): Syed's exact checker at modulus 2^64 against our model + dcde7078 site angles; dcde7078 itself PASSES (control),
  negative controls fail. Model margin 116,320,642 = the angle LP optimum.
- Audits on dcde7078 text: affine products 0 findings; 647 recomputed-product pairs, all cross a 46-live point (no spare lane);
  affine-dependent live wires only at 14 sparse checkpoints (5 at 46 live), not enough to hold a product across any pair.
- Free table edits (XOR masks on loaded A0..A9, S1..S3, exact per-v slack): none raises the margin (all worse).
- Decoder: order a5,a4,a3,a1,a0,a2 needs 7 ANDs instead of 8 (exhaustive one-/two-AND tests). Spliced into dcde7078:
  64715b8c, full-domain proof PASS, official ratio 26.381944 on salt '' and 26.381935..26.381964 on 6 random salts (runs/invsqrt/20261114-dec7).
- S4 rebuild (2 ANDs at coefficient inverse): no one-AND form with L over the plan wires plus any 12 extra live wires (sampled 2048 inputs). Closed for now.
- Width-forced conditional recomputations in coefficient and divider inverse rows (0.5 each) need a free lane at 46-live peaks: none.
