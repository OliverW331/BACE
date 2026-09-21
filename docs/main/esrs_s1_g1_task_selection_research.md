# S1 and G1 task selection for the BACE experiment

Research date: 2026-09-15. Status: research recommendation and configuration proposals; not frozen or activated. On 2026-09-16, the proposals were also expressed in the exact E1 configuration structure and connected to explicit retrieval templates; see [shared task execution](esrs_task_pipeline_alignment.md).

## Recommendation

For the existing experiment, retain the 2023 ESRS requirement definitions and propose:

- S1: S1-1 workforce policies; S1-4 workforce actions and resources; S1-5 workforce targets; S1-14 health and safety metrics.
- G1: G1-1 business conduct policies and corporate culture; G1-2 supplier relationships; G1-3 corruption and bribery prevention and detection; G1-4 corruption and bribery incidents.

This selection follows the subject matter of the standards, historical evidence examples, and the experiment's interest in evidence-supported disclosure. It does not require every standard to have identical task archetypes. S1-5 has an explicit basis in the 2023 standard; an independent G1 target requirement does not exist in that edition. G1-4 is the least secure selection on evidence coverage and must pass a source audit before freezing. [1]

The corresponding proposals are [S1 task specifications](../../_archive/previous_stage_20260921/config/tasks/proposals/esrs_s1_task_specs_2023_research_v1.json) and [G1 task specifications](../../_archive/previous_stage_20260921/config/tasks/proposals/esrs_g1_task_specs_2023_research_v1.json). They retain the existing E1 task-spec field structure and add research metadata. They do not add retrieval queries, generation templates, metric mappings or runtime enforcement.

## The standard edition must be explicit

The European Commission's live acts page lists an amendment adopted on 3 July 2026, C(2026) 5010 final. At retrieval, that page labels the act and annexes as not in force until publication in the Official Journal. The adopted text provides for application from financial year 2027, with an option for financial year 2026. This is a report of the inspected sources, not a separate determination of subsequent Official Journal publication. [2, 3]

The 2026 annex substantially changes identifiers and some content:

| Topic | 2023 requirement | 2026 adopted annex |
|---|---|---|
| Workforce policies | S1-1 | S1-1 |
| Workforce actions and resources | S1-4 | S1-3 |
| Workforce targets | S1-5 | S1-4 |
| Health and safety metrics | S1-14 | S1-13 |
| Business conduct policies | G1-1 | G1-1, with revised scope |
| Supplier relationship management | G1-2 | Within G1-2 actions, with related policy content in G1-1 |
| Corruption and bribery prevention | G1-3 | Within G1-2 actions, with related policy content in G1-1 |
| Business conduct targets | No standalone requirement | G1-3 |
| Corruption and bribery outcomes | G1-4 | G1-4, revised to convictions and sanctions, including fines |

These are topic correspondences, not assertions of identical requirements. In particular, the two proposed 2023 operational G1 tasks partly merge in the 2026 structure. A study explicitly adopting the 2026 edition could instead investigate S1-1/S1-3/S1-4/S1-13 and G1-1/G1-2/G1-3/G1-4, but would need to redesign the target task, review the narrower incident metric scope, and reassess E1 and the metric catalogue as well. Simply replacing identifiers would change their meaning. [3, 4]

Using the original 2023 Annex I is a proposed study-design choice to preserve consistency with the existing E1 configuration and local data catalogue. The 2019-2023 reports remain historical ESRS-style simulation inputs, not reports retrospectively subject to ESRS. The study should identify its frozen standard edition in its methods.

## Proposed task boundaries

| Requirement and official basis in 2023 | Information sought | Main distinctions to preserve |
|---|---|---|
| S1-1, paragraphs 17-24 | Adopted workforce policies; labour and human rights; non-discrimination; safety policy; covered workers | Commitment versus implementation; own workforce versus supplier workers; employee-only versus broader coverage |
| S1-4, paragraphs 35-43 | Actions taken, planned or underway; resources; remediation; assessment of effectiveness | Planned versus completed; activity versus demonstrated outcome; programme spending versus group spending |
| S1-5, paragraphs 44-47 and ESRS 2 MDR-T | Disclosed time-bound, outcome-oriented targets; dates; baselines where stated; population; progress; worker involvement | Ambition versus target; current result versus future objective; leadership subgroup versus all employees |
| S1-14, paragraphs 86-90 and AR 80-95 | Safety-system coverage; fatalities; recordable accidents and rates; ill health; days lost | Worker categories; accidents versus persons; LTIFR/TRIR/high-severity rates; denominator and measurement definition |
| G1-1, paragraphs 7-11 | Conduct policies and culture; reporting channels; whistleblower protection; scope and responsibilities | Policy existence versus effectiveness; confidentiality versus anonymity; hotline operation versus investigation independence |
| G1-2, paragraphs 12-15 and AR 2-3 | Supplier relationships; sustainability criteria; screening; assessments; supplier development; late-payment prevention policy | Assessment versus compliance; assessed spend versus supplier count; company actions versus an industry initiative's totals |
| G1-3, paragraphs 16-21 and AR 4-8 | Anti-corruption procedures; investigation independence; reporting; communication; training | General compliance training versus anti-corruption training; unique people versus attendances; correct coverage denominator |
| G1-4, paragraphs 22-26 | Convictions and fines; actions addressing breaches; confirmed incidents and related outcomes when disclosed | Allegations versus confirmed incidents versus convictions; general compliance cases versus corruption cases; missing versus zero |

