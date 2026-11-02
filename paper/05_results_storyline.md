# Results storyline and main-figure plan

Prepared: 29 September 2026. Target: Nature Sustainability, Article.

This is an evidence-linked writing plan. It selects three principal findings, assigns each a display item and defines the interpretation permitted by the current artifacts. The figures below are proposed manuscript compositions, not newly rendered figures. Human validation remains pending in the inspected local workbooks.

The plan follows the agreed [research foundation](03_research_foundation.md) and the narrower contribution established by the [literature comparison](04_research_gap_verification.md). It replaces the earlier six-slot figure proposal in the [evidence map](02_evidence_map.md).

## Scientific message

In the evaluated disclosure workflow, BACE assigns a mean support rate of 55.4%; factual boundary distortion and evidence conflation account for 73.5% of its unsupported-claim diagnoses. Its native scores differ from those of RAGChecker and RAGAS on the same disclosures. Together, these observations motivate attention to the representation of evidence support and the validity of automated judgments when reviewing generated sustainability disclosures.

This is a statement about automated observations under the evaluated workflow. Source-inspected counterexamples and the pending human study constrain its interpretation. Support is relative to supplied evidence and the subsequent extracted and selected claims; it does not establish external truth or reporting compliance.

## Three principal findings

| ID / question | Working English result sentence | Role in the paper | Main display |
|---|---|---|---|
| R1 / RQ1 | Across 1,798 completed disclosures, BACE assigned a mean disclosure-level support rate of 55.4% (saved company-cluster 95% interval, 53.9–56.8%). | Establish the assessed extent of support and its distribution across reporting tasks. | Figure 2 |
| R2 / RQ2 | Factual boundary distortion and evidence conflation accounted for 31,335 of 42,646 BACE-unsupported DCs (73.5%). | Describe the dominant automated diagnostic patterns and inspect their meaning against concrete evidence. | Figure 3 |
| R3 / RQ3 | On the same 1,798 disclosures, BACE's native scores averaged 34.9 percentage points below RAGChecker and 35.3 points below RAGAS. | Establish dependence of reported support levels on the assessment method; examine inventories and judgment paths. | Figure 4 |

Numerical records N1, N3 and N4 in the [numeric ledger](analysis/storyline/numeric_ledger.json) support these sentences. The sentences should remain explicitly attributed to BACE and the native comparators until the relevant validation results are available.

## R1: Evidentiary support across disclosure tasks

**Question.** How much generated disclosure content receives support, and how does the assessment vary across the reporting tasks?

**Evidence and statistical definition.** The primary estimate averages each completed disclosure's supported/all-DC rate, giving disclosures equal weight. The pooled decomposition instead gives each DC equal weight. Direct and inferred support together count as supported. All-DC results include non-disclosure statements.

| Quantity | Verified value | Denominator / interpretation |
|---|---|---|
| Disclosure-macro support | 55.4%; saved 95% interval 53.9–56.8% | 1,798 completed disclosures across 30 companies |
| Directly supported DCs | 34,430 (36.3%) | All 94,955 BACE DCs |
| DCs supported by inference | 17,879 (18.8%) | All 94,955 BACE DCs; this share is not the separately defined inference-rate metric |
| Unsupported DCs | 42,646 (44.9%) | All 94,955 BACE DCs |
| Pooled support | 55.1% | 52,309 supported DCs / 94,955 total DCs |
| Task-specific mean range | 43.9% for S1-5 to 62.5% for G1-1 | All completed disclosures within each task; show all tasks, not only these endpoints |

Sources: [per-disclosure scores](../BACE/analysis/outputs/figures/01/01_support_distribution__disclosures.csv), [claim counts](../BACE/analysis/outputs/figures/01/01_support_distribution__claim_counts.csv), [task estimates](../BACE/analysis/outputs/figures/01/01_task_support__data.csv), and [saved mean/interval](../BACE/analysis/outputs/figures/03/03_native_comparison__cohort_summary.csv), row `BACE / Common`. Numeric ledger: N0–N2.

**Paragraph progression.** State the macro estimate; describe the full distribution; separate the pooled direct/inferred/unsupported decomposition; then show task variation. Retain protocol task order and actual task sample sizes: S1-1 and S1-5 each contain 149 completed disclosures, while the other tasks each contain 150.

**Meaning for disclosure review.** The analysis identifies the extent of support assigned under an explicit claim-evidence definition. Task variation indicates where that assessment differs within the observed workflow and sample.

