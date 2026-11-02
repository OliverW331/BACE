# Final analysis QA review

This review covers the final four English notebooks and their 34 exported figures. All figures were inspected panel by panel and as complete pages using PDF proofs at 1.6 pixels per point, with physical dimensions retained in metadata. This is analyst/source inspection, not blinded human annotation.

## Scientific and statistical review

- All 1,800 cases remain in the inventory. BACE has 1,798 completed cases; both external evaluators have 1,800. Missing BACE scores remain missing.
- Cross-method primary comparisons use the same 1,798 cases. Native claim inventories are not treated as a shared truth set.
- Intervals resample complete company clusters (2,000 draws, seed 20260921); subgroup ordering and correlations remain descriptive.
- Exact-text matching is deliberately narrow: 0 BACE–RAGChecker pairs and 5,709 BACE–RAGAS pairs. The zero includes sentence/triple formatting differences; it is not evidence of zero semantic overlap. No accuracy estimate is inferred.
- Examples retain automatic labels even when source inspection challenges them. ASML exposes source-layout/EC association, Air France-KLM exposes omitted indicator content, and the Investec/Banco BPM comparison shows different evidence representations and combination paths.
- Source excerpts are contiguous where described as excerpts. Unsupported source glyph U+F0B7 is displayed as an explicit code-point escape, with the untouched original in the source table. Pennon table text retains its original interleaving instead of being silently repaired.

## Rendering and source-audit decisions

- Final vector text passes the 5 pt gate. PDF crop subscripts are checked separately using original font size × actual display scale, because vector-text auditing cannot inspect rasterised source text.
- Comparable plot rectangles and panel-label anchors pass the 1.5 pt alignment gate. Reliable collision failures and unresolved clipping are absent.
- Blue/green/orange lines use line-style or marker redundancy when they share axes. Fixed categorical rows have explicit labels; heatmaps use a monotone luminance scale. Deuteranomaly, protanomaly and grayscale previews were generated from every final PDF. The colour-bearing layouts were inspected for ambiguity; monochrome reading plates retain their textual meaning.
- The source scanner requests TIFF, but the agreed deliverable is 600 dpi PNG plus PDF/SVG. Measured metadata and PNG dimensions verify the requested 183 mm output width; the scanner cannot infer this dynamic helper parameter.
- Generic missing-data warnings refer to explicitly counted undefined ratios, incomplete cohorts, and the exact-text alignment subset. No observation is removed from the master inventory for visual convenience.
- Log-scale counts and lengths are asserted positive before plotting. No pseudocount or unreported exclusion is used. Source-scanner positivity warnings reflect its limited static pattern matching.
- Vertical heatmap year labels intentionally use centred 90-degree tick rotation. Their final bounding boxes, clearance and full-page readability were inspected; no label collision is present.

## Panel-level record

Each row records a distinct evidence role. Exact n and source values are in the figure captions and exported tables. All labels, legends and axes in this table passed final visual inspection; uncertainty is either explicitly defined below or unnecessary for an observed count/source excerpt.

