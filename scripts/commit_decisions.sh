#!/usr/bin/env bash
# Commit decisions/ to main safely when other runs pushed in the meantime.
# Never rebases text files (history.csv would conflict): it re-applies this run's changes
# on top of the latest main and rebuilds the registry from all parts.
set -euo pipefail
MSG="${1:-Decisions $(date -u +%F)}"
git config user.name "quant-lab-bot"
git config user.email "actions@users.noreply.github.com"
rm -rf /tmp/dec && cp -r decisions /tmp/dec
for i in 1 2 3 4 5 6; do
  git fetch -q origin main
  git reset -q --hard origin/main
  mkdir -p decisions/parts decisions/live
  cp /tmp/dec/parts/*.json decisions/parts/ 2>/dev/null || true
  cp /tmp/dec/live/*.csv decisions/live/ 2>/dev/null || true
  [ -f /tmp/dec/live_status.json ] && cp /tmp/dec/live_status.json decisions/live_status.json
  if [ -f /tmp/dec/history.csv ]; then
    [ -f decisions/history.csv ] || head -n 1 /tmp/dec/history.csv > decisions/history.csv
    grep -Fxv -f decisions/history.csv /tmp/dec/history.csv >> decisions/history.csv || true
  fi
  python run.py --merge > /dev/null
  git add decisions
  git diff --cached --quiet && { echo "[decisions] nothing to commit"; exit 0; }
  git commit -q -m "$MSG"
  if git push -q origin HEAD:main; then echo "[decisions] pushed"; exit 0; fi
  sleep $((5 + RANDOM % 15))
done
echo "[decisions] push failed after retries"; exit 1
