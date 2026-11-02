# Main-experiment repository scope

Scope narrowed at the author's request on 2 November 2026.

## Included in the current Git tree

- Main-experiment implementation, tests, existing dependency locks and frozen
  protocol/configuration/prompt/schema records under `BACE/`.
- Framework definitions under `docs/` and repository-scope documentation.
- Main-run planned-case and execution records under `BACE/results/main_v1/`.
- The original main sampling record, `BACE/evidence/sample/sample.json`.
- Main notebooks 00–03, their analysis helpers and validation exporter code.
- The existing main-run snapshot under `BACE/analysis/outputs/snapshot/`, including
  per-case metrics, BACE claims, native comparator claims, source inventories,
  completion records, consumed-source hashes and the table-hash manifest.
- Existing main-analysis figures 00–03, plotted source tables, selected complete
  example bundles, HTML reading copies and QA/verification records.
- The main-only workflow/result report under
  `paper/reports/main_experiment_2026-11-02/`, with its PDF, editable sources,
  numerical ledger, result tables, source provenance and figures.

The saved snapshot contains all 1,800 planned cases in its metrics table and
records 1,798 BACE-complete cases. The saved main execution status remains
`incomplete`. Completed-case paired comparisons and the full planned inventory
are not interchangeable; missing outcomes must remain missing.

## Excluded from tracking, preserved locally

- AI-agent instruction files and skills: `AGENTS.md`, `SKILL.md`, `.agents/`,
  `.codex/` and `skills/`, including nested copies. Scientific method documents,
  experiment prompts and result documentation remain in scope.
- Manuscript drafts, bibliography/literature maintenance, writing
  analyses, other paper reports and skill audits.
- `prototypes/`, product-design documents, previous-stage `_archive/` material
  and historical framework-development notes.
- `BACE/experiments/`, analysis notebook 04 and all evaluator-gap, evidence-chain
  and prompt-sensitivity follow-up-study tooling and outputs.
- Source datasets, canonical evidence payloads, frozen per-case input payloads,
  pilot/runtime/follow-up output directories and raw main-case call histories.
- Credentials, private coordinator records, reviewer XLSX files, environments,
  caches, logs and temporary review screenshots.

Untracking a file removes it from the current Git tree, not from the local disk.
This scope change does not rewrite existing Git history. Older commits may
still contain earlier-stage, writing or prototype files.

## Result inspection and reproduction

Use the root README's result links to inspect the committed main report,
notebooks, reading copies and tables. Existing saved result files are tracked
without regenerating or changing their contents.

A clone is not a complete raw experiment backup. Full reproduction, native
case inspection and source re-verification require separately restored inputs,
raw outputs and the recorded environments. The snapshot loader checks consumed
source hashes before cache reuse; the presence of a cached table alone does
not disable that verification. Compare restored artifacts with the recorded
hashes and never invent missing files or silently turn missing outcomes into
zero scores.

Two existing native replay tests require separately restored saved pilot-case
artifacts under `BACE/results/pilot_v1/`. Those test-data prerequisites remain
local rather than broadening the tracked main-result scope. Source-only tests
can run against an isolated checkout; the complete existing suite also requires
the local replay artifacts.

Support scores are conditional on supplied evidence, not external truth,
legal compliance or independently established evaluator accuracy. Main human
validation remains separate from prepared guides and exporter code.

## Maintenance

```bash
git status --short
git diff --stat
git diff --cached --stat
git ls-files
```

Use `git rm --cached` to remove tracked files without deleting local copies.
Review the resulting tracked-file inventory against this scope. Do not modify
frozen environments, dependencies, prompts or saved research artifacts, run
new experiments, regenerate results or publish the repository as a cleanup
step. Push only when the author requests it.
