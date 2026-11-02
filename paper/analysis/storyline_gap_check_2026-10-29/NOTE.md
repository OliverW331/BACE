# Storyline premise and research-gap check

Date: 29 October 2026. Status: working argument for author confirmation, not an approved manuscript revision or a systematic literature review.

## Assessment

Commercial AI-assisted sustainability disclosure drafting is a supportable motivation. The inspected sources do not establish how widely it is adopted, how fast the market is growing, or that sustainability reporting receives more AI attention than other report types. Distinguish advertised product availability, a co-authored implementation case, and independently measured adoption.

The proposed absence claim is too broad. Prior work includes RAG-based sustainability report generation, a report-generation benchmark, source-linked sustainability QA with human support judgments, and a domain-specific hallucination benchmark. The contribution must therefore concern a specified measurement target and empirical setting, not an absence of all sustainability-specific evaluation.

## Proposed argument progression

1. **Practical motivation:** commercial products and research systems already assist sustainability disclosure drafting and report analysis. Use named, dated examples rather than unverified market-size or adoption-growth claims.
2. **Reporting problem:** frame evidence credibility as a research concern. A sourced fact can acquire a different reporting year, entity, scope, metric boundary, or stronger relationship when turned into a disclosure. These are conceptual examples until tied to verified experimental cases.
3. **Mechanism and unresolved question:** retrieval supplies material for generation; it does not itself establish that every resulting proposition follows from that material. Ask whether the generated disclosure retains the complete meaning of its supplied evidence.
4. **Existing foundations:** acknowledge report-generation evaluation, report-analysis QA benchmarks, and general claim-support methods. Do not describe all existing evaluators as lexical matching or claim that context preservation and joint evidence are new ideas.
5. **Specific assessment target:** examine task-level disclosure drafting under a fixed supplied-evidence universe, using explicit DC-to-EC support sets, direct versus inferred support, and reporting-oriented unsupported diagnoses.
6. **Empirical answer:** characterize support patterns and native evaluator disagreements in the saved workflow, with source-grounded counterexamples and independent human judgment validation at the scope actually completed.
7. **Bounded implication:** motivate more explicit substantiation and review of AI-assisted disclosure. Do not infer industry-wide effects, real-world sustainability outcomes, legal compliance, or comparative accuracy from native score differences.

## Working research question

To what extent are the complete factual meanings of AI-generated sustainability disclosure claims supported by the evidence supplied to the generator, how is that support structured, and what diagnostic patterns characterize unsupported claims?

Scope correction after author feedback on 29 October 2026: factual boundary distortion and evidence conflation are two prominent empirical diagnostic categories, not the scope of the entire framework. BACE also distinguishes non-disclosure statements, contradictions, inferential inflation and unsupported novelty. The investigation covers supplied-evidence support, direct versus inferred support, support-set structure and unsupported diagnoses. It does not measure every aspect of reporting quality. See the original-source comparison in `../related_work_comparison_2026-10-29/REPORT.md`.

## Working contribution formulation

BACE integrates established claim-evaluation principles into an explicit, reporting-oriented support representation. The study uses that representation to investigate supplied-evidence support and diagnostic patterns across defined sustainability disclosure tasks, and to examine disagreement with native RAG evaluator scores. This is a methodological integration and empirical measurement contribution, not a verified exclusive first or a validated end-to-end assessment of complete sustainability reports.

## Original-source verification records

The academic passages below were reinspected in local full texts on 29 October 2026. Their publisher versions were originally retrieved on 29 September 2026. Online publisher records/PDF entry points were also checked on 29 October; the browser's academic extracts were truncated, so full-text support relies on the identified local original PDFs and passages, not abstracts alone.

