# Citation occurrence ledger

Each occurrence records the exact local claim and original-source evidence. DIRECT means that the inspected passage supports the stated source-specific claim. QUALIFIED marks a grouped claim for which this source supports only its identified component.

These are source-specific literature judgments, not validation of BACE. Full machine-readable records are in [JSON](citation_ledger.json) and [CSV](citation_ledger.csv).

## CIT-001: chatreport2023

Occurrence: `03_research_foundation.md:21`, Research background.

Generative artificial intelligence (AI) has been explored for sustainability-information analysis in ChatReport and disclosure drafting in SusGen-GPT.

Verdict: QUALIFIED. Source: [PDF](sources/chatreport2023/original.pdf), PDF pages 3–6, Sections 3.3–3.4 and 5–5.4.

Evidence: Human content annotation counts extrapolation or partial support as hallucination. Source annotation additionally checks references. Section 5.2 illustrates erroneous concatenation of distinct chunks; Section 5.4 describes the expert-annotated support dataset.

Limits: This is direct domain precedent for evidence support, human evaluation and erroneous synthesis. The inspected work focuses on TCFD-oriented report analysis and question answering; it should not be recast as an absence of domain evaluation. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-002: susgen2025

Occurrence: `03_research_foundation.md:21`, Research background.

Generative artificial intelligence (AI) has been explored for sustainability-information analysis in ChatReport and disclosure drafting in SusGen-GPT.

Verdict: QUALIFIED. Source: [PDF](sources/susgen2025/original.pdf), PDF pages 3–5, Section 3 and Section 3.4; PDF page 8, Limitations.

Evidence: Section 3.4 lists BERTScore, ROUGE, METEOR and BLEU-N for sustainability report generation. The limitations distinguish expert analysis of some cases from reliance on automated metrics at scale.

Limits: This characterizes the stated evaluation, not a proof that the system cannot preserve evidence boundaries. Generation quality and evaluator validity are different targets. Preserve the original PDF spelling Hejia Huang in the working bibliography. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-003: ragas2024

Occurrence: `03_research_foundation.md:22`, Research background.

Retrieval-augmented generation (RAG) provides a language model with retrieved external context for generating a response.

Verdict: DIRECT. Source: [PDF](sources/ragas2024/original.pdf), PDF pages 2–4, Sections 3–4, especially Faithfulness and WikiEval.

Evidence: Faithfulness is the proportion of extracted statements supported by context. The original paper describes statement extraction and Yes/No verification, followed by human comparisons on question-context-answer examples.

Limits: The paper supports the metric's original definition. Exact behavior of the BACE experiment's installed RAGAS version must be established from frozen implementation records. An entailment criterion can in principle reject a changed qualifier.

## CIT-004: factscore2023

Occurrence: `03_research_foundation.md:33`, Research gap.

Existing approaches already evaluate claim-level support relative to evidence: FActScore uses a specified knowledge source, while RAGAS and RAGChecker assess faithfulness to retrieved context.

Verdict: QUALIFIED. Source: [PDF](sources/factscore2023/original.pdf), PDF page 3, Section 3.1, Key Idea 2 and Definition.

Evidence: The definition averages the proportion of atomic facts supported by knowledge source C; the preceding paragraph explicitly distinguishes support by a chosen source from global truth.

Limits: Its knowledge source need not be the exact evidence supplied during generation. This establishes prior source-relative claim assessment, not an ESRS-specific diagnosis scheme. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-005: ragas2024

Occurrence: `03_research_foundation.md:33`, Research gap.

Existing approaches already evaluate claim-level support relative to evidence: FActScore uses a specified knowledge source, while RAGAS and RAGChecker assess faithfulness to retrieved context.

Verdict: QUALIFIED. Source: [PDF](sources/ragas2024/original.pdf), PDF pages 2–4, Sections 3–4, especially Faithfulness and WikiEval.

Evidence: Faithfulness is the proportion of extracted statements supported by context. The original paper describes statement extraction and Yes/No verification, followed by human comparisons on question-context-answer examples.

Limits: The paper supports the metric's original definition. Exact behavior of the BACE experiment's installed RAGAS version must be established from frozen implementation records. An entailment criterion can in principle reject a changed qualifier. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-006: ragchecker2024

