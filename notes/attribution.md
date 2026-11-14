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
