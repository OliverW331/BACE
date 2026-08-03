# Retrieval Quality Evaluation Rubric

## Purpose

This rubric is for manually or LLM-assistively evaluating retrieved evidence cards used in the W2 RAG experiment.

The goal is to assess whether a retrieved card is a good evidence item for a specific company-year-task case. This is an evidence-level retrieval quality review. It is not an evaluation of a generated disclosure paragraph, answer quality, regulatory compliance, or final W2 output quality.

## Annotation Unit

One annotation unit is:

**one retrieved evidence card within one company-year-task case**

A case is defined by:

- `company_name`
- `target_reporting_year`
- `task_id`

A retrieved evidence card is defined by:

- `evidence_id`
- `evidence_type`
- `retrieval_text`
- source/provenance fields such as `source_file`, `source_year`, `page_start`, `page_end`, `metric`, `value_text`, and `unit`

Annotators should judge the card against the specific task and company-year context shown in the row. Do not judge the retrieval system globally from one row, and do not evaluate whether a generated response would be correct.

## General Annotation Principles

Use the card text and provenance as the primary evidence. If the card is partly relevant but too generic, stale, ambiguous, unreadable, or poorly tied to the target task, reflect that in the relevant score dimensions.

Scores should capture different aspects of quality:

- `relevance_0_3`: Is the card about the requested task?
- `usefulness_0_3`: Would the card help answer or support the W2 case?
- `source_fit_0_2`: Is the source/provenance appropriate for the company-year-task context?
- `specificity_0_2`: Is the evidence concrete and case-specific?
- `extraction_quality_0_2`: Is the extracted text readable and usable?

A card may be relevant but not useful, useful but weakly sourced, or readable but too generic. Score each dimension independently.

## 1. Retrieval Relevance Score: `relevance_0_3`

This score measures topical relevance to the task.

| Score | Label | Guidance |
|---:|---|---|
| 0 | Not relevant | The card is unrelated to the task, company climate disclosure, or requested ESRS E1 topic. |
| 1 | Weakly relevant | The card is broadly climate-, ESG-, energy-, emissions-, target-, or strategy-related, but does not clearly address the specific task. |
| 2 | Relevant | The card clearly relates to the task topic, but may be incomplete, generic, indirect, or missing key details. |
| 3 | Highly relevant | The card directly addresses the task and contains evidence that is clearly aligned with what the W2 generation step needs. |

Relevance is about topic match, not whether the card alone is sufficient.

## 2. Evidence Usefulness Score: `usefulness_0_3`

This score measures how useful the card would be as input evidence for answering the W2 task.

| Score | Label | Guidance |
|---:|---|---|
| 0 | Not useful | The card would not help answer the task, even if it contains some related words. |
| 1 | Marginally useful | The card provides weak context, vague background, or fragments that might be useful only with stronger evidence elsewhere. |
| 2 | Useful | The card provides concrete information that can support part of an answer, but may need complementary evidence. |
| 3 | Very useful | The card provides strong, directly usable evidence for the answer, such as a specific plan, action, target, emissions value, metric, date, investment, or implementation detail. |

Usefulness should consider whether the card can support a grounded generated answer, not whether the final answer is already complete.

## 3. Source/Provenance Fit Score: `source_fit_0_2`

This score measures whether the source metadata and provenance fit the company-year-task context.

| Score | Label | Guidance |
|---:|---|---|
| 0 | Poor fit | The source appears to be the wrong company, wrong reporting context, wrong evidence type, clearly outside the allowed time window, or otherwise unreliable for this case. |
| 1 | Acceptable fit | The source is plausibly from the right company/context, but may be older, indirect, non-primary, weakly contextualized, or missing some provenance detail. |
| 2 | Strong fit | The source is clearly appropriate for the company-year-task case, with usable provenance such as file, source year, page, metric, value, or document type. |

For CSV metric cards, check whether the metric/value/unit/source year fit the target task. For PDF cards, check source file, page range, source year, and whether the extracted passage appears to come from the right report context.

## 4. Specificity Score: `specificity_0_2`

This score measures how concrete and specific the evidence is.

| Score | Label | Guidance |
|---:|---|---|
| 0 | Generic | The card is vague, boilerplate, or general background with no specific facts, targets, values, actions, dates, or company-specific claims. |
| 1 | Moderately specific | The card includes some specific information but remains incomplete, broad, or only partially tied to the task. |
| 2 | Highly specific | The card contains concrete details such as quantitative values, named targets, dates, actions, resources, implementation status, emissions categories, scopes, units, or source-specific statements. |

Specificity is not the same as relevance. A card can be highly relevant but generic, or specific but only weakly relevant.

## 5. Extraction/Readability Quality Score: `extraction_quality_0_2`

This score measures whether the extracted text is readable and technically usable.

| Score | Label | Guidance |
|---:|---|---|
| 0 | Poor | The text is garbled, truncated beyond usefulness, dominated by layout artifacts, missing key context, or unreadable. |
| 1 | Usable with issues | The text is mostly readable but has layout noise, table extraction artifacts, awkward fragmentation, duplicated headers/footers, or missing context. |
| 2 | Clean | The text is readable, coherent, and sufficiently complete for evidence review. |

Do not penalize a card solely because it is short. Penalize it if the extraction prevents reliable interpretation.

## Derived Labels

After assigning numeric scores, derive the two boolean labels using these rules.

### `usable_evidence`

