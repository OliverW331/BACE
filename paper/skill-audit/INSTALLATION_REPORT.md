# BACE Codex skills installation audit

Date: **29 September 2026**. Target: **Nature Sustainability, Article**.

Twelve project-specific English adapters were installed and passed discovery,
structure and bounded instruction-invocation checks under
`/home/muwang/master_thesis/.agents/skills/`. They are deliberately reviewed
subsets of the pinned upstream skills, not unmodified full-repository installs.
The source review, omitted functionality and dependency boundaries are recorded
in [SOURCE_REVIEW.md](SOURCE_REVIEW.md).

## Installed skills and sources

All names below are both directory names beneath the installation root and
explicit invocation names when prefixed with `$`.

| Installed name(s) | Verified upstream source | Pinned commit |
|---|---|---|
| `citation-verification` | [ruichenrui/citation-verification](https://github.com/ruichenrui/citation-verification) | `61f42ae438afa93fcb3eeb1302f5f4ef7f59e32f` |
| `citation-management`, `scientific-critical-thinking`, `statistical-analysis` | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | `065b734670d7d990627dbc06a05b5a99be33f1f1` |
| `paper-writing` (upstream `paper_writing`) | [sayonari/claude-paper-writing-skills](https://github.com/sayonari/claude-paper-writing-skills) | `dc3044cddbc76d4e828a3368edc7d99252c67151` |
| `citation-audit` (from `skills/skills-codex/citation-audit`) | [wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | `2132036060e03e8d0df69a4b21e5971819c0c2d6` |
| `bace-nature-writing`, `bace-nature-polishing`, `bace-nature-reviewer`, `bace-nature-response`, `bace-nature-data`, `bace-nature-statistics` | [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | `84880815fb37317b3766bff2c2abba395b8993c3` |

Exact source paths, dates, licences, inventories and file hashes are in
[manifest.json](manifest.json). Each installed adapter has `PROVENANCE.json` and
the upstream licence. Existing global Nature skills were preserved; the project
prefix prevents ambiguous replacement. No manuscript sections or BACE code were
rewritten by this installation.

## Invocation

Use the skills in the BACE project, for example:

```text
Use $citation-verification to verify each claim's original supporting passage.
Use $citation-management to prepare and check the reference metadata.
Use $scientific-critical-thinking to audit the evidence for the proposed conclusion.
Use $statistical-analysis to plan the paired, company-aware analysis.
Use $paper-writing to draft the Methods from saved results and the frozen protocol.
Use $citation-audit to audit citation occurrences without changing the bibliography.
Use $bace-nature-writing to prepare the Nature Sustainability submission materials.
Use $bace-nature-polishing to tighten this paragraph while preserving its evidence boundary.
Use $bace-nature-reviewer for an internal pre-submission critique.
Use $bace-nature-response to map the reviewer comments to verified manuscript changes.
Use $bace-nature-data to draft the Data and Code availability statements.
Use $bace-nature-statistics to audit the Methods and figure-statistics reporting.
```

The official [Codex customization documentation](https://learn.chatgpt.com/docs/customization/overview#skills),
fetched on the review date, identifies `.agents/skills` as the repository skill
location and supports explicit and implicit invocation. Automatic selection is
enabled. The installed skills are available on the next user turn; the current
turn's initial skill catalogue need not refresh in place. Desktop picker clicks
were not exercised by this audit.

## Verification evidence

| Check | Observed result | Evidence |
|---|---|---|
| Source retrieval and staging | All five pinned sources retrieved; selected skills staged and hash-compared; repository installers/hooks not run | Source inventory in `manifest.json`, `*-install.log` |
| Codex schema validation | 12/12 entrypoints passed the system skill-creator validator | `static-validation.json` |
| Active local references | No broken active SKILL.md links | `link-validation.json` |
| Actual runtime discovery | Codex CLI 0.153.4 app-server `skills/list`, `forceReload=true`: 12 project skills, all `scope=repo`, all enabled, no errors | `codex-discovery.json` |
| Retained executable helpers | All three CLI entrypoints returned working `--help`; shared parser imported successfully | `cli-smoke.json` |
| Regression checks | 12 tests passed, including false HTTP success, partial DOI batch, wrong DOI, lossy BibTeX, missing response, stale quote and cyclic include | `helper-tests.txt`, `test_helpers.py` |
| Live network smoke | Public DOI `10.1038/s41586-021-03819-2` yielded a matching record; formatting completed | `live-doi-test.json`, `live-doi-output.bib`, `live-doi-formatted.bib` |
| Independent instruction invocation | All 12 entrypoints explicitly read/applied in six synthetic paired workflows; no blocking findings or mandatory missing tools | `behavioral-invocation.md` |
| Dependency compatibility | Independent Python 3.13.14 environment; `pip check` passed | `requirements.lock.txt`, `dependency-check.txt` |
| Frozen-state preservation | 698 protected entries compared before/after; no changes | `protected-comparison.json` and before/after hash maps |

The live DOI is a tool test, not a proposed BACE citation. Metadata retrieval,
skill discovery, fixture behavior and mechanical tests do not certify manuscript
citations, statistical conclusions or journal acceptance. The independent test
uses synthetic inputs and is not independent scientific peer review.

## Environment and reproducibility

Writing-tool Python:
`/home/muwang/.local/share/bace-writing-skills/venv/bin/python`.
Only requests, PyYAML and their resolved dependencies were added. Both
`BACE/.venv` and `BACE/analysis/.venv` and their dependency locks were preserved.
The check was a read-only hash comparison, not a rerun of acceptance or experiments.

Re-run local helper checks from the project root:

```bash
/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/skill-audit/test_helpers.py
/home/muwang/.local/share/bace-writing-skills/venv/bin/python -m pip check
```

The exact dependency set is in `requirements.lock.txt`; reinstall only into a
new/separate venv. Upstream source archives, original extracted trees and raw
official-page HTML remain in `/home/muwang/.cache/bace-skills-2026-09-29/`.
The installed adapter source and provenance should be retained together; an
upstream update is a new review, not an automatic overwrite.

## Writing and journal rules

The project [AGENTS.md](../../AGENTS.md) and
[WRITING_RULES.md](../WRITING_RULES.md) require original-source citation checks,
number-to-calculation traceability, conclusions bounded by evidence and explicit
missing information. They also preserve BACE's supplied-evidence boundary,
analysis units, planned/completed sample distinction and human-validation scope.

The [official journal profile](../NATURE_SUSTAINABILITY_GUIDELINES.md) records
the current Article limits, submission stages, availability requirements and AI
policy. Ten official pages were retrieved, with URLs, dates and hashes in
`official-sources.json` and readable snapshots in `official-text/`. Initial
submission flexibility is distinguished from acceptance-stage formatting.

## Unresolved or deliberately excluded functionality

- The upstream statistical auto-diagnostic helper was withheld after concrete
  correctness concerns; the statistical skill is an instruction workflow.
  Optional numerical/Bayesian packages were not installed or claimed tested.
- Scholar scraping, unneeded provider-specific extraction scripts, the ARIS
  autonomous/reviewer infrastructure, remote image generation, R and local TeX
  were not installed. The adapters do not require these missing components.
- Full-text access and actual source support remain to be verified when auditing
  real paper citations. No BACE-wide citation or numerical audit was performed.
- The formatter supports a restricted BibTeX subset; the revision checker has
  explicit macro/rendering limits. See `SOURCE_REVIEW.md` before broader use.
- Two nonblocking instruction-scope frictions were observed: citation-audit's
  default two-file output and writing skills' default project-context reading.
  Explicit task output/evidence boundaries took precedence in the fixture tests.
- Source author identity/commit signatures and complete transitive package code
  were not independently certified. Package versions and source hashes are recorded.
- A journal page-specific revision date was not established. Recheck the official
  sources and any editor-specific instructions at submission. Author declarations,
  repository deposits, data rights and completed validation remain project work.
