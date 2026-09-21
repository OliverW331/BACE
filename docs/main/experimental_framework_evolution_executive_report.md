# Research Progress and Revised Experimental Design

**Asynchronous update for supervisory review | 10 September 2026**

## 1. Progress and the reason for changing direction

The W2 workflow has now been run end to end, from company-evidence retrieval to disclosure generation and claim-level evaluation. The completed E1 pilot produced all 120 planned disclosures. Its initial automated evaluation found a mean disclosure-level support rate of **67.91%**, indicating that successful generation still leaves a substantial evidence-support question to investigate.

The original experimental direction involved comparing W2 with W1, a workflow based on using the ChatGPT app with uploaded company evidence. Subsequent exploration of W1's feasibility led to a practical concern: implementing that arm entirely through the app, while also automating execution and maintaining sufficiently controlled experimental records, was not a realistic basis for the main study.

The experiment is therefore being refocused around the completed W2 infrastructure. **One fixed RAG workflow will produce disclosures, and three evaluation frameworks will assess the same evidence and outputs: BACE, RAGChecker and RAGAS.** The paper's message changes accordingly, from comparing generation workflows to investigating evidence support and the validity and diagnostic value of evaluation in sustainability reporting.

### The original comparison

| Workflow | Intended role |
|---|---|
| **W1: ChatGPT app with company evidence** | Generate disclosure text from an uploaded or full rolling-window evidence package through an app-based workflow. |
| **W2: Controlled evidence-card RAG** | Retrieve relevant company evidence, construct a recorded prompt, generate a disclosure, and assess its claims against the supplied evidence. |

Both workflows were evidence-conditioned. The intended contrast concerned how evidence was made available and used in the generation workflow.

### What W2 has delivered

The completed pilot covers **5 companies, reporting years 2018-2023, and 4 ESRS E1 tasks**: transition plans, actions and resources, targets, and greenhouse-gas emissions. This gives 5 x 6 x 4 = **120 generation cases**.

The retained run uses text-embedding-3-large with hybrid lexical/dense retrieval and selects up to ten cards from each of three evidence types: narrative text, PDF table rows and structured metrics. The generator receives 26-30 cards per case. GPT-5.6-sol produced all 120 disclosures within the requested 300-500-word range. Case identifiers, supplied evidence, prompts, outputs and evaluation records are retained for analysis.

**Decision:** Preserve this working pipeline and change the experimental comparison. The W2 results remain the starting evidence; the W1 feasibility assessment explains the change in design.

Source: [Generation run manifest](/home/muwang/master_thesis/_archive/previous_stage_20260921/generation_outputs/w2_main_text_embedding_3_large_stratified_n10_top200/gpt_5_6_sol_run1/generation_run_manifest.json); [original workflow definitions](/home/muwang/master_thesis/_archive/previous_stage_20260921/config/prompts/generation_prompt_templates.json). W1 feasibility is the project assessment described in Section 3.

<div class="page-break"></div>

## 2. What the completed W2 experiment found

The initial evaluation decomposed the supplied evidence into **13,533 case-local Evidence Claims (ECs)** and the generated disclosures into **5,518 Disclosure Claims (DCs)**, after deduplication. It then searched for evidence supporting each DC and diagnosed claims without sufficient support.

### Overall evidence support

| Outcome | Number of disclosure claims | Mean share per disclosure |
|---|---:|---:|
| Directly supported | 2,592 | 47.67% |
| Supported through valid inference | 1,115 | 20.24% |
| Unsupported under the evaluation rules | 1,811 | 32.09% |
| **All supported claims** | **3,707** | **67.91%** |

Percentages average the 120 disclosure-level rates. Pooling claims instead gives **67.18%** support. Every disclosure contained at least one claim classified as unsupported by the initial evaluator.

### Variation across E1 tasks

