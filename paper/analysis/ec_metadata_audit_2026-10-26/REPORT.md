# ESRS metadata in evidence claims: forensic audit

Audit date: 26 October 2026. Scope: the saved `main_v1` study, its current source code and prompts, canonical CSV evidence, and the current private human-review manifest. This is a read-only pipeline audit, not a new experiment or a manuscript revision.

## Finding

The phrases originate in a data-to-text boundary failure. The CSV card builder places dataset taxonomy fields in `retrieval_text`; the generation renderer presents that entire string as evidence `Text`; direct EC extraction sometimes rewrites the taxonomy as a qualifier on the measurement. The selected review stages preserve those qualifiers, deduplication copies a representative claim, and downstream scoring and human-review materials consume the resulting text.

There is no separate S1/G1 requirement instructing the extractor to append these words. E1 has the same behavior, including the directly parallel phrase `under ESRS E1 disclosure requirement E1-6`. The main problem is inconsistent treatment of metadata as substantive claim content. A dataset's classification of a metric does not establish that the company reported it under that standard or complied with that requirement.

## Verified origin and propagation

1. **Metric values and taxonomy enter through different sources.** `data/processed/results/esg_indicators_postprocessed.csv` contains company, year, indicator description, extracted model output, final value and unit. `data/raw/datasets/indicator_metadata.csv` separately supplies `topic`, `standard` and `discl_req`. [prepare_evidence.py](/home/muwang/master_thesis/BACE/script/prepare_evidence.py:30) joins the metadata on `data_point_id`. The three traced E1/S1/G1 metric rows contain no ESRS tail in their indicator description or saved numeric model output.

2. **The deterministic card builder embeds the taxonomy in prose.** [csv_2_evidence.py](/home/muwang/master_thesis/BACE/script/data_2_evidence/csv_2_evidence.py:596) constructs:

   ```text
   Company: ... Reporting year: ... ESG topic: ...
   ESRS standard: ... Disclosure requirement: ... Indicator: ... Value: ...
   ```

   The structured fields also remain on the card. The current and archived `construct_retrieval_text` functions are identical by AST comparison, so this behavior was inherited from the previous pipeline stage. Git's current checkpoint does not establish who requested the original design or why; no user authorization to add EC tails can be inferred from it.

3. **Retrieval text becomes claim-source text without separation.** [build_w2_generation_inputs.py](/home/muwang/master_thesis/BACE/script/rag/build_w2_generation_inputs.py:475) copies `retrieval_text` directly under `Text:` and into `prompt_evidence`. Every one of the 18,000 CSV card presentations in the 1,800 saved generation inputs contains ESRS metadata, and every presentation matches its canonical CSV card text exactly. The same evidence text is visible to generation.

4. **The EC extractor receives that entire evidence section.** [generation_claims.py](/home/muwang/master_thesis/BACE/script/evaluation/generation_claims.py:429) supplies the exact prompt-visible evidence section plus company, target year and task title. Extraction is performed separately per case. It does not impose one canonical EC rendering per source card across tasks.

5. **The model produces the tail in direct extraction.** Saved native `raw_output`, parsed direct output and compiled occurrences agree for all three traced examples. [generation_claims.py](/home/muwang/master_thesis/BACE/script/evaluation/generation_claims.py:989) copies `claim_text` from the model; it does not append an ESRS string in Python.

6. **Review does not remove it.** For each traced card, both integrated review and atomicity review returned `edits: []`, `additions: []`, and `exclusion_update: null`. Their compiled claims therefore retain the exact direct-extraction wording. This is preservation by empty patches, not proof that either model independently revalidated the ESRS qualifier. At the broader reference-flag level, no later stage introduces a newly flagged case/evidence-card pair; the flags already occur in direct extraction.

7. **Deduplication and export preserve the result.** [run_generation_claim_semantic_dedup.py](/home/muwang/master_thesis/BACE/script/evaluation/run_generation_claim_semantic_dedup.py:814) assigns a selected occurrence's `claim_text` to `ec_text`. The current review manifest contains 4,873 EC presentations across 600 review units. Every EC text exactly matches a saved final EC in its case; there are zero text mismatches. Seven review units contain the user's exact S1/G1 phrases, with 31 EC presentations counted case-sensitively. The source of these words is upstream of export.

## Why the prompts and checks permit this

