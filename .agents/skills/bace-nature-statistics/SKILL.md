---
name: bace-nature-statistics
description: "Audit BACE manuscript statistical reporting, units, replication, effect estimates and figure uncertainty against saved analyses and Nature Sustainability guidance."
metadata:
  upstream-commit: "84880815fb37317b3766bff2c2abba395b8993c3"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Bace Nature Statistics

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/Yuan1z0825/nature-skills/blob/84880815fb37317b3766bff2c2abba395b8993c3/skills/nature-statistics/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Statistical reporting audit

Identify what was measured, the analysis unit and the inference asserted. Separate
company, company-year, case and claim counts; repeated measurements do not create
independent replication. Extract pairing, clustering, exclusions, missingness,
randomization/blinding status and exploratory versus confirmatory intent from
the real protocol and executed analyses.

Map each reported result to its saved output, test/model, effect estimate,
uncertainty definition, sample size and correction family. Verify the numbers
rather than beautifying statistics copied from prose. Preserve macro/micro
aggregation and conditional human-validation scope. Unknown methods or values
remain `AUTHOR_INPUT_NEEDED`.

For figures and tables, define centre values, error bars, interval levels,
resampling unit and denominators, and identify applicable tests and P values.
Do not manufacture a hypothesis test for a descriptive panel. Distinguish SD,
SE, confidence intervals and model-run variability. Check repeated values and
rounding across text, displays and supplements.

Return scope, major reporting issues with evidence pointers, conservative revised
text and unresolved facts. Do not turn association into causation or non-significance
into equivalence. New computation needs the data and a requested calculation;
the statistical-analysis adapter covers that workflow. This reporting skill has
no numerical runtime dependency or automatic reanalysis step.
