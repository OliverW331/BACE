# E1/S1/G1 BACE pipeline and prompt parity audit

Access date: 26 October 2026. Scope: the current `main_v1` study, with supplementary comparisons of preserved historical prompt files. This audit reads saved records and does not change frozen prompts, experiments, results or review materials.

## Finding

**The current main study does not use separate E1, S1 and G1 BACE extraction or judgment prompts.** Across all 247,050 saved BACE call records, each stage/claim-role combination has one prompt/schema/model contract, identical across the three topic families. All 1,800 generation instructions exactly match the same configured instruction template after substitution of company, year and task title.

This establishes implementation parity in the saved study. It does not establish equal source preservation, extraction fidelity or judgment quality across domains. The shared direct-extraction prompt has six worked examples: five concern environment, climate or emissions; one concerns a generic unresolved reference. That is a documented imbalance in example coverage, not evidence that S/G were routed to a different prompt or that the examples caused their errors.

## What was checked

The cohort contains 600 E1, 600 S1 and 600 G1 cases. All saved EC/DC direct extraction, integrated review, atomicity review, semantic deduplication, candidate selection, support and diagnosis call records were read, including retries and deterministic records. These 247,050 records are not all distinct model API calls or independent observations.

For each call, the audit compared prompt version and hash, response-schema version and hash, model key/name/version, deployment and request parameters. It also compared stage manifests, configuration hashes, processing modes, recorded code identities, dynamic-input field sets and generation instructions. Prompt hashes were checked against the current local prompt files; read stage artifacts were checked against available execution receipts.

There were zero prompt-file hash mismatches, zero generation-instruction mismatches and zero mismatched receipt hashes. A total of 32,369 read files matched completed-stage receipts. Six read files belong to unfinished stages without completed-stage receipts; missing stages and files remain explicitly recorded.

E1 and G1 each have 600 final case inventories. S1 has 598: Banco BPM 2019 S1-5 and Investec 2023 S1-1 have incomplete BACE execution. This is missing execution, not a separate S1 workflow. Direct/integrated file presence does not by itself establish successful stage completion.

## Stage-by-stage result

| Stage | Shared implementation / prompt | E1 vs S1 vs G1 |
| --- | --- | --- |
| Retrieval queries | Task-specific terms, using one retrieval algorithm | Wording differs by task as intended |
| Disclosure generation | One `instruction_template`; company/year/title substitution | Identical template and recorded generation parameters |
| Direct EC/DC extraction | `generation_*_claim_extraction_prompt_v8` | Identical within each claim role |
| Integrated EC/DC review | `generation_*_claim_patch_review_prompt_v4` | Identical within each claim role |
| Atomicity EC/DC review | `generation_*_claim_atomicity_review_prompt_v2` | Identical within each claim role |
| Semantic deduplication | `generation_claim_semantic_dedup_prompt_v1` | Identical |
| Candidate selection | `generation_claim_candidate_selection_prompt_v1` | Identical |
| Support assessment | `generation_claim_support_prompt_v1` | Identical |
| Unsupported diagnosis | `generation_claim_unsupported_diagnosis_prompt_v1` | Identical |

EC and DC prompts differ by source role, consistently across all three families. Their direct-extraction definition, procedure and worked-example body are identical; their closing source-role instructions differ. EC extraction can use visible report attribution, while DC extraction must preserve the generated disclosure's assertions without inventing report attribution.

The [orchestrator](/home/muwang/master_thesis/BACE/script/pipeline.py:156) resolves one configured sequence of direct, integrated, atomic, dedup, candidate, support and diagnosis stages for every case. No topic-specific extraction or judgment branch was found in this path. The call-record audit confirms the shared path was actually used, rather than relying only on the current code's intention.

## The differences that are real

### Task content and retrieval terms

The twelve task records have the same field schema but different topic descriptions, evidence concepts and risk notes. Each family uses two subqueries for three tasks and three subqueries for its fourth task. These task-specific queries seek different evidence; they do not select different BACE judgment rules.

Task metadata such as `claim_risk_notes` is not interpolated into the support or diagnosis prompts. The generation renderer resolves the [task title](/home/muwang/master_thesis/BACE/script/rag/build_w2_generation_inputs.py:309), then substitutes it into the shared instruction. A detailed task specification is therefore not equivalent to the actual prompt received by every downstream stage.

The saved dynamic-input fields are also shared across families:

| Stage | Supplied dynamic information |
| --- | --- |
| EC extraction | Company, target year, task title, complete visible evidence section |
| DC extraction | Company, target year, generated disclosure |
| Integrated / atomic review | Corresponding source input plus draft extraction and immutable claim index |
| Deduplication | Claim units |
| Candidate selection | Target DC and available EC texts |
| Support / diagnosis | Company, target year, target DC and selected EC texts |

The task title is present in EC extraction context, but absent as a separate field in candidate selection, support and diagnosis. Topic wording can still be apparent in claim texts. Different source content and generated claims necessarily produce different full request bodies even when the static prompt is byte-identical.

### Example coverage in the shared extraction prompt

The [direct EC prompt](/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_ec_claim_extraction_prompt_v8.txt:19) uses these worked examples, repeated in the DC prompt:

| Example | Subject |
| --- | --- |
| A | Environmental policy and planned action time |
| B | Combined Scope 1/2 reduction target |
| C | Climate targets, 1.5-degree alignment and downstream references |
| D | Generic unresolved `This` |
| E | GHG figures, life-cycle indicators and Standard X |
| F | Environmental issue classification and carbon-footprint target |

