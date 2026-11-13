# Competition paper, arXiv:2610.23832v2 (Khattar, Rubin, Gidney, Broughton, Low, Babbush), read in full 2026-11-13

## Host hints (places the paper says "can be improved" or offers an alternative)
- Sec III: hosts committed SHA-256 hashes of internal runs that beat everything reported to date; all three benchmarks "can be further improved" (Acknowledgments).
- invsqrt (III A 1): "not using a cubic polynomial over a small rescaled range but a simpler polynomial over a larger range may reduce cost"; "the accuracy of coefficients output by QROM can be further optimized"; "simply finding a good polynomial approximation over the input domain".
- invsqrt (III A 2): Newton step computed on the unshifted 17-bit y0 and shifted afterwards, which saves 30 n_p ANDs: the hosts already think in terms of where the shift sits.
- dqi (III B 1): "Implementations may recover error symbols one at a time or compute the required parity directly".
- dqi (III B 2): "Every part of this baseline (explicit remainder storage, pointer-driven EEA steps, polynomial-basis F_2^12 arithmetic, and per-position Itoh-Tsujii inversion) can be improved." Mentions a hand-tuned 51-Toffoli multiplier (Ref 12) vs their 63.
- dqi (III B 3): decoding failures are allowed; R(1e-5, 1e-4, 1e-3, 1e-2) = 1.02, 1.06, 1.21, 1.94; zero failures in 102,400 shots pays the floor R about 1.19. The floor is set by N, so failures only ever cost.
- chemistry (III C): optimize (R, B, C, u, w, W) under 20 mHa and the floors; choose J, brot, tree, loader circuits; S fixed to baseline.
- chemistry (III C 4, eq. 72): Angle_k is defined as |a>|z> -> |a>|z XOR Delta> for every z (see notes/rules.md: the public frontier only meets this on reachable z).

## Cost model details that matter
- invsqrt: Q counts every qubit; C = Toffoli + T/4 with each fine Z_POW priced 0.56 log2(1/eps) + 5.3 T, eps = pi * min margin / n_rot. Clifford angles (multiples of 1/4 turn) are free. With 33 rotations at about 28 T each, rotations are about 13% of C in the current best (321aff83).
- dqi: S = R * Q^2 * T. The syndrome alone is 840 qubits, so the current 889 has only 49 workspace qubits; the qubit floor is 840 (12% of S at most from Q).
- chemistry: Q_tot = persistent (state prep + J*brot words) + largest temp among Outer, Inner and Angle_k.
