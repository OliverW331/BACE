# Methods evidence outline

Version 1, 1 October 2026. Companion to the [Results draft](08_results_draft.md). This evidence-linked planning record is now implemented in the [connected Methods draft](10_methods_draft.md); use that draft for manuscript review. Completed procedures, configuration records and planned validation are distinguished below. Protocol/model-version labels describe saved settings; they do not guarantee future remote-service identity.

## M1. Study design, sampling frame and case cohort

**What Methods should establish.** One generated disclosure is a company–target-year–task case. The design evaluates one fixed retrieval and generation configuration. The research questions and descriptive analysis were organized after the experiment and must not be described as preregistered hypotheses.

The source register contains 600 companies, of which 250 met the recorded eligibility rules. Eligibility required a known latest SICS sector at or before 2023, at least one valid nonempty CSV metric in each source year 2015–2023, and a local PDF with a valid header in each source year 2015–2022. Subsequent parsing checked annual narrative availability. These criteria define a complete-source subpopulation, not an unrestricted corporate population.

Thirty companies were selected across the eleven eligible sectors. The allocation first assigned one place per sector and distributed the remaining places by Hamilton largest remainders using eligible sector size minus one, with alphabetical ties. Within-sector ordering used the recorded seed 20260916 and a sector-specific SHA-256 seed. No replacement on generated text or evaluator scores was allowed. The record states that no replacement was made in this draw.

The planned matrix contains 30 companies × five years × 12 tasks = 1,800 cases. The current analysed cohort contains 1,798 completed BACE cases with all native comparison scores. Banco BPM / 2019 / S1-5 and Investec / 2023 / S1-1 have incomplete BACE branches and remain excluded, without zero imputation. Do not infer that generation or the comparator branches failed in these cases.

**Evidence:** [protocol](../BACE/PROTOCOL.md), Population and stratified selection; [sample manifest](../BACE/evidence/sample/sample.json), `population_count`, `eligible_count`, `quotas`, `selected`, `seed`; [selected companies](../BACE/evidence/sample/selected_companies.csv); [experiment configuration](../BACE/config/experiment.json); [case metrics](../BACE/analysis/outputs/snapshot/metrics.csv); [execution status](../BACE/results/main_v1/execution_status.json). Draft verification: `cohort` and `sampling`.

**Placement:** concise scope in Results/Fig. 1; full eligibility rules, sector allocation, selected-company list and exclusions in Methods and supplementary material. Do not apply population weights to the reported disclosure-macro estimates or extrapolate them to the source register.

## M2. Disclosure tasks and source-year boundaries

Each selected company received each task for reporting years 2019–2023. The tasks use the 2023 ESRS edition as a common task definition; this is not a statement of legal requirements applicable to every company or year.

| Topic | Task identifiers and meanings |
|---|---|
| Climate change | E1-1 transition plan; E1-3 actions and resources; E1-4 targets; E1-6 greenhouse gas emissions |
| Own workforce | S1-1 policies; S1-4 actions and resources; S1-5 targets; S1-14 health and safety metrics |
| Business conduct | G1-1 policies; G1-2 supplier relationships; G1-3 anti-corruption controls; G1-4 corruption and bribery incidents |

For a target year *t*, structured metrics came from *t*−4 through *t*, whereas PDF report years ranged from *t*−4 through *t*−1. These are report-year windows, not publication-date cutoffs. A source report may contain measurements for other periods or future commitments. Disclosures from other tasks were never supplied as evidence.

**Evidence:** [task definitions](../BACE/config/tasks.json), [retrieval queries](../BACE/config/queries.json), [experiment windows](../BACE/config/experiment.json) and [protocol](../BACE/PROTOCOL.md), Tasks and years / Evidence and retrieval.

**Interpretation requirement:** explain how the historical PDF window can influence temporal support judgments. Neither current-year information completeness nor absence of publication-date leakage has been established by these windows alone. Final standard citations belong in the manuscript's bibliography after checking the exact regulatory text used; a task-definition record is sufficient for describing this experiment's selected tasks.

