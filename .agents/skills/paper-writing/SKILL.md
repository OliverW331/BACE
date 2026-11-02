---
name: paper-writing
description: "Draft and revise BACE paper sections with original-source citations, result-to-number traceability and Nature Sustainability structure; adapted from paper_writing."
metadata:
  upstream-commit: "dc3044cddbc76d4e828a3368edc7d99252c67151"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Paper Writing

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/sayonari/claude-paper-writing-skills/blob/dc3044cddbc76d4e828a3368edc7d99252c67151/skills/paper_writing/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Project writing workflow

Use the existing `paper/` workspace, agreed blueprint, evidence map and research
foundation. Do not rebuild the project or create Claude-specific directories.
The target is Nature Sustainability, Article; the upstream speech-processing
venues and Elsevier templates do not govern this paper.

Before drafting, map the question to the findings, source artifacts and exact
evidence boundary. Build a paragraph-level argument at the scale requested.
Draft Results and Methods from verified artifacts, then Introduction and
Discussion; finalize the abstract and title from the completed argument. Follow
the existing author's sequence if already established.

Classify numbers as source-reported, computed-and-verified, computation-pending
or unverified. Keep calculation evidence, source locators and dependent claims
together. Verify individual cells in related-work comparison tables against
original sources. Unknown cells remain unknown, not inferred from a paper title.

Write precise English for a broad sustainability readership. Retain necessary
technical terms, define abbreviations, and replace vague performance claims with
the metric, comparison and boundary actually established. Do not strengthen
causality, generality or validation status during polishing.

When removing an unsupported value, update all dependent differences, rankings,
claims and repeated occurrences. Do not replace an uncomputed p value with
"beyond sampling variability" or a comparison to CI width. These upstream
fallbacks are not valid substitutes for statistical evidence. A failed search
does not by itself prove fabrication; keep the status unresolved.

Deliver the requested prose plus concise unresolved facts. Existing permission
for writing includes routine edits; do not add a confirmation gate after every
paragraph. Author identities, declarations, deposits and completed experiments
must come from verified information. Keep manuscript and citation audits linked
to actual source versions. For standalone LaTeX use the native Codex editor and
compile tool when available, not the upstream `compile.sh` cleanup workflow.

The upstream invocation `paper_writing` is normalized to `$paper-writing` for
Codex. No speech-style corpus, make-project command or LaTeX engine was installed.