The direct prompt's [tracker rule](/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_ec_claim_extraction_prompt_v8.txt:76) says to retain company, reporting year, indicator, value and unit. It does not request an ESRS suffix. However, it does not explicitly identify the builder's inline taxonomy fields as retrieval metadata that must stay outside the measurement proposition.

Other instructions pull toward retaining qualifiers: the prompt requires self-contained claims and material context, its Standard X example repeats an explicitly asserted reporting standard in each child, and its classification example admits company issue classifications as substantive claims. Those rules are reasonable for actual source assertions, but they do not distinguish a corporate classification assertion from a dataset's externally supplied indexing label. Their contribution to the model's choice is an interpretation of the prompt, not access to the model's internal reasoning.

The review definition states that bare taxonomy labels belong in exclusions. That rule does not clearly address a taxonomy label already embedded as a qualifier in an admitted numerical claim. The atomicity stage is expressly constrained to splitting existing claims and retaining their governing context. It is consequently a poor place to expect this admission/fidelity defect to be repaired.

The direct configuration also uses `output_validation.mode = schema_only`; [the runner](/home/muwang/master_thesis/BACE/script/evaluation/run_generation_claim_extraction.py:513) accepts parsed output without the strict source-quote validator. Even an exact quote check would not resolve this problem: the synthetic evidence `Text` already contains the taxonomy. An exact match to that text establishes quotation location, not that the company asserted the regulatory qualifier.

## E1, S1 and G1: measured extent

The inventory includes 1,800 direct-extraction files, 1,799 integrated files, and 1,798 atomic/final files. Two cases lack completed BACE outputs; missing stages remain missing and are not counted as zero claims. Final counts below use 224,611 saved deduplicated ECs from the 1,798 completed final inventories. Repeated use of a source card across cases counts as distinct case-level ECs, not independent source observations.

Case-insensitive phrase matching gives:

| Phrase in final EC text | EC count |
| --- | ---: |
| `under ESRS E1 disclosure requirement E1-...` | 1,177 |
| `under ESRS S1 disclosure requirement S1-14` | 588 |
| `under ESRS G1 disclosure requirement G1-6` | 58 |

The census also finds 10,627 of 18,203 CSV-derived final ECs containing a broader ESRS/disclosure-reference flag. The broader screen includes standard names inside literal indicator descriptions and is **not a count of adjudicated extraction errors**. Another 23 PDF-derived ECs match that screen; they include genuine source statements about disclosure requirements and must not be treated as artificial tails merely because they match.

Among 6,823 CSV evidence IDs represented in final ECs, 2,104 have both a flagged and an unflagged claim somewhere in their case-level outputs. This is a wording-variation screen rather than a semantic error count. A directly checked example uses the identical Air France-KLM 2017 employee-fatality card:

```text
S1-14 task:
For reporting year 2017, Air France-KLM reported a value of 0.0 for the
number of fatalities among employees in its own workforce as a result
of work-related injuries and work-related ill health.

S1-4 task:
For reporting year 2017, the Corporate Sustainability Tracker recorded
0.0 employee fatalities in Air France-KLM's own workforce as a result
of work-related injuries and work-related ill health under ESRS S1
disclosure requirement S1-14.
```

Thus the distinction is not an E-only versus S/G-only extraction convention. It can change between tasks even for the same source card and measurement.

## Why G1-6 appears in a G1-2 task

The source indicator for Intertek's payment-term percentage is classified as `G1-6` in the dataset metadata. The generation task is `G1-2_supplier_relationships`. These are different fields with different roles.

[Candidate-pool validation](/home/muwang/master_thesis/BACE/script/rag/run_w2_retrieval_sanity_check.py:947) constrains company, source year and evidence type; it does not require the card's disclosure-requirement code to equal the task code. Semantic retrieval can select payment-practice evidence for a supplier-relationship task. The EC prompt then explicitly preserves off-topic assertions as written. Cross-task evidence availability explains why a G1-6-labelled card can be present; it does not justify turning that label into an assertion that Intertek reported under G1-6.

## Concrete source trace

For Intertek 2015, indicator `0549c0a0-5322-4545-9d6b-01aaac7e06c7`:

