# dqi qubit floor of 80ee0183 (Syed v13 line, 890 qubits): measured, no candidate

Base: public `80ee0183de812b5b...` (890 Q, 368,606 static Toffoli-likes, ratio 70.4323 with no failed shot).
Lineage: Syed Asad Ali v13 decoder `46446af1` (Apache-2.0), Balram Srinivasan norm-preserving closings,
boristown product-cache chains; see notes/attribution.md. The v13 builder is not public (the dataset
`syed3000/vqcc-own-circuit-portfolio` ships only the .kmb), so generator-level work is only possible on v12 (889 Q),
which starts about 3.8% behind v13 on cost.

## Measurements [ours]

1. Builder cap test (Syed v12 source, tasks/dqi/syed/build_variant.py --maxq Q --no-retain): the builder does not
   adapt to a lower cap; it stops at a hard allocation: Q=860 fails at 840+24 (the extractor carry), Q=870 at 865+8,
   Q=880 at 877+12 (the GF(2^12) norm of the nested-norm inverse). Logs: maxq*.log.
2. Allocation anatomy (runs/dqi/anatomy/syed_v12_cut15.json): persistent state is 864 to 866 in every stage
   (840 syndrome + 24 carry + 1 to 2 flags). The remaining 23 to 25 wires are the transient workspace of the
   GF(2^24) and GF(2^12) inverses (nested norms 12+6+3+3; compact_inverse_twelve 22 helpers) and of the
   gauge_park_lender products. 889 is reached at several hundred allocation sites of about 30 function types in
   the extractor, outer (transpose14), finish and every closing; only the scan stays at 875.
3. Structural live profile of 80ee0183 (tasks/dqi/width/live_profile.py): live 889 for 5.6M and 890 for 3.4M of the
   qubit-touching instructions; the peak is spread over the whole quantum part, not one site.
4. Value liveness (tasks/dqi/width/value_live.py, the official sampler and simulator, 512 shots, 20k-line chunks,
   2,858 boundaries): 358 boundaries have >= 888 wires nonzero in some shot, 12 have all 890; no wire is zero in every
   shot. So no allocated wire is idle at the peaks and wire renaming cannot free one.

## Conclusion

The width is set by the algorithm (840-qubit syndrome register used in place + a 24-bit carry + an out-of-place
field inverse), not by allocation slack. A cut needs a new extractor and closing design: an in-place or
lower-workspace GF(2^24)/GF(2^12) inverse used at every one of the hundreds of peak sites, plus re-tiling the lender
products, all on the v12 source that starts 3.8% behind v13. Break-even for v12 to beat 80ee0183 at unchanged T is
Q <= 872 (17 qubits); the best case of the design (persistent floor 865) is -24 to -25 qubits. This is a multi-day
redesign with uncertain T cost, not an edit; not attempted further here.
