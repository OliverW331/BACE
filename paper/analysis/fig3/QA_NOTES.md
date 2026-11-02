# Figure 3 delivery checks

Prepared: 2 October 2026. Target: Nature Sustainability, Article.

## Scientific and source checks

The six diagnostic counts were recomputed over all 1,798 completed BACE cases and
checked against the saved composition export. They sum to 42,646 unsupported
DCs; factual boundary distortion and evidence conflation total 31,335 (73.5%).
Each case's six counts sum to its unsupported count. The two incomplete cases
remain excluded, with no zero imputation. Non-disclosure statements and the 42
contradiction labels are retained. No confidence interval or hypothesis test is
asserted for these pooled descriptive shares.

Both case IDs and original seeds are unchanged. Exported input, generated text,
DCs, ECs, support sets, candidate membership and diagnoses match the saved case
JSONL. `case_evidence.json` retains the complete generated disclosures and all
supplied evidence cards, plus all candidate ECs for each selected DC. The figure
shows only the relevant excerpts, explicitly labelled by stage.

The original Wärtsilä report passage on p. 132 was read directly. The ASML PDF
hash matches the saved source-layout record, and the original glossary rows on
printed p. 209 / PDF p. 216 were checked in both extracted text and an unaltered
local crop. The figure's typeset transcription preserves direct Scope 1 and
indirect Scope 2 as separate rows. Quoted text changes only wrapping and stated
CO2-to-CO₂ typography. Original report identifiers, versions, locators, hashes
and access date are in `original_source_checks.json`.

The temporal rationale is attributed to BACE, and discontinuation is not inferred.
The ASML example challenges an automated rationale without validating the entire
generated claim or disclosure. Neither case is a representative validation sample.

## Rendering and integration

The final artifact is an editable 180 × 170 mm PDF/SVG with a 600 dpi PNG preview.
The minimum source text size is 6.5 pt, giving 5.78 pt at the manuscript's 160 mm
width. All three panel rectangles and letter anchors pass the 1.5 pt alignment
gate, without exemptions. A separate rendered text-spacing guard keeps the
panel-a axis label more than 3 pt clear of the panel-b heading (measured gap
10.68 pt). The figure was built anew; only styling and audit conventions were
inherited from the earlier manuscript figures.

Source validation has no failures. Two warnings are reviewed: a TIFF is
unnecessary for this editable vector figure, and the static parser cannot resolve
the width variable, so actual PDF geometry is measured independently. The final
PDF text-size and collision audits pass. Text inside the deliberately shaded
case boxes is intentional; the collision report contains no failures or warnings.

The full 215-word English legend matches `main.tex`. Figure 3 and its legend are
on page 13 of the 14-page manuscript. Figures 1 and 2 remain on pages 11 and 12
with unchanged artwork hashes. The manuscript compiles without warnings; the
portable source ZIP independently compiles and renders matching text. All 39
imported Results and Methods paragraphs and the two existing citations are
preserved. Figure 4 and unfinished manuscript sections remain labelled pending.

## Visual scope and reproducibility

Assistant inspection covers all three panels, the whole figure, the embedded
figure and complete legend, and the 14-page layout contact sheet. It also covers
the original ASML glossary crop. Category labels, counts, quotations, row links,
source locators and interpretation limits are readable. No clipping or unintended
overlap is retained. `visual_review.json` binds this inspection to final hashes.
These checks do not constitute author scientific approval or human validation.

Run `prepare_data.py` with the independent writing environment's Python
(PyMuPDF), then `render_fig3.py` with `/usr/bin/python3` (Matplotlib). Build from
`paper/manuscript/` with `python3 build.py`, then run `audit_fig3.py` and the
manuscript `verify_latex.py` audit. New outputs are confined to `paper/`; no
experiment environment, frozen configuration, saved result, or original PDF is
modified. No model call, external upload or submission is performed.
