# Research gap verification

Checked on 29 September 2026. Scope: a targeted original-source review for the agreed disclosure-evidence framing, not a systematic review or a proof of priority.

## Finding

BACE should be positioned as a reporting-specific operationalization and integration of established claim-evaluation ideas, with an empirical investigation of generated disclosures under a defined supplied-evidence boundary.
The reviewed literature already contains source-relative factual precision, contextual claim extraction, joint-source attribution and human evaluation of unsupported sustainability answers.
The presence of these ideas in prior work narrows the novelty claim; it does not settle whether BACE's particular operationalization is useful or valid.

The defensible research question concerns how support, permitted inference and unsupported synthesis are characterized in the evaluated disclosure workflow, and how those assessments compare with other evaluators and independent reviewers.
The saved experiment provides automated descriptive evidence; the planned human review can assess conditional judgment validity once its results are completed and checked.
It does not isolate the incremental causal effect of each BACE component or establish comparative accuracy from native-score differences.

## What the original sources establish

Citation keys resolve to [references.bib](references.bib). Original PDFs, exact locators and qualifications are indexed in [the source index](literature/SOURCE_INDEX.md) and [citation ledger](literature/citation_ledger.md).

| Source | Verified capability or finding | Consequence for BACE positioning |
|---|---|---|
| FActScore | FActScore decomposes generated text into atomic facts and defines factual precision relative to a specified knowledge source. [@factscore2023] | Claim-level assessment and source-relative support are established concepts. |
| RAGAS | RAGAS extracts statements, checks whether they can be inferred from supplied context, and compares its metrics with human judgments in WikiEval. [@ragas2024] | The baseline already uses a support criterion. Its capacity to handle a particular boundary must be tested rather than assumed absent. |
| RAGChecker | RAGChecker uses claim extraction and entailment for retrieval and generation diagnostics, including native faithfulness, and performs human preference meta-evaluation. [@ragchecker2024] | Diagnostics and human meta-evaluation are prior contributions. Compare the actual native metric used in BACE's experiment, not the full framework as if all its metrics were evaluated. |
| RefChecker | RefChecker assesses claim-triplets against references using Entailment, Contradiction and Neutral labels, including settings where input context is the reference. [@refchecker2024_arxiv] | Insufficient evidence is already distinguished from contradiction. This reading uses the identified arXiv v1 source. |
| ALCE | ALCE evaluates support using concatenated cited passages and asks human annotators whether a joint citation set fully supports a statement. [@alce2023] | Joint evidence support is established. ALCE explicitly does not require a minimal citation set; BACE's minimal support-set specification is a design difference from this formulation. |
| VeriScore | VeriScore explicitly retains necessary spatial and temporal modifiers, uses surrounding context to extract self-contained claims, and requires support for the complete claim. [@veriscore2024] | Preserving material qualifiers is not a new general principle introduced by BACE. The two methods have different evidence universes. |
| Claimify | Claimify treats entailment, coverage and decontextualization as extraction criteria and resolves referential and structural ambiguity using context. [@claimify2025] | Context preservation, ambiguity handling and the effect of omitted context on verification must be credited to prior work. |
| DnDScore | DnDScore examines the interaction of decomposition and decontextualization and verifies subclaims with their contextualized forms. [@dndscore2025] | Claim construction can affect factuality scores. BACE's score differences cannot be attributed solely to stricter support decisions. |
| ChatReport | ChatReport provides source-linked sustainability report analysis, human support and attribution evaluation, and an example of false concatenation of separate retrieved chunks. [@chatreport2023] | Domain-specific support evaluation and erroneous synthesis are direct precedents, not newly discovered categories of concern. |
| SusGen-GPT | SusGen-GPT includes RAG-based sustainability report generation and evaluates generated reports using reference-text metrics while acknowledging limited expert evaluation. [@susgen2025] | A relevant distinction is the evaluation target and evidence-support representation, not whether report generation has previously been attempted. |
| ESGH-RAG | ESGH-RAG generates ESG reports and evaluates report-level characteristics and expert feasibility, with additional qualitative expert feedback. [@esghrag2025] | Prior generation work includes human input; do not describe all existing evaluation as purely automated or purely lexical. |
| ESG-Bench | ESG-Bench provides human-annotated ESG question answering with support-related labels, supporting source pages and adjudication of disagreements. [@esgbench2026] | A broad claim that ESG-specific human hallucination benchmarks are missing is untenable. BACE addresses a different unit and workflow. |
| ESRS-aligned indicator extraction | Forster and colleagues use RAG to extract ESRS-aligned numerical indicators from corporate reports and validate extracted values against external and human-annotated data. [@europe2026] | The domain already has ESRS-oriented RAG with validation. Numerical extraction and newly drafted disclosure claims remain distinct evaluation targets. |

ARES combines learned RAG judges with a human-annotated validation set and prediction-powered inference. [@ares2024]
This is further precedent for calibrating automated assessment against humans; BACE's sampling intervals do not provide the same correction for judge errors.

RAGTruth distinguishes evident and subtle conflicts and evident and subtle introductions of unsupported information in RAG outputs. [@ragtruth2024]
Its taxonomy is relevant when explaining how BACE's diagnostic categories relate to earlier distinctions.