Occurrence: `03_research_foundation.md:33`, Research gap.

Existing approaches already evaluate claim-level support relative to evidence: FActScore uses a specified knowledge source, while RAGAS and RAGChecker assess faithfulness to retrieved context.

Verdict: QUALIFIED. Source: [PDF](sources/ragchecker2024/original.pdf), PDF pages 3–6, Sections 3.2, 3.3.3 and 4.2.

Evidence: Section 3.3.3 defines faithfulness through claims entailed by retrieved chunks. Its other diagnostics distinguish sources of unsupported or incorrect output. Section 4.2 compares response-pair preferences for correctness, completeness and overall assessment.

Limits: The full metric suite includes ground-truth-dependent metrics; the BACE experiment uses native faithfulness. The original study's preference validation does not validate BACE's diagnoses or establish accuracy in ESRS disclosure drafting. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-007: veriscore2024

Occurrence: `03_research_foundation.md:34`, Research gap.

VeriScore explicitly preserves necessary spatial and temporal modifiers, Claimify addresses contextual ambiguity, and ALCE evaluates whether joint cited evidence supports a statement.

Verdict: QUALIFIED. Source: [PDF](sources/veriscore2024/original.pdf), PDF page 3, Sections 2.1.2–2.3; PDF pages 18–19, Appendix C.

Evidence: The definition of a verifiable claim includes necessary modifiers. The extraction method resolves references using a sliding context window. Verification requires every part of the claim to be supported and no part to be contradicted, with evidence retrieved through web search.

Limits: This directly defeats a blanket claim that previous factuality methods ignore material qualifiers. Its web-retrieved evidence universe differs from BACE's generator-visible evidence boundary. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-008: claimify2025

Occurrence: `03_research_foundation.md:34`, Research gap.

VeriScore explicitly preserves necessary spatial and temporal modifiers, Claimify addresses contextual ambiguity, and ALCE evaluates whether joint cited evidence supports a statement.

Verdict: QUALIFIED. Source: [PDF](sources/claimify2025/original.pdf), PDF pages 2–5, Sections 2.1–2.3 and 3.1–3.4.

Evidence: The paper examines how omitted context changes retrieved evidence and verification outcomes. Its examples include relative time, ambiguous actors and relations between company-specific activities. Claimify includes selection, disambiguation and decomposition stages.

Limits: Context preservation and ambiguity handling are established prior work. The paper primarily addresses claim extraction and its evaluation; it does not by itself establish the quality of BACE's extraction or diagnoses. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-009: alce2023

Occurrence: `03_research_foundation.md:34`, Research gap.

VeriScore explicitly preserves necessary spatial and temporal modifiers, Claimify addresses contextual ambiguity, and ALCE evaluates whether joint cited evidence supports a statement.

Verdict: QUALIFIED. Source: [PDF](sources/alce2023/original.pdf), PDF page 4, Section 3.3; PDF page 15, Appendix F.2.

Evidence: Citation recall checks entailment from concat(C_i). The authors explicitly state that citation precision does not require a minimal set. Human citation-recall annotation assesses the joint cited evidence.

Limits: This is prior multi-source support evaluation. BACE's explicit minimal support-set specification is a design distinction from this formulation, not evidence of a first-ever multi-evidence method or of greater accuracy. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-010: chatreport2023

Occurrence: `03_research_foundation.md:37`, Research gap.

Sustainability-specific evidence evaluation also has direct precedents. ChatReport uses human support and attribution judgments and documents false concatenation of retrieved chunks; ESG-Bench supplies human-annotated support and hallucination assessments for ESG question answering.

Verdict: QUALIFIED. Source: [PDF](sources/chatreport2023/original.pdf), PDF pages 3–6, Sections 3.3–3.4 and 5–5.4.

Evidence: Human content annotation counts extrapolation or partial support as hallucination. Source annotation additionally checks references. Section 5.2 illustrates erroneous concatenation of distinct chunks; Section 5.4 describes the expert-annotated support dataset.

Limits: This is direct domain precedent for evidence support, human evaluation and erroneous synthesis. The inspected work focuses on TCFD-oriented report analysis and question answering; it should not be recast as an absence of domain evaluation. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-011: esgbench2026

Occurrence: `03_research_foundation.md:37`, Research gap.

