# What explains the BACE–RAGAS and BACE–RAGChecker support gaps?

20 October 2026. Exploratory analysis of saved main-experiment outputs.

**There are substantial support disagreements for matched target texts. Most
positive disagreements carry BACE's factual-boundary-distortion diagnosis.
The full native score gap cannot yet be identified as comparator misses.**
Some inspected records show a comparator accepting an assertion that exceeds
its cited evidence. Others expose differences in BACE's candidate evidence or
in the interpretation of time, scope and inference. Independent adjudication
has not established their frequencies.

## 1. What the main score gap measures

Among 1,798 jointly completed disclosures from 30 companies, the mean support
rates are 55.38% for BACE, 90.66% for RAGAS and 90.24% for RAGChecker. The
comparator-minus-BACE gaps are therefore **35.28 and 34.86 percentage points**.
Each disclosure receives equal weight. Two of the 1,800 planned disclosures
remain incomplete and are excluded, without assigning zero scores.

These scores use different target inventories: 94,955 BACE claims, 76,123 RAGAS
claims and 72,633 RAGChecker claims. Subtracting the rates does not tell us
which BACE-unsupported assertions were accepted, rejected, merged or omitted
by the other evaluator. Native scores are evidence-support measures, not
independently validated accuracy measures.

## 2. Do the evaluators disagree on the same target text?

We matched complete target text within each disclosure after casefolding,
whitespace normalization and removal of one final period. Only unique
one-to-one matches were retained. Internal punctuation, word order, numbers,
units and qualifiers were preserved. No fuzzy matching was used.

RAGChecker saves subject/relation/object triples; their space-joined text
usually lacks the final period used by BACE. The original period-sensitive
rule produced zero RAGChecker matches. Removing this surface difference
produces 1,317 pairs. RAGAS's 5,709 pairs are unchanged from the earlier analysis.

| Saved paired outcome | RAGAS | RAGChecker |
|---|---:|---:|
| All matched pairs | 5,709 | 1,317 |
| Matched disclosures | 1,454 | 653 |
| Coverage of all 94,955 BACE claims | 6.01% | 1.39% |
| Both supported | 3,354 | 775 |
| BACE unsupported; comparator supported | **2,010** | **500** |
| BACE supported; comparator unsupported | 30 | 8 |
| Both unsupported | 315 | 34 |

Among **matched BACE-unsupported** claims, RAGAS accepted
2,010/2,325 = **86.45%**, and RAGChecker accepted 500/534 = **93.63%**.
These are conditional disagreement rates. They are not confirmed miss rates:
BACE labels are not independent ground truth. Same target wording also leaves
the evidence representation and checking procedure different.

The two selected subsets differ. Neither their coverage nor these acceptance
rates support a population-level accuracy comparison between the comparators.
Unmatched text is unresolved alignment, not evidence of extraction omission.

## 3. Which unsupported categories occur in the positive disagreements?

Here the denominator is **2,010** for RAGAS and **500** for RAGChecker: only
the pairs where BACE is unsupported and the comparator is supported. Each
pair has one saved BACE diagnostic label.

| BACE diagnosis | RAGAS: count (share) | RAGChecker: count (share) |
|---|---:|---:|
| Factual boundary distortion | 1,419 (70.6%) | 392 (78.4%) |
| Evidence conflation | 283 (14.1%) | 56 (11.2%) |
| Inferential inflation | 156 (7.8%) | 34 (6.8%) |
| Unsupported novelty | 100 (5.0%) | 15 (3.0%) |
| Non-disclosure statement | 52 (2.6%) | 3 (0.6%) |
| Contradiction | 0 (0.0%) | 0 (0.0%) |

Rounding can make displayed percentages sum to slightly more than 100%.
No contradiction-labeled BACE claim entered either matched subset, so its
zero count does not establish successful contradiction detection.

![BACE diagnostic composition among positive support disagreements](/home/muwang/master_thesis/paper/analysis/support_gap_composition_2026-10-20/category_composition.png)

