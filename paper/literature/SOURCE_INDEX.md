# Verified source index

Checked on 29 September 2026. Entries describe the specific inspected passages, not whole-paper endorsements.

Citation keys match `../references.bib`. Pending-access candidates are recorded separately in the gap report.

## factscore2023

FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation

[Original PDF](sources/factscore2023/original.pdf) · [Extracted text](sources/factscore2023/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2023.emnlp-main.741)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF page 3, Section 3.1, Key Idea 2 and Definition.

Verified statement: FActScore decomposes generated text into atomic facts and defines factual precision relative to a specified knowledge source.

Evidence paraphrase: The definition averages the proportion of atomic facts supported by knowledge source C; the preceding paragraph explicitly distinguishes support by a chosen source from global truth.

Limits: Its knowledge source need not be the exact evidence supplied during generation. This establishes prior source-relative claim assessment, not an ESRS-specific diagnosis scheme.

## ragas2024

RAGAs: Automated Evaluation of Retrieval Augmented Generation

[Original PDF](sources/ragas2024/original.pdf) · [Extracted text](sources/ragas2024/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2024.eacl-demo.16)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 2–4, Sections 3–4, especially Faithfulness and WikiEval.

Verified statement: RAGAS extracts statements, checks whether they can be inferred from supplied context, and compares its metrics with human judgments in WikiEval.

Evidence paraphrase: Faithfulness is the proportion of extracted statements supported by context. The original paper describes statement extraction and Yes/No verification, followed by human comparisons on question-context-answer examples.

Limits: The paper supports the metric's original definition. Exact behavior of the BACE experiment's installed RAGAS version must be established from frozen implementation records. An entailment criterion can in principle reject a changed qualifier.

## ragchecker2024

RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation

