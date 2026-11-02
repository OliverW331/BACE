# BACE main experiment: meaningful findings and evidence boundaries

Audit date: 29 October 2026. Primary run: `BACE/results/main_v1`.
Status: `COMPUTED_VERIFIED` for the primary numerical reanalysis. Separate saved follow-up and forensic findings are explicitly `SOURCE_REPORTED` and were not rerun.

## Executive interpretation

The strongest result is not that BACE has proved a higher error rate or higher accuracy. It is that the saved disclosures frequently fail BACE's supplied-evidence support contract, predominantly through boundary changes and unsupported combinations rather than unanchored novelty. Large native-score disagreements persist after limited denominator diagnostics, and some survive identical claim wording. Workforce-target tasks are consistently weaker within matched company-years. These observations motivate proposition-level and source-grounded validation; they do not substitute for it.

## 1. Cohort and integrity

- Planned: 1,800 company-year-task cases; complete BACE and common native-comparison cohort: 1,798; companies: 30; target years: 2019–2023; tasks: 12.
- Incomplete: Banco BPM / 2019 / S1-5 and Investec / 2023 / S1-1. Exclude these cases from BACE and matched comparisons, not score them as zero. Comparator-only cases remain outside the paired cohort.
- Independently checked 18,155 consumed source/stage file hashes with zero mismatches, plus all nine saved snapshot table hashes and the snapshot-builder hash.
- Recomputed all complete case-level BACE and native numerators from 94,955 saved DCs and native verdict inventories. Checked each diagnosis partition, sensitivity denominator, and multi-EC-required count.
- This is not a new extraction, generation, support or diagnosis run. Hash identity does not prove source truth, extraction completeness, or annotation accuracy.

Sources: `integrity.json`; `results.json/cohort`; `provenance.json`; frozen snapshot manifest and stage source-hash map.

## 2. Meaningful primary finding: incomplete supplied-evidence support is pervasive

The disclosure-weighted BACE support mean is **55.38% [53.92%, 56.87%]**. The pooled claim-weighted rate is **55.09%** (52,309/94,955); these are distinct estimands.

The median is 55.63%, with an interquartile range of 45.24%–65.90%. There are 634/1,798 disclosures (35.26%) below 50% support and 89/1,798 (4.95%) at or above 80%. No completed disclosure is automatically classified as fully supported. The observed minimum and maximum are 6.67% and 93.42%.

Leaving out any one company changes the overall mean only to 55.02%–55.64%. The aggregate is therefore not driven by one sampled company. This is cohort robustness, not external validity.

Warranted claim: under this frozen pipeline and its supplied candidate-EC interface, unsupported claims are common across generated disclosures. Do not describe 44.91% as a verified real-world falsehood or hallucination rate.

Numerical locators: `results.json/rates/bace`, `claims`, `distribution`, `leave_one_company_out`.

## 3. Strongest diagnostic finding: scope and relationship errors dominate automated unsupported labels

The following are exclusive automated diagnoses assigned in the frozen rule order, not independent human-confirmed error classes.

| Automated diagnosis | DCs | Share of unsupported DCs | Share of all DCs | Disclosures containing label |
| --- | ---: | ---: | ---: | ---: |
| factual_boundary_distortion | 19,130 | 44.86% | 20.15% | 1,772 |
| evidence_conflation | 12,205 | 28.62% | 12.85% | 1,735 |
| non_disclosure_statement | 6,378 | 14.96% | 6.72% | 1,157 |
| inferential_inflation | 3,193 | 7.49% | 3.36% | 1,246 |
| unsupported_novelty | 1,698 | 3.98% | 1.79% | 551 |
| contradiction | 42 | 0.10% | 0.04% | 36 |

Boundary distortion and evidence conflation together account for **31,335/42,646 unsupported DCs (73.48%)**. They concern anchored facts whose time, entity, population, measurement scope or relationship is not supported as stated. Unsupported novelty accounts for only 3.98% of unsupported DCs.

Boundary labels occur in 1,772/1,798 disclosures (98.55%); conflation labels occur in 1,735/1,798 (96.50%). These patterns are distributed broadly, not confined to a few large claim inventories.

Meaning: this study's useful distinction is *preserving evidential boundaries and justified relations*, not merely detecting text with no recognizable anchor. Rare contradiction labels do not establish that almost all disclosures are factually correct. Ordered exclusive diagnosis rules and EC extraction errors can change the apparent composition.

Numerical locators: `results.json/diagnoses`, `claims/label_counts`; `diagnoses.csv`. Rule source: `BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt`.

