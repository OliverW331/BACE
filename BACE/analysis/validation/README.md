# Formal human validation

Guide updated: 2026-09-25. Layout: `one_sample_one_row_v3`.

This document specifies a single-sheet workbook for classification of BACE
claims using the same factual inputs as the corresponding automated support
and unsupported-diagnosis stages. Two formal reviewer workbooks have been
prepared, each containing the same 600 unique samples with blank human labels.
Preparing these files does not constitute calibration or human annotation.

## Start here

Open your assigned reviewer workbook. Each sample occupies exactly one row.
Read columns B-E, then use the dropdowns in F and G on that same row. Read the
whole candidate set in E before making a decision; expand the formula bar for
long cells. Only F and G are for human answers.

| Your decision in F | What to enter in G |
| --- | --- |
| `Supported` | Leave the cell empty |
| `Supported by inference` | Leave the cell empty |
| `Unsupported` | Select exactly one of the six types defined below |

Do not enter `N/A`, `Not applicable`, a rationale or a new label. If you change F
from `Unsupported` to either supported category, clear the previous value in G.

## Which file to use

| File | Sheet | Purpose |
| --- | --- | --- |
| `human_validation_600_reviewer_A.xlsx` | `Claim_review` | Reviewer A's independent annotations; F and G start blank |
| `human_validation_600_reviewer_B.xlsx` | `Claim_review` | Reviewer B's independent annotations; F and G start blank |
| `human_validation_600_with_main_results.xlsx` | `Main_results` | Coordinator reference with original BACE results in F/G and saved diagnostic rationales in H; not an annotation file |

Each reviewer receives only their assigned workbook and this README. The
coordinator keeps the result-reference file, `_private` directory and earlier
exploratory workbook. Reviewers must not consult automated answers or the other
reviewer's annotations during independent review.

## Worksheet layout and reading long cells

Each reviewer workbook has seven columns; the coordinator result reference has
eight, including the original rationale column. All three have one sheet and
exactly **601 worksheet rows: one header row and 600 sample rows**. Every Sample ID occurs once. A sample's
entire candidate EC set is in its one column-E cell, with blank lines between
EC entries inside the cell. There are no continuation rows or additional
material sheets.

Excel limits the visible height of a row, so the worksheet preview of a long
cell can end before its stored text ends. To read the full candidate set:

1. Select the sample's cell in column E.
2. Expand the formula bar above the worksheet using its expand arrow or by
   dragging its lower edge downward.
3. Scroll within the expanded formula bar to read the complete text without
   editing it, then return to F and G in the same sample row.

Do not infer that an EC or its text is missing merely because it is below the
visible part of the cell. The longest candidate cell contains 24,007 characters;
all 600 complete candidate sets fit within Excel's single-cell limit and have
been checked against the saved inputs.

EC IDs are identifiers from the case's EC inventory, not consecutive positions
within this particular candidate set. Gaps between IDs do not indicate missing
candidate entries. Use every EC actually listed in the cell; do not add others.

Use column-header filters to locate samples, and clear filters when checking
the full set of 600 rows. Keep Sample IDs and source materials unchanged. Source
cells A-E are protected against accidental edits; reviewer cells F and G are
editable. Sample IDs and sample order are unchanged from prior layouts, although
old physical row numbers may differ.

`unsupported_diagnosis_validation_500.xlsx` is an earlier exploratory export
with automated diagnoses and rationales. It is not the formal sample or a
blinded reviewer workbook.

## Scope

Reviewers make exactly two classifications:

1. `Human support label`: `Supported`, `Supported by inference`, or `Unsupported`.
2. `Human unsupported type`: one of the six diagnosis categories, only when the
   reviewer selects `Unsupported`.

There are no extraction, coverage, eligibility, confidence, rationale or
evidence-selection tasks. Reviewers do not rewrite claims or transcribe quotes.

