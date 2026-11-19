# Handoff (2026-11-19): moving the VQCC work to a new machine

State of the Kaggle competition `google-verifiable-quantum-circuit-compilation` (team Spinwave) at handoff.

## Where we stand

* Best public score: **v16, Kaggle ref 58523343, public 28.20034**, rank 290 of 3344 (bronze).
  Cutoffs on 2026-11-18 20:08 UTC: top 31.61727, silver (5%) 28.21029, bronze (10%) 28.19215.
* v16 = invsqrt `a0c7a668` + dqi `940c4516` + chemistry (dfthcsos) `889999b0`. All public Apache-2.0 notebook outputs,
  credited in notes/attribution.md. Byte hashes in manifests/portfolio_v16.sha256.
* v15 (ref 58521953) = v16 with dqi `f3f2519e`. Locally 28.2317 on 5 of 7 salts, but `f3f2519e` fails a shot on the
  public salt, so public is 28.18862. Its 20 salt dqi geo mean (70.6399) is the best known, so it is a good private salt bet.
* **Final selections to tick on Kaggle: v16 (58523343) and v15 (58521953).** The better private score counts.
* Deadline 2027-01-20 23:59 UTC. Kaggle evaluation takes 16 to 29 minutes (ledger/kaggle_timing.csv); upload the final
  file several hours early.

## The standing rule from the owner

"The current score shouldn't fall, must increase." So:

1. Only submit a portfolio verified with `harness/score.py` on salt `''` plus `--random-salts 6`, every task passing on
   every salt, whose salt `''` score beats the current best public (28.20034).
2. dqi files: failures depend on file SHA-256 plus salt (one failed shot costs about 0.46% on dqi). Judge a dqi file by a
   20 salt run (`--tasks dqi --random-salts 20`): geo mean must beat 70.4744 (940c4516) AND it must pass salt `''`.
   Ignore `f3f2519e` (already tried as v15).
3. Never edit the official verifier. Only official verifier numbers count. Honest numbers in all notes.
4. Every public member used goes into notes/attribution.md with its source notebook and licence.
5. Commits authored by Nasir Ali only. No Co-Authored-By lines, no AI tool mentions. No dashes used as punctuation in prose.
6. Competition data (data/, *.kmb, *.npz, verifiers, metric) never goes into git. Packaged zips may go to a GitHub
   release (they hold only public Apache-2.0 circuits), as done for earlier versions.
7. After every upload log submit time, scored time, eval minutes and public score in ledger/kaggle_timing.csv.

## Routine (twice a day)

```
bash tools/scan_frontier.sh 1          # downloads newest public notebook outputs, scores new members on 3 salts
```

It prints, per task, the best public member next to the `cur` dict (top of the python block in the script; now v16).
The dqi "BETTER" flag compares a 2 salt worst case with our 20 salt geo mean, so verify dqi with the 20 salt run.
If something is better: copy `data/candidates/portfolio_v16` to `portfolio_vN`, swap the member file(s) from
`data/cand2/pub_<task>_<sha8>/`, run `harness/score.py data/candidates/portfolio_vN --random-salts 6` (about 11 min,
run in background), then package:

```
P=data/candidates/portfolio_vN; D=$(date +%Y%m%d)
(cd $P && find . -type f | sort | xargs sha256sum) > manifests/portfolio_vN.sha256
(cd $P && zip -q -r ../../../submissions/${D}_vN.zip invsqrt.kmb dqi.kmb dfthcsos)
mkdir -p data/upload/vN && cp submissions/${D}_vN.zip data/upload/vN/submission.zip   # name must be submission.zip
../.venv/bin/kaggle competitions submit google-verifiable-quantum-circuit-compilation -f data/upload/vN/submission.zip -m "vN: ..."
../.venv/bin/kaggle competitions submissions google-verifiable-quantum-circuit-compilation | sed -n 3p   # poll until COMPLETE
```

Rank and cutoffs: `kaggle competitions leaderboard <comp> --download -p DIR`, unzip, sort the CSV by Score
(the `-s` table output does not parse). Silver = score at index int(n*0.05)-1, bronze at int(n*0.10)-1.

## Measured nulls (do not repeat without a new idea)

* dqi width: 890 qubit floor; the builder hard allocates, no idle wires at peaks.
* Chemistry R7: 8 bit rounding adds about 170 mHa; a continuous fit within 13.5 mHa would be needed.
* invsqrt efd84ca5 lineage: angles LP optimal, 44 qubit floor, no peephole, 7 AND decoder is a proved lower bound,
  2 conditioned CCZ cleanup minimal.
* More in docs/NOTES.md, notes/RESEARCH_LOG.md and notes/PLAN.md.

## Setting up the new machine

See README.md "Reproduce". Short form, with the workspace `W` one level above the repo:

```
git clone https://github.com/nasir26/vqcc-kaggle.git $W/repo && cd $W/repo
# Python 3.13 venv in $W/.venv with numpy==2.5.4 scipy==1.18.1 pandas==3.1.0 kaggle==2.2.5
# (kickmix.so needs glibc >= 2.34; on older hosts use tools/host_runtime.sh $W)
# Kaggle token in ~/.kaggle/access_token; the account must have joined the competition
tools/fetch_all.sh                     # competition data, vendored metric, starter kit (about 3.7 GB)
bash tools/scan_frontier.sh 3          # rebuilds data/cand2 from public notebooks
```

The submitted zips for v15 and v16 are attached to the GitHub release `submissions-2026-11-19`. To rebuild
`data/candidates/portfolio_v16`, unzip `v16.zip` there and check it against manifests/portfolio_v16.sha256.
dqi scoring needs a lot of RAM (the old host had 503 GB; one dqi verification takes about 1 minute there).
