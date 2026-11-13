# Leaderboard metric (verified against the hosts' scoring code)

Source: the Kaggle metric notebook `metric/google-quantum-ai-metric` (id 138355854), vendored verbatim in
`harness/metric_vendor.py`; see its `score()` function and module docstring.

## Definition

For each leaderboard split (public about 50% of test data, private the other 50%), each with its own secret salt:

    ratio_task = baseline_cost(task, salt) / cost(task, salt)          task in {invsqrt, dqi, dfthcsos}
    score      = (ratio_invsqrt * ratio_dqi * ratio_dfthcsos) ** (1/3)

* `cost` is the verifier's own score for the task (lower is better):
  * invsqrt: Q * (Toffoli + T/4), rotations priced at 0.56 log2(1/eps) + 5.3 T.
  * dqi: R(eps+) * Q^2 * T.
  * dfthcsos: lambda_eff * T_tot * Q_tot.
* `baseline_cost` is the hosts' reference submission run under the same salt, so the reference scores 1.0.
* Any failed verification raises an error, and the submission gets no score at all. There is no partial credit.
* The salt changes the simulator seeds. invsqrt and dfthcsos costs barely move with it; dqi moves through
  its decode failures (eps+ and R).

## Worked example (v6, salt '', public LB 27.11056)

| task | baseline_cost | our cost | ratio |
|---|---:|---:|---:|
| invsqrt | 2,076,774.23 | 80,162.73 | 25.906979 |
| dqi | 24,439,463,583,672.9 | 360,209,905,486.0 | 67.847839 |
| dfthcsos | 3,355,599,588.32 | 296,010,654.33 | 11.336077 |

(25.906979 * 67.847839 * 11.336077) ** (1/3) = 27.11056, the public LB value.

## What it implies for effort

* The score is scale free per task: a 1% cost cut on any task lifts the score by about 0.33%,
  whichever task it is. So effort should go where a percent is cheapest, not to the "biggest" task.
* dqi: 1% fewer qubits cuts its cost by about 2%, i.e. about 0.67% on the score. invsqrt: 1% fewer qubits
  gives about 0.33%. dfthcsos: 1% on any of lambda_eff, T_tot or Q_tot gives about 0.33%.
* Targets from 27.11056:
  * gold (27.573 on 2026-11-13): the product of the three ratios must rise by 5.2%, e.g. 5.2% on one task.
  * leader (29.909): the product must rise by 34.3%, e.g. about 10.3% on every task, or 34% on one.
* Because the score is the cube root of a product, a gain on one task cannot be cancelled by another unless
  that task gets worse. Each task can be improved and swapped in independently.
