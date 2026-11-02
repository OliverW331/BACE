# Diagnosing the native evaluator score gap

Prepared: 30 September 2026. Status: exploratory analysis of saved results.

The objective is to distinguish differences in claim construction, loss or
alteration of supporting evidence, and support judgments. The analysis does
not take any evaluator's decision as ground truth. No new model evaluations,
human annotations, or changes to experiment artifacts were performed.

## Executed analysis and provenance

The [analysis script](analyze_saved_gap.py) reads the saved metrics, BACE claims,
and comparator claims. Their hashes match the existing snapshot manifest. It
reconciles every paired case's support counts and native scores with the
claim-level records and reproduces the existing literal-alignment counts.
Full raw model histories and extraction lineage were not re-audited.

- Results: [results.json](results.json).
- Per-disclosure inputs to the new calculations: [case_diagnostics.csv](case_diagnostics.csv).
- All uniquely matched literal pairs and their original labels: [literal_pairs.csv](literal_pairs.csv).
- Input hashes, output hashes, command and environment: [provenance.json](provenance.json).

The cohort contains 1,798 paired disclosures across 30 companies from 1,800
planned cases. The two incomplete BACE cases remain excluded, never scored as
zero. Native and sensitivity macro scores give each disclosure equal weight;
pooled and matched-claim scores give each relevant claim equal weight. Claims
are nested within disclosures and companies. These are descriptive results;
no new confidence intervals, significance tests, or resampling were performed.

Reproduce in the independent writing environment:

```bash
/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/evaluator_gap/analyze_saved_gap.py
/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/evaluator_gap/inspect_evonik.py
```

## What the saved results can already establish

### Non-disclosure sensitivity leaves a large difference

Removing the 6,378 unsupported DCs diagnosed by BACE as
`non_disclosure_statement` raises its disclosure-macro score from 55.4% to
59.7%, an increase of 4.35 percentage points. The remaining mean differences
are 30.51 points below RAGChecker and 30.94 points below RAGAS.

This calculation preserves the supported numerator of 52,309 DCs and reduces
the pooled denominator from 94,955 to 88,577. It removes only statements given
that unsupported diagnosis, not every non-disclosure assertion. The change
therefore describes a different estimand; it is not an accuracy correction or
a fair common-inventory comparison. It does show that this particular
denominator treatment is insufficient to eliminate the observed difference.

Numerical locator: `results.json.non_disclosure_sensitivity`.

### Completely empty candidate sets are a limited subset

There are 1,911 zero-candidate DCs: 2.01% of all BACE DCs and 4.48% of its
unsupported DCs. They occur in 600 disclosures. Their diagnoses are
`non_disclosure_statement` (985) and `unsupported_novelty` (926).

If every zero-candidate DC were hypothetically relabelled supported, with
everything else fixed, the BACE macro score would rise to 57.4%, at most
2.05 percentage points above its saved value. This is an arithmetic ceiling
for changing this subset alone. Their actual support was not determined.

**This does not bound the overall effect of extraction or candidate-selection
errors.** A nonempty candidate set can still omit its decisive premise, and
an extracted EC can change a qualifier. The zero-candidate scenario overlaps
with the non-disclosure sensitivity; their increases must not be added.

Numerical locator: `results.json.zero_candidates`.

### Equal wording does not eliminate support disagreement

The existing matching rule finds 5,709 unique BACE–RAGAS pairs after
casefolding and whitespace normalization within each disclosure. They span
1,454 disclosures and cover only 6.01% of BACE DCs. Six ambiguous RAGAS rows
are excluded. On these pairs, BACE supports 59.3% and RAGAS supports 94.0%.

| Saved paired judgments | Claim pairs |
| --- | ---: |
| Both supported | 3,354 |
| Both unsupported | 315 |
| BACE unsupported, RAGAS supported | 2,010 |
| BACE supported, RAGAS unsupported | 30 |

These are counts of automated judgments, not a confusion matrix against human
truth. Identical wording removes one explanation for these particular
disagreements: the methods did not simply extract differently worded target
claims in these pairs. Their evidence representations and judgment procedures
still differ. Interpretation may also depend on context supplied with the
same words.

The matched subset is highly selected. Its rates cannot be extrapolated to
the unmatched claims or treated as a decomposition of the overall native
score gap. RAGChecker has no matches under this strict string rule because
its joined triples use a different representation; this does not mean no
semantic overlap.

Numerical locator: `results.json.literal_alignment`.

### Claim count alone is not a sufficient explanation

Among the 167 disclosures where BACE has no more claims than RAGChecker,
BACE still averages 32.09 points lower. The corresponding RAGAS subset has
233 disclosures and a 33.51-point difference. Even exactly equal counts
leave large differences: 32.45 points in 40 BACE–RAGChecker cases and 33.74
points in 72 BACE–RAGAS cases.

These conditional subsets do not match claim meaning, and selection into them
is not random. They rule out a simplistic account in which a larger claim
count is necessary for a lower BACE score; they do not quantify a causal
effect of splitting, merging, or coverage.

Numerical locator: `results.json.claim_count_diagnostics`.

## A correction to the previously discussed Evonik example

The [targeted recheck](evonik_boundary_recheck.json), produced by
[inspect_evonik.py](inspect_evonik.py), preserves the full supplied evidence,
EC inventory, candidate ECs, original decisions and source hashes for the
previously discussed emissions-total claim. The consumed case artifacts
match their entries in the existing snapshot source ledger.