**Interpretation boundary.** The unsupported proportion is not a factual-error rate. Some unsupported labels describe non-disclosure statements, and all judgments depend on extraction and candidate selection. Task differences do not isolate an effect of the reporting standard or task difficulty. In particular, the protocol supplies historical PDF evidence and a different CSV time window; it cannot establish that a temporal diagnostic pattern is general to other evidence configurations.

Keep the non-disclosure sensitivity visible in the text and supplement: excluding these statements changes the denominator, with a median within-disclosure increase of 1.9 percentage points and a maximum of 58.0 points in the saved cohort. These are descriptive changes, not corrections to a known true score. Source: [sensitivity inputs](../BACE/analysis/outputs/figures/01/01_secondary_metrics__data.csv); ledger N6.

## R2: Patterns of unsupported disclosure claims

**Question.** Which automated diagnoses account for the unsupported claims, and what do those judgments mean in source-linked cases?

**Evidence and statistical definition.** Factual boundary distortion accounts for 19,130 diagnoses (44.9% of unsupported DCs); evidence conflation accounts for 12,205 (28.6%). Their combined share is 73.5%. Keep all six categories in the displayed denominator, including non-disclosure statements. These are mutually exclusive labels assigned under ordered diagnosis rules, not independent measurements of six underlying mechanisms.

Sources: [diagnosis composition](../BACE/analysis/outputs/figures/02/02_label_composition__data.csv), [task-specific label rates](../BACE/analysis/outputs/figures/02/02_task_patterns__data.csv), [diagnosis prompt](../BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt). Numeric ledger: N3.

**Paragraph progression.** Present the composition; explain a temporal-boundary judgment; give a concise conflation example; then retain a source-extraction counterexample that limits interpretation of the automated labels. The complete task-by-label display belongs in the supplement and answers the distributional part of RQ2 without adding another main figure.

| Selected case | Intended role | Evidence-supported reading and limit |
|---|---|---|
| Wärtsilä, 2022, G1-2; DC `dc_0a68745f651e5169efaa2c0409458081` | Figure 3b: temporal boundary | The selected 2019 report card explicitly describes an online supply-chain risk solution. BACE disputes its carry-forward into the target reporting context. This illustrates the judgment; it does not show that the company discontinued the solution or independently establish the final label. |
| Nestlé, 2022, G1-2; DC `dc_84ccccefb3191a8866e4d95907b86623` | Main-text example with full evidence in the supplement | BACE disputes an ongoing development-priority relation synthesized from earlier site assessments and a later comprehensive approach. Retain the temporal and relational ambiguity; the example is not an adjudicated conflation error. |
| ASML, 2019, E1-6; DC `dc_7448bba670219eca599b5121b2de5985` | Figure 3c: source-extraction counterexample | The original glossary associates electricity conversion factors with indirect Scope 2; the flattened source text and extracted EC associate them with direct Scope 1. This challenges the automated contradiction rationale. It does not independently certify the entire generated claim as correct. |

The [case records](analysis/storyline/example_candidates.json) retain exact IDs, verbatim generated excerpts, source cards, original selection seeds and limitations. Their relevant exported inputs, DCs, ECs, candidates and diagnoses were checked against saved case artifacts. The [original ASML crop](../BACE/analysis/outputs/figures/02/02_asml_source_layout.png) and [source-page record](../BACE/analysis/outputs/figures/02/02_asml_source_layout__data.csv) preserve the local layout evidence.

**Selection rule.** Reuse the existing seeded within-label examples; do not redraw for a cleaner story. Their original sampling pools required a localizable generated-text quotation. The subset selected for the manuscript is illustrative and editorially chosen, not a representative validation sample. The source-layout comparison is a targeted follow-up to the selected ASML case.

**Meaning for disclosure review.** Reporting qualifiers and relationships between evidence items provide concrete points for inspection. The same traceability also exposes weaknesses in the assessment pipeline.

**Interpretation boundary.** Diagnosis frequencies are BACE outputs. They do not show the prevalence of independently confirmed errors or prove that boundary awareness improves evaluation. The counterexample remains in the main Results because it changes how the aggregate diagnoses should be read.

## R3: Differences among automated evaluators

**Question.** How do native assessments differ when the three methods evaluate the same generated disclosures?

| Measure | BACE | RAGChecker | RAGAS |
|---|---|---|---|
| Mean native score, common cohort | 55.4% | 90.2% | 90.7% |
| Median native claim count per disclosure | 52 | 40 | 42 |
| BACE minus comparator, percentage points | — | −34.9 | −35.3 |
| Saved 95% interval for the paired difference | — | −36.2 to −33.5 | −36.5 to −34.1 |