The task scopes are bounded disclosure-generation tasks, not a claim that each generated section will satisfy every legal datapoint. Under 2023 G1-4, paragraph 24 uses mandatory language for convictions, fines and actions addressing breaches; paragraph 25 presents additional incident information as voluntary. Relevance, completeness and materiality should not be inferred from BACE's support rate. [1]

Overlap needs deliberate control. S1-1 concerns policies, S1-4 implemented or planned action, S1-5 targets and progress, and S1-14 measured safety results. The same source passage may legitimately support several tasks, but the requested output differs. G1-1 concerns the policy framework, G1-3 operational anti-corruption controls, and G1-4 outcomes. G1-2 adds supplier management, so governance coverage is not confined to internal compliance. Four tasks do not represent every topic in either standard.

## What the evidence currently supports

Online source checks provide examples rather than a coverage estimate for the eventual 30-company sample:

- BASF's 2023 diversity disclosure gives a target of 30% women in leadership positions by 2030 and reports 28.4% female leaders with disciplinary responsibility at year end. This illustrates a usable S1-5 target and a population qualifier that must survive extraction. [5]
- BASF's 2023 safety disclosure reports a high-severity injury rate of 0.03 per 200,000 working hours and a 2030 target of no more than 0.05. It also describes a change in the metric focus. The 2023 ESRS S1-14 AR 89 rate uses one million hours; changing the denominator alone does not make high-severity injuries equivalent to all recordable accidents. [1, 6]
- BASF's supplier-management disclosure provides supplier selection, assessment, development and corrective-action evidence. Its compliance disclosure separately describes policies, training, hotline reports and audits. These are plausible sources for G1-1/G1-2/G1-3, but hotline reports and audit counts do not establish confirmed corruption incidents. [7, 8]

A local scan used the five existing development companies, the years 2019-2023, `indicator_metadata.csv`, and `esg_indicators_postprocessed.csv`. Nonempty values were counted after excluding blank/null markers; numeric zero was retained. These are extracted cells, not verified source facts, independent observations, or a representative estimate for the main sample. The detailed results are saved in [the local indicator audit](esrs_s1_g1_local_indicator_audit.json).

| Requirement | Indicator definitions in local catalogue | Company-years with at least one nonempty extracted value, out of 25 |
|---|---:|---:|
| S1-6 employee characteristics, alternative | 52 | 25 |
| S1-14 health and safety | 23 | 18 |
| G1-3 prevention/training | 21 | 25 |
| G1-4 incidents | 5 | 10 |
| G1-6 payment practices, alternative | 3 | 19 |

The numeric catalogue has no dedicated S1-1, S1-4, S1-5, G1-1 or G1-2 entries. That does not demonstrate missing narrative evidence. Those tasks need PDF narrative and table retrieval rather than mandatory CSV quotas. For metric tasks, a verified table or narrative can also be valid evidence when no suitable CSV card exists.

### Source checks reveal existing metric-mapping problems

Evonik's 2023 sustainability report was checked in the local original PDF, including visual inspection of pages 124 and 130. [9]

| Existing extracted value | Source passage and problem |
|---|---|
| 8 confirmed corruption/bribery incidents | Page 124 says eight **alleged** cases were investigated; it explicitly says no evidence of the suspected conduct was found in six kick-back cases. The heading about confirmed incidents does not remove those qualifications. |
| 12 corruption-related dismissal/disciplinary incidents | Page 124 says 12 employees were dismissed following investigations of compliance violations generally. This does not establish 12 corruption incidents or convert a count of people into a count of incidents. |
| 3 corruption-related terminated business-partner incidents | The three terminated relationships on page 124 likewise concern general compliance outcomes; the passage does not establish the extracted corruption-specific classification. |
| Average invoice payment time of 60 days | Page 130 says about 90% of invoices are settled **within** 60 days. A proportion below a threshold does not establish a mean of 60 days. |

These observations are sufficient to reject unverified CSV availability as the sole task-selection criterion. They do not establish how often all other cells are wrong. The existing data have not been modified by this research.

This distinction also matters for BACE: a generated claim may faithfully repeat a wrongly labelled input card. An evaluator restricted to that supplied evidence cannot be expected to detect the original PDF-to-card error. Source-to-card validity must therefore be checked separately from generated-claim support.

## Alternatives and the decision before freezing

