# BACE claim-to-evidence map

**Prepared:** 29 September 2026.  
**Basis:** Current saved descriptive analysis; 1,798 completed cases.  
**Purpose:** Connect candidate manuscript claims to their sources and limits.

Point estimates below were independently recomputed from the saved [case-level metrics](../BACE/analysis/outputs/snapshot/metrics.csv).
Intervals are taken from the existing analysis exports and were not rerun during paper preparation.
This document is not a validation report or a new experimental freeze.

## Principal findings available for drafting

| ID | Candidate result statement | Evidence | Interpretation boundary |
|---|---|---|---|
| C1 | The analyzed cohort comprises 1,798 completed BACE cases from a planned 30-company, five-year, 12-task design. | [Protocol](../BACE/PROTOCOL.md), [case metrics](../BACE/analysis/outputs/snapshot/metrics.csv), [saved execution status](../BACE/results/main_v1/execution_status.json). | The run status is incomplete. Availability-based eligibility limits population inference; planned cases and completed cases are different denominators. |
| C2 | BACE assigns a mean disclosure-level support rate of 55.4%, with a reported company-cluster 95% interval of 53.9–56.8%. | [Disclosure scores](../BACE/analysis/outputs/figures/01/01_support_distribution__disclosures.csv), [figure interpretation](../BACE/analysis/outputs/figures/01/01_support_distribution.reading.json). | This is an automated support estimate, not externally verified factual accuracy. Disclosures are equally weighted in the mean. |
| C3 | Of 94,955 BACE DCs, 34,430 are directly supported, 17,879 are supported by inference and 42,646 are unsupported; pooled support is 55.1%. | [Claim counts](../BACE/analysis/outputs/figures/01/01_support_distribution__claim_counts.csv), [case metrics](../BACE/analysis/outputs/snapshot/metrics.csv). | Claims are equally weighted in the pooled rate. Do not interchange this denominator with the disclosure-level mean. Non-disclosure statements remain included. |
| C4 | Factual boundary distortion and evidence conflation account for 73.5% of BACE's 42,646 unsupported-claim diagnoses. | [Diagnosis composition](../BACE/analysis/outputs/figures/02/02_label_composition__data.csv), [figure interpretation](../BACE/analysis/outputs/figures/02/02_label_composition.reading.json). | These are automated label frequencies, not validated error prevalence. Diagnosis depends on extracted claims and selected candidate evidence. |
| C5 | In 1,798 paired disclosures, BACE's native score averages 34.9 percentage points below RAGChecker and 35.3 points below RAGAS. | [Paired differences](../BACE/analysis/outputs/figures/03/03_native_comparison__paired_differences.csv), [paired scores](../BACE/analysis/outputs/figures/03/03_native_comparison__scores.csv). | Native claim inventories differ. Score differences do not establish which evaluator is more accurate or isolate the source of disagreement. |
| C6 | Source-inspected cases illustrate both disputed generated interpretations and weaknesses in source extraction or evaluator judgments. | [Narrative review](../BACE/analysis/NARRATIVE_REVIEW.md), [ASML source-layout example](../BACE/analysis/outputs/figures/02/02_asml_source_layout__data.csv), [judgment example](../BACE/analysis/outputs/figures/03/03_judgement_source_coverage__data.csv). | Case illustrations are not representative validation. Preserve counterexamples and their selection rules; do not infer a general error rate from them. |

The reported 95% intervals for C5 are −36.2 to −33.5 percentage points for BACE minus RAGChecker and −36.5 to −34.1 for BACE minus RAGAS.
The existing analysis resamples company clusters, with 2,000 bootstrap draws.
Intervals do not incorporate all extraction, judge, annotation or missing-case uncertainty.

## Supporting analyses

| Question | Existing source | Proposed role |
|---|---|---|
| How does support vary across tasks? | [Task summaries](../BACE/analysis/outputs/figures/01/01_task_support__data.csv) | Main Results, descriptive heterogeneity; interval overlap is not a pairwise test. |
| How does support vary across companies and years? | [Company-year scores](../BACE/analysis/outputs/figures/01/01_company_year__data.csv), [year summaries](../BACE/analysis/outputs/figures/01/01_year_support__data.csv) | Supporting context; no causal interpretation of year differences. |
| How much supplied evidence is used, and how much support is inferred? | [Secondary metrics](../BACE/analysis/outputs/figures/01/01_secondary_metrics__data.csv) | Supporting analysis; evidence use is not disclosure completeness or task-relevant coverage. |
| Do evaluators rank cases similarly? | [Rank associations](../BACE/analysis/outputs/figures/03/03_rank_agreement__rank_associations.csv) | Complement native score differences; ranking agreement is not accuracy. |
| Do evaluators construct different claim inventories? | [Claim inventories](../BACE/analysis/outputs/figures/03/03_claim_inventories__data.csv) | Explain comparison limits without causally attributing the score gap to segmentation. |

