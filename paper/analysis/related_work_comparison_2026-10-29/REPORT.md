# BACE scope and comparison with three sustainability AI studies

Date: 29 October 2026. Status: original-source comparison for storyline development; not a systematic review, a verified priority claim or an approved manuscript revision.

## 1. Correct the research scope

The earlier working question confused two prominent diagnostic findings with the framework's entire research scope. BACE evaluates supplied-evidence support, including supported claims and multiple unsupported patterns. Its purpose is not restricted to preserving factual boundaries and relationships.

**Working research question:** To what extent are the complete factual meanings of AI-generated sustainability disclosure claims supported by the evidence supplied to the generator, how is that support structured, and what diagnostic patterns characterize unsupported claims?

**Working manuscript formulation:** This study evaluates the evidentiary support of AI-generated sustainability disclosures, distinguishes direct from inferred support, and diagnoses why unsupported claims fail to follow from the evidence supplied to the generator.

This formulation is broader than two failure categories but narrower than overall report quality, external truth, legal compliance or actual sustainability performance. An assigned diagnosis is a structured description of a support failure, not independent identification of its causal origin in the generation process.

## 2. What the implemented BACE diagnosis actually covers

The frozen diagnosis prompt applies these checks in order and returns the first applicable label, only after a DC has been classified as unsupported.

| Order | Label | Decisive distinction |
| --- | --- | --- |
| 1 | `non_disclosure_statement` | The central proposition asserts that something was not disclosed, identified, quantified or otherwise provided within a stated scope. This is not simply negative wording or missing candidate evidence. |
| 2 | `contradiction` | Evidence affirmatively establishes an incompatible proposition at materially matching entity, time, scope and metric boundaries. |
| 3 | `evidence_conflation` | Elements from multiple ECs are combined into an unsupported relationship, attribution, entity, event or conclusion. |
| 4 | `factual_boundary_distortion` | An anchored core fact is transferred across entity, organizational level, time, geography, population, activity, metric, unit or measurement boundaries. |
| 5 | `inferential_inflation` | Material boundaries match, but certainty, causality, status, effectiveness or another semantic conclusion is stronger than the evidence entails. |
| 6 | `unsupported_novelty` | No supplied candidate EC gives a recognizable anchor for the core proposition. This does not establish that the proposition is false outside that evidence set. |

These are six mutually exclusive primary assignments under an ordered decision rule, not six independently measured or exhaustive causal mechanisms. A supported assertion of non-disclosure is not automatically an error. Novelty assignments, like other judgments, can reflect extraction or candidate-selection limitations.

Boundary distortion and conflation together account for 31,335 of 42,646 automated unsupported assignments, or 73.48%, in the saved main analysis. This is an empirical concentration within the full taxonomy; it is not a reason to retrospectively redefine the entire question around those two categories.

**Numerical provenance:** `../main_results_reaudit_2026-10-29/diagnoses.csv`, rows `factual_boundary_distortion` and `evidence_conflation`, column `claims`; denominator is the sum of all six diagnosis counts in the same file. The saved `REPORT.md`, Section 3, reports this combined calculation. These are `COMPUTED_VERIFIED` upstream analysis results, not new measurements here. Cohort: 1,798 completed BACE generation cases; within-case deduplicated DCs, pooled claim aggregation. Upstream code: `reanalyse_main.py`; its `integrity.json` and `provenance.json` record input checks and calculation provenance. No experiment was rerun.

## 3. SusGen-GPT: generation model, training resource and reference benchmark

**Source:** SusGen-GPT: A Data-Centric LLM for Financial NLP and Sustainability Report Generation, NAACL Findings 2025, DOI `10.18653/v1/2025.findings-naacl.66`, version of record. Original locators: Sections 3.1–3.2 and Figure 3, PDF pages 3–4; Section 3.4, pages 4–5; Limitations, page 9.

The study develops financial/ESG instruction data and fine-tuned models. Its sustainability generation component retrieves annual-report material to produce TCFD-oriented text. TCFD-Bench uses context, an instruction/question and a reference answer extracted from TCFD reports. Figure 3 shows question-conditioned disclosure-like generation, so it is not defensible to distinguish this work from BACE merely as full-report generation versus QA.

Its report-generation metrics are BERTScore, ROUGE, METEOR and BLEU-N against expert reference content. The limitations acknowledge expert analysis of some cases but reliance on automated metrics at scale.

**Comparison inference:** BACE's principal difference is the assessment target and representation: support within supplied evidence, without a target reference disclosure, with explicit DC-to-EC support sets and unsupported diagnoses. Reference similarity and evidence entailment answer different questions. This does not establish superior generation quality or evaluator accuracy.

## 4. ChatReport: source-linked analysis with human support assessment

**Source:** CHATREPORT: Democratizing Sustainability Disclosure Analysis through LLM-based Tools, EMNLP Demo 2023, DOI `10.18653/v1/2023.emnlp-demo.3`, version of record. Original locators: Sections 3.1–3.4, PDF pages 3–4; Sections 5–5.4, pages 5–6.