**S1-6 employee characteristics** is the strongest quantitative alternative, with all 25 development company-years containing extracted values. It introduces headcount/FTE, year-end/average, employee/non-employee and contract-type distinctions. Retain S1-14 initially because it covers occupational outcomes and their measurement, and retain S1-5 because it covers forward-looking workforce commitments. If a balanced source audit finds S1-14 unusable outside a narrow set of sectors, a single prespecified replacement by S1-6 is defensible. Do not switch requirements separately for different companies or years while keeping the same task label.

**S1-13 training and skills** is another plausible quantitative alternative, but it can overlap with workforce-action descriptions. **S1-16 remuneration** is relevant but requires careful gender-pay-gap definitions and scope. This research did not establish their comparative coverage; they are not ruled out on evidence grounds.

**G1-6 payment practices** is the main alternative to G1-4. Its 19/25 nonempty company-year count exceeds G1-4's 10/25, so it should not be dismissed as inherently unavailable. However, the Evonik example demonstrates that this apparent availability can include a threshold mislabelled as an average. An audit must distinguish invoice payment time, standard terms, days payable outstanding, proportions paid within a threshold, and legal proceedings. Compare source-validated G1-4 and G1-6 coverage before the final decision. G1-4 remains the provisional choice because incident status and outcomes are substantively distinct from policies and controls, not because BACE is expected to outperform on them.

**G1-5 political influence and lobbying** is substantively valid. It would broaden coverage, but the current source checks do not establish sufficient cross-country comparability or historical evidence coverage to prioritize it. General board composition and executive remuneration mostly belong to ESRS 2 GOV; they are not replacements for G1 business-conduct requirements.

The next source audit should use companies spanning the intended sectors and early/late years, selected before examining evaluator disagreements. Record whether each core information need has traceable evidence, its definition and boundaries, and whether absence is explicitly stated. Evaluate retrieval failure separately. Set coverage and task-retention criteria before running the comparison; this research does not invent a numerical cutoff after observing the five-company counts.

Sparse evidence may be a legitimate case characteristic. Keep explicit zero, explicit absence, non-disclosure, unavailable documents and retrieval failure separate; do not fill them with invented facts. If a case yields no assessable disclosure claims, define its treatment before the run rather than interpreting a missing support-rate denominator as perfect faithfulness.

## Implementation status

Both proposal files contain four tasks, English task descriptions, official locators, retrieval facets, evidence types, claim boundaries and research status. Their target years match the planned 2019-2023 main study. The existing E1 configuration still includes 2018, so the eventual combined run must use one explicit year matrix.

The original research files are stored under `config/tasks/proposals/`. The 2026-09-16 integration adds S1/G1 files with the exact E1 field structure, a combined twelve-task specification, and explicit expanded retrieval queries. The existing generation instruction is already generic and is reused; the title resolver reads each task's name from its specification. These configurations passed an offline compatibility check, documented in [shared task execution](esrs_task_pipeline_alignment.md). Source-card validity, corpus eligibility and actual retrieval performance remain to be checked. The proposal metadata does not enforce source validation or temporal eligibility. No retrieval, generation or model-based evaluation was run for this research.

## Sources inspected

1. [Commission Delegated Regulation (EU) 2023/2772, original Annex I](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2772). ESRS S1, ESRS G1 and ESRS 2 MDR-T; paragraph locators are provided above.
2. [European Commission: Implementing and delegated acts, CSRD](https://finance.ec.europa.eu/regulation-and-supervision/financial-services-legislation/implementing-and-delegated-acts/corporate-sustainability-reporting-directive_en). Adoption and publication-status information inspected on the research date.
3. [C(2026) 5010 final, adopted act](https://ec.europa.eu/finance/docs/level-2-measures/csrd-delegated-act-2026-5010_en.pdf). Explanatory memorandum and application provisions.
4. [C(2026) 5010 final, annex](https://ec.europa.eu/finance/docs/level-2-measures/csrd-delegated-act-2026-5010-annex_en.pdf). S1 contents and requirements; G1 printed pages 145-149, especially page 148 for the new G1-3 targets requirement.
5. [BASF Report 2023: Inclusion of Diversity](https://report.basf.com/2023/en/combined-managements-report/environmental-social-governance/social/employees/in-focus-inclusion-of-diversity.html).
6. [BASF Report 2023: Safety and Health](https://report.basf.com/2023/en/combined-managements-report/environmental-social-governance/social/in-focus-safety-and-health.html).
7. [BASF Report 2023: Supplier Management](https://report.basf.com/2023/en/combined-managements-report/environmental-social-governance/governance/supplier-management.html).
8. [BASF Report 2023: Compliance](https://report.basf.com/2023/en/corporate-governance/compliance.html).
9. [Evonik Sustainability Report 2023, local original PDF](../../data/raw/reports_pdf/060107a1-5462-4b5b-adf7-ca200f3bb587_2023_SR.pdf), pages 124 and 130. Local catalogue: [indicator metadata](../../data/raw/datasets/indicator_metadata.csv). Extracted values: [postprocessed indicators](../../data/processed/results/esg_indicators_postprocessed.csv).