Sources: [paired scores](../BACE/analysis/outputs/figures/03/03_native_comparison__scores.csv), [common-cohort summaries](../BACE/analysis/outputs/figures/03/03_native_comparison__cohort_summary.csv), [paired differences](../BACE/analysis/outputs/figures/03/03_native_comparison__paired_differences.csv), and [native claim inventories](../BACE/analysis/outputs/figures/03/03_claim_inventories__data.csv). Numeric ledger: N4–N5.

**Paragraph progression.** Present score distributions and within-disclosure mean differences, then place the native claim inventories alongside them. Refer to the existing opposite-direction and combined-evidence case analyses when explaining possible mechanisms, identifying their deliberate selection. Use the complete [analysis review](../BACE/analysis/NARRATIVE_REVIEW.md) as a map to those cases, not as a replacement for their saved evidence.

**Meaning for disclosure review.** A reported support level depends on the evaluator's operationalization and claim construction. The comparison makes that dependence visible in this workflow.

**Selected claim-level illustrations.** The subsequent [disagreement review](06_verified_disagreement_examples.md) identifies Continental's employee/own-worker coverage combination and Kinnevik's adoption-status claim as unsupported under the supplied evidence despite positive native judgments from both comparators. Their native statements preserve the disputed qualifiers. Use their complete source records to develop the comparative case illustration; retain the source-extraction counterexample in R2 and distinguish this analyst inspection from independent human validation.

The [30 September expansion](07_expanded_disagreement_examples.md) adds SCA's incident-count-to-worker-count error and Banco BPM's emissions-outcome-to-target error, plus a lower-priority employee-population candidate. SCA offers the clearest counting-unit illustration. Banco BPM adds climate relevance and an original-PDF check, but its supplied table lost column headings and BACE's candidate ECs omitted the numbers; do not present it as validation that BACE recovered the original table structure.

**Interpretation boundary.** Pairing disclosures does not align the native claim inventories or judgment procedures. Lower scores do not demonstrate greater accuracy, and inventory differences do not causally explain the score gap. Literal claim overlap is not a representative semantic alignment. Retain rank comparisons and detailed judgment paths in the supplement; neither is a substitute for independent validation.

## Validation readiness and the fourth research question

The local formal A and B workbooks each contain 600 unique sample rows with no filled support or diagnosis labels. Their supplied input cells match across reviewers. The private manifest states `prepared_not_annotated`; calibration is recorded as not conducted. This establishes the state of the inspected local copies, not whether reviewers hold separate returned files elsewhere.

Sources: [validation status check](analysis/storyline/validation_status.json), [review guide](../BACE/analysis/validation/README.md), and [private sampling manifest](../BACE/analysis/validation/_private/sample_manifest.json). Numeric ledger: N7. The coordinator workbook containing automatic results is not an annotated human reference.

The design separates 400 primary units from 200 diagnosis-enriched supplementary units. Overall population-oriented estimates must use the primary units and their stratum weights under the recorded analysis rule. Do not treat all 600 as an unweighted representative sample or substitute conditional supplementary inclusion probabilities for unconditional union probabilities.

Figure 5 and its Results subsection remain `COMPUTATION_PENDING`. Once independent annotations are available, the subsection should cover:

- Inter-reviewer support agreement before adjudication, missing labels and unresolved cases.
- BACE versus the documented human reference for support judgments, using the planned sample design and company/case dependence.
- Conditional diagnosis agreement where the human reference is unsupported and a BACE diagnosis exists, with an explicit denominator and separate reporting of human-unsupported/BACE-supported cases.

These classifications assess judgments conditional on the supplied DC and candidate ECs. They do not validate extraction, candidate recall, selected support sets or comparator accuracy. Do not publish empty validation panels or write an agreement result before the corresponding analysis exists. The present descriptive Results can be drafted while this evidence remains pending; methodological validity claims must reflect what is eventually completed.

## Main-figure specification

Use five planned display slots, including the conditional validation slot. This remains within the journal's maximum of six figures and tables combined. Task heterogeneity is integrated into Figure 2 rather than assigned a separate main figure. Proposed panel letters are planning labels.

