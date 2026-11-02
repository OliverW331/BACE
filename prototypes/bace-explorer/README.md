# BACE Evidence Explorer

A local interactive explorer following the author's four-column layout:

**Generated disclosure — Disclosure claims — Evidence claims — Evidence list**

The [product baseline](../../docs/design/bace_product_baseline.md) defines the final goal, intended experience, development principles, and release acceptance criteria. This README describes current behavior; baseline targets marked partial or planned are not yet delivered.

The default local preview loads one completed saved BACE case: **Intesa Sanpaolo, 2020, E1-6**. The case selector also offers the synthetic example. Saved automated assessments are presented as recorded, not as independently verified truth or human validation. The overall main run remains marked `incomplete`; this selected case has completed stages.

## Reading and tracing

- Read the complete generated disclosure, including its original table. The original Markdown string is preserved independently of the canonical DCs. Expand the document for a wider reading view.
- Hover to preview a connection; click to pin it and open the review. Hover alone never opens or replaces the review panel. Escape closes an open filter menu/reader first; otherwise it clears the selection. Reset clears the view and filters.
- Hover source text to highlight all mapped DCs; click to pin the passage. Single/shared passages use the same highlight treatment. All details stay in the bottom review: compact DC switches expose each mapped claim, with previous/next navigation within a shared passage. Selecting a switch focuses that DC. There is no top chooser or source-text instruction tooltip. Click a graph DC to reveal its verified source spans.
- Start at either side: selecting an EC or evidence card shows its associated DCs without recursively including unrelated co-candidates.
- Normal middle lines are candidate relationships. Green lines indicate membership in accepted support sets. Selection uses blue emphasis; green support lines retain their meaning.
- Expand support sets independently to compare complete EC texts. Opening a set focuses its graph membership without closing other sets. Expand all preserves graph focus; Collapse all closes the content and returns to all candidates. A set's graph icon changes focus independently of expansion. AND joins required members; OR separates alternatives. Each set retains its direct/inferred type.
- Unsupported DCs have an amber marker. Their review displays the saved diagnosis and unedited rationale alongside expandable candidate ECs. No diagnosis is assigned to individual candidate edges.
- Open original evidence from an EC's source button. Closing the reader preserves the pinned DC, all open sets, graph-focused set, inspected candidate, scroll position, and return focus. Clicking a connected graph EC inspects it while retaining the DC; an explicit Trace from action starts a reverse review. A set member already visible in full is not duplicated in the candidate list.
- Previous/next arrows move through the stable DC order. The warning-icon control beside Disclosure claims filters to unsupported claims and limits navigation to that queue. The review header shows its current position.
- Related only and Support only are in the graph filter menu. Lists scroll independently and retain full inventory counts. Offscreen links are not drawn through unrelated visible nodes.
- Select evidence and use Read evidence to inspect the complete supplied text. The contextual Source record control exposes original identifiers and available source metadata.
- Display excerpts omit repeated company/source lead-ins and abbreviate “greenhouse gas” as “GHG.” EC numeric previews are literal excerpts from the saved claim. Complete canonical texts remain unedited in details and hover labels.

The default workspace omits repeated titles, column step numbers, per-card year/type/count labels, and the empty instructional panel. Core line meanings remain in the legend. Help, metadata, example shortcuts, and filters appear on demand. Controls retain accessible names and contextual titles; typography, position, grouping, and state carry the remaining structure.

The selected Carbon Studio theme uses charcoal surfaces and soft white DM Sans text throughout, including original readers, tables, popovers, and the review inspector. Blue marks selection, green marks support membership, and amber marks unsupported results. Candidate lines stay neutral during selection. Unrelated nodes remain readable. Shared CSS tokens control the palette and native browser controls use a dark color scheme.

## Saved-case adapter

`server/native-case.mjs` implements a local, read-only Vite endpoint. It reads only the allowlisted case and verifies:

1. Membership in the saved run manifest and a complete case state with all BACE stages.
2. The freeze-file digest and global generation-input digest, with an exact comparison of the selected case input.
3. Consumed generation, deduplication, candidate, support, and diagnosis artifact hashes against saved stage receipts.
4. Generated/evidence text hashes, case identities, unique IDs, candidate references, nonempty valid support sets, and the exact unsupported/diagnosis partition.
5. Saved source quotes at their Unicode code-point offsets, independently checking literal uniqueness before conversion to browser UTF-16 offsets.

Missing candidate/support assessments fail loading; they never become unsupported by default. Ambiguous or unverifiable source spans remain unlocated. No fuzzy matching, new evaluation, rewritten rationale, or inferred diagnosis is used.

Native IDs remain available alongside display aliases. DC aliases follow earliest verified source position, with native ID as a deterministic tie-breaker; EC aliases follow the saved EC inventory and evidence aliases follow the supplied evidence order. Alias numbers are not original experiment identifiers.

| Route | Result |
| --- | --- |
| `GET /api/bace/cases` | Allowlisted local case catalog |
| `GET /api/bace/cases/<case-id>` | Verified, normalized case with provenance |
| Any write request | `405` |
| Unknown case | `404` |
| Verification failure | `422`; a visible error preserves the last successfully loaded view |

The native API is available only through local loopback access in development/preview. Native text is loaded at runtime and is not included in the production bundle. Native screenshots and reports (`qa/native-*`) are ignored by Git. Raw provider responses, encrypted response fields, generation prompts, and credentials are never returned by the adapter. Nothing is uploaded or published.

## Run and verify

```sh
npm install
npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
npm run verify:native
npm run test:adapter
npm run build
npm run test:sites
```

The browser checks require Chrome's native debugging endpoint on port 9334 and the preview on port 4173:

```sh
npm run test:browser
npm run test:native-browser
npm run test:review
npm run test:passage
npm run test:multiset
npm run test:theme
```

The first suite checks the synthetic case at `?case=demo`; the second checks the real case. The third checks focused-review continuity, complete EC texts, exact alternatives, candidate/source comparison, keyboard activation, focus restoration, and the unsupported navigation queue. The passage suite checks unified single/shared highlighting, group restoration, bottom-only details, per-DC switching, filtered preview, keyboard operation, and narrow layouts. The multiset suite verifies independent expansion and graph focus. The theme suite samples computed text contrast and dark surfaces, candidate/support colors, and narrow review access; it is not a full accessibility audit. Run browser suites sequentially against Chrome's native debugging endpoint.

`qa/native-case-audit.json` records input hashes, adapter/model code hashes, count definitions, and results. `qa/native-browser-check.json` and `qa/native-review-check.json` record browser checks and viewports; `qa/native-transport-check.json` records read-only routing and production-bundle isolation checks. Visual comparison and limitations are documented in `design-qa.md`.

## Files and scope

- `server/native-case.mjs`: allowlist, source verification, normalized data adapter, and local API.
- `src/data.js`: original synthetic fixture.
- `src/graph-model.js`: dataset-independent graph and overlapping source-span segmentation.
- `src/Document.jsx`: safe Markdown/table rendering and exact inline source mappings.
- `src/App.jsx`: case loading, graph, reading views, and inspectors.
- `src/Review.jsx`: anchored claim review, expandable support/candidate evidence, source records, and review navigation.
- `tests/native-adapter.test.mjs`: failure-oriented adapter and mapping tests.

This is one engineering example selected for manageable inventory size and mixed saved outcomes, not a representative research sample. The adapter verifies consumed artifacts and source locations; it does not re-audit every extraction/model-call history or certify assessment correctness. Broader case browsing, larger inventories, richer PDF viewing, and production accessibility require further work. Bidirectional navigation does not make logical support symmetric.
