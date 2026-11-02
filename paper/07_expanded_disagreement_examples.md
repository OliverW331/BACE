# Expanded source-inspected disagreement examples

Prepared: 30 September 2026. This extends the [initial two examples](06_verified_disagreement_examples.md) with two principal illustrations and one lower-priority qualified candidate. The selected pool now contains **five cases: four principal illustrations and one qualified candidate**. It is not an exhaustive count of unsupported claims accepted by the comparators.

All five have an empty BACE support set and saved supported judgments from both RAGAS and RAGChecker for the disputed proposition or its relevant component. Inspection includes the full generated passage, every prompt-visible evidence card, candidate evidence claims and native outputs. The cases illustrate support relative to supplied evidence. They are author-review materials, not completed independent human adjudication or comparative-accuracy estimates.

## Current selection

| Case | Unsupported inference | Native RAGChecker / RAGAS indices | Interpretation priority |
|---|---|---|---|
| Kinnevik, 2020, E1-1 | A prospective adoption-date field becomes confirmation of completed adoption. | 1 / 0 | Retain the earlier qualification: BACE's contradiction diagnosis is too strong. |
| Continental, 2021, S1-4 | Employee coverage and audited-system coverage for own workers become an employee-specific audited-coverage rate. | 44 / 38 | Useful population-and-property example; depends on preserving the supplied population definitions. |
| **SCA, 2022, G1-4** | **Five incidents involving worker dismissal or discipline become five workers dismissed or disciplined.** | **25 / 31** | **Clearest new example of a changed counting unit.** |
| **Banco BPM, 2023, E1-3** | **A reported emissions outcome becomes the plan's numerical target.** | **21 / 22** | **Strong climate-disclosure illustration; preserve the table-extraction and BACE-extraction qualifications below.** |
| Deutsche Bank, 2020, S1-1 | Counts for named employment categories become an unqualified employee-population total. | 18 / 31 | Additional population-boundary example; lower priority because the duplicated source values require caution. |

Indices are zero-based. Different native inventories are not treated as interchangeable. In particular, the selected Banco BPM RAGChecker claim is the target-value component of a longer BACE/RAGAS proposition; it preserves the precise disputed attribution of 7.4 thousand tonnes to a target.

## Example 3: An incident count becomes a worker count

Case: `w2__text_embedding_3_large__stratified_by_evidence_type_n10__svenska_cellulosa__2022__g1_4_corruption_bribery_incidents`  
BACE DC: `dc_94969d707006865673f9d8456fa98a4f`

**Generated passage, verbatim:**

> In 2022, SCA reported **five confirmed incidents of corruption or bribery**. In connection with these incidents, **five own workers were dismissed or subjected to disciplinary measures**.

**Evidence 23, supplied indicator and value, verbatim:**

> Indicator: Number of confirmed incidents in which own workers were dismissed or disciplined for corruption or bribery-related incidents. Value: 5.0.

Evidence 26 separately records five confirmed incidents of corruption or bribery. Both count **incidents**. Neither reports the number of distinct workers involved. An incident can involve several workers, and a worker can be involved in more than one incident. Equal incident counts therefore do not establish five distinct workers.

The full supplied context has no 2022 worker-count record that supplies this missing link. The subsequent generated paragraph calls the figures “five disciplinary or dismissal outcomes”; this does not retract or qualify the explicit five-worker statement.

| Evaluator | Exact native proposition | Saved judgment |
|---|---|---|
| RAGChecker | `SCA` / `dismissed or subjected to disciplinary measures in connection with 2022 corruption or bribery incidents` / `5 own workers` | Supported; Evidence 23 receives `Entailment`. |
| RAGAS | “SCA dismissed or subjected five SCA workers to disciplinary measures in connection with the confirmed incidents of corruption or bribery in 2022.” | Supported; native verdict 1. |

RAGAS's reason explicitly cites “five confirmed incidents in which SCA's own workers were dismissed or disciplined.” Its accepted proposition changes the unit to workers despite that incident-based justification. BACE's saved `factual_boundary_distortion` rationale identifies this same change, and both candidate ECs preserve the incident-count wording.

**Source-inspection judgment: `UNSUPPORTED_UNDER_SUPPLIED_EVIDENCE`.** This is a count-unit failure, not a disagreement over whether disciplinary action occurred.

**Evidence-preserving alternative:** “The 2022 tracker records five confirmed incidents in which own workers were dismissed or disciplined; it does not specify the number of distinct workers involved.”

