# Evaluator-model precedents for a BACE evaluation-only extension

Evidence access date: 2 November 2026.

## Scope and interpretation

This targeted inspection identifies models actually used for extraction,
verification, hallucination detection, or judging in related papers. It is not
an exhaustive literature review, a model leaderboard, or a BACE compatibility
test. No experiment, frozen configuration, prompt, or environment was changed.

Models that generate the answers being evaluated are not counted as evaluator
models unless the source explicitly assigns them an evaluator role. Prompted
general-purpose models, fine-tuned generative evaluators, and specialized
classifiers are distinguished. Parameter sizes below are source-reported model
designations, not measured memory requirements.

## Model-role comparison

| Paper | Models actually used in evaluation | Role and training status | Relevance to BACE |
| --- | --- | --- | --- |
| RAGChecker (2024) | Llama3-70B; Llama3-70B-Instruct for applicable comparison metrics | Prompted claim extractor and checker; shared backbone for applicable baselines | Most direct precedent for replacing the backend across BACE and native comparators |
| Benchmarking LLM Faithfulness in RAG with Evolving Leaderboards / FaithJudge (2025) | Qwen2.5 7B and 72B; Llama3.1 8B; Llama3.3 70B; GPT-4o; o3-mini-high | Prompted hallucination judges; FaithJudge supplies annotated demonstrations | Direct precedent for Qwen/Llama judges, but its demonstrations are not part of the frozen BACE prompts |
| RLSeek (2026) | Qwen3-14B for prompted reasoning comparisons; Qwen2.5-7B-Instruct and Qwen2.5-14B-Instruct for supervised detector baselines | Prompted CoT/CoT+Seek detection and task-trained span detectors; RL-based 7B/14B detector comparisons are also reported | Recent precedent for Qwen in evidence-grounded hallucination detection; detector training is not a backend-only substitution |
| VeriScore (2024) | Fine-tuned Mistral-7B-Instruct-v0.2 for extraction; fine-tuned Llama3-8B-Instruct for verification | Separate task-trained checkpoints; GPT-4 extraction data and GPT-4o verification data | Demonstrates an open-weight multistage pipeline, not the performance of untouched base checkpoints |
| RefChecker (2024) | Mistral 7B extractor distilled from Mixtral 8x7B; GPT-4 and Claude 2 checkers; AlignScore/RoBERTa-NLI and Mistral-based trained checkers | Extraction, NLI verification, LoRA fine-tuning, and representation-based classifiers | Useful architectural precedent; a fine-tuned Mistral checker must not be presented as a generic zero-shot model |
| Lynx (2024) | Llama-3-Instruct-8B and 70B; task-fine-tuned Lynx 8B and 70B; Mistral-Instruct-7B baseline | Prompted baselines and trained response-faithfulness evaluators | Relevant to judge-only or additional-detector comparisons; not evidence of full BACE extraction/diagnosis compatibility |
| MiniCheck (2024) | RoBERTa-Large/AlignScore backbone, DeBERTa-v3-Large, and Flan-T5-Large | Specialized trained document-claim support classifiers | Additional support-checking baselines, not replacements for all BACE generative stages |
| Judge's Verdict (2025 preprint) | Among the evaluated judges: Qwen2.5-32B/72B-Instruct, Qwen3-30B-A3B-Instruct-2507, Llama3/3.3 70B, Gemma-3-27B-IT, gpt-oss-20b/120b, and Mixtral-8x22B-Instruct | General-purpose models used as RAGAS Answer Accuracy judges | Indirect precedent for model diversity; reference-answer alignment is not supplied-evidence faithfulness |
| RAGAS (2024) | gpt-3.5-turbo-16k | All prompted evaluations in the original paper, including faithfulness | Establishes the original paper's backend, not the backend of the frozen BACE installation |
| DnDScore (2025) | GPT-4o mini for joint decomposition/decontextualization; Inst-LLaMA 7B for verification | Inst-LLaMA is instruction-trained on Super Natural Instructions; verifier reused from FActScore | Another open-weight verifier precedent, but not an all-open-weight extraction-plus-verification pipeline |

## Verified source records

### 1. RAGChecker

