# Figure 2 delivery checks

Prepared: 2 October 2026. Target: Nature Sustainability, Article.

## Numerical integrity

The figure includes all 1,798 completed disclosure scores, all three support
categories for 94,955 deduplicated disclosure claims, and all 12 tasks in protocol
order. Every score is checked against its integer claim counts and saved export.
Completed IDs match the execution record. Two incomplete cases are listed in
`excluded_cases.csv` and excluded without zero imputation.

The 55.4% disclosure mean and 55.1% pooled claim support use different weights,
explicitly distinguished in the legend. All-DC denominators retain non-disclosure
statements. Means and counts are independently checked; 95% company-cluster
interval endpoints are copied from saved exports. No new bootstrap run,
hypothesis test, model call or human-validation result was added.

Histogram edges use integer percentages divided by 100. Every bin assignment is
checked against exact integer supported/all-DC ratios to prevent floating-point
boundary misclassification. Bins are left-closed and right-open, except the final
bin includes 100%. All bins together contain all 1,798 scores.

## Automated checks

- `fig2.alignment.json`: PASS at 1.5 pt tolerance; no exemptions.
- `source_validation.json`: no failures; two reviewed warnings described below.
- `fig2.glyph-audit.json`: minimum standalone PDF text size 6.5 pt.
- `fig2.collision-audit.json`: no failures or warnings for the final PDF.
- `qa.json`: editable vector text, 180 × 154 mm PDF, 600 dpi PNG, minimum embedded font 5.78 pt; 202-word legend matches `main.tex`.
- Figure 2 and its full legend occupy page 12 of the 13-page manuscript. Figure 1 remains on page 11 with unchanged artwork.
- Results and Methods checks pass; all 39 imported scientific paragraphs remain unchanged. The source ZIP independently compiles without warnings and renders matching text; see `../latex_draft/provenance.json`.

The optional-TIFF warning is acceptable because primary artwork is vector PDF/SVG;
PNG is a preview. The width warning reflects the static parser's inability to
resolve `width_in`; actual PDF geometry is measured independently. These are
reviewed heuristic limitations, not waived rendering or data failures.

## Visual inspection

Assistant inspection covers each panel, the full figure, its embedded manuscript
page and the 13-page layout contact sheet. Labels, counts, means, intervals and
sample sizes are visible without clipping or overlap. The task numeric axis spans
0–100%, with label/value columns outside that numeric region. Category labels
supplement colour. The legend stays on the figure page and distinguishes
company-resampling uncertainty from judgment validity. `visual_review.json`
records the inspected artifact hashes.

These preparation checks do not constitute author scientific approval, journal
peer review or completed human validation. Figures 3 and 4 and other unfinished
manuscript sections remain explicitly marked as pending.

## Reproduction

From the repository root:

```bash
/usr/bin/python3 paper/analysis/fig2/render_fig2.py
```

Build with `python3 build.py` from `paper/manuscript/`, then run `audit_fig2.py`
with the independent writing environment's Python, which provides PyMuPDF.
`verify_latex.py` independently compiles the source archive. All new calculations
and QA outputs live under `paper/`; experiment environments and artifacts remain
read-only throughout this workflow.
