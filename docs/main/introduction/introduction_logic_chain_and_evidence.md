# Introduction Logic Chain and Academic Evidence Map

## Purpose and Status

This document provides the argumentative and evidentiary foundation for the paper's Introduction. It is not a finished Introduction. Its purposes are to:

1. define the logical progression from the broad reporting context to the study objective;
2. identify academic and regulatory sources supporting each step;
3. distinguish established findings from application-specific inferences and research gaps;
4. prevent claims that exceed the available literature; and
5. provide a paragraph structure for drafting the final Introduction.

**Study context:** Evaluation of one fixed evidence-card retrieval-augmented generation (RAG) workflow across 30 companies, five target reporting years, ESRS E1, S1, and G1, and four disclosure tasks per standard.

**Evaluation context:** Validation of BACE (Boundary-Aware Claim Evaluation) against RAGChecker and a stratified human assessment. RAGAS will also be piloted; its inclusion in the full experiment remains conditional on the pilot findings.

**Review status:** Targeted narrative literature and citation audit, updated 4 September 2026. This document does not constitute a systematic review or prove the absence of prior work.

---

## 1. Central Paper Positioning

The paper should be positioned as a validation and domain-extension study of RAG evaluation in sustainability reporting. It is not primarily:

- a comparison of alternative RAG architectures;
- the first application of RAG to sustainability-report generation;
- the first claim-level factuality evaluation framework;
- an evaluation of whether RAG is superior to standalone generation; or
- a claim that automated evaluation is equivalent to statutory assurance.

The central argument is:

> Sustainability disclosures are evidence-dependent and institutionally consequential. RAG can make company-specific evidence available to a language model, but evidence access does not guarantee that generated claims preserve the evidence's factual boundaries. If unsupported or distorted claims remain undetected and enter formal reporting workflows, they may affect the assessments of investors and other stakeholders and increase governance, review, and assurance burdens. Existing RAG evaluators measure useful general constructs, including retrieval quality, relevance, faithfulness, entailment, and hallucination, but their adequacy for boundary-sensitive ESRS disclosure generation has not been established. This motivates a reporting-specific evaluation framework whose validity must be tested against established evaluators and human judgments across heterogeneous reporting cases.

---

## 2. Essential Conceptual Distinctions

The Introduction should preserve the following distinctions throughout.

### 2.1 Digitalisation is established; AI-assisted drafting is emerging

The digital transformation of corporate reporting is supported by an established literature on structured reporting, XBRL, data technologies, and digital reporting processes. In contrast, generative AI use in sustainability-report production is documented mainly through conceptual research and recent prototype systems. The paper should not imply widespread organizational adoption without direct adoption data.

### 2.2 Evidence access is not evidence support

```text
Evidence exists in the eligible corpus
        !=
Evidence is retrieved and supplied to the generator
        !=
Evidence is used by the generator
        !=
The generated claim is fully supported by that evidence
```

### 2.3 Institutional requirements and evaluation constructs serve different roles

The institutional importance of sustainability reporting explains why unreliable generation matters. ESRS qualitative characteristics specify what high-quality sustainability information should satisfy. The former establishes the stakes; the latter informs the evaluation construct.

### 2.4 Evaluator agreement is not evaluator validity

Agreement among automated evaluators provides evidence of convergence, not correctness. Human judgments provide a criterion reference, although human annotation is itself fallible and must be supported by a predefined rubric, independent annotators, agreement analysis, and adjudication.

### 2.5 The domain gap is an open question, not a prior finding

The paper may state that it remains unclear whether general-purpose RAG evaluation adequately captures reporting-specific evidentiary failures. It should not state before the experiment that RAGAS or RAGChecker necessarily misses those failures.

---

## 3. Complete Logic Chain

```text
1. Corporate reporting is undergoing digital transformation.
   ↓
2. Generative AI applications for sustainability-information
   processing and disclosure drafting are emerging.
   ↓
3. Sustainability disclosure is evidence-dependent and
   institutionally consequential.
   ↓
4. Parametric LLMs have limitations as the sole source of
   company-specific, time-specific, and traceable information.
   ↓
5. RAG is relevant because it conditions generation on
   explicit and updateable external corporate evidence.
   ↓
6. Retrieval can reduce but does not eliminate unsupported
   or misleading generation.
   ↓
7. Undetected generation failures may affect report users,
   reporting organisations, regulators, and assurance providers.
   ↓
8. Reliable evaluation is therefore required; existing frameworks
   evaluate general RAG constructs,
   including retrieval quality, relevance, faithfulness,
   claim entailment, and hallucination.
   ↓
9. ESRS disclosure additionally requires complete, neutral,
   accurate, faithfully represented, and verifiable information.
   ↓
10. It remains unclear whether generic RAG metrics adequately
   capture failures involving reporting-specific evidence boundaries.
   ↓
11. This motivates a boundary-aware evaluation framework,
    whose validity cannot be assumed and must be tested empirically.
   ↓
12. The study therefore compares the proposed framework with
    RAGAS, RAGChecker, and human judgments across heterogeneous
    E1, S1, and G1 disclosure cases.
```

---

## 4. Step-by-Step Argument and Evidence

## Step 1. Corporate Reporting Is Undergoing Digital Transformation

### Defensible claim

> Corporate reporting is undergoing a continuing digital transformation involving structured data formats, machine-readable disclosures, and increasingly data-driven reporting processes.

### Why this step is needed

This establishes the broad technological context. The paper begins with a documented transformation in reporting practices rather than beginning narrowly with RAG.

### Academic support

- Lombardi and Secundo (2020) systematically review how digital and smart technologies affect corporate reporting processes.
- Seele (2016) examines XBRL-based real-time transparency and its potential relationship with integrated sustainability reporting and performance control.
- Bartolacci et al. (2020) review two decades of XBRL research and its implications for financial and business reporting.
- Hummel and Jobst (2024) explain the development of European sustainability-reporting legislation, including standardisation and digital reporting requirements.

