# Figure and analysis review

Reviewed 20 October 2026 after the final render.

| Check | Result |
|---|---|
| Single panel claim | Boundary distortion is the largest diagnostic category in each selected positive-disagreement subset |
| Data and denominator | All six categories present; counts and percentages agree with the saved source CSV; separate n = 2,010 and n = 500 labels |
| Statistical unit and uncertainty | Unique target-claim pairs; exact descriptive proportions; no interval or test and no independent-replicate claim |
| Labels and legend | Readable; filled blue and hollow orange bars distinguish the series without relying on color alone |
| Interpretation | Subtitle defines positive disagreement; footnotes state limited coverage and that percentages are not confirmed error rates |
| Panel alignment | Not applicable: one plot area; audit JSON preserved |
| Source preflight | 19 PASS, 2 WARN, 0 FAIL |
| Rendered PDF typography | Minimum 7.5 pt; no text below the 5 pt floor |
| Rendered collision check | PASS: 0 FAIL, 0 WARN |
| Visual inspection | Final Matplotlib PNG inspected; no clipped labels, overlaps or obscured bar values |
| Numerical accounting | All four paired outcomes retained; category sums and both pooled/macro gap identities asserted by the analysis |
| File integrity | All 11 analysis output hashes checked after the final run; plotting input CSV and all figure export hashes checked |

The two source preflight warnings are accepted for this discussion artifact:
the PNG is a 300 dpi preview rather than a submission raster, and no TIFF was
requested. Editable vector PDF and SVG are the primary figure exports.

The RAGAS and RAGChecker series use different selected target subsets. The
figure cannot identify comparative evaluator accuracy, represent the entire
native score gap, or show contradiction detection performance. No
contradiction-labeled BACE claim entered either matched subset.
