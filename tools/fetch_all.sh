#!/usr/bin/env bash
# Download everything the repo does not ship: competition data, starter kit files, the public notebooks and the
# public dataset that the submitted circuits come from. All public sources are Apache-2.0 (competition rules); the
# competition data itself must not be redistributed, so it is fetched here and kept out of git (.gitignore: data/).
#
# Needs the Kaggle CLI (tools/host_runtime.sh installs it into ../.venv) and a token in ~/.kaggle/access_token,
# and the account must have joined the competition.
# Usage: tools/fetch_all.sh          (from the repo root; about 3.7 GB)
set -euo pipefail
cd "$(dirname "$0")/.."
K="${KAGGLE:-../.venv/bin/kaggle}"
export KAGGLE_API_TOKEN="${KAGGLE_API_TOKEN:-$(cat ~/.kaggle/access_token)}"
COMP=google-verifiable-quantum-circuit-compilation

# 1. competition data: verifiers, kickmix, sample submission, paper
mkdir -p data/raw data/comp
[ -f data/raw/$COMP.zip ] || "$K" competitions download -c $COMP -p data/raw -q
[ -d data/comp/verifiers ] || unzip -q -o data/raw/$COMP.zip -d data/comp

# 1b. the Kaggle metric, vendored verbatim for harness/score.py (not redistributed here)
if [ ! -f harness/metric_vendor.py ]; then
  mkdir -p data/metric; "$K" kernels pull metric/google-quantum-ai-metric -p data/metric -m >/dev/null
  ../.venv/bin/python -I tools/vendor_metric.py data/metric harness/metric_vendor.py
fi

# 2. starter kit files used by tasks/dfthcsos
SK=sohier/verifiable-circuit-compilation-starter-kit
for f in FeMoCo76o113e.fixed_shifts.npz starter_kit/pyproject.toml starter_kit/data/systems.toml \
         starter_kit/dfthc/__init__.py starter_kit/dfthc/df_thc_sga.py starter_kit/dfthc/train_df_thc_sga.py \
         starter_kit/dfthc/load_integrals.py starter_kit/dfthc/verify_dfthc.py starter_kit/dfthc/dfthc_u_to_tei.py \
         starter_kit/starter/task2_angles/encode.py starter_kit/starter/task2_angles/trees.py \
         starter_kit/starter/task1_factorization/solution_io.py \
         starter_kit/starter/task1_factorization/check_factorization.py \
         starter_kit/starter/task1_factorization/train_df_thc_qaggle.py; do
  dst="data/starter/$(dirname "$f")"; mkdir -p "$dst"
  [ -f "data/starter/$f" ] || "$K" datasets download $SK -f "$f" -p "$dst" -q --unzip >/dev/null
done

# 3. public notebook outputs (submission.zip of each); staged by tools/scan_public.py
NOTEBOOKS="atakanaldemir/quantum-circuits-iso-gap-dqi-h5 avazaku/gauge-prox-sign-copy-qrom
avazaku/slack-homotopy-897-qubit-dqi busyaprime/lb-22-72431-22x-cheaper-than-google-s-circuits
gedouluhui/qcc-heliosli-v12-22-7003-local-gm-verified-fork heliosli/the-dataset-is-now-public-now-enjoy
kirilltym/quantum-circuits-exact-gauge-5-word-qrom leoprovorov/but-some-q-squared-width-lab
leoprovorov/full-xor-chemistry-no-borrowed-bits nilanjansaha123/auto-portfolio-drop-in-best-of-all-circuits
somejoint/quantum-circuits-22-75-local-gm-897-qubit-dqi zongaobian/quantum-circuits-signed-digits-bm-psi-qrom"
for r in $NOTEBOOKS; do
  o="data/public_out/${r/\//__}"
  [ -d "$o" ] || { mkdir -p "$o"; "$K" kernels output "$r" -p "$o" -q >/dev/null || echo "WARN: no output for $r"; }
done

# 4. notebook sources, read by tasks/dqi/attribute_somejoint.py and the study notes
for r in somejoint/quantum-circuits-22-75-local-gm-897-qubit-dqi ahmedberatozer/quantum-ai-df-thc-group-compression \
         avazaku/gauge-prox-sign-copy-qrom kirilltym/quantum-circuits-exact-gauge-5-word-qrom \
         leoprovorov/full-xor-chemistry-no-borrowed-bits; do
  d="data/public/${r/\//__}"
  [ -d "$d" ] || { mkdir -p "$d"; "$K" kernels pull "$r" -p "$d" -m >/dev/null
                   ../.venv/bin/python -I tools/nb2py.py "$d"/*.ipynb > "$d/code.py"; }
done
../.venv/bin/python -I tools/extract_sources.py data/public/somejoint__quantum-circuits-22-75-local-gm-897-qubit-dqi

# 5. public chemistry dataset (v2's dfthcsos member: open_circuits_v33 circuits + open_circuits_v34 weights)
G=data/public_out/dmitriigluzdov__vqcc-femoco-public-factorization
[ -d $G/files ] || { mkdir -p $G; "$K" datasets download dmitriigluzdov/vqcc-femoco-public-factorization -p $G -q
                     unzip -q -o $G/*.zip -d $G/files; }
echo FETCH_DONE
