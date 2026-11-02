# Current open-weight model families for BACE evaluation

Verified on: 2 November 2026.

## Scope

This follow-up prioritizes current publicly released Qwen, Gemma, and Llama
families, rather than the older checkpoints used in related papers. It also
includes Meta's Muse Glimmer as a separate current open-weight model, not a
Llama checkpoint. The earlier `CANDIDATES.md` remains a mixed
literature-anchored/accessibility list and should not be described as a list of
the latest model versions.

Official family pages, model cards, repository metadata, and one anonymous
weight-URL HEAD request per listed checkpoint were inspected. Repository
creation dates were not interpreted as public release dates. Searches returning
no newer family are not proof that no unannounced or differently named model
exists. This is a targeted selection, not an exhaustive inventory.

Free means downloadable weights without a model purchase, subject to the
published license. Compute and hosted inference are not thereby free. A
custom-license open-weight model must not be presented as Apache-2.0 licensed.
No legal-compliance determination is made for the author's particular use.

## Current-family candidate set

| Exact checkpoint | Source-reported scale | License | Weight access | Proposed evaluation role |
| --- | --- | --- | --- | --- |
| `Qwen/Qwen3.8-27B` | 27B dense language model | Apache-2.0 | Ungated; anonymous weight HEAD 200 | First-choice Qwen-family full-pipeline pilot |
| `google/gemma-4-31B-it` | 31B model designation | Apache-2.0 | Ungated; anonymous weight HEAD 200 | First-choice Gemma-family full-pipeline pilot |
| `google/gemma-4-26B-A4B-it` | 26B total / approximately 4B active model designation; MoE | Apache-2.0 | Ungated; anonymous weight HEAD 200 | Alternative Gemma-family deployment arm |
| `google/gemma-4-12B-it` | 12B model designation | Apache-2.0 | Ungated; anonymous weight HEAD 200 | Smaller current-family control/pilot |
| `meta-models/Muse-Glimmer-30B` | 30B model designation | Apache-2.0 | Ungated; anonymous weight HEAD 200 | Different-family Meta-model pilot; not a Llama replication |
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | 17B active / 109B total; MoE | Llama 4 Community License | Manually gated; anonymous weight HEAD 401 | Conditional Llama-family pilot after access and hardware checks |
| `meta-llama/Llama-4-Maverick-17B-128E-Instruct` | 17B active / 400B total; MoE | Llama 4 Community License | Manually gated; anonymous weight HEAD 401 | Large-compute reserve, not the default first-pass candidate |
| `Qwen/Qwen3.8-Flash-Next` | Approximately 180B total weights in official repository metadata | Qwen Community 1.0, not Apache-2.0 | Ungated; anonymous weight HEAD 200 | Later current-family, large-compute reserve |

Scale values are `SOURCE_REPORTED`, not measured memory requirements or BACE
results. MoE active parameters do not represent all weights that must be stored.
The nominal Qwen 27B size refers to its language model; full checkpoint tensor
counts also include other components. Nominal family sizes and exact tensor
counts should not be conflated.

## Recommendation and evidence boundary

For three access-simple current models from different developers, pilot
Qwen3.8-27B, Gemma-4-31B-it, and Muse-Glimmer-30B. If a specifically
Llama-labelled arm is required, add Llama 4 Scout after access approval and
resource checks; Muse Glimmer is not a substitute for a claimed Llama result.

These are proposed general-purpose generative backends for claim extraction,
review, support assessment, and diagnosis. All are
`BACE_COMPATIBILITY_UNTESTED` and `BACE_PERFORMANCE_UNMEASURED`. Public chat or
agent capabilities do not establish evidence-support judging accuracy, stable
claim inventories, or compatibility with BACE's strict schemas. Released
post-trained/instruction-tuned checkpoints do not require new fine-tuning
merely to run inference.

Before a complete rerun, an authorized pilot should check schema adherence,
evidence identifiers, output truncation, reasoning/final separation, retries,
peak memory, and throughput. Reuse the saved generations and supplied evidence
to isolate the evaluation-model change. A same-backend native comparator
extension and a fixed-inventory checker-only extension are different studies.

The current claim-support entry point restricts the provider/API to
`azure_openai`/`responses` at
`BACE/script/evaluation/run_generation_claim_support_assessment.py:198`.
An independent backend adapter is needed; changing a model name alone does not
enable the frozen pipeline. No frozen prompts, configurations, environments,
or saved experiment artifacts were changed in this investigation.

## Sources and full-text locators

All sources below were accessed on 2 November 2026. Inspected checkpoint
revisions and raw access observations are in `latest_family_access_checks.json`.

- Qwen family: https://github.com/QwenLM/Qwen3.8 ; News and Models identify the released Qwen3.8 family. Qwen3.8-27B public availability is dated 14 August 2026 in News.
- Qwen 27B: https://huggingface.co/Qwen/Qwen3.8-27B ; license header, repository introduction, Highlights, Model Overview, Quickstart. The introduction explicitly identifies the released artifact as post-trained.
- Qwen Flash Next: https://huggingface.co/Qwen/Qwen3.8-Flash-Next ; license header and Safetensors/Model size. License source: https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE . It is separately labelled Qwen Community 1.0 despite Apache licensing of the Qwen3.8 code repository.
- Gemma family: https://ai.google.dev/gemma/docs ; Gemma models overview identifies Gemma 4 as the core general-purpose family; page updated 7 October 2026.
- Gemma family model card: https://ai.google.dev/gemma/docs/core/model_card_4 ; license header, model information and inputs/outputs.
- Gemma 31B IT: https://huggingface.co/google/gemma-4-31B-it ; license header and model overview.
- Gemma 26B A4B IT: https://huggingface.co/google/gemma-4-26B-A4B-it ; license header and model information. The A4B designation describes active parameters, not total storage.
- Gemma 12B IT: https://huggingface.co/google/gemma-4-12B-it ; license header, model information and Safetensors/Model size.
- Llama family: https://dev.meta.ai/llama/models/llama-4 ; LATEST and Llama 4 models sections list Scout and Maverick. This establishes the current Llama-labelled selection, not that Llama is Meta's newest model branding.
- Llama Scout: https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct ; Model Information table reports 17B active, 109B total and release on 5 April 2025. License: https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct/blob/main/LICENSE .
- Llama Maverick: https://huggingface.co/meta-llama/Llama-4-Maverick-17B-128E-Instruct ; Model Information table reports 17B active and 400B total; license header identifies Llama 4 terms.
- Muse Glimmer: https://dev.meta.ai/models/muse-glimmer ; introductory paragraph identifies a 30B model with Apache-2.0 licensing.
- Muse Glimmer weights: https://huggingface.co/meta-models/Muse-Glimmer-30B ; license header, Model Card and Released Artifacts. The card states release in August 2026. It is a distinct model family, distilled from Muse Spark.

The official Muse Spark Open page,
https://dev.meta.ai/models/muse-spark-open , advertises open weights, but its
download route redirected to authentication. The exact downloadable checkpoint,
license, and resource requirements were not established in this follow-up.
It is `UNVERIFIED_IMMEDIATE_ACCESS` and is not an immediate-download
recommendation. This is an access/verification boundary, not a claim that the
model is unavailable to authorized users.
