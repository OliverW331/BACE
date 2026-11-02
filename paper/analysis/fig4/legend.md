# Figure 4 legend

**Native evaluator scores and claim inventories.**
All panels use the same 1,798 completed disclosures from 30 companies. Two incomplete BACE assessments are excluded throughout without zero imputation.
**a,** Empirical cumulative distributions of native scores; each step gives the percentage of disclosures at or below the displayed value. Legends report arithmetic mean scores. BACE uses its all-disclosure-claim support rate, including non-disclosure statements; RAGChecker and RAGAS retain their native faithfulness scores.
**b,** Mean within-disclosure score differences, calculated as BACE minus each comparator, in percentage points. Squares identify RAGChecker and triangles RAGAS. Horizontal bars show saved 95% percentile company-cluster bootstrap intervals from 2,000 resamples, retaining all disclosures within each sampled company. Labels give means and interval limits; the dashed line marks zero difference. No hypothesis test is reported.
**c,** Empirical cumulative distributions of native claim counts on the identical cohort, with medians in the legend. The cumulative percentage refers to disclosures, not claims. Both distributions retain every observation and count ties exactly, without smoothing or subsampling. Pairing disclosures does not align the methods' claim inventories or judgment procedures. Score gaps and inventory sizes do not establish comparative accuracy or a causal explanation for the gaps. The intervals capture company-resampling uncertainty, not model-run variability or judgment validity.

## Provenance

Prepared: 2 October 2026. This legend is synchronized with `main.tex`.

| Content | Saved record | Status and aggregation |
|---|---|---|
| Common cohort and all panel inputs | `paired_disclosures.csv`, `excluded_cases.csv` | Unique case-ID intersection checked against the completed snapshot and execution record; no comparator-only additions. |
| Means and claim-count medians | `method_summaries.csv` | `COMPUTED_VERIFIED`; arithmetic means of native scores and medians of native counts over 1,798 disclosures. |
| Exact distribution steps | `ecdf_coordinates.csv` | `COMPUTED_VERIFIED`; frequencies of tied values, cumulative counts and common denominator. |
| Paired score gaps | `paired_differences.csv` | Means `COMPUTED_VERIFIED`; saved interval endpoints `SOURCE_REPORTED`. |

The original numerical function is
`BACE/analysis/analysis_data.py::company_bootstrap`, using seed 20260921 and
2,000 draws. The original analysis constructs each paired difference before
calling that function. Interval endpoints are copied from
`03_native_comparison__paired_differences.csv`; no marginal-interval subtraction,
new bootstrap run or hypothesis test is performed. Inputs, hashes, commands and
software versions are in `provenance.json`.

The figure introduces no new literature citation occurrence. Native method
definitions remain in the existing Methods section and its verified citations.
The completed automated assessments are distinct from the pending independent
human study; no accuracy estimate is inferred from these distributions.