| Figure / panel | Unique evidence role | Summary and uncertainty | Observation / inference unit | Alignment | Collision | Visual review |
|---|---|---|---|---|---|---|
| 00_evidence_scale / a | Representation scale | Canonical card counts | Cards | PASS | Pass | Pass |
| 00_evidence_scale / b | Representation length | Exact weighted empirical cumulative distribution | Cards | PASS | Pass | Pass |
| 00_geography / single | Register-country representation | Country counts; no interval | Companies | NOT APPLICABLE | Pass | Pass |
| 00_provenance_example / single | Source-to-prompt trace | Exact text with explicit unsupported-glyph escapes | One fixed visible card | NOT APPLICABLE | Pass | Pass |
| 00_screening_gaps / single | Availability-based selection bias | Two missing-year counts; marker area encodes company count | Companies | NOT APPLICABLE | Pass | Pass |
| 00_sector_selection / single | Selection changes sector proportions | Cohort percentages; no interval | Companies | NOT APPLICABLE | Pass | Pass |
| 00_selection / single | Population narrowing | Observed company counts; no interval | Companies | NOT APPLICABLE | Pass | Pass |
| 00_source_coverage / a | Extracted-metric availability | Observed count per source year; no interval | Company-year | PASS | Pass | Pass |
| 00_source_coverage / b | Report availability | Valid PDF-header counts; no interval | Company-year | PASS | Pass | Pass |
| 00_time_windows / a | PDF time boundary | Configured inclusion, not observed data | Protocol | PASS | Pass | Pass |
| 00_time_windows / b | CSV time boundary | Configured inclusion, not observed data | Protocol | PASS | Pass | Pass |
| 00_visible_evidence / single | Exposure rather than storage | Frequency of visible card counts | Disclosures | NOT APPLICABLE | Pass | Pass |
| 01_company_year / single | Local variation | Mean across available tasks, fixed colour scale | Company-year; repeated companies | NOT APPLICABLE | Pass | Pass |
| 01_completion / single | Analysis cohort | Completed and missing branch counts | Disclosures | NOT APPLICABLE | Pass | Pass |
| 01_secondary_metrics / a | Secondary metric interpretation | Empirical distributions; undefined counts reported | Disclosures | PASS | Pass | Pass |
| 01_secondary_metrics / b | Non-disclosure sensitivity | Paired within-disclosure score changes | Disclosures | PASS | Pass | Pass |
| 01_support_distribution / a | Typical support and variation | All disclosure scores; 20 fixed bins | Disclosures nested in companies | PASS | Pass | Pass |
| 01_support_distribution / b | Support decomposition | Pooled direct/inferred/unsupported DC counts | DCs nested in disclosures/companies | PASS | Pass | Pass |
| 01_task_support / single | Task heterogeneity | Macro mean with 95% company-cluster percentile interval | Company clusters | NOT APPLICABLE | Pass | Pass |
| 01_year_support / single | Year-level description | Macro mean with 95% company-cluster percentile interval | Repeated companies | NOT APPLICABLE | Pass | Pass |
| 02_asml_source_layout / single | Original layout challenges a diagnosis | Unmodified PDF crop; effective source-font check | One source-page crop | NOT APPLICABLE | Pass | Pass |
| 02_example_contradiction / single | Contradiction interpretation | Fixed random example; exact quotes and automatic rationale; no population estimate | One DC and its complete case sources | NOT APPLICABLE | Pass | Pass |
| 02_example_evidence_conflation / single | Evidence conflation interpretation | Fixed random example; exact quotes and automatic rationale; no population estimate | One DC and its complete case sources | NOT APPLICABLE | Pass | Pass |
| 02_example_factual_boundary_distortion / single | Factual boundary distortion interpretation | Fixed random example; exact quotes and automatic rationale; no population estimate | One DC and its complete case sources | NOT APPLICABLE | Pass | Pass |
| 02_example_inferential_inflation / single | Inferential inflation interpretation | Fixed random example; exact quotes and automatic rationale; no population estimate | One DC and its complete case sources | NOT APPLICABLE | Pass | Pass |
| 02_example_non_disclosure_statement / single | Non disclosure statement interpretation | Fixed random example; exact quotes and automatic rationale; no population estimate | One DC and its complete case sources | NOT APPLICABLE | Pass | Pass |
| 02_example_unsupported_novelty / single | Unsupported novelty interpretation | Fixed random example; exact quotes and automatic rationale; no population estimate | One DC and its complete case sources | NOT APPLICABLE | Pass | Pass |
| 02_label_composition / a | Diagnostic composition | Pooled unsupported-DC shares with exact counts | Unsupported DCs | PASS | Pass | Pass |
| 02_label_composition / b | Diagnostic prevalence | Disclosures with at least one labelled DC | Disclosures | PASS | Pass | Pass |
| 02_pipeline_checks / single | Candidate/provenance dependencies | Label-specific proportions, missingness retained | Unsupported DCs | NOT APPLICABLE | Pass | Pass |
| 02_task_patterns / single | Task-specific diagnostic burden | Percent of all task DCs, no row scaling | DCs within tasks | NOT APPLICABLE | Pass | Pass |
| 03_alignment_coverage / single | Limits of exact-text matching | Unique exact-text partner counts; unmatched claims retained | Native claims | NOT APPLICABLE | Pass | Pass |
| 03_case_higher / single | Opposite-direction native score example | Extreme paired gap with explicit selection rule | One common case | NOT APPLICABLE | Pass | Pass |
| 03_case_lower / single | Opposite-direction native score example | Extreme paired gap with explicit selection rule | One common case | NOT APPLICABLE | Pass | Pass |
| 03_claim_inventories / a | Different native denominators | Empirical claim-count distributions | Disclosures | PASS | Pass | Pass |
| 03_claim_inventories / b | Count and score differences | All paired points; no causal decomposition | Disclosures | PASS | Pass | Pass |
| 03_judgement_combined_evidence / single | Combined evidence judgement path | Native claims and source values; qualitative comparison | One source-inspected case | NOT APPLICABLE | Pass | Pass |
| 03_judgement_source_coverage / single | Source coverage judgement path | Native claims and source values; qualitative comparison | One source-inspected case | NOT APPLICABLE | Pass | Pass |
| 03_native_comparison / a | Native score levels | Common-cohort empirical distributions | Paired disclosures | PASS | Pass | Pass |
| 03_native_comparison / b | Within-case score gaps | Mean difference with 95% company-cluster interval | Company clusters | PASS | Pass | Pass |
| 03_rank_agreement / a | BACE vs RAGChecker ordering | All points; descriptive Spearman, no test | Paired disclosures | PASS | Pass | Pass |
| 03_rank_agreement / b | BACE vs RAGAS ordering | All points; descriptive Spearman, no test | Paired disclosures | PASS | Pass | Pass |
| 03_rank_agreement / c | Comparator ordering | All points; descriptive Spearman, no test | Paired disclosures | PASS | Pass | Pass |
| 03_task_disagreement / single | Task variation in paired gaps | Both comparator differences with company-cluster intervals | Company clusters | NOT APPLICABLE | Pass | Pass |

## Per-figure reading revision

Each of the 34 figures now has a specific question, an encoding caption, an evidence-based pattern reading, an interpretation and figure-specific limits. All 44 panels are covered. NARRATIVE_REVIEW.md records the editorial/source review; outputs/qa/reading_checks.json checks actual saved output order, source recomputation and complete code-hidden HTML visibility. The prose revision retains pixel-identical PNGs and identical plotted CSVs relative to its baseline, carrying forward the earlier layout/colour inspection. Current PDF font, collision and alignment audits also pass.

## Reproduction and source preservation

All four notebooks completed independently in fresh kernels. Figure-source numerical outputs were compared across repeated executions. Native arithmetic, cohort counts, cache hashes, output dimensions, hyperlinks and rendered figure audits passed. The integrity report verifies 254 frozen files, all 401 source PDFs, and the unchanged native Python/package inventory. Analysis dependencies are isolated from that native environment.

No claim of formal journal submission compliance, evaluator accuracy, company compliance, causality or complete main-experiment execution is made.
