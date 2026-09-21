# RAGChecker and RAGAS feasibility audit

Date: 6 September 2026

This audit checks released package source, dependencies, project schemas and existing E1 data. It does not report an executed external-evaluator pilot. No judge API calls were made and no packages were installed into the project environment.

## Assessment

Both frameworks can evaluate the available disclosures without generating a new set of answers. The required substantive inputs for their faithfulness metrics already exist. RAGAS faithfulness has low-to-moderate integration difficulty. RAGChecker has moderate integration difficulty because of its older dependency stack, provider interface, per-card checking and parsing behavior. A reliable 1,800-case comparison still needs input adapters, versioned judge configurations, intermediate-result logging and human validation.

The inspected releases are RAGChecker 0.1.9 and RAGAS 0.4.3. RAGChecker requires RefChecker >=0.2,<0.3; this audit inspected RefChecker 0.2.13. These versions are audit targets, not newly adopted experimental configuration.

## Existing project data

The complete E1 run inspected is:

- Input: `generation_inputs/w2_main_text_embedding_3_large_stratified_n10_top200/generation_cases.jsonl`.
- Output: `generation_outputs/w2_main_text_embedding_3_large_stratified_n10_top200/gpt_5_6_sol_run1/generated_disclosures.jsonl`.

| Property | Observed value |
|---|---|
| Input cases | 120 unique cases |
| Successful generated disclosures | 120 |
| Companies | 5 |
| Reporting years | 2018–2023 |
| Tasks | Four E1 tasks |
| Cases within the planned 2019–2023 window | 100 |
| Evidence cards per case | 26–30; median 30 |
| Generated response words, whitespace count | 339–443; median 400 |
| Recorded generation input tokens | 2,962–6,009; median 3,907 |
| Evidence text tokens using o200k_base | 1,844–4,890; median 2,846 |
| Largest individual evidence text using o200k_base | 1,099 tokens |
| Missing instructions or empty evidence texts | 0 |
| Unmatched output case IDs | 0 |
| Input prompt-hash or output-to-input prompt-hash mismatches | 0 |

The earlier Qwen-retrieval input set also contains 120 cases, with 88 successful generation records in its inspected run. These are separate retrieval settings and should not be pooled as one fixed-workflow main experiment.

The input files preserve `instruction`, `generation_prompt`, ordered `prompt_evidence`, card text, prompt-visible source labels and hashes. Outputs preserve `generation_case_id`, `generated_text`, model settings and usage. Inputs and outputs can therefore be joined without reconstructing corporate facts or running retrieval again.

Only E1 task specifications were found in `config/tasks`. The 30-company E1/S1/G1 matrix remains a design target. The current E1 cases are sufficient for an integration pilot, but not for a cross-standard pilot. No complete human claim-support benchmark was identified in the repository audit.

## Input mapping

| Project object | RAGChecker 0.1.9 | RAGAS 0.4.3 |
|---|---|---|
| `generation_case_id` | `query_id` | Retained as an external join key |
| `instruction` | `query` | `user_input` |
| Ordered prompt-visible evidence blocks | `retrieved_context`: objects with `doc_id` and `text` | `retrieved_contexts`: list of strings |
| `generated_text` | `response` | `response` |
| Expert reference disclosure | `gt_answer` for reference-dependent metrics | `reference` for reference-dependent metrics |

Use the instruction actually seen by the generator, including company, year and task. Do not put the entire generation prompt into the query field or introduce more detailed task requirements retrospectively.

Evidence serialization should preserve the factual text, visible source labels and relevant group context from the actual prompt. Hidden metadata such as retrieval scores and source fields not shown to the generator should not become additional evidence. Do not substitute BACE's extracted ECs or DCs for either framework's native input in the primary comparison.

RAGChecker's `RAGResult` constructor requires a `gt_answer` field even though faithfulness does not use it. An explicit empty string can serve as a schema placeholder for a run restricted to `metrics=["faithfulness"]`. It is not an expert answer. Calling `all_metrics` with that placeholder would not produce interpretable reference-based results.

## Metric eligibility

