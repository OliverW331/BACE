# Who is better supported in the remaining disagreements?

20 October 2026.

**The reviewed disagreements run in both directions. Some BACE rejections miss accurate descriptions of the supplied input; some comparator decisions accept an additional unsupported proposition or reject a supported inference. Many remaining cases depend on time, scope or the meaning of a verb.**

This is a completed, non-blinded AI internal review of 18 selected pairs: 12 positive disagreements outside BACE's factual-boundary category, four reverse disagreements, and two supported-agreement controls. Complete generated disclosures and all supplied cards were read. The sample was fixed by the rule in REVIEW_PLAN.md before reading its source evidence and judgment reasons. It is not independent human validation or a representative accuracy study.

## Findings that can be discussed now

1. **BACE can reject a correct statement about missing information.** R11 says that the available evidence does not contain Evonik's 2023 lost-time injury-rate result. The cards contain the 2022 result (0.25) and a 2023 target (no more than 0.26), but not the 2023 result. RAGAS accepts it. The full closed input supports that statement; BACE's own diagnosis even repeats the absence. R10 is a similar input-limited statement about SME-supplier arrangements. Neither finding establishes company-wide non-disclosure.

2. **A comparator can accept a proposition beyond the metric supplied.** R05 adds that Intesa Sanpaolo 'monitored' a Scope 1 target. The evidence supplies a 2019 target and a reduction value, not the monitoring activity. Under the stated entailment rule BACE's rejection is better supported. This depends on retaining the distinction between reporting a metric and establishing an organizational activity.

3. **BACE can also accept an unsupported inference.** In reverse disagreement R13, SES's assessment is performed in a legal context and according to EN 16247. The extracted target attributes the relation 'reflects the legal framework' to the standard itself. RAGAS rejects that added relation; BACE accepts it. The review favors RAGAS under the necessary-inference rule. Modifier attachment during target extraction also needs checking.

4. **RAGChecker can reject a supported claim.** R16 says changing weather can affect food production systems. The supplied report explicitly says changing weather influences crop yields, and other cards connect it to agriculture and food security. BACE accepts; RAGChecker marks every card Neutral. R15 is another supported reverse disagreement under the ordinary business meaning of 'material', using current and prior high-impact revenues. It does not establish a formal regulatory materiality classification.

5. **Some apparent novelty is missing from the final EC inventory, not the original input.** In R04, R07, R08 and R09, cards containing on-time payment, investment-property measures, the ASML Speak Up supplier channel or employee development reviews yield no final ECs. This is verified from EC provenance. Three targets have zero candidates; R04 gets only a payment-duration metric. Their ultimate support remains unresolved because historical applicability, missing table headings or action status still matter. The audit identifies upstream information loss, not four proven BACE false rejections.

6. **Excluding one diagnostic label does not remove all boundary issues.** R02 is labeled evidence_conflation but its rationale is a historical-to-2021 transfer. R12 is labeled non_disclosure_statement but concerns 2022 evidence used in a 2023 disclosure. Agreement control R18 is also supported by both evaluators from earlier-year sources. A uniform continuity rule must apply to agreements as well as disagreements.

## Counts within this review only

| Reviewed set | BACE better supported | Comparator better supported | Unresolved | Both supported by review |
|---|---:|---:|---:|---:|
| Positive disagreements (12) | 1 | 2 | 9 | 0 |
| Reverse disagreements (4) | 2 | 1 | 1 | 0 |
| Agreement controls (2) | 0 | 0 | 1 | 1 |

These counts reflect the explicit review rules and interpretation limits in each case. They do not estimate how much of the native residual gap is attributable to either method. In particular, uncertain cases were retained rather than forced into a winner category.

## Every reviewed pair

| Case | Comparator | Company/year | Source verdict | Review assessment |
|---|---|---|---|---|
| [R01](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R01.md) | ragas | Inter­­conti­­nenta­­l Hot­­els G­­roup / 2020 | UNRESOLVED | Unresolved |
| [R02](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R02.md) | ragas | Svenska Cellulosa / 2021 | UNRESOLVED | Unresolved |
| [R03](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R03.md) | ragchecker | Subsea 7 / 2019 | UNRESOLVED | Unresolved |
| [R04](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R04.md) | ragas | OMV / 2023 | UNRESOLVED | Unresolved |
| [R05](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R05.md) | ragas | Intesa Sanpaolo / 2019 | UNSUPPORTED | BACE better supported |
| [R06](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R06.md) | ragchecker | Hera / 2021 | UNRESOLVED | Unresolved |
| [R07](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R07.md) | ragas | Banco BPM / 2020 | UNRESOLVED | Unresolved |
| [R08](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R08.md) | ragas | ASML / 2021 | UNRESOLVED | Unresolved |
| [R09](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R09.md) | ragchecker | Evonik Industries / 2023 | UNRESOLVED | Unresolved |
| [R10](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R10.md) | ragas | Mowi / 2021 | SUPPORTED | Comparator better supported |
| [R11](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R11.md) | ragas | Evonik Industries / 2023 | SUPPORTED | Comparator better supported |
| [R12](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R12.md) | ragchecker | Deutsche Bank / 2023 | UNRESOLVED | Unresolved |
| [R13](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R13.md) | ragas | SES / 2021 | UNSUPPORTED | Comparator better supported |
| [R14](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R14.md) | ragas | Nestle / 2020 | UNRESOLVED | Unresolved |
| [R15](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R15.md) | ragchecker | Subsea 7 / 2020 | SUPPORTED | BACE better supported |
| [R16](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R16.md) | ragchecker | Nestle / 2019 | SUPPORTED | BACE better supported |
| [R17](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R17.md) | ragas | Wärtsilä / 2020 | SUPPORTED | Both supported by review |
| [R18](/home/muwang/master_thesis/paper/analysis/residual_gap_review_2026-10-20/reviews/R18.md) | ragchecker | Subsea 7 / 2020 | UNRESOLVED | Unresolved |

## What remains necessary for a full answer

The non-boundary positive-disagreement frame contains 591 RAGAS pairs and 108 RAGChecker pairs; these are separate, selected matching subsets. Their composition is saved in remaining_disagreement_composition.csv. Most of the main experiment's targets remain outside these surface matches, and the native BACE sensitivity adjusted only BACE's denominator. This review therefore cannot apportion the complete residual 21.96/21.54 percentage-point gaps.

Before estimating evaluator error rates, specify three support-policy decisions: whether unqualified historical practices may carry into the reporting year; how input-limited absence is verified; and which verbs/characterizations require separate evidence (for example monitored, delivered, allocated and material). Preserve or restore list and paragraph relations before assessing EC candidate recall. Then perform source-based human adjudication with both disagreement directions and agreement controls, keeping unresolved targets and extraction defects visible. No such additional human study or new model experiment has been performed here.

## Reproducibility

prepare_review.py fixes the sample and checks raw artifacts against the saved source ledger. review_assessments.json contains the AI judgments. finalize_review.py checks every quoted passage, audits missing EC provenance, computes the review counts and writes the per-case reports. The full packets retain original target IDs, all evidence cards, ECs, candidates, support sets and native comparator records. The scripts reproduce packet extraction and arithmetic; they do not constitute an independent rerun of the AI review.