This study assesses support and diagnosis decisions conditional on the supplied
DC and candidate ECs. It does not independently validate extraction quality,
candidate selection, source completeness, real-world truth, or the entire
generation/evaluation pipeline.

## The information actually supplied to BACE

The support and diagnosis scripts construct these factual inputs:

- `context_metadata.company_name`;
- `context_metadata.target_reporting_year`;
- `dc_claim`: one `dc_claim_id` and its `dc_text`;
- `ec_claims`: the selected candidate ECs, each with `ec_claim_id` and `ec_text`.

A DC is a claim extracted from the generated disclosure. An EC is a claim
extracted from evidence. At these two judgment stages, the evidence consists of
the candidate EC texts. It is not the original evidence-card text or the full
EC inventory.

For every one of the 600 sampled DCs, the saved support input has been checked
against receipt-verified source artifacts. Where a diagnosis exists, its saved
factual input has also been checked for exact equality with the support input.
All supplied material has passed full-cell read-back verification, including
exact equality between each complete candidate set and its single column-E cell.

The reviewer packet must preserve the exact selected EC membership, order,
identifiers and wording from the corresponding saved input. Use the saved
`dynamic_input` as the source of truth; check agreement between the support and
diagnosis inputs where both stages exist. Input differences must be resolved
before a row is represented as a comparison using identical inputs.

The stage-specific instructions differ: support assesses entailment, while
diagnosis assigns a failure category. Reviewers receive the corresponding
decision rules in this README. They do not receive the automated answers.

## Workbook columns

Each reviewer workbook contains only `Claim_review`, with these seven columns in order:

| Column | Header | Contents | Filled by |
| --- | --- | --- | --- |
| A | `Sample ID` | A neutral unique ID for joining the two reviewers' answers and the private experiment mapping | Coordinator |
| B | `Company name` | Exact company name from the judgment input | Coordinator |
| C | `Reporting year` | Exact target reporting year from the judgment input | Coordinator |
| D | `Target DC` | The supplied DC identifier and complete, unedited DC text | Coordinator |
| E | `Candidate ECs` | All and only the candidate EC identifiers and complete texts supplied for that DC, in the original order, together in one cell | Coordinator |
| F | `Human support label` | `Supported` / `Supported by inference` / `Unsupported` | Reviewer |
| G | `Human unsupported type` | One of the six labels below, only if F is `Unsupported`; otherwise blank | Reviewer |

`Sample ID` is an administrative identifier, not additional factual evidence.
Do not encode a diagnosis, support label or disclosure topic in it.

The following are not separate inputs to these BACE judgment stages and are
therefore omitted from the reviewer workbook: disclosure-topic metadata,
generated-disclosure quotations or full text, raw evidence cards, source PDF
pages, and ECs outside the selected candidate set. If a topic, source year or
other detail already occurs inside the DC or EC text, preserve it unchanged.
The private coordinator manifest can retain the omitted metadata and source
links for traceability.

Do not include automated support labels, support sets, diagnoses, rationales
or scores in reviewer files, including in hidden sheets, comments, formatting
or filenames. Reviewer A and Reviewer B receive separate copies with identical
sample IDs and factual materials, and blank classification cells.

### Coordinator result reference

`human_validation_600_with_main_results.xlsx` retains the same 600 samples,
order and complete input cells A-E. Columns F and G contain `BACE support label`
and `BACE unsupported type`. Column H, `Unedited automatic rationale`, copies
the original diagnosis-stage `rationale` verbatim for all 380 BACE-unsupported
samples. It explains the saved unsupported-type decision and is not a separate
support-stage rationale or a newly generated explanation.

The other 220 samples (145 `Supported` and 75 `Supported by inference`) have H
blank. The original support stage returns only support sets and their
direct/inferred types; it explicitly does not output prose rationales. These
blank cells therefore mean that no original prose rationale was recorded,
not that text was lost during export. The original support sets remain in the
private manifest. No explanations have been reconstructed or paraphrased.

