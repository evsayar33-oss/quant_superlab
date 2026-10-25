---
id: 1
title: "Coverage answers must check named strategy families against the rule catalog, not only list what exists"
status: open
type: open-source
skill: []
proposes_skill: []
target_file: ["CLAUDE.md"]
siblings_checked: "none — target is a project instruction file, no skill family"
area: "answering 'was everything tested?' questions"
date: 2026-10-18
session_context: "quant_lab: user asked if all trading styles were tested; the answer listed the catalog and some untested data sources but missed the whole SMC/ICT family (and divergence, pivots). User found it later from a social post and was upset."
parked_until:
resolved:
resolution:
reference:
commands_verified: none
---

**Issue:** Asked whether every trading style had been tested, the agent listed what the catalog contains plus untested data-dependent ideas, but never checked the catalog against a list of popular retail strategy families (SMC/ICT, divergence, pivots, Fibonacci, Wyckoff, harmonics, grid/DCA). The gap read as "everything tested".

**Suggested improvement:** Add to CLAUDE.md: a coverage answer must compare the catalog with an explicit external checklist of strategy families and name every family that is missing, before saying the search is complete.

**Principle:** "What did we test?" is answered from the inventory; "did we miss anything?" needs an outside checklist — an inventory cannot show its own gaps.
