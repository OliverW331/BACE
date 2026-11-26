# BACE derived-data release (release_v1)

Derived data for *Evidence-grounded reliability of AI-generated sustainability disclosures* (main run `bace_30x5x12_v1`). The tables were exported from the saved run outputs by `BACE/analysis/release_v1/export_release.py`. `manifest.json` records the row counts, columns and SHA-256 checksums.

All tables are gzip-compressed UTF-8 CSV. Multi-valued fields are joined with `;`. `generation_case_id` identifies one disclosure, defined by company, target reporting year and disclosure task. `dc_id` and `ec_id` are unique within a disclosure.

| File | Rows | Content |
|---|---:|---|
| `generated_disclosures.csv.gz` | 1,800 | Generated disclosure text and generation metadata, one row per case |
| `disclosure_claims.csv.gz` | 94,955 | Deduplicated disclosure claims (DCs) from the 1,798 disclosures that completed BACE, with the BACE label |
| `evidence_claims.csv.gz` | 224,611 | Deduplicated evidence claims (ECs) |
| `support_sets.csv.gz` | 117,509 | Accepted support sets, one row per set |
| `diagnoses.csv.gz` | 42,646 | Primary diagnosis and rationale for each unsupported DC |

## Columns

**generated_disclosures**
- Case: `company_id`, `company_name`, `target_reporting_year`, `task_id`, `task_title`.
- Output: `generated_text` and its `generated_text_sha256`, `generated_word_count`, `length_within_requested_range`, `generation_status`, `retry_attempts`.
- Model: `model`, `configured_model_version`, `deployment_name`, `reasoning_effort`, `max_output_tokens`.
- Sampling: no temperature was sent. `returned_temperature` and `returned_top_p` are the values the service returned with each response.
- Response: `service_tier`, `provider_response_id`, `created_at_utc`, token usage.
- Evidence: `evidence_card_count`, the number of evidence cards supplied to the generator.

**disclosure_claims**
- `dc_text`.
- `bace_label`: `direct` or `inferred` if at least one support set was accepted (`direct` when any accepted set is direct); otherwise the primary diagnosis of the unsupported DC.
- `grounding_status`: whether the claim text was located in the generated disclosure.

**evidence_claims**
- `ec_text` and `evidence_card_ids`.
- Provenance of the cards: `evidence_types`, `source_files`, `document_types`, `source_years`, `pages`, `metrics`.
- `grounding_status`: whether the claim was located in the evidence card.

**support_sets**
- `dc_id`, `support_set_index`, `support_type` (`direct` or `inferred`), `set_size`, and `ec_ids` (the ECs in the set; they refer to `evidence_claims` of the same `generation_case_id`).

**diagnoses**
- `dc_id`, `primary_diagnosis` and `rationale`.

The disclosure support rate and Evidence Claim Coverage Ratio of each disclosure can be recomputed from these tables. `disclosure_claims` gives the share of DCs labelled `direct` or `inferred`. `support_sets` and `evidence_claims` give the distinct ECs in accepted support sets divided by all ECs. The recomputed values match `snapshot/metrics.csv` for all 1,798 disclosures.

## Not included

The annual and sustainability reports and the structured ESG indicators come from the Corporate Sustainability Tracker (https://github.com/forsterkerstin/corporate-sustainability-tracker) and are not redistributed. The release therefore leaves out:
- evidence-card text;
- prompts;
- the source quotes used to ground each EC;
- raw model-call records.

Evidence cards are identified by source file, page and chunk identifiers, so they can be reconstructed from the source reports. Local file paths and encrypted reasoning content have also been removed.

## Licence

CC BY 4.0 (see `DATA_LICENSE.md` in the repository).
