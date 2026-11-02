# Figure 2 contract

Prepared: 2 October 2026. Target: Nature Sustainability, Article.

## Scientific purpose

**Question:** How much generated disclosure content receives BACE-assessed support, and how does that assessment vary across reporting tasks?

**Claim:** Across the completed workflow, BACE assigns a mean disclosure support rate of 55.4%, with variation across the observed disclosures and tasks. These are automated, conditional support assessments, not externally validated accuracy, corporate truth or legal compliance.

## Evidence architecture

| Panel | Inferential role | Measurement and denominator |
|---|---|---|
| a | Show the full distribution behind the primary mean | All 1,798 completed disclosure scores, equal disclosure weights; 5-percentage-point histogram bins, including 100% in the last bin. |
| b | Decompose the underlying claim inventory | Direct, inferred and unsupported counts pooled across all 94,955 deduplicated disclosure claims; claims have equal weight. |
| c | Show the scope of task variation | All 12 tasks in protocol order; equally weighted disclosure means and saved 95% company-cluster percentile intervals, with actual task sample sizes. |

Archetype: distribution with claim decomposition and a full-width task estimate
table. Panels a and b have equal plot dimensions. Panel c occupies the full grid
width and more height to retain all tasks and readable topic labels. It includes
label and value columns inside the axes rectangle; its numeric region explicitly
shows the complete 0–100% range. No task is selected based on its result.

## Numerical and interpretation contract

- Match disclosure IDs to the saved snapshot and execution-status record. Keep two incomplete cases excluded and listed; never impute zeros.
- Recompute score means, claim counts and proportions from the snapshot; verify against saved figure CSVs and the Results numerical record. All denominators include non-disclosure statements.
- Copy interval endpoints from saved analysis exports, classified `SOURCE_REPORTED`; preserve 2,000 company bootstrap draws, seed 20260921, 95% percentile definition and all selected disclosures within a resampled company. No new bootstrap run or hypothesis test is required.
- Mark recomputed descriptive values `COMPUTED_VERIFIED`. The task topic labels are concise paraphrases of the frozen task configuration, not new official requirements.
- Keep the 55.4% disclosure mean separate from the 55.1% pooled supported-claim proportion. The inferred share is relative to all claims, not only supported claims.
- This figure adds no literature claim or citation occurrence. Company resampling does not quantify extraction, judgment or model-run uncertainty, or the two missing assessments.

## Visual and export contract

Use the established Python backend and Matplotlib. Export editable vector PDF and
SVG at 180 × 154 mm and a 600 dpi PNG. Use 7 pt sans-serif labels and 8 pt panel
letters; no text below 6.5 pt. Embedded at the manuscript's 160 mm width, 6.5 pt
becomes 5.78 pt. Use blue for direct support and disclosure estimates, pale blue
for inferred support, and amber for unsupported claims. Explicit labels preserve
meaning without reliance on colour. Bars start at zero; no truncated data range,
smoothing, significance stars or accuracy language.

## Delivery gates

Save per-disclosure source data, histogram bins, pooled counts, task estimates,
omitted-case records, numerical provenance and the exact English legend under
`paper/analysis/fig2/`. Run the rendered alignment gate at 1.5 pt tolerance before
export, then source, PDF text-size and collision audits. Inspect every panel and
the figure with its legend in the manuscript. Rebuild the PDF and portable source
archive, preserving Results and Methods prose, and verify isolated compilation.
Automated and assistant visual checks do not constitute author scientific review.
