---
name: citation-audit
description: "Audit BACE manuscript citations occurrence by occurrence for existence, metadata and full-text support, producing a traceable audit ledger."
metadata:
  upstream-commit: "2132036060e03e8d0df69a4b21e5971819c0c2d6"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Citation Audit

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/skills-codex/citation-audit/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Citation audit

Inventory the manuscript and bibliography files in scope and hash them. Extract
all actual citation keys and surrounding assertions with file/line locations,
including supported citation macros and Markdown references. Report the parser
scope and unresolved syntax instead of claiming coverage of unseen citations.
Compare cited keys with bibliography entries; report uncited entries separately
when requested. Never delete uncited entries merely because they are uncited.

For every cited occurrence, verify three distinct layers: existence, metadata,
and support in the relevant original full text. An identifier lookup verifies
only the first layer. Record source versions, locators, retrieval dates and
qualifications. Repeated uses of one source can have different support verdicts.

Save `CITATION_AUDIT.md` and `CITATION_AUDIT.json` under the requested paper audit
directory. Include input hashes, actual coverage counts, per-occurrence verdict,
evidence locations, recommended correction and unresolved access. Use `PASS`,
`WARN`, `FAIL`, `BLOCKED` or `ERROR` with explanations. Inaccessible full text
blocks semantic verification; a network error does not prove a nonexistent paper.

Record actual review independence (`single-context`, `separate-context` or a
verified alternative) and keep semantic acceptance `provisional` until the
author/reviewer verifies it. Never infer scientific acceptance from model-family
differences or claim a fresh reviewer without one. A focused partial-draft audit
is allowed if coverage is clearly bounded. Do not auto-edit the bibliography in
an audit-only request; a requested soft-only audit preserves it and proposes
manuscript wording changes.

This adapter preserves the upstream three-layer audit but replaces ARIS shared
files, fixed reviewer model, per-entry spawned agents and HTML review gates with
available Codex tools and an honest scope/independence record. No ARIS workflow,
external model backend or automatic rendering dependency was installed.