Sustainability-specific evidence evaluation also has direct precedents. ChatReport uses human support and attribution judgments and documents false concatenation of retrieved chunks; ESG-Bench supplies human-annotated support and hallucination assessments for ESG question answering.

Verdict: QUALIFIED. Source: [PDF](sources/esgbench2026/original.pdf), PDF pages 2–4, benchmark construction, Human Annotation and Benchmark Analysis and Usage.

Evidence: The annotation protocol assigns Correct, Hallucination, Incomplete or Answer Not Found; it checks factual accuracy and supporting source pages. Two annotators review each response and another resolves disagreement. The benchmark also supports hallucination-mitigation evaluation.

Limits: This defeats a claim that ESG-specific human hallucination benchmarks are absent. Report-based QA and mitigation evaluation are not identical to BACE's generated-disclosure and conditional candidate-EC judgment tasks. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-012: factscore2023

Occurrence: `04_research_gap_verification.md:21`, What the original sources establish.

FActScore decomposes generated text into atomic facts and defines factual precision relative to a specified knowledge source.

Verdict: DIRECT. Source: [PDF](sources/factscore2023/original.pdf), PDF page 3, Section 3.1, Key Idea 2 and Definition.

Evidence: The definition averages the proportion of atomic facts supported by knowledge source C; the preceding paragraph explicitly distinguishes support by a chosen source from global truth.

Limits: Its knowledge source need not be the exact evidence supplied during generation. This establishes prior source-relative claim assessment, not an ESRS-specific diagnosis scheme.

## CIT-013: ragas2024

Occurrence: `04_research_gap_verification.md:22`, What the original sources establish.

RAGAS extracts statements, checks whether they can be inferred from supplied context, and compares its metrics with human judgments in WikiEval.

Verdict: DIRECT. Source: [PDF](sources/ragas2024/original.pdf), PDF pages 2–4, Sections 3–4, especially Faithfulness and WikiEval.

Evidence: Faithfulness is the proportion of extracted statements supported by context. The original paper describes statement extraction and Yes/No verification, followed by human comparisons on question-context-answer examples.

Limits: The paper supports the metric's original definition. Exact behavior of the BACE experiment's installed RAGAS version must be established from frozen implementation records. An entailment criterion can in principle reject a changed qualifier.

## CIT-014: ragchecker2024

Occurrence: `04_research_gap_verification.md:23`, What the original sources establish.

RAGChecker uses claim extraction and entailment for retrieval and generation diagnostics, including native faithfulness, and performs human preference meta-evaluation.

Verdict: DIRECT. Source: [PDF](sources/ragchecker2024/original.pdf), PDF pages 3–6, Sections 3.2, 3.3.3 and 4.2.

Evidence: Section 3.3.3 defines faithfulness through claims entailed by retrieved chunks. Its other diagnostics distinguish sources of unsupported or incorrect output. Section 4.2 compares response-pair preferences for correctness, completeness and overall assessment.

Limits: The full metric suite includes ground-truth-dependent metrics; the BACE experiment uses native faithfulness. The original study's preference validation does not validate BACE's diagnoses or establish accuracy in ESRS disclosure drafting.

## CIT-015: refchecker2024_arxiv

Occurrence: `04_research_gap_verification.md:24`, What the original sources establish.

RefChecker assesses claim-triplets against references using Entailment, Contradiction and Neutral labels, including settings where input context is the reference.

Verdict: DIRECT. Source: [PDF](sources/refchecker2024_arxiv/original.pdf), PDF page 4, Sections 3.1–3.2 and Figures 3–4; arXiv v1.

Evidence: Noisy Context and Accurate Context both use the supplied input context as reference. A triplet inferred from the reference is entailed; an incompatible triplet is contradicted; insufficient reference information leads to Neutral.

Limits: Verified against arXiv:2405.14486v1, not a claimed journal or conference version. Its Neutral category must not be equated automatically with one BACE diagnosis.

## CIT-016: alce2023

Occurrence: `04_research_gap_verification.md:25`, What the original sources establish.

ALCE evaluates support using concatenated cited passages and asks human annotators whether a joint citation set fully supports a statement.

Verdict: DIRECT. Source: [PDF](sources/alce2023/original.pdf), PDF page 4, Section 3.3; PDF page 15, Appendix F.2.

