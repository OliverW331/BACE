# Sampled fixed-claim evidence-chain sensitivity

This exploratory amendment was requested by the author on 2 October 2026 to
reduce runtime and token use. The preceding full-cohort run was interrupted;
its journals are retained and must not be presented as a completed experiment.
The author selected 90 disclosures before this sampled run was launched.

## Selection and reuse

The sampling frame is the frozen 1,798-disclosure, 30-company cohort in
`../evidence_chain_v1/plan.json`. Partition it into company by E/S/G topic
strata using the first character of the task code. Select one complete
disclosure from each of the 90 strata by ascending SHA-256 of
`20261002|sample_case|<generation_case_id>`. Keep all of its original DCs,
including supported DCs and empty-candidate DCs. No verdict, disagreement,
completion status, input size or claim count enters this ranking. The seed
and sample size are not tuned to observed results. Years and individual tasks
are sampled within strata, not exhaustively covered.

The selection ledger records every frame member, stratum size, rank,
inclusion probability and selected status. Reuse every already journalled
record for the selected disclosures, including any exhausted failures, verbatim.
Verify the original job, rendered messages, settings, model and parser. The
reuse ledger records source file, line, and exact record hash. Other existing
records remain outside the primary analysis; they are not added to enlarge
the sample. Previously submitted calls without saved outputs are unavailable
and may already have consumed tokens. No recorded result is retried.

This is an amendment after a full run began, not a preregistered design. Prior
technical results and aggregate run counts were known. New selection uses
metadata only, independently of response values. Preserve the original stop
audit and freeze this amendment, selection and journals before new calls.

## Fixed intervention

The original evidence-chain protocol's three conditions and common BACE
criterion apply unchanged: original prompt-visible raw cards, all deduplicated
ECs, and the original candidate ECs. Keep DCs, prompt bytes/version, native
schema/parser, minimal sufficient support sets, model/version, deployment,
reasoning effort, request parameters and retry policy unchanged. There is no
new retrieval, extraction, deduplication, candidate selection or truncation.
Historical BACE is a descriptive bridge, not the current candidate condition.

Reuse the preceding successful 33-DC/99-record technical pilot as a transport
and schema gate; do not repeat it or include out-of-sample pilot DCs in the
primary cohort. Perform offline checks for the sampled cases and reused records.
Use the shared native support gate, with at most 48 workers. Resume only after
checking process identity. The amended runner drains and journals active
requests after SIGTERM/SIGINT, then stops without scheduling further requests.

## Estimands and uncertainty

The primary outcome is support (a valid nonempty support-set array). Empty
candidate evidence is deterministic unsupported. Exhausted API/output failures
are missing. Analyse only disclosures for which all original DCs are valid in
all three conditions; report exclusions and their company-topic strata.

Average DC support within each complete disclosure, then average disclosures
with equal weight. The planned sample balances the 90 company-topic strata;
this is a sampled-cohort mean, not the full-cohort measured support rate.
Report raw-minus-all-EC, all-EC-minus-candidate and raw-minus-candidate paired
differences, both flip directions, all eight support patterns, company effects,
leave-one-company-out influence and historical-reference differences. Report
pooled claim proportions separately. No final primary estimates before completion.

Use shared 2,000-draw company-cluster percentile bootstrap intervals, seed
20260921. These describe resampling of the observed company bundles and
condition on observed model outputs. They do not estimate model-run variance
or provide an exact finite-population sampling interval for all 1,798 texts.
With one sampled disclosure per stratum, within-stratum sampling variance is
not separately estimable. Do not claim a prespecified precision or power.

As a descriptive sensitivity, report the inverse-inclusion-weighted mean,
using stratum size as each sampled disclosure's weight. This standardizes the
observed stratum means to the frame's company-topic composition. If any
stratum is excluded, normalize over represented frame strata and report the
unrepresented frame count; do not call it an estimate covering the full frame.
The primary result remains the equal-disclosure sampled-cohort comparison.

## Interpretation and deliverables

Raw-to-all-EC changes bundle extraction, deduplication and representation;
all-EC-to-candidate changes selection and context quantity. Neither difference
is a validated evidence-loss rate. Increased support is not established accuracy,
external truth or compliance, and does not allocate the native evaluator gap.
Prepare source-linked, verdict-blinded review materials with empty reviewer
labels. Their preparation does not establish independent human validation.

Write sampled outputs separately under `results/evidence_chain_sample_v1` and
`analysis/outputs/evaluator_gap/evidence_chain_sample`. After completion and
audits, integrate this amendment and its findings into notebook 04 while keeping
the preceding completed prompt experiment. The original full evidence-chain
run remains visibly interrupted. The author will monitor the run; no recurring
chat notifications or automatic sample expansion are requested.