## 4. Native evaluator disagreements are large, but are not an accuracy comparison

All rows below use the same 1,798 complete disclosures. Each evaluator retains its own claim inventory and evidence interface.

| Evaluator | Disclosure-weighted mean [95% interval] | Pooled native claim rate | Median native claim count |
| --- | ---: | ---: | ---: |
| bace | 55.38% [53.92%, 56.87%] | 55.09% | 52 |
| ragchecker | 90.24% [89.53%, 90.97%] | 90.78% | 40 |
| ragas | 90.66% [89.96%, 91.32%] | 90.67% | 42 |

The paired native-minus-BACE gaps are 34.86 pp [33.44, 36.22] for RAGChecker and 35.28 pp [34.06, 36.50] for RAGAS. Both company-level mean gaps are positive in all 30 sampled companies. Spearman rank associations with BACE are only 0.289 and 0.328, respectively: disagreement is not just an overall level offset.

### Same-wording selected overlap

Independent unique casefold/whitespace-normalized matching reproduces 5,709 BACE–RAGAS literal pairs from 1,454 disclosures, covering 6.01% of BACE DCs. In this selected overlap, BACE support is 59.27% and RAGAS support is 93.96%.

- Both supported: 3,354.
- Both unsupported: 315.
- BACE unsupported / RAGAS supported: 2,010.
- BACE supported / RAGAS unsupported: 30.
- Boundary distortion accounts for 1,419 of the 2,010 first-direction disagreements.

Meaning: differing segmentation cannot be the sole explanation for these selected same-wording disagreements. Evidence representation, candidate access and judgment rules still differ. The overlap is not representative semantic alignment, and neither verdict is ground truth. RAGChecker has no unique literal overlap under this rule; that does not mean no semantic overlap exists.

Numerical locators: `results.json/rates`, `native_minus_bace`, `native_inventories`, `literal_alignment`, `spearman_descriptive`.

## 5. Sensitivities reject two narrow explanations, not all pipeline error

Removing only BACE-unsupported DCs diagnosed as non-disclosure statements removes 6,378 DCs while leaving the supported numerator at 52,309. The disclosure-weighted mean becomes **59.72%**, a **4.35 pp** increase. Native-minus-BACE gaps remain 30.51 pp and 30.94 pp. This is a changed estimand, not a corrected support or accuracy score.

There are 1,911 zero-candidate DCs in 600 disclosures, accounting for 4.48% of unsupported DCs. Even hypothetically relabeling every such DC as supported raises the macro mean by at most **2.05 pp**, to 57.42%.

Meaning: penalizing the diagnosed non-disclosure subset or the empty-candidate subset alone cannot account for the approximately 35 pp native score gap. This does not bound extraction omissions, nonempty-but-incomplete candidate sets, or other sources of bias. The two scenarios overlap and cannot be added.

Numerical locators: `results.json/sensitivity`, `rates/non_disclosure_sensitivity`, `rates/zero_candidate_upper_bound`.

## 6. Newly paired finding: workforce-target tasks are consistently less supported

| Task | Disclosures | All-DC mean [95% interval] | Non-disclosure sensitivity mean | Diagnosed non-disclosure share of all DCs |
| --- | ---: | ---: | ---: | ---: |
| S1-5 | 149 | 43.87% [41.12%, 46.62%] | 49.69% | 12.11% |
| S1-4 | 150 | 52.24% [49.73%, 54.66%] | 53.42% | 2.13% |
| S1-1 | 149 | 52.55% [49.23%, 55.89%] | 53.26% | 1.31% |
| E1-3 | 150 | 53.15% [50.35%, 55.94%] | 54.89% | 3.32% |
| S1-14 | 150 | 53.43% [50.47%, 56.50%] | 63.82% | 16.35% |
| G1-3 | 150 | 55.30% [52.17%, 58.43%] | 58.25% | 5.10% |
| G1-4 | 150 | 55.43% [52.39%, 58.33%] | 64.45% | 14.18% |
| E1-1 | 150 | 56.54% [53.92%, 59.27%] | 60.05% | 6.38% |
| G1-2 | 150 | 57.47% [53.78%, 61.29%] | 59.76% | 4.03% |
| E1-6 | 150 | 60.78% [57.97%, 63.64%] | 71.01% | 14.00% |
| E1-4 | 150 | 61.14% [57.34%, 64.99%] | 65.23% | 7.08% |
| G1-1 | 150 | 62.51% [59.38%, 65.79%] | 62.76% | 0.42% |