Audit: [case bundle](analysis/disagreement_cases/sca_incidents_workers.json), [full disclosure and all 30 supplied cards](analysis/disagreement_cases/sca_incidents_workers_full_evidence.md). Original CSV data records 1926004 and 1926005 match the supplied labels and values. These are extracted records, not independent verification of corporate misconduct.

## Example 4: An observed emissions value becomes a target

Case: `w2__text_embedding_3_large__stratified_by_evidence_type_n10__banco_bpm__2023__e1_3_actions_resources`  
BACE DC: `dc_9481ed6b85983e7179efe1939f81b94f`

**Generated sentence, verbatim:**

> The Strategic Plan established carbon neutrality during the plan horizon and envisaged a reduction in total net direct and indirect Scope 1 and Scope 2 emissions from 17.5 thousand to 7.4 thousand tonnes of CO₂ equivalent.

**Evidence 19, relevant supplied table row, verbatim:**

> Table row: KEY OBJECTIVES OF THE 2021-2024 STRATEGIC PLAN = Total net direct & indirect emissions (Scope 1 & 2 T-CO equivalent) 2; unnamed_column_1 = 17.5K; unnamed_column_2 = CARBON NEUTRALITY DURING THE PLAN HORIZON; unnamed_column_4 = 7.4K. Table extraction requires manual review.

The supplied row contains both numbers but loses their column headings. It does not establish that 7.4K is the target. No other supplied card establishes that attribution. Numeric co-occurrence in a strategic-plan table is insufficient to assign the target role.

**Original-page check:** Banco BPM's 2022 sustainability report, page 15, labels these columns as follows:

| Metric | 2019 | Target to 2024 | Status in 2022 |
|---|---|---|---|
| Total net direct and indirect emissions, Scope 1 and 2, tonnes CO₂ equivalent | 17.5K | Carbon neutrality during the plan horizon | 7.4K |

The original layout identifies **7.4K as the 2022 status**, while the target column states carbon neutrality. The page was checked both as [layout-preserving extracted text](analysis/disagreement_cases/banco_bpm_2022_p15.txt) and as a [rendered image](analysis/disagreement_cases/banco_bpm_2022_p15.png). The [original PDF](../data/raw/reports_pdf/1f87c1c3-4366-472a-a793-ac759c4c93cc_2022_SR.pdf) is included in the provenance manifest.

| Evaluator | Exact native proposition | Saved judgment |
|---|---|---|
| RAGChecker | `Banco BPM's 2021–2024 Strategic Plan` / `set total net Scope 1 and Scope 2 emissions target at` / `7.4 thousand tonnes of CO₂ equivalent` | Supported; Evidence 19 receives `Entailment`. |
| RAGAS | “The Strategic Plan envisaged a reduction in total net direct and indirect Scope 1 and Scope 2 emissions from 17.5 thousand tonnes to 7.4 thousand tonnes of CO₂ equivalent.” | Supported; native verdict 1. |

RAGAS's reason says the table “associates” the emissions metric with the two numbers. Association does not identify which number is a target. RAGChecker makes the incorrect target attribution explicit in its predicate.

**Source-inspection judgment: `UNSUPPORTED_UNDER_SUPPLIED_EVIDENCE`; original-page role check also contradicts the target attribution.** The model-visible evidence supports uncertainty about the number's role; the original page resolves that uncertainty as a reported outcome.

**BACE qualification.** BACE marks the proposition unsupported with `inferential_inflation`, but its selected ECs omit the two numerical cells. They preserve the plan's carbon-neutrality objective and the metric name. This example does **not** establish that BACE recovered the original column roles or successfully reasoned over both values. It demonstrates a binary disagreement involving missing table structure, with a correct unsupported result whose internal rationale has an extraction limitation.

**Evidence-preserving alternative using the supplied row only:** “The table states a carbon-neutrality objective and contains emissions values of 17.5K and 7.4K, but the extracted row does not identify their reporting roles.” After consulting the original page, a writer can instead report the 2019 value and 2022 status separately from the target. The restored headings and page image were not supplied to any evaluator and must not be retroactively added to its input.

Audit: [case bundle](analysis/disagreement_cases/banco_bpm_actual_as_target.json), [full disclosure and all 30 supplied cards](analysis/disagreement_cases/banco_bpm_actual_as_target_full_evidence.md).

## Example 5: Named employee categories become an unqualified total

Case: `w2__text_embedding_3_large__stratified_by_evidence_type_n10__deutsche_bank__2020__s1_1_workforce_policies`  
BACE DC: `dc_caf6118fd0e40f922a5261620ed0bf59`

**Generated sentence, verbatim:**