| Metric | Additional requirements | Current status |
|---|---|---|
| RAGChecker faithfulness | Claim extractor and entailment judge | Data ready; runtime not integrated |
| RAGChecker precision, recall, F1 | Expert reference answer | Reference unavailable |
| RAGChecker claim recall, context precision, context utilization | Expert reference answer and related entailment results | Reference unavailable |
| RAGChecker noise sensitivity, hallucination, self-knowledge | Reference-answer comparisons | Reference unavailable |
| RAGAS Faithfulness | Judge LLM; no embeddings required | Data ready; runtime not integrated |
| RAGAS AnswerRelevancy | Judge LLM and embedding model | Input data ready; metric configuration and construct validation pending |
| RAGAS ContextPrecisionWithoutReference / ContextUtilization | Query, generated response, contexts and judge | Technically eligible; interpretation differs from task coverage |
| RAGAS reference-based ContextPrecision, ContextRecall or answer correctness | Expert reference answer or the metric's required reference data | Reference unavailable |

RAGAS AnswerRelevancy generates questions from the response and compares their embeddings with the original input. A long ESRS drafting instruction is different from the short QA inputs motivating this metric. Its score requires calibration against human task relevance; it cannot establish that all ESRS disclosure elements were covered. Existing retrieval embeddings do not automatically constitute the query/answer embeddings needed by this metric.

RAGAS context precision without a reference uses the generated response as its anchor and computes an order-sensitive average precision. The project groups evidence by type in the prompt, so this score describes that presented order unless another order is explicitly defined. It is neither a reference-independent completeness measure nor BACE's EC coverage rate.

## A consequential methodological difference

RAGChecker 0.1.9 passes the retrieved cards separately to its checker for `retrieved2response`, with `merge_psg=False`. The faithfulness computation takes the maximum entailment value across cards for each response claim. A claim counts as faithful when at least one card individually supports it.

Its default `joint_check=True` groups five claims per checking prompt. It does not combine the evidence cards into a joint premise set. The inspected extractor also defaults to triplet-form claims, introducing another representational difference from BACE's self-contained EC/DC statements.

RAGAS 0.4.3 Faithfulness joins all supplied context strings before checking its generated statements. It can therefore expose the judge to premises distributed across cards, although whether the model reasons correctly remains an empirical question.

For example, if one card supplies Scope 1 emissions and another supplies Scope 2 emissions, a claim reporting their sum may need both cards. Failure of a card-wise checker on that claim would reflect its available premise unit as well as entailment quality. It would not by itself establish the value of BACE's boundary rules.

Recommended pilot conditions are native card-wise RAGChecker and native RAGAS Faithfulness on the same cases. Include a clearly labelled merged-context RAGChecker sensitivity condition for a subset of cross-card support cases, using only the same prompt-visible content. Preserve the native primary comparison and report the changed context unit. Combined with claim-alignment analysis, this helps distinguish evidence segmentation from support-judgment differences.

This difference gives RAGAS Faithfulness a concrete reason to be piloted alongside RAGChecker. Inclusion in the full experiment should still follow the documented pilot decision.

## Environment and provider integration

The project `.venv` currently uses Python 3.13.14, with OpenAI 2.47.0, Pydantic 2.13.4, tiktoken 0.13.0, PyTorch 2.12.1 and Transformers 5.12.1. RAGChecker, RefChecker, RAGAS, LiteLLM and spaCy were not installed in that environment. Neither evaluator was found in project requirements or evaluation scripts/configurations.

RefChecker 0.2.13 requires `transformers>=4.41,<5`, which conflicts with the installed Transformers 5.12.1. It also depends on spaCy, LiteLLM and older bounded versions of other libraries. Its text processing loads the `en_core_web_sm` spaCy model. Use a separate, pinned evaluation environment; a Python 3.11 environment is a reasonable compatibility starting point to verify. API-based judging does not require a local GPU, even though the dependency stack includes local-model libraries.

The project generation and BACE scripts currently use an Azure-configured Responses interface. RefChecker's default provider path uses LiteLLM chat completions; RAGAS's inspected Instructor-based path uses a chat-completions interface. Existing credentials and deployments cannot be assumed to work with those paths without a provider smoke test.

