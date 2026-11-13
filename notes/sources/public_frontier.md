# Public Kaggle frontier, 2026-11-13 (what we actually have to beat)

| task | member | origin | Q | T per shot | ratio |
|---|---|---|---:|---:|---:|
| invsqrt | 321aff83 | Syed Asad Ali, VQCC Own-Circuit Portfolio v12 (Apache-2.0, full builder source) | 46 | 1,511.57 Toffoli + 1 T + 33 rotations | 25.907 |
| dqi | 821bf8d1 | Syed v12 decoder + Ozer extractor cutoff 18 + areebbb product retention (241 products) | 889 | 382,600 | 67.848 |
| dfthcsos | f90d6c66 | prvsiyan refit on maoxin123 coded-word loaders (lineage ozertuu, marculera, Syed) | 427 | about 14,8xx | 11.336 |

Sources pulled: data/src_pull/syed_v12 (builders: invsqrt 43k lines as 13 patches on a frozen base generator plus full-domain proof passes; dqi 46k lines, entry integration_v7/gen_dqi.py; dfthcsos plans + emitter), data/src_pull/nov13 (areebbb, ozertuu, kirilltym, maoxin v25, prvsiyan notebooks).

Notes from areebbb's notebook: a failed dqi shot costs about -0.041 on the board; the dqi file's SHA decides the test draw ("the draw belongs to the bytes"); their audit found min_qubits = qubits (no relabelling saves a dqi qubit) and no repeated products left in the loaders. The invsqrt went from 62 to 46 qubits through a qubit-for-Toffoli trade.