Factual boundary distortion plus evidence conflation account for **84.7%**
and **89.6%** of these positive disagreements. This points to boundaries and
relationships as the first issues to inspect. These diagnostic categories
are not independently confirmed causal explanations of the support decisions.

The percentages describe disagreement composition, not shares of the entire
native 35-point gap. Within the matched subsets alone, exact pooled gap
accounting is possible:

`Matched gap (pp) = 100 × [positive disagreements − reverse disagreements] / all matched pairs.`

Thus RAGAS's matched pooled gap is 34.68 pp and RAGChecker's is 37.36 pp.
Factual boundary distortion contributes +24.86 and +29.76 pp, respectively;
the reverse-disagreement corrections are −0.53 and −0.61 pp. Every category's
contribution is in `matched_gap_accounting.csv`. These pooled calculations
weight pairs equally; they must not be substituted for the complete native
disclosure-macro gaps. Equal-disclosure calculations on the selected subsets
are also saved separately in that table.

For context, all 42,646 BACE-unsupported claims have a different composition:
19,130 boundary distortion, 12,205 evidence conflation, 6,378 non-disclosure,
3,193 inferential inflation, 1,698 novelty and 42 contradiction. These are
not counts of comparator disagreements.

## 4. What can already be checked against source evidence?

**A comparator acceptance that crosses a measurement boundary: SCA, 2022.**
The supplied indicator reports five confirmed **incidents in which workers
were dismissed or disciplined**. The generated disclosure instead reports
five **workers** dismissed or disciplined. Five incidents do not establish
five distinct workers. RAGChecker accepted its worker-count triple using
that incident-count indicator as entailment. RAGAS accepted a worker-count
assertion and explicitly invoked the incident count in its reason. BACE
rejected its corresponding assertion as factual boundary distortion.

This is a concrete source-relative unit mismatch in the inspected record.
It does not establish the actual number of workers outside the supplied
evidence or an error rate. The three extracted phrasings differ, so this
illustration is **outside** the surface-matched frequency tables. Exact
targets, indicator text, evidence identifiers and original paths are saved
in `sca_source_example.json`; original records were rechecked on 20 October.

**An alternative explanation requiring review: missing candidate evidence.**
Of the 100 RAGAS positive disagreements diagnosed as unsupported novelty,
**78 have zero BACE candidate ECs**; for RAGChecker the count is **13/15**.
Across all positive categories, the corresponding zero-candidate counts are
80/2,010 and 13/500. An empty candidate set prevents a positive BACE support
decision, but does not establish absence of support in the original cards.
Conversely, a nonempty candidate set does not guarantee that all decisive
evidence was retained.

For the matched claim “Social reporting covers HOP!.”, RAGAS accepts the
claim and BACE has no candidate EC. The supplied 2018 report nevertheless
contains “Social: Air France in France, HOP!, KLM in the Netherlands and
KLM Catering Services.” This is an evidence-path difference. The footnote's
precise scope and its applicability to the 2019 disclosure still require
review; it is not a confirmed BACE false rejection. The original-source hash
checks and the complete saved example are in `hop_candidate_example.json`.

## 5. The decision for the next analysis

The next question is which paired disagreements are comparator false
acceptances, BACE false rejections, differences in the available evidence, or
unresolved interpretation. A shared review policy must specify temporal
continuity, population and units, planned versus completed action, and the
inferences permitted from combined evidence.

Use blinded source review with the complete generated paragraph and original
supplied cards. Include both disagreement directions and agreement controls;
record claim equivalence separately from support. Prioritize boundary
distortion and conflation for the main mechanism review, and examine
zero-candidate novelty as a separate pipeline diagnostic. A prevalence estimate
would require an explicit sampling frame, known inclusion probabilities and
appropriate weighting, accounting for company clustering. No such independent
adjudication or population estimate is reported here.

All numerical results are reproducible from `analyze_gap_composition.py`.
The run verified snapshot hashes, all native counts and rates, prior RAGAS
pair membership, both matched-gap identities, and original comparator text
and verdicts for all 7,026 retained pairs across 2,107 source files. No model
calls, experiment changes, confidence intervals or hypothesis tests were made.