RAGChecker exposes `custom_llm_api_func`, which accepts a batch of prompts and returns response strings. This offers a way to reuse an existing provider transport while preserving the framework's native prompts, extraction and checking logic. RAGAS needs a supported structured-output client or a suitable adapter. Judge model and deployment, parameters, token limits and transport behavior must be recorded. Selecting a different judge model family from the generator remains a methodological choice to resolve.

## Runtime and observability

The inspected E1 contexts do not suggest an immediate context-window barrier for a suitably selected judge. New S1/G1 cases may differ, and evaluator prompts, extracted claims and output budgets must be included in the token calculation.

RAGChecker's cost can be driven by card-by-claim comparisons. With C cards, M extracted claims and the default group size of five, its LLM checker produces approximately `C * ceil(M / 5)` prompts per case, plus extraction. As an illustrative calculation, 30 cards and 40 claims produce 240 checking prompts per case. This is not an observed RAGChecker claim count or a monetary estimate. Provider batching and concurrency affect latency, not the underlying number of prompts.

RAGAS Faithfulness makes two logical LLM calls per case in the inspected implementation: statement generation and statement checking. The second call includes the concatenated evidence and all statements. Retries and structured-output repair can increase the actual number of requests.

The pilot should record raw responses, parsed claims, per-claim verdicts, parsing status, token usage, cost and latency. Specific behaviors to address include:

- RAGChecker's default extractor output budget is 1,000 tokens. Verify complete extraction rather than assuming successful parsing implies completeness.
- RefChecker's joint checker pads missing parsed labels with `Neutral` and truncates excess labels. Track these events so parser failures do not silently become support judgments.
- RAGAS Faithfulness returns a scalar `MetricResult`; its intermediate statements, reasons and verdicts need tracing or wrapper capture for claim-level comparison.
- RAGChecker returns 0 when its faithfulness input has no claims; RAGAS returns NaN when no statements are generated. Define a shared invalid-case policy before comparing aggregate scores.
- RAGChecker stores per-case faithfulness on a 0–1 scale but reports aggregate percentages rounded to one decimal. Recompute comparisons from per-case values on a consistent scale.

## Recommended next integration step

Build one case adapter and separate evaluator runners. Start with roughly 8–12 E1 cases from the existing 2019–2023 subset, spanning all four tasks and both typical and long contexts. This is an engineering pilot recommendation, not a validation sample-size calculation. Inspect numerical claims, non-disclosure statements and cases requiring evidence from several cards.

Run RAGChecker faithfulness and RAGAS Faithfulness with native claim extraction. Check reference-free execution, provider compatibility, extraction completeness, intermediate logging and runtime. Use a small merged-context sensitivity check to diagnose cross-card disagreements. Add AnswerRelevancy only if it answers a distinct question and agrees with an appropriate human relevance rubric.

After this pilot, select and freeze the full-run configurations and decide RAGAS inclusion. Expand to E1/S1/G1 only after the corresponding tasks and evidence pipeline exist. Human validation is still required to interpret the automated comparison; schema compatibility alone does not establish evaluator validity.

## Sources and local evidence

- [RAGChecker 0.1.9 release](https://pypi.org/project/ragchecker/0.1.9/): wheel source inspected, especially `container.py`, `metrics.py`, `evaluator.py` and `computation.py`.
- [RefChecker 0.2.13 release](https://pypi.org/project/refchecker/0.2.13/): wheel dependency metadata, extractor, checker and provider utility source inspected.
- [RAGAS 0.4.3 release](https://pypi.org/project/ragas/0.4.3/): wheel source inspected, especially collections-based faithfulness, answer relevancy, context precision and LLM transport.
- [RAGAS Faithfulness documentation](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/).
- [RAGAS Answer Relevancy documentation](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/).
- [RAGAS Context Precision documentation](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/).
- [Generation input builder](../../_archive/previous_stage_20260921/script/rag/build_w2_generation_inputs.py), [generation runner](../../_archive/previous_stage_20260921/script/generation/run_w2_generation.py), [requirements](../../_archive/previous_stage_20260921/requirements.txt), and [project framework](project_framwork_v2.md).

Verification boundary: package-source and metadata inspection, local environment inventory, JSONL schema and join checks, prompt-hash validation, and token-length measurements. Native framework execution, provider authentication, model output quality, observed judge cost and end-to-end runtime remain untested.
