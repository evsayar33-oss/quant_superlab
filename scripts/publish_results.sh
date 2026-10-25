#!/usr/bin/env bash
# Publish ./results to the `results` branch as ONE fresh commit (force push).
# Old versions are not kept in git history -> the repository never grows with charts/CSVs.
set -euo pipefail
: "${GITHUB_TOKEN:?}" "${GITHUB_REPOSITORY:?}"
rm -rf _pub && mkdir -p _pub/results
cp -r results/. _pub/results/
cat > _pub/README.md <<'MD'
# quant_lab results

Reports, charts, OOS return series and scan leaderboards. This branch is overwritten on every
publish (single commit) so the repository does not grow. Decisions live on `main` in `decisions/`.

- `results/H*.md` — validation reports (open them here on GitHub)
- `results/scan_*.md` — discovery scan leaderboards, `*_variants.csv` = every variant's result
- `results/charts/` — equity, drawdown, monthly, holding-time and stop/target charts
MD
cd _pub
git init -q -b results
git config user.name "quant-lab-bot"
git config user.email "actions@users.noreply.github.com"
git add -A
git commit -q -m "results $(date -u +%F_%H%M)"
git push -q -f "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" results
cd .. && rm -rf _pub
echo "[results] published"
