# 2026-11-14 dqi generator track on Syed v12: reproduction, anatomy, multiplier search (no candidate)

No new dqi file beats 821bf8d1 from this run. Everything here is measurement.

## Reproduction (not ours except the driver)
- tasks/dqi/syed/build_variant.py: Syed Asad Ali's v12 source (copy in data/work/dqi_gen/root, untouched) +
  Ertugrul Ozer's extractor cutoff wrapper at 18 + areebbb's retention planner (vendored verbatim as
  tasks/dqi/syed/retain_areebbb.py). Output sha256 821bf8d157c03c3e868a0099b0ab1438cfba664ab1bc6fec3210654099b672a3,
  byte-identical to data/candidates/portfolio_v6/dqi.kmb (sha256.txt). Static T 383,655 -> 383,414 (241 retained).
- Official scorer, salt '': ratio 67.8478388 (scorer_salt_empty.txt), 54 s.
- The driver takes `--patch mod.py` (module with apply(P) that rebinds functions on the live pipeline modules),
  so any future change lands like for like on top of cutoff 18 + retention.

## Anatomy (ours)
- tasks/dqi/syed/anatomy.py: proxy builder, exact attribution of all 384,003 static Toffoli-like gates.
  Summary in notes/sources/syed_dqi_anatomy.md, raw chains in runs/dqi/anatomy/syed_v12_cut15.json,
  breakdown.txt here.

## Multiplier rank search (ours)
- tasks/dqi/flipgraph_t.c (our flip graph, target tensor taken from the start scheme so it runs in Syed's
  basis). Start schemes dumped by tasks/dqi/syed/dump_tensors.py: Syed's rank-99 GF(2^24) tensor and his
  rank-42 GF(2^12) tensor (data/work/dqi_gen/tensors).
- Runs: 160 walks on GF(2^24) and 32 on GF(2^12), 2 h each, 192 cores (data/work/dqi_gen/fg24, fg12);
  48 Frobenius-symmetric walks on GF(2^24) from the trivial normal-basis scheme (stopped after 4 min: 575 of 576,
  far too slow to reach about 98).
- Result: see RESULT below.
- Value had it worked: -1 rank on GF(2^24) = -1,376 static T (0.36% of dqi); -1 on GF(2^12) = about -4,150 T (1.08%).

## RESULT
- 160 GF(2^24) walks x 2 h (10:06 to 12:06, plateau 200,000 flips, plus transitions) from Syed's rank-99 scheme: no
  scheme below 99. 32 GF(2^12) walks x 2 h from Syed's rank-42 scheme: none below 42 (same as our 2026-10-29
  200 x 1 h walks from our own rank-42 scheme). So: no candidate, nothing to score beyond the reproduction.
