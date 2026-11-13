# Rules summary (from docs/RULES.md, the Kaggle rules digest of 2026-10-27; re-check the live page before the final upload)

External code and data are allowed when they are publicly available at no cost to other participants
("Reasonableness Standard"); public Apache-2.0 notebooks, datasets and repos such as andigu/uncompute qualify,
and we keep their notices and credit them in notes/attribution.md. Private sharing of code or data outside the
team is forbidden, while public forum sharing is fine. Competition data must not be redistributed (it stays git
ignored and is never pushed). Winners license their submission and its generating code under Apache-2.0 and must
deliver reproducible code with an environment description. Limits: 5 submissions a day, 2 final selections, teams
of at most 5, merges allowed until the entry and merger deadline 2027-01-13; final submission deadline
2027-01-20 23:59 UTC (Kaggle took 24 min to score our last upload). Prizes: leaderboard top 6, a $10k milestone
snapshot on 2026-11-20 23:59 UTC (needs a public notebook), $10k for the longest leader (window ends 2027-01-04),
and $10k per task for the best single-task score among selected submissions.

## The angle-loader contract question (forum thread 757522)

The paper's eq. (72) defines `Angle_k : |a>|z> -> |a>|z XOR Delta_k(a)>` for every z. The verifier only simulates
reachable states (z equal to the previous batch on the forward pass, the current batch on the reverse pass).
Measured 2026-11-13 (scratchpad znum.py on portfolio_v6/dfthcsos, prvsiyan f90d6c66 with maoxin-lineage
loaders): on reachable z every loader reproduces its delta table exactly; on random z, 1171 to 1200 of 1220
addresses give a wrong delta for k = 1, 4, 9, 14. So every loader after the first reads the incoming word bits.
The construction is physically sound for the algorithm (z is always the previous batch of the same address),
but it does not satisfy eq. (72) as written. No host answer was found. Per the team rule, treat it as not
allowed until the hosts say otherwise; the decision on what to submit is the user's (see notes/PLAN.md).