> In 2020, the reported employee population comprised 84,659 employees.

The two supplied records carrying this number are:

| Evidence | Exact indicator | Value |
|---|---|---|
| 18 | Number of employees (head count or full-time equivalent), during period Gender not reported / Non-guaranteed hours employees | 84659.0 |
| 20 | Number of employees (head count or full-time equivalent), during period Gender not reported / Permanent employees | 84659.0 |

Neither is an unrestricted total-employee indicator. Both retain employment-category and measurement qualifications. All 20 supplied cards were inspected; none establishes that either category exhausts the employee population or supplies an unrestricted total. The generated paragraph does not disclose the category limitation.

| Evaluator | Exact native proposition | Saved judgment |
|---|---|---|
| RAGChecker | `Deutsche Bank employee population in 2020` / `comprised` / `84,659 employees` | Supported; Evidence 18 and Evidence 20 receive `Entailment`. |
| RAGAS | “The reported Deutsche Bank employee population comprised 84,659 employees in 2020.” | Supported; native verdict 1. |

RAGAS's justification describes the records simply as “a number of employees of 84,659,” dropping their category qualifications. BACE's saved `factual_boundary_distortion` rationale identifies the missing total-population support; its two candidate ECs preserve the category labels.

**Source-inspection judgment: `UNSUPPORTED_UNDER_SUPPLIED_EVIDENCE` for the unqualified population-total reading.** The identical values in the two categories may indicate an upstream extraction or classification problem. They do not justify summing the records, treating the categories as disjoint, or silently relabelling either as an overall total. This example is less decisive for manuscript display than the SCA count-unit case because “reported employee population” could be read as an unspecified reported subset; the full paragraph gives readers no such subset definition.

**Evidence-preserving alternative:** “The tracker records 84,659 under both permanent-employee and non-guaranteed-hours employee indicators; these category-specific records do not establish an unrestricted employee total.” This is a statement about the supplied records, not a claim about Deutsche Bank's actual workforce size.

Audit: [case bundle](analysis/disagreement_cases/deutsche_bank_employee_population.json), [full disclosure and all 20 supplied cards](analysis/disagreement_cases/deutsche_bank_employee_population_full_evidence.md). Original CSV data records 1844401 and 1844402 match the supplied labels and values.

## Selection safeguards and limits

The initial search and numerical supplementary search are candidate-discovery procedures, not semantic adjudication. Their candidate counts overlap. Lexical similarity can match a supported neighboring claim that omits the disputed qualifier. Such matches are not counted as verified shared errors.

Further inspection excluded several plausible-looking candidates. Their exact claims, native records and source hashes are retained in the [expansion review notes](analysis/disagreement_cases/expansion_review_notes.json):

- Subsea7's claim that it monitors the percentage of onshore sites is explicitly supported by a supplied bullet point. Its separate numerical claim incorrectly assigns an electricity-volume percentage to sites, but RAGChecker rejects that numerical claim. It therefore does not satisfy the requested both-supported pattern.
- Investec's 4,483-employee passage immediately explains that the value appears under both permanent and temporary classifications and declines to infer workforce composition. Cropping away that sentence would overstate the disagreement.
- Dufry's closest numerical matches omit the disputed relationship between the at-risk population and managers. They cannot establish that both evaluators accepted that same relationship.
- Cofinimmo's renewable-electricity statement and Dufry's purchased-goods emissions share have explicit support in supplied cards despite BACE's missing-evidence rationales.
- Several policy statements are flagged unsupported only because BACE questions persistence into the target year. These are weaker examples than a changed counting unit or a demonstrated table-role error.

For a compact manuscript illustration, prioritize SCA for the clearest counting-unit error and consider Banco BPM for climate relevance with its extraction limitation disclosed. Continental remains useful for the population/property mechanism. Retain the other cases as qualified supplementary candidates. This selection is illustrative and cannot establish how often either comparator fails or whether BACE is more accurate overall.

## Reproducibility

The [bundle builder](analysis/disagreement_cases/build_case_bundles.py) verifies the five selections against frozen artifacts, checks the original native outputs and input hashes, and preserves all supplied cards. It also matches seven unique CSV source rows and records the original Banco BPM PDF. See the [bundle provenance](analysis/disagreement_cases/bundle_provenance.json), [source rows](analysis/disagreement_cases/verified_source_rows.json) and [document checks](analysis/disagreement_cases/document_checks.json).

CSV record indices exclude the header and are not physical line numbers. Source matching establishes provenance, not the correctness of the upstream extraction. No model calls, new experiments or independent human annotations were performed for this expansion.
