# Per-figure interpretation review

This revision preserves the four notebook roles and the plotted experiment data.
Each figure now has a question immediately before it, a reading caption, and
separate paragraphs for observed patterns, interpretation, and limits. The
English prose is saved in notebook outputs and code-hidden HTML. Earlier short
observations were removed where the fuller readings supersede them.

The review below concerns fit between evidence and interpretation. It is an
analyst review of the supplied results and inspected sources, not blinded human
adjudication. `outputs/qa/reading_checks.json` separately verifies saved output
order, panel coverage, source hashes, recomputation and HTML visibility. Those
mechanical checks alone cannot establish the validity of an interpretation.

## Editorial and source review

| Figure | Evidence checked and interpretation retained |
|---|---|
| 00_selection | 600 → 250 → 30; distinguish availability filtering from final sampling and population representation. |
| 00_geography | UK and Germany contribute 12/30 companies; distinguish count concentration, polygon size and operational geography. |
| 00_sector_selection | Two sectors have five selected companies each; the smallest has one. Explain minimum sector allocation and separate cohort denominators. |
| 00_source_coverage | CSV range 33–281 and rising annual medians; PDFs have one or two qualifying headers. Explain both panels, separate scales and the excluded 2023 PDF column. |
| 00_screening_gaps | The (0, 0) and (0, 8) groups contain 250 and 267 companies. Identify the collected-PDF bottleneck without inferring non-publication. |
| 00_evidence_scale | Check all three card counts and exact frequency-weighted length quantiles. Explain the short typical table row and sparse long tail, logarithmic axes and shared source reports. |
| 00_visible_evidence | Ten-card counts are 1,731, 1,520 and 1,800. Treat the peak as a retrieval cap, not evidence relevance. |
| 00_time_windows | Four PDF years versus five CSV years; adjacent windows share three/four years. Interpret the diagonal as a protocol rule, not an observed trend. |
| 00_provenance_example | The first Genmab card contains compensation/development text and a truncated ending. Exact provenance does not establish task relevance or complete PDF fidelity. |
| 01_completion | 1,798/1,800 BACE branches; separate finished generation from incomplete evaluation and retain missingness. |
| 01_support_distribution | Tallest 0.55–0.60 bin; median 55.6%, middle half 45.2–65.9%. Explain the full distribution and pooled direct/inferred/unsupported decomposition without mixing weights. |
| 01_task_support | S1-5 43.9% to G1-1 62.5%; eight means in 50–60%. Describe cluster intervals without treating overlap as a task-comparison test. |
| 01_company_year | Cell range 38.2–72.0%; row averages and within-row ranges both vary. Preserve alphabetical rows, common colour scale and two 11-task cells. |
| 01_year_support | Means 53.1, 56.1, 54.3, 56.0 and 57.4%. Report the intervening decline and avoid a monotonic-improvement claim. |
| 01_secondary_metrics | Explain both ECDF centres and the sensitivity tail: 641 zero changes, median +1.9 points, maximum +58.0. Distinguish constructs and the mechanical denominator effect. |
| 02_label_composition | Boundary/conflation comprise 73.5% of unsupported DCs and occur in nearly all disclosures. Explain both denominators; 42 contradiction labels are not 42 validated factual errors. |
| 02_task_patterns | Boundary is the largest label share in 11/12 tasks; non-disclosure varies from 0.42% to 16.4%. Interpret common-scale columns and local cells without row normalisation. |
| 02_pipeline_checks | Zero candidates: 54.5% of novelty and 15.4% of non-disclosure DCs; only 33 unsupported DCs lack literal generated-text quotes. Do not confuse quote localisation with evidence support. |
| 02_example_non_disclosure_statement | Compare 2021 fines non-disclosure with zero 2017 incidents; the year and measure both differ. Do not equate caution with fabricated data. |
| 02_example_contradiction | The source card flattens glossary definitions. Preserve the automatic label while directing the reader to the original row association. |
| 02_example_evidence_conflation | Inspect “remains”, earlier assessments and the more comprehensive 2021 approach. The contested addition is relational/temporal, not an entirely invented topic. |
| 02_example_factual_boundary_distortion | 2019 online-solution wording is explicit; the dispute is carry-forward to 2022. Missing confirmation does not demonstrate discontinuation. |
| 02_example_inferential_inflation | Contrast “require” and “expect”, retaining interleaved table text and the qualifications from other visible supplier-policy material. |
| 02_example_unsupported_novelty | The visible severity-rate indicator is omitted from the card's three retained ECs. Distinguish that omission from proof of target-year workforce-policy monitoring. |
| 02_asml_source_layout | Original PDF page 216/printed 209 associates gas/purchased CO₂ with Scope 1 and electricity factors with Scope 2. This resolves a local source association, not overall evaluator accuracy. |
| 03_native_comparison | Explain all three ECDFs, 155/233 comparator perfect scores and paired gaps of −34.9/−35.3 points. Native distributions do not identify accuracy. |
| 03_rank_agreement | Explain all three panels using above/below/tied counts, near-diagonal proportions and ρ=0.289/0.328/0.445. Separate level offsets, shared ranking and ceiling ties. |
| 03_claim_inventories | Medians 52/40/42 claims; paired count-score association ρ=−0.104. The weak relation cannot causally apportion score differences. |
| 03_task_disagreement | All 24 means are negative, with the largest between-comparator gap separation at E1-6 (10.2 points). Avoid task-selection and multiple-comparison claims. |
| 03_alignment_coverage | Zero literal RAGChecker matches and 5,709 RAGAS pairs (6.0% coverage). Neither zero semantic overlap nor representative agreement follows. |
| 03_case_lower | Investec: 9/46, 29/29 and 29/34 supported native claims. Explain the different inventories and deliberate extreme selection. |
| 03_case_higher | Banco BPM: 20/28, 12/24 and 27/29. A reversed ordering motivates cross-card inspection without attributing the whole gap to one claim. |
| 03_judgement_source_coverage | “Suppliers” appears explicitly in the 2017 visible risk definition. Challenge absence-of-anchor while retaining the 2021 temporal qualification. |
| 03_judgement_combined_evidence | Two equal pairs (35,103 and 4,638 tCO₂e), four ECs and three different judgement paths. Equality of extracted numbers does not verify real-world emissions. |

## Verification boundary

The revision baseline contains hashes of all 39 plotted source tables and all
34 rendered PNGs. The reading audit requires exact equality with that baseline,
so the earlier panel-layout and colour review can be carried forward when that
check passes. Current PDF text, alignment and collision checks still run on the
new exports. The refreshed execution and analysis manifests bind the reports to
the delivered notebook files.

Key descriptive summaries were checked against the source tables independently
of the prose renderer. Fixed examples were compared with their generated text,
visible evidence and exported case material; the original ASML page provides an
additional layout check. No main-experiment stage, evaluator score, diagnostic
label, selected example or frozen input was changed for this revision.
