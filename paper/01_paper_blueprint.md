# BACE paper blueprint

**Version:** Working blueprint, revision 5, 29 September 2026.
**Target:** Nature Sustainability, Article.  
**Positioning:** Author-confirmed focus on disclosure evidence credibility and boundaries.  
**Evidence status:** Descriptive main-run analysis available; completed human-validation results not verified.

## Agreed framing

**Agreed focus:** Evidence credibility and factual boundaries in AI-assisted sustainability disclosure, with BACE providing the operational method and empirical analysis.

The author selected this focus on 29 September 2026.
The paper leads with the reporting problem and uses the method, comparative evaluation and validation to develop the answer.
Evidentiary support is treated as one component of disclosure reliability; the study does not measure all dimensions of reporting quality.
The title, precise wording and final conclusions remain working proposals.

| Possible emphasis | Leading question | Role in the proposed paper | Evidence implications |
|---|---|---|---|
| Disclosure evidence boundaries | How well do generated disclosures preserve the factual meaning of supplied evidence? | Agreed organizing question: connects the study directly to sustainability information and its review. | Support estimates and diagnoses require transparent measurement limits and validation. |
| BACE method development | How can evidence support and its failures be operationalized and assessed? | Methodological contribution supporting the organizing question. | Novelty must be established against prior methods; validation must match the claimed scope. |
| General-purpose evaluator applicability | How do existing evaluators assess the same generated disclosures? | Comparative result informing interpretation of automated assessment. | Native-score differences support a finding of disagreement; comparative accuracy requires an appropriate independent reference. |

The reporting problem organizes the title, Introduction and Discussion; method development and evaluator comparison support this argument.
The agreed emphasis does not change the empirical standards for the claims.
The [research foundation](03_research_foundation.md) develops the background, problem, gap and purpose as editable English prose.

## Working title

**Evidence boundaries in AI-generated corporate sustainability disclosures**

Finalize the title after the main findings and validation scope are settled.

## Research background and problem

Corporate sustainability disclosures communicate information about environmental, social and governance matters to stakeholders.
Their usefulness depends in part on whether statements can be traced to supporting evidence.
Generative AI and retrieval-augmented generation offer ways to assist disclosure drafting, but providing relevant evidence does not establish that generated statements preserve its meaning.
Changes to the entity, reporting period, organizational scope, metric or certainty can alter a disclosure while retaining recognizable source content.

These background statements require citation support in the manuscript.
The existing Introduction evidence map is a starting point for verification, not a substitute for checking the underlying sources.

## Research gap

The [original-source review](04_research_gap_verification.md) establishes prior work on claim-level support, preservation of material context, joint evidence assessment and human evaluation of unsupported sustainability answers.
BACE's contribution is the reporting-focused integration and empirical evaluation of an explicit support representation and diagnosis scheme within the supplied-evidence boundary.
The study asks how these support judgments and diagnoses characterize generated disclosure statements and differ across evaluation methods, with validation at the scope actually completed.

Do not frame the gap as an absence of boundary-sensitive evaluation or ESG-specific human benchmarks.
Exclusive priority remains unestablished, including because two relevant full texts were not accessible in the targeted review.

## Research aim and questions

**Aim:** To assess the evidentiary support of AI-generated sustainability disclosures, characterize the unsupported claims identified by boundary-aware evaluation, and examine how support assessments vary across evaluation methods.

**Central question:** To what extent do AI-generated sustainability disclosures preserve the factual boundaries of the evidence supplied to the model?

| ID | Research question | Evidence required |
|---|---|---|
| RQ1 | To what extent are generated sustainability disclosures supported by the evidence supplied to the model? | Support distributions, direct and inferred support, and descriptive variation across tasks and companies. |
| RQ2 | What types of evidence-boundary failures does BACE identify, and how are they distributed across disclosure tasks? | Automated diagnosis frequencies, traceable examples and explicit qualifications about evaluator errors. |
| RQ3 | How do BACE assessments differ from those of general-purpose RAG evaluators? | Paired native scores, claim inventories and source-inspected disagreements. |
| RQ4 | How closely do BACE support and diagnostic judgments agree with independent human assessments? | Completed independent annotations, agreement analysis and documented adjudication. |

RQ4 is conditional on completion of the specified validation study.
Its judgments use supplied DCs and candidate ECs; agreement does not independently validate extraction or candidate recall.
These questions organize the paper retrospectively and are not a preregistered analysis plan.

## Study scope and central concepts

The planned design comprises 30 companies, five reporting years (2019–2023) and 12 tasks based on the 2023 ESRS edition, yielding 1,800 planned disclosures.
The current analysis contains 1,798 completed BACE cases.
One fixed retrieval and generation configuration is evaluated with BACE, RAGChecker and RAGAS.

- **Evidence boundary:** The evidence actually supplied to the generator.
- **Factual boundaries:** Material qualifiers such as entity, time, scope, metric and certainty.
- **Evidence claim (EC):** An atomic factual proposition extracted from supplied evidence.
- **Disclosure claim (DC):** An atomic proposition extracted from a generated disclosure.
- **Support:** An operational judgment that the supplied candidate ECs establish the complete DC, directly or by permitted inference.

The paper should distinguish source evidence, extracted ECs, selected candidate ECs and final support judgments.
Each transformation can affect the observed results.

## Candidate central message

**Conceptual focus:** Preserving the factual boundaries of evidence is essential to substantiating AI-generated sustainability disclosures.

**Evidence-grounded working message:** In the evaluated sustainability-disclosure workflow, BACE classifies a substantial share of generated claims as unsupported, with boundary distortion and evidence conflation accounting for most automated diagnoses. Its assessments differ markedly from general-purpose evaluator scores, motivating explicit examination of support criteria and independent validation of automated judgments.