Evidence: Citation recall checks entailment from concat(C_i). The authors explicitly state that citation precision does not require a minimal set. Human citation-recall annotation assesses the joint cited evidence.

Limits: This is prior multi-source support evaluation. BACE's explicit minimal support-set specification is a design distinction from this formulation, not evidence of a first-ever multi-evidence method or of greater accuracy.

## CIT-017: veriscore2024

Occurrence: `04_research_gap_verification.md:26`, What the original sources establish.

VeriScore explicitly retains necessary spatial and temporal modifiers, uses surrounding context to extract self-contained claims, and requires support for the complete claim.

Verdict: DIRECT. Source: [PDF](sources/veriscore2024/original.pdf), PDF page 3, Sections 2.1.2–2.3; PDF pages 18–19, Appendix C.

Evidence: The definition of a verifiable claim includes necessary modifiers. The extraction method resolves references using a sliding context window. Verification requires every part of the claim to be supported and no part to be contradicted, with evidence retrieved through web search.

Limits: This directly defeats a blanket claim that previous factuality methods ignore material qualifiers. Its web-retrieved evidence universe differs from BACE's generator-visible evidence boundary.

## CIT-018: claimify2025

Occurrence: `04_research_gap_verification.md:27`, What the original sources establish.

Claimify treats entailment, coverage and decontextualization as extraction criteria and resolves referential and structural ambiguity using context.

Verdict: DIRECT. Source: [PDF](sources/claimify2025/original.pdf), PDF pages 2–5, Sections 2.1–2.3 and 3.1–3.4.

Evidence: The paper examines how omitted context changes retrieved evidence and verification outcomes. Its examples include relative time, ambiguous actors and relations between company-specific activities. Claimify includes selection, disambiguation and decomposition stages.

Limits: Context preservation and ambiguity handling are established prior work. The paper primarily addresses claim extraction and its evaluation; it does not by itself establish the quality of BACE's extraction or diagnoses.

## CIT-019: dndscore2025

Occurrence: `04_research_gap_verification.md:28`, What the original sources establish.

DnDScore examines the interaction of decomposition and decontextualization and verifies subclaims with their contextualized forms.

Verdict: DIRECT. Source: [PDF](sources/dndscore2025/original.pdf), PDF pages 2–4, Figure 1 and Section 3.

Evidence: The study motivates contextual verification by showing that adding or omitting context can change what is checked or counted. It proposes joint decomposition and decontextualization and a verifier that distinguishes the target subclaim from contextual information.

Limits: Segmentation and contextualization can change factuality scores, so BACE's score gaps cannot be attributed solely to stricter boundary judgments. DOI metadata pagination differs from the publisher page and PDF; use the corrected publisher pagination and PDF-page locators.

## CIT-020: chatreport2023

Occurrence: `04_research_gap_verification.md:29`, What the original sources establish.

ChatReport provides source-linked sustainability report analysis, human support and attribution evaluation, and an example of false concatenation of separate retrieved chunks.

Verdict: DIRECT. Source: [PDF](sources/chatreport2023/original.pdf), PDF pages 3–6, Sections 3.3–3.4 and 5–5.4.

Evidence: Human content annotation counts extrapolation or partial support as hallucination. Source annotation additionally checks references. Section 5.2 illustrates erroneous concatenation of distinct chunks; Section 5.4 describes the expert-annotated support dataset.

Limits: This is direct domain precedent for evidence support, human evaluation and erroneous synthesis. The inspected work focuses on TCFD-oriented report analysis and question answering; it should not be recast as an absence of domain evaluation.

## CIT-021: susgen2025

Occurrence: `04_research_gap_verification.md:30`, What the original sources establish.

SusGen-GPT includes RAG-based sustainability report generation and evaluates generated reports using reference-text metrics while acknowledging limited expert evaluation.

Verdict: DIRECT. Source: [PDF](sources/susgen2025/original.pdf), PDF pages 3–5, Section 3 and Section 3.4; PDF page 8, Limitations.

Evidence: Section 3.4 lists BERTScore, ROUGE, METEOR and BLEU-N for sustainability report generation. The limitations distinguish expert analysis of some cases from reliance on automated metrics at scale.

