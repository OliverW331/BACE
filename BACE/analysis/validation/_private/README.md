# Coordinator-only human-validation records

Do not distribute this directory or the earlier exploratory workbook to either
reviewer. Share only each reviewer's own formal XLSX and `../README.md`.

## Deliverables and status

Two independent copies contain the same 600 unique DCs, identical factual
materials and blank human labels. Each file has one sheet, seven columns,
600 pairs of editable classification cells and exactly 600 sample rows, plus
the header. Every complete candidate set occupies a single column-E cell.
Calibration and formal human annotation have not been conducted.

- `sample_manifest.json`: exact judgment inputs, private sample-group mapping,
  automated support and diagnosis outputs, unedited automatic rationales,
  per-stage call IDs, inclusion probabilities and annotation-row mapping.
- `export_qa.json`: consumed source hashes, experiment receipt checks, exporter
  hash, workbook hashes and complete read-back verification results.
- `layout_archive/`: exact pre-revision workbooks, row mappings and QA records.
  The current one-row layout replaces the earlier multirow layouts without
  changing any sampled input, automated label or sampling probability. Join
  returned ratings by Sample ID; row numbers differ between layout revisions.
- `qa_preview/`: selected layout examples, rendering checks and their source
  sample mapping. These are inspection artifacts, not reviewer packets.
- `../human_validation_600_with_main_results.xlsx`: coordinator reference with
  the same sample order and materials, with eight columns. F/G contain
  `BACE support label` and `BACE unsupported type`; H contains
  `Unedited automatic rationale`, copied verbatim from the original diagnosis
  output for all 380 unsupported samples. The 220 supported samples have no
  unsupported type or prose rationale: the support stage records support sets
  only. The blank rationale cells are intentional. These are original automated
  results, not human judgments. This file must not be given to
  independent reviewers before their annotations are preserved.
- `main_results_export_qa.json`: verification of the result reference against
  the original support/diagnosis output files and complete workbook read-back.

## Sampling design fixed for these packets

The frame contains 94,955 DCs from 1,798 completed BACE cases. Two incomplete
cases remain excluded and are listed in the manifest. The sampler does not use
the prior 500-row selection as its input or sampling frame. A new probability
sample can overlap that earlier selection by chance.

Seed: `bace-human-validation-v1-20260924`.

The 400-unit primary sample uses proportional allocation across the three
automated support strata. Integer quotas use largest remainders. Within each
stratum, units are ranked by SHA-256 of the seed, stage, case ID and DC ID and
selected without replacement.

| Automated support stratum | Population | Primary sample |
| --- | ---: | ---: |
| Supported, meaning direct support | 34,430 | 145 |
| Supported by inference | 17,879 | 75 |
| Unsupported | 42,646 | 180 |
| Total | 94,955 | 400 |

The 200-unit supplement is selected from automated unsupported DCs outside the
primary sample. Given the primary counts, allocate each supplementary slot to
the diagnosis currently represented least often in the combined sample, with
ties resolved in the frozen diagnosis order. Cap the combined contradiction
count at 40 so that at least two of its 42 population units remain available
for a separate calibration exercise. The primary sample is never changed to
meet this cap. Rank eligible remaining units uniformly by a separate seeded
SHA-256 ranking within each diagnosis.

| Automated diagnosis | Population | Primary | Supplement | Combined |
| --- | ---: | ---: | ---: | ---: |
| non_disclosure_statement | 6,378 | 30 | 38 | 68 |
| contradiction | 42 | 0 | 40 | 40 |
| evidence_conflation | 12,205 | 55 | 12 | 67 |
| factual_boundary_distortion | 19,130 | 71 | 0 | 71 |
| inferential_inflation | 3,193 | 17 | 50 | 67 |
| unsupported_novelty | 1,698 | 7 | 60 | 67 |
| Total | 42,646 | 180 | 200 | 380 |

These are automated sampling labels, not validated human categories. The 600
selected DCs span 512 cases, all 30 companies, all five target years and all
12 disclosure tasks. The primary sample itself covers all 30 companies.
All 600 are mixed using a third, independent seeded ranking; neither workbook
identifies the sample groups or automated labels.

## Input checks and interpretation

Every sampled support call input is bound to the successful recorded result,
its canonical input hash, source EC/DC inventories and candidate selection.
Company/year context is checked against the frozen generation inputs. All 380
available diagnosis inputs exactly match their paired support inputs. There
are 48 empty candidate sets: their BACE support outputs were deterministic,
without an LLM support call. Keep these units distinguishable in analysis.

The longest sampled evidence list contains 134 candidate ECs and 24,007 display
characters. Text, IDs, ordering and whitespace are preserved in one cell per
candidate set. Excel read-back checks compare each complete cell with its
source-derived content. Both reviewers have the same input hash. Long-cell
content may exceed Excel's maximum display height and must be read using the
expanded formula bar; it is not truncated in storage.

Use the 400 primary units for the primary overall estimate. Their inclusion
probability is the support-stratum sample size divided by its population;
analysis weights are its reciprocal. The manifest stores both exact fractions
and decimal values. Supplement probabilities are conditional on the realized
primary sample and equal each diagnosis's supplementary quota divided by its
remaining population. They are not unconditional inclusion probabilities for
the combined sample. Do not average all 600 outcomes to report overall accuracy.

Category analyses must disclose the oversampling and their denominators. A
human-unsupported / BACE-supported unit has no original automated diagnosis.
Report this as a support disagreement, without inventing a diagnostic outcome.
Original human ratings, adjudicated ratings and automated outputs must remain
distinct. The two reviewers do not double the independent sample size.

## Reproduction and preservation

The exporter is `../../scripts/build_human_validation.py`, using an independent
environment with `XlsxWriter==3.2.5` and `openpyxl==3.1.5`. The execution used:

```bash
/tmp/bace-validation-export-env/bin/python BACE/analysis/scripts/build_human_validation.py
```

The default command refuses to overwrite published files or their manifest.
Use a new version directory for a new study; preserve all returned reviewer
files. The `--refresh-layout` option only refreshes pristine workbooks whose
hashes still match export QA, and requires every complete input block and
automated result to remain identical. It archives the previous workbooks and
updates the row mappings when text is regrouped. It refuses to overwrite a
changed workbook.

The result-reference exporter is `../../scripts/export_validation_main_results.py`.
Its `--refresh` option verifies the existing file against its QA hash, preserves
all existing A-G values and archives the prior result workbook and QA before
replacement. The rationale update verifies all 380 texts against the original
diagnosis outputs and leaves reviewer A/B and the sample manifest unchanged:

```bash
/tmp/bace-validation-export-env/bin/python BACE/analysis/scripts/export_validation_main_results.py --refresh
```

Keep the existing 500-row exploratory workbook unchanged. It contains automatic
answers and is unsuitable for this blinded classification exercise.