## M3. Evidence preparation, source quality and retrieval

**Recorded procedure.** Evidence cards comprise deterministic structured-metric cards, narrative chunks extracted with PyMuPDF, and PDF table rows extracted with pdfplumber. Narrative chunking follows the recorded 40–250-word rules. Entire eligible reports were processed without selecting pages by task keywords or evaluator outcomes. Source files, hashes, years and stable evidence identifiers were retained; PDF cards include page locations. A structured-metric card points to its extracted CSV record, which is not an independently verified PDF quotation.

The pre-generation quality gate excluded whole cards with at least ten unmapped private-use/replacement glyphs constituting more than 5% of non-whitespace characters, or more than 8,191 `cl100k_base` tokens. The protocol also records four quarantined Evonik 2023 metric mappings following source inspection. These checks do not validate every remaining extracted metric or table relationship. Original files and exclusion records were retained, and absent metrics or retrieval strata were not imputed.

Hybrid retrieval combined BM25 with `text-embedding-3-large` vectors of 3,072 dimensions. Company and source-year filtering preceded ranking. Each subquery/channel retrieved up to 200 candidates; subqueries and channels were combined through reciprocal rank fusion with *k* = 60. Final selection retained up to ten cards per evidence type, with no reranker or redistribution of missing type quotas. Prompt order was narrative, table row, then structured metric. Thus 30 is a maximum card count, not an asserted count for every case.

**Evidence:** [protocol](../BACE/PROTOCOL.md), Evidence and retrieval; [experiment source-quality settings](../BACE/config/experiment.json); [retrieval configuration](../BACE/config/retrieval/retrieval_algorithm_config_text_embedding_3_large_top200_v1.json); saved per-case generation inputs and the [snapshot manifest](../BACE/analysis/outputs/snapshot/manifest.json).

**Reproducibility detail for the full Methods:** explain that the stored vector matrix is already normalized; the retrieval configuration's `normalize_corpus_embeddings: false` controls additional normalization. It must not be paraphrased as evidence that the stored vectors are unnormalized. Export the exact query bundles, card order and exclusions with the reproducibility materials rather than introducing alternative retrieval settings from unused diagnostic configuration sections.

## M4. Generation, execution and failure handling

The configured Azure deployment is `gpt-5.6-sol`, with recorded model-version label `2026-07-09`, medium reasoning, no temperature parameter, and a maximum generation output budget of 8,192 tokens. The shared instruction requests a professional 300–500-word disclosure based only on supplied evidence. The first complete response satisfying the length rule is accepted; incomplete or out-of-range responses trigger retries of the same prompt, and rejected attempts are retained. Selection does not use evaluator scores.

Generation precedes the BACE, RAGChecker and RAGAS branches. Completion receipts preserve stage dependencies and allow verified successful work to be reused after interruption. Unresolved failures remain missing. Report the first-acceptable-response rule and saved retry policy rather than implying one model call or byte-identical reproduction for every case.

**Evidence:** [generation configuration](../BACE/config/experiment.json), `generation`; [shared prompt templates](../BACE/config/prompts/generation_prompt_templates.json); [protocol](../BACE/PROTOCOL.md), Generation and evaluations / Pilot, failures and human materials; [runtime configuration](../BACE/config/claim_execution.json); saved generated-disclosure and execution-status records.

**Full-Methods follow-up:** cite the archived freeze and environment manifest in the release package. Distinguish configured identity from provider-returned identity. Scheduling limits belong in supplementary execution details only where needed for reproduction; they are not scientific replicates or provider quota measurements.

## M5. BACE claim construction, support and diagnosis

Describe the following transformations explicitly, because each limits what the final support rate measures:

1. **Construct ECs and DCs.** Extract evidence claims (ECs) from the complete prompt-visible evidence and disclosure claims (DCs) from the generated text. The fixed pipeline uses direct extraction v8, identified-patch review v4 with operational definition v2, constrained atomicity review v2, then semantic deduplication within each case. Preserve material qualifiers and source occurrences. In `schema_only` mode, quotation matching is not an acceptance condition; stored quotations are not automatically verified attribution.
2. **Select candidate ECs.** Selection uses deduplicated EC/DC texts. It does not receive the task definition, retrieval scores or source-provenance fields as separate factual inputs.
3. **Assess full support.** The judge receives one DC, its selected candidate EC texts, company name and target reporting year. Shared company/year context assists interpretation but cannot supply missing facts. The judge returns minimal sufficient support sets with direct/inferred types, not a prose support rationale. The prompt requests all distinct minimal sufficient sets; their completeness and minimality are not independently guaranteed.
4. **Aggregate a DC verdict.** Any accepted direct set yields direct support. Accepted inferred sets with no direct set yield inferred support. No accepted set yields unsupported. Support-set size does not determine the support type. Empty candidate sets produce an empty support result deterministically without a support-model call.
5. **Diagnose unsupported DCs.** Assign exactly one label by the order below. A nonempty candidate set can still produce unsupported; topical similarity alone does not establish support.

| Order | Saved label | Operational distinction |
|---|---|---|
| 1 | `non_disclosure_statement` | The unsupported proposition asserts absence of disclosure or evidence within a stated scope. |
| 2 | `contradiction` | Evidence establishes an incompatible proposition at the same material boundaries. |
| 3 | `evidence_conflation` | Elements from multiple ECs are combined into an unsupported relationship or attribution. |
| 4 | `factual_boundary_distortion` | An anchored fact is transferred to a different material entity, time, scope, population, metric or unit. |
| 5 | `inferential_inflation` | A claim strengthens meaning, status, certainty or conclusion beyond the evidence at matching boundaries. |
| 6 | `unsupported_novelty` | No candidate EC anchors the core proposition. |

**Evidence:** [method definition](../docs/generation_evaluation.md), sections 2–10; [support prompt](../BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt); [diagnosis prompt](../BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt); [extraction configuration](../BACE/config/evaluation/configs/generation_claim_extraction_config_v8.json), [patch review](../BACE/config/evaluation/configs/generation_claim_patch_review_config_v4.json), [atomicity review](../BACE/config/evaluation/configs/generation_claim_atomicity_review_config_v2.json), [candidate selection](../BACE/config/evaluation/configs/generation_claim_candidate_selection_config.json), [support configuration](../BACE/config/evaluation/configs/generation_claim_support_config.json) and [metric implementation](../BACE/script/evaluation/metrics.py).

**Required limit:** the support decision is conditional on extraction and candidate selection. A valid-looking support graph is an output representation, not independent verification of source fidelity, candidate recall or corporate truth.

## M6. Native comparator configuration and input correspondence

The experiment used RAGChecker 0.1.9 with RefChecker 0.2.13, and RAGAS 0.4.3. Both evaluated their native faithfulness metric, using the same generated response and prompt-visible evidence through the common adapter. They retained their own extraction and checking prompts and their own claim denominators. No reference answers were supplied, and reference-dependent metrics were not reported.

| Evaluator | Judgment input and recorded aggregation |
|---|---|
| RAGChecker | Extracted response triplets are checked against individual supplied evidence cards; a response claim is counted supported when at least one card receives `Entailment`. The configured joint-checking group size is five claims; it does not mean five evidence cards are merged into one premise. |
| RAGAS | Extracted response statements are assessed against the combined supplied contexts; the faithfulness score uses the supported fraction of its own statements. |
| BACE | Each extracted DC is assessed against selected extracted ECs, with direct/inferred support aggregated as described in M5. |

The comparator transport uses the configured Azure `gpt-5.6-sol` judge with medium reasoning, preserving native prompts and scoring while adapting the request transport. The shared adapter checks input correspondence; this does not align the native proposition inventories or make the internal judgment inputs identical to BACE's candidate-EC inputs.

