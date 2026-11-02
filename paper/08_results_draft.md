# Results: first manuscript draft

Version 2, 1 October 2026. Target: Nature Sustainability, Article. This draft uses the existing main-run snapshot and the source inspections recorded during manuscript preparation. It is paired with the [full Methods draft](10_methods_draft.md), including a Results–Methods crosswalk. Figure numbers refer to the proposed compositions in the [Results storyline](05_results_storyline.md); those manuscript figures have not yet been rendered. Paragraph identifiers in HTML comments link the prose to the working evidence ledger below.

<!-- MANUSCRIPT_START -->
## Results

### Study scope and boundary-aware evaluation

<!-- R01 -->
We examined the evidentiary support of corporate sustainability disclosures generated for 30 companies across five reporting years, 2019–2023, and 12 tasks based on the 2023 European Sustainability Reporting Standards (ESRS). The tasks covered climate change, own workforce and business conduct. The design specified 1,800 company–year–task cases; 1,798 had completed BACE assessments and available scores from both comparison methods and formed the analysed cohort (Fig. 1). The two incomplete BACE cases were excluded from support summaries and paired comparisons. Each disclosure was generated using a fixed retrieval and generation configuration, with narrative passages, table rows and structured metrics drawn from the permitted company-specific source years.

<!-- R02 -->
Boundary-Aware Claim Evaluation (BACE) reconstructed support relationships between claims extracted from each generated disclosure and claims extracted from its supplied evidence. A disclosure claim received direct support when an accepted evidence set explicitly entailed its complete meaning, and inferred support when entailment required a necessary reasoning step. Claims with no accepted support set were classified as unsupported. Material qualifiers, including entity, period, population, metric and certainty, formed part of the proposition being assessed. These judgments operated on extracted claims and selected candidate evidence claims (Fig. 1); they assessed support within the supplied evidence boundary rather than independently verified corporate facts.

### Evidentiary support across disclosure tasks

<!-- R03 -->
Across the 1,798 completed disclosures, the mean disclosure-level BACE support rate was 55.4% (95% company-cluster bootstrap interval, 53.9–56.8%; Fig. 2a). This estimate gave each disclosure equal weight and counted both direct and inferred support. Pooling claims instead yielded a support rate of 55.1%: of 94,955 deduplicated disclosure claims, 34,430 received direct support (36.3%), 17,879 received inferred support (18.8%) and 42,646 were classified as unsupported (44.9%; Fig. 2b). The pooled proportions describe claims, whereas the disclosure-level mean describes the average assessed disclosure.

<!-- R04 -->
Mean support varied across the reporting tasks, from 43.9% for workforce targets (S1-5) to 62.5% for business conduct policies (G1-1; Fig. 2c). The workforce-policies and workforce-targets tasks each contributed 149 completed disclosures; the other tasks each contributed 150. These differences describe the observed workflow and evidence configuration. They do not isolate task difficulty or establish that one reporting topic is intrinsically more amenable to evidence-supported generation.

<!-- R05 -->
The primary support denominator retained all extracted disclosure claims, including assertions that information had not been disclosed or supplied. Excluding claims assigned the non-disclosure-statement diagnosis increased the support rate by a median of 1.9 percentage points within disclosures, with a maximum change of 58.0 percentage points. This sensitivity analysis shows that such assertions materially affect some disclosure-level scores. Neither denominator converts an automated unsupported proportion into a factual-error rate.

### Patterns of unsupported disclosure claims

<!-- R06 -->
Factual boundary distortion and evidence conflation together accounted for 31,335 of the 42,646 unsupported-claim diagnoses (73.5%; Fig. 3a). BACE assigned factual boundary distortion to 19,130 claims (44.9% of unsupported claims) and evidence conflation to 12,205 (28.6%). The remaining diagnoses were non-disclosure statements, inferential inflation, unsupported novelty and contradiction. Boundary distortion denotes a transfer of an anchored fact beyond a material qualifier; conflation denotes an unsupported relationship constructed from separately evidenced elements. These are mutually exclusive outputs of an ordered diagnostic procedure, rather than independently established frequencies of underlying reporting errors.

<!-- R07 -->
A temporal example illustrates why the reporting context matters to those judgments (Fig. 3b). In a disclosure generated for Wärtsilä's 2022 supplier-relationships task, the statement that the company uses an online solution for supply-chain risk identification was assigned factual boundary distortion. The cited evidence explicitly describes such a solution in a 2019 report. BACE disputed whether that historical description established use in the target reporting context; the source does not establish that the company subsequently discontinued the solution. This ambiguity is relevant to the study design, in which PDF evidence precedes the target reporting year, while structured metrics may include that year.

<!-- R08 -->
Source inspection also exposed a limitation in an automated diagnosis (Fig. 3c). For ASML's 2019 emissions disclosure, a contradiction rationale relied on an extracted evidence claim that associated electricity-consumption conversion factors with direct Scope 1 emissions. In the original 2018 report glossary, those factors belong to the adjacent indirect Scope 2 entry; the direct Scope 1 entry instead refers to natural-gas combustion and purchased carbon dioxide. Flattening the glossary had obscured the row association. This case challenges the recorded contradiction rationale and demonstrates why diagnostic counts must be interpreted alongside the transformations from source documents to evidence claims.