The result reference has eight columns and no human input fields. Its entire
candidate set remains together in E on the sample's single row. Read long H
cells through the expanded formula bar in the same way as E. The two reviewer
files retain their seven-column layout and contain no automated rationales.

## How to annotate one row

1. Read the company and target reporting year, then the complete target DC.
2. Read every candidate EC in the same row's column-E cell, expanding the formula
   bar if necessary. Consider individual ECs and
   combinations of ECs when assessing the complete factual meaning of the DC.
3. Click column F in the same row and choose one of the three labels from its
   dropdown. Green cells are for this support decision.
4. If F is `Unsupported`, apply the ordered failure-type guide and choose one
   label from the dropdown in orange column G. Otherwise leave G empty.
5. Save your own workbook as you work. Continue independently without viewing
   or discussing the other reviewer's formal item-level decisions.

Company/year context can help interpret an explicit expression, but does not
itself establish a missing factual proposition. Do not use outside knowledge,
web searches, original source passages or unprovided ECs to fill gaps. Treat
ECs as the supplied factual basis; their extraction fidelity and real-world
truth are outside this task.

Classify the supplied DC as written, without silently correcting it or changing
its scope. A complete claim requires support for its material entity, time,
quantity, unit, scope, negation and degree of certainty.

## Support labels

| Label | Decision rule |
| --- | --- |
| `Supported` | At least one EC or combination of ECs explicitly entails the complete DC without a substantive reasoning step. Meaning-preserving paraphrase is allowed. This label means direct support in this three-category scheme. |
| `Supported by inference` | No direct support is available, but the complete DC follows from the ECs through a necessary reasoning step, such as a calculation or comparison, without adding or recharacterizing a substantive fact. |
| `Unsupported` | No individual EC or combination establishes the complete factual meaning of the DC. Partial support, relevance, similarity, plausibility or compatibility alone is insufficient. |

If both direct and inferred support are possible, select `Supported`. The
number of ECs used does not determine whether support is direct or inferred.
A historically supported statement does not automatically establish that the
same fact holds in the target reporting year.

These labels match the aggregation of BACE support sets: any accepted direct
set means `Supported`; accepted inferred sets without a direct set mean
`Supported by inference`; no accepted support set means `Unsupported`.
Humans do not have to enumerate or submit support sets.

A confirmed empty candidate set must be represented explicitly as
`No candidate ECs supplied`, rather than a cell that could be mistaken for a
missing export. In the BACE support stage, this case is assigned an empty
support-set result without calling the LLM. Retain this fact privately and
distinguish such deterministic decisions from LLM judgments in analysis.

There is no fourth support category. A missing or damaged packet is not an
empty candidate set and must not be forced into `Unsupported`. Leave the
affected item unanswered and notify the coordinator using its sample ID.
Preserve the unresolved status outside the reviewer sheet until the packet
or interpretation issue is resolved; do not invent an answer or silently
drop or replace the sample.

## Unsupported types

Only classify the type after making your own `Unsupported` judgment. Apply
these checks in order and select the first applicable category.

| Order | Label | Decision rule |
| --- | --- | --- |
| 1 | `non_disclosure_statement` | The central assertion is that a specified item was not disclosed, identified, quantified, described or otherwise provided within a stated reporting or evidence scope. Negative wording or absent support alone is insufficient. |
| 2 | `contradiction` | The ECs establish an incompatible proposition at the same material entity, time, scope and metric boundaries. A difference in boundaries alone is insufficient. |
| 3 | `evidence_conflation` | The DC constructs an unsupported connection, attribution or conclusion by combining elements supplied by two or more ECs. Using multiple ECs alone does not imply conflation. |
| 4 | `factual_boundary_distortion` | An anchored core fact is transferred to a different entity, organizational level, time, geography, population, activity, metric, unit or measurement boundary. |
| 5 | `inferential_inflation` | Material boundaries match, but the claim adds a stronger conclusion, characterization, status, certainty, causality or effectiveness than the ECs establish. |
| 6 | `unsupported_novelty` | No EC provides a recognizable evidential anchor for the core factual proposition. |

