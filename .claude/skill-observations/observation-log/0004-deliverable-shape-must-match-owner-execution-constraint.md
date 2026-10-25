---
id: 4
title: "Deliverable shape must match how the owner can execute it (one bot, one platform, per-asset rules)"
status: open
type: internal
skill: []
proposes_skill: []
target_file: ["CLAUDE.md"]
siblings_checked: "none — target is a project instruction file, no skill family"
area: "scoping a 'find profitable strategies' request in quant_lab"
date: 2026-10-24
session_context: "Owner asked for strategies that beat the S&P 500 using both labs. H072 answered with a multi-sleeve portfolio (index + trend overlay + crypto sleeve). Owner corrected: wanted profitable rules PER ASSET that one bot can trade on one platform; a portfolio cannot be wired from a phone. Follow-up became H073 (per-asset book on Bitget perps)."
parked_until:
resolved:
resolution:
reference:
commands_verified: none
---

**Issue:** The request said "find strategies"; the repo already showed the execution path (one bot per
system, Bitget perps, phone + GitHub Actions, decisions/watch/venues.md). The first study still produced a
portfolio-construction answer that the owner cannot execute. The constraint was readable from the repo but
was not turned into a scoping rule before the study design.

**Suggested improvement:** add to CLAUDE.md under "quant_lab rules": "A strategy deliverable is one rule per
asset that one bot can trade on one platform (Bitget USDT-M perps unless the owner says otherwise). A
multi-asset portfolio is only a secondary answer and must be labelled as such."

**Principle:** before designing a study, write down how the result will be executed; a result the owner
cannot run is not an answer, however rigorous.
