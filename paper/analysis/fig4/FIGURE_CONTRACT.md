# Figure 4 contract

Prepared: 2 October 2026. Target: Nature Sustainability, Article.

## Scientific question and claim

**Question:** How do native evaluator scores and claim inventories differ on the
same generated disclosures?

**Claim:** Native BACE support scores are lower than the native comparator
faithfulness scores in the common cohort, while the methods also construct
different claim inventories. These observations do not establish an accuracy
ranking or a causal explanation for the score differences.

## Evidence architecture

| Panel | Role | Measurement |
|---|---|---|
| a | Show the full native-score distributions | Three exact empirical cumulative distribution functions (ECDFs) on all 1,798 common disclosures; equally weighted disclosure scores. Legend reports arithmetic means. |
| b | Quantify within-disclosure contrasts | Mean BACE-minus-RAGChecker and BACE-minus-RAGAS differences, in percentage points, with the saved 95% company-cluster percentile intervals. |
| c | Expose the differing native inventories | Exact ECDFs of native claims per disclosure on the identical cohort; legend reports medians. Counts do not align claim meanings. |

Archetype: asymmetric quantitative grid. Panel a spans the left column; b and c
occupy the upper and lower right. This preserves the reading sequence a–b–c and
gives the primary distribution more height. The artwork is built anew, with
style and audit conventions inherited from earlier manuscript figures.

## Statistical and source contract

Match the saved scores and claim-count exports by unique generation-case ID to
the completed-case snapshot and execution record. Recompute means, medians and
within-disclosure differences, retaining all observations and actual missingness.
Exclude the two incomplete BACE cases from every panel without zero imputation;
do not mix the 1,800 comparator-only cohorts into any panel.

Save paired source rows, omissions, ECDF jump counts, method summaries and contrast
summaries under `paper/analysis/fig4/`. ECDFs count ties exactly and preserve all
1,798 observations; no binning, smoothing, jitter or subsampling. Every plotted
score/count must be finite and in its permitted range. Both ECDF axes show
cumulative percentage of disclosures, not a cumulative count of claims.

Use the saved paired-difference interval endpoints, classified `SOURCE_REPORTED`.
The original method resamples 30 companies with replacement, retains all their
disclosures, and uses 2,000 draws with seed 20260921 and 2.5th/97.5th percentiles.
Point estimates and distribution coordinates are `COMPUTED_VERIFIED`. Do not
derive paired uncertainty by subtracting marginal intervals or run new inference.
There are no hypothesis tests or significance markers in this figure.

## Interpretation limits

Pairing disclosures does not align native claim inventories or judgment inputs.
BACE uses its all-DC support metric, including non-disclosure statements; the
comparators retain their native faithfulness metrics. Lower scores do not prove
greater accuracy. Inventory counts do not quantify what caused the score gap.
Intervals describe company-resampling uncertainty, excluding extraction,
model-run, annotation and missing-case uncertainty. No human validation is implied.

## Visual and delivery contract

Use the established Python backend with Matplotlib. Export editable 180 × 138 mm
PDF/SVG and a 600 dpi PNG preview. Text is 6.5–7 pt, panel letters 8 pt; at the
manuscript's 160 mm width, 6.5 pt remains above the 5 pt floor. Use consistent
colour and line style for each method in a and c: BACE blue/solid, RAGChecker
amber/dashed, RAGAS purple/dotted. Panel b encodes comparator identity with colour
and distinct marker shape. Include zero on the difference axis and retain the
full score/count ranges in the ECDFs.

Run the strict final panel-alignment gate at 1.5 pt tolerances, source validation,
PDF glyph-size and collision checks, followed by visual inspection of every panel
and the embedded figure with its complete legend. Preserve the first three
artworks and imported Results/Methods prose. Replace the final figure placeholder,
rebuild the PDF and source ZIP, and verify isolated compilation. This completes
the four current main figures, not the manuscript or pending human assessment.
