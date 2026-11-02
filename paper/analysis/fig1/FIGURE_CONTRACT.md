# Figure 1 contract

Prepared: 1 October 2026. Target: Nature Sustainability, Article.

## Scientific purpose

**Results-level question:** What was evaluated, and which evidence actually reaches a BACE support judgment?

**Figure-level claim:** The study evaluates generated disclosure claims within a defined supplied-evidence workflow; BACE support and the prepared human assessment are conditional on extracted claims and selected candidate evidence.

This is a schematic of the executed workflow and the prepared review scope, not
evidence of evaluator accuracy. A conflict with recorded inputs, completion status
or the formal review design would require revising the schematic.

## Evidence architecture

| Panel | Role | Content and source |
|---|---|---|
| a | Define the empirical cohort and evidence boundary | Company-year-task counts from saved metrics; source-year windows and retrieval limits from frozen configurations. Distinguish 1,800 planned and 1,798 completed paired cases. |
| b | Define the conditional measurement and review boundary | Supplied evidence and generated disclosure lead to EC/DC construction, candidate selection and per-claim judgment. Only unsupported claims receive automated diagnoses. The review branch uses the actual judgment inputs and is marked prepared, with local annotation cells blank. |

Archetype: schematic-led composite. Panel b has greater height because its
workflow carries the central measurement distinction. Panels share left/right
edges and letter anchors; their heights encode layout needs, not data magnitude.

## Visual and export contract

- Use the saved Python plotting preference. Matplotlib draws the figure; no external image-generation API or borrowed artwork is involved.
- Export a 180 mm-wide vector PDF and SVG with editable text, plus a 600 dpi PNG preview. The planned height is 167 mm.
- Use a white background, muted blue for supplied/constructed evidence and automated processing, neutral grey for study bookkeeping, and an amber dashed outline for prepared human review. Direct labels and dashed geometry preserve the distinction without depending on colour.
- Use sans-serif text at 6.5-7.5 pt and 8 pt panel letters. At the manuscript's 160 mm display width, the smallest 6.5 pt labels remain above 5 pt.
- Keep source/report years distinct from publication dates. The extracted metric records are not shown as independently verified original report quotations.
- Support receives one DC, selected candidate EC texts, company and reporting year. Separate provenance, raw reports and unselected ECs are not depicted as judgment inputs. Candidate selection itself uses EC/DC texts only.
- Do not draw a completed human-validation result, comparative-accuracy ranking or representative error estimate.

## Numerical and source contract

Recompute cohort counts from the saved metrics and verify completed IDs against
the execution record. Check the prepared review sample and inspect both workbook
label columns. Save every displayed count and configured limit with its source,
locator and aggregation rule. No statistical intervals, hypothesis tests or model
calls are needed for this schematic; they are not applicable to its count/flow role.

The method definition, support/diagnosis instructions, formal review guide and
native-input adapter support the operational wording. The figure is original and
does not introduce new literature claims or citation occurrences. Native evaluator
procedures remain described in Methods; panel a's paired cohort refers to the
three available native scores, not aligned claim inventories.

## Delivery gates

Measure the final panel rectangles and letter anchors with the Matplotlib
alignment gate. Run source validation, a PDF glyph-size audit and the rendered
collision audit. Inspect both panels and the whole figure, then inspect the figure
and full legend inside the compiled manuscript. Preserve each audit against the
final PDF hash. Update the Overleaf package and verify isolated compilation.
These checks do not substitute for the author's scientific review.