Limits: This characterizes the stated evaluation, not a proof that the system cannot preserve evidence boundaries. Generation quality and evaluator validity are different targets. Preserve the original PDF spelling Hejia Huang in the working bibliography.

## CIT-022: esghrag2025

Occurrence: `04_research_gap_verification.md:31`, What the original sources establish.

ESGH-RAG generates ESG reports and evaluates report-level characteristics and expert feasibility, with additional qualitative expert feedback.

Verdict: DIRECT. Source: [PDF](sources/esghrag2025/original.pdf), PDF pages 16–18, Sections 4.4–4.6 and Table 5.

Evidence: Table 5 compares model, retrieval, content sources, report characteristics and expert feasibility; Section 4.6 presents third-party and company feedback.

Limits: The paper's reported compliance and feasibility claims are not independent proof of legal compliance or claim-level support accuracy. The table here describes its evaluation design only.

## CIT-023: esgbench2026

Occurrence: `04_research_gap_verification.md:32`, What the original sources establish.

ESG-Bench provides human-annotated ESG question answering with support-related labels, supporting source pages and adjudication of disagreements.

Verdict: DIRECT. Source: [PDF](sources/esgbench2026/original.pdf), PDF pages 2–4, benchmark construction, Human Annotation and Benchmark Analysis and Usage.

Evidence: The annotation protocol assigns Correct, Hallucination, Incomplete or Answer Not Found; it checks factual accuracy and supporting source pages. Two annotators review each response and another resolves disagreement. The benchmark also supports hallucination-mitigation evaluation.

Limits: This defeats a claim that ESG-specific human hallucination benchmarks are absent. Report-based QA and mitigation evaluation are not identical to BACE's generated-disclosure and conditional candidate-EC judgment tasks.

## CIT-024: europe2026

Occurrence: `04_research_gap_verification.md:33`, What the original sources establish.

Forster and colleagues use RAG to extract ESRS-aligned numerical indicators from corporate reports and validate extracted values against external and human-annotated data.

Verdict: DIRECT. Source: [PDF](sources/europe2026/original.pdf), PDF pages 2 and 13–14, framework description and Methods: generation and Validation.

Evidence: The generation stage returns requested indicator values and units in JSON. Validation compares extracted numerical values with an external ESG dataset and manually annotated values, and explicitly discusses the reference datasets' limitations.

Limits: The evaluation target is numerical extraction from existing reports. It is distinct from auditing claims in newly drafted disclosures. The presence of the same broad population scale does not by itself establish a data lineage relationship with BACE.

## CIT-025: ares2024

Occurrence: `04_research_gap_verification.md:35`, What the original sources establish.

ARES combines learned RAG judges with a human-annotated validation set and prediction-powered inference.

Verdict: DIRECT. Source: [PDF](sources/ares2024/original.pdf), PDF page 2, framework overview.

Evidence: The overview describes synthetic question-answer generation, separate relevance and faithfulness judges, and use of human annotations to correct model-based estimates and compute uncertainty intervals.

Limits: Human-calibrated automated assessment is established prior work. BACE's company-cluster sampling intervals do not implement ARES's estimator or account for judge errors in the same way.

## CIT-026: ragtruth2024

Occurrence: `04_research_gap_verification.md:38`, What the original sources establish.

RAGTruth distinguishes evident and subtle conflicts and evident and subtle introductions of unsupported information in RAG outputs.

Verdict: DIRECT. Source: [PDF](sources/ragtruth2024/original.pdf), PDF page 3, Sections 3.1–3.2.

Evidence: The taxonomy includes changes to contextual meaning and unsupported inferred details. Data construction covers question answering, data-to-text generation and summarization under provided-context conditions.

Limits: Failure taxonomy and subtle unsupported inference are prior concepts. A different label set is not itself proof of scientific novelty or improved diagnosis.

## CIT-027: factscore2023

Occurrence: `04_research_gap_verification.md:61`, Revised gap formulation.

Claim-level assessment of source support is established, and prior methods explicitly address context preservation and joint-source attribution.

Verdict: QUALIFIED. Source: [PDF](sources/factscore2023/original.pdf), PDF page 3, Section 3.1, Key Idea 2 and Definition.

Evidence: The definition averages the proportion of atomic facts supported by knowledge source C; the preceding paragraph explicitly distinguishes support by a chosen source from global truth.

