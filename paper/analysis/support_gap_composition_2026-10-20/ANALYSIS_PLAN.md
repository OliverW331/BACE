# Support-gap composition: descriptive analysis plan

Analysis date: 20 October 2026. This is a post-experiment analysis of saved
outputs, planned after inspecting exploratory matching counts. It is not
preregistered. No new evaluator calls or human annotations are performed.

1. Recompute native support rates on disclosures completed by all three
   evaluators. Give each disclosure equal weight; exclude incomplete cases,
   without assigning zero. Check claim counts and judgments against metrics.
2. Match target text within the same disclosure, using casefolding and
   whitespace normalization, optionally removing one final period from both
   sides. Retain only unique one-to-one matches. Keep internal punctuation,
   numbers, units, qualifiers and word order. Report the original strict rule
   and the period-normalized rule separately. RAGChecker text is the saved
   subject/relation/object triple joined with spaces. This is surface-text
   alignment, not independent semantic validation or a shared evidence input.
3. Tabulate all four paired verdict combinations. Define the positive
   disagreement as BACE unsupported and comparator supported. Its category
   shares use all positive disagreements for that comparator as denominator.
   These are BACE's automated diagnostic labels, not adjudicated error types.
4. Also report comparator acceptance among matched BACE-unsupported claims,
   per-category denominators, coverage, reverse disagreements and exact
   arithmetic contributions to the pooled matched-subset gap. Do not call
   this a decomposition of the complete native disclosure-macro gap.
5. Verify snapshot hashes, reproduce prior RAGAS matching and read original
   comparator records for every retained pair. Review the existing SCA
   incidents/workers example against original saved inputs and verdicts.
6. Save a reproducible script, tables, numerical results, provenance, and an
   English interpretation. Use a grouped horizontal bar chart to show category
   composition. Each series represents a different selected subset. No
   confidence intervals or tests: this is an exact description of saved
   outcomes, with no claim of population representativeness or independence.

The unanswered question is how many disagreements are comparator false
acceptances, BACE false rejections, or evidence/interpretation differences.
Resolving it requires a shared support policy and blinded source-based review
of both disagreement directions and controls. Unmatched claims are unresolved
alignment, not automatically comparator extraction omissions.
