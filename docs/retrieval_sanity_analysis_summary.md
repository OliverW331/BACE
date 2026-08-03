# Retrieval Sanity Analysis Summary

## Scope and Source Tables

This report summarizes the retrieval sanity run outputs under `evidence_pilot/retrieval_runs/_analysis_outputs/tables/`, with supporting checks from the combined case and task summaries.

Primary source tables:

- `summary_evidence_type_coverage.csv`
- `summary_global_vs_stratified_paired_settings.csv`
- `summary_diagnostic_model_score.csv`
- `summary_pairwise_model_overlap_jaccard.csv`
- `diagnostic_risk_cases.csv`

Supporting combined outputs:

- `evidence_pilot/retrieval_runs/_combined/combined_retrieval_summary_by_case.csv`
- `evidence_pilot/retrieval_runs/_combined/combined_retrieval_summary_by_task.csv`

Important interpretation note: the diagnostic metrics in these tables are sanity and coverage metrics only. They do not measure true retrieval relevance, factual usefulness, or whether a card is the best evidence for a W2 answer. They check whether the retrieval package is populated, balanced across expected evidence types, and free from obvious coverage failures.

## Experiment Setup

The sanity run evaluates two retrieval selection families:

1. `global_topk`: a single globally ranked top-k selection.
2. `stratified_per_type`: separate per-evidence-type selection for CSV metric, PDF narrative, and PDF table-row evidence.

The evaluated selection settings are:

- `global_top_k_30`
- `global_top_k_45`
- `global_top_k_60`
- `stratified_by_evidence_type_n10`
- `stratified_by_evidence_type_n15`
- `stratified_by_evidence_type_n20`

The evaluated embedding models are:

- `qwen3_0_6b` / Qwen3-Embedding-0.6B
- `bge_m3` / BGE-M3
- `snowflake_m_v1_5` / Snowflake Arctic Embed
- `nomic_v1_5` / Nomic Embed Text v1.5
- `e5_large_instruct` / multilingual-e5-large-instruct
- `text_embedding_3_small` / OpenAI text-embedding-3-small

The case grid covers 5 companies, 6 target reporting years, and 4 ESRS E1 W2 task families:

- `E1-1_transition_plan`
- `E1-3_actions_resources`
- `E1-4_targets`
- `E1-6_ghg_emissions`

This gives 120 cases per model-setting combination.

## Completeness Check

The run grid appears complete. The combined case table contains 4,320 rows, matching:

`6 models x 6 selection settings x 120 cases = 4,320 case-level outputs`

The combined task table contains 144 rows, matching:

`6 models x 6 selection settings x 4 tasks = 144 task-level outputs`

No task-level no-result failures were found. The combined task summaries report `cases_with_no_results = 0` across the run.

Global top-k count completeness is very strong:

- `global_top_k_30`: all 720 model-case rows returned 30 cards.
- `global_top_k_45`: all 720 model-case rows returned 45 cards.
- `global_top_k_60`: 715 of 720 model-case rows returned 60 cards.

The 5 global top-k shortfalls all occur for `Genmab`, target year `2022`, task `E1-6_ghg_emissions`, and non-Qwen models. These rows returned 54 to 57 cards instead of 60. This is a small abnormality worth checking, but it does not indicate a broad run failure.

The stratified settings often return fewer than the theoretical maximum of `3 x per_type_n`. This is expected under the current no-deficit-redistribution design when one evidence-type stratum cannot provide enough cards. It should be interpreted as a coverage diagnostic rather than an execution failure.

## Global Top-k vs Stratified Per-type

The two retrieval families show different strengths.

`global_topk` is more stable if stability means filling the requested card count and producing more similar results across embedding models. Mean pairwise model Jaccard overlap is higher for global top-k:

- `global_top_k_30`: mean Jaccard about 0.507
- `global_top_k_45`: mean Jaccard about 0.531
- `global_top_k_60`: mean Jaccard about 0.543

By comparison, stratified settings show lower pairwise overlap:

- `stratified_by_evidence_type_n10`: mean Jaccard about 0.405
- `stratified_by_evidence_type_n15`: mean Jaccard about 0.430
- `stratified_by_evidence_type_n20`: mean Jaccard about 0.448

However, `stratified_per_type` is more stable if stability means evidence-type coverage and balance. Global top-k heavily favors CSV metric cards. The coverage table shows that global top-k usually retrieves CSV metrics for every case but often misses PDF narrative or PDF table-row evidence.