ChatReport processes existing sustainability reports to generate TCFD summaries, conformity assessments and customized answers. Retrieval and source attribution facilitate checking these generated outputs; expert feedback also informs prompt development.

Its human hallucination assessment has content and source dimensions: complete answer support, and honest references together with non-hallucinated content. Section 5.2 explicitly describes false concatenation of retrieved chunks and extrapolation. Section 5.4 describes an expert-annotated support/attribution dataset.

**Comparison inference:** It is a direct precedent for sustainability-specific support assessment and unsupported synthesis. BACE cannot claim to discover either idea. BACE instead operationalizes per-DC assessment using extracted ECs, explicit minimal support sets, direct/inferred support and ordered diagnoses. The reviewed ChatReport paper does not document an equivalent integrated automated support-set/diagnosis pipeline; this is a comparison of published descriptions, not proof of universal absence. ChatReport evaluates generated text, although its primary application is analysis of existing reports.

## 5. ESG-Bench: grounded QA, completeness, answerability and mitigation

**Source:** ESG-Bench: Benchmarking Long-Context ESG Reports for Hallucination Mitigation, AAAI 2026, DOI `10.1609/aaai.v40i46.41281`, version of record published 14 March 2026. Local full-text verification uses the publisher PDF. The additionally inspected online text is arXiv `2603.13154v1`, dated 13 March 2026, and is recorded separately. Original locators: Human Annotation and Benchmark Analysis and Usage, PDF page 4; Strategies Toward Hallucination Mitigation, page 5; Experimental Setting and Evaluation for the Generation, page 6.

ESG-Bench builds report-grounded QA data with human review of answers and supporting pages/formats. Its answer-level labels are Correct, Hallucination, Incomplete and Answer Not Found. The last means inappropriate abstention despite an available source answer. It also provides a hallucination-mitigation variant and evaluates supervised fine-tuning and structured reasoning, including answering when supported and abstaining when information is absent.

**Comparison inference:** This is a substantive domain-specific evaluation precedent, not merely a general QA dataset. BACE provides a different granularity and representation: individual DCs, EC support sets and specific primary unsupported patterns. BACE's non-disclosure diagnosis is not equivalent to inappropriate abstention. Conversely, BACE's evidence-use coverage does not directly measure omitted required answer content or report completeness, which ESG-Bench explicitly considers.

## 6. The defensible distinction is an integrated measurement design

| Comparison dimension | SusGen-GPT | ChatReport | ESG-Bench | BACE |
| --- | --- | --- | --- | --- |
| Primary application | Financial/ESG model development and generation | Existing-report analysis | Grounded ESG QA and hallucination mitigation | Assessment of generated disclosure claims |
| Main evaluation representation | Generated versus reference text | Generated answer, report and attribution | Answer, report context and human labels | Deduplicated DCs/ECs and accepted support sets |
| Main distinction from BACE | Reference similarity rather than the BACE support contract | Human answer/source judgment rather than the BACE integrated automated claim pipeline | Answer quality and answerability rather than BACE support-set/diagnostic granularity | Explicit support structure and differentiated failure profiles |

The BACE-specific implementation exposes:

- **The proposition being assessed:** a self-contained DC with its material qualifiers, rather than only an aggregate output score.
- **The supporting representation:** accepted minimal sufficient sets of ECs. The support prompt requests every distinct sufficient minimal set among supplied candidates; the outputs are model judgments, not guaranteed exhaustive logical proofs.
- **The semantic relation:** direct or inferred for each accepted set. Multi-EC support is not synonymous with inferred support.
- **The unsupported pattern:** an exclusive diagnosis and rationale after the support stage.
- **The empirical profile:** support, support structure, evidence use and unsupported patterns across the saved task/company/year cohort, together with carefully qualified evaluator disagreements.

The underlying support judgment and diagnosis see a DC, selected candidate EC texts and company/year interpretive context, not the complete original report or raw evidence cards. The EC extraction stage reads generator-visible evidence. BACE's nominal evidence universe is what was supplied to generation, but the implemented judgment is conditional on that evidence's extracted and selected representation. Shared metadata is not an independent factual premise. This is both a transparency feature and an error pathway that needs validation.

## 7. Contribution and limits for the storyline

**Working positioning paragraph:** Existing research has addressed sustainability disclosure generation, source-linked report analysis and grounded ESG question answering. BACE investigates a complementary measurement target: whether the complete propositions in generated disclosures follow from the evidence supplied for drafting, which evidence combinations support them, and which unsupported patterns arise. It integrates explicit claim-level support representation with reporting-oriented diagnosis and applies that design to a defined generation workflow.

This is an integration and empirical measurement contribution. The comparison does not establish that BACE is the first framework to preserve qualifiers, combine evidence, assess ESG hallucinations or diagnose unsupported synthesis. These three studies are relevant counterexamples to an unrestricted absence claim; a review of only three studies cannot establish the exact remaining gap across the entire literature.

