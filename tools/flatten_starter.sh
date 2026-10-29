#!/usr/bin/env bash
# The Kaggle CLI nests single-file downloads under their full dataset path, so files land at
# data/starter/starter_kit/<dir>/starter_kit/<dir>/<file>. Move each to data/starter/starter_kit/<dir>/<file>.
set -euo pipefail
cd /mnt/c/Users/dell/Work/vqcc/data/starter
find starter_kit -type f | while read -r f; do
  rel="starter_kit/${f##*/starter_kit/}"
  if [ "$f" != "$rel" ]; then
    mkdir -p "$(dirname "$rel")"
    mv "$f" "$rel"
  fi
done
find starter_kit -depth -type d -empty -delete
find starter_kit -type f | sort