### Evidence assessment

**Strength:** Strong for the digital transformation of corporate reporting.

**Limitation:** This literature does not by itself demonstrate widespread use of generative AI for disclosure drafting.

### Avoid

> Sustainability reporting is already broadly automated by artificial intelligence.

---

## Step 2. Generative AI Applications in Reporting Are Emerging

### Defensible claim

> Within the broader digital transformation of reporting, generative AI is emerging as a potential tool for sustainability-information processing, analysis, and disclosure drafting.

### Why this follows from Step 1

Generative AI represents a recent development within the longer digitalisation of reporting. Separating the two prevents evidence about XBRL or general digital reporting from being used as evidence of generative-AI adoption.

### Academic support

- de Villiers, Dimes, and Molinari (2024) develop a conceptual framework for how AI text generation and processing may affect sustainability reporting.
- Moodaley and Telukdarie (2023) review relationships among artificial intelligence, sustainability reporting, and greenwashing detection.
- Yang et al. (2024) present EcoSmartGuide, an LLM- and RAG-based platform for ESG information access and report generation.
- Wu et al. (2025) present SusGen-GPT and use RAG for TCFD-oriented sustainability-report generation.
- Wang, Zhang, and Tseng (2025) present ESGH-RAG for GRI-oriented ESG-report generation.
- Ni et al. (2023) present ChatReport for sustainability-disclosure analysis, summarisation, question answering, and TCFD-oriented conformity analysis.

### Evidence assessment

**Strength:** Strong evidence that AI-assisted sustainability-reporting applications and research prototypes exist.

**Limitation:** These studies do not establish widespread industry adoption. ChatReport is mainly an analysis system rather than a system for drafting complete new corporate disclosures.

### Preferred wording

> Generative AI applications for sustainability reporting are emerging in conceptual research and prototype systems.

### Avoid

> Sustainability reporting is increasingly AI-assisted across companies.

This stronger adoption claim would require survey, field, or market-adoption evidence.

---

## Step 3. Sustainability Disclosure Is Evidence-Dependent and Institutionally Consequential

### Defensible claim

> Sustainability disclosure is an evidence-dependent and institutionally consequential reporting activity because disclosed information is intended for stakeholder decision-making and may be subject to governance, control, and assurance processes.

### Why this follows from Step 2

The use of generative AI is not equally consequential in every writing task. The characteristics of sustainability reporting explain why factual support, boundaries, traceability, and reviewability matter in this application.

### Regulatory and academic support

- Directive (EU) 2022/2464 places sustainability information within the management report and establishes governance and assurance requirements.
- Commission Delegated Regulation (EU) 2023/2772 establishes the ESRS disclosure framework.
- Christensen, Hail, and Leuz (2021) review the institutional and economic consequences of mandatory CSR and sustainability reporting.
- Hummel and Jobst (2024) analyse the EU sustainability-reporting legislative architecture.
- Simnett, Vanstraelen, and Chua (2009) examine external assurance of sustainability reports internationally.
- Michelon, Pilonato, and Ricceri (2015) show why disclosure quality cannot be reduced to disclosure quantity.
- Diouf and Boiral (2017) document stakeholder concerns about sustainability-report quality, credibility, and impression management.

### Evidence assessment

**Strength:** Strong. The regulatory sources directly establish formal reporting and assurance requirements; the academic literature supports their institutional and informational importance.

### Interpretation of “high accountability”

The term should be operationalised rather than used rhetorically. Relevant features include:

- inclusion in formal corporate reporting;
- management and governance responsibility;
- use by investors and other stakeholders;
- external assurance requirements;
- potential regulatory and reputational consequences; and
- the need to substantiate material factual statements.

### Avoid

> Every factual error in a sustainability report causes investor harm.

The study does not estimate downstream causal harm.

---

## Step 4. Parametric LLMs Have Limitations as Standalone Evidentiary Sources

### Defensible claim

> Parametric language models have important limitations when used as the sole evidentiary basis for company-specific, time-specific, and traceable disclosure drafting.

### Why this follows from Step 3

An evidence-dependent task requires access to the correct company's information for the correct reporting period. A model's parametric memory is neither a controlled company evidence repository nor a reliable provenance mechanism.

### Academic support

- Lewis et al. (2020) identify limitations in the ability of parametric language models to access and manipulate knowledge, update world knowledge, and provide provenance.
- Lazaridou et al. (2021) show that static language models face temporal-generalisation problems as the world and language change.
- Mallen et al. (2023) compare parametric and non-parametric memories and show the value of retrieval for less frequent knowledge.
- Kandpal et al. (2022) show that large language models struggle to learn long-tail factual knowledge reliably.
- Ji et al. (2023) review hallucination across natural-language-generation systems.

### Evidence assessment

**Strength:** Strong for general limitations of parametric language models.

**Limitation:** Most evidence comes from general NLP tasks rather than corporate disclosure drafting. The application to company- and year-specific reporting is a reasoned domain inference.

### Preferred wording

> These limitations make an ungrounded LLM unsuitable as the sole evidentiary basis for company- and period-specific disclosure drafting.

### Avoid

> Standalone LLMs cannot generate accurate sustainability disclosures.

The cited literature does not establish an absolute inability.

---

## Step 5. RAG Is a Relevant Architecture for Evidence-Dependent Drafting

### Defensible claim

> RAG is particularly relevant to disclosure drafting because it enables generation to be conditioned on an explicit and updateable external evidence source.

### Why this follows from Step 4

RAG addresses evidence access by combining a generator's parametric memory with non-parametric external evidence. In a transparent implementation, the retrieved context can also be preserved for subsequent evaluation.

### Academic support

