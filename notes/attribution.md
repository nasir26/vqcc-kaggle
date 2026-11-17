# Attribution (keep current; Apache-2.0 notices travel with any adapted code)

| member or code | author / source | licence | used in |
|---|---|---|---|
| invsqrt 321aff83 and its builder | Syed Asad Ali, Kaggle dataset syed3000/vqcc-own-circuit-portfolio v12 | Apache-2.0 | v6; base for our invsqrt changes |
| dqi decoder builder (7cbe8ecf) | Syed Asad Ali, same dataset | Apache-2.0 | base for our dqi changes |
| dqi 821bf8d1 | Syed's decoder + extractor cutoff idea by Ertugrul Ozer (ozertuu) + product retention by Areeb Ali (areebbb) | Apache-2.0 | v6 |
| dfthcsos f90d6c66 | prvsiyan refit on maoxin123 coded-word loaders (lineage ozertuu, marculera, Syed, Ahmed Berat Ozer) | Apache-2.0 / CC0 | v6 |
| andigu/uncompute | Gu, Kemeny, Yelin, Lukin | Apache-2.0 | ideas only so far |
| invsqrt 4560ac0c, K=6 table fork (patch_k6.py, k6data.json, fork.py) | Ali Haydar Ozdag (ahoirg), kernel qcc-invk6-k6c, on Syed's generator | Apache-2.0 | reference for the next invsqrt step; not yet built here |
| invsqrt dcde7078 | alexchilton v151 (angle refit of the K=6 skeleton), shipped by heliosli | per source | portfolio_v8 |
| invsqrt 64715b8c (runs/invsqrt/20261114-dec7) | dcde7078 + our 7-AND address decoder | Apache-2.0 lineage (Syed, ahoirg) | candidate |
| invsqrt 240ae447 (runs/invsqrt/20261114-clean6) | 64715b8c + our 6-AND table cleanup | Apache-2.0 lineage | best candidate |
| invsqrt e0db1ac7 | Ertugrul Ozer angle refit of ahoirg's K=6 build | Apache-2.0 | not used |
| tools/loader_contract.py, tasks/*/ tools (incl. tasks/invsqrt/syed_model.py, syed_profile_build.py, syed_prof_report.py, k6_angle_lp.py) | ours | | |
| tasks/dqi/syed/retain_areebbb.py | areebbb notebook qai-fewer-toffolis-same-qubits-lb-27-08903, cell 4 (retention planner), vendored verbatim | Apache-2.0 | tasks/dqi/syed/build_variant.py (rebuilds 821bf8d1 byte for byte) |
| extractor cutoff wrapper (in build_variant.py) | Ertugrul Ozer (ozertuu), as applied at cutoff 18 by areebbb | Apache-2.0 | build_variant.py |
| tasks/dqi/syed/anatomy.py, dump_tensors.py, build_variant.py, tasks/dqi/flipgraph_t.c, notes/sources/syed_dqi_anatomy.md | ours (instrumentation, search) on Syed's v12 dqi source | | |

* v10 dfthcsos `58ae6c0d`: unchanged bytes from the public Kaggle notebooks
  `atakanaldemir/qcc-gap-3-residue-repair-and-c43-native-compiler` and
  `mizeroluckygall/quantum-circuits-4033-chemistry-refit-guide` (Kaggle notebooks, Apache-2.0). Not ours.

* dqi `80ee0183` (v11 member, analysed in runs/dqi/20261117-0901-width-floor): Syed Asad Ali v13 decoder `46446af1`
  (Apache-2.0, dataset syed3000/vqcc-own-circuit-portfolio) with Balram Srinivasan's norm-preserving closings and
  boristown's product-cache chains, shipped by the notebooks alexchilton/28-12-lb-which-circuits-survive-private-salt
  and boristown/qcc-gap-3-residue-repair-and-c43-native-compiler (Kaggle, Apache-2.0). Not ours.
* v11 dfthcsos `c4391ffc`: maoxin123 notebooks `qcc-28-14-4-022-toffoli-chemistry-loaders` and
  `qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` (Kaggle notebook outputs, Apache-2.0); also re-shipped by
  leotang09 `vqcc-t7421-submission` and the dataset ratnachand/vqcc-verified-public-floor (dataset licence field
  "unknown"; it credits the maoxin123 notebook, which is the source we rely on). Not ours.
* Chemistry negative-results ledger manwithacat/vqcc-chemistry-negative-results (Apache-2.0): cited for NR-0236 and the
  8-bit rounding-noise results in runs/dfthcsos/20261117-r7c58-null.

* v13 invsqrt `9a78a646`: unchanged public bytes; notebooks alexchilton/28-15-lb-which-circuits-survive-private-salt,
  atakanaldemir/qcc-shared-products-and-controlled-refits (Kaggle, Apache-2.0). Chemistry `889999b0`: leotang09/vqcc-t7421-submission.