On 149 matched company-years, G1-1 minus S1-5 is **18.69 pp [13.89, 23.60]**, with positive company means in 27/30 companies. After the non-disclosure sensitivity, the same contrast is 13.12 pp [8.57, 17.78]. S1-5 remains the lowest-scoring task after this removal. The exact paired contrast differs slightly from subtracting the two unpaired task means because G1-1 has an additional available case.

E1-4 and E1-6 also exceed S1-5 in matched company-years by 17.35 pp [13.08, 21.91] and 16.84 pp [13.74, 19.95], respectively.

| Task domain | All-DC mean [95% interval] | Disclosures |
| --- | ---: | ---: |
| E1 | 57.90% [55.51%, 60.26%] | 600 |
| G1 | 57.68% [55.31%, 60.12%] | 600 |
| S1 | 50.53% [48.95%, 52.04%] | 598 |

On the 148 company-years with all 12 task outputs, within-company-year domain contrasts are E1 minus S1: 7.48 pp [5.10, 9.96]; G1 minus S1: 7.33 pp [4.85, 9.92]. These compare four-task domain means within the same company-year and do not treat tasks as independent companies.

Important qualification: task ranking changes under the sensitivity denominator. For example, E1-6 becomes 71.01%, above G1-1 at 62.76%. Thus “G1-1 is intrinsically the easiest task” is not established. Task scope, non-disclosure assertions, historical evidence availability, prompt behavior and extraction may all contribute.

Numerical locators: `task_summary.csv`, `task_non_disclosure_sensitivity.csv`, `domain_summary.csv`, `paired_contrasts.csv`, `task_label_composition.csv`.

## 7. Supporting finding: BACE accepts inferred and multi-evidence support

There are 34,430 direct-support DCs and 17,879 inferred-support DCs. Inferred-only DCs constitute **34.18%** of supported DCs. A DC is classified as direct whenever it has any accepted direct set; inferred-only is therefore not the fraction of all support sets that use inference.

For 13,710/52,309 supported DCs (**26.21%**), every saved accepted support set contains more than one EC. This is an operational property of accepted support sets, not proof that a single-EC justification is logically impossible.

The case-level EC inventory contains 224,611 deduplicated ECs, of which 71,187 occur in at least one accepted support set. Macro ECCR is 34.34%; pooled ECCR is 31.69%. Repeated evidence across cases is not independent source replication. Unused ECs may be redundant or task-irrelevant; do not translate this into “the model ignores two thirds of necessary evidence” or a completeness/recall estimate.

Numerical locators: `results.json/claims/label_counts`, `evidence_use`; metric definition: `BACE/script/evaluation/metrics.py`.

## 8. Secondary exploratory pattern: later target years, not monotonic improvement

| Target year | Disclosures | All-DC mean [95% interval] |
| --- | ---: | ---: |
| 2019 | 359 | 53.11% [50.91%, 55.26%] |
| 2020 | 360 | 56.06% [53.80%, 58.40%] |
| 2021 | 360 | 54.28% [52.32%, 56.37%] |
| 2022 | 360 | 56.01% [54.23%, 57.86%] |
| 2023 | 359 | 57.41% [55.27%, 59.40%] |

On 358 matched company-task observations, 2023 minus 2019 is 4.30 pp [1.68, 6.88]; company means are positive in 20/30 companies. Annual means decline between 2020 and 2021, so a monotonic trend is not observed. The generator is fixed; changes in the reporting year and overlapping historical evidence windows do not show model learning, better real-world sustainability or causal improvements in reporting quality.

Descriptive score associations with disclosure word count and EC count are 0.018 and 0.080. These unadjusted associations do not identify mechanisms and are not headline findings.

Numerical locators: `year_summary.csv`, `paired_contrasts.csv`, `results.json/spearman_descriptive`.

## 9. Separate saved follow-up: prompt criteria matter, but do not erase the native gap

`SOURCE_REPORTED`: the saved prompt-sensitivity analysis uses 1,796 common complete disclosures and 94,854 DCs, not the primary 1,798-disclosure cohort. Adapted prompts judge the same BACE DCs against the same candidate ECs. The original macro mean on that follow-up cohort is 55.36%.

| Saved adapted condition | Increase over original BACE | Saved 95% interval for increase |
| --- | ---: | ---: |
| BACE–RAGAS-style | 7.66 pp | 6.84 to 8.46 pp |
| BACE–RAGChecker-style | 4.97 pp | 4.14 to 5.79 pp |