- Lewis et al. (2020) introduce RAG as a combination of parametric and non-parametric memory and emphasise knowledge updating, provenance, and factuality.
- Shuster et al. (2021) show that retrieval augmentation can reduce hallucination in conversational generation.
- Gao et al. (2023a) review RAG as an approach to limitations involving outdated knowledge, hallucination, and traceability.
- EcoSmartGuide, SusGen-GPT, and ESGH-RAG demonstrate the practical relevance of retrieval-supported generation in sustainability-reporting applications.

### Evidence assessment

**Strength:** Strong for the architectural role of external retrieval and for its potential factuality benefits.

**Limitation:** Relevance does not establish superiority over all alternative architectures, and access to evidence does not establish faithful use of that evidence.

### Preferred wording

> RAG makes selected external evidence available to the generator and creates an observable evidence context against which the resulting text can be evaluated.

### Avoid

> RAG ensures that generated disclosures are grounded.

---

## Step 6. RAG Does Not Guarantee Reliable Generation

### Defensible claim

> Although retrieval can improve factuality, access to retrieved evidence does not guarantee that the generator will use that evidence completely, correctly, or exclusively.

### Why this follows from Step 5

Retrieval and generation are separate system components. Retrieval can fail to supply necessary evidence, while generation can ignore, distort, conflate, or exceed evidence that is available in the prompt.

### Academic support

- Niu et al. (2024) show that RAG outputs can still contain claims that are unsupported by or contradictory to retrieved content.
- Chen et al. (2024) demonstrate variation in how language models use retrieved information under RAG settings.
- Shi et al. (2023) show that irrelevant context can distract language models.
- Liu et al. (2024) show that language models do not use all positions in long contexts equally well.
- Gao et al. (2023b) show that citation presence does not eliminate the need to assess citation correctness and completeness.
- Shuster et al. (2021) support the more limited claim that retrieval reduces hallucination, not that it eliminates it.

### Evidence assessment

**Strength:** Strong and direct for the proposition that retrieval does not guarantee faithful generation.

### Analytical distinction

```text
Retrieval evaluation
→ Was relevant, sufficient, and usable evidence supplied?

Generation evaluation
→ Did each generated claim remain within the supplied evidence?
```

---

## Step 7. Undetected Generation Failures May Affect Reporting Audiences

### Defensible claim

> If unsupported or boundary-distorted AI-generated claims are not detected before entering a formal reporting workflow, they may impair the faithful representation and verifiability of reported information, mislead report users, and increase governance, review, and assurance burdens.

### Why this follows from Step 6

The persistence of unsupported claims in RAG outputs is not only a technical limitation. Its practical importance depends on whether such claims remain undetected and are incorporated into information used by investors, lenders, employees, regulators, assurance providers, and other stakeholders. The need for evaluation therefore arises from the combination of residual generation risk and the institutional uses of sustainability information.

### Risk pathway

```text
Unsupported or boundary-distorted generation
        ↓
Failure to detect the error during review
        ↓
Incorporation into a disclosure draft
        ↓
Exposure of report audiences to misleading information
        ↓
Potential decision, accountability, governance,
reputational, or assurance consequences
```

Each arrow represents a plausible risk pathway rather than a causal effect established by this study.

### Potential effects on report audiences

| Audience | Potential effect of undetected claims | Principal support |
|---|---|---|
| Investors, lenders, and creditors | Distorted assessment of sustainability-related impacts, risks, opportunities, targets, performance, or future prospects | Christensen et al. (2021); Reimsbach et al. (2018); Directive (EU) 2022/2464 |
| Employees and workers' representatives | Misrepresentation of workforce policies, working conditions, incidents, targets, or remedial actions | Commission Delegated Regulation (EU) 2023/2772, especially ESRS S1 |
| Affected communities, customers, civil-society organisations, and other stakeholders | Misleading impressions of environmental and social performance or corporate accountability | Boiral (2013); Diouf and Boiral (2017); Commission Delegated Regulation (EU) 2023/2772 |
| Regulators | Reduced confidence that reported information satisfies applicable disclosure and information-quality requirements | Hummel and Jobst (2024); Directive (EU) 2022/2464; Commission Delegated Regulation (EU) 2023/2772 |
| Internal reviewers and assurance providers | Additional verification effort and greater difficulty tracing claims to sufficient evidence | Simnett, Vanstraelen, and Chua (2009); Reimsbach, Hahn, and Gürtürk (2018) |
| Management and governance bodies | Decisions based on inaccurate drafts and potential compliance, control, and reputational exposure | de Villiers, Dimes, and Molinari (2024); Moodaley and Telukdarie (2023) |

### Academic support

- Ji et al. (2023) show that generative systems can produce fluent text containing factual hallucinations, while Niu et al. (2024) show that unsupported and contradictory claims persist in RAG outputs.
- de Villiers, Dimes, and Molinari (2024) directly discuss the implications and risks of AI text generation and processing for sustainability reporting.
- Christensen, Hail, and Leuz (2021) review the economic and institutional consequences of mandatory sustainability reporting.
- Reimsbach, Hahn, and Gürtürk (2018) provide experimental evidence concerning professional investors' processing of sustainability information and assurance.
- Boiral (2013) shows how sustainability reports can project idealised representations that obscure sustainable-development problems.
- Diouf and Boiral (2017) document stakeholder concerns about report quality, credibility, and impression management.
- Moodaley and Telukdarie (2023) review relationships among artificial intelligence, sustainability reporting, and greenwashing.
- Simnett, Vanstraelen, and Chua (2009) establish the relevance of external assurance to sustainability reporting.

### Relationship with greenwashing

Unsupported AI-generated claims should not automatically be classified as greenwashing because greenwashing may involve strategic intent, whereas generation errors may be inadvertent. Nevertheless, if unsupported claims are accepted into corporate disclosures, they may contribute to misleading sustainability narratives or facilitate impression management.

