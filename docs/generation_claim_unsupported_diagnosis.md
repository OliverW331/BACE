# Unsupported Disclosure Claim Diagnosis

## 1. Purpose

This document defines the diagnostic stage applied after candidate selection and claim support assessment. It explains why a Disclosure Claim (DC) is unsupported by the candidate Evidence Claims (ECs) available within the same generation case.

Diagnosis is performed only for DCs whose support assessment returns an empty `support_sets` array. It does not replace candidate selection, repeat support-set construction, or evaluate external truth.

The stage answers one question:

> Which failure mechanism explains why the candidate evidence claims do not support the complete factual meaning of this disclosure claim?

## 2. Evidence and context boundary

Each diagnosis is conducted at the atomic-claim level. The diagnostic LLM receives:

- one unsupported DC;
- all candidate ECs previously selected for that DC;
- the shared company name and target reporting year.

The company and reporting year provide the same bounded interpretive context used during support assessment. They may help interpret an explicit expression, but they do not independently establish a factual proposition.

The LLM does not receive:

- raw evidence-card text;
- evidence-card identifiers or provenance;
- source documents, pages, or source years;
- retrieval scores;
- the task title or task definition;
- non-candidate ECs;
- the support judge's reasoning;
- external information.

The candidate EC texts therefore remain the complete factual evidence boundary for diagnosis.

## 3. Dynamic LLM input

The diagnostic LLM receives a fixed, general prompt and one dynamic JSON object:

```json
{
  "context_metadata": {
    "company_name": "Example Company",
    "target_reporting_year": 2024
  },
  "dc_claim": {
    "dc_claim_id": "dc_001",
    "dc_text": "An unsupported target claim."
  },
  "ec_claims": [
    {
      "ec_claim_id": "ec_003",
      "ec_text": "A relevant candidate evidence claim."
    }
  ]
}
```

Original claim identifiers are replaced deterministically with temporary IDs before the request. The same case-level ID mapping used by candidate selection and support assessment should be reused so that aliases remain stable across stages.

## 4. Diagnostic output

The output contains only the claim identifier, one diagnostic label, and a concise explanation:

```json
{
  "dc_claim_id": "dc_001",
  "unsupported_label": "factual_boundary_distortion",
  "rationale": "The evidence reports revenue outside high-impact sectors, but the target generalizes this to the classification of the company's overall business activities."
}
```

The output does not repeat the support verdict, candidate set, support sets, or a confidence score. Those fields are already available from earlier stages.

`rationale` must be a brief, claim-level explanation of the material support gap. It must compare the meaning of the DC with the supplied candidate ECs and must not introduce external facts.

## 5. Mutually exclusive diagnostic labels

Each unsupported DC receives exactly one label. The categories are made mutually exclusive by distinguishing direct incompatibility, multi-evidence combination, boundary transfer, semantic strengthening, and absence of an evidential anchor.

### 5.1 `contradiction`

The candidate evidence affirmatively establishes a proposition incompatible with the DC at the same material boundaries.

This includes an opposite trend, incompatible value, reversed comparison, negated status, or mutually exclusive factual state for the same entity, period, scope, and metric. Absence of support is not contradiction. When the apparent conflict results from different entities, periods, scopes, or metrics, use `factual_boundary_distortion` instead.

### 5.2 `evidence_conflation`

The DC combines elements supplied by two or more candidate ECs into a relationship, attribution, entity, event, or conclusion that the evidence does not establish.

The individual elements may each be evidenced; the unsupported construction between them is the failure. This label takes precedence over `inferential_inflation` when the invalid conclusion is specifically created by combining multiple ECs.

### 5.3 `factual_boundary_distortion`

The DC preserves the core fact of recognizable evidence but transfers it to a different material boundary.

Material boundaries include:

- entity or organizational level;
- reporting period, baseline year, or target year;
- geography, facility, or business unit;
- operational, emissions, product, population, or activity scope;
- metric definition, unit, or measurement boundary.

This label concerns where, when, to whom, or to what scope the fact applies. Changes in semantic force, certainty, implementation status, causality, or effectiveness are instead classified as `inferential_inflation`.

### 5.4 `inferential_inflation`

The DC and its evidence anchor have materially matching boundaries, but the DC derives a stronger semantic conclusion, characterization, relationship, status, or level of certainty than the evidence entails.

