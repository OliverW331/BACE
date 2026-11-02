# Design QA

Date: 2026-10-23

final result: passed

No actionable P0/P1/P2 findings remain in the scoped Carbon Studio style implementation. Neutral charcoal surfaces, soft white reading text, blue selection, green support, and amber diagnosis are applied throughout the working application. Six browser suites, the production build, and four hosting checks passed. Reference/implementation and multi-state comparison images were opened and inspected.

## Latest change: selected Carbon Studio style

The author selected the third displayed concept, Canva media `MAHY0v9kUAc`. The scope is applying that color and style direction to the existing interactive application. The selected source is saved as `qa/carbon-selected-reference.png`. Canva returned only a 200 × 128 preview of its 1712 × 1104 asset; its original-media browser viewer remained behind an access challenge. The available image was inspected directly. This review establishes style consistency and implementation readability, not pixel-accurate reconstruction of unavailable raster details.

- **[P1, fixed] Light surfaces and green-tinted body text conflicted with the selected dark direction.** Replaced legacy colors with shared CSS tokens and applied explicit surface/foreground states across nodes, original text, tables, case controls, filters, source records, support sets, diagnoses, and full readers. Native browser controls use `color-scheme: dark`.
- **[P2, fixed] Selection recolored ordinary candidate relationships blue.** Candidate paths now stay neutral during tracing; blue is used for node outlines and source selection. Green paths retain support-membership meaning.
- **[P2, fixed] The synthetic reference capture had excessive empty space above the nodes.** Top-aligned the four column bodies and reduced the desktop canvas height. Full support texts retain readable sizes and scroll rather than being compressed to reproduce the mock's compact bottom panel.
- The initial theme test had a misplaced parenthesis when reading computed SVG strokes; it was corrected before the successful run. No application-state logic, native adapter, graph model, saved claims, or assessments changed.

### Comparison evidence

| Artifact | Scope |
| --- | --- |
| `qa/carbon-reference-comparison.png` | Selected preview left / live synthetic implementation right; 1712 × 552 |
| `qa/carbon-before.png` | Earlier light application, same synthetic DC-01 with joint set expanded; 1712 × 1104 |
| `qa/carbon-demo.png` | Final dark application, DC-01 with expanded joint set and all its candidates traced; 1712 × 1104 |
| `qa/carbon-states-comparison.png` | Filter, original-evidence reader, diagnosis, and narrow review; 1712 × 1104 |
| `qa/carbon-reader.png`, `qa/carbon-diagnosis.png` | Full-size detailed reading and diagnosis captures; 1712 × 1104 |
| `qa/carbon-narrow.png` | Stacked diagnosis/candidate review; 430 × 900 |
| `qa/native-carbon-overview.png` | Saved-case overview and original table; 1712 × 1104 |
| `qa/native-carbon-review.png` | DC-04 with all four support sets expanded; 1712 × 1104 |
| `qa/native-carbon-reader.png` | Complete saved disclosure reader and table; 1712 × 1104 |

Captures use Chrome's native DevTools Protocol, CSS viewports matching capture size, and `deviceScaleFactor: 1`. The full comparison displays each half at 856 × 552; the selected preview is enlarged and the implementation is downsampled. This explicitly limited comparison supports broad palette, topology, and hierarchy judgments only. The full-size implementation captures were also inspected for typography, text wrapping, controls, and reading comfort. Original saved-case captures remain local and Git-ignored. The selected sketch uses synthetic content; the separate saved-case captures verify practical density rather than claiming identical contents.

### Required fidelity surfaces for this change

| Surface | Review and disposition |
| --- | --- |
| Fonts and typography | Local DM Sans now covers UI and reading content, replacing the prior serif document styling. It follows the selected sans-serif direction. Exact font identification from the tiny generated preview is unverified. Original prose is 15 px, full readers 17 px, with generous line height. Full-size saved text and table wrapping were inspected. |
| Spacing and layout | Four columns and the bottom inspector remain. Source prose sits on the common surface; claim nodes are compact and top-aligned. Existing full-text controls and larger readable support content intentionally require more space than the mock. Native inventories and narrow graph scrolling remain usable. |
| Colors and tokens | Canvas #18191B, surface #202124, soft white #E9E9E7; blue #85AEF5, green #62BD90, amber #D4A354. Related nodes use a subdued blue surface. Unrelated node text remains readable. Sixteen computed text samples have a minimum contrast of 5.9259:1; this is not a whole-product contrast certification. |
| Images and assets | Existing Phosphor controls and D3 relationship geometry remain. The selected design contains no decorative raster assets to recreate. No generated image is substituted for working controls or source text. |
| Copy and content | Existing English labels, complete source text, canonical claims, source tables, AND/OR groupings, and recorded outcomes remain intact. No visible theme explainer, new badges, or extra navigation were added. |

