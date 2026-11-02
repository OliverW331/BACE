# Statistical design for evidence loss and evaluator disagreement

Prepared: 30 September 2026.
Status: proposed post-experiment exploratory analyses, `COMPUTATION_PENDING`
unless a result is explicitly linked to the existing descriptive outputs.
No additional model runs, human review, or statistical tests were performed
to prepare this plan. The native main experiment remains unchanged.

## Questions and identification

Two questions require different observations:

1. How often does BACE reject a target that is supported by the complete
   prompt-visible evidence, and where does the representation cease to
   preserve sufficient evidence?
2. How do target-claim construction and support rules affect assessments
   when evidence, target meaning, or the decision procedure are held fixed?

An association between claim count, candidate count, and score cannot by
itself identify either mechanism. Native scores do not supply a reference
label for evidence sufficiency. The existing matched-text results establish
disagreement but do not identify which method is correct.

The primary evidence boundary is the actual prompt-visible cards. A complete
source PDF may diagnose card-preparation loss in a separate audit; it must not
be silently substituted for what the generator and comparators received.

## 1. Paired evidence-representation audit

### Measurements

Sample target claims and assess each against successive evidence conditions:

| Variable | Evidence condition / outcome |
| --- | --- |
| R | Complete original prompt-visible evidence cards |
| E0, optional | Extracted ECs before semantic deduplication |
| E | Complete deduplicated EC inventory |
| C | Candidate ECs supplied to the support stage |
| B | Saved binary BACE support decision |

For each evidence condition X, let H_X be an independent reference judgment
of whether that condition establishes the complete target assertion. Direct
and permitted inferred support both count as supported. Record unresolved
judgments separately; do not force ambiguity into unsupported.

Review target fidelity against the full generated passage before attributing
a failure to evidence processing. Assess the target as written and retain a
separate flag for invented, omitted, or altered qualifiers. A source-support
score on BACE's extracted targets alone does not validate its representation
of the original disclosure.

Evidence sufficiency judgments need a source locator or sufficient premise
set. Positive/negative labels alone cannot establish which material premise
was lost. Check each identified premise against the corresponding earlier and
later representation. To distinguish extraction from deduplication loss,
include E0; comparing R with E combines those stages.

### Primary estimands

Use design weights w_i = 1 / pi_i for sampled claims, where pi_i is their
inclusion probability. All expressions refer to the defined analyzed population
and must report numerator, denominator, unresolved cases, and selection rules.

**Fraction of BACE rejections that full-source review supports:**

q = sum_i w_i 1(B_i = 0, H_Ri = 1) / sum_i w_i 1(B_i = 0).

This directly answers how much of the unsupported output fails to survive
full-source review. It is a false-omission proportion, not the false-negative
rate. The latter conditions on H_R = 1:

FNR = sum_i w_i 1(B_i = 0, H_Ri = 1) / sum_i w_i 1(H_Ri = 1).

**Loss of sufficient support between successive representations:**

L_RE = sum_i w_i 1(H_Ri = 1, H_Ei = 0) / sum_i w_i 1(H_Ri = 1).

L_EC = sum_i w_i 1(H_Ei = 1, H_Ci = 0) / sum_i w_i 1(H_Ei = 1).

**Saved rejection despite sufficient candidate evidence:**

J_C = sum_i w_i 1(H_Ci = 1, B_i = 0) / sum_i w_i 1(H_Ci = 1).

These rates have different denominators and must not be summed. Report both
directions of every transition, including apparent support introduced by
extraction. Do not enforce monotonicity: extraction may distort evidence,
evidence may conflict, and reviewers may disagree. Investigate unusual
transitions against the underlying premises before assigning a mechanism.

For the population of BACE rejections, a separate weighted cross-tabulation
of H_R, H_E and H_C shows observed pathways on a common denominator. A
first-failure label can be used descriptively when the evidence supports it,
but it is not an additive causal decomposition of the native score gap.

### Link to the reported disclosure-macro score

Let D be the number of paired disclosures and n_d the number of BACE target
claims in disclosure d. A full-source reference shift on that fixed inventory
would be:

Delta_R = (1/D) sum_d (1/n_d) sum_i_in_d (H_Ri - B_i).

This gives each disclosure equal weight, matching the main BACE score.
It is distinct from averaging sampled claims without weights.

With probability-sampled claims and known full-inventory n_d, an unbiased
Horvitz–Thompson estimator for the finite-cohort difference is:

Delta_R_hat = (1/D) sum_i_in_sample (H_Ri - B_i) / (pi_i n_d(i)).