Typical forms include:

- converting an intention into an established plan;
- converting an activity into demonstrated effectiveness;
- converting an association into causation;
- converting partial progress into target achievement;
- converting tentative language into certainty;
- recharacterizing a process event as a broader strategy or approach.

Use `evidence_conflation` instead when the unsupported conclusion is constructed from elements supplied by multiple ECs.

### 5.5 `unsupported_novelty`

No candidate EC provides a recognizable evidential anchor for the core factual proposition of the DC.

This label applies when the DC asserts an activity, target, result, attribute, event, or relationship whose core predicate has no basis in the candidate evidence. It is the final category in the decision sequence, not a generic label for every unsupported conclusion.

## 6. Exclusive decision sequence

Apply the following checks in order and return the first applicable label:

1. If evidence affirmatively establishes an incompatible fact at matching material boundaries, return `contradiction`.
2. If the DC constructs an unsupported relationship from elements supplied by two or more ECs, return `evidence_conflation`.
3. If the DC transfers an anchored fact to a different entity, time, geography, scope, metric, or unit, return `factual_boundary_distortion`.
4. If the DC derives a stronger semantic conclusion from an anchored fact at otherwise matching boundaries, return `inferential_inflation`.
5. If no candidate EC anchors the core factual proposition, return `unsupported_novelty`.

Because the input DC is atomic, one primary mechanism should explain its support failure. If two genuinely independent mechanisms are required, the claim should be reviewed for insufficient atomic decomposition rather than assigned multiple labels.

## 7. Deterministic and LLM responsibilities

### 7.1 Deterministic processing

The script is responsible for:

1. selecting only DCs with empty `support_sets`;
2. joining each selected DC to its candidate EC set and permitted case context;
3. creating and restoring stable temporary claim identifiers;
4. skipping the LLM when the candidate set is empty;
5. validating the response schema, identifier, label vocabulary, and non-empty rationale;
6. recording call manifests, failures, token usage, and quality summaries;
7. aggregating diagnostic-label counts and rates.

When candidate selection returns an empty set, the diagnosis is constructed deterministically:

```json
{
  "dc_claim_id": "the_original_dc_id",
  "unsupported_label": "unsupported_novelty",
  "rationale": "No candidate evidence claim materially bears on the target claim."
}
```

### 7.2 LLM judgment

For unsupported DCs with one or more candidate ECs, the LLM is responsible for:

1. comparing the complete factual meaning of the DC with the candidate ECs;
2. applying the exclusive decision sequence to the material reason that full entailment fails;
3. selecting exactly one diagnostic label;
4. producing one concise rationale grounded only in the supplied claims.

## 8. Validation and canonical storage

Each LLM response must satisfy the following requirements:

- the root contains exactly `dc_claim_id`, `unsupported_label`, and `rationale`;
- `dc_claim_id` matches the requested temporary DC ID;
- `unsupported_label` is exactly one defined label;
- `rationale` is a non-empty string;
- no additional field is returned.

After validation, the script restores the original DC ID and writes one canonical record per unsupported DC to `dc_unsupported_diagnoses.jsonl`.

The candidate EC set remains stored separately in `dc_candidate_ecs.jsonl`. Diagnosis does not create support edges: candidate ECs explain the assessment context but do not become supporting ECs merely because they were used diagnostically.

## 9. Relationship to evaluation metrics

The unsupported label explains the primary failure mechanism; it does not replace the support verdict. For each diagnostic label $f$, reporting may include both prevalence among all DCs and composition among unsupported DCs:

$$
FailureRate_{f,d} =
\frac{|\{DC_j \in D_d : Label(DC_j)=f\}|}{|D_d|}
$$

$$
UnsupportedComposition_{f,d} =
\frac{|\{DC_j : Label(DC_j)=f\}|}{N_{unsupported,d}}
$$

Because every unsupported DC receives exactly one label, unsupported composition values sum to one across the five categories.

## 10. Methodological boundary

This stage diagnoses claim-level evidential failure within the supplied generation context. It does not determine whether the DC is true in the real world, evaluate retrieval quality, assess regulatory completeness, or inspect the original evidence text. Human validation should separately review a sample of support verdicts and diagnostic labels, because a diagnostic judgment assumes that the upstream unsupported verdict and candidate set are valid.
