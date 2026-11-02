# Repository maintenance and artifact policy

Policy introduced: 2 November 2026.

## Organization

Keep the existing directory boundaries. Experiment entrypoints live under `BACE/`,
analysis tooling under `BACE/analysis/`, writing and numerical provenance under
`paper/`, and the review prototype under `prototypes/bace-explorer/`.
Do not relocate saved research artifacts merely to make the tree smaller:
manifests, source ledgers and verification scripts may depend on their paths.

## Version-controlled material

- Implementation code, tests, dependency specifications and existing locks.
- Existing experiment protocols, prompts, plans, freeze records and selection
  ledgers, without editing their contents.
- Project instructions, design decisions and audited writing adapters.
- Manuscript sources, bibliography, selected figure exports and source tables.
- Derived calculation results, cohorts, denominators, source hashes, citation
  occurrence ledgers, access records and explicit verification limitations.
- Validation guides and exporter code, without coordinator or reviewer payloads.

Tracking a plan, freeze record or result ledger does not mean every referenced
input or output is included in Git, and does not establish a completed study.

## Material that stays local

| Material | Paths or patterns | Reason |
| --- | --- | --- |
| Credentials | `.env`, `.env.*`, `*.key`, `*.pem` | Do not include service secrets in commits |
| Frozen environments and caches | `.venv/`, Python caches, `node_modules/` | Preserve local environments; dependency specifications are tracked separately |
| Source data and main experiment outputs | `data/`, `BACE/evidence/`, `BACE/results/`, existing runtime-output patterns | Large research inputs and outputs need a separate backup and access policy |
| Reviewer workbooks | `BACE/analysis/validation/*.xlsx` | Preserve independent review and keep annotation payloads out of Git |
| Coordinator records | `BACE/analysis/validation/_private/`, except its README | Includes private sample mappings, automatic answers and archived workbooks |
| Copied prompt-sensitivity inputs | `paper/analysis/prompt_sensitivity/v1/inputs/` | Large per-case copies; keep the frozen manifests and source hashes in Git |
| Literature source copies | `paper/literature/sources/*/*`, except `retrieval.json` | Downloaded full texts are not automatically cleared for redistribution |
| Raw literature search responses | `paper/literature/searches/` | Retain search logs and audit records; raw downloaded pages remain local |
| Complete exploratory review packets | `paper/analysis/residual_gap_review_2026-10-20/packets/` | Source payload copies remain local; review ledgers and bounded reports remain tracked |
| Generated reading and QA products | Manuscript PDF/ZIP, page-preview directories, report build/review directories, selected screenshot patterns | Rebuild from source where the required local inputs and tools are available |

The ignore rules do not delete these files or replace a backup. Selected
manuscript figure PDFs/SVGs/PNGs and JSON QA records remain version-controlled;
there is no blanket exclusion of all PDF, image, JSON or CSV files.

## Fresh-clone limitations

Restore authorized source data and saved run outputs before executing analysis
or using the native-case adapter. Restore the correct original literature
versions before running full-text citation checks. Compare restored files with
the recorded hashes and locators; missing files remain missing until restored.
Use the existing independent environments where available, or an explicitly
separate environment under the project's environment policy.

Do not infer human-validation completion from the presence of a guide, exporter,
report or prepared workbook. Keep original reviewer ratings, adjudication and
automated outputs separate.

## Before committing

```bash
git status --short
git diff --stat
git diff --cached --stat
git diff --cached --check
git ls-files --cached
```

Review the staged paths for credentials, private reviewer material, native
prototype data, copied inputs and accidental build products. Run relevant
offline tests using installed dependencies; do not launch live model calls,
overwrite experiment outputs or install into frozen environments as a cleanup
step. Inspect the staged snapshot before committing. Push only when explicitly
requested; a local commit does not publish or back up ignored files.