A non-disclosure assertion is not automatically unsupported: decide support
first. The first category applies only if that assertion was judged
unsupported. Absence of a supporting EC does not establish absence of the
information from the company's entire report.

A supported row has G blank. An unsupported row is complete only when G
contains one of the six categories. If a category remains unresolved after
consulting the guide, preserve the support answer, leave G unanswered and raise
the sample ID with the coordinator; do not add a new label or force a guess.

## Before returning your file

- Check all 600 samples after clearing filters. Each completed sample must have
  one allowed label in F.
- For every `Unsupported` in F, G must contain one of the six allowed types.
  For either supported label, G must be empty.
- Where an item remains unresolved, keep the undecided field blank and notify
  the coordinator of its Sample ID. Do not guess to make the sheet look complete.
- Keep all source text, Sample IDs, rows and column names unchanged. Do not add
  explanations, claims or extra sheets.
- Save and return your assigned A or B workbook. Keep the two reviewers' files
  separate; do not merge answers or overwrite the other reviewer's copy.

## Coordinator notes: preparation and analysis

- Conduct a separate calibration exercise, then fix the guide and sampling
  plan before formal annotation. The former source-review plan is superseded
  for this human study; the frozen experiment artifacts remain unchanged.
- Use a new sample covering automated supported and unsupported outcomes.
  Record the sampling frame, inclusion probabilities and any stratification
  privately. The former 500 unsupported-only sample is not the formal sample.
- Keep each sampled DC's company/year and exact candidate EC set together.
  Preserve original text without shortening or paraphrasing. Keep one sample
  per row and its entire candidate set in one cell. Verify cell-length limits
  before export; never truncate content or create continuation rows. All 600
  candidate sets in the current sample fit within Excel's single-cell limit.
- Protect supplied material cells against accidental editing. Use dropdowns
  only in F and G, with filters, frozen identifiers and wrapped text. Put all
  instructions in this README, without adding a guide sheet or input columns.
- Validate that both packets contain identical factual inputs, valid sample
  mappings and no automated-answer leakage. Preserve the input and file hashes
  and any export issues in the private coordinator manifest.
- Preserve both original returned files. Compute inter-reviewer agreement before
  adjudication, retain unresolved counts, and record any subsequent adjudicated
  labels separately without overwriting the original responses.
- Compare support classifications with the corresponding BACE outcomes.
  Diagnosis comparison requires both a human unsupported classification and an
  existing automated diagnosis. BACE only diagnoses its own unsupported claims;
  a human-unsupported / BACE-supported case is a support disagreement with no
  original automated diagnosis, not a diagnosis match or a forced label.
- Report support and conditional diagnosis results separately, with explicit
  denominators. Also report support disagreements separately so that a
  diagnosis-agreement statistic does not conceal them.
- This packet validates BACE decisions under BACE inputs. RAGChecker and RAGAS
  have different native inputs and claim inventories. These ratings do not
  automatically establish their accuracy or a common three-framework benchmark.
- Account for sampled claims being nested within cases and companies. Two
  reviewers do not double the independent sample size. A few sampled claims
  do not constitute a fully reviewed disclosure-level score.
- Do not claim validation of extraction, candidate recall, original evidence
  quality, selected support sets, automatic rationales or full-pipeline accuracy
  from these two classification columns.

## Project references

- [Support input construction](../../script/evaluation/run_generation_claim_support_assessment.py)
- [Diagnosis input construction](../../script/evaluation/run_generation_claim_unsupported_diagnosis.py)
- [Support decision rules](../../config/evaluation/prompts/generation_claim_support_prompt_v1.txt)
- [Unsupported-diagnosis rules](../../config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt)
- [Support-label aggregation](../../script/evaluation/metrics.py)
- [Original main experiment protocol](../../PROTOCOL.md)