## Contribution that remains supportable

The following are design and empirical contributions to substantiate, not claims that every component is unprecedented:

1. A reporting-focused operational definition that preserves material qualifiers and distinguishes legitimate inference from unsupported changes in meaning.
2. An explicit EC–DC support representation, with requested minimal sufficient support sets and separate direct/inferred support labels.
3. An integrated account of disclosure support, use of supplied evidence and ordered unsupported-claim diagnoses.
4. An empirical analysis across the defined company-year-task cases, with paired native evaluator comparisons and independent judgment validation at its actual scope.

The first three points are grounded in the [BACE method definition](../docs/generation_evaluation.md), particularly Sections 2–8, and the [frozen support prompt](../BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt).
The prompt requests minimal support sets; this request does not establish that every returned set is minimal, complete or correct.
The empirical scope and limitations are in the [evidence map](02_evidence_map.md) and [human-validation guide](../BACE/analysis/validation/README.md).

To claim improved accuracy or incremental diagnostic value, the paper would need evidence aligned with that specific claim.
The existing native-score comparison demonstrates differences in assessment.
The current human-review design can assess BACE judgments conditional on supplied claims and candidate ECs; it does not independently establish extraction quality, candidate recall or superiority over the comparators.
No new experiment is implied by this review. The manuscript can retain a narrower contribution if stronger evidence is not available.

## Revised gap formulation

Claim-level assessment of source support is established, and prior methods explicitly address context preservation and joint-source attribution. [@factscore2023; @veriscore2024; @claimify2025; @alce2023]
In sustainability applications, ChatReport evaluates answer support and identifies erroneous synthesis, while ESG-Bench provides human-annotated hallucination assessment. [@chatreport2023; @esgbench2026]
These studies motivate a more specific measurement question for disclosure drafting: how should support assessments account for material reporting qualifiers and distinguish valid inference from unsupported synthesis when the evidence universe is fixed to the material supplied to the generator?
This study examines that question through BACE's explicit support representation, reporting-oriented diagnoses and comparison with native evaluator scores, with independent validation restricted to the judgments actually reviewed.

This formulation establishes the motivation and scope of the present investigation.
It does not assert that no previous study has considered the component ideas or that this targeted search establishes an exclusive first.

## Search and verification scope

- Starting sources: the project's earlier Introduction evidence map, original RAG evaluator papers and directly relevant sustainability-generation studies.
- Discovery: recorded Crossref bibliographic queries, OpenAlex ranked searches, exact-title follow-ups, the official NeurIPS index and original-paper references. The [query log](literature/SEARCH_LOG.md) records the exact requests and returned hit sets.
- Selection: retain direct evaluators, work on contextual claim extraction or evidence combination, and sustainability studies that bear on the proposed domain gap. Original full text was required for a positive capability statement.
- Full-text access: publisher/conference PDFs and a version-identified arXiv manuscript. Duplicate preprint/published copies of Claimify and RAGChecker are retained as retrieval artifacts; the published versions support the citations above.
- Verification: read the relevant original methods, definitions, examples or annotation instructions; inspect the source version and bibliographic metadata; retain source hashes and page locators. Two key pages were also inspected visually to confirm column and annotation-protocol interpretation.
- Limits: bounded ranked results, noisy broad searches, no exhaustive screening or citation-network closure. OpenAlex queries containing Boolean-looking syntax returned broad ranked sets; their results are not treated as an exhaustive Boolean intersection. Failed requests were not counted as zero matches.

The Consensus connector was unavailable. Some Crossref search requests returned HTTP 429; successful exact-source discovery used other recorded routes.
These limitations do not prevent a source-specific comparison, but they preclude a systematic-review or absence-of-literature claim.

## Unresolved access and metadata

**UNVERIFIED_FULL_TEXT:** EcoSmartGuide, DOI [10.1109/ECBIOS61468.2024.10885500](https://doi.org/10.1109/ECBIOS61468.2024.10885500), has verified bibliographic metadata but no substantive full text was retrieved through the attempted publisher route. Its detailed evaluation capabilities remain unknown in this audit.

**UNVERIFIED_FULL_TEXT:** Self-Evaluating Agentic Framework Using Retrieval-Augmented Generation for Accountable Environmental Sustainability Communication, DOI [10.1051/epjconf/202637001014](https://doi.org/10.1051/epjconf/202637001014), has verified bibliographic metadata; both the publisher landing page and indexed publisher PDF returned HTTP 403. This potentially close comparison remains unresolved and must be considered before a broad novelty claim.

Bibliographic checks found a DnDScore page-range discrepancy between DOI metadata and the ACL publisher page/PDF, and author-name presentation differences for FActScore, SusGen-GPT and RAGChecker. The working bibliography uses the inspected original-paper forms, with each change recorded in [metadata corrections](literature/metadata_corrections.json).
The available Crossref update/relation fields for the checked published sources did not surface a correction or retraction notice. This is a bounded metadata/landing-page check, not a guarantee that no notice exists elsewhere.

The background's general reporting/ESRS citation task L1 remains outside this step's completed verification. It remains visibly pending in the research foundation.
