# BACE main experiment and results

BACE expands to **Bidirectional Atomic Claim Evaluation**. The author-confirmed
terminology correction is dated 2 November 2026; it changes the name, not the
frozen methods or saved results.

This repository contains the frozen BACE main experiment and its saved,
descriptive results. Follow-up studies, manuscript preparation, AI-agent
instructions and skills, the review prototype and previous-stage archives are
not part of the tracked repository. Their existing local files are preserved.

## Repository map

| Directory | Purpose | Entry point |
| --- | --- | --- |
| `BACE/` | Main implementation, frozen configuration, prompts, schemas and tests | [Experiment README](BACE/README.md) |
| `BACE/evidence/sample/` | Original main sampling record, without evidence payloads | [Sample record](BACE/evidence/sample/sample.json) |
| `BACE/results/main_v1/` | Saved planned-case manifest and execution-status record | [Execution status](BACE/results/main_v1/execution_status.json) |
| `BACE/analysis/` | Main notebooks 00–03, analysis helpers and validation exporters | [Analysis README](BACE/analysis/README.md) |
| `BACE/analysis/outputs/` | Saved source tables, provenance, HTML reading copies, figures and selected examples | [Snapshot manifest](BACE/analysis/outputs/snapshot/manifest.json) |
| `paper/reports/main_experiment_2026-11-02/` | Main-experiment workflow/result report, numerical ledger and rendering sources | [Report README](paper/reports/main_experiment_2026-11-02/README.md) |
| `docs/` | Framework definitions and repository scope | [Method definition](docs/generation_evaluation.md) |

## Read the main results

- [Main-experiment report](paper/reports/main_experiment_2026-11-02/BACE_main_experiment_report.pdf).
- [Data landscape](BACE/analysis/outputs/00_data_landscape.html).
- [Evidence support](BACE/analysis/outputs/01_evidence_support.html).
- [Failure patterns](BACE/analysis/outputs/02_failure_patterns.html).
- [Native evaluator comparison](BACE/analysis/outputs/03_evaluator_comparison.html).

Result status checked on 2 November 2026: the saved snapshot records 1,800
planned cases. Generation, RAGChecker and RAGAS are complete for all 1,800;
BACE is complete for 1,798, with two failures. The execution record remains
`incomplete`; paired comparisons use the 1,798 common completed cases and do
not treat missing BACE outcomes as zero scores. See the linked status and
snapshot manifests for the underlying records.

Readiness records describe preparation and pilot acceptance, not main-run
completion. The frozen protocol's statement that the next main invocation
starts from scratch describes an earlier scheduling revision, not the current
saved run. The separate main-experiment report does not change the execution
record or establish completed human validation.

## Working boundaries

- Do not alter frozen protocols, prompts, model settings, environments or saved
  experiment outputs during writing or repository maintenance.
- Treat support as conditional on the supplied evidence, not external truth,
  legal compliance or independently established evaluator accuracy.
- Prepared reviewer packets do not establish completed human validation.
- Trace reported numbers and citations to their saved calculation or original
  supporting passage; preserve missingness and explicit verification limits.

## Local data and reproducibility

Git tracks main-experiment source code and protocol records, the saved result
snapshot, derived tables, source hashes, figure exports and the main report.
Credentials, original source datasets, full per-case model-call histories,
frozen evidence/input payloads, private reviewer workbooks and temporary
previews remain local. No separate study results enter the main snapshot.

A fresh clone is therefore **not a complete experimental data backup**. Analysis,
native-case inspection and citation rechecking may require separately restored
local artifacts. See [repository scope and artifact policy](docs/REPOSITORY.md)
before staging files or preparing a shareable copy.

Use the experiment and analysis READMEs for environment prerequisites and commands.
Repository maintenance must not start new experiments or install dependencies
into either frozen BACE environment.