```text
Processed source row:
data_point_description = Percentage of payments aligned with standard payment terms
model_output = {'value': 42.7, 'unit': '%'}
value_final = 42.7
unit_final = percent

Separate metadata row:
standard = G1
discl_req = G1-6

Built evidence Text:
Company: Intertek. Reporting year: 2015. ESG topic: gov. ESRS standard: G1.
Disclosure requirement: G1-6. Indicator: Percentage of payments aligned
with standard payment terms. Value: 42.7 percent.

Direct model output, preserved through final EC:
For reporting year 2015, Intertek reported that 42.7 percent of payments
were aligned with standard payment terms under ESRS G1 disclosure
requirement G1-6.
```

The direct call started on 17 September 2026 at 19:27:34 UTC. The saved numerical source output contains no assertion about reporting under G1-6. That qualifier is traceable to the metadata-to-prose conversion. Comparable native-response traces for Air France-KLM's 2017 E1-6 emissions metric and Mowi's 2020 S1-14 fatality metric are saved in `trace_results.json`.

## Downstream implications and limits

Among all broadly flagged final ECs, 8,986 are selected as candidates and 5,207 occur in at least one accepted support set. There are 6,905 DC records whose support sets use at least one flagged EC. These figures establish downstream exposure, not a causal effect of the ESRS words on a verdict. No counterfactual extraction, generation or scoring run was performed, and no score correction can be inferred from these counts.

Potential consequences are changed claim scope, inconsistent deduplication or candidate selection, and evidence that appears to support an unestablished reporting-standard assertion. Some tails merely repeat dataset classification and may not affect a particular support decision. Each affected decision would need a versioned comparison to establish its effect.

## Recommended correction boundary

The intended EC convention should separate the measurement proposition from the dataset's classification. For the traced Intertek record, an appropriate proposed rendering is:

> For reporting year 2015, the Corporate Sustainability Tracker records that 42.7 percent of Intertek's payments were aligned with standard payment terms.

Retain `standard = G1` and `discl_req = G1-6` as source metadata. This example preserves the dataset-level attribution and does not independently validate the underlying measurement.

Recommended implementation work, **not performed by this audit**:

1. Define a typed boundary between retrieval metadata and assertable evidence content. Keep taxonomy useful for retrieval without silently treating it as a company assertion.
2. Specify the same rule for E/S/G extraction and integrated review: do not synthesize regulatory-reporting, compliance or classification assertions from dataset labels. Preserve an actual source assertion about a reporting standard when the source makes it. Company, measurement period, metric, population, value, unit and material boundaries must remain intact.
3. Add targeted regression checks for a metadata-only ESRS label, a genuine source statement about a standard, identical cards under different tasks, and taxonomy appearing inside a metric description. A blanket deletion of every ESRS phrase would damage legitimate claims.
4. Version corrected extraction and downstream evaluation separately. If only the EC extraction contract changes, recompute affected BACE stages against the retained generation inputs. If prompt-visible evidence text changes, generation and other evaluators also require a separately versioned comparison. Do not overwrite frozen ECs, scores or human-review inputs or present display-only edits as original model inputs.

## Reproduction and integrity

```bash
python paper/analysis/ec_metadata_audit_2026-10-26/audit.py
python paper/analysis/ec_metadata_audit_2026-10-26/trace.py
```

Both scripts use Python's standard library, read saved artifacts, and write only into this audit directory. No project credentials, model API, package installation, prompt edit, frozen-artifact rewrite or new experiment is involved.

- `summary.json`: cohorts, denominators, stage counts, missing files and broad-pattern definition.
- `flagged_final_ec.csv`: case/EC/evidence IDs and the exact final text for every broad match.
- `case_counts.csv` and `same_card_variation.csv`: per-case counts and source-card wording variation.
- `trace_results.json`: narrow phrase counts, three full source/model/review traces, review-export comparisons and receipt checks.
- `input_manifest.json` and `trace_input_manifest.json`: read-input SHA-256 hashes and script hashes.

Of 10,791 census-stage files checked against execution receipts, 10,789 match a completed-stage receipt exactly. Banco BPM 2019 S1-5 has an integrated-extraction file without a completed integrated-stage receipt; Investec 2023 S1-1 has a direct-extraction file without a completed direct-stage receipt. These partial saved files are included only in the corresponding file-inventory counts, not treated as completed final cases. There are zero mismatched receipt hashes. The audit does not independently validate all Corporate Sustainability Tracker measurements against original company PDFs, establish legal compliance, or establish evaluator accuracy.