### Validation

`npm run test:theme` passes computed contrast, dark reader/menu surfaces, neutral candidates versus green support paths, reader return, and narrow review checks. Its evidence is `qa/carbon-theme-check.json`. `test:review`, `test:passage`, `test:multiset`, `test:native-browser`, and `test:browser` all passed sequentially without runtime errors. `npm run build` passed and the four `test:sites` checks passed. The adapter and graph model were not modified, so their prior verification was not rerun for this style-only change.

Remaining scope limits: exact raster micro-fidelity is unverified because only the selected thumbnail was exposed; participant usability testing, complete screen-reader tasks, and full accessibility conformance remain pending. The current pass applies to the requested theme implementation and tested interactions.

## Previous correction: simultaneous support-set expansion

The author's screenshot shows four alternative support sets for DC-04, with only Set 2 expanded. The correction keeps the existing bottom review and adds simultaneous reading without changing the saved support relationships.

- **[P1, fixed] Opening a support set closed the previous one.** Expansion previously depended on the single graph-focus ID. An independent collection now tracks expanded sets. Each header toggles only its own content; the compact sticky control expands or collapses all sets. Switching DCs clears stale expansion state.
- **[P2, prevented] Reading several alternatives could imply that their members form one joint support set.** AND and OR grouping remains explicit. Bulk expansion preserves the current graph focus. A separate graph icon focuses one exact set without collapsing other content; expanded alternatives are never treated as a new combined support set.
- Returning from an original-evidence reader preserves all open sets and the DC anchor. Inspecting an EC already visible in an expanded set reveals that existing text instead of duplicating it in candidates.

Evidence opened and compared:

| Artifact | State and dimensions |
| --- | --- |
| `qa/native-multiset-before.png` | DC-15, only Set 2 open before the correction; 1710 × 803 |
| `qa/native-multiset-all-open.png` | DC-15, all four alternatives expanded, Set 2 graph focus preserved; 1710 × 803 |
| `qa/native-multiset-comparison.png` | Before above / after below; 1710 × 1606 |
| `qa/native-multiset-focus-comparison.png` | Native-density review crops, before left / after right; 1690 × 400 |
| `qa/native-multiset-reference-after.png` | The author's DC-04 example, all four singleton sets expanded; 1710 × 803 |
| `qa/native-multiset-narrow.png` | Expanded review and bulk control at 430 × 900 |

Individual capture sizes match CSS viewports at `deviceScaleFactor: 1`. No density normalization was required. The before/after states intentionally differ in expansion; the graph focus remains on the same set. The inspector stays scrollable, so expanded content does not need to fit in one viewport. The final DC-04 capture visually confirms the first two open sets; all four expanded IDs were also verified in the DOM.

Fidelity pass: typefaces, canonical content, relationship colors, and four-column geometry are unchanged. Existing Phosphor icons supply the compact focus and bulk controls. Spacing accommodates the new control row without clipping narrow layouts; scroll padding keeps revealed content below that row. Only the necessary bulk-action copy is added.

`npm run test:multiset` and `qa/native-multiset-check.json` verify independent toggles, bulk toggles, exact graph focus, separate AND/OR groups, full EC text, reader return, keyboard activation, narrow layout, and resetting state across DCs. The focused-review, passage, native, and synthetic browser suites also passed sequentially without runtime errors. The final production build and four hosting tests passed. Adapter, graph-model semantics, and saved artifacts are unchanged in this correction.

## Previous correction: unified source interaction

The author identified inconsistent single/shared passage highlighting and rejected the additional top chooser. The supplied screenshots are the behavioral reference; existing four-column geometry and the bottom review remain the visual reference.

- **[P1, fixed] A shared passage did not highlight its DCs until the user chose one.** Hover now highlights all mapped DCs and their bounded paths; click pins that group. Single/shared passages use the same blue treatment. Hover exit restores the prior group or individual review, including its selected support set.
- **[P2, fixed] A second detail surface displaced the graph.** Removed the top chooser and source instruction tooltip. Compact DC switches live inside the existing bottom review header. The current switch controls only its own canonical text, outcome, and support sets; group highlighting does not merge assessments.
- The first browser color comparison sampled an unfinished CSS transition. The check now waits for the settled state; no separate single/shared color styles were introduced.