[Original PDF](sources/ragchecker2024/original.pdf) · [Extracted text](sources/ragchecker2024/fulltext.txt) · [Canonical identifier](https://doi.org/10.52202/079017-0692)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 3–6, Sections 3.2, 3.3.3 and 4.2.

Verified statement: RAGChecker uses claim extraction and entailment for retrieval and generation diagnostics, including native faithfulness, and performs human preference meta-evaluation.

Evidence paraphrase: Section 3.3.3 defines faithfulness through claims entailed by retrieved chunks. Its other diagnostics distinguish sources of unsupported or incorrect output. Section 4.2 compares response-pair preferences for correctness, completeness and overall assessment.

Limits: The full metric suite includes ground-truth-dependent metrics; the BACE experiment uses native faithfulness. The original study's preference validation does not validate BACE's diagnoses or establish accuracy in ESRS disclosure drafting.

## refchecker2024_arxiv

RefChecker: Reference-based Fine-grained Hallucination Checker and Benchmark for Large Language Models

[Original PDF](sources/refchecker2024_arxiv/original.pdf) · [Extracted text](sources/refchecker2024_arxiv/fulltext.txt) · [Canonical identifier](https://doi.org/10.48550/ARXIV.2405.14486)

Version: arXiv:2405.14486v1, submitted 23 May 2024.

Locator: PDF page 4, Sections 3.1–3.2 and Figures 3–4; arXiv v1.

Verified statement: RefChecker assesses claim-triplets against references using Entailment, Contradiction and Neutral labels, including settings where input context is the reference.

Evidence paraphrase: Noisy Context and Accurate Context both use the supplied input context as reference. A triplet inferred from the reference is entailed; an incompatible triplet is contradicted; insufficient reference information leads to Neutral.

Limits: Verified against arXiv:2405.14486v1, not a claimed journal or conference version. Its Neutral category must not be equated automatically with one BACE diagnosis.

## alce2023

Enabling Large Language Models to Generate Text with Citations

[Original PDF](sources/alce2023/original.pdf) · [Extracted text](sources/alce2023/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2023.emnlp-main.398)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF page 4, Section 3.3; PDF page 15, Appendix F.2.

Verified statement: ALCE evaluates support using concatenated cited passages and asks human annotators whether a joint citation set fully supports a statement.

Evidence paraphrase: Citation recall checks entailment from concat(C_i). The authors explicitly state that citation precision does not require a minimal set. Human citation-recall annotation assesses the joint cited evidence.

Limits: This is prior multi-source support evaluation. BACE's explicit minimal support-set specification is a design distinction from this formulation, not evidence of a first-ever multi-evidence method or of greater accuracy.

## veriscore2024

VeriScore: Evaluating the factuality of verifiable claims in long-form text generation

[Original PDF](sources/veriscore2024/original.pdf) · [Extracted text](sources/veriscore2024/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2024.findings-emnlp.552)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF page 3, Sections 2.1.2–2.3; PDF pages 18–19, Appendix C.

Verified statement: VeriScore explicitly retains necessary spatial and temporal modifiers, uses surrounding context to extract self-contained claims, and requires support for the complete claim.

Evidence paraphrase: The definition of a verifiable claim includes necessary modifiers. The extraction method resolves references using a sliding context window. Verification requires every part of the claim to be supported and no part to be contradicted, with evidence retrieved through web search.

Limits: This directly defeats a blanket claim that previous factuality methods ignore material qualifiers. Its web-retrieved evidence universe differs from BACE's generator-visible evidence boundary.

## claimify2025

Towards Effective Extraction and Evaluation of Factual Claims

[Original PDF](sources/claimify2025/original.pdf) · [Extracted text](sources/claimify2025/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2025.acl-long.348)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 2–5, Sections 2.1–2.3 and 3.1–3.4.

Verified statement: Claimify treats entailment, coverage and decontextualization as extraction criteria and resolves referential and structural ambiguity using context.

Evidence paraphrase: The paper examines how omitted context changes retrieved evidence and verification outcomes. Its examples include relative time, ambiguous actors and relations between company-specific activities. Claimify includes selection, disambiguation and decomposition stages.

Limits: Context preservation and ambiguity handling are established prior work. The paper primarily addresses claim extraction and its evaluation; it does not by itself establish the quality of BACE's extraction or diagnoses.

## dndscore2025

DnDScore: Decontextualization and Decomposition for Factuality Verification in Long-Form Text Generation

[Original PDF](sources/dndscore2025/original.pdf) · [Extracted text](sources/dndscore2025/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2025.emnlp-main.1205)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 2–4, Figure 1 and Section 3.

Verified statement: DnDScore examines the interaction of decomposition and decontextualization and verifies subclaims with their contextualized forms.

Evidence paraphrase: The study motivates contextual verification by showing that adding or omitting context can change what is checked or counted. It proposes joint decomposition and decontextualization and a verifier that distinguishes the target subclaim from contextual information.

Limits: Segmentation and contextualization can change factuality scores, so BACE's score gaps cannot be attributed solely to stricter boundary judgments. DOI metadata pagination differs from the publisher page and PDF; use the corrected publisher pagination and PDF-page locators.

## chatreport2023

CHATREPORT: Democratizing Sustainability Disclosure Analysis through LLM-based Tools

[Original PDF](sources/chatreport2023/original.pdf) · [Extracted text](sources/chatreport2023/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2023.emnlp-demo.3)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 3–6, Sections 3.3–3.4 and 5–5.4.

Verified statement: ChatReport provides source-linked sustainability report analysis, human support and attribution evaluation, and an example of false concatenation of separate retrieved chunks.

Evidence paraphrase: Human content annotation counts extrapolation or partial support as hallucination. Source annotation additionally checks references. Section 5.2 illustrates erroneous concatenation of distinct chunks; Section 5.4 describes the expert-annotated support dataset.

Limits: This is direct domain precedent for evidence support, human evaluation and erroneous synthesis. The inspected work focuses on TCFD-oriented report analysis and question answering; it should not be recast as an absence of domain evaluation.

## susgen2025

SusGen-GPT: A Data-Centric LLM for Financial NLP and Sustainability Report Generation

[Original PDF](sources/susgen2025/original.pdf) · [Extracted text](sources/susgen2025/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2025.findings-naacl.66)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 3–5, Section 3 and Section 3.4; PDF page 9, Limitations. Page locator rechecked against the original PDF on 29 October 2026.

Verified statement: SusGen-GPT includes RAG-based sustainability report generation and evaluates generated reports using reference-text metrics while acknowledging limited expert evaluation.

Evidence paraphrase: Section 3.4 lists BERTScore, ROUGE, METEOR and BLEU-N for sustainability report generation. The limitations distinguish expert analysis of some cases from reliance on automated metrics at scale.

Limits: This characterizes the stated evaluation, not a proof that the system cannot preserve evidence boundaries. Generation quality and evaluator validity are different targets. Preserve the original PDF spelling Hejia Huang in the working bibliography.

## esghrag2025

An innovative ESGH-RAG module with ChatGPT-4o for automatic ESG-report generation

[Original PDF](sources/esghrag2025/original.pdf) · [Extracted text](sources/esghrag2025/fulltext.txt) · [Canonical identifier](https://doi.org/10.1007/s11227-025-07604-0)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 16–18, Sections 4.4–4.6 and Table 5.

Verified statement: ESGH-RAG generates ESG reports and evaluates report-level characteristics and expert feasibility, with additional qualitative expert feedback.

Evidence paraphrase: Table 5 compares model, retrieval, content sources, report characteristics and expert feasibility; Section 4.6 presents third-party and company feedback.

Limits: The paper's reported compliance and feasibility claims are not independent proof of legal compliance or claim-level support accuracy. The table here describes its evaluation design only.

## esgbench2026

ESG-Bench: Benchmarking Long-Context ESG Reports for Hallucination Mitigation

[Original PDF](sources/esgbench2026/original.pdf) · [Extracted text](sources/esgbench2026/fulltext.txt) · [Canonical identifier](https://doi.org/10.1609/aaai.v40i46.41281)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 2–4, benchmark construction, Human Annotation and Benchmark Analysis and Usage.

Verified statement: ESG-Bench provides human-annotated ESG question answering with support-related labels, supporting source pages and adjudication of disagreements.

Evidence paraphrase: The annotation protocol assigns Correct, Hallucination, Incomplete or Answer Not Found; it checks factual accuracy and supporting source pages. Two annotators review each response and another resolves disagreement. The benchmark also supports hallucination-mitigation evaluation.

Limits: This defeats a claim that ESG-specific human hallucination benchmarks are absent. Report-based QA and mitigation evaluation are not identical to BACE's generated-disclosure and conditional candidate-EC judgment tasks.

## europe2026

Assessing corporate sustainability with large language models: evidence from Europe

[Original PDF](sources/europe2026/original.pdf) · [Extracted text](sources/europe2026/fulltext.txt) · [Canonical identifier](https://doi.org/10.1038/s41467-026-75160-z)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF pages 2 and 13–14, framework description and Methods: generation and Validation.

Verified statement: Forster and colleagues use RAG to extract ESRS-aligned numerical indicators from corporate reports and validate extracted values against external and human-annotated data.

Evidence paraphrase: The generation stage returns requested indicator values and units in JSON. Validation compares extracted numerical values with an external ESG dataset and manually annotated values, and explicitly discusses the reference datasets' limitations.

Limits: The evaluation target is numerical extraction from existing reports. It is distinct from auditing claims in newly drafted disclosures. The presence of the same broad population scale does not by itself establish a data lineage relationship with BACE.

## ares2024

ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems

[Original PDF](sources/ares2024/original.pdf) · [Extracted text](sources/ares2024/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2024.naacl-long.20)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF page 2, framework overview.

Verified statement: ARES combines learned RAG judges with a human-annotated validation set and prediction-powered inference.

Evidence paraphrase: The overview describes synthetic question-answer generation, separate relevance and faithfulness judges, and use of human annotations to correct model-based estimates and compute uncertainty intervals.

Limits: Human-calibrated automated assessment is established prior work. BACE's company-cluster sampling intervals do not implement ARES's estimator or account for judge errors in the same way.

## ragtruth2024

RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models

[Original PDF](sources/ragtruth2024/original.pdf) · [Extracted text](sources/ragtruth2024/fulltext.txt) · [Canonical identifier](https://doi.org/10.18653/v1/2024.acl-long.585)

Version: Publisher/conference version of record retrieved 29 September 2026.

Locator: PDF page 3, Sections 3.1–3.2.

Verified statement: RAGTruth distinguishes evident and subtle conflicts and evident and subtle introductions of unsupported information in RAG outputs.

Evidence paraphrase: The taxonomy includes changes to contextual meaning and unsupported inferred details. Data construction covers question answering, data-to-text generation and summarization under provided-context conditions.

Limits: Failure taxonomy and subtle unsupported inference are prior concepts. A different label set is not itself proof of scientific novelty or improved diagnosis.
