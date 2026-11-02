# BACE support-instruction sensitivity, v1

Established 1 October 2026, before new support calls. This is an exploratory
post-main-experiment extension, not a preregistered confirmatory experiment.

## Question and conditions

With BACE targets, candidate evidence and the support-set output task fixed,
how much do changed judgment instructions change support rates and individual
decisions? Compare Original BACE, BACE–RAGAS-style and BACE–RAGChecker-style.
These adapted conditions are not native evaluator reruns. Native inventories
and rates are background only and never enter this controlled denominator.

Copy the original prompt's task, input scope, output contract and minimality
sections verbatim. Replace only support assessment and support type sections.
Both variants use the same support-type description: explicit support is direct;
support requiring a reasoning step is inferred under that condition's criterion.
The primary endpoint is a nonempty support set. The replacement omits the
original strict restrictions on recharacterization and necessary entailment;
retaining field names does not retain those substantive criteria. No capability
comparison of original/new inferred fractions is planned.

RAGAS provenance: installed ragas 0.4.3,
`ragas/metrics/collections/faithfulness/util.py`, NLIStatementPrompt.instruction.
Its criterion is whether the statement can be directly inferred from context.
RefChecker provenance: installed refchecker 0.2.13 (used by ragchecker 0.1.9),
`refchecker/checker/checker_prompts.py`, JOINT_CHECKING_PROMPT_Q.
Read both complete source passages on 1 October 2026. Their source files,
versions, locators and hashes are saved with the frozen run. No paper-level
claim of fidelity is inferred from bibliographic metadata.

## Population and fixed inputs

Inventory all 1,800 main-run planned texts and every saved deduplicated DC,
including originally supported DCs. Do not regenerate, extract, deduplicate,
select candidates or diagnose. A missing original candidate-selection stage
is an input failure, not a reason to invent candidates. Preserve all such
claims/texts in the integrity accounting and exclude incomplete texts from
the common complete analysis. No selection uses new condition outcomes.

Reconstruct jobs using the original frozen builder, verify every available
saved support-call dynamic input, alias mapping, candidate order, input hash,
message hash and final support result. Preserve DC/EC text and permanent IDs,
temporary IDs, full inventory, original prompt-visible order, company name
and target reporting year. The deterministic empty-candidate rule is unchanged:
an empty support-set list, counted in the denominator without a model call.

Retain model key, configured version, deployment name, reasoning effort,
system/user roles, API request parameters, JSON schema, response validation,
ID restoration and invalid-output/network retry policy. Use the original
support executor, not a reimplementation. Keep the native per-case eight
workers, up to sixteen concurrent cases and the shared 48-call deployment
ceiling. Conditions are interleaved within cases by a seeded hash order;
the repeat baseline is interleaved on its selected texts. Record the resolved
endpoint hash without credentials. Historical records do not expose the
resolved endpoint or an immutable provider model revision; matching the
deployment/configuration cannot prove an unchanged provider backend.

Freeze source hashes, prompts, schema, configuration and per-text job files
before any new call. Use a separate versioned directory under this folder.
Raw responses, attempts and failures are append-only. Resume skips completed
terminal jobs, including failures after the original retry budget; it does
not retry failures indefinitely or select a preferred successful decision.
Unexpected infrastructure exceptions remain explicit failures. Changing a
frozen input or prompt requires a new version, never overwriting v1.

## Stability control fixed before calls

Select two complete texts per company by the smallest SHA-256 values of
`20261001|stability|generation_case_id`. Repeat the original prompt on their
entire original claim inventories once. This is a company-stratified sample
of texts; it is not chosen by baseline support rate, diagnosis or new outcome.
Save IDs before calls. Summarize repeat-minus-original text-macro effects,
both transition directions and exact support-set agreement on complete repeat
texts. Compare new-prompt effects on the identical repeat-complete subset.
A single repeat estimates observed run-to-run disagreement; it does not
isolate all stochastic components or fully remove provider/time drift.

## Endpoints, pairing and uncertainty

For each text, support rate = supported original DCs / all original DCs.
The primary mean weights texts equally. Use texts with every original claim
valid in all three primary conditions. Recompute Original BACE on this same
cohort. Missing calls/parses remain missing, never unsupported. Report planned,
input-ready, attempted, complete, failed, pending and included texts/claims,
and deterministic empty-candidate counts. No complete-claim-only analysis is
substituted for the primary complete-text cohort.

Use 2,000 paired company-cluster bootstrap draws, seed 20260921, percentile
95% intervals, matching notebook 04. Sample companies with replacement and
keep all of each selected company's texts and all conditions together.
Estimate ratios of text-score sums to text counts: do not silently weight
companies equally. Differences and their intervals are in percentage points.
Pooled claim rates are supplementary. Undefined bootstrap denominators remain
explicit. No significance tests or multiplicity-dependent selection is planned.

For each new prompt, give a 2×2 Original/new judgment table on the common
cohort. Report accepted-to-rejected / original accepted and rejected-to-accepted
/ original rejected, plus each / all paired claims. Report company macro
effects, leave-one-company-out effects and flip-count concentration. Compare
the two new prompts' support sets of claims and their directional flip sets
with intersection, union and Jaccard (undefined for an empty union).

Select up to three cases per condition and flip direction by smallest hash
`20261001|example|condition|direction|dc_id`, allowing at most one per company
until companies are exhausted. Show complete DC, every candidate EC in order,
and all three support-set outputs with permanent and temporary ID mappings.
This is illustrative outcome-stratified sampling, not frequency evidence or
an independent correctness judgment. Do not use BACE diagnoses as labels.

## Deliverables and interpretation

Append a separate section to notebook 04 with conditions, integrity, main
three-row table, two-contrast paired effect plot, two transition matrices,
company results, overlap, repeat control, cases and provenance. Tables and
figures derive from saved calls. Retain readable HTML and PDF/SVG/PNG exports.
The effect plot answers magnitude/direction; the transition matrices answer
whether opposing flips conceal instability. Use the existing Python visual
style, 183-mm width, editable text, a 5-pt glyph floor and rendered QA.

No result proves that Original BACE is wrong, that unchanged scores imply no
evidence loss, that a percentage of the native evaluator gap is caused by
prompt, or that any condition is more accurate without independent labels.
Company bootstrap is sampling uncertainty, not repeated-model uncertainty.
Success means reproducible, paired and interpretable results, regardless of
whether support increases.