### Evidence assessment

**Strength:** Strong for the separate propositions that generative systems can produce unsupported claims, sustainability information is used by multiple audiences, reporting quality affects credibility and information processing, and sustainability reports may be affected by impression management.

**Limitation:** The literature does not directly establish that the absence of the proposed framework causes investor losses, regulatory violations, assurance failure, or greenwashing. These outcomes must be presented as potential risks rather than observed causal effects.

### Introduction-ready transition

> Reliable evaluation is therefore not merely a technical benchmarking exercise but a potential reporting-control mechanism for identifying unsupported claims before they affect formal disclosures and their audiences.

### Avoid

> Without the proposed framework, AI-generated sustainability reports will mislead investors and constitute greenwashing.

---

## Step 8. Existing Frameworks Evaluate General RAG Properties

### Defensible claim

> Existing RAG evaluation frameworks operationalise general-purpose constructs such as context relevance, answer relevance, retrieval coverage, faithfulness, claim entailment, attribution, and hallucination.

### Why this follows from Step 7

The potential consequences of undetected retrieval and generation failures establish the need for reliable evaluation. Existing frameworks provide several mechanisms for measuring different components of RAG performance and must be acknowledged before identifying a narrower domain gap.

### Academic support

- RAGAS evaluates reference-free dimensions including faithfulness, answer relevance, and context relevance (Es et al., 2024).
- RAGChecker uses claim extraction and claim-level entailment to construct overall, retrieval, and generation metrics (Ru et al., 2024).
- ARES evaluates context relevance, answer faithfulness, and answer relevance using trained judges and prediction-powered inference (Saad-Falcon et al., 2024).
- FActScore evaluates factual precision by decomposing long-form generations into atomic facts (Min et al., 2023).
- ALCE evaluates correctness, citation correctness, and citation completeness in attributed generation (Gao et al., 2023b).
- VeriScore evaluates the factuality of verifiable claims in long-form generation (Song et al., 2024).
- RAGTruth provides manually annotated hallucination data for RAG outputs (Niu et al., 2024).

### Evidence assessment

**Strength:** Strong.

**Important correction:** The paper must not claim that existing evaluation is only paragraph-level or that claim-level evaluation is absent. RAGChecker, FActScore, RAGTruth, and VeriScore directly contradict such a claim.

### Defensible limitation statement

> These frameworks were developed and validated primarily on general question-answering, retrieval, summarisation, biography, or long-form generation tasks rather than regulated ESRS disclosure drafting.

---

## Step 9. Sustainability Reporting Imposes Specific Information-Quality Requirements

### Defensible claim

> ESRS requires sustainability information to possess the fundamental qualitative characteristics of relevance and faithful representation. Faithful representation requires information to be complete, neutral, and accurate, while verifiability is an enhancing qualitative characteristic.

### Why this follows from Step 8

Generic RAG constructs and reporting-quality requirements overlap, but they are not automatically identical. A disclosure can be broadly faithful or semantically entailed while still mishandling a material reporting-period, entity, unit, scope, methodology, or implementation-status qualifier.

### Primary and academic support

- Commission Delegated Regulation (EU) 2023/2772, ESRS 1, Appendix B, provides the primary definitions of relevance, faithful representation, completeness, neutrality, accuracy, comparability, verifiability, and understandability.
- Hummel and Jobst (2024) explain the regulatory context of these requirements.
- Michelon, Pilonato, and Ricceri (2015) examine the quality of CSR disclosures and distinguish substantive quality from reporting practice alone.
- Diouf and Boiral (2017) identify stakeholder concerns involving completeness, balance, reliability, and credibility.
- Simnett, Vanstraelen, and Chua (2009) provide evidence on the role of sustainability-report assurance.

### Evidence assessment

**Strength:** Strong. The exact qualitative characteristics should be cited to ESRS itself because it is the authoritative primary source.

### Boundary-aware operationalisation proposed by this study

The study translates these broad qualitative characteristics into observable evidence-support checks involving:

- company and entity;
- reporting period;
- baseline and target year;
- metric and unit;
- organizational and reporting scope;
- methodology;
- implementation status;
- certainty and modality;
- comparison and causal meaning; and
- synthesis across multiple evidence items.

This boundary list is the study's analytical operationalisation. It should not be presented as a verbatim ESRS taxonomy.

---

## Step 10. The Adequacy of Generic RAG Evaluation for ESRS Disclosure Is Unclear

### Defensible gap statement

> It has not yet been established whether general-purpose RAG evaluation metrics adequately capture reporting-specific failures involving temporal, organizational, quantitative, methodological, and implementation-status boundaries.

### Why this follows from Steps 8 and 9

Step 8 establishes what general-purpose RAG frameworks measure. Step 9 establishes the reporting-specific information-quality requirements and proposed boundary operationalisation. The unresolved question is whether the former sufficiently captures the latter.

### Evidence supporting the gap

The gap is established by comparing two bodies of literature rather than by citing one paper claiming that the gap exists.

#### General RAG evaluation literature

- RAGAS;
- RAGChecker;
- ARES;
- FActScore;
- ALCE;
- VeriScore; and
- RAGTruth.

#### Sustainability-report generation literature

- EcoSmartGuide;
- SusGen-GPT; and
- ESGH-RAG.

### Limitations observed in direct reporting-generation studies

- SusGen-GPT evaluates sustainability-report generation primarily with BERTScore, ROUGE, and METEOR against expert reference content. Its limitations section notes that large-scale evaluation relies on automated scores and lacks the depth of human ESG expertise.
- ESGH-RAG reports 92.1% accuracy for retrieval of reporting guidance rather than 92.1% factual accuracy of generated corporate disclosures. Its report-quality evidence includes a limited feasibility and company-feedback assessment.
- EcoSmartGuide reports citation accuracy and ESG coverage, but the accessible publication record does not establish boundary-aware atomic claim auditing or validation against human judgments.
- The targeted review did not identify a study that validates RAGAS or RAGChecker against human judgments for multi-company, multi-year, cross-standard ESRS disclosure generation.