Meaning: judgment instructions affect support decisions even when the supplied DC/EC representation is held fixed in the saved comparison. These adapted conditions are not the native frameworks. This is not a causal decomposition of the entire native gap, evidence of evaluator accuracy, or a new computation performed here. Diagnoses were not rerun, and these changes are not additive with the removal sensitivities.

Source locator: `paper/analysis/prompt_gap_review_2026-10-22/results.json/saved_prompt_effects`, `saved_prompt_scores`; this audit's `provenance.json` records the consumed result hash.

## 10. Material validity caveat: evidence metadata enters extracted propositions

`SOURCE_REPORTED`: the 26 October saved forensic audit traces ESRS/disclosure taxonomy in CSV card text into final EC wording. It reports 6,905 DC records with at least one broadly flagged EC in an accepted support set, across 1,154 cases. The screen includes legitimate standard references and is not an adjudicated extraction-error count. It establishes downstream exposure, not how many decisions would change without those words.

This limits interpretation of the primary outcomes: supplied EC text can already have a disputed boundary or qualifier before support judgment. An original-source audit and a separately versioned sensitivity are needed to estimate effects. Do not silently remove these words from frozen ECs or reviewer packets and call the modified material the original input. The primary score is conditional on the saved pipeline, not a clean source-level error rate.

Sources: `paper/analysis/ec_metadata_audit_2026-10-26/REPORT.md`, `summary.json/downstream`; source-relative counterexamples in `BACE/analysis/NARRATIVE_REVIEW.md`.

## 11. What the main experiment cannot currently establish

The inspected formal A and B workbooks each contain 600 sample rows, **zero completed human support labels and zero completed human diagnosis labels** as of this audit. Preparing reviewer materials is not completed human validation. No new labels or adjudication were produced here.

Consequently, the current record does not establish:

- BACE has higher accuracy, precision, recall or F1 than RAGChecker/RAGAS.
- Every BACE-unsupported claim is false or externally ungrounded.
- Diagnosis percentages are independent human-confirmed error rates.
- Higher or lower scores reflect a company's real sustainability performance or legal compliance.
- ECCR measures complete use of necessary evidence.
- The 30 availability-filtered companies represent all companies or sectors.
- Cluster bootstrap intervals capture model-run randomness, extraction/annotation error or missing-case uncertainty.

Numerical locator: `results.json/human_review`, with workbook hashes. Validation scope: `BACE/analysis/validation/README.md`.

## Recommended results hierarchy

1. Lead with the *type and prevalence of supplied-evidence support failures*, especially boundary distortion and unsupported combinations.
2. Show *large native level and rank disagreements*, then the selected identical-wording comparison and limited alternative-explanation diagnostics. Label all of these disagreements, not accuracy gains.
3. Use *within-company-year task contrasts* to demonstrate where support is weakest, retaining the denominator sensitivity and all tasks.
4. Use *accepted inferred/multi-EC support* to explain the method's analytical value without claiming inference correctness.
5. Put annual patterns, raw EC coverage and weak unadjusted associations in supporting material rather than the headline.
6. Treat the saved prompt comparison as a separate follow-up and the metadata finding as a central validity caveat.

The highest-value next steps are source-grounded review of boundary/conflation disagreements (including cases where BACE is wrong), completion and analysis of the blinded support/diagnosis sample, representative semantic proposition alignment, and a separately versioned extraction sensitivity. These are recommendations, not completed or launched work.

## Reproduction and uncertainty

Run `reanalyse_main.py`, then `render_report.py` with the independent writing-tools Python environment. Only Python's standard library is required. New outputs live in this directory; frozen environments and experiment artifacts are unchanged.

All newly computed intervals use 5,000 complete-company cluster draws, seed 20261029, Python `random.Random`, and linearly interpolated 95% percentile intervals. Within each draw retain all observed records of each sampled company. Paired contrasts match the specific company-year or company-task cells before resampling. Their observations and exclusions are saved explicitly.

This intentionally differs from the original 2,000-draw NumPy bootstrap seed 20260921. Point estimates reproduce the saved results; small interval differences are Monte Carlo implementation differences, not a changed experiment. No hypothesis tests, P values or multiple-testing declarations were generated. Selected contrasts are exploratory, not prespecified confirmation.

Input hashes, code version, runtime and command are in `provenance.json`; primary results and denominators are in `results.json`; component tables are supplied as CSV. Report values are rendered directly from saved results, not copied from manuscript prose.
