---
id: 2
title: "Commit made before running the mandatory test suite (config-only pre-registration commit)"
status: open
type: internal
skill: []
proposes_skill: []
target_file: ["CLAUDE.md"]
siblings_checked: "none — target is a project instruction file, no skill family"
area: "pre-commit checks in quant_lab"
date: 2026-10-24
session_context: "quant_lab H072 synthesis study: the pre-registration commit (config/synthesis.yaml, registry, CHANGELOG) was made to timestamp the rules before results; tests/test_core.py was run only after the commit (all passed)."
parked_until:
resolved:
resolution:
reference:
commands_verified: "run: python tests/test_core.py after the commit — all ok"
---

**Issue:** CLAUDE.md says "Run `python tests/test_core.py` before every commit." The rule was in context
(loaded via CLAUDE.md), but a config-only commit felt exempt and was made first; the suite ran afterwards and
passed. Protection in play: written down and loaded, no checkpoint. Nothing enforces the order.

**Suggested improvement:** a structural barrier instead of a sentence: a repo `.githooks/pre-commit` (enabled
via `git config core.hooksPath .githooks` in the session-start hook) that runs `python tests/test_core.py`
and refuses the commit on failure. Config-only commits are not exempt by the rule as written.

**Principle:** a "before every commit" rule that relies on memory gets skipped exactly on the commits that
feel trivial; put the check in the commit path itself.