| Figure / working English title | Panel composition | Source material and readiness |
|---|---|---|
| 1. Study design and evidence boundaries | a, observed company–year–task design and analysis cohort; b, prompt-visible evidence → EC/DC extraction → candidate EC selection → support judgment → diagnosis, with the human-review boundary marked at DC/candidate-EC inputs. | [Protocol](../BACE/PROTOCOL.md), [method definition](../docs/generation_evaluation.md), [verified cohort](analysis/storyline/cohort.json), validation guide. Ready to design as a schematic; no empirical performance claim. |
| 2. Evidentiary support across disclosure tasks | a, full disclosure-score histogram; b, pooled direct/inferred/unsupported composition; c, all task means with saved company-cluster intervals. | R1 source tables. Ready for manuscript composition. Mark the different weights in a and b; show task sample sizes in c. |
| 3. Automated diagnoses and source-linked cases | a, all six diagnosis shares among unsupported DCs; b, Wärtsilä temporal example; c, ASML extraction counterexample with the source row association. | R2 tables and fixed case records. Ready for layout design; preserve exact quotations and case limits. Full Nestlé and other examples accompany the supplement. |
| 4. Native evaluator scores and claim inventories | a, three common-cohort score ECDFs; b, paired BACE-minus-comparator mean differences and saved intervals; c, distributions of native claim counts on that cohort. | R3 source tables. Ready for composition. Identify all metrics as native; avoid accuracy or superiority labels. |
| 5. Agreement with independent human assessments | a, pre-adjudication human agreement; b, BACE–human support comparison; c, conditional diagnosis comparison with support disagreements visible. | Pending annotations and analysis. Final encodings depend on completed results and estimands. |

Quantitative legends must state the unit, denominator, centre, interval definition and selection rules. Saved intervals use 2,000 company-cluster bootstrap draws, seed 20260921, with all observed disclosures retained in each resampled company cluster. No new tests or intervals were run for this writing plan. These intervals omit model-run, extraction, annotation and missing-case uncertainty and do not yield a population estimate for all source-register companies.

Apply the [journal profile](NATURE_SUSTAINABILITY_GUIDELINES.md) when rendering manuscript figures. The existing analysis specification uses a different width; prepare manuscript exports to the journal's 180 mm maximum with legible labels. Existing figures supply data and analytical content, but do not by themselves establish readiness for submission.

## Supporting material and paragraph order

| Material | Placement and reason |
|---|---|
| Sampling frame, availability exclusions, permitted source years and full provenance | Methods and supplement; retain the principal cohort and evidence boundary in Figure 1/main text. |
| Company-year heatmap and year summaries | Supplement: descriptive scope and variation, without a temporal-improvement claim. |
| Evidence-claim coverage, inference rate and non-disclosure sensitivity | Supplement, with the sensitivity qualification retained in R1 text. Evidence use is not completeness. |
| Task-by-label rates and all fixed diagnostic examples | Supplement, with the selected temporal example and source counterexample in Figure 3. |
| Rank associations, task-specific native gaps, exact-text alignment and opposite-direction cases | Supplement, with the native-inventory limitation and key judgment qualifications in R3 text. |
| Reviewer rules, sampling weights, original labels and adjudication record | Methods and supplement when available; principal validation findings belong in the main paper. |

Draft Results in this order:

1. **Study scope and boundary-aware evaluation:** establish the observed cohort and Figure 1's measurement boundary.
2. **Evidentiary support across disclosure tasks:** R1 and Figure 2.
3. **Patterns of unsupported disclosure claims:** R2, Figure 3 and the source-extraction limitation.
4. **Differences among automated evaluators:** R3 and Figure 4.
5. **Agreement with independent human assessments:** RQ4 and Figure 5 when completed evidence is available.

The current saved cohort remains 1,798 completed BACE cases from 1,800 planned cases. The incomplete cases are Banco BPM / 2019 / S1-5 and Investec / 2023 / S1-1. Native comparator-only observations are not silently added to paired analyses. Keep this snapshot for the present writing plan and refresh all dependent values together if the underlying analysis changes.

## Verification and next writing deliverable

The [verification script](analysis/storyline/verify_storyline_evidence.py) checked point-estimate arithmetic, cohort membership, task means, label counts, paired differences, workbook label completion and selected case exports. It saved [verified results](analysis/storyline/verified_results.json), a [numeric ledger](analysis/storyline/numeric_ledger.json) and [input hashes, command and environment](analysis/storyline/provenance.json). Mixed records explicitly distinguish independently checked arithmetic from source-reported intervals. No experiment output or frozen environment was modified.

The next deliverable is a first Results draft using R1–R3 and the study-scope paragraph, alongside a Methods evidence outline. Keep RQ4 explicitly pending until completed annotation and analysis artifacts are available. Revisit the strength of the main claims when those results arrive.