- Title: RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation.
- Identifier: DOI 10.52202/079017-0692; arXiv:2408.08067v1.
- Versions inspected: locally retained NeurIPS 2024 proceedings PDF and arXiv v1 HTML.
- Locator: Sections 4.1 and 4.2; Appendix G.
- Original source: https://proceedings.neurips.cc/paper_files/paper/2024/file/27245589131d17368cccdfa990cbf16e-Paper-Datasets_and_Benchmarks_Track.pdf
- Web cross-check: https://arxiv.org/html/2408.08067v1
- Local text: `paper/literature/sources/ragchecker2024/fulltext.txt`, lines 299-334.
- Verified distinction: GPT-4, Mixtral-8x7B, Llama3-8B, and Llama3-70B are listed as answer generators; the evaluator setup specifically uses Llama3-70B as extractor and checker. Applicable comparator metrics share Llama3-70B-Instruct, with an exception for embedding-dependent metrics.

### 2. FaithJudge

- Title: Benchmarking LLM Faithfulness in RAG with Evolving Leaderboards.
- Identifier: DOI 10.18653/v1/2025.emnlp-industry.54.
- Version inspected: EMNLP 2025 Industry Track proceedings PDF.
- Locator: Section 5; Section 6; Tables 1 and 2, PDF pages 4-5.
- Original source: https://aclanthology.org/2025.emnlp-industry.54.pdf
- Verified distinction: Qwen2.5 and Llama models occur in detector/judge result rows, not only among the answer generators. Table 2 includes a Qwen 72B, Llama 70B, and GPT-4o majority-vote ensemble. FaithJudge uses human-annotated demonstrations rather than the unmodified RAGAS prompt.

### 3. RLSeek

- Title: RLSeek: Evidence-Grounded Reasoning for RAG Hallucination Detection.
- Identifier: DOI 10.18653/v1/2026.acl-long.1492.
- Version inspected: ACL 2026 proceedings PDF.
- Locator: Section 4.2 and Section 5.1, PDF page 5; Appendix D, PDF pages 12-13.
- Original source: https://aclanthology.org/2026.acl-long.1492.pdf
- Verified distinction: Section 4.2 explicitly names Qwen2.5-7B-Instruct and Qwen2.5-14B-Instruct as supervised baselines. Section 5.1 names Qwen3-14B in the prompted reasoning comparison. These are hallucination detectors, not the generators whose responses populate the benchmark.

### 4. VeriScore

- Title: VeriScore: Evaluating the factuality of verifiable claims in long-form text generation.
- Identifier: DOI 10.18653/v1/2024.findings-emnlp.552.
- Version inspected: Findings of EMNLP 2024 proceedings PDF.
- Locator: Sections 3.4 and 4.1; Appendix G, PDF pages 16-17.
- Original source: https://aclanthology.org/2024.findings-emnlp.552.pdf
- Local text: `paper/literature/sources/veriscore2024/fulltext.txt`.
- Verified distinction: Appendix G selects Mistral fine-tuned for two epochs for extraction and Llama3-8B-Instruct fine-tuned for one epoch for verification. Merely listing both base families would conceal the use of different trained stage-specific checkpoints.

### 5. RefChecker

- Title: RefChecker: Reference-based Fine-grained Hallucination Checker and Benchmark for Large Language Models.
- Identifier: arXiv:2405.14486v1.
- Version inspected: arXiv v1 PDF retained locally and v1 HTML.
- Locator: Sections 4.1, 4.2, 6.1, and 6.2.
- Original source: https://arxiv.org/html/2405.14486v1
- Local text: `paper/literature/sources/refchecker2024_arxiv/fulltext.txt`.
- Verified distinction: Mixtral supplies extraction distillation data. Mistral 7B is trained for extraction and also investigated for checking. The paper reports weaknesses of its zero-shot Mistral checker and investigates trained alternatives. This does not support assuming that any unmodified 7B model is an adequate BACE evaluator.

### 6. Lynx

- Title: Lynx: An Open Source Hallucination Evaluation Model.
- Identifier: arXiv:2407.08488v1.
- Version inspected: arXiv v1 HTML.
- Locator: Section 3.3, Section 4.1, Table 3, and Appendix B.
- Original source: https://arxiv.org/html/2407.08488v1
- Verified distinction: Table 3 separates baseline Llama-3-Instruct-8B/70B from fine-tuned Lynx 8B/70B. Reported gains for Lynx do not establish equivalent performance for baseline Llama or for the BACE task.

