---
name: statistical-analysis
description: "Plan or interpret BACE statistical analyses with explicit estimands, paired cohorts, clustering, uncertainty and reproducible numerical provenance."
metadata:
  upstream-commit: "065b734670d7d990627dbc06a05b5a99be33f1f1"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Statistical Analysis

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/065b734670d7d990627dbc06a05b5a99be33f1f1/skills/statistical-analysis/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Design before calculation

State the estimand, outcome, comparison, independent unit, pairing, clustering,
missing-data rules and analysis status. Distinguish post-experiment exploratory
analyses from prespecified confirmatory tests. Use saved analysis outputs when
they answer the request; verify their inputs and denominator before quoting them.

For BACE, distinguish company, company-year, case and extracted claim. Preserve
matched cases for comparisons. Consider company dependence across tasks/years
and use justified cluster-aware inference where warranted. Native score
differences are not accuracy differences without suitable validation labels.
Report macro and micro results separately. Retain failed/missing cases visibly.

When computation is requested, first verify available data and the method's
assumptions. Compute in an independent environment, save scripts and outputs
under `paper/`, and record input hashes, versions, seeds, resampling unit,
effect estimate, interval method and any test statistic or correction. Never
silently re-run or change frozen evaluation. Do not select a method solely by
a Shapiro-Wilk cutoff; no diagnostic test proves independence or all assumptions.

Report effect sizes and uncertainty with sample sizes. Distinguish confidence,
credible and prediction intervals and SD versus SE. Non-significance does not
establish equivalence. Multiple testing, outlier handling and deviations from a
plan need explicit treatment. Do not use observed post-hoc power or bootstrap
sampling variability as a substitute for independent model-run variability.

Paired testing needs matched data or valid sufficient paired summaries. Two
separate confusion matrices cannot recover discordant pairs. Verified joint
discordant counts can support McNemar's test under its assumptions.

This is a validated instruction adapter. The upstream `assumption_checks.py`
and its numerical stack are deliberately not installed: review found misleading
automatic test recommendations, missing-value index drift and unguarded inputs.
Do not call that helper or claim numerical execution when only a plan was made.
Select and pin additional statistical dependencies in a separate environment
only when an actual calculation needs them; check the chosen API then.