Set `usable_evidence = True` when:

```text
relevance_0_3 >= 2 and usefulness_0_3 >= 2 and source_fit_0_2 >= 1
```

Otherwise set `usable_evidence = False`.

Interpretation: the card is good enough to be used as supporting evidence in the W2 generation context, even if it is not the strongest evidence available.

### `strong_evidence`

Set `strong_evidence = True` when:

```text
relevance_0_3 == 3 and usefulness_0_3 >= 2 and source_fit_0_2 == 2
```

Otherwise set `strong_evidence = False`.

Interpretation: the card is directly on-task, useful, and strongly sourced for the company-year-task case.

A card can be usable without being strong.

## Task-Specific Guidance

### E1-1 Transition Plan

Task focus: transition plan for climate change mitigation.

Strong evidence may include:

- explicit transition plan or climate transition strategy;
- decarbonisation roadmap or implementation pathway;
- net-zero plan, Paris alignment, 1.5C alignment, or science-based transition claim with supporting detail;
- transition-plan governance, approval, timing, milestones, or implementation status;
- actions, targets, investments, CapEx, OpEx, or resources explicitly linked to the transition plan.

Score lower when:

- the card only mentions general sustainability ambition;
- the card discusses emissions or targets without connecting to a transition plan;
- the passage is about unrelated strategy, remuneration, governance, or risk unless it clearly supports the transition-plan question.

### E1-3 Actions/Resources

Task focus: climate-related actions and resources.

Strong evidence may include:

- specific mitigation or adaptation actions;
- operational initiatives, energy-efficiency programs, renewable energy procurement, fleet/building/process changes, product changes, supplier actions, or investment plans;
- implementation status, timelines, owners, or expected impact;
- financial resources, CapEx, OpEx, funding, staffing, or other resources allocated to climate actions;
- links between actions and emissions reduction, targets, or transition-plan implementation.

Score lower when:

- the card only states a target without action details;
- the card provides generic environmental policy language;
- the action is not clearly climate-related;
- the resource discussion is financial but not connected to climate actions.

### E1-4 Targets

Task focus: climate-related targets.

Strong evidence may include:

- GHG reduction targets;
- net-zero, carbon-neutrality, renewable energy, energy efficiency, or science-based targets;
- target baseline year, target year, scope, coverage, metric, unit, percentage reduction, or absolute value;
- progress against target;
- target governance, validation, or revision details.

Score lower when:

- the card mentions ambition without a measurable target;
- the target is not climate-related;
- the card gives emissions values but no target context;
- the card lacks baseline, target year, scope, or metric detail and is therefore only partially useful.

### E1-6 GHG Emissions

Task focus: gross Scope 1, Scope 2, Scope 3, and total GHG emissions, including relevant units, methods, and boundaries where available.

Strong evidence may include:

- Scope 1, Scope 2, Scope 3, or total GHG emissions values;
- market-based or location-based Scope 2 values;
- emissions intensity metrics;
- base-year or comparative-year emissions data;
- units such as tCO2e, ktCO2e, MtCO2e, or equivalent;
- methodological notes, reporting boundaries, restatements, exclusions, or assurance context directly tied to emissions figures.

Score lower when:

- the card only discusses emissions reduction qualitatively without emissions values;
- the card gives targets but no actual emissions data;
- the card includes environmental metrics unrelated to GHG emissions;
- units, scope, or year are unclear and cannot be inferred from provenance.

CSV metric cards can be especially strong for E1-6 if they contain the right metric, value, unit, and source year. PDF narrative or table-row cards can also be strong when they provide context, boundaries, scope definitions, or reported emissions tables.

## Common Edge Cases

### Old but Eligible Evidence

If a source year is older than the target reporting year but within the retrieval package window, do not automatically mark it poor. Score based on whether it plausibly supports the target case. Use `source_fit_0_2 = 1` when the age makes the evidence less direct but still potentially useful.

### Correct Company, Wrong Task

If the card is from the correct company and year range but addresses another E1 task, give source/provenance fit credit but lower relevance and usefulness.

### Metric-Only Cards

Metric-only CSV cards can be highly useful when the metric, value, unit, and year directly match the task. They may score lower on extraction/readability only if the text is unclear or missing needed context.

### Narrative-Only Cards

Narrative cards can be strong when they contain concrete task evidence. Do not penalize them for lacking a numeric value unless the task specifically requires one, such as many E1-6 emissions cases.

### Table-Row Cards

PDF table-row cards may have extraction artifacts. Score extraction quality separately from relevance and usefulness. A noisy table row can still be useful if the value, label, year, and unit are interpretable.

## What Not To Evaluate

Do not use this rubric to score:

- generated disclosure quality;
- writing style of generated text;
- whether the final RAG answer is complete;
- legal or regulatory compliance of the company's disclosure;
- whether the retrieval model is generally better than another model;
- whether diagnostic risk flags are correct as ground truth.

Diagnostic risk flags are sampling aids and coverage signals. They are not labels of relevance.

## Recommended Annotation Workflow

1. Read the case fields: company, target reporting year, and task.
2. Read the evidence type and source/provenance fields.
3. Read the retrieval text.
4. Assign the five numeric scores independently.
5. Derive `usable_evidence` and `strong_evidence` from the numeric scores.
6. Add `reviewer_notes` only when needed to explain ambiguity, extraction problems, provenance concerns, or task-specific interpretation.

Keep notes concise and evidence-specific.