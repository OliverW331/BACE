# Figure 2 legend

**Evidentiary support across disclosure tasks.**
**a,** Distribution of BACE-assessed support across 1,798 completed disclosures from 30 companies, using 5-percentage-point bins. Each disclosure's score is its number of directly or inferentially supported disclosure claims (DCs) divided by all its deduplicated DCs. The dashed line marks the equally weighted disclosure mean of 55.4% (95% confidence interval, 53.9–56.8%).
**b,** Pooled composition of all 94,955 DCs; labels give category percentages and counts. Direct and inferred support together comprise 52,309 DCs (55.1%). This panel weights claims equally, whereas panels a and c weight disclosures equally. All denominators retain non-disclosure statements.
**c,** Means and horizontal 95% confidence intervals for all 12 tasks in protocol order, with abbreviated task topics. The n column gives completed disclosures: 149 for S1-1 and S1-5 and 150 for each remaining task; every task includes 30 companies. Intervals in a and c are the saved percentile company-cluster bootstrap intervals from 2,000 resamples, retaining all disclosures within each sampled company. Two incomplete assessments are excluded without zero imputation. Task variation is descriptive; no hypothesis test is reported. BACE verdicts are conditional on the supplied evidence, extracted claims and selected candidate evidence. These intervals describe company-resampling uncertainty, not the validity or model-run variability of those verdicts.

## Provenance

Prepared: 2 October 2026. This legend is synchronized with `main.tex` by a
caption-content audit. It introduces no new citation occurrence.

| Content | Saved record | Aggregation and status |
|---|---|---|
| Histogram and mean | `disclosures.csv`, `histogram.csv`, `verified_facts.json` | All completed disclosure scores; mean and bin counts `COMPUTED_VERIFIED`. |
| Pooled composition | `claim_composition.csv` | Sum category DC counts over the same disclosures; counts and shares `COMPUTED_VERIFIED`. |
| Task means and n | `task_estimates.csv` | Arithmetic mean within each task; actual nonmissing count, `COMPUTED_VERIFIED`. |
| Overall and task intervals | `verified_facts.json`, `task_estimates.csv` | Copied saved exports, `SOURCE_REPORTED`; no bootstrap rerun. |
| Missing cases | `excluded_cases.csv` | Two incomplete assessments listed by actual company, year and task; no score imputation. |

Input paths, hashes, interval locators, software versions and rendering command
are recorded in `provenance.json`. Bootstrap configuration is 2,000 draws with
seed 20260921; the original function is
`BACE/analysis/analysis_data.py::company_bootstrap`. All panel data are derived
from the same saved snapshot and verified against the original figure exports.
Histogram bins are left-closed and right-open, except the final bin includes
100%. Bin assignments are checked against exact integer supported/all-DC ratios
to prevent floating-point boundary misclassification. The counts represent
model-extracted, deduplicated claims, not an
independently validated inventory. Human validation remains pending.
