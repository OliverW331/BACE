# Ready-weight candidates for a BACE evaluation-only extension

Access date: 2 November 2026.

## Decision boundary

Here, free means that released weights can be obtained without purchasing a
model license, subject to the applicable terms. Ready means that the candidate
does not require new user-side training before inference. Neither term means
free GPU compute, an unlimited free hosted API, or drop-in compatibility with
the frozen BACE implementation. No model was downloaded or executed.

The availability checks used unauthenticated Hugging Face metadata requests
and HTTP HEAD requests to one listed weight artifact per accessible repository.
The observations and inspected repository revisions are saved in
`availability_checks.json`. A successful HEAD verifies access to that URL, not
a complete download, runtime compatibility, or evaluator validity.

All general-purpose candidates remain `BACE_COMPATIBILITY_UNTESTED` and
`BACE_PERFORMANCE_UNMEASURED`. Priorities are proposed study-design choices,
not a performance ranking.

## General-purpose candidates

| Priority | Exact checkpoint | Weight license | Anonymous weight URL | Proposed role | Literature relationship |
| --- | --- | --- | --- | --- | --- |
| First-pass candidate | `Qwen/Qwen3-30B-A3B-Instruct-2507` | Apache-2.0 | Accessible | General-purpose full-pipeline pilot; non-thinking instruction model | Judge's Verdict Table 4 includes this checkpoint as an Answer Accuracy judge; this is indirect precedent, not evidence-faithfulness validation |
| First-pass candidate | `openai/gpt-oss-20b` | Apache-2.0 | Accessible | Different-family reasoning evaluator; requires correct Harmony formatting and final-channel parsing | Judge's Verdict Table 4 includes this checkpoint; indirect Answer Accuracy precedent |
| First-pass diversity candidate | `google/gemma-4-31B-it` | Apache-2.0 | Accessible | Different-family current-model extension | No exact-version evaluator precedent established in the inspected paper set; Gemma 3 precedent must not be attributed to Gemma 4 |
| Literature-anchored large candidate | `Qwen/Qwen2.5-72B-Instruct` | Custom Qwen license, not Apache-2.0 | Accessible | Larger prompted evaluator after hardware feasibility checks | FaithJudge Table 2 evaluates Qwen2.5 72B hallucination judging; model-family/size precedent rather than reproduction of its demonstration protocol |
| Intermediate-size alternative | `Qwen/Qwen2.5-32B-Instruct` | Apache-2.0 | Accessible | Non-thinking dense alternative | Judge's Verdict Table 4 includes this checkpoint; indirect Answer Accuracy precedent |
| Reasoning-size alternative | `Qwen/Qwen3-14B` | Apache-2.0 | Accessible | Smaller reasoning model; choose and record thinking mode | RLSeek Section 5.1 and Table 1 use prompted Qwen3-14B-CoT and CoT-Seek, distinct from the paper's trained RLSeek models |
| Current-model alternative | `Qwen/Qwen3.8-27B` | Apache-2.0 | Accessible | Current-model extension within the Qwen family | No exact-version evaluator precedent established in the inspected paper set |
| Small-size control | `Qwen/Qwen2.5-7B-Instruct` | Apache-2.0 | Accessible | Pilot/debugging and size-sensitivity arm; not presumed accurate enough for every BACE stage | FaithJudge Table 2 evaluates Qwen2.5 7B hallucination judging |
| Compute-dependent reserve | `openai/gpt-oss-120b` | Apache-2.0 | Accessible | Larger different-family evaluator if deployment resources permit | Judge's Verdict Table 4 includes this checkpoint; indirect Answer Accuracy precedent |

MoE active-parameter counts are not total weight-storage requirements. No
memory, throughput, or complete-run cost estimate has been measured here.
Quantization, context length, KV cache, concurrency, and supported kernels must
be checked before selecting a deployment.

## Conditional-access and stage-only candidates

| Exact checkpoint | Weight license | Access observation | Proposed scope |
| --- | --- | --- | --- |
| `meta-llama/Llama-3.3-70B-Instruct` | Llama 3.3 Community License | Repository metadata reports manual gating; anonymous weight HEAD returned HTTP 401 | Strong literature-anchored candidate after authorized access; FaithJudge Table 2 includes Llama3.3 70B; not the exact Llama3 checkpoint used in the original RAGChecker setup |
| `lytang/MiniCheck-Flan-T5-Large` | MIT as reported by the released checkpoint card | Ungated; anonymous weight HEAD returned HTTP 200 | Already task-trained document-claim support checker; no new training is needed to use the released weights, but this is not a full extraction/review/diagnosis backend |