## Provisional main-figure plan

The journal allows at most six main figures and tables combined.
The [Results storyline](05_results_storyline.md) selects five proposed slots, including a conditional validation figure, and supplies the panel specifications and exact source tables.
Existing notebook figures are source material and may need regrouping for the manuscript.

| Slot | Scientific question | Proposed content | Status |
|---|---|---|---|
| Figure 1 | What is evaluated? | Study design, EC–DC support representation and the boundary of conditional human review. | Ready for schematic design from the protocol and method definition. |
| Figure 2 | How much generated content is supported, and how does it vary by task? | Support distribution, direct/inferred/unsupported decomposition and all task estimates (C2–C3). | Source analyses available. Company-year detail moves to supporting material. |
| Figure 3 | Which diagnoses does BACE assign, and what do they mean? | All six diagnosis shares, the fixed temporal example and the ASML source-extraction counterexample (C4 and C6). | Automated results and case records available; retain their validity limits. |
| Figure 4 | How do evaluators differ? | Paired native distributions, score differences and native claim-count distributions (C5). | Source analyses available. |
| Figure 5 | How well do BACE judgments agree with independent reviewers? | Human–human and BACE–human support agreement and conditional diagnosis agreement. | Reserved; the inspected local formal labels remain blank. |

Candidate supplementary material includes detailed source availability, sampling, full task and year breakdowns, prompt versions, expanded examples and analysis specifications.
Keep evidence essential to the central conclusion visible in the main paper.

## Evidence still needed for stronger claims

| Intended claim | What would be needed | Current implication for writing |
|---|---|---|
| BACE judgments agree with independent reviewers. | Completed reviewer files, label-quality checks, human–human agreement, adjudication and BACE–human comparison. Account for stratified sample selection when estimating population-level performance. | Reserve the validation subsection; do not insert an agreement estimate. |
| BACE is more accurate than RAGChecker or RAGAS. | Independent evaluation of the methods on appropriately aligned targets and evidence, with a defensible comparison design. | The current BACE-specific annotation packet alone does not establish comparative superiority. |
| BACE accurately captures all failures in the original evidence and disclosure. | Separate assessment of extraction fidelity, candidate recall and effects on final decisions against original materials. | Current conditional judgment validation does not establish end-to-end validity. |
| BACE represents a novel contribution beyond existing methods. | The [original-source comparison](04_research_gap_verification.md) supports an integration/domain-evaluation framing; any stronger claim needs additional evidence. | Prior methods already address context, joint support and ESG hallucination evaluation. Exclusive priority and superiority remain unestablished. |
| The findings generalize across models or improve reporting outcomes. | Additional model/workflow comparisons or an appropriate intervention/field study, respectively. | Scope the present conclusions to the evaluated workflow; discuss broader uses as implications. |

These are evidence requirements for particular claims, not an instruction to run every possible additional experiment.
Prioritize only the work required by the final paper argument.

## Immediate preparation tasks

- [x] Create a working title, aim, research questions and contribution map.
- [x] Recompute the main point estimates from existing case-level analysis data.
- [x] Link candidate findings to existing source tables and interpretations.
- [x] Record the author's choice to foreground disclosure evidence credibility and boundaries.
- [x] Draft the English research foundation around the agreed positioning.
- [ ] Review the proposed central message and determine which findings are essential.
- [ ] Document the final cohort and any refresh of the saved analysis.
- [ ] Establish human-annotation completion and the appropriate validation analysis.
- [x] Conduct a targeted original-source gap review and revise the active research foundation and blueprint, preserving unresolved access and priority limits.
- [ ] Resolve the reporting-background citation task L1 and any inaccessible close comparisons needed for stronger claims.
- [x] Select three principal findings and five proposed main display slots; record result sentences, denominators, source tables and limits in the Results storyline.
- [ ] Draft Results and Methods from the selected evidence.