### Evidence assessment

**Strength:** Qualified research-gap inference.

This is not proof that no relevant study exists. A formal novelty claim requires a documented database search with search strings, inclusion and exclusion criteria, date limits, screening records, and a reproducible study-selection process.

### Preferred wording

> A targeted review did not identify a study that validates general-purpose RAG evaluators against human judgments for boundary-sensitive ESRS disclosure generation.

### Avoid

> No previous study has evaluated RAG-generated sustainability disclosures.

This would be contradicted by EcoSmartGuide, SusGen-GPT, and ESGH-RAG.

---

## Step 11. A Reporting-Specific Framework Must Itself Be Validated

### Defensible claim

> The identified gap motivates a reporting-specific operationalisation of evidentiary support. However, proposing a new framework does not establish its validity; its scores and classifications must themselves be evaluated empirically.

### Why this follows from Step 10

If existing constructs may not fully capture the target domain, a domain-specific operationalisation is justified. Measurement validity nevertheless requires evidence that the proposed framework measures the intended construct and adds useful information.

### Academic support

- Flake and Fried (2020) explain how weakly defined or insufficiently validated measures can undermine research conclusions.
- Fabbri et al. (2021) demonstrate the importance of evaluating automated natural-language-generation metrics against comprehensive human annotations.
- RAGAS validates its metrics against human comparisons in WikiEval (Es et al., 2024).
- RAGChecker conducts a meta-evaluation against human preferences and finds that different automated metrics do not provide interchangeable measurements (Ru et al., 2024).
- Wang et al. (2024) document systematic bias in LLM-based evaluators.
- Zheng et al. (2023) show that strong LLM judges can approximate human preferences while still exhibiting position, verbosity, and self-enhancement biases.

### Required forms of validity evidence

#### Convergent validity

Do the proposed framework, RAGAS, and RAGChecker produce associated judgments when they evaluate overlapping constructs?

#### Criterion-related validity

How closely does each automated evaluator align with human judgments under a common annotation rubric?

#### Incremental validity

Does the proposed framework identify boundary-sensitive errors or provide diagnostic information beyond that available from RAGAS and RAGChecker?

#### Robustness and transfer

Are results stable across E1, S1, G1, task archetypes, companies, and target reporting years?

### Avoid

> A domain-specific framework is necessarily more accurate than a generic framework.

That proposition is an empirical question for the study.

---

## Step 12. Comparative and Human-Validated Evaluation Across Heterogeneous Cases

### Defensible study response

> The study therefore compares the proposed boundary-aware framework with RAGAS, RAGChecker, and human judgments across heterogeneous environmental, social, and governance disclosure cases.

### Why this follows from Step 11

The three automated approaches provide complementary measurement perspectives:

- the proposed framework provides reporting-specific boundary modelling and failure diagnostics;
- RAGAS provides widely used reference-free RAG measures; and
- RAGChecker provides the closest general-purpose claim-level comparator.

Human assessment is needed because agreement among automated evaluators cannot determine which assessment is substantively correct.

### Academic support

- Es et al. (2024) establish RAGAS and compare its metrics with human judgments.
- Ru et al. (2024) establish RAGChecker and use human meta-evaluation to test metric reliability.
- Thakur et al. (2025) directly compare LLM and human assessments of evidentiary support in the TREC 2024 RAG Track.
- Zheng et al. (2023) and Wang et al. (2024) show both the usefulness and limitations of LLM-based judging.
- Fabbri et al. (2021) provide a broader precedent for using expert and crowd annotations to evaluate automatic text-generation metrics.

### Empirical implementation

```text
One fixed evidence-card RAG workflow
        ↓
30 companies × 5 target years × 12 ESRS tasks
        ↓
1,800 generated disclosures
        ↓
Independent evaluation by:
    1. Proposed boundary-aware framework
    2. RAGAS
    3. RAGChecker
        ↓
Stratified human-validation sample
        ↓
Convergence, criterion validity, incremental value,
disagreement analysis, and cross-context robustness
```

### Interpretation boundary

The 2019–2023 cases are historical ESRS-style disclosure simulations unless a source document is an actual ESRS disclosure. The paper must not imply that every sampled company was legally subject to ESRS during those years.

---

## 5. Introduction-Ready Condensed Logic

> Corporate reporting is undergoing digital transformation, while generative AI applications for sustainability-information processing and disclosure drafting are beginning to emerge. Sustainability reporting is nevertheless an evidence-dependent and institutionally consequential activity in which the meaning of a disclosure can depend on its temporal, organizational, quantitative, methodological, and implementation-status boundaries. Parametric language models have limitations as standalone sources of company-specific, time-specific, and traceable information. RAG is therefore relevant because it makes explicit external evidence available during generation and can improve factuality and provenance. However, retrieval does not ensure that the generator will use the supplied evidence completely or correctly, and RAG outputs may still contain unsupported or contradictory claims. If these failures remain undetected and enter formal reporting workflows, they may impair the faithful representation and verifiability of reported information, distort assessments by investors and other stakeholders, contribute to misleading sustainability narratives, and increase governance and assurance burdens. Reliable evaluation is therefore not merely a technical benchmarking exercise but a potential reporting-control mechanism. Existing frameworks such as RAGAS and RAGChecker evaluate general constructs including context relevance, faithfulness, claim entailment, and hallucination. ESRS reporting additionally requires information to be complete, neutral, accurate, faithfully represented, and verifiable. It remains unclear whether general-purpose RAG metrics adequately identify failures involving these reporting-specific evidence boundaries. This gap motivates a boundary-aware claim-level evaluation framework, but the validity and incremental value of that framework must be established rather than assumed. The present study therefore compares the proposed framework with RAGAS, RAGChecker, and human judgments across environmental, social, and governance disclosure tasks spanning multiple companies and target reporting years.