Examples from `summary_evidence_type_coverage.csv`:

- BGE-M3 at `global_top_k_30`: average 27.09 CSV metric cards, 1.81 PDF narrative cards, and 1.10 PDF table-row cards; 74 cases without PDF narrative and 78 without PDF table rows.
- Snowflake Arctic Embed at `global_top_k_30`: average 27.60 CSV metric cards, 2.29 PDF narrative cards, and 0.11 PDF table-row cards; 109 cases without PDF table rows.
- Qwen3 at `global_top_k_30`: average 21.22 CSV metric cards, 2.72 PDF narrative cards, and 6.07 PDF table-row cards; better than most global settings, but still 36 cases without PDF narrative and 13 without PDF table rows.

The paired comparison table shows that stratification sharply reduces imbalance. At the 30-card setting for Qwen3:

- Global top-k 30 average counts: 21.22 CSV, 2.72 narrative, 6.07 table-row.
- Stratified 10/type average counts: 10.00 CSV, 8.68 narrative, 9.89 table-row.
- Average imbalance falls from 20.04 to 1.39.
- Missing-any-type cases fall from 49 to 0.

For W2 generation, this evidence-type balance is important because the generation prompt should see both structured metrics and textual/table evidence rather than only the cards that dominate a single global ranking.

## Model Comparison

Qwen3-Embedding-0.6B is the strongest model from a diagnostic coverage perspective.

Mean diagnostic scores by model:

| Model | Mean diagnostic score | Global mean | Stratified mean |
|---|---:|---:|---:|
| Qwen3-Embedding-0.6B | 0.812 | 0.854 | 0.771 |
| Nomic Embed Text v1.5 | 0.710 | 0.804 | 0.616 |
| OpenAI text-embedding-3-small | 0.630 | 0.744 | 0.515 |
| BGE-M3 | 0.591 | 0.707 | 0.475 |
| multilingual-e5-large-instruct | 0.588 | 0.737 | 0.438 |
| Snowflake Arctic Embed | 0.553 | 0.686 | 0.420 |

The strongest individual diagnostic rows are:

| Rank | Model | Setting | Diagnostic score |
|---:|---|---|---:|
| 1 | Qwen3-Embedding-0.6B | Global top-k 60 | 0.883 |
| 2 | Qwen3-Embedding-0.6B | Global top-k 45 | 0.859 |
| 3 | Qwen3-Embedding-0.6B | Stratified 10/type | 0.855 |
| 4 | Nomic Embed Text v1.5 | Global top-k 60 | 0.835 |
| 5 | Qwen3-Embedding-0.6B | Global top-k 30 | 0.819 |

These scores should not be read as relevance scores. For example, `global_top_k_60` can score highly because it fills the requested count and includes more evidence types at larger k, even if it still over-represents CSV metric cards. The diagnostic ranking is therefore best used to detect retrieval-package coverage quality, not final evidence quality.

Qwen3 is also the only model with zero missing evidence-type cases across the Qwen stratified settings. Under `stratified_by_evidence_type_n10`, Qwen3 has:

- 0 cases without CSV metric evidence
- 0 cases without PDF narrative evidence
- 0 cases without PDF table-row evidence
- average retrieved count of 28.57 out of a maximum 30
- average evidence-type imbalance of 1.39

Nomic Embed Text v1.5 is the strongest runner-up. It performs well under global top-k and has better balanced coverage than BGE-M3, Snowflake, E5, and OpenAI in several settings, but it still has missing PDF narrative and table-row cases under stratified retrieval.

## Task-level Diagnostics

The task-level outputs indicate that all four W2 task families are covered for every model-setting combination. Each task summary has 30 cases per model-setting, matching 5 companies x 6 years.

Risk diagnostics are not evenly distributed across tasks. `diagnostic_risk_cases.csv` shows the most risk rows for:

| Task | Risk rows |
|---|---:|
| `E1-6_ghg_emissions` | 964 |
| `E1-4_targets` | 917 |
| `E1-3_actions_resources` | 734 |
| `E1-1_transition_plan` | 614 |

`E1-6_ghg_emissions` is the main task to inspect manually. It accounts for the largest number of risk rows and the largest share of highest-severity risk rows. This is plausible because GHG emissions retrieval can be dominated by CSV metric cards, while narrative/table context may be sparse or harder to rank.

