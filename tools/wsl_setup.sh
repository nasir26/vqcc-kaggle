#!/usr/bin/env bash
# One-time WSL2 (Ubuntu) setup for vqcc: uv + Python 3.13 venv at /opt/vqcc/venv.
# kickmix.so in the competition data is built for CPython 3.13 / glibc >= 2.34.
# Run as root: wsl -d Ubuntu -u root -- bash /mnt/c/Users/dell/Work/vqcc/tools/wsl_setup.sh
set -euo pipefail

UV_VERSION=0.13.6
UV_TGZ=uv-x86_64-unknown-linux-gnu.tar.gz
mkdir -p /opt/vqcc
cd /opt/vqcc

if ! command -v uv >/dev/null; then
  curl -fsSL -o "$UV_TGZ" "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_TGZ"
  curl -fsSL -o "$UV_TGZ.sha256" "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_TGZ.sha256"
  echo "$(cut -d' ' -f1 "$UV_TGZ.sha256")  $UV_TGZ" | sha256sum -c -
  tar xzf "$UV_TGZ" --strip-components=1 -C /usr/local/bin
fi
uv --version

uv python install 3.13 -q
[ -d /opt/vqcc/venv ] || uv venv --python 3.13 /opt/vqcc/venv -q
uv pip install --python /opt/vqcc/venv/bin/python -q numpy scipy pandas
/opt/vqcc/venv/bin/python -c 'import sys, numpy, scipy, pandas; print("python", sys.version.split()[0], "numpy", numpy.__version__, "scipy", scipy.__version__, "pandas", pandas.__version__)'

# kickmix import check against the competition's prebuilt module.
/opt/vqcc/venv/bin/python -c 'import sys; sys.path.append("/mnt/c/Users/dell/Work/vqcc/data/comp/kickmix"); import kickmix as km; print("kickmix ok:", km.__file__)'
