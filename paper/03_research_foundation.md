# BACE research foundation

Version 2, 29 September 2026. Research-gap wording revised after original-source verification.

The author has confirmed the focus on disclosure evidence credibility and factual boundaries.
The paragraphs below are working formulations of the research elements, not separate headings required in the submitted paper.
They will inform the Introduction after citation verification and integration with the final results.

The marker [L1] remains a pending background-citation task, not a verified citation.
Other citation keys resolve to [references.bib](references.bib); their exact occurrences and source locators are recorded in the [citation ledger](literature/citation_ledger.md).
The [research gap verification](04_research_gap_verification.md) records the targeted search, original-source findings and unresolved access.

## Working title

Evidence boundaries in AI-generated corporate sustainability disclosures

## Research background

Corporate sustainability disclosures provide information about companies' environmental and social impacts, as well as related policies, risks and actions. Their usefulness depends in part on whether readers can substantiate the factual statements they contain. The 2023 European Sustainability Reporting Standards (ESRS) articulate requirements for faithful representation and verifiability that make this evidentiary basis important to disclosure preparation and review. [L1]

Generative artificial intelligence (AI) has been explored for sustainability-information analysis in ChatReport and disclosure drafting in SusGen-GPT. [@chatreport2023; @susgen2025]
Retrieval-augmented generation (RAG) provides a language model with retrieved external context for generating a response. [@ragas2024]
In corporate reporting, this offers a way to condition drafting on company evidence. The resulting statements still need to be assessed against that evidence, including the qualifications that determine their meaning.

## Research problem

A disclosure can retain recognizable details from a source while changing the proposition that the source supports. For example, a statement about an action in an earlier year does not by itself establish that the action continues in the target reporting year. Evidence about one subsidiary also does not necessarily establish a group-wide practice. These are conceptual examples, not findings from the experiment.

The research problem is whether generated disclosures preserve such factual boundaries when converting supplied evidence into reporting statements. Material boundaries include the entity and reporting period, organizational scope, metric and degree of certainty. Unsupported relationships between separately supported facts can also change the meaning of a disclosure. BACE operationalizes these concerns through claim-level support assessment and diagnosis, as defined in the [method specification](../docs/generation_evaluation.md).

## Research gap

Existing approaches already evaluate claim-level support relative to evidence: FActScore uses a specified knowledge source, while RAGAS and RAGChecker assess faithfulness to retrieved context. [@factscore2023; @ragas2024; @ragchecker2024]
VeriScore explicitly preserves necessary spatial and temporal modifiers, Claimify addresses contextual ambiguity, and ALCE evaluates whether joint cited evidence supports a statement. [@veriscore2024; @claimify2025; @alce2023]
Context preservation and evidence combination therefore form part of the methodological foundation for this study.

Sustainability-specific evidence evaluation also has direct precedents. ChatReport uses human support and attribution judgments and documents false concatenation of retrieved chunks; ESG-Bench supplies human-annotated support and hallucination assessments for ESG question answering. [@chatreport2023; @esgbench2026]
These studies motivate a more specific measurement question for disclosure drafting: how should support assessments account for material reporting qualifiers and distinguish valid inference from unsupported synthesis when the evidence universe is fixed to the material supplied to the generator?
This study examines that question through BACE's explicit support representation, reporting-oriented diagnoses and comparison with native evaluator scores, with independent validation restricted to the judgments actually reviewed.

This is a domain-specific measurement and empirical contribution. The targeted review does not establish an exclusive first, and the detailed capabilities of two relevant inaccessible works remain unresolved in the gap-verification report.

## Research purpose

This study assesses the evidentiary support of AI-generated sustainability disclosures, characterizes the unsupported claims identified by boundary-aware evaluation, and examines how support assessments vary across evaluation methods.

We develop and apply Boundary-Aware Claim Evaluation (BACE) to link disclosure claims to claims extracted from the evidence supplied to the generator. We use this representation to describe support patterns and unsupported-claim diagnoses in a fixed generation workflow, then compare BACE assessments with the native faithfulness scores of RAGChecker and RAGAS. Independent human assessment is intended to evaluate BACE's support and diagnostic judgments conditional on the supplied disclosure claims and candidate evidence claims; completed validation results remain to be incorporated.

## Research questions

Central research question:

> To what extent do AI-generated sustainability disclosures preserve the factual boundaries of the evidence supplied to the model?

