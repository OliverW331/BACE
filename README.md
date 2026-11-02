# BACE main experiment and results

This repository contains the frozen BACE main experiment and its saved,
descriptive results. Follow-up studies, manuscript preparation, writing skills,
the review prototype and previous-stage archives are not part of the tracked
repository. Their existing local files are preserved.

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

The saved snapshot records 1,800 planned cases, 1,798 BACE-complete cases and two
failures. The execution record remains `incomplete`; the paired analysis does
not silently treat the two missing cases as zero scores. See the linked status
and snapshot manifests for the underlying records.

## Working boundaries

- Follow [project instructions](AGENTS.md) and any more-specific `AGENTS.md`.
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