| Proposed claim | Identifier and version | Supporting original locator | Verdict and qualification |
| --- | --- | --- | --- |
| A commercial example combines generative AI, RAG and text-to-SQL for ESG reporting. | AWS/Gardenia, co-authored implementation blog, published 11 June 2025; https://aws.amazon.com/blogs/machine-learning/how-gardenia-technologies-helps-customers-create-esg-disclosure-reports-75-faster-using-agentic-generative-ai-on-amazon-bedrock/ | Opening implementation description, paragraphs naming Report GenAI, Amazon Bedrock, RAG and text-to-SQL; accessed 29 October 2026. | DIRECT for a documented solution; QUALIFIED for adoption. Vendor/co-developer account, not independent market evidence. No efficiency percentage is adopted here. |
| A reporting platform offers AI-assisted sustainability narrative drafting. | Workiva Support Center, "Use Workiva AI for sustainability reporting," updated 13 August 2026; https://support.workiva.com/hc/en-us/articles/48891676353428-Use-Workiva-AI-for-sustainability-reporting | Opening capabilities, Framework Intelligence distinction, and Sustainability Disclosure Agent section; accessed 29 October 2026. | DIRECT for documented functionality. Do not infer universal availability or error-free/compliant output. The source explicitly disclaims error-free content and professional advice. |
| Sustainability report generation and a dedicated generation benchmark already have research precedents. | SusGen-GPT, DOI 10.18653/v1/2025.findings-naacl.66, NAACL Findings 2025 version of record. | `paper/literature/sources/susgen2025/original.pdf`, PDF pp. 3–5, Section 3/3.4; p. 9, Limitations. Extracted text near lines 154–174, 302–322 and 533–548. | DIRECT. Section 3.4 evaluates report generation using BERTScore, ROUGE, METEOR and BLEU-N; limitations acknowledge limited expert evaluation at scale. This does not prove that the system cannot preserve boundaries. |
| Sustainability-specific human support/attribution evaluation and unsupported synthesis analysis predate BACE. | ChatReport, DOI 10.18653/v1/2023.emnlp-demo.3, EMNLP 2023 version of record. | `paper/literature/sources/chatreport2023/original.pdf`, PDF pp. 3–6, Sections 3.3–3.4 and 5–5.4; extracted text around lines 340–342 and 398–422. | DIRECT. Report analysis and TCFD-oriented QA, not the same disclosure-drafting task. False concatenation is explicitly discussed, so BACE cannot claim discovery of that component idea. |
| A domain-specific human-annotated ESG hallucination benchmark already exists. | ESG-Bench, DOI 10.1609/aaai.v40i46.41281, AAAI-26 version of record; distinguish arXiv:2603.13154v1. | `paper/literature/sources/esgbench2026/original.pdf`, PDF pp. 2–4, Human Annotation and Benchmark Analysis and Usage; extracted text around lines 205–234. Publisher PDF: https://ojs.aaai.org/index.php/AAAI/article/download/41281/45242 | DIRECT. Its assessment target is long-context ESG QA with human support-related labels and source pages. It contradicts an unqualified absence-of-domain-evaluation claim. |

## Rejected or unresolved formulations

- **UNVERIFIED:** "Many companies now use RAG to generate complete sustainability reports." Named solution examples establish existence, not a population estimate or full end-to-end deployment.
- **UNVERIFIED:** "Adoption is expanding faster than research." Requires separate, temporally comparable evidence for both adoption and research volume.
- **UNVERIFIED:** "Very few studies explore what this means." Specify which consequence is meant and support scarcity through a defined review before using it as a factual claim.
- **CONTRADICTED AS WRITTEN:** "There is no dedicated systematic framework for evaluating AI sustainability reporting." Existing generation benchmarks and human-annotated QA evaluation are direct counterexamples to this broad formulation.
- **NOT ESTABLISHED:** "BACE is the first boundary-sensitive evaluation framework." The prior verified gap review identifies context-preserving and joint-evidence precedents; two relevant full-text access gaps also remain unresolved.
- **OUT OF CURRENT EXPERIMENTAL SCOPE:** "The study establishes effects of AI reporting on industry, stakeholder decisions, greenwashing or sustainability outcomes." The saved experiment measures support within a controlled drafting workflow.

## Scope decision for author confirmation

Use "AI-assisted sustainability disclosure drafting" or "AI-generated sustainability disclosures" for the empirical object. Use "sustainability reporting" for the broader motivation. Do not imply that the experiment evaluates complete published reports, all reporting-quality dimensions, or actual deployment outcomes.

Preserve the central distinction between a generation capability, an automated support judgment, source-level fidelity, and independently validated judgment accuracy. Current formal reviewer workbooks remain unfilled according to the saved 29 October main-results audit. Do not present prepared packets as completed validation.

## Related saved evidence

- `paper/03_research_foundation.md`, especially Research gap and Scope of the argument.
- `paper/04_research_gap_verification.md`, especially Search and verification scope and unresolved access.
- `paper/literature/SOURCE_INDEX.md` and original-source citation ledgers.
- `paper/analysis/main_results_reaudit_2026-10-29/REPORT.md` and `results.json` for the primary empirical evidence.

No existing manuscript, bibliography, experiment artifact, reviewer material or frozen environment was modified by this note.