| Task | Disclosures | Mean support rate |
|---|---:|---:|
| E1-1: Transition plan | 30 | 64.94% |
| E1-3: Actions and resources | 30 | 65.50% |
| E1-4: Targets | 30 | 70.92% |
| E1-6: GHG emissions | 30 | 70.31% |

Targets and emissions received somewhat higher support estimates. These are descriptive differences; task content and available evidence also differ.

### What the failure diagnoses suggest

Among unsupported claims, the largest category was **evidence conflation**: 604 claims, or 33.35%. Another 364 were assigned to inferential inflation and 310 to factual boundary distortion. These diagnoses concern how generation combines evidence, strengthens statements, or changes their boundaries.

A further **474 claims concerned non-disclosure statements**, such as asserting that a particular item was not reported. These require separate interpretation because an assertion about missing information is not equivalent to an affirmative factual hallucination. The remaining diagnoses were unsupported novelty (54) and contradiction (5).

**Interpretation:** W2 is operational and supplies support failures for investigation. Later audits identified extraction and context-preservation defects, so these automated estimates still need independent validation. “Unsupported” concerns support within the supplied evidence; it does not establish real-world falsity.

Source: Full-run [W2 analysis notebook](/home/muwang/master_thesis/evidence_pilot/w2_generation_evaluation_analysis.ipynb), [support records](/home/muwang/master_thesis/evidence_pilot/evaluation/generation_claim_support/text_embedding_3_large_gpt_5_6_sol_schema_only_full/dc_support_sets.jsonl) and [diagnosis summary](/home/muwang/master_thesis/evidence_pilot/evaluation/generation_claim_unsupported_diagnosis/text_embedding_3_large_gpt_5_6_sol_schema_only_full/quality_summary.json). Recomputed for all 120 cases; separate from the later ten-case comparison.

<div class="page-break"></div>

## 3. Why the W1 feasibility exploration changed the design

W1 was intended to represent an app-based route to disclosure generation: supply company documents or an evidence package to ChatGPT, issue the disclosure instruction, and collect the response. Its appeal was a workflow close to how a researcher or reporting team might use a general-purpose application.

The feasibility exploration led to the assessment that **relying entirely on the ChatGPT app while automating W1 was not sufficiently practical and controllable for the planned experiment**. Producing individual answers was not the relevant completion criterion. The research arm also needed consistent case execution, traceable evidence exposure and reliable records across a large set of company-year-task combinations.

### Why this matters experimentally

| Requirement | Implication for the app-based W1 design |
|---|---|
| Repeatable case execution | Each case needs a consistent setup, document set, instruction, output capture and recovery procedure. App interaction would require an additional automation and monitoring layer. |
| Traceable evidence exposure | The comparison needs to distinguish documents supplied to the application from evidence actually available to the generation step. That equivalence had not been established for W1. |
| Comparable experimental conditions | Any workflow difference must be interpreted alongside differences in evidence handling, context and application behaviour. Without sufficient records, a result would be difficult to attribute. |
| Scalable quality control | Manual checking of uploads, sessions and outputs would add work as the case matrix grows. A successful demonstration on a few cases would not establish reliable execution at study scale. |

These are the methodological requirements underlying the feasibility assessment. W1 was not taken through a completed, matched generation benchmark, and no numerical W1 failure rate, throughput estimate or quality comparison is reported here.

### The resulting decision

Keeping W1 as a main experimental arm would make completion depend on building and validating an additional app-automation workflow. It would also complicate the interpretation of any W1-W2 difference. The revised design therefore removes that dependency and uses the reproducible W2 pipeline already in place.

This changes the research question. The study will no longer seek to establish which of those two generation workflows performs better. Instead, it will investigate the reliability of disclosures from one fixed RAG workflow and whether different evaluators identify the same support failures.

The change preserves the project's most developed assets: the company evidence, retrieval process, generated disclosures and claim-support records. It also creates a comparison in which the raw evidence and generated text can be held constant while the evaluation method varies.

