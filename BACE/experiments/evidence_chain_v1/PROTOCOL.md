# Fixed-claim evidence-chain sensitivity experiment

Designed on 2 October 2026 after the prompt-sensitivity experiment. This is an
exploratory controlled sensitivity analysis, not a preregistered accuracy study.

## Question and interpretation

For the same historical BACE DCs, how do support judgments change when one
fixed judge sees the original supplied evidence cards, the complete deduplicated
EC pool, or the DC-specific candidate ECs?

The primary contrasts are raw cards minus all ECs, and all ECs minus candidate
ECs, with raw cards minus candidate ECs reported as the combined contrast.
The first contrast bundles extraction, semantic deduplication and representation.
The second changes selection and the amount of context. Neither is a validated
evidence-loss rate. Additional context can distract a judge; richer inputs need
not produce monotonic decisions. A source-supported claim still requires
independent adjudication. No contrast allocates the native evaluator gap.

## Three conditions and a common judge

1. `raw_cards`: every prompt-visible evidence card, in its original order,
   reconstructed by the frozen baseline adapter, including the original group
   heading, source label and retrieval text. This means the supplied cards,
   not newly retrieved material or additional PDF pages.
2. `all_ec`: the complete deduplicated EC pool available before candidate
   selection, with its original EC text and case-level aliases.
3. `candidate_ec`: the original ordered candidate EC subset for the same DC.

One common prompt uses the chosen support criterion in all three conditions.
The default criterion is original BACE. The general input description changes
from atomic evidence claims to evidence units, because a raw card can contain
several propositions. The substantive support, scope and inference rules are
kept from the chosen criterion. `judge_prompt.diff` documents every adaptation.

The native BACE JSON schema, minimal sufficient support-set task, direct/inferred
definitions for the chosen criterion, parser and ID restoration are used in all
three conditions. Legacy `ec_claims`, `ec_text` and `ec_claim_ids` fields refer
to evidence units here: their original IDs identify ECs in the two EC conditions
and cards in the raw condition. Minimality is relative to supplied units; a
card is not an atomic EC. Unit granularity remains part of the representation
intervention and must not be mistaken for pure information removal.

Candidate judgments are rerun under this common prompt. Historical BACE labels
are a separate descriptive reference, not substituted for this condition.
Model ID, version, deployment, reasoning effort, message roles, request parameters,
and retry policy match the preceding native support experiment. No historical
verdict, framework name, diagnosis or evidence-lineage annotation enters a call.
Company name and target reporting year remain fixed. Each call judges one DC.

## Cohort, source checks and freezing

Use all DCs from the original complete three-framework cohort recorded in the
preceding experiment's input plan. Do not condition selection on the new prompts'
outcomes or their three failed records. Audit the complete source inventory before
freezing this experiment. Verify input hashes against support manifests, raw-card
reconstruction against the actual generation prompt and the baseline manifest,
and extracted occurrence IDs and text against the deduplication input manifest.

Save the pre-dedup occurrence lineage for review. Omitted occurrence IDs, if any,
are reported explicitly. Do not regenerate or repair extraction, deduplication,
candidate selection, target claims, source tables or original outputs.

Freeze the common prompt, schema, model settings, protocol, execution code,
source hashes, all per-case caches, complete cohort and technical-pilot selection
before the first call. No evidence truncation is permitted. An input-size or
transport failure remains visible and triggers the specified stop/gap handling.
Full-pool conditions use every EC; the original candidate-selection count ceiling
is not a license to drop ECs from this condition.

## Execution and technical gate

Select one nonempty-candidate DC per company by fixed SHA-256 ranking with seed
20261002, plus the claims with the largest raw text, full-EC text and candidate
count. These additional technical checks use input sizes, never verdicts.
Run every selected claim under all three conditions. The gate checks exact
inputs, unchanged model settings, valid references and schema/transport success.
Support rates are not a gate and cannot motivate prompt retuning.

Retain successful pilot records as the first observations in the full run.
Order remaining cases by a separate fixed hash, and hash-order the three
conditions within each DC. Use the existing shared support request gate and
at most its frozen concurrency ceiling. Record every output attempt and all
exhausted failures. Never rerun a recorded success or exhausted failure on resume.
Persistent authentication/deployment/request errors stop new scheduling. Store
all new artifacts separately under `results/evidence_chain_v1`.

## Estimands and missingness

Support means a valid nonempty support-set array. Empty evidence is deterministic
unsupported and remains in the denominator. API, output or parser failure is
missing, not unsupported. Retain every original DC, including previously supported
claims and those with empty candidate sets.

The primary cohort contains only disclosures with every DC valid in all three
conditions. Exclude an incomplete disclosure as a whole; report planned, recorded,
valid, failed and analysed counts. Compute support within each disclosure using
its fixed full DC denominator, then average disclosures with equal weight.
The primary effects are paired differences in percentage points, with 95%
percentile intervals from 2,000 company-cluster bootstrap draws, seed 20260921,
using shared resamples across conditions. Report pooled claim proportions separately.
No final primary score is reported before the scheduled run is complete.

Report both flip directions for each contrast, each original-status denominator,
all eight three-condition support patterns, company-specific effects and
leave-one-company-out influence. These intervals condition on the observed
model runs and do not estimate all model-run variance. The previous prompt repeat
control is context, not a direct variance estimate for these new inputs.

## Source review and deliverables

Integrate completed results into a separate evidence-chain section of notebook 04,
preserving the prompt experiment and earlier diagnostics. Include the common
judge adaptation, execution completeness, paired scores and effects, transitions,
company influence, source-linked cases, input-length summaries and limitations.

Prepare a blinded source-review packet sampled by fixed hash within the observed
three-condition patterns, with complete DCs, all supplied cards, pre-dedup
occurrences, full ECs and candidate memberships. Preserve empty annotation fields
and a separate analyst key. A packet is not completed human validation. Assistant
source readings must be labelled as such and cannot substitute for independent
reviewer labels. Do not contact reviewers or send unpublished material externally.

Independent review should distinguish support in supplied cards, preservation in
the EC pool, preservation in candidates, and the temporal/inference rule applied.
Higher raw-card support alone does not prove extraction loss; an increase with the
full EC pool alone does not prove candidate recall failure. No condition establishes
external truth, evaluator accuracy or regulatory compliance.