**Implementation evidence:** [external evaluation configuration](../BACE/config/evaluation/configs/external_evaluation_config.json), [common adapter](../BACE/script/evaluation/external_evaluation.py), [RAGChecker wrapper](../BACE/script/evaluation/run_ragchecker.py) and [RAGAS wrapper](../BACE/script/evaluation/run_ragas.py). The selected case bundles independently verify native verdicts and common prompt/response/context hashes.

**Literature attribution for the eventual prose:** cite `ragchecker2024` for claim-level entailment and retrieved-context faithfulness, and `ragas2024` for statement extraction followed by context-support assessment. Original full-text passages were checked for these exact methodological descriptions; see the [citation occurrence record](analysis/results_draft/citation_occurrences.json). Package versions, transport settings and this experiment's behavior are established by code/configuration records, not by those papers.

## M7. Outcomes, aggregation and statistical uncertainty

For a completed disclosure *d*, let *D*₍d₎ denote its deduplicated DC set, with *N*₍direct,d₎ and *N*₍inferred,d₎ accepted support counts. Define its primary support rate as:

\[
s_d = \frac{N_{\mathrm{direct},d}+N_{\mathrm{inferred},d}}{|D_d|}.
\]

The main estimate is the unweighted mean of *s*₍d₎ across completed disclosures. The pooled estimate instead divides the total supported-claim count by the total DC count. These have different weighting and must be named explicitly. Diagnosis composition divides each label count by all unsupported DCs, including those labelled non-disclosure statements. The sensitivity metric removes claims assigned that diagnosis from the all-DC denominator and reports within-disclosure changes.

The supplementary evidence-claim coverage rate divides the number of ECs used in accepted support relations by all extracted, deduplicated ECs for that disclosure. The supplementary inference rate divides inferred-supported DCs by all supported DCs. Neither should be confused with the inferred share among all DCs reported in Results. Coverage measures supplied-evidence use, not reporting completeness.

Native comparisons intersect available scores on the same completed disclosures. Compute BACE-minus-comparator differences within each disclosure before averaging. Native claim-count medians use that same paired cohort. Do not infer representative semantic matching from identical strings or the same disclosure ID.

Saved 95% percentile intervals use 2,000 company-cluster bootstrap draws with seed 20260921. Each draw resamples companies with replacement and retains every observed disclosure in each sampled company, including multiplicities; the statistic is the disclosure-weighted ratio of resampled sums to counts. The analysis is descriptive and reports no significance tests. These intervals omit model-run, extraction, annotation and missing-case uncertainty and do not implement a sector-design-adjusted extrapolation to the register. This drafting step recomputes point estimates and checks saved interval endpoints; it does not rerun bootstrap inference.

**Evidence:** [analysis contract](../BACE/analysis/ANALYSIS_SPEC.md), Statistical contract; [bootstrap implementation](../BACE/analysis/analysis_data.py), `company_bootstrap`; [metric definitions](../BACE/script/evaluation/metrics.py); per-figure CSVs linked in the Results evidence ledger. [Draft verification](analysis/results_draft/verify_draft.py) records arithmetic, cohorts and source hashes separately from `SOURCE_REPORTED` intervals.

## M8. Source inspection and illustrative case selection

The fixed diagnostic illustrations were selected from the earlier within-label pools using recorded seeds, with a localizable generated-text quotation required for that original sampling pool. Retain their IDs and this availability restriction. The Wärtsilä temporal example and ASML extraction counterexample remain fixed. Inspection of the original ASML glossary tests its row association; it does not validate the entire generated disclosure.

The additional comparator disagreements were found through targeted screening of saved BACE-unsupported claims and native comparator outputs, followed by inspection of the generated passage, full prompt-visible context and exact native statements. Lexical matches were candidate-discovery aids only. Cases where the disputed qualifier was omitted, another supplied card supported the statement, or the full generated passage supplied a qualification were not promoted as clean shared errors.

The main-text SCA, Continental and Banco BPM cases retain native claim indices and all input evidence in their bundles. For Banco BPM, the original PDF was inspected after evaluation to resolve lost column headings. Its restored headings were never evaluator inputs. BACE's omission of the numerical cells is a limitation of that example, not a reason to conceal it. The case collection is illustrative, not a probability sample for estimating evaluator error.