This requires positive inclusion probability for every relevant claim and
resolved reference outcomes or explicit treatment of missing labels. A
rejection-only sample cannot estimate the net difference. Separately report
the positive contribution from rejected-but-supported claims and the negative
contribution from accepted-but-unsupported claims. This is a reference-based
reassessment of BACE's own inventory, not a neutral full-disclosure score or
a correction of comparator scores.

For unresolved reference outcomes, report their weighted share and worst-case
reference-label bounds, with any missingness assumptions explicit. Do not
treat a complete-case estimate as automatically representative.

### Inference and review design

Estimate paired transition proportions and differences with uncertainty that
respects the sampling design and clustering within company and disclosure.
For inference across the sampled company population, use a company-cluster
bootstrap preserving paired records and sampling weights, with sensitivity
to individual companies. If inference is restricted to the observed finite
cohort, use design-based variance reflecting the actual claim/disclosure
sampling scheme. State which target is intended; the two intervals answer
different questions.

Specify the replicate scheme, seed, draws and interval definition before
calculation. With only the observed company clusters available, inspect
sparsity and unstable replicate denominators. Do not rely on a standard
independent-claim McNemar test. McNemar's paired logic can describe discordance,
but its ordinary variance assumptions do not account for this clustering and
unequal sampling.

Keep initial reference judgments blind to native labels and method identities.
Use separate or counterbalanced evidence-condition reviews to limit carryover.
Preserve pre-adjudication agreement and unresolved decisions. Multiple human
judgments do not multiply the number of independent claims.

## 2. Controlled evidence-condition reassessment

This optional experiment estimates how the automated decision changes when
its available evidence representation changes. Hold each target, judge model,
decision rule, transport settings and output contract fixed. Compare C, E and
R; include E0 when the deduplication question matters.

The original BACE support interface expects ECs. A raw-card condition requires
an explicit compatible wrapper or a common decision interface across all
conditions. Document formatting changes and verify that no evidence is
truncated. These are additional controlled conditions, not unchanged native
BACE results. Score shifts combine consequences of information, presentation,
length and model response; a raw-card condition cannot isolate information
loss merely by returning a higher score.

Primary outputs are paired support-rate shifts, both directions of verdict
change, and agreement with the independently defined full-source reference.
A shift from unsupported to supported is only a recovered correct judgment
when reference evidence supports it. If resources permit repeated model calls,
pair runs and record run variability separately from claim/company uncertainty.

This reassessment is useful when broad coverage is needed, but an automated
judge cannot serve as its own independent proof that a recovered answer is
correct.

## 3. Claim construction and common-proposition comparison

### Establish a neutral target inventory

Use probability-sampled generated passages to build a method-independent
inventory of substantive assertions and their material qualifiers. Reviewers
should not begin by assuming BACE captured every assertion. Map all three
native inventories to this inventory, retaining splits, merges, repeated
representations, omissions and added qualifiers.

Report proposition coverage, extraction fidelity, and judgment on comparable
propositions separately. Fewer claims alone neither establish missed content
nor explain a higher support rate. Coverage must be measured against assertions
in the generated passage, not all facts in the evidence corpus.

A native unsupported conjunction cannot be copied as an unsupported label
for every constituent proposition. Where splits/merges prevent a faithful
mapping, retain the composite unit, mark the comparison unresolved, or use
an explicitly additional common-target evaluation.

### Comparisons that separate operational factors

| Comparison | Held fixed | Varied | Interpretation |
| --- | --- | --- | --- |
| Inventory comparison | Evidence and common judgment procedure/rubric | Native target inventories | Operational consequence of claim selection, wording and granularity under that procedure |
| Judgment comparison | Same target propositions and same evidence | Framework-adapted judgment procedures | Procedure differences after removing those inventory/evidence differences |
| Native comparison | Generated disclosures and initial evidence | Complete native methods | Total observed method difference; existing main result |

Both controlled comparisons change some native interfaces. Report them as
additional conditions, with no claim that the altered score is the published
framework's native faithfulness. If evidence differs between judgment arms,
the contrast remains a combined evidence-and-judgment difference.

### Optional crossed design

For one comparator, let S(I, J) be the disclosure-macro support score for
inventory I under judgment procedure J, with a common evidence condition and
explicit compatible interfaces. Run both inventories under both procedures.
Paired contrasts estimate an inventory effect under each procedure and a
procedure effect under each inventory. Their interaction is:

[S(I_B, J_B) - S(I_B, J_R)] - [S(I_R, J_B) - S(I_R, J_R)].

