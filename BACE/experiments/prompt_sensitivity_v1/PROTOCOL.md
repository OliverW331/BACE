# BACE support-prompt sensitivity experiment, version 1

Established 2026-10-01, after the main experiment and before new model calls.
This is an exploratory controlled sensitivity experiment, not a preregistered
comparison of evaluator accuracy. The author authorized two full support-stage
reruns and the associated paired analysis.

## Objective and conditions

Hold BACE target claims, candidate evidence, context metadata, serialized input,
model settings, message roles, schema and parser fixed. Estimate how changing
the judgment instructions and criteria changes support rates and individual
decisions. The conditions are historical Original BACE, BACE–RAGAS-style and
BACE–RAGChecker-style. The latter two are adapted BACE conditions, not native
RAGAS or RAGChecker evaluations.

The two new prompts share their input, output, support-type and minimality
sections. RAGAS-style uses the native directly-inferred faithfulness criterion.
RAGChecker-style uses entailment/contradiction/neutral reasoning and prohibits
outside knowledge; only nonempty support sets versus empty sets are output.
Both permit combinations of candidate ECs. A native evidence card is not an
atomic EC: copying the native any-card rule as an any-single-EC rule would
introduce an additional evidence-combination restriction.

The original input/output/minimality sections are retained. The original
substantive scope and necessary-inference restrictions are replaced, including
restrictions previously embedded in its support-type section. Both new prompts
use a common descriptive direct/inferred distinction. The primary endpoint is
binary support; new versus original inferred-label proportions do not identify
reasoning ability or a common strict-inference construct. Prompt length and
criterion specificity are part of this bundled instruction intervention.

## Frozen cohort and replay

Use every claim from the existing complete three-framework snapshot cohort.
Before execution, rebuild each original support job using the frozen native
builder, verify upstream files against the original run manifest, compare its
dynamic input and call identity with saved successful calls, and reconcile its
original restored support sets with both saved results and the snapshot.
Save source hashes, original support sets and exact jobs in a separate input
cache. Replay the native support executor and output validator without edits.
No generation, extraction, deduplication, selection or diagnosis is rerun.
No original labels or diagnoses enter the LLM input.

Zero-candidate jobs remain deterministic unsupported in all conditions and
remain in denominators. Runtime/API/parse failures remain missing. Do not
select claims based on the original verdict. New raw calls and parsed outputs
are saved under `BACE/results/prompt_sensitivity_v1/`, never in main_v1.

## Repeat control and order

Before inspecting new outputs, select two complete disclosures per company by
SHA-256 ranking of `20261001|repeat|generation_case_id`. Rerun the original
prompt on all claims in these 60 disclosures once, without using historical
cached responses. This is a limited historical-to-current repeat control,
not a replicated estimate of all model-run variance or a third full condition.

Select one nonempty job per company, inside the repeat sample, by SHA-256 rank
for a 30-job technical pilot. Run both new prompts and the original-repeat
condition on these jobs. Evaluate only input/schema/transport integrity for the
pilot gate, never whether scores increased. Successful pilot calls remain the
first observations for those jobs in the final run. Do not choose a preferred
response among successful attempts or retune prompts after observing scores.

Rank remaining cases by a separate SHA-256 ordering and alternate the two
new conditions within each job; interleave the repeat condition where selected.
Use the frozen support stage's shared deployment request gate and per-request
retry policy. A bounded orchestration pool may use up to the existing 48-call
shared ceiling. Concurrency does not change model request parameters. Persistent
authentication, deployment or transport failures stop scheduling new requests.
Successful calls are durable and never rerun on resume. Exhausted per-job
failures remain visible; any later recovery pass must be explicitly logged.

## Estimands and missingness

The main cohort contains disclosures for which all planned claims have valid
results in historical BACE and both full new conditions. Recompute the original
mean on that same cohort. For each disclosure, divide supported DCs by all its
fixed DCs, including deterministic empty-candidate DCs. Average disclosures
with equal weight. The two primary contrasts are paired new-minus-original
differences in percentage points. Report 95% percentile intervals from 2,000
company-cluster bootstrap draws with seed 20260921, using identical resamples
across conditions. Do not treat claims as independent replicates. Report
claim-pooled estimates separately. No p-values or significance stars are planned.

Report planned, attempted, valid, failed and pending counts by condition, as
well as complete and incomplete disclosures. No final primary estimate is
presented while a scheduled run is still active. Never convert failures to
unsupported or silently drop failed claims within a disclosure.

Report each 2x2 transition count, pooled fractions of all paired claims, and
directional flip rates conditional on original support or non-support. A
disclosure-macro net change is not the pooled net flip fraction. Supplement
with company-specific paired changes, leave-one-company-out influence, overlap
of both variants' flip sets and flip directions. Undefined rates remain missing.

For the repeat sample, report original-repeat minus historical BACE on matched
complete disclosures and both flip directions, alongside the two new conditions
on that same subset. Resampling intervals are conditional on observed runs;
neither bootstrap nor one repeat establishes comprehensive model stability.

Select up to three examples per variant and flip direction using a fixed hash
ranking, preferring distinct companies before additional records. Export full
DC text, all candidate EC texts and original plus both new support sets.
Selection is illustrative, not human validation or error prevalence. Do not
use original BACE diagnoses as ground truth.

## Deliverables and acceptance

Extend notebook 04 with condition definitions, execution completeness, the
three-condition main table, two-contrast effect plot, paired transition plots,
company and overlap summaries, repeat-control results and source-linked cases.
The notebook only reads saved calls; it never initiates API requests. Export
source CSV, SVG, PDF and 600-dpi PNG with uncertainty, units and denominators.
Keep the existing four notebooks, shared snapshot, scientific freeze and both
project environments unchanged. Preserve notebook 04's earlier diagnostic data.

Freeze prompts, schema, model configuration, replay code, source-package prompt
files, input-cache hashes, cohort and selections before the pilot. Record later
execution-code corrections as deviations; never rewrite a frozen prompt to
obtain a desired rate. Final verification covers all planned jobs, source
integrity, parser behavior, paired arithmetic, missingness, reproducibility,
notebook execution and visual inspection.

Higher support does not establish that original BACE was wrong. Unchanged
support does not rule out evidence loss. These contrasts do not causally
allocate the native evaluator gap or establish accuracy, external truth or
compliance. Independent source and judgment validation remain pending.
