# Figure 4 delivery checks

Prepared: 2 October 2026. Target: Nature Sustainability, Article.

## Cohort and numerical checks

All three panels use the identical 1,798 completed disclosures from 30 companies.
Unique generation-case IDs, company IDs, scores and counts match the snapshot,
the execution record and both original figure exports. Two incomplete BACE cases
are listed in `excluded_cases.csv` and excluded throughout without imputation.
Comparator-only rows from the 1,800-case cohorts are not added to any panel.

Mean native scores (55.4%, 90.2%, 90.7%), native claim-count medians (52, 40, 42),
and paired mean score gaps (−34.9 and −35.3 percentage points) were independently
recomputed and checked against saved outputs. Score gaps are formed within each
disclosure before taking a mean. The saved paired 95% interval endpoints are
`SOURCE_REPORTED`; means, medians and ECDF coordinates are `COMPUTED_VERIFIED`.

Every ECDF jump stores its tied-value frequency and cumulative count. Each of
the six curves represents all 1,798 observations and ends at 100%. No bins,
smoothing, jitter, subsampling, new bootstrap run or hypothesis test are used.
The count axis includes the complete observed range for every method. The
difference axis includes zero, and signs and interval limits are preserved.

## Interpretation checks

Panels a and c use cumulative percentages of disclosures, with arithmetic mean
scores and median claim counts respectively. Native BACE all-DC support and
comparator faithfulness retain their own denominators and judgment procedures.
The figure does not imply matched claims, evaluator accuracy, or a causal
decomposition of the score gap. Saved intervals resample companies, not individual
claims, and do not quantify model-run variability or judgment validity.

## Rendering and integration

- `fig4.alignment.json`: PASS at 1.5 pt tolerances, with the left panel spanning two rows and the two right panels aligned. No exemptions.
- `source_validation.json`: no failures; two reviewed heuristic warnings described below.
- `fig4.glyph-audit.json`: minimum standalone text size 6.5 pt.
- `fig4.collision-audit.json`: no failures or warnings.
- `qa.json`: editable vector text, 180 × 138 mm PDF, 600 dpi PNG and minimum embedded text size 5.78 pt.
- The 203-word caption exactly matches the working legend. Figure 4 and its full legend occupy page 14 of the 14-page manuscript.
- Figures 1–3 remain unchanged on pages 11–13. All 39 imported Results/Methods paragraphs and the two existing citations are preserved.
- Local manuscript compilation and isolated source-ZIP compilation pass without warnings; portable PDF text matches. No current main-figure placeholders remain.

The source parser cannot resolve the width variable; actual PDF dimensions are
measured independently. Its optional-TIFF warning is acceptable because the
primary artwork is editable vector PDF/SVG and the 600 dpi PNG is a preview.
Neither warning concerns missing data or a rendering failure.

## Visual inspection and reproduction

Assistant inspection covers every panel, the complete figure, its embedded page
and the 14-page layout contact sheet. Method colours and line styles are
consistent; marker shapes supplement the contrast colours. Legends occupy clear
areas, all intervals have visible caps, and signs, labels and source values are
legible. The final visual record is bound to artifact hashes in
`visual_review.json`. This is not author scientific approval or human validation.

Run `/usr/bin/python3 paper/analysis/fig4/render_fig4.py` from the repository root.
Build with `python3 build.py` from `paper/manuscript/`, then run `audit_fig4.py`
with the independent writing environment's Python (PyMuPDF). The manuscript
`verify_latex.py` audit independently compiles the source archive. All new outputs
stay under `paper/`; no experiment artifact, environment, model setting or frozen
protocol is changed, and no external upload is performed.

The four current main figures are complete as drafting artifacts. Introduction,
Discussion, Abstract, author information and declarations remain incomplete;
independent human assessment remains pending.
