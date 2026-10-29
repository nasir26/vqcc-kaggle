#!/usr/bin/env bash
# User-level runtime for the official kickmix.so on hosts with glibc < 2.34 (e.g. Ubuntu 20.04), no root needed.
# kickmix.so needs GLIBC_2.34 and GLIBCXX_3.4.32 (Ubuntu 24.04 runtime). This unpacks Ubuntu 24.04's libc6 and
# libstdc++6 into $W/rt/lib, copies uv's CPython 3.13 into $W/rt/python and patches its interpreter and RPATH,
# so every process the verifier forks or spawns uses the same loader. Then builds $W/.venv on it.
# Usage: tools/host_runtime.sh /path/to/vqcc_kaggle   (needs $W/.tools with uv and patchelf: pip install uv patchelf)
set -euo pipefail
W=$(readlink -f "${1:?work dir}")
B=http://archive.ubuntu.com/ubuntu/pool/main
mkdir -p "$W/rt/debs" "$W/rt/lib"
cd "$W/rt/debs"
for p in g/glibc/libc6_2.39-0ubuntu8.9_amd64.deb g/gcc-14/libgcc-s1_14.2.0-4ubuntu2~24.04.1_amd64.deb \
         "g/gcc-14/libstdc++6_14.2.0-4ubuntu2~24.04.1_amd64.deb"; do
  [ -f "$(basename "$p")" ] || wget -q "$B/$p"
done
for f in *.deb; do dpkg-deb -x "$f" ../root; done
cp -a ../root/usr/lib/x86_64-linux-gnu/*.so* ../root/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 "$W/rt/lib/"
PD=$(dirname "$(dirname "$(readlink -f "$("$W/.tools/bin/uv" python find 3.13)")")")
rm -rf "$W/rt/python" && cp -a "$PD" "$W/rt/python"
"$W/.tools/bin/patchelf" --set-interpreter "$W/rt/lib/ld-linux-x86-64.so.2" --force-rpath \
  --set-rpath "$W/rt/lib:\$ORIGIN/../lib" "$W/rt/python/bin/python3.13"
rm -rf "$W/.venv" && "$W/rt/python/bin/python3.13" -m venv "$W/.venv"
"$W/.tools/bin/uv" pip install --python "$W/.venv/bin/python" -q numpy==2.5.4 scipy==1.18.1 pandas==3.1.0 kaggle==2.2.5
"$W/.venv/bin/python" -c "import platform; print('glibc', platform.libc_ver()[1])"
