#!/usr/bin/env bash
# Rebuild the submitted portfolios from the downloads of tools/fetch_all.sh and check every member against
# manifests/portfolio_v*.sha256 (the exact bytes uploaded to Kaggle). Writes data/candidates/portfolio_v{1,2}/
# and submissions/2026-10-29_v{1,2}.zip. If a public source has changed since 2026-10-29 the check fails; the
# submitted zips are also attached to the GitHub release "submissions-2026-10-29" (see manifests/submissions.sha256).
# Usage: tools/build_portfolios.sh   then   ../.venv/bin/python harness/score.py data/candidates/portfolio_v2
set -euo pipefail
cd "$(dirname "$0")/.."
PY=../.venv/bin/python
$PY -I tools/scan_public.py
$PY -I tools/stage_glz.py
C=data/candidates
assemble() {  # name invsqrt_dir dqi_dir dfthcsos_dir
  local d=$C/$1; rm -rf "$d"; mkdir -p "$d"
  cp "$C/$2/invsqrt.kmb" "$C/$3/dqi.kmb" "$d/"
  cp -r "$C/$4/dfthcsos" "$d/"
  (cd "$d" && sha256sum --quiet -c "../../../manifests/$1.sha256") && echo "$1: all members match the manifest"
}
assemble portfolio_v1 pub_invsqrt_e623b659 pub_dqi_c300b06e pub_dfthcsos_ee1619fc
assemble portfolio_v2 pub_invsqrt_e623b659 pub_dqi_c300b06e glz_open_circuits_v33_w34
mkdir -p submissions
for v in 1 2; do
  z=$PWD/submissions/2026-10-29_v$v.zip; rm -f "$z"
  (cd $C/portfolio_v$v && zip -q -X -r "$z" invsqrt.kmb dqi.kmb dfthcsos)
done
echo "BUILD_DONE (upload a zip under the name submission.zip; the Kaggle CLI refused other names with HTTP 400)"