### 7. MiniCheck

- Title in inspected version: MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents.
- Identifier: arXiv:2404.10774v1. Publication metadata also identifies EMNLP 2024, DOI 10.18653/v1/2024.emnlp-main.499.
- Version used for model-role verification: arXiv v1 HTML; the publisher PDF fetch timed out, so no version-of-record passage comparison is claimed.
- Locator: Section 3.3, Table 3, and Appendix G.
- Original source used: https://arxiv.org/html/2404.10774v1
- Verified distinction: MiniCheck-Rbta, MiniCheck-Dbta, and MiniCheck-FT5 are task-trained models. Their document-claim classification interface does not implement BACE extraction, candidate selection, support-set enumeration, or unsupported-claim diagnosis.

### 8. Judge's Verdict

- Title: Judge's Verdict: A Comprehensive Analysis of LLM Judge Capability Through Human Agreement.
- Identifier: arXiv:2510.09738v1.
- Version inspected: arXiv v1 preprint HTML; no peer-reviewed publication status is claimed.
- Locator: Section 1.1; Table 4, complete judge performance matrix.
- Original source: https://arxiv.org/html/2510.09738v1
- Verified distinction: The task uses RAGAS Answer Accuracy with a reference answer. Table 4 supplies actual evaluator-model identities, including Gemma 3 and gpt-oss, but their appearance is not evidence about BACE support judgments. No paper performance ranking is adopted here.

### 9. RAGAS

- Title: RAGAs: Automated Evaluation of Retrieval Augmented Generation.
- Identifier: DOI 10.18653/v1/2024.eacl-demo.16.
- Version inspected: EACL 2024 System Demonstrations proceedings PDF.
- Locator: Section 3, PDF page 3, introductory model statement and faithfulness subsection.
- Original source: https://aclanthology.org/2024.eacl-demo.16.pdf
- Local text: `paper/literature/sources/ragas2024/fulltext.txt`, lines 153-172.
- Verified distinction: The original paper uses gpt-3.5-turbo-16k for all prompted evaluations; later software versions and BACE's adapter must be inspected separately.

### 10. DnDScore

- Title: DnDScore: Decontextualization and Decomposition for Factuality Verification in Long-Form Text Generation.
- Identifier: DOI 10.18653/v1/2025.emnlp-main.1205.
- Version inspected: EMNLP 2025 proceedings PDF retained locally and fetched online.
- Locator: Sections 3, 4.1, and 4.2, PDF pages 4-5.
- Original source: https://aclanthology.org/2025.emnlp-main.1205.pdf
- Local text: `paper/literature/sources/dndscore2025/fulltext.txt`, lines 247-321.
- Verified distinction: GPT-4o mini performs DnD processing; Inst-LLaMA 7B performs the modified factuality verification. It would be incorrect to describe the whole method as an entirely open-model pipeline.

## Proposed model-selection implications

These are design recommendations, not completed BACE results:

1. Include a Llama 70B instruction model if connecting the extension directly to RAGChecker is important. Llama3-70B-Instruct follows the original setup most closely; Llama3.3-70B-Instruct has additional direct FaithJudge precedent but is not the checkpoint used by the RAGChecker paper.
2. Include Qwen2.5-72B-Instruct for a direct prompted-faithfulness precedent, or a Qwen3 model for a more recent reasoning comparison. The verified Qwen3 precedents here concern Qwen3-14B and Qwen3-30B-A3B-Instruct-2507, not Qwen3.8.
3. Use Gemma or gpt-oss as additional model-family robustness comparisons if desired. The verified general-judge precedent concerns Gemma-3-27B-IT and gpt-oss, not Gemma 4 or a complete BACE pipeline.
4. Treat Lynx, MiniCheck, and the VeriScore fine-tuned models as specialized comparator arms or stage-specific experiments. Replacing every BACE stage with a specialized checker is not supported by their documented interfaces.
5. Hold generated disclosures and their visible evidence fixed. Distinguish evaluation-only pipeline reruns from fixed-inventory judge-only reruns. Public-paper results do not validate a new BACE configuration.

All source records above were inspected on the evidence access date at the top.
No unpublished BACE material was uploaded, no models were downloaded, and no
new experiment or training run was started.
