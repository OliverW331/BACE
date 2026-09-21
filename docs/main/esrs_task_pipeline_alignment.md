# Shared E1, S1 and G1 task structure and execution

Date: 2026-09-16. Status: configuration integration checked offline; expanded retrieval and generation have not been run.

## Experimental unit

Each task is an independent disclosure topic. For one company and reporting year, the four E1 tasks create four separate retrieval cases and four separate generation inputs. One task's disclosure is not passed to another task as evidence. The tasks are not four sequential stages or four evaluation metrics.

The recorded E1 input manifest contains 120 cases: five companies, six years (2018-2023), and four tasks. The planned expanded matrix is 30 companies, five years (2019-2023), and twelve tasks, yielding 1,800 disclosure cases. The task-spec year list is descriptive: the retrieval CLI's `--target-years` and the available package manifests determine the actual case years.

## The same pipeline for every task

1. Load a task record and a company-year evidence-package manifest.
2. Render two or three explicit, deterministic retrieval subqueries from the task's information needs. A query is an evidence-seeking request, not a writing instruction.
3. Apply the same company and manifest-defined source-year boundaries and the same retrieval configuration. The current main workflow uses BM25 plus `text_embedding_3_large`, with reciprocal-rank fusion. Its final selection takes up to ten cards of each type: narrative, PDF table row and CSV metric, at most thirty cards. Missing strata are not filled by increasing another stratum's quota.
4. Render the shared generation instruction with company name, reporting year and task title, followed by the selected evidence in the order narrative, PDF table row, CSV metric. Prompt labels are `Evidence 1`, `Evidence 2`, etc.; stable evidence IDs remain in the mapping metadata. The instruction requests a 300-500 word corporate-report disclosure section using only the supplied evidence. There is no task-specific generation prompt.
5. Generate one disclosure using the same model and generation settings chosen for the experiment.
6. Evaluate the disclosure against its own prompt-visible evidence using the same selected BACE configuration. EC/DC extraction, deduplication, candidate selection, support assessment and unsupported diagnosis operate within that case. RAGChecker and RAGAS receive the same case's visible evidence and generated response through their common adapter, using their own native evaluation methods.

The same procedure, source eligibility rules, evidence budget, model settings and evaluation versions must apply to all three standards in a comparative run. Domain-specific information needs and retrieved content vary by task. The four topics within each standard do not need a forced one-to-one semantic correspondence with the other standards.

## What task fields actually do

| Fields in the E1 task record | Current implementation role |
|---|---|
| `task_id` | Selects the task, keys the query bundle, identifies cases and supports filtering and aggregation |
| `esrs_reference`, `task_name` | Supply query metadata and the generation `task_title` |
| `expected_evidence_content`, `query_facets` | Fill the explicit retrieval templates; expected content also appears in retrieval review metadata |
| `retrieval_intent` | Available as a retrieval-template placeholder; it affects queries only if a template references it |
| `expected_evidence_types` | Included in retrieval review metadata; it does not replace the global eligible types or allocate task-specific quotas |
| `task_scope`, selection rationale, official basis, evidence-availability rationale | Document the task's substantive definition and justification |
| `generation_intent` | Design metadata; the actual generator instruction comes from the shared generation template |
| `claim_type_coverage`, `claim_risk_notes` | Research metadata; not a special generation instruction or an automatic BACE scoring rubric |
| `evidence_type_coverage_rule`, status fields | Task-spec metadata; the current retrieval runner does not enforce the task's `required_for_sanity_check` list as a case-admission gate |

The `targeted_claim_risks` field in the query-template file is also metadata: the template loader keeps the subquery ID, evidence need and template text. Any substantive distinctions intended to guide retrieval must appear in the actual query text.

Task definitions, retrieval templates and generation instructions are therefore separate configuration layers. Adding a task specification alone would let an unknown task fall back to the generic one-query template; that would not reproduce E1's explicit multi-query treatment. The expanded bundle provides explicit subqueries for all twelve tasks.

## Aligned configurations

The S1 and G1 files have exactly the same top-level, design-note, per-task and evidence-rule field sets as the existing E1 file. Official source locators and broader research discussion remain in [the selection research memo](esrs_s1_g1_task_selection_research.md). The eight new task choices retain draft status.

| Configuration | Purpose |
|---|---|
| [Existing E1 tasks](../../_archive/previous_stage_20260921/config/tasks/esrs_e1_task_specs.json) | Existing four task definitions |
| [S1 tasks](../../_archive/previous_stage_20260921/config/tasks/esrs_s1_task_specs.json) | Four S1 definitions using the E1 structure |
| [G1 tasks](../../_archive/previous_stage_20260921/config/tasks/esrs_g1_task_specs.json) | Four G1 definitions using the E1 structure |
| [Combined task specification](../../_archive/previous_stage_20260921/config/tasks/esrs_e1_s1_g1_task_specs.json) | One input file for all twelve tasks; E1 task records copied unchanged |
| [Expanded query templates](../../_archive/previous_stage_20260921/config/prompts/retrieval_query_bundle_templates_e1_s1_g1_v1.json) | Original E1 templates plus explicit S1/G1 subqueries |
| [Shared generation template](../../_archive/previous_stage_20260921/config/prompts/generation_prompt_templates.json) | Existing generation instruction and evidence presentation for every task |
| [Shared retrieval configuration](../../_archive/previous_stage_20260921/config/retrieval/retrieval_algorithm_config_text_embedding_3_large_top200_v1.json) | Existing ranking and evidence-selection settings |

The identifiers use the original 2023 ESRS edition, consistent with the existing E1 records. The 2026 revision changes several meanings and identifiers; its implications are documented in the research memo.

For an expanded retrieval run, supply the combined file through `--task-spec`, the expanded bundle through `--query-bundle-template`, all twelve requested `--task-ids`, and the common 2019-2023 `--target-years`. Keep the existing embedding choice and ranking configuration. Package manifests and embeddings must contain the source-audited expanded evidence pool. The task configuration itself does not rebuild or validate those artifacts.

For generation-input construction, use the same combined `--task-spec` and the existing `--generation-template`, with the same `stratified_by_evidence_type_n10` setting and the expanded retrieval results. The existing title resolver reads task names from the specification, so new hardcoded titles or a separate S1/G1 generator are unnecessary. Evaluation run inputs and case selection must point to those newly generated cases; the historical ten-case external pilot configuration is not an automatic expanded-run configuration.

## Verification and remaining work

[The offline check](esrs_task_pipeline_alignment_check.json) exercised the existing retrieval and generation loaders, query renderer, generation-case builder and native external-evaluator adapter for two synthetic company-years and all twelve tasks (24 cases). It checked explicit subqueries, placeholder substitution, unique cases, shared instructions, evidence labels and hashes. It also confirmed that the E1 task records, rendered queries and generation cases remain identical when the combined configurations are used.

No model calls were made. This check verifies configuration and input compatibility. Evidence availability, source-to-card validity, retrieval relevance, generated disclosures and evaluation quality still require the expanded pilot. Any source-quality rule adopted for that pilot should apply consistently across E1, S1 and G1.

Implementation references: `build_cases` and `render_query_bundle` in [the retrieval runner](../../_archive/previous_stage_20260921/script/rag/run_w2_retrieval_sanity_check.py); `resolve_task_title` and `build_generation_case` in [the generation-input builder](../../_archive/previous_stage_20260921/script/rag/build_w2_generation_inputs.py); `adapt_case` in [the external-evaluation adapter](../../_archive/previous_stage_20260921/script/evaluation/external_evaluation.py).