---

## 6. Recommended Introduction Structure

The final Introduction can be organised into six paragraphs.

### Paragraph 1 — Digital transformation and emerging AI use

Establish the digital transformation of corporate reporting and introduce generative AI as an emerging reporting technology. Distinguish established digitalisation from early-stage generative-AI adoption.

**Primary sources:** Lombardi and Secundo (2020); Seele (2016); de Villiers et al. (2024).

### Paragraph 2 — Existing AI and RAG sustainability-reporting applications

Show that sustainability-report generation is no longer hypothetical by introducing EcoSmartGuide, SusGen-GPT, and ESGH-RAG. Clarify that these are recent implementations rather than evidence of universal industry adoption.

**Primary sources:** Yang et al. (2024); Wu et al. (2025); Wang et al. (2025); Ni et al. (2023) as adjacent work.

### Paragraph 3 — Evidence dependence, accountability, and the RAG rationale

Explain the institutional requirements of sustainability reporting, the limitations of standalone parametric models, and why external company evidence makes RAG relevant.

**Primary sources:** European Parliament and Council (2022); European Commission (2023); Christensen et al. (2021); Hummel and Jobst (2024); Lewis et al. (2020); Mallen et al. (2023).

### Paragraph 4 — The retrieval–generation reliability gap and its audience consequences

Explain that RAG reduces but does not eliminate hallucination and that retrieved information can be ignored, distorted, or misused. Trace how undetected errors may affect investors, lenders, employees, regulators, other stakeholders, internal reviewers, and assurance providers. Distinguish inadvertent unsupported generation from intentional greenwashing, while explaining that undetected claims may still contribute to misleading disclosure or impression management. End by establishing reliable evaluation as a potential reporting-control mechanism.

**Primary sources:** Niu et al. (2024); Chen et al. (2024); de Villiers et al. (2024); Christensen et al. (2021); Boiral (2013); Diouf and Boiral (2017); Reimsbach et al. (2018); Simnett et al. (2009).

### Paragraph 5 — Evaluation landscape and domain-specific gap

Acknowledge RAGAS, RAGChecker, ARES, FActScore, ALCE, and VeriScore. Contrast their general constructs and benchmark domains with ESRS information-quality requirements and boundary-sensitive reporting claims. State the gap cautiously as an unresolved validation question.

**Primary sources:** Es et al. (2024); Ru et al. (2024); Saad-Falcon et al. (2024); Min et al. (2023); Gao et al. (2023b); Song et al. (2024); European Commission (2023).

### Paragraph 6 — Study purpose, design, and contribution

State that the study evaluates one fixed RAG workflow and validates the proposed framework against RAGAS, RAGChecker, and human judgments across 1,800 disclosure cases. Present the contribution as domain adaptation, validation, and diagnostic extension rather than invention of claim-level evaluation.

---

## 7. Proposed Gap, Purpose, and Contribution Statements

### Research gap

> Although existing RAG evaluation frameworks provide measures of retrieval quality, relevance, faithfulness, claim entailment, and hallucination, their validity for boundary-sensitive sustainability disclosure generation has not been established. In particular, it remains unclear whether general-purpose metrics detect evidentiary failures involving reporting period, entity, scope, unit, methodology, implementation status, and multi-evidence composition, or how closely their judgments align with human assessment in this domain.

### Research purpose

> The purpose of this study is to evaluate the evidentiary reliability of disclosures generated by a fixed evidence-card RAG workflow and to determine whether a boundary-aware claim-level framework provides valid and diagnostically useful assessments compared with RAGAS, RAGChecker, and human judgments.

### Intended methodological contribution

> The study adapts and integrates established claim-level factuality and RAG-evaluation principles for a boundary-sensitive reporting context, and evaluates the resulting framework across environmental, social, and governance disclosure tasks.

### Intended empirical contribution

> The study provides large-scale evidence on claim support, failure mechanisms, evaluator agreement, and evaluator disagreement across 1,800 multi-company, multi-year ESRS-style disclosure cases.

### Intended validation contribution

> The study distinguishes convergence among automated metrics from criterion-related agreement with human judgments and tests whether boundary-aware evaluation provides incremental diagnostic information beyond general-purpose RAG metrics.

---

## 8. Claims That Should Not Appear Without Additional Evidence

The Introduction should not claim:

1. that generative AI is already widely used by companies to draft sustainability reports;
2. that this is the first use of RAG for sustainability-report generation;
3. that existing RAG evaluation lacks claim-level methods;
4. that RAG guarantees grounded or reliable disclosure generation;
5. that the proposed framework is more accurate than RAGAS or RAGChecker before the validation results are available;
6. that agreement between automated evaluators establishes validity;
7. that human annotation is infallible ground truth;
8. that historical 2019–2023 cases represent mandatory ESRS reporting by all sampled firms;
9. that the evaluation constitutes statutory sustainability assurance; or
10. that results from one fixed RAG workflow generalise to all models and RAG architectures; or
11. that the absence of the proposed framework has already been shown to cause investor losses, regulatory violations, assurance failures, or greenwashing.

---

## 9. Core References

Bartolacci, F., Caputo, A., Fradeani, A., and Soverchia, M. (2020). Twenty years of XBRL: What we know and where we are going. *Meditari Accountancy Research*. https://doi.org/10.1108/MEDAR-04-2020-0846

Boiral, O. (2013). Sustainability reports as simulacra? A counter-account of A and A+ GRI reports. *Accounting, Auditing & Accountability Journal, 26*(7), 1036–1071. https://doi.org/10.1108/AAAJ-04-2012-00998

