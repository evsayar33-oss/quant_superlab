---
id: 3
title: "Pinned workspace path in CLAUDE.md does not resolve in the cloud container"
status: open
type: internal
skill: [task-observer]
proposes_skill: []
target_file: ["CLAUDE.md"]
siblings_checked: "none — task-observer belongs to no family in this repo"
area: "Session Start Protocol, step 1 (storage probe and anchoring)"
date: 2026-10-24
session_context: "quant_lab H072 synthesis session in a cloud container: CLAUDE.md pins /home/claude/quant_lab/.claude, but the checkout lives at /home/user/quant_lab, so the probe of the pinned path failed and the log was found under the repo path instead."
parked_until:
resolved:
resolution:
reference:
commands_verified: "run: ls /home/claude/quant_lab/.claude -> No such file or directory; ls /home/user/quant_lab/.claude -> skill-observations, skills"
---

**Issue:** The pinned absolute path differs between environments (earlier sessions ran with the checkout at
/home/claude/..., this one at /home/user/...). The probe failed; the session fell back to the repo-relative
location, which is the one that actually persists (observations are committed to the repo).

**Suggested improvement:** pin the workspace as "<repo root>/.claude" (resolved with `git rev-parse
--show-toplevel`) instead of one absolute path, or list both known roots in CLAUDE.md with the rule
"first that exists".

**Principle:** when the log persists through the repository, anchor it on the repository root, not on one
machine's absolute path.
