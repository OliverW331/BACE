# Candidate Selection and Claim Support Assessment

## 1. Purpose

This document defines the two-stage relationship assessment performed after Evidence Claim (EC) and Disclosure Claim (DC) extraction and semantic deduplication.

For each DC, the procedure first selects a recall-oriented candidate EC set from the complete deduplicated EC set for the same generation case. A separate support judge then identifies zero or more minimal sufficient support sets from those candidates.

The two stages answer different questions:

1. Which ECs materially bear on assessing this DC?
2. Which minimal combinations of those ECs fully support the DC?

Candidate selection is not a support verdict. Candidate ECs are retained even when the DC is unsupported so that a later diagnostic stage can explain the failure using the relevant evidence.

## 2. Evidence boundary

Both stages operate only on self-contained deduplicated claim texts. No LLM request contains:

- provenance;
- evidence-card identifiers;
- source spans;
- retrieval scores;
- task definitions;
- company, reporting-year, or other case metadata;
- thesis-specific information.

The supplied claim texts are the complete factual boundary for each model call. External facts and unstated assumptions are prohibited.

## 3. End-to-end procedure

```text
Deduplicated ECs and DCs
        |
        v
Deterministic temporary-ID mapping
        |
        v
Candidate LLM: one DC + complete case EC set
        |
        v
Candidate EC IDs
        |
        v
Support LLM: one DC + its candidate EC set
        |
        v
Minimal sufficient support sets
        |
        v
Deterministic validation and original-ID restoration
        |
        v
Supported or not supported
        |
        v
Later diagnosis of unsupported DCs using candidate ECs
```

For a disclosure containing `n` deduplicated DCs, candidate selection plans `n` LLM calls. Support assessment plans at most `n` additional LLM calls. A DC with an empty candidate set is assigned an empty support-set result deterministically without a support-model call.

## 4. Deterministic temporary IDs

Original IDs are not sent to either LLM. For each generation case, the scripts:

1. sort original EC IDs lexicographically and assign `ec_001`, `ec_002`, and so on;
2. sort original DC IDs lexicographically and assign `dc_001`, `dc_002`, and so on;
3. retain the mappings for validation, audit, and restoration.

Both stages derive aliases from the complete deduplicated claim sets, so a claim receives the same temporary ID in candidate selection and support assessment.

## 5. Stage 1: candidate selection

### 5.1 LLM input

The candidate LLM receives a fixed, general prompt and one dynamic JSON object:

```json
{
  "ec_claims": [
    {
      "ec_claim_id": "ec_001",
      "ec_text": "A self-contained evidence claim."
    },
    {
      "ec_claim_id": "ec_002",
      "ec_text": "Another self-contained evidence claim."
    }
  ],
  "dc_claim": {
    "dc_claim_id": "dc_001",
    "dc_text": "A self-contained target claim."
  }
}
```

The `ec_claims` array contains the complete deduplicated EC set for the same generation case.

### 5.2 Candidate criterion

Candidate selection is recall-oriented but not purely topical. An EC is a candidate when it materially bears on at least one component or boundary of the DC, including when it:

- supports all or part of the DC;
- could contribute to a joint inference;
- differs in a material entity, time, scope, quantity, modality, status, polarity, or relationship;
- contradicts a material component;
- helps explain why the DC may be partially supported or unsupported.

Shared topics, entities, or keywords alone are insufficient.

### 5.3 LLM and canonical outputs

The LLM returns temporary IDs only:

```json
{
  "dc_claim_id": "dc_001",
  "candidate_ec_ids": ["ec_021", "ec_049", "ec_084"]
}
```

After validation, the script restores original IDs and writes the same two-field structure to `dc_candidate_ecs.jsonl`.

## 6. Stage 2: support assessment

### 6.1 LLM input

The support LLM receives an independent, general support prompt and one dynamic JSON object:

```json
{
  "ec_claims": [
    {
      "ec_claim_id": "ec_021",
      "ec_text": "A candidate evidence claim."
    },
    {
      "ec_claim_id": "ec_049",
      "ec_text": "Another candidate evidence claim."
    }
  ],
  "dc_claim": {
    "dc_claim_id": "dc_001",
    "dc_text": "A self-contained target claim."
  }
}
```

The support prompt does not refer to candidate selection or any other pipeline stage. It treats `ec_claims` simply as the supplied evidence set and applies a full-support standard.

### 6.2 Support-set criterion

Each returned set must independently entail the complete DC:

- a singleton represents direct support;
- a multi-EC set represents joint or inferred support;
- every set must be minimal, so removing any member makes it insufficient;
- partial relevance, compatibility, plausibility, or absence of contradiction is not support.

### 6.3 LLM and canonical outputs

The LLM returns temporary IDs only:

```json
{
  "dc_claim_id": "dc_001",
  "support_sets": [
    ["ec_021"],
    ["ec_049", "ec_084"]
  ]
}
```

After validation, the script restores original IDs and writes the same two-field structure to `dc_support_sets.jsonl`.

If `candidate_ec_ids` is empty, the support script does not call the LLM and deterministically writes:

```json
{
  "dc_claim_id": "the_original_dc_id",
  "support_sets": []
}
```

## 7. Deterministic validation

Candidate-selection validation requires that:

- the response contains exactly `dc_claim_id` and `candidate_ec_ids`;
- the DC ID matches the request;
- every EC ID exists in the complete input EC set;
- no EC ID is repeated.

Support-assessment validation requires that:

- the candidate input contains exactly one valid record for each selected DC;
- every candidate EC belongs to the same generation case as its DC;
- the response contains exactly `dc_claim_id` and `support_sets`;
- every support-set member belongs to that DC's candidate set;
- no member, support set, or obvious strict superset is duplicated.

Structural validation cannot prove semantic relevance, sufficiency, or minimality. Those remain LLM judgments.

## 8. Derived outcomes

The scripts derive downstream labels deterministically:

- non-empty `support_sets`: `supported`;
- empty `support_sets`: `not_supported`;
- one-member support set: direct support;
- multi-member support set: joint or inferred support;
- an EC in any support set: supporting EC;
- a candidate EC outside every support set: relevant to assessment but not part of a sufficient support set.

## 9. Unsupported diagnosis boundary

Support assessment does not diagnose unsupported claims. A later diagnostic stage receives the unsupported DC and its candidate EC texts. This preserves partial, boundary-mismatched, or contradictory evidence that would be lost if only an empty support set were retained.

## 10. Responsibility boundary

| Component | Responsibility |
|---|---|
| Candidate-selection LLM | Select materially relevant EC IDs from the complete EC set |
| Support-assessment LLM | Identify minimal sufficient support sets from the supplied evidence claims |
| Deterministic scripts | Validate inputs and outputs, map IDs, skip empty-candidate calls, restore IDs, record manifests, and aggregate usage |
| Later diagnostic stage | Explain why a `not_supported` DC is unsupported using its candidate ECs |