Chen, J., Lin, H., Han, X., and Sun, L. (2024). Benchmarking large language models in retrieval-augmented generation. *Proceedings of the AAAI Conference on Artificial Intelligence, 38*(16). https://doi.org/10.1609/aaai.v38i16.29728

Christensen, H. B., Hail, L., and Leuz, C. (2021). Mandatory CSR and sustainability reporting: Economic analysis and literature review. *Review of Accounting Studies, 26*, 1176–1248. https://doi.org/10.1007/s11142-021-09609-5

de Villiers, C., Dimes, R., and Molinari, M. (2024). How will AI text generation and processing impact sustainability reporting? Critical analysis, a conceptual framework and avenues for future research. *Sustainability Accounting, Management and Policy Journal, 15*(1), 96–118. https://doi.org/10.1108/SAMPJ-02-2023-0097

Diouf, D., and Boiral, O. (2017). The quality of sustainability reports and impression management: A stakeholder perspective. *Accounting, Auditing & Accountability Journal, 30*(3), 643–667. https://doi.org/10.1108/AAAJ-04-2015-2044

Es, S., James, J., Espinosa Anke, L., and Schockaert, S. (2024). RAGAs: Automated evaluation of retrieval augmented generation. *Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics: System Demonstrations*, 150–158. https://doi.org/10.18653/v1/2024.eacl-demo.16

European Commission. (2023). Commission Delegated Regulation (EU) 2023/2772 supplementing Directive 2013/34/EU as regards sustainability reporting standards. *Official Journal of the European Union*. https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj

European Parliament and Council of the European Union. (2022). Directive (EU) 2022/2464 as regards corporate sustainability reporting. *Official Journal of the European Union*. https://eur-lex.europa.eu/eli/dir/2022/2464/oj

Fabbri, A. R., Kryscinski, W., McCann, B., Xiong, C., Socher, R., and Radev, D. (2021). SummEval: Re-evaluating summarization evaluation. *Transactions of the Association for Computational Linguistics, 9*. https://doi.org/10.1162/tacl_a_00373

Flake, J. K., and Fried, E. I. (2020). Measurement schmeasurement: Questionable measurement practices and how to avoid them. *Advances in Methods and Practices in Psychological Science, 3*(4). https://doi.org/10.1177/2515245920952393

Gao, T., Yen, H., Yu, J., and Chen, D. (2023b). Enabling large language models to generate text with citations. *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing*, 6465–6488. https://doi.org/10.18653/v1/2023.emnlp-main.398

Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., and Wang, H. (2023a). Retrieval-augmented generation for large language models: A survey. *arXiv*. https://doi.org/10.48550/arXiv.2312.10997

Hummel, K., and Jobst, D. (2024). An overview of corporate sustainability reporting legislation in the European Union. *Accounting in Europe, 21*, 320–355. https://doi.org/10.1080/17449480.2024.2312145

Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y. J., Madotto, A., and Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys, 55*(12), 1–38. https://doi.org/10.1145/3571730

Kandpal, N., Deng, H., Roberts, A., Wallace, E., and Raffel, C. (2022). Large language models struggle to learn long-tail knowledge. *arXiv*. https://doi.org/10.48550/arXiv.2211.08411

Lazaridou, A., Kuncoro, A., Gribovskaya, E., Agrawal, D., Liska, A., Terzi, T., Gimenez, M., de Masson d'Autume, C., Ruder, S., Yogatama, D., Cao, K., Kocisky, T., Young, S., and Blunsom, P. (2021). Mind the gap: Assessing temporal generalization in neural language models. *arXiv*. https://doi.org/10.48550/arXiv.2102.01951

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-T., Rocktäschel, T., Riedel, S., and Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems, 33*. https://doi.org/10.48550/arXiv.2005.11401

Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., and Liang, P. (2024). Lost in the middle: How language models use long contexts. *Transactions of the Association for Computational Linguistics, 12*. https://doi.org/10.1162/tacl_a_00638

Lombardi, R., and Secundo, G. (2020). The digital transformation of corporate reporting: A systematic literature review and avenues for future research. *Meditari Accountancy Research*. https://doi.org/10.1108/MEDAR-04-2020-0870

Mallen, A., Asai, A., Zhong, V., Das, R., Khashabi, D., and Hajishirzi, H. (2023). When not to trust language models: Investigating effectiveness of parametric and non-parametric memories. *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics*, 9802–9822. https://doi.org/10.18653/v1/2023.acl-long.546

Michelon, G., Pilonato, S., and Ricceri, F. (2015). CSR reporting practices and the quality of disclosure: An empirical analysis. *Critical Perspectives on Accounting, 33*, 59–78. https://doi.org/10.1016/j.cpa.2014.10.003

Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W.-T., Koh, P. W., Iyyer, M., Zettlemoyer, L., and Hajishirzi, H. (2023). FActScore: Fine-grained atomic evaluation of factual precision in long-form text generation. *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing*, 12076–12100. https://doi.org/10.18653/v1/2023.emnlp-main.741

Moodaley, W., and Telukdarie, A. (2023). Greenwashing, sustainability reporting, and artificial intelligence: A systematic literature review. *Sustainability, 15*(2), 1481. https://doi.org/10.3390/su15021481

Ni, J., Bingler, J., Colesanti-Senni, C., Kraus, M., Gostlow, G., Schimanski, T., Stammbach, D., Ashraf Vaghefi, S., Wang, Q., Webersinke, N., Wekhof, T., Yu, T., and Leippold, M. (2023). ChatReport: Democratizing sustainability disclosure analysis through LLM-based tools. *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing: System Demonstrations*, 21–51. https://doi.org/10.18653/v1/2023.emnlp-demo.3