The conceptual focus expresses the rationale for the study.
The working message summarizes the current automated observations; it is not a final validated conclusion about the true error rate.
It does not establish that BACE is more accurate, that unsupported statements are false, or that observed diagnoses are all correct.

## Three principal findings and their argumentative roles

These are proposed priorities for the main text, with numerical sources and qualifications in the [evidence map](02_evidence_map.md).
The [Results storyline](05_results_storyline.md) now implements these priorities as source-linked result units and a five-slot main-figure plan, with independent arithmetic and local annotation-status checks.

| Priority | Candidate result sentence | Role in the argument | Evidence-map IDs |
|---|---|---|---|
| 1. Extent of support | Across 1,798 completed disclosures, the mean disclosure-level BACE support rate was 55.4%. | Establishes the extent of support assigned under an explicit operational definition. | C1–C3 |
| 2. Form of unsupported content | Factual boundary distortion and evidence conflation accounted for 73.5% of BACE's unsupported-claim diagnoses. | Identifies the dominant automated diagnostic patterns and motivates close inspection of how source meaning is altered. | C4, C6 |
| 3. Dependence on assessment method | On the same disclosures, BACE's native scores averaged 34.9 and 35.3 percentage points below those of RAGChecker and RAGAS, respectively. | Shows that the assessed level of support differs across operationalizations and motivates scrutiny of inventories and judgments. | C5 |

The first number is a disclosure-level mean; the second uses only BACE-unsupported DCs as its denominator.
The third compares different native claim inventories on the same cases and does not isolate the cause of the score gap.

**Cross-cutting validation question:** How well do independent reviewers support the automated judgments underlying these observations?
Completed human-validation results should qualify the interpretation throughout the paper, as well as appear in their own Results subsection.
The planned conditional validation may strengthen conclusions about judgment agreement, but it will not independently establish pipeline accuracy or comparator superiority.

Task and company heterogeneity describe the scope and variation of these findings.
Evidence coverage and inference rates provide additional dimensions of BACE assessment.
Retain these analyses where they advance the central argument; none requires a separate headline contribution by default.

## Intended contributions

1. **Operational:** A reporting-focused specification of material evidence boundaries, building on established contextual claim evaluation.
2. **Methodological:** An integrated, traceable claim-support representation that distinguishes direct support, inferred support, evidence use and unsupported-claim diagnoses.
3. **Empirical:** Evidence about support patterns and evaluator differences across a defined set of corporate disclosure tasks.
4. **Validation, conditional:** An assessment of support and diagnosis decisions against independent human judgments using the same supplied claim inputs.

The sustainability relevance lies in how disclosure information can be substantiated and reviewed.
Implications for governance and assurance should be discussed as implications; the experiment does not measure downstream investor effects, organizational adoption or reductions in greenwashing.

## Argument in six sentences

The following is a drafting scaffold, not a citation-complete Introduction or an abstract.

1. Corporate sustainability disclosures need a traceable evidentiary basis for their factual statements.
2. Retrieval-augmented generation supplies evidence for drafting, while leaving open whether generated statements preserve its material qualifiers and relationships.
3. The adequacy of automated support assessment in this reporting context therefore requires empirical examination.
4. We operationalize claim support and its failure types with BACE and examine a fixed disclosure-generation workflow across companies, years and ESRS-based tasks.
5. The current analysis shows substantial BACE-assessed unsupported content, a concentration of boundary-distortion and conflation diagnoses, and marked differences among native evaluator scores.
6. The resulting contribution is an explicit, inspectable account of evidence support in this workflow, whose validity and implications must be interpreted in light of human assessment and pipeline limitations.

Sentences 1–3 need literature support, sentence 4 is grounded in the protocol, and sentence 5 is grounded in the evidence map.
Sentence 6 must be revised to reflect the completed validation results.

## Manuscript architecture

| Section | Proposed content | Planning allocation |
|---|---|---|
| Introduction | Reporting stakes; emerging AI drafting; unresolved evidence-support problem; specific gap; study aim and contribution. | About 650 words, four paragraphs. |
| Results | Study scope; support patterns; automated diagnoses; evaluator differences; completed human validation if available. | About 1,750 words. |
| Discussion | Meaning for disclosure review; relation to prior work; alternatives and limitations; bounded implications. | About 900 words. |
| Methods | Sampling; task design; source preparation; retrieval and generation; BACE; comparators; statistics; human validation. | Sufficient detail for reproducibility; excluded from the main-text limit. |

This allocates approximately 3,300 main-text words, leaving 200 words of flexibility.
The allocation is a writing aid, not a journal requirement.

Provisional Results subheadings:

1. Study scope and boundary-aware evaluation
2. Evidentiary support across disclosure tasks
3. Patterns of unsupported disclosure claims
4. Differences among automated evaluators
5. Agreement with independent human assessments

The fifth subsection requires completed results.
Use final findings to refine the subheadings; preserve neutral wording while evidence is unresolved.

Provisional Discussion subheadings:

1. Implications for sustainability disclosure review
2. Interpretation of evaluator differences
3. Limitations and scope of inference

## Decisions to resolve before finalizing the argument

- Retain the verified integration/domain-evaluation framing; resolve the inaccessible close comparisons before making any stronger priority claim.
- Document the final analyzed cohort and treatment of the two currently missing BACE cases.
- Establish the actual human-annotation status and the conclusions its design supports.
- Determine whether conditional judgment validation is sufficient for the intended methodological claims; identify any additional validation only after specifying the unsupported claim.
- Review the five proposed main display items in the Results storyline; the validation slot depends on completed annotations and analysis.
- Update the earlier Introduction plan to reflect the completed inclusion of RAGAS in the main experiment.