Evidence opened and compared:

| Artifact | State and dimensions |
| --- | --- |
| `qa/native-passage-before.png` | Earlier top chooser after a shared-passage click; 1710 × 803 |
| `qa/native-passage-pinned.png` | All mapped DCs pinned, no top chooser; 1710 × 803 |
| `qa/native-passage-comparison.png` | Before above / after below; 1710 × 1606 |
| `qa/native-passage-focus-comparison.png` | Single hover left / shared hover right, source and DC regions; 1560 × 400 |
| `qa/native-passage-review.png` | Existing bottom review with compact DC switches; 1710 × 803 |
| `qa/native-passage-narrow.png` | Stacked bottom review and usable switches; 430 × 900 |

Captures use CSS viewports matching their individual image sizes and `deviceScaleFactor: 1`. No density normalization was required; comparison crops remain at native size. The before/after full views intentionally differ in chooser presence, which is the correction being reviewed. The focused comparison uses two distinct passages to verify consistent treatment, not identical text or identical relationship counts.

Fidelity pass: local typefaces, source reading size, graph spacing, icons, and base colors are unchanged. All mapped DCs receive the same active border. Source content stays verbatim, ordinary/green relationship meanings remain intact, and the removed tooltip/chooser copy is replaced by layout and selected-state controls inside the bottom panel. The narrow header wraps rather than clipping its controls.

`npm run test:passage` and `qa/native-passage-check.json` verify single/shared hover, all mapped DCs, no source tooltip or top chooser, no graph displacement, pinned restoration, bottom-only details, individual text/support-set fidelity, passage navigation, reader return, filtered hover restoration, keyboard activation, and narrow switch access. Existing synthetic, native, and focused-review regressions also pass without captured runtime errors. Seven adapter tests pass. `verify:native` refreshed the artifact report because the graph model gained the bounded trace-union helper; saved case counts and all 12 consumed files still verify.

## Scope and source

The author's four-column sketch, complete-disclosure correction, and latest direction to reduce secondary labels define the target. This iteration adds focused single-DC evidence review and continuous DC navigation while preserving the saved relationship semantics. This is engineering and visual QA for one saved case plus synthetic fixtures, not participant usability evaluation, WCAG certification, or assessment-accuracy validation.

- Source visual: `qa/reference.png`, the author's candidate/support sketch, 1710 × 803 pixels.
- Before refinement: `qa/native-before-refinement.png`, 1710 × 803 pixels.
- Final overview: `qa/native-refined-overview.png`, 1710 × 803 pixels.
- Before/after full-view comparison: `qa/native-refinement-comparison.png`, 1710 × 1606 pixels; before above, after below.
- Sketch/current full-view comparison: `qa/native-refined-reference-comparison.png`, 1710 × 1606 pixels; sketch above, current below.
- Focused evidence-card comparison: `qa/native-refined-card-comparison.png`, 720 × 240 pixels; before left, after right, cropped at native density.
- Implementation: `http://localhost:4173/`, captured through Chrome's native DevTools Protocol. Available tools expose opening the in-app browser, but no in-app capture/interaction surface. No Playwright was used.
- Comparison viewport: 1710 × 803 CSS pixels, `deviceScaleFactor: 1`. No density normalization was necessary. The chat viewer may resize combined images; source files retain their native dimensions.
- Before/after overview state: the same saved case, no selection, all relationships enabled, zoom 100%, and lists at the beginning. The sketch defines topology, not native inventory size or exact typefaces.

## Findings and iteration history

1. **[P2, fixed] Redundant default copy competed with source reading.** The before capture repeats titles, company/year, column numbers, evidence metadata, and usage instructions. Removed duplicate workspace/source headings, step numbers, paper header/footer, evidence metadata rows, persistent tutorial, and empty detail panel. Filters, metadata, shortcuts, and help are contextual. Original content, core relationship meanings, counts, and accessible names remain. Evidence: before/after full-view comparison.
2. **[P1, fixed] Related evidence inspection replaced the DC under review.** The earlier inspector exposed support mainly as IDs and linked away to ECs. Full set/candidate evidence now opens within the anchored DC review; the original-evidence reader preserves DC, set, scroll, and return focus. Explicit trace controls change the anchor. The focused browser suite verifies this behavior against saved text.
3. **[P2, fixed] Inspecting an expanded support member repeated its full text in candidates.** Inspection now reveals the already visible set member. Candidate expansion is used when the requested EC is not in the open set. An expanded set header also omits repeated member IDs. The focused browser suite checks that the duplicate candidate list remains closed.
4. **[P2, fixed] A compact evidence preview clipped a distinguishing accounting-boundary qualifier.** The first focused comparison showed the qualifier truncated after increasing reading size. Previews now abbreviate the repeated phrase “greenhouse gas” to “GHG” and allow three lines. The original title remains complete in accessible names, tooltips, and the reader. The final focused comparison shows the accounting-boundary qualifier intact, with secondary metadata removed. The final overview and support captures were also reinspected.
5. **[P2, fixed] Filter dismissal could leave focus on a removed control.** Escape restores focus to the filter trigger without clearing the pinned review. Outside pointer activation dismisses the menu. The focused browser suite checks focus restoration and anchor preservation.