The attempted repository lookup for
`PatronusAI/Llama-3-Lynx-8B-Instruct` returned HTTP 401. Its current access and
license were not established in this follow-up, so it is
`UNVERIFIED_CURRENT_ACCESS`, not an immediate-download recommendation. This
does not establish that all Lynx checkpoints are unavailable.

Released task-trained models must not be excluded solely because training was
used in their paper. The relevant distinction is whether a usable checkpoint
is released and whether its output/task interface fits the proposed stage.

## Proposed first study set

For an access-simple, different-family pilot, start with
`Qwen/Qwen3-30B-A3B-Instruct-2507`, `openai/gpt-oss-20b`, and
`google/gemma-4-31B-it`. The Gemma candidate is a current-model extension,
not a literature-matched replication.

For closer literature alignment, include `Qwen/Qwen2.5-72B-Instruct` and,
after access approval, `meta-llama/Llama-3.3-70B-Instruct`. Related papers are
selection precedents, not evidence that these models perform well on BACE.

Select the final set only after checking actual GPU resources and a
separately authorized pilot. The current code explicitly restricts claim
support to `azure_openai` plus `responses` at
`BACE/script/evaluation/run_generation_claim_support_assessment.py:198`.
An independent backend adapter and structured-output validation are needed;
no frozen configuration or prompt was changed during this investigation.

## Original sources and locators

The paper identifiers, inspected versions, access date, and full-text locators
are recorded in `REPORT.md`. This follow-up uses FaithJudge Section 5/Table 2,
RLSeek Section 5.1/Table 1, and Judge's Verdict Section 1.1/Table 4. The latter
evaluates reference-answer alignment, not supplied-evidence support.

Model sources below were accessed on 2 November 2026. Repository revisions
inspected by the metadata checks are recorded separately. Model-card license
labels and inference sections establish the released checkpoint/interface;
they do not establish legal compliance for every use or measured BACE quality.

- Qwen3-30B-A3B-Instruct-2507: https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507 ; license header, Model Overview, Quickstart.
- Qwen3-14B: https://huggingface.co/Qwen/Qwen3-14B ; license header, Switching Between Thinking and Non-Thinking Mode.
- Qwen2.5-32B-Instruct: https://huggingface.co/Qwen/Qwen2.5-32B-Instruct ; license header, Quickstart.
- Qwen2.5-72B-Instruct: https://huggingface.co/Qwen/Qwen2.5-72B-Instruct ; license header, Quickstart. License text: https://huggingface.co/Qwen/Qwen2.5-72B-Instruct/blob/main/LICENSE ; Sections 2-5 establish a royalty-free limited grant with conditions, not Apache-2.0 licensing.
- Qwen2.5-7B-Instruct: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct ; license header, Quickstart.
- Qwen3.8-27B: https://huggingface.co/Qwen/Qwen3.8-27B ; license header, inference guidance.
- Gemma 4 31B IT: https://huggingface.co/google/gemma-4-31B-it ; license header, model overview and usage sections.
- gpt-oss-20b: https://huggingface.co/openai/gpt-oss-20b ; license header, Highlights, Inference examples.
- gpt-oss-120b: https://huggingface.co/openai/gpt-oss-120b ; license header, Highlights, Inference examples.
- gpt-oss interface: https://developers.openai.com/cookbook/articles/openai-harmony ; introduction and Structured output. Prompting for a schema alone does not guarantee adherence.
- gpt-oss availability: https://help.openai.com/en/articles/11870455-openai-open-weight-models-gpt-oss ; Overview, Getting started, and FAQ. Downloadable weights are not hosted through the OpenAI API or ChatGPT.
- Llama 3.3: https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct ; license header. Metadata: https://huggingface.co/api/models/meta-llama/Llama-3.3-70B-Instruct ; `gated: manual`.
- MiniCheck: https://huggingface.co/lytang/MiniCheck-Flan-T5-Large ; license header, model description, usage. The card identifies a task-trained Flan-T5 checkpoint for document-grounded checking.

No unlimited free hosted API capable of the complete BACE workload was
verified in this investigation. Free model access must not be reported as a
zero-cost completed evaluation.