**Evidence:** [fixed examples](analysis/storyline/example_candidates.json); [initial review](06_verified_disagreement_examples.md); [expanded review](07_expanded_disagreement_examples.md); [screening provenance](analysis/disagreement_cases/screen_provenance.json); [bundle provenance](analysis/disagreement_cases/bundle_provenance.json); [exclusion notes](analysis/disagreement_cases/expansion_review_notes.json). Original-source locators, full evidence and both native records are linked from these files.

## M9. Independent human assessment — prepared, not completed

**Current status:** `COMPUTATION_PENDING`. The inspected formal reviewer A and B workbooks each contain the same 600 sample IDs with blank support and diagnosis cells. The private manifest states `prepared_not_annotated`; calibration is recorded as not conducted. No reviewer agreement, adjudication outcome or accuracy result can be reported from those files. This establishes the status of the local copies, not whether annotated copies exist elsewhere.

The prepared design has 400 primary units allocated proportionally across automated support strata and 200 diagnosis-enriched supplementary units. Overall claim-level agreement is to use the primary units and their stratum weights. Supplementary inclusion probabilities are conditional on the realized primary sample; the combined 600 cannot be treated as an unweighted representative sample.

Each reviewer receives company name, target year, one DC and exactly its original candidate EC set, with automated answers withheld. The requested labels are direct support, inferred support or unsupported, followed by one diagnosis only for unsupported claims. The review does not assess extraction, candidate recall, complete source documents or the accuracy of the native comparators.

**When annotations become available:** preserve original returned labels; report pre-adjudication inter-reviewer agreement, missing/unresolved units and the adjudication procedure; compare BACE support decisions with the stated human reference using the sample design and company/case dependence. Diagnosis agreement requires an appropriate human-unsupported denominator and an existing BACE diagnosis; report human-unsupported/BACE-supported cases separately. Specify the actual agreement statistic, uncertainty calculation and adjudication procedure before writing the resulting Methods as completed work.

**Evidence:** [formal review guide](../BACE/analysis/validation/README.md), [private sampling manifest](../BACE/analysis/validation/_private/sample_manifest.json), and the A/B workbooks named there. The formal conditional-judgment design supersedes the broader source-review materials described in the original protocol; distinguish that change transparently. Draft verification: `validation`.

**`AUTHOR_INPUT_NEEDED` for final reporting:** actual reviewer identities or qualifications as appropriate, calibration and annotation dates, returned files, adjudication process, and applicable ethics/consent determination. None is inferred from the prepared workbooks.

## M10. Reproducibility, availability and AI-use reporting

Keep frozen experiment outputs, prompts, dependency locks and environments unchanged. The writing checks run in the separate writing-tools environment, read saved artifacts and produce only files under `paper/`. Preserve exact data/version identifiers and the distinction between deterministic input reconstruction and stochastic model execution.

Data and Code availability statements require verified release locations, access conditions and rights for third-party metrics and corporate reports. Those facts remain `AUTHOR_INPUT_NEEDED`; do not claim an open dataset, repository DOI or completed deposit. They can be prepared after the manuscript's minimum reproducibility package is defined.

Record the actual use of LLMs in generation and evaluation and material AI assistance in manuscript preparation, including draft composition and source-inspection suggestions. Final reporting must state the authors' actual oversight and verification, rather than treating an automated internal check as independent peer review. Use the dated [journal profile](NATURE_SUSTAINABILITY_GUIDELINES.md) and recheck official requirements before submission.

## Completion and drafting order

M1–M8 have sufficient saved evidence for a substantive Methods draft with the limits above. M9 remains a prepared protocol until returned annotations and their analysis are available. M10 requires author-specific availability and oversight facts. The present Results can be reviewed alongside this outline; the next writing pass should turn M1–M8 into connected Methods prose, compose the main figures and integrate the Introduction and Discussion around the supported findings.