### Differences among automated evaluators

<!-- R09 -->
The same 1,798 disclosures received mean native faithfulness scores of 90.2% from RAGChecker and 90.7% from RAGAS, compared with BACE's mean support rate of 55.4% (Fig. 4a). Mean within-disclosure differences, calculated as BACE minus comparator, were −34.9 percentage points for RAGChecker (95% company-cluster bootstrap interval, −36.2 to −33.5) and −35.3 percentage points for RAGAS (−36.5 to −34.1; Fig. 4b). These comparisons paired disclosures but retained each method's native claim inventory and scoring procedure.

<!-- R10 -->
The median numbers of claims per disclosure were 52 for BACE, 40 for RAGChecker and 42 for RAGAS (Fig. 4c). Thus, matching the generated text and supplied evidence did not produce identical sets of evaluated propositions. The internal checking contexts also differed: RAGChecker checked individual evidence cards, RAGAS used their combined context, and BACE assessed selected extracted evidence claims (Methods). Inventory size alone does not explain the score differences, and the differences do not establish an accuracy ranking. We therefore inspected specific native judgments against the generated passages and their complete supplied evidence.

<!-- R11 -->
One disagreement changed the unit being counted. In SCA's generated 2022 corruption-and-bribery disclosure, five incidents involving worker dismissal or discipline became five workers dismissed or disciplined. The supplied indicator counted incidents, without specifying the number of distinct workers. BACE classified the claim as unsupported and diagnosed factual boundary distortion. Both RAGChecker and RAGAS retained the five-worker proposition in their extracted claims and marked it supported. RAGAS's justification itself referred to five incidents. Because an incident count does not determine a distinct-worker count, the shared positive judgments accepted a proposition that the supplied indicator did not establish.

<!-- R12 -->
A population distinction appeared in Continental's generated 2021 workforce disclosure. One supplied indicator reported 62% employee coverage by qualifying health and safety management systems; another reported 62% audited or certified system coverage for own workers. The generated passage combined these into an employee-specific audited-coverage percentage. Both comparators accepted that proposition, whereas BACE diagnosed evidence conflation. The supplied records contained no definition equating the two populations for this indicator. Identical percentages did not establish the employee-specific audited-coverage rate, although they also did not prove that the company's actual rate differed.

<!-- R13 -->
A climate-related disagreement concerned the role assigned to an emissions value. Banco BPM's generated 2023 disclosure described a strategic plan envisaging a reduction from 17.5 thousand to 7.4 thousand tonnes of carbon dioxide equivalent. Both comparators accepted the planned-reduction interpretation; RAGChecker explicitly labelled 7.4 thousand tonnes as the target. The supplied table row contained both numbers but had lost their column headings. Inspection of the original 2022 report showed that 17.5 thousand tonnes was the 2019 value, 7.4 thousand tonnes was the 2022 status, and the target column specified carbon neutrality during the plan horizon. BACE returned unsupported, but its candidate evidence claims omitted the numerical cells. Its verdict therefore does not demonstrate recovery of the original table structure.

<!-- R14 -->
These targeted cases locate disagreements in counting units, population qualifiers and the attribution of values to outcomes or targets. They complement the aggregate comparison by showing which propositions were accepted, while the source-extraction counterexample identifies a limitation within BACE. The cases were selected through lexical screening followed by inspection of complete passages and supplied evidence (Methods). They do not provide representative error frequencies or independent human validation of any evaluator.
<!-- MANUSCRIPT_END -->

## Working evidence ledger — not manuscript text

Point estimates are recomputed from saved tables by the [draft verification script](analysis/results_draft/verify_draft.py). Bootstrap endpoints are `SOURCE_REPORTED`: the script checks their saved provenance and conversion to percentages but does not rerun the bootstrap. [Verified numbers](analysis/results_draft/verified_numbers.json) retain full precision; [provenance and document checks](analysis/results_draft/provenance.json) record inputs, hashes and the command.

