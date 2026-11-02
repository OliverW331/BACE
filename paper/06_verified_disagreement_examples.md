# Unsupported propositions accepted by both native comparators

Prepared: 29 September 2026. Review scope: generated propositions, all prompt-visible evidence cards, BACE candidate ECs, and saved claim-level RAGAS and RAGChecker judgments.

Update, 30 September 2026: the [expanded report](07_expanded_disagreement_examples.md) adds three cases and documents the current five-case selection and its qualifications. The two-example count below describes this initial selection, not an exhaustive total.

Two examples meet the requested pattern under the supplied-evidence definition of support. Their disputed event-status or population qualifier remains present in both comparators' extracted claims, and both comparators mark that claim supported. Full evidence inspection identifies the missing support described below.

These are source-inspected illustrations selected during manuscript preparation, not independent human validation or a comparative-accuracy estimate. The source CSV is itself an extracted dataset; matching its rows verifies what the evaluators received, not what actually happened at a company.

## Selection result

| Example | Unsupported step in the generated proposition | BACE | RAGChecker | RAGAS |
|---|---|---|---|---|
| Kinnevik, 2020, E1-1 | Treat a date recorded for an undertaking that had not yet adopted a transition plan as confirmation that adoption occurred. | Unsupported; saved diagnosis `contradiction` | Supported, native claim index 1 | Supported, native statement index 0 |
| Continental, 2021, S1-4 | Combine employee-specific coverage with audited-system coverage for own workers to assert an employee-specific audited-system percentage. | Unsupported; saved diagnosis `evidence_conflation` | Supported, native claim index 44 | Supported, native statement index 38 |

All native indices in this report are zero-based. The claims were inspected for semantic correspondence rather than equated solely through lexical similarity. Native verdicts were checked against RAGAS's original NLI output and RAGChecker's original claim-by-context entailment matrix. The frozen adapter verified that both comparators received the same generated text and prompt-visible evidence.

## Example 1: A prospective adoption date becomes a completed event

Case: `w2__text_embedding_3_large__stratified_by_evidence_type_n10__kinnevik__2020__e1_1_transition_plan`  
BACE DC: `dc_0ff3878beb20287502637f91ef1dd03c`

**Generated sentence, verbatim:**

> Kinnevik adopted its climate transition plan on 11 May 2020.

The BACE DC reproduces this sentence exactly. It is the opening sentence of the generated disclosure, rather than an interpretation introduced only during claim extraction.

**Evidence 21, relevant supplied fields, verbatim:**

> Reporting year: 2019.
>
> Indicator: Date of adoption of transition plan for undertaking not having adopted transition plan yet ESRS E1 Climate change. Value: 2020-05-11.

The evidence provides a date in a not-yet-adopted-plan field for the earlier reporting year. It does not confirm that the anticipated adoption subsequently occurred. The remaining supplied cards describe historical climate reporting, investment-company objectives, portfolio-company activity and other metrics; none confirms Kinnevik's adoption on that date. A numerical date match cannot supply the missing event-status confirmation.

**Native comparator records:**

| Evaluator | Exact extracted claim / statement | Saved judgment |
|---|---|---|
| RAGChecker | `Kinnevik climate transition plan` / `adopted on` / `11 May 2020` | `supported: true`; Evidence 21 receives `Entailment` |
| RAGAS | “Kinnevik adopted a climate transition plan on 11 May 2020.” | `verdict: 1`; reason: “The tracker gives 2020-05-11 as the date of adoption of Kinnevik's transition plan.” |

**Source-inspection judgment: `UNSUPPORTED_UNDER_SUPPLIED_EVIDENCE`.** The statement converts a date for a plan not yet adopted into an observed completed adoption. Both native statements retain the completed-adoption predicate, so this is a local judgment disagreement, not merely an omitted proposition in the comparator inventories.

**BACE qualification.** The saved binary unsupported judgment is defensible. Its `contradiction` diagnosis is stronger than the evidence warrants for the target year: non-adoption in the earlier reporting year does not prove continued non-adoption in the following year. Describe the example as an unsupported completion claim; do not claim the evidence proves Kinnevik never adopted a plan or that BACE's diagnosis category has been validated.

**Evidence-preserving alternative:** “The 2019 tracker records 11 May 2020 in the adoption-date field for an undertaking that had not yet adopted a transition plan.” This reports the record without certifying a subsequent event.

Audit material: [case bundle](analysis/disagreement_cases/kinnevik_adoption.json), [complete generated disclosure and all supplied evidence](analysis/disagreement_cases/kinnevik_adoption_full_evidence.md). The key card's source row is data record 167693 in the original CSV, retained in the [verified source-row extract](analysis/disagreement_cases/verified_source_rows.json). Record indices exclude the header and are not physical text-line numbers.

## Example 2: Equal percentages acquire a different population and property

Case: `w2__text_embedding_3_large__stratified_by_evidence_type_n10__continental__2021__s1_4_workforce_actions_resources`  
BACE DC: `dc_36a636280cb20a73d7f616d90a887cfe`

**Generated passage, verbatim:**

> In 2021, 62% of employees were covered by a health and safety management system based on legal requirements and/or recognized standards or guidelines. The same proportion was covered by systems that had been internally audited and/or externally audited or certified.

The second sentence inherits the employee population from the first. BACE and both comparators make that population explicit in their extracted statements.

**The two relevant source records:**

| Evidence | Population named in the indicator | Property measured | Value |
|---|---|---|---|
| Evidence 21 | Employees | Coverage by a health and safety management system based on legal requirements and/or recognized standards or guidelines | 62.0% |
| Evidence 27 | Own workers | Coverage by such a system that has also been internally audited and/or externally audited or certified | 62.0% |

