# BACE research workspace

BACE studies claim support within supplied evidence for generated sustainability
disclosures. This repository separates the experiment implementation, descriptive
analysis, manuscript preparation and exploratory review interface.

## Repository map

| Directory | Purpose | Entry point |
| --- | --- | --- |
| `BACE/` | Main experiment implementation, configurations and frozen protocol records | [Experiment README](BACE/README.md) |
| `BACE/analysis/` | Descriptive notebooks, analysis helpers and validation exporters | [Analysis README](BACE/analysis/README.md) |
| `BACE/experiments/` | Separate evidence-chain and prompt-sensitivity studies | Each study's README and protocol |
| `paper/` | Manuscript sources, figures, numerical provenance and citation ledgers | [Paper README](paper/README.md) |
| `docs/design/` | Evidence Explorer product baseline and design decisions | [Product baseline](docs/design/bace_product_baseline.md) |
| `prototypes/bace-explorer/` | Local evidence-review UI with illustrative fixtures and a read-only native-case adapter | [Prototype README](prototypes/bace-explorer/README.md) |
| `.agents/skills/` | Project-scoped research and writing adapters | [Skill installation audit](paper/skill-audit/INSTALLATION_REPORT.md) |
| `_archive/` | Previous-stage source snapshot; not the active workflow | [Archive README](_archive/previous_stage_20260921/README.md) |

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

Git tracks source code, protocols, manuscript sources, selected figure exports,
derived analysis tables and provenance records. Credentials, source datasets,
main-run outputs, private reviewer workbooks, large copied experiment inputs,
downloaded literature full texts and temporary previews remain local.

A fresh clone is therefore **not a complete experimental data backup**. Analysis,
native-case inspection and citation rechecking may require separately restored
local artifacts. See [repository maintenance and artifact policy](docs/REPOSITORY.md)
before staging files or preparing a shareable copy.

Use each component's README for environment prerequisites and supported commands.
Repository maintenance must not start new experiments or install dependencies
into either frozen BACE environment.