The exact supplied Evidence 18 contains `9,519 5,468 2008 2021`, but it does
not explicitly retain a thousand-tonne unit or intact numerical column
headings. Its extracted EC retains the previous emissions target, without
the numerical emissions levels. The support-stage candidates contain the
separately reported Scope 1 and Scope 2 values instead.

The earlier conversation and Evonik row in
[the alternative-case report](../../06_verified_disagreement_examples.md)
overstate the certainty that the complete generated numerical claim is
supported by the prompt-visible table. This recheck supersedes that strong
interpretation. Missing numbers in an EC are not automatically an extraction
error when the supplied source itself loses material context. The original
PDF was not rechecked here and cannot silently be added to the evaluator's
evidence boundary.

BACE's contradiction rationale nevertheless treats a sum of coarsely reported
components as establishing incompatibility with a more precise total, without
resolving precision and accounting basis. This challenges the diagnosis; it
does not independently prove the binary unsupported judgment wrong. The
diagnosis was produced after the support decision and is not a causal record
of that earlier decision. Retain this as an ambiguous pipeline/diagnosis
example rather than a confirmed error by either side.

## Analyses still needed to address the two scientific questions

The following is a proposed design, not completed validation or authorization
to run additional model experiments.

### A. Is support being lost before the BACE judgment?

For each reviewed proposition, first check whether the DC faithfully
represents the generated passage. Then independently assess the same
proposition against the complete prompt-visible evidence, the full EC
inventory, and the selected candidate ECs. Preserve exact source passages,
material qualifiers, EC identifiers, uncertainty, and multiple applicable
failure flags.

| Observation after source review | Diagnostic interpretation |
| --- | --- |
| DC changes or adds a material assertion relative to the generated passage | Target-claim extraction problem; resolve before evaluating the original disclosure |
| Supplied evidence supports the proposition, but full ECs lose a required premise or qualifier | Evidence extraction/representation loss |
| Full ECs preserve sufficient evidence, but selected ECs do not | Candidate-selection loss |
| Selected ECs suffice, but BACE returns unsupported | Support-judgment disagreement supported by review |
| Supplied evidence does not establish the proposition and comparators accept the same complete proposition | Comparator acceptance unsupported under the documented rubric |
| Supplied cards omit essential units, headers, attribution, or scope | Input ambiguity or source-preparation limitation; do not force a clean evaluator-error attribution |

The observation should be tied to a sufficient support set where support is
claimed. A full-EC failure cannot be inferred simply from the existence of an
empty candidate set. Reverse cases also matter: extraction can introduce
spurious support, and all methods can accept unsupported claims. Multiple
problems can occur in one pipeline, so error flags are not automatically an
additive causal decomposition.

The proposed review should hide method names and original verdicts while the
reference judgment is made. Use independent or counterbalanced review of
evidence conditions to limit anchoring and carryover. Adjudicate disagreements
after recording initial judgments. Keep uncertain cases visible.

The [current formal workbook](../../../BACE/analysis/validation/README.md)
contains only DCs and candidate ECs. Its intended conditional support and
diagnosis validation remains useful, but it cannot answer the first two
upstream questions in the table. Additional source-review materials would be
needed; the existing packets should retain their defined scope.

### B. Are native claim construction and support policies driving disagreement?

Use sampled generated passages as the reference for proposition coverage,
rather than treating BACE's inventory as the complete set. Construct a
method-independent proposition inventory, with source quotations and material
qualifiers, and map each native inventory to it. Record one-to-one,
one-to-many, many-to-one, missing, and incompatible mappings. Splits and
merges must preserve the same substantive proposition before native verdicts
can be compared. Unmatched claims are not automatically unsupported or absent
from the original disclosure.

This separates coverage of propositions from judgment on shared propositions.
Report both; a method can receive a high native score by missing difficult
propositions without making an incorrect decision on those it did extract.
Conversely, a method can lower its score by inventing a qualifier during
extraction.

Specify the support rubric before examining verdicts. Review temporal
continuity, population transfers, missing units, reporting precision,
cross-card reasoning, and statements about missing disclosure separately.
Where more than one interpretation is defensible, retain ambiguity or report
a clearly labelled policy sensitivity. Agreement with BACE's operational rules
alone does not demonstrate that its rules are the uniquely appropriate
definition of disclosure support.

If standardized-claim or standardized-evidence model reruns are later used,
label them as additional controlled conditions, not the frameworks' native
scores. Changing prompts and inputs can change the method being evaluated.

### Sampling and estimands

Start with a probability sample of disclosures/passages from the paired
cohort. If disagreement cases are enriched, include both directions and retain
selection probabilities. Review some shared-supported and shared-unsupported
cases to detect common errors. A discrepancy-only sample estimates properties
of discrepancies, not overall accuracy. The literal-match pool is useful for
inspection but cannot substitute for the probability sample.

Choose sample size after specifying precision and reviewer workload. Report
the fraction of BACE rejections supported by full-source review, upstream
losses among reviewed rejections, native proposition coverage, and judgment
agreement on comparable propositions with their actual denominators. These
quantities should remain separate from a proposed corrected disclosure-macro
score, which requires appropriately designed full-disclosure review or a
justified weighted estimator. Account for company and disclosure dependence.

Until those annotations exist, the warranted finding is substantial native
assessment disagreement with identifiable representation and judgment paths.
Neither evaluator superiority nor an attribution of the approximately
35-point gap to specific mechanisms has been established.
