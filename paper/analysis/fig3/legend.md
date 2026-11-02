# Figure 3 legend

**Automated diagnoses and source-linked cases.**
**a,** Counts and percentages of the 42,646 unsupported disclosure claims (DCs) across 1,798 completed disclosures. All six categories are retained in diagnostic-rule order, including non-disclosure statements. Each unsupported DC receives one mutually exclusive label. Factual boundary distortion and evidence conflation together account for 31,335 diagnoses (73.5%). These are descriptive pooled counts, with no confidence intervals or hypothesis tests; they do not estimate independently confirmed error prevalence.
**b,** The fixed Wärtsilä 2022 supplier-relationships example pairs a supplied excerpt from its 2019 Annual Report (p. 132) with the extracted DC. BACE assigned factual boundary distortion; its rationale questions whether the historical description establishes target-year use. The excerpt does not show that the practice ceased.
**c,** For the fixed ASML 2019 emissions example, two rows transcribed from the original Integrated Report 2018 glossary (printed p. 209; PDF p. 216) are juxtaposed with a selected candidate evidence claim. Electricity conversion factors belong to indirect Scope 2 in the original layout but are associated with direct Scope 1 in the extracted claim. This challenges the recorded contradiction rationale without validating the full disclosure. The original page was inspected separately from the supplied flattened card. Case excerpts are illustrative; complete selected-case evidence is retained in the source records. Neither case constitutes representative or independent human validation.

## Provenance

Prepared: 2 October 2026. Exact text is synchronized with the manuscript caption.

- `diagnosis_composition.csv` and `verified_facts.json` contain recomputed counts and denominators, classified `COMPUTED_VERIFIED`.
- `case_evidence.json` retains fixed case/DC IDs, full generated disclosures, all supplied evidence cards, original generated quotations, selected cards, all selected-DC candidate ECs, automatic judgments and original sampling records. The seeds are 20260924 for Wärtsilä and 20260922 for ASML; cases were not redrawn for the manuscript.
- `original_source_checks.json` identifies each original local report version by filename and SHA-256, with page locators and access date. The ASML PDF hash matches the saved source-layout export.
- `text_evidence.csv` retains verbatim saved passages and judgments. `displayed_text.csv` records the rendered excerpts and their roles. Typesetting changes only line wrapping and CO2-to-CO₂ typography where stated; it preserves the original glossary row association.
- `asml_original_glossary.png` is an unaltered source crop for local inspection. The manuscript uses an original typeset transcription of the two relevant rows, not the report image.

The original illustration pools required localizable generated-text quotations.
The manuscript subset was editorially chosen, and the source-layout comparison
was a targeted follow-up. These selection rules preclude treating the two cases
as a representative validation sample. The displayed EC is only one of the
recorded candidates; the complete candidate membership is retained.

No new literature citation occurrence, model call or experiment was added. The
original reports support the exact displayed passage and row relationship, not
external truth of the generated disclosures or the aggregate diagnostic labels.
