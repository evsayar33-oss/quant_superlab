#!/usr/bin/env bash
# Copy the current content of the `results` branch into ./results (reports, OOS series, charts).
# Main branch keeps only small decision files; heavy outputs live on `results` (single commit).
set -u
rm -rf _res
if git clone -q --depth 1 -b results "https://github.com/${GITHUB_REPOSITORY}.git" _res 2>/dev/null; then
  mkdir -p results
  cp -r _res/results/. results/ 2>/dev/null || true
  echo "[results] fetched $(find results -type f | wc -l) files"
else
  echo "[results] no results branch yet"
fi
rm -rf _res
