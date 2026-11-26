# Repository scope

## Included

- The BACE implementation, tests, dependency locks and the frozen protocol, configurations, prompt templates and response schemas under `BACE/`.
- Framework definitions under `docs/`.
- The planned-case manifest and execution status of the main run under `BACE/results/main_v1/`.
- The company sampling record, `BACE/evidence/sample/sample.json`.
- Analysis code: notebooks 00–03, the article's figure code (`BACE/analysis/figures_v3/`), additional analyses (`BACE/analysis/revision_2026-11/`) and the derived-data exporter.
- The main-run snapshot under `BACE/analysis/outputs/snapshot/`. It contains:
  - per-disclosure metrics;
  - BACE claim labels;
  - comparator claim verdicts;
  - sample and source-coverage tables;
  - consumed-source hashes and a table-hash manifest.
- HTML reading copies of notebooks 00–03.
- The derived-data release under `BACE/analysis/outputs/release_v1/`.

The snapshot contains all 1,800 planned cases in its metrics table and records 1,798 BACE-complete cases. Paired comparisons use the 1,798 cases completed by all evaluators, and missing outcomes are not converted to zero scores.

## Not included

- Source reports and ESG indicator data from the Corporate Sustainability Tracker, and material derived from them:
  - evidence-card text;
  - prepared evidence packages;
  - filled generation prompts;
  - source quotes used for grounding;
  - case bundles.
- Raw per-case model-call records, which are available from the corresponding author on reasonable request.
- Credentials, environments, caches and logs.
- Human-review workbooks.

## Reproduction

A clone can be used to inspect the released results and the code. Rerunning the pipeline, rebuilding the snapshot or re-executing the notebooks also needs:
- the source data;
- the prepared evidence;
- the per-case outputs;
- the recorded environments.

The snapshot loader checks consumed-source hashes before reusing cached tables.

Source-only tests run on a fresh checkout. Two native replay tests also need saved pilot-case outputs under `BACE/results/pilot_v1/`, which are not tracked.