**Status:** This was a feasibility-based scope decision. A controlled W1-W2 performance comparison was not completed; the decision concerns the suitability of W1 for this project's experimental requirements.

<div class="page-break"></div>

## 4. The revised experiment: one RAG workflow, three evaluators

The revised design holds the generation workflow fixed and compares **BACE, RAGChecker and RAGAS** on the same company-year-task cases. BACE is the name adopted for the project's existing claim-level approach: **Boundary-Aware Claim Evaluation**.

For each case, the workflow is:

1. Retrieve company evidence under the specified temporal and organizational boundaries.
2. Preserve the exact evidence supplied in the generation prompt and generate one disclosure.
3. Run each evaluator independently on that evidence and disclosure.
4. Compare support estimates and explanations, using independent human annotation to assess correctness.

### What each evaluator contributes

| Evaluator | Role in the comparison |
|---|---|
| **BACE** | Extract evidence and disclosure claims, reconstruct minimal sufficient support sets, distinguish direct from inferred support, and diagnose unsupported claims using boundary-sensitive categories. |
| **RAGChecker** | Provide an established external faithfulness assessment using its own claim extraction and entailment procedure. The inspected native implementation checks evidence cards individually. |
| **RAGAS** | Provide a second established faithfulness assessment using its own statement extraction and checking procedure. Its inspected implementation joins the supplied contexts for checking. |

The primary external comparison uses faithfulness, which can be assessed without an expert-written reference disclosure. Other metrics requiring reference answers are outside this comparison unless those references are separately constructed.

### What is already feasible

Both external frameworks completed a **ten-case engineering pilot** using existing W2 disclosures. Their integration is workable. This selected sample is separate from the full 120-case results and still lacks independent human validation.

BACE extraction revisions changed support estimates on unchanged disclosures, demonstrating measurement sensitivity. The revised extraction candidate retains documented defects and has not replaced the default pipeline. Extraction validation is therefore part of the remaining work.

### What the comparison must establish

Score differences can arise from claim extraction, evidence segmentation or support judgments. Higher faithfulness does not establish better evaluation accuracy. Independent human annotation must assess false alarms and missed failures, and resolve the substantive disagreements.

The experiment tests **validity** and **incremental diagnostic value**. BACE may add useful support paths or boundary explanations even when verdicts agree, provided those explanations are validated.

Source: [BACE method](/home/muwang/master_thesis/docs/generation_evaluation.md); [external pilot](/home/muwang/master_thesis/evidence_pilot/evaluation/external_comparison/pilot_v1/summary.json); [revised comparison](/home/muwang/master_thesis/evidence_pilot/evaluation/external_comparison/pilot_v2/summary.json). This update includes both external evaluators in the planned comparison, superseding the earlier design document's conditional treatment of full-study RAGAS inclusion.

<div class="page-break"></div>

## 5. How the paper's messaging changes

The original comparison would have organized the paper around differences between W1 and W2. Removing W1 changes the claim the experiment can support. The paper should now focus on **whether generated sustainability disclosures preserve the meaning and boundaries of supplied evidence, and how reliably that can be evaluated**.

### Proposed central message

> RAG makes corporate evidence available for disclosure generation, but the reliability of the resulting text depends on whether its claims remain supported by that evidence. This study evaluates those support relationships and tests BACE against RAGChecker, RAGAS and independent human judgments across environmental, social and governance disclosure tasks.

The W2 pilot supplies the starting observation: fluent disclosures can contain claims that the internal evaluator cannot support. The next step is to validate those judgments and explanations.

### Revised research questions

1. To what extent are generated disclosure claims supported by the evidence supplied to the fixed RAG workflow?
2. Which mechanisms account for unsupported claims, including changes in temporal, organizational, quantitative or commitment boundaries?
3. How accurately do BACE, RAGChecker and RAGAS assess support against independent human judgments, and what additional diagnostic information does BACE provide?
4. Do the support patterns and evaluation findings recur across E1, S1 and G1 tasks?