| Paragraph | Evidence and locator | Main display / supporting material | Claim boundary |
|---|---|---|---|
| R01 | [Protocol](../BACE/PROTOCOL.md), Tasks and years; [case metrics](../BACE/analysis/outputs/snapshot/metrics.csv), completion and native-score columns; [execution status](../BACE/results/main_v1/execution_status.json), completed IDs and failures. Verified numbers: `cohort`. | Fig. 1; Methods M1–M4 | Planned matrix differs from analysed cases; no generalization to all companies. |
| R02 | [Method definition](../docs/generation_evaluation.md), sections 2–7; [support prompt](../BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt). | Fig. 1; Methods M5 | Operational rules, not a claim that extraction or entailment is error-free. |
| R03 | [Native cohort summaries](../BACE/analysis/outputs/figures/03/03_native_comparison__cohort_summary.csv), Common/BACE; [claim counts](../BACE/analysis/outputs/figures/01/01_support_distribution__claim_counts.csv). Verified numbers: `support`. | Fig. 2a–b | Macro and pooled denominators differ; inferred fraction uses all claims. |
| R04 | [Task estimates](../BACE/analysis/outputs/figures/01/01_task_support__data.csv), all task rows. Verified numbers: `tasks`. | Fig. 2c | Descriptive differences; all tasks remain visible. |
| R05 | [Sensitivity data](../BACE/analysis/outputs/figures/01/01_secondary_metrics__data.csv), sensitivity minus all-DC support within disclosure. Verified numbers: `sensitivity`. | Supplement; Methods M7 | Changes are percentage points; only claims with the diagnosis are removed. |
| R06 | [Diagnosis composition](../BACE/analysis/outputs/figures/02/02_label_composition__data.csv), all six rows; [diagnosis rules](../BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt). Verified numbers: `diagnoses`. | Fig. 3a | Denominator includes all unsupported diagnoses; categories follow ordered rules. |
| R07 | [Fixed example records](analysis/storyline/example_candidates.json), Wärtsilä DC `dc_0a68745f651e5169efaa2c0409458081`, Evidence 7; protocol source windows. | Fig. 3b | Historical-to-current interpretation is disputed, not proof of discontinued use. |
| R08 | Same example records, ASML DC `dc_7448bba670219eca599b5121b2de5985`; [original glossary crop](../BACE/analysis/outputs/figures/02/02_asml_source_layout.png) and [source-page record](../BACE/analysis/outputs/figures/02/02_asml_source_layout__data.csv), PDF page 216 / printed page 209. | Fig. 3c | Challenges a specific rationale; not blanket confirmation of the disclosure. |
| R09 | [Common-cohort scores](../BACE/analysis/outputs/figures/03/03_native_comparison__scores.csv), [summaries](../BACE/analysis/outputs/figures/03/03_native_comparison__cohort_summary.csv) and [paired differences](../BACE/analysis/outputs/figures/03/03_native_comparison__paired_differences.csv). Verified numbers: `comparators`. | Fig. 4a–b | Comparisons pair disclosures, not aligned claims. |
| R10 | [Native inventories](../BACE/analysis/outputs/figures/03/03_claim_inventories__data.csv), three claim-count columns. Verified numbers: `inventory_medians`. | Fig. 4c | No causal attribution of score gaps to segmentation. |
| R11 | [SCA bundle](analysis/disagreement_cases/sca_incidents_workers.json), DC `dc_94969d707006865673f9d8456fa98a4f`; Evidence 23 and 26; RAGChecker 25 / RAGAS 31. | Source-linked supplementary case material | Source-relative worker-count inference; not independent verification of misconduct. |
| R12 | [Continental bundle](analysis/disagreement_cases/continental_coverage.json), DC `dc_36a636280cb20a73d7f616d90a887cfe`; Evidence 21 and 27; RAGChecker 44 / RAGAS 38. | Source-linked supplementary case material | No supplied population equivalence; real-world percentage remains unverified. |
| R13 | [Banco BPM bundle](analysis/disagreement_cases/banco_bpm_actual_as_target.json), DC `dc_9481ed6b85983e7179efe1939f81b94f`; Evidence 19; RAGChecker 21 / RAGAS 22; [original page image](analysis/disagreement_cases/banco_bpm_2022_p15.png). | Source-linked supplementary case material | Original headings were not evaluator inputs; BACE ECs omitted the numbers. |
| R14 | [Initial case review](06_verified_disagreement_examples.md), [expanded review](07_expanded_disagreement_examples.md), and their selection and exclusion records. | Methods M8 | Targeted illustrative inspection, not a validation sample. |

Native case indices above are zero-based. Methods M1–M8 in this original evidence table refer to sections of the [Methods outline](09_methods_evidence_outline.md). The [connected Methods draft](10_methods_draft.md) uses paragraph identifiers M01–M25 and supplies the current full crosswalk. Figure 4 remains the quantitative comparison specified in the storyline; the cases are described in text with linked working evidence for later supplementary packaging. The fixed Fig. 3 examples have not been replaced by the targeted comparator cases.

## Editorial status — not manuscript text

- **Completed in this draft:** study scope, RQ1–RQ3 prose, source-linked examples and paragraph-level provenance.
- **`COMPUTATION_PENDING`:** the independent-human-assessment subsection and conditional Fig. 5. The inspected formal A/B workbooks remain blank; no agreement results are written here. The updated local status check is in `verified_numbers.json / validation`.
- **Display preparation pending:** compose manuscript Figs. 1–4, write legends and package source data and supplementary cases. Figure references currently specify intended placements.
- **Next author review:** assess the argument and balance of the four subsections, particularly the population assumption in R12 and the extraction qualification in R13. The [full Methods draft](10_methods_draft.md) describes the procedures, maps all Results paragraphs to Methods and records outstanding author facts.
- **Later integration:** revise the strength of the Results and Discussion when independent annotations and their analysis are available. The present draft makes no comparative-accuracy or externally verified error-rate claim.