The examples give detailed treatment to emissions boundaries and target identities, but contain no equally explicit worked example for a supplier stakeholder-concern table, workforce-policy population coverage, or allegations versus confirmed corruption incidents. The shared integrated and atomicity prompts also contain many emissions/target examples, although atomicity includes healthcare examples as well. These prompts should not be described as uniformly domain-balanced.

This is a content-review finding. Its effect on errors or scores has not been isolated experimentally. Adding topic-specific exceptions merely to change S/G outcomes would not establish a better or more comparable evaluator.

### Existing shared-contract defects

The previous [metadata audit](/home/muwang/master_thesis/paper/analysis/ec_metadata_audit_2026-10-26/REPORT.md) shows that the CSV builder puts dataset ESRS taxonomy inside source `Text`. Shared extraction then sometimes turns it into an EC qualifier. E1 exhibits the same pattern, so it is not an S/G-only suffix rule.

The [R04 audit](/home/muwang/master_thesis/paper/analysis/r04_source_trace_2026-10-26/R04_SOURCE_TRACE.md) shows a second failure mode. A 2019 stakeholder table becomes a narrative string without its column headings. Direct extraction excludes the card as document structure; integrated review leaves the exclusion unchanged; atomicity is constrained to preserve an empty source unit. The final support judge consequently receives a payment-duration EC from another card. This is an observed loss in source representation and EC retention, not evidence of a separate G1 support prompt.

The [atomicity instruction](/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_ec_claim_atomicity_review_prompt_v2.txt:15) explicitly says `An empty source unit must stay empty`. That restriction is shared by E/S/G. Integrated review is permitted to repair admission and coverage, but did not do so in R04.

## Descriptive screen of empty direct-extraction sources

As an additional screen, the audit counts successful direct-EC call/card presentations with an empty `claims` list. It does not classify those exclusions as correct or incorrect. The denominator is presented cards in successful saved direct calls, not independent company observations or a paired controlled comparison.

| Source type | E1: empty / presented | S1: empty / presented | G1: empty / presented |
| --- | ---: | ---: | ---: |
| Narrative | 448 / 5,728 | 753 / 5,862 | 467 / 6,000 |
| PDF table row | 1,696 / 5,319 | 1,603 / 5,182 | 1,991 / 5,715 |
| CSV metric | 0 / 6,000 | 0 / 6,000 | 0 / 6,000 |

S1 narrative cards have more empty outputs in this screen; G1 narrative cards do not show the same increase relative to E1. Source content, task mix and extraction quality can all differ. These counts do not establish a common S/G disadvantage or a causal prompt effect. Multiple exclusion reasons can attach to one source, so reason counts are not disjoint error categories.

## Historical E comparisons require a version boundary

The preserved archive contains multiple extraction-prompt versions. Archived v1 and current v8 differ substantively:

| Aspect | Preserved v1 | Current v8 |
| --- | --- | --- |
| Source context | Only `Text` is factual source material; `Source` fields organize records | Visible `Source` can identify report/speaker and source-relative dates; report attribution is required for report-derived ECs |
| Unresolved references | Replace unresolved expressions with faithful nonspecific descriptions | Preserve genuine ambiguity in the claim and record `unresolved_context`; do not invent a referent type |
| Worked examples | No A-F example section | Six examples described above |
| Output schema | Claim text and source quotes | Adds explicit unresolved context and excluded spans with reasons |

If an early E output used v1 and a later output used v8, those outputs would indeed be from different extraction contracts. However, the retained files alone do not identify a unique author-intended early E baseline or prove which version every historical output used. This audit therefore does not label all archived E results as v1.

All eleven current BACE evaluation prompt files that have archived files with the same names are byte-identical to those counterparts. The current generation instruction is also identical to the archived generation instruction, and all twelve task records match the archived combined E1/S1/G1 task file. Thus a preserved file version, a historical result, and the current main-study runtime must be distinguished when discussing a change.

The exact v1-to-v8 text difference is saved in `archived_v1_to_current_v8.diff`.

## Recommended scope of correction

The evidence supports reviewing the shared source-to-claim contract, rather than assuming that S/G currently run different BACE prompts. A coherent correction should:

1. Separate retrieval taxonomy from substantive source content consistently across E/S/G.
2. Preserve source table headings and row/column relationships, and distinguish recoverable relational tables from incomplete fragments without guessing missing structure.
3. Give the shared prompt balanced worked examples for the same underlying inference and fidelity rules across environmental, workforce and governance content.
4. Check admission and coverage before atomicity can lock in exclusions; test legitimate empty-source cases as well as recoverable claims.
5. Reconcile the evidence displayed to readers with the actual source of each candidate EC, so a source-loss defect cannot look like a judge rejecting that source directly.
6. Evaluate any revised version on fixed cross-domain cases while preserving frozen outputs. Prompt identity, source fidelity and score changes should be reported separately.

These are recommendations, not completed prompt edits or new experimental results. No existing prompt, model setting, source card, EC or score was modified.

## Reproduction and saved evidence

```bash
python paper/analysis/esg_pipeline_parity_2026-10-26/audit.py
python paper/analysis/esg_pipeline_parity_2026-10-26/static_review.py
```

- `results.json`: per-family prompt/model/schema signatures, manifests, input-field shapes, call counts, processing modes, empty-source screen, missing files and receipt checks.
- `case_call_counts.csv`: saved call-record counts by case and stage/claim role.
- `input_manifest.json`: hashes and sizes for the read evidence, plus the audit-script hash.
- `static_review.json`: task-query inventory, exact prompt-example locations, historical comparisons and supporting file hashes.
- `archived_v1_to_current_v8.diff`: preserved historical v1 versus current v8 prompt text.

This is a local implementation and evidence-flow audit. It does not establish evaluator accuracy, completed human validation or the causal effect of prompt examples on domain-specific outcomes.
