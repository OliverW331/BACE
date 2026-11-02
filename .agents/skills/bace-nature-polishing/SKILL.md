---
name: bace-nature-polishing
description: "Polish or translate existing BACE academic prose into precise English while preserving claims, numbers, terminology and Nature Sustainability constraints."
metadata:
  upstream-commit: "84880815fb37317b3766bff2c2abba395b8993c3"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Bace Nature Polishing

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/Yuan1z0825/nature-skills/blob/84880815fb37317b3766bff2c2abba395b8993c3/skills/nature-polishing/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Evidence-preserving editing

Identify whether the task is language editing, compression or structural repair.
Preserve the author's meaning, study design, uncertainty, numerical values,
denominators, citations and evidence boundary. Check the underlying evidence
before changing a factual statement; never silently make an unsupported claim
more persuasive. Flag missing support without filling it in.

Repair paragraph logic before sentence ornament. Use concrete subjects and verbs,
define necessary terms, remove repetition and preserve qualifiers that limit the
claim. In Discussion, remove replay of Results and connect each implication to
specific findings. For compression, protect the minimum evidence chain and move
supporting detail only where its availability remains clear.

Return the requested edited prose and material factual questions. For local edits,
check affected repeated terminology, values and claims rather than restarting a
full manuscript audit. Apply the official Sustainability profile; do not enforce
flagship Nature or speech-journal style defaults. Typesetting work requires
rendering/compilation and visual inspection when requested, not prose-only checks.