### Consequences for manuscript structure

| Section | Revised emphasis |
|---|---|
| **Introduction** | Explain why scope, period, measurement boundaries and implementation status determine disclosure meaning. Introduce the evaluation problem and existing RAG evaluators. |
| **Methods** | Describe the fixed workflow, three evaluators, human validation and expanded case matrix. Record extraction and evaluator versions. |
| **Results** | Establish measurement validity, then report support patterns, failure mechanisms, evaluator disagreements and variation across standards and tasks. |
| **Discussion** | Connect validated findings to disclosure-review needs, within the tested workflow and evidence corpus. |

The contribution concerns validated evidence support in sustainability reporting. Claim-level evaluation already exists; whether BACE adds value remains an empirical question.

If BACE and the comparators perform similarly against humans, that is a meaningful convergence result. If humans confirm additional correct detections or explanations from BACE, the paper can claim incremental value for those demonstrated cases and mechanisms.

The intended outlet remains *Nature Sustainability*. Claims about improved human-review performance or downstream sustainability outcomes would require additional experiments.

Source: [Introduction evidence map](/home/muwang/master_thesis/docs/main/introduction/introduction_logic_chain_and_evidence.md); [experiment objectives and claim boundaries](/home/muwang/master_thesis/docs/main/bace_experiment_flow_and_claims.md).

<div class="page-break"></div>

## 6. Expanded scope and the path to the main study

The revised experiment expands the substantive coverage from climate disclosure alone to **E1, S1 and G1, with four tasks per standard and five reporting years**. The purpose is to examine whether support failures and evaluation behaviour transfer across environmental, social and governance reporting content.

### Planned study matrix

| Dimension | Completed W2 pilot | Revised main study |
|---|---|---|
| Companies | 5 | 30 planned |
| Reporting years | 2018-2023: six years | **2019-2023: five years** |
| Standards | E1: Climate Change | **E1, S1: Own Workforce, G1: Business Conduct** |
| Tasks | 4 E1 tasks | **4 per standard; 12 in total** |
| Generation workflow | W2 evidence-card RAG | One fixed evidence-card RAG workflow |
| Main evaluation | Internal claim-support assessment | **BACE, RAGChecker and RAGAS**, with human validation |
| Disclosures | 120 completed | **30 x 5 x 12 = 1,800 planned** |

The four E1 tasks are retained. Four S1 and four G1 tasks must be selected before the main run, based on meaningful workforce and business-conduct disclosures rather than artificial matching to E1 task types.

Of the 120 pilot cases, 100 fall within 2019-2023. Reuse depends on matching the frozen main-study protocol; these development cases should not automatically become fresh validation data.

The historical cases are **ESRS-style reporting simulations**, not observations of mandatory ESRS reporting or historical AI adoption.

### Next steps

1. **Finalize the case matrix:** select the 30 companies, define the eight S1/G1 tasks, and specify document eligibility and temporal evidence windows.
2. **Validate and freeze evaluation:** resolve claim-extraction requirements and assess extraction, support judgments and diagnoses with at least two independent human annotators and adjudication.
3. **Pilot the expanded domains:** check retrieval coverage and evaluator behaviour on E1/S1/G1 cases, then freeze the generation and three-evaluator configurations.
4. **Execute and write to the evidence:** run the main matrix, aggregate at disclosure level with company clustering, and formulate conclusions from validated results.

**Current position:** W2 is complete; W1's app-based execution requirements make it unsuitable as the main comparison arm in this project. The revised study preserves the RAG pipeline, compares three evaluators, and expands the reporting scope. Its paper contribution centres on evidence reliability and evaluation validity.

Source: [Project Framework v2](/home/muwang/master_thesis/docs/main/project_framwork_v2.md) supplies the 30-company, five-year, 12-task scope. This update records the subsequent decision to include both RAGChecker and RAGAS; the expanded experiment remains planned, not completed.