Earlier findings are retained in `design-qa-2026-10-22.md`. Its historical screenshot filenames may have been refreshed by subsequent regression runs. `native-before-refinement.png` preserves the pre-change overview for this iteration.

## Required fidelity surfaces

| Surface | Review and disposition |
| --- | --- |
| Fonts and typography | Existing local DM Sans and Libre Baskerville remain. Source prose is larger in the graph; canonical review text has readable line height. Claim previews remain compact. Distinguishing evidence-title content takes priority over secondary metadata. |
| Spacing and layout | Four-column order, original reader, nodes, and evidence inventory remain. Removing repeated chrome gives more height to the graph. A shared review header identifies the anchor and position; the body groups DC/diagnosis beside evidence. Narrow review layouts stack these regions. |
| Colors and tokens | Neutral candidates, green support membership, blue interaction focus, and amber unsupported markers preserve their meanings. AND/OR and outcome text supplement color. This is not a global contrast audit. |
| Images and assets | Existing Phosphor icons supply controls; D3 draws actual relationships. No decorative images or flattened screenshot controls were introduced. |
| Copy and content | Original source text, canonical EC/DC text, saved rationale, and memberships remain unchanged. Secondary explanations appear in help/source records. UI is English. Saved-assessment or illustrative-data labeling remains visible. |

## Validation evidence

- `npm run test:review`: complete joint EC texts, exact alternative sets, source fidelity and return context, graph-EC inspection, explicit reverse tracing, diagnosis/candidate comparison, previous/next boundaries, unsupported queue, filter dismissal, and named buttons in Chrome's accessibility tree.
- `npm run test:browser`: synthetic original paragraphs, mapping, hover restoration, exact support focus, reverse tracing, unused EC, empty candidates, readers, filters, Escape, zoom, and responsive reachability.
- `npm run test:native-browser`: real inventories, source table, joint/inferred alternatives, saved diagnosis, reverse tracing, shared passages, full readers, and responsive layouts.
- `npm run test:adapter`: seven failure-oriented adapter/mapping tests passed. The adapter is unchanged. The graph model now combines existing bounded DC traces for a shared passage; recorded assessments remain separate.
- `npm run build` and `npm run test:sites`: production packaging and the four existing hosting checks.
- Reports: `qa/native-review-check.json`, `qa/browser-check.json`, and `qa/native-browser-check.json`. Native screenshots and reports remain local and Git-ignored.

Browser suites run sequentially. Tested viewports include 1710 × 1000, 1710 × 803, 1440 × 900, and 430 × 900. Focused-review checks cover overview/open review at desktop and narrow widths, keyboard activation, reader return focus, and accessible button names. Completed runs captured no runtime errors.

## Limits

- Participant task testing has not been conducted. Discoverability of compact controls needs evaluation with intended users.
- Full screen-reader tasks, a complete contrast audit, and high text-enlargement validation remain pending. The tested behavior is narrower than WCAG conformance.
- Only one real case is connected; catalog browsing and substantially larger inventories require separate validation.
- The graph retains horizontal scrolling on narrow screens. Focused review and full readers fit the viewport; a dedicated mobile graph workflow is outside this change.
- Saved automated assessments describe support within supplied evidence; this work does not establish human validation or external truth.

## Implementation checklist

- [x] Preserve four columns and the complete original disclosure.
- [x] Reduce secondary labels through contextual controls and grouping.
- [x] Preserve exact candidate/support semantics and AND/OR membership.
- [x] Read full EC/source content while retaining the DC anchor.
- [x] Provide explicit reverse tracing, previous/next, and unsupported filtering.
- [x] Check desktop/narrow layouts and named keyboard controls.
- [x] Inspect final post-fix comparisons and record the passing final build result.
