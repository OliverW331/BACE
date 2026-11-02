# Figure 1 delivery and QA notes

Figure 1 is included on page 11 of the current 12-page manuscript, with a
195-word English legend. The Overleaf ZIP includes the final PDF/SVG/PNG artwork;
the PDF is used for typesetting. Isolated source compilation passed and retained
all 39 existing Results/Methods paragraphs.

| Panel | Scientific role | Quantification and uncertainty | Geometry and visual check |
|---|---|---|---|
| a | Define study cohort and supplied evidence | Cohort counts and configured source/card limits; no interval or hypothesis test applies. | Common panel edges and letter anchors pass; labels and source windows are legible. |
| b | Define conditional judgment and review scope | Prepared sample/workbook counts; no human-agreement estimate. | Inputs, support outputs and unsupported-only diagnosis are distinct; pending review uses a dashed amber branch. |

The final figure is 180 × 167 mm with editable vector text. The PDF text audit
found a 6.5 pt minimum; the minimum after embedding at the manuscript width is
approximately 5.78 pt. The collision audit reports zero failures and zero
warnings. Its contained-fill records correspond to intentional text inside boxes.

Two source-preflight warnings were reviewed: TIFF is unnecessary for the primary
vector artwork, and a heuristic misread of `180/25.4` is resolved by the measured
180 mm PDF width. The 600 dpi PNG is a preview. These warnings are retained in
the audit records rather than hidden.

`source_data.csv` and `verified_facts.json` preserve the displayed numbers and
rules. `provenance.json` hashes original inputs and exports; `qa.json` records
physical measurements and caption checks; `visual_review.json` records inspection
of both panels and all manuscript pages. Run the renderer before the geometry
and integration audit when revising the artwork. Rebuild the manuscript before
checking its embedded figure dimensions and the Overleaf package.

The diagram is an original Python/Matplotlib schematic. No image-generation API,
new model evaluation, external upload or author approval is claimed. It remains
subject to the author's scientific review. The next manuscript figure is Fig. 2.
