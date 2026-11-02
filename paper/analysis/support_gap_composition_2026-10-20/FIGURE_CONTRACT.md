# Figure contract

- Claim: factual boundary distortion is the largest BACE diagnostic category
  among positive disagreements in each selected surface-matched subset.
- Audience and use: a descriptive figure for discussion with the supervisor;
  not a journal submission or an evaluator accuracy claim.
- Backend: Python/Matplotlib, following the project's existing analysis stack.
  Use the existing analysis interpreter without installing or changing packages.
- Archetype: one horizontal grouped bar chart; six mutually exclusive BACE
  diagnosis labels, two comparator series. Categories remain in the same order.
- Denominator: 2,010 positive BACE/RAGAS disagreements and 500 positive
  BACE/RAGChecker disagreements. These are distinct selected claim subsets.
- Statistical unit: a unique matched target-claim pair within a disclosure.
  Percentages are exact pooled category counts, not means over repeats.
  No confidence intervals, tests, random sampling or independence assumptions.
- Source: `category_composition.csv`, verified by `analyze_gap_composition.py`.
- Geometry: 183 by 116 mm; sans-serif editable text, minimum 7.5 pt;
  blue and orange series, with hollow bars for the second for grayscale use.
- Deliverables: PDF, SVG, PNG preview, plotting script, source table and fresh
  source/glyph/collision/alignment QA. A single plot area makes alignment N/A.
- Interpretation boundary: the figure describes saved automated disagreements,
  not the complete native support-rate gap or confirmed comparator errors.
  Zero contradiction means no contradiction-labeled pair was matched.
