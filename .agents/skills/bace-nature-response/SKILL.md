---
name: bace-nature-response
description: "Draft or audit BACE responses to editors and reviewers, mapping each claimed revision to completed evidence and the actual changed manuscript."
metadata:
  upstream-commit: "84880815fb37317b3766bff2c2abba395b8993c3"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Bace Nature Response

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/Yuan1z0825/nature-skills/blob/84880815fb37317b3766bff2c2abba395b8993c3/skills/nature-response/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Response workflow

Read the actual editor letter and reviewer comments. Extract decision type,
deadline, required files and visibility instructions rather than inferring them
from tone. A local edit can proceed when decision type is unknown; package-level
strategy needs the actual decision. Keep each comment's substantive severity
separate from the overall decision label.

Assign comment IDs and separate proposed, in-progress and completed actions.
Reply respectfully and specifically, with the rationale, executed change or
reasoned limitation, and a verified manuscript locator. Never say an experiment,
analysis or edit was completed until its artifact exists. Unknown line numbers,
additional results and author decisions remain explicit placeholders.

Keep the response complete while making manuscript changes as concise as the
reader needs. Preserve clean and marked sources when requested. Check every
quoted revision and claimed location after editing. Apply actual editorial
reviewer-visibility instructions; do not invent mutual blindness requirements.

For LaTeX packages, use the bundled `scripts/check_package_consistency.py` with
the independent writing-tools Python and `--help`. It checks supported quote
macros, comment/response counts and normalized clean/marked text. It reads static
input/include files but does not compile TeX, inspect figures, resolve every
macro or prove scientific correctness. A zero-finding result is mechanical only;
check supported-macro coverage and inspect the compiled document as applicable.
Do not use arbitrary untrusted TeX includes pointing outside the supplied packet.

Use the native Codex editor/compilation for standalone LaTeX documents when
available. No TeX runtime is installed by this skill. Initial-submission cover
letters belong to the writing adapter.
