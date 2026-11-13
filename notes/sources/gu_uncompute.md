# Gu, Kemeny, Yelin, Lukin, arXiv:2610.22367 and github.com/andigu/uncompute (Apache-2.0), cloned to data/ext/uncompute

Read: the repo README and the dqi-reed-solomon, coulomb-potential and chemistry-fe2s2 READMEs and result tables.
Not yet read: the paper PDF and SI in full (only the summary relayed by the user and the repo READMEs).

| task | discovered (T, Q) | compared with our v6 member |
|---|---|---|
| dqi-reed-solomon | 442,397, 1,837 | ours 382,600, 889: theirs is about 5x worse on R*Q^2*T |
| coulomb-potential | 1,140, 142 | different contract (8-bit coordinates, 25-bit accumulator, 32-unit absolute error, no phase) |
| chemistry-fe2s2 | 14,978, 126 | alias-sampling state prep, not our angle loaders |

Ideas worth keeping (technique matrix): phase-only recovery Tr(nu * omega(beta) * Psi(beta)) with Psi = 1/sigma' mod sigma; Berlekamp-Massey with rescaled replace update and routing; delta never stored; one-entry history stack with a failure budget; per-round adaptive coefficient cutoffs from the DQI weight law; omega in place over the syndrome. General principles: conditional routing instead of conditional arithmetic; decode branch decisions from current state during uncompute; spend the failure budget on rare expensive inputs. Several of these are already in the public frontier (Syed's extractor cutoffs are the failure-budget idea).