A nonzero interaction means that an attribution to inventory depends on the
judgment procedure. Two sequential paths give different decompositions; do
not present one arbitrary path as a unique causal allocation. These contrasts
describe the controlled conditions and need not reproduce the original
35-point native gap, especially if its evidence processing has been changed.

Use paired case estimates, design weights where required, and company-aware
uncertainty. Report rates and percentage-point differences rather than only
odds ratios or p-values. No assumption of interchangeable native claim
denominators is required to describe the controlled macro contrast, but it
still does not establish evaluator accuracy.

## 4. Temporal boundaries and permissible-inference sensitivity

### Independent characterization

Annotate whether each target requires a temporal carry-forward assumption,
the actual claimed period, the period supported by relevant premises, and
whether the proposition is a state, policy, event, plan or measurement. Keep
report year, publication year and measurement year separate. A policy
mentioned in an older report is not automatically a statement about only
that year. A historical claim explicitly written as historical does not
require carry-forward merely because the disclosure's target year is later.

Use the relevant source for each proposition, not the oldest/newest card in
the entire prompt. When no relevant source is identified, retain the source
age as undefined. Do not derive temporal-risk labels only from BACE diagnoses:
that would make a test of BACE's temporal behavior circular.

### Paired descriptive interaction

For a shared target, define d_i = Y_Bi - Y_Ri and T_i as independently labelled
need for a carry-forward assumption. Estimate:

Delta_T = E(d_i | T_i = 1) - E(d_i | T_i = 0).

Use the sampling weights and company-aware paired uncertainty. Report the
two group differences and their interaction in percentage points. A larger
negative value means the BACE–comparator gap is greater on temporal-extension
targets; it does not prove BACE's judgment is right or identify a causal
effect of evidence age.

For sufficient sample size and outcome variation, a secondary mixed logistic
model or marginal model can include evaluator, temporal requirement, their
interaction, task and proposition type. Account for repeated evaluations of
the same claim and nesting within disclosure and company, using justified
random effects or suitable cluster-aware inference. Report standardized
probability contrasts. Sparse cells, near-perfect support rates and few
clusters require diagnostics and may favor the simpler paired summaries.

### Explicit rule sensitivity

Define plausible support policies before examining results, for example:

- A strict policy requiring evidence of the material asserted period/status.
- A separate policy allowing specified continuity assumptions for continuing
  policies, with those assumptions disclosed and exceptions defined.

Use the same claims and evidence to assess how reference judgments and
method-reference agreement change under each policy. Relaxed assumptions
change what "support" means; they do not show that every newly accepted claim
was previously a factual error by BACE. Do not relax numerical units,
population identities or completed-event status merely to close the gap.

If model prompts are changed to implement the policies, treat them as new
experimental conditions. Repeated judges and human reviewers need order and
anchoring controls. Predefine primary interactions and sensitivity families;
label exploratory contrasts and address multiplicity if conducting formal
tests.

## Practical minimum and current data limits

The highest-priority addition is a paired source/EC/candidate audit with
independent reference judgments. It directly measures the proposed evidence
loss without rerunning the full experiment. A common-proposition review on
the same sampled passages then addresses native inventory differences.
Temporal labels can be recorded in that review and used for prespecified
exploratory subgroup contrasts.

The current workbook's candidate-only judgments remain useful for H_C. They
do not provide H_R or H_E. The manifest defines 400 primary units and 200
diagnosis-enriched supplementary units; use primary inclusion weights for
overall estimands under that design. Do not pool all 600 unweighted or treat
conditional supplemental probabilities as unconditional inclusion weights.
Extending those units with full-source evidence can address BACE-inventory
questions, but cannot establish the completeness of BACE extraction.

For coverage and three-method comparisons, sample generated passages or
disclosures independently of BACE's inventory. Include both disagreement
directions and some shared-positive/shared-negative cases. An enriched
diagnostic sample requires recorded inclusion probabilities and a clear
separation between conditional mechanism estimates and population estimates.
Choose sample size after specifying precision, anticipated discordance,
within-company dependence and annotation workload; no universal claim count
guarantees adequacy.

Existing [descriptive results](results.json) are diagnostic starting points.
New reference-based loss rates, false-rejection estimates, confidence intervals,
controlled-condition effects and temporal interactions are all
`COMPUTATION_PENDING`.

The Evonik example quoted in the earlier discussion remains qualified by the
[input-boundary recheck](evonik_boundary_recheck.json): the supplied table
omits material unit/column context. Its questionable contradiction rationale
does not establish a confirmed wrong binary rejection. It must not be used
as a known-positive reference item without further adjudication.