The most frequent high-severity risk pattern is an evidence package that contains only or almost only CSV metric cards, especially for global top-k settings or weaker models under stratified settings.

## Risk Cases

The diagnostic risk table contains 3,229 risk rows. The most common risk flags are:

- `risk_shortfall`: 1,752 rows
- `risk_missing_pdf_table_row`: 1,526 rows
- `risk_extreme_type_dominance`: 1,308 rows
- `risk_missing_pdf_narrative`: 784 rows
- `risk_missing_csv_metric`: 0 rows
- `risk_e1_6_low_structured`: 0 rows

The absence of `risk_missing_csv_metric` means the retrieval system consistently finds CSV metric evidence. The recurring problem is the opposite: PDF narrative and PDF table-row evidence can be under-represented or missing.

Highest-severity `risk_score = 3` rows are concentrated in:

| Dimension | Main concentration |
|---|---|
| Retrieval family | `global_topk` |
| Setting | `global_top_k_30`, then `global_top_k_45` |
| Models | BGE-M3, Snowflake Arctic Embed, OpenAI text-embedding-3-small, E5 |
| Companies | Mercedes-Benz Group, Admiral Group, Informa |
| Task | `E1-6_ghg_emissions` |

For Qwen3 specifically, risks are substantially lower:

- `global_top_k_30`: 65 risk rows, including 4 score-3 rows.
- `global_top_k_45`: 44 risk rows, no score-3 rows.
- `global_top_k_60`: 23 risk rows, no score-3 rows.
- `stratified_by_evidence_type_n10`: 36 risk rows, all score 1 and all due to shortfall only.
- `stratified_by_evidence_type_n15`: 54 risk rows, all score 1 and all due to shortfall only.
- `stratified_by_evidence_type_n20`: 80 risk rows, all score 1 and all due to shortfall only.

This matters because Qwen3 stratified risks are not missing-modality risks. They are mostly cases where the stratified package does not fill all possible slots because one stratum has fewer retrieved cards than the quota. For W2 generation, that is less concerning than a package that fills all slots but omits narrative or table-row evidence.

Manual review should prioritize:

1. `Genmab 2022 E1-6_ghg_emissions` global top-k 60 shortfalls for non-Qwen models.
2. `E1-6_ghg_emissions` cases with only CSV metric cards.
3. Mercedes-Benz Group, Admiral Group, and Informa high-severity risk rows.
4. Snowflake and BGE-M3 cases missing PDF table-row evidence.
5. Qwen3 stratified shortfall cases only as a lighter check, especially where retrieved count drops far below the nominal maximum.

## Recommended Setting for Main W2 Generation

Recommended main setting:

`qwen3_0_6b` with `stratified_by_evidence_type_n10`

This corresponds to 10 cards per evidence type, with a maximum of 30 cards per case.

Rationale:

- It is consistent with the stratified retrieval configuration's intended main generation setting.
- It gives the best balance across CSV metric, PDF narrative, and PDF table-row evidence.
- It has zero missing evidence-type cases for Qwen3.
- Its diagnostic score is high at 0.855, nearly matching the top global settings.
- Its risk rows are all low-severity shortfall flags, not missing-modality failures.
- It avoids the strong CSV dominance observed in global top-k retrieval.

`qwen3_0_6b` with `global_top_k_60` can be kept as a robustness or sensitivity condition. It has the highest diagnostic score, but this is partly because it fills a larger card budget. It still shows CSV dominance and some missing narrative/table cases, so it is not the best main setting if the goal is balanced W2 evidence coverage.

## Limitations

This sanity analysis does not establish true retrieval relevance. The diagnostics measure coverage, balance, count completeness, and obvious missing-evidence-type patterns. They do not answer whether:

- the retrieved evidence is substantively correct for the W2 question;
- the best available evidence was retrieved;
- the evidence supports the final generated answer;
- the retrieval ranking is optimal;
- the evidence is temporally or contextually sufficient beyond the hard filters;
- PDF narrative/table cards contain the exact disclosure needed for a task.

A setting can score well diagnostically while still retrieving weak or tangential evidence. Conversely, a setting can have a shortfall but still retrieve highly useful evidence. For that reason, the recommendation should be treated as a retrieval-input construction choice for the main W2 generation experiment, not as proof of retrieval relevance.

The next validation layer should manually inspect selected high-risk cases and a small sample of recommended Qwen3 stratified cases to confirm that the retrieved evidence is actually usable for generation.