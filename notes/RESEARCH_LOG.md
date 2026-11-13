# Research log

## 2026-11-13
- Metric confirmed from the hosts' scoring code (notes/metric.md): geometric mean of ref/cost; 1% on any task is 0.33% on the score. Gold needs +5.2% on the product of ratios, the leader +34.3%.
- Loader contract: tools/loader_contract.py (ours) feeds random incoming words with the real simulator. Hosts' reference loaders PASS eq. (72); v6, maoxin v22, all pub_dfthcsos members and glz v23+ FAIL (they only work on reachable states); glz open circuits v21, v22, v26-v28 PASS. Best legal public chemistry 9.79 vs 11.336.
- Gu et al. repo cloned; their dqi (442k T, 1,837 Q) is about 5x worse than the public frontier on R*Q^2*T; coulomb and fe2s2 use different contracts.
- Syed Asad Ali v12 builders (Apache-2.0) reproduce byte for byte here: dqi 7cbe8ecf in 154 s, invsqrt 321aff83 in 75 s with the full-domain exact proof. These are our base generators.
- Gu dqi reproduction (uv run tools/eval.py dqi-reed-solomon) started; result pending.
- Not yet read in full: Gu SI, Khattar et al. arXiv:2510.10967 (51-Toffoli multiplier), hardware RS decoder literature, Low et al. Table 3, kickmix builder library source (not in the competition files; Qualtran path to find).
