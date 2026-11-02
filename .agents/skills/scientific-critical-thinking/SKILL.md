---
name: scientific-critical-thinking
description: "Evaluate the design, validity, bias and evidence boundaries of BACE scientific claims; distinguish methodological concerns from presentation issues."
metadata:
  upstream-commit: "065b734670d7d990627dbc06a05b5a99be33f1f1"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Scientific Critical Thinking

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/065b734670d7d990627dbc06a05b5a99be33f1f1/skills/scientific-critical-thinking/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Evidence appraisal

Identify the exact claim and the study design before evaluating evidence. Keep
observations, inference and proposed implications separate. Assess sampling and
source availability, measurement validity, confounding, selective reporting,
dependence, missingness, uncertainty and plausible alternative explanations.

For BACE, check supplied-evidence boundaries, extraction and candidate-selection
errors, automated judge errors, native evaluator denominators and the scope of
human labels. A lower support score is not evidence of higher evaluator accuracy;
a supported statement is not independently verified real-world truth. Repeated
tasks and years within companies are not automatically independent observations.

Trace each concern to a supplied artifact and claim location. Use proportional
severity: identify whether it invalidates a central conclusion, narrows its
scope or only affects clarity. State strengths supported by evidence as well as
limitations. Distinguish confirmed error, plausible risk and not-assessable fact.
Apply the same standard regardless of whether the result supports the narrative.

Return the evaluated claim, evidence, warranted conclusion, concern and a
concrete resolution test. Apply clinical frameworks such as GRADE or Cochrane
risk-of-bias only when appropriate to the study; do not give BACE a medical
evidence grade by analogy. This skill has no runtime, diagram-service or model
dependency and does not prescribe new experiments without an author request.