Limits: Its knowledge source need not be the exact evidence supplied during generation. This establishes prior source-relative claim assessment, not an ESRS-specific diagnosis scheme. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-028: veriscore2024

Occurrence: `04_research_gap_verification.md:61`, Revised gap formulation.

Claim-level assessment of source support is established, and prior methods explicitly address context preservation and joint-source attribution.

Verdict: QUALIFIED. Source: [PDF](sources/veriscore2024/original.pdf), PDF page 3, Sections 2.1.2–2.3; PDF pages 18–19, Appendix C.

Evidence: The definition of a verifiable claim includes necessary modifiers. The extraction method resolves references using a sliding context window. Verification requires every part of the claim to be supported and no part to be contradicted, with evidence retrieved through web search.

Limits: This directly defeats a blanket claim that previous factuality methods ignore material qualifiers. Its web-retrieved evidence universe differs from BACE's generator-visible evidence boundary. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-029: claimify2025

Occurrence: `04_research_gap_verification.md:61`, Revised gap formulation.

Claim-level assessment of source support is established, and prior methods explicitly address context preservation and joint-source attribution.

Verdict: QUALIFIED. Source: [PDF](sources/claimify2025/original.pdf), PDF pages 2–5, Sections 2.1–2.3 and 3.1–3.4.

Evidence: The paper examines how omitted context changes retrieved evidence and verification outcomes. Its examples include relative time, ambiguous actors and relations between company-specific activities. Claimify includes selection, disambiguation and decomposition stages.

Limits: Context preservation and ambiguity handling are established prior work. The paper primarily addresses claim extraction and its evaluation; it does not by itself establish the quality of BACE's extraction or diagnoses. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-030: alce2023

Occurrence: `04_research_gap_verification.md:61`, Revised gap formulation.

Claim-level assessment of source support is established, and prior methods explicitly address context preservation and joint-source attribution.

Verdict: QUALIFIED. Source: [PDF](sources/alce2023/original.pdf), PDF page 4, Section 3.3; PDF page 15, Appendix F.2.

Evidence: Citation recall checks entailment from concat(C_i). The authors explicitly state that citation precision does not require a minimal set. Human citation-recall annotation assesses the joint cited evidence.

Limits: This is prior multi-source support evaluation. BACE's explicit minimal support-set specification is a design distinction from this formulation, not evidence of a first-ever multi-evidence method or of greater accuracy. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-031: chatreport2023

Occurrence: `04_research_gap_verification.md:62`, Revised gap formulation.

In sustainability applications, ChatReport evaluates answer support and identifies erroneous synthesis, while ESG-Bench provides human-annotated hallucination assessment.

Verdict: QUALIFIED. Source: [PDF](sources/chatreport2023/original.pdf), PDF pages 3–6, Sections 3.3–3.4 and 5–5.4.

Evidence: Human content annotation counts extrapolation or partial support as hallucination. Source annotation additionally checks references. Section 5.2 illustrates erroneous concatenation of distinct chunks; Section 5.4 describes the expert-annotated support dataset.

Limits: This is direct domain precedent for evidence support, human evaluation and erroneous synthesis. The inspected work focuses on TCFD-oriented report analysis and question answering; it should not be recast as an absence of domain evaluation. Grouped citation: this source supports its stated component, not every component of the combined sentence.

## CIT-032: esgbench2026

Occurrence: `04_research_gap_verification.md:62`, Revised gap formulation.

In sustainability applications, ChatReport evaluates answer support and identifies erroneous synthesis, while ESG-Bench provides human-annotated hallucination assessment.

Verdict: QUALIFIED. Source: [PDF](sources/esgbench2026/original.pdf), PDF pages 2–4, benchmark construction, Human Annotation and Benchmark Analysis and Usage.

Evidence: The annotation protocol assigns Correct, Hallucination, Incomplete or Answer Not Found; it checks factual accuracy and supporting source pages. Two annotators review each response and another resolves disagreement. The benchmark also supports hallucination-mitigation evaluation.

Limits: This defeats a claim that ESG-specific human hallucination benchmarks are absent. Report-based QA and mitigation evaluation are not identical to BACE's generated-disclosure and conditional candidate-EC judgment tasks. Grouped citation: this source supports its stated component, not every component of the combined sentence.