The current formal BACE reviewer workbooks have no completed support/diagnosis labels according to the saved 29 October audit. The three studies contain some expert assessment or human annotation. The case for BACE must therefore rest on its explicit measurement design and bounded empirical findings, not a claim of better validated judgments. Completing suitable human and original-source validation remains necessary for stronger accuracy claims.

## 8. Claim-to-source verification ledger

All entries were checked against original local full text on 29 October 2026. The repository source index records retrieval of the publisher PDFs on 29 September 2026. Online primary-source entry points were reinspected on 29 October 2026. The ledger records the exact claim location in this report; comparison inferences are distinguished from source-described methods.

| Occurrence | Assertion | Original identifier / locator | Support and qualification |
| --- | --- | --- | --- |
| Section 3, paragraph 1 | Model/data work includes RAG-based TCFD generation and question-conditioned benchmark examples. | SusGen DOI above; Sections 3.1–3.2; Figure 3, PDF pp. 3–4. | DIRECT; not an assertion that every task uses RAG or that evaluation requires full reports. |
| Section 3, paragraph 2 | Report-generation reference metrics and limited expert assessment at scale. | SusGen Section 3.4, PDF pp. 4–5; Limitations, p. 9. | DIRECT; some expert analysis exists. Earlier local p. 8 limitation locator was corrected to p. 9. |
| Section 4, paragraph 1 | Existing-report summary, conformity and QA tool with attribution and expert prompt feedback. | ChatReport DOI above; Sections 3.1–3.4, PDF pp. 3–4. | DIRECT; conformity assessment is not independent verification of company actions or legal compliance. |
| Section 4, paragraph 2 | Content/source human support assessment, false concatenation, annotated dataset. | ChatReport Sections 5–5.4, PDF pp. 5–6. | DIRECT; support/synthesis principles precede BACE. |
| Section 5, paragraph 1 | Four human answer labels and mitigation of unsupported answering/incorrect abstention. | ESG-Bench DOI above; Human Annotation, PDF p. 4; Strategies, p. 5; Evaluation for the Generation, p. 6. | DIRECT; distinguish benchmark variants and answering/verification tasks. |
| Section 5, source record | Published date and version distinction. | AAAI publisher record; arXiv 2603.13154v1. | DIRECT for dates/versions; publisher full text is the main local evidence, online arXiv is supplementary. |
| Sections 3–7, comparisons | Different task, unit, evidence representation and documented evaluation outputs. | Above original passages; BACE prompts and implementation listed below. | QUALIFIED comparison inference; not a verified priority or accuracy claim. |
| Section 2 | Six diagnoses and exclusive order. | BACE frozen unsupported diagnosis prompt, Exclusive classification; execution builds candidate-EC inputs. | DIRECT implementation evidence; human correctness not established. |
| Section 6 | Full-claim sufficiency, minimal sets and direct/inferred relation. | BACE frozen support prompt, Support assessment / Support type / Minimal sufficient support sets. | DIRECT contract evidence; not proof that all stored outputs fulfill the contract. |
| Section 7 | Formal human validation not completed. | Main-results reaudit REPORT, Section 11; upstream result/provenance files. | DIRECT saved-status evidence, scoped to inspected formal workbooks. |

## 9. Source paths and reproducibility

- Original papers and extracted text: `../../literature/sources/susgen2025/`, `../../literature/sources/chatreport2023/`, `../../literature/sources/esgbench2026/`.
- Online primary sources: `https://aclanthology.org/2025.findings-naacl.66.pdf`; `https://aclanthology.org/2023.emnlp-demo.3.pdf`; `https://ojs.aaai.org/index.php/AAAI/article/view/41281`; `https://arxiv.org/html/2603.13154v1`.
- BACE scope: `../../../docs/generation_evaluation.md`, Sections 1–5, 7, 13–16.
- BACE contracts: `../../../BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt` and `generation_claim_unsupported_diagnosis_prompt_v1.txt` in that directory.
- Implemented diagnosis input: `../../../BACE/script/evaluation/run_generation_claim_unsupported_diagnosis.py`, `build_jobs`, especially candidate selection and `dynamic_input` construction.
- Empirical and validation provenance: `../main_results_reaudit_2026-10-29/REPORT.md`, `diagnoses.csv`, `results.json`, `reanalyse_main.py`, `integrity.json` and `provenance.json`.
- Visual verification: `source_previews/esgbench_pdf_page_4.png` and `source_previews/susgen_pdf_page_4.png`, rendered from the original PDFs using `pdftoppm` and inspected locally.
- `generate_manifest.py` records SHA-256 hashes of input evidence and generated comparison artifacts using the independent writing environment. This is artifact provenance, not a new statistical analysis.

No experiment artifacts, prompts, model settings, environments or reviewer materials were changed. The earlier working question was broadened in its writing note, and an incorrect SusGen page locator was corrected in that note and the literature source index. No manuscript section was rewritten.
