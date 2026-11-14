#!/usr/bin/env bash
# Commit decisions/arena/*.json to main safely when other runs pushed in the meantime.
# Only small JSON files are committed (roster, switcher picks, state). Heavy outputs go elsewhere:
# the dashboard is deployed to GitHub Pages as an artifact, reports go to the `results` branch.
set -euo pipefail
MSG="${1:-Arena $(date -u +%F_%H%M)}"
SUB="${2:-}"          # optional: only this timeframe folder (parallel screen jobs must not overwrite each other)
git config user.name "quant-lab-bot"
git config user.email "actions@users.noreply.github.com"
SRC="decisions/arena${SUB:+/$SUB}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -r "$SRC"/. "$TMP"/
for i in 1 2 3 4 5 6; do
  git fetch -q origin main
  git reset -q --hard origin/main
  mkdir -p "$SRC"
  cp -r "$TMP"/. "$SRC"/
  git add "$SRC"
  git diff --cached --quiet && { echo "[arena] nothing to commit"; exit 0; }
  git commit -q -m "$MSG"
  if git push -q origin HEAD:main; then echo "[arena] pushed"; exit 0; fi
  sleep $((5 + RANDOM % 15))
done
echo "[arena] push failed after retries"; exit 1