Niu, C., Wu, Y., Zhu, J., Xu, S., Shum, K., Zhong, R., Song, J., and Zhang, T. (2024). RAGTruth: A hallucination corpus for developing trustworthy retrieval-augmented language models. *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics*, 10862–10878. https://doi.org/10.18653/v1/2024.acl-long.585

Reimsbach, D., Hahn, R., and Gürtürk, A. (2018). Integrated reporting and assurance of sustainability information: An experimental study on professional investors' information processing. *European Accounting Review, 27*(3), 559–581. https://doi.org/10.1080/09638180.2016.1273787

Ru, D., Qiu, L., Hu, X., Zhang, T., Shi, P., Chang, S., Jiayang, C., Wang, C., Sun, S., Li, H., Zhang, Z., Wang, B., Jiang, J., He, T., Wang, Z., Liu, P., Zhang, Y., and Zhang, Z. (2024). RAGChecker: A fine-grained framework for diagnosing retrieval-augmented generation. *Advances in Neural Information Processing Systems, 37*, 21999–22027. https://doi.org/10.52202/079017-0692

Saad-Falcon, J., Khattab, O., Potts, C., and Zaharia, M. (2024). ARES: An automated evaluation framework for retrieval-augmented generation systems. *Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics*, 338–354. https://doi.org/10.18653/v1/2024.naacl-long.20

Seele, P. (2016). Digitally unified reporting: How XBRL-based real-time transparency helps in combining integrated sustainability reporting and performance control. *Journal of Cleaner Production, 136*, 65–77. https://doi.org/10.1016/j.jclepro.2016.01.102

Shi, F., Chen, X., Misra, K., Scales, N., Dohan, D., Chi, E. H., Schärli, N., and Zhou, D. (2023). Large language models can be easily distracted by irrelevant context. *Proceedings of the 40th International Conference on Machine Learning*. https://proceedings.mlr.press/v202/shi23a.html

Shuster, K., Poff, S., Chen, M., Kiela, D., and Weston, J. (2021). Retrieval augmentation reduces hallucination in conversation. *Findings of the Association for Computational Linguistics: EMNLP 2021*, 3784–3803. https://doi.org/10.18653/v1/2021.findings-emnlp.320

Simnett, R., Vanstraelen, A., and Chua, W. F. (2009). Assurance on sustainability reports: An international comparison. *The Accounting Review, 84*(3), 937–967. https://doi.org/10.2308/accr.2009.84.3.937

Song, Y., Kim, Y., and Iyyer, M. (2024). VeriScore: Evaluating the factuality of verifiable claims in long-form text generation. *Findings of the Association for Computational Linguistics: EMNLP 2024*, 9447–9474. https://doi.org/10.18653/v1/2024.findings-emnlp.552

Thakur, N., Pradeep, R., Upadhyay, S., Campos, D., Craswell, N., Soboroff, I., Dang, H. T., and Lin, J. (2025). Assessing support for the TREC 2024 RAG Track: A large-scale comparative study of LLM and human evaluations. *Proceedings of the 48th International ACM SIGIR Conference on Research and Development in Information Retrieval*. https://doi.org/10.1145/3726302.3730165

Wang, J.-F., Zhang, W.-Y., and Tseng, S.-P. (2025). An innovative ESGH-RAG module with ChatGPT-4o for automatic ESG-report generation. *The Journal of Supercomputing, 81*, Article 1103. https://doi.org/10.1007/s11227-025-07604-0

Wang, P., Li, L., Chen, L., Cai, Z., Zhu, D., Lin, B., Cao, Y., Kong, L., Liu, Q., Liu, T., and Sui, Z. (2024). Large language models are not fair evaluators. *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics*, 9440–9450. https://doi.org/10.18653/v1/2024.acl-long.511

Wu, Q., Xiang, X., Hejia, H., Wang, X., Wei Jie, Y., Satapathy, R., Filho, R. S., and Veeravalli, B. (2025). SusGen-GPT: A data-centric LLM for financial NLP and sustainability report generation. *Findings of the Association for Computational Linguistics: NAACL 2025*, 1184–1203. https://doi.org/10.18653/v1/2025.findings-naacl.66

Yang, J.-Y., Chi, R.-H., Wu, C.-C., Chen, L.-J., Lin, W.-M., Hu, H.-W., and Cheng, H.-R. (2024). EcoSmartGuide: Language Learning Model and retrieval-augmented generation-based platform for streamlined environmental, social, and governance information access and report generation. *2024 IEEE 6th Eurasia Conference on Biomedical Engineering, Healthcare and Sustainability*, 343–347. https://doi.org/10.1109/ECBIOS61468.2024.10885500

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., and Stoica, I. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. *Advances in Neural Information Processing Systems, 36*. https://doi.org/10.48550/arXiv.2306.05685

---

## 10. Literature-Search and Citation Caveats

1. The literature search supporting this document was targeted rather than systematic.
2. The strongest evidence for exact ESRS qualitative characteristics is the regulation itself, not a secondary academic paper.
3. Evidence on generative-AI use in sustainability-report drafting comes mainly from conceptual articles and recent technical prototypes; it should not be interpreted as evidence of widespread corporate adoption.
4. General NLP evidence on temporal knowledge, long-tail knowledge, hallucination, and context use motivates the study but does not directly estimate performance in ESRS disclosure drafting.
5. The absence of an identified boundary-aware, human-validated ESRS evaluation study is a qualified search result, not proof of non-existence.
6. Before journal submission, bibliographic metadata should be checked against publisher records and the novelty search should be documented using reproducible database queries and screening criteria.
7. The audience effects described in Step 7 are plausible risk pathways assembled from adjacent literatures. They are not direct causal estimates of harm produced by AI-generated sustainability disclosures or by the absence of the proposed evaluation framework.