The full labels are preserved in the case bundle and original CSV rows. Evidence 21 does not establish audited/certified coverage. Evidence 27 does not identify the percentage for the employee subgroup. The same percentage in two indicators does not establish that their populations or covered individuals coincide. The complete supplied evidence contains no bridge establishing that the own-worker population equals the employee population for this audited-coverage indicator.

**Native comparator records:**

| Evaluator | Exact extracted claim / statement | Saved judgment |
|---|---|---|
| RAGChecker | `Continental employees covered by internally audited and/or externally audited or certified health and safety systems in 2021` / `proportion` / `62%` | `supported: true`; Evidence 27 receives `Entailment` |
| RAGAS | “In 2021, 62% of Continental employees were covered by health and safety management systems that had been internally audited, externally audited or certified.” | `verdict: 1`; reason: “The 2021 metric reports 62.0 percent of own workers covered by systems that were internally audited, externally audited or externally certified.” |

**Source-inspection judgment: `UNSUPPORTED_UNDER_SUPPLIED_EVIDENCE`.** Both comparators accept the employee-specific audited-coverage claim using a source whose population is own workers. The generated claim joins the employee qualifier from one indicator to the audited/certified property of another. BACE's two candidate ECs preserve both original indicator labels, so the inspected disagreement does not depend on the key source being absent from its candidate set.

**Evidence-preserving alternative:** “The 2021 tracker reports 62% employee coverage by qualifying health and safety management systems, and separately reports 62% audited or certified system coverage for own workers.” Keep the two population/property definitions separate.

**Interpretation boundary.** This does not prove that Continental's actual employee audited-coverage percentage differed from 62%. It establishes that the specific employee-level percentage cannot be obtained from the supplied indicators without an additional population assumption. If an independently verified definition established identical populations, the support judgment would need to be reconsidered.

Audit material: [case bundle](analysis/disagreement_cases/continental_coverage.json), [complete generated disclosure and all supplied evidence](analysis/disagreement_cases/continental_coverage_full_evidence.md). Original CSV data records 616149 and 616150 match the supplied indicator labels and values; see the [verified source-row extract](analysis/disagreement_cases/verified_source_rows.json).

## Candidates deliberately not promoted as clear failures

The following checks prevented selection based solely on BACE's unsupported label. They are selected review notes, not an exhaustive adjudication of the screening output. Exact DC IDs, native claim records and source hashes are retained in the [alternative-review record](analysis/disagreement_cases/reviewed_alternatives.json).

| Candidate | Reason for exclusion from the two principal examples |
|---|---|
| Dufry, 2022, S1-14: absent employee coverage percentage | BACE used a non-employee coverage metric to challenge an employee-specific statement. RAGAS explicitly recognized that distinction. This does not demonstrate a comparator error. |
| Evonik, 2023, E1-4: 5.468 million tonnes in 2021 | The supplied table explicitly gives 5,468 thousand tonnes. BACE's rationale instead adds separately rounded component values. The complete supplied source supports the comparator's numerical reading. |
| IHG, 2019, E1-4: absolute emissions used in assessment | The generated passage says performance uses **both** absolute emissions and occupied-room intensity. A claim that this contradicts intensity-based targets does not follow; the full wording must be retained. |
| Nestlé, 2022, G1-3: 1.2 million compliance-training sessions | The paragraph explicitly concerns strengthening compliance culture. Whether its training count can be described as compliance training is context-dependent; it is not a clean numerical failure. |
| IHG, 2022, G1-2: mandatory supplier questionnaire since 2021 | The main dispute is persistence of a stated policy into the target year. It is less decisive than the event-status and population examples above. |
| Pennon, 2019, E1-6: 60,547 tonnes of Scope 3 emissions | The source labels a subcategory, but the full generated disclosure also qualifies available Scope 3 reporting and identifies the other-category amount. Keep this as a qualified aggregation question, rather than cropping away the surrounding qualifications to create an unequivocal failure. |
| ASML, 2021, E1-1: worldwide scope | A supplied table explicitly maps climate-related risk/opportunity disclosure to “ASML worldwide.” The source must be considered before accepting a missing-scope rationale. |

The [earlier ASML source-layout counterexample](05_results_storyline.md) also remains relevant. Favorable and unfavorable case inspections should both inform the interpretation of BACE.

## Search, verification and use in the manuscript

The first [reproducible screen](analysis/disagreement_cases/screen_candidates.py) considered all BACE contradiction labels and other unsupported DCs with an exact normalized supported RAGAS statement. It produced 2,346 screened records and 2,211 records with positive nearest native claims. The [supplementary quantitative screen](analysis/disagreement_cases/screen_numerical_candidates.py) examined 2,329 records and retained 281 lexical candidates. These overlapping, targeted screens are discovery tools, not counts of semantic disagreements or baseline errors. Uninspected candidates remain unadjudicated.

For the two selected cases, verification checked the complete generated text, all supplied cards, material qualifiers, BACE candidate ECs and empty support sets, native statements and original verdicts. The [bundle builder](analysis/disagreement_cases/build_case_bundles.py) additionally verified input hashes through the frozen adapter and matched the three decisive indicator rows to the original source CSV. [Provenance](analysis/disagreement_cases/bundle_provenance.json) records the command, environment and input hashes. No model was rerun and no frozen result was changed.

Use Continental as the main evidence-conflation illustration and Kinnevik as a complementary event-status illustration. Show the original qualifiers and both native accepted propositions beside the BACE judgment. These cases substantiate local failures to preserve support boundaries; they cannot quantify how common those failures are or establish overall BACE superiority. An independent reviewer should assess them before they are presented as human-validated examples.