| ID | Research question | Function |
|---|---|---|
| RQ1 | To what extent are generated sustainability disclosures supported by the evidence supplied to the model? | Quantify BACE-assessed support and describe variation across disclosure tasks and companies. |
| RQ2 | What types of evidence-boundary failures does BACE identify, and how are they distributed across disclosure tasks? | Characterize automated diagnoses and inspect their meaning in traceable cases. |
| RQ3 | How do BACE assessments differ from those of general-purpose RAG evaluators? | Examine native-score differences, claim inventories and specific disagreements on the same disclosures. |
| RQ4 | How closely do BACE support and diagnostic judgments agree with independent human assessments? | Assess conditional judgment validity, subject to completion of the specified human-validation study. |

RQ1–RQ3 currently rely on automated observations; RQ4 informs confidence in their interpretation within its validation scope.
These questions organize the completed experiment and subsequent validation for writing purposes.
They are not presented as preregistered hypotheses.

## Contribution statement

The study adapts and integrates established claim-evaluation principles for sustainability disclosure drafting. BACE specifies a traceable support representation, distinguishes direct from inferred support, and organizes unsupported claims into reporting-oriented diagnoses. The empirical contribution concerns support patterns and differences among automated assessments across the defined reporting tasks. These contributions address the substantiation and review of generated disclosure information.

The [verified comparison](04_research_gap_verification.md) identifies the established component ideas and the narrower contribution that BACE can substantiate.
Any contribution based on human validation must describe the completed results and their conditional scope.
The experiment does not establish changes in real reporting practice or downstream sustainability outcomes.

## Scope of the argument

The study addresses evidentiary support as one component of disclosure reliability.
It evaluates one fixed retrieval and generation workflow across 30 companies, five reporting years and 12 tasks based on the 2023 ESRS edition.
The [evidence map](02_evidence_map.md) records the analyzed cohort and quantitative results.

The evidence universe is the material actually supplied to the generator.
The judgments depend on subsequent claim extraction and candidate selection.
An unsupported judgment therefore does not establish external falsity, and agreement on the supplied claim inputs does not independently validate those earlier transformations.

## Citation tasks

| Task | Claim to support or question to resolve | Sources | Current status |
|---|---|---|---|
| L1 | Reporting purpose; faithful representation and verifiability. | Christensen, Hail and Leuz (2021); Commission Delegated Regulation (EU) 2023/2772, ESRS 1, Appendix B. | Check the exact passages and distinguish the study's 2023 standard edition from claims about current legal applicability. |
| L2 | Generative AI applications in sustainability analysis and drafting. | ChatReport; SusGen-GPT. | Original full-text support verified for the specific application statement above; widespread adoption is not claimed. |
| L3 | RAG supplies retrieved context for generation. | RAGAS, Section 3; complementary taxonomy evidence in RAGTruth is recorded in the review. | Original full-text support verified for the mechanism stated above. |
| L4 | Existing approaches operationalize faithfulness, entailment and factual precision. | RAGAS; RAGChecker; FActScore; relevant context-preservation and joint-evidence methods. | Definitions checked against original texts. Exact frozen implementation behavior remains a separate Methods concern. |
| L5 | The precise contribution of BACE relative to prior work. | The verified comparison and the source index. | A defensible integration/domain-evaluation framing is established; exclusive priority and comparative superiority are not established. Two relevant full texts remain inaccessible. |

The [existing Introduction evidence map](../docs/main/introduction/introduction_logic_chain_and_evidence.md) supplies the source leads and earlier reasoning.
The research gap requires comparison across papers; no single citation establishes a field-wide absence.

## Placement in the eventual Introduction

| Paragraph | Function | Source in this document |
|---|---|---|
| 1 | Establish the sustainability reporting problem and its stakes. | Research background, first paragraph; L1. |
| 2 | Explain AI-assisted drafting and the evidence-boundary problem. | Research background, second paragraph; Research problem; L2–L3. |
| 3 | Situate existing evaluation and state the precise unresolved question. | Research gap; L4–L5. |
| 4 | State the study aim, approach, scope and evidence-supported contribution. | Research purpose, research questions and contribution statement, updated to the final evidence. |

## Editorial pass

An initial purpose formulation was: "The purpose of this study is to provide a comprehensive assessment of evidentiary reliability in AI-generated sustainability reporting through a boundary-aware evaluation framework."

The wording was too broad: "comprehensive" exceeded the study scope, "reliability" obscured the measured construct, and the sentence did not identify the analyses.

The revised formulation is: "This study assesses the evidentiary support of AI-generated sustainability disclosures, characterizes the unsupported claims identified by boundary-aware evaluation, and examines how support assessments vary across evaluation methods."

The final prose above retains the distinction between automated observations and independently validated judgments, defines abbreviations, and removes promotional claims.
