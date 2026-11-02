# Server feasibility for the four selected evaluation models

Inspection date: 2 November 2026. Host: `stratus`.
Memory, quota, and disk probe timestamp: `2026-11-02T16:21:15+01:00`.

## Verdict

The visible server is a high-memory CPU host, not a ready GPU inference host.
All four models' estimated BF16 weight payloads individually fit in observed
available host RAM. This does not establish working inference, acceptable
throughput, full-context capacity, or feasibility of a complete BACE rerun.

No NVIDIA/AMD inference GPU is visible. The display adapter is ASPEED, vendor
`0x1a03`, device `0x2000`, using the `ast` driver; it is not evidence of a CUDA
or ROCm accelerator. CPU inference is a candidate path, but no benchmark was
performed. The immediate additional blocker is the user's home quota.

## Observed configuration

| Item | Observation | Source |
| --- | --- | --- |
| CPU | Two AMD EPYC 9335 processors; 64 physical cores and 128 logical CPUs | `lscpu`; physical count is 2 sockets x 32 cores/socket |
| Available process CPUs | 128; effective cpuset `0-127` | `nproc`; cgroup cpuset |
| NUMA | Two nodes | `lscpu` |
| Instructions | AVX2, AVX512, AVX512_BF16 observed | `lscpu` flags |
| Host RAM | Approximately 2.2 TiB total; 2.1 TiB available | `/proc/meminfo`; exact values and conversion in saved artifacts |
| Compute GPU | No NVIDIA/AMD GPU exposed; no NVIDIA/ROCm tools in PATH | PCI vendor inventory, device nodes, and tool discovery |
| User home quota | 100 GiB limit; approximately 5.4 GiB remaining | `quota -v -w`; remaining = (104857600 - 99171608) KiB |
| Home filesystem | Approximately 3.8 TiB filesystem-wide availability, not the user's allowance | `df -B1 .` |
| `/tmp` | Approximately 1.47 TiB free; writable; persistence policy unverified | `df -B1 /tmp`; access check |
| Default Python | No torch, transformers, vllm, sglang, accelerate, or llama-cpp-python distributions detected | Standard-library `importlib.metadata` |

Host-wide RAM and filesystem availability are shared observations, not reserved
resources. No readable numeric cgroup memory/CPU cap was found in the inspected
hierarchy, but that does not establish unrestricted use. Other isolated Python
environments and non-PATH binaries were not exhaustively searched.

## Model weight payload estimates

| Model | BF16 payload (GiB) | Uniform INT4 payload lower bound (GiB) | Weight-only RAM fit | Inference status |
| --- | --- | --- | --- | --- |
| Qwen3.8-27B | 51.7 | 12.9 | Yes | Not tested |
| Gemma-4-31B-it | 58.3 | 14.6 | Yes | Not tested |
| Muse-Glimmer-30B | 55.5 | 13.9 | Yes | Not tested |
| Llama-4-Scout | 202.4 | 50.6 | Yes | Not tested |

These are `COMPUTED_VERIFIED` arithmetic estimates, not measurements of RAM,
VRAM, GGUF file sizes, or inference performance. Source counts and exact model
revisions are recorded in `latest_family_access_checks.json`. Formulas are
tensor count x 2 bytes for BF16 and tensor count x 0.5 bytes for an idealized
uniform INT4 payload, divided by 2^30. Values are rounded to one decimal here.

Actual quantized weights include scales, metadata and mixed-precision tensors;
runtime also needs KV cache, activations and other allocations. Context length,
concurrency, implementation and NUMA placement matter. The INT4 column neither
verifies a particular quantization artifact nor predicts its evaluator quality.

Even the idealized INT4 payloads exceed the remaining home quota. Scout's BF16
payload exceeds the entire 100 GiB home allowance. Do not mistake the shared
home filesystem's `df` capacity for usable personal cache space.

## Practical next steps

1. Resolve persistent model storage outside the current home quota, or obtain
   an increased quota. `/tmp` is only a potential temporary cache; confirm its
   policy before use, and retain experiment outputs in an approved persistent
   location. Do not delete saved experiment artifacts to make space.
2. Choose CPU versus an authorized GPU node. For CPU, use an independent
   inference environment and verify the exact checkpoint/runtime combination.
   Do not modify the frozen BACE environments.
3. If CPU-only is the available path, authorize a small Qwen/Gemma pilot first
   and measure prefill time, decoding throughput, peak memory, schema validity,
   and representative long-input behavior. NUMA-aware physical-core settings
   should be benchmarked rather than assuming 128 threads is optimal.
4. Estimate the full evaluation workload only after that pilot. No token/s,
   days-to-completion, or complete-run cost was measured here.
5. For a GPU alternative, Meta documents Scout INT4 inference on one H100.
   This is not BF16 Scout inference or a guarantee of the advertised maximum
   context on one GPU. Model access approval and exact runtime support remain
   separate requirements.

Recent llama.cpp artifacts provide a credible CPU-pilot route for Qwen3.8,
Gemma 4, and Muse Glimmer. This is upstream evidence of an implementation
path, not a successful deployment on this host. A generic vLLM CPU installation
also does not prove support for every selected architecture and quantization.

## Reproducibility and sources

- Hardware and raw resource counters: `SERVER_SNAPSHOT.json`.
- Calculation code: `estimate_weight_memory.py`.
- Calculation output with input hashes: `WEIGHT_MEMORY_ESTIMATES.json`.
- Run command: `python paper/analysis/evaluator_model_precedents_2026-11-02/estimate_weight_memory.py`.
- Model metadata input: `latest_family_access_checks.json`.
- Upstream sources accessed on 2 November 2026:
  - https://docs.vllm.ai/en/latest/getting_started/installation/cpu/?device=x86 ; Requirements, AMD Zen optimizations, and CPU supported-model FAQ. CPU hardware instructions and model implementation support are separate questions.
  - https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF ; llama.cpp usage sections and Q4_K_M artifact. Runtime-maintainer release, not an untouched BF16 checkpoint.
  - https://huggingface.co/google/gemma-4-31B-it-qat-q4_0-gguf ; llama.cpp usage and released Google QAT artifact. QAT is a distinct released quantized checkpoint and must be recorded as such in an experiment.
  - https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF ; llama.cpp minimum-build notice: b10353 or newer, support merged 10 August 2026. The displayed CUDA build example is not a CPU build instruction.
  - https://github.com/ggml-org/llama.cpp/blob/master/src/models/muse-glimmer.cpp ; implemented model architecture, inspected on the access date.
  - https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/llama4 ; Introduction table and footnotes: Scout 109B total, 17B active; single-H100 claim specifically uses INT4; maximum-context evaluation uses distributed hardware.

No model download, package installation, inference benchmark, BACE experiment,
remote-node login, credential sourcing, quota change, or cleanup was performed.
