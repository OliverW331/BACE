# Prototype Instructions

## Product baseline

Follow [BACE Evidence Explorer: Product Baseline](../../docs/design/bace_product_baseline.md) for the product target, interaction semantics, development principles, and acceptance criteria. It supersedes the earlier v1/v2 layout proposals. New author instructions take precedence. Keep current implementation status separate from target requirements.

The focused single-DC review and continuous navigation are implemented: preserve the pinned DC while inspecting full support-set EC texts, candidates, and original evidence. Verify this behavior with `npm run test:review` when changing review state. Multi-case browsing follows single-case acceptance, including the still-pending usability and broader accessibility work. Do not interpret this roadmap as permission to rerun experiments, publish native material, or contact participants.

## BACE-specific decisions

- The author selected Carbon Studio (the third displayed concept, Canva media MAHY0v9kUAc). Use charcoal neutral surfaces, soft white sans-serif reading text, blue selection, green support membership, and amber diagnosis. Keep original documents legible during tracing; apply the palette consistently to readers, tables, menus, and review panels. Do not add decorative gradients or color the whole interface green.
- Reduce secondary labels and unnecessary visible information. Use alignment, grouping, spacing, selection, and disclosure interactions before adding explanatory copy. Keep essential relationship meanings, error states, original content, and accessible names. Move metadata and operation guidance to contextual details/help rather than repeating them on cards.
- Converse in Chinese; write UI, code, and documentation in English.
- The visual source is the author's four-column sketch: generated disclosure, DCs, ECs, evidence list. Preserve this order.
- The first column is the complete original generated disclosure for reading, with natural paragraphs and no numbered claim rows. Store it independently from the canonical DCs; map source spans to DCs for inline highlighting. Keep normal text readable during tracing. The second column contains the extracted DC nodes.
- Provide an expanded document reading view without replacing the graph's current selection.
- Interactions work bidirectionally. Ordinary middle links are candidates; green middle links indicate membership in accepted support sets.
- Do not insert support-set nodes as a fifth column. Show complete support groups in the selected DC's details.
- Support sets expand independently; opening one must not close another. Provide a compact Expand all / Collapse all control. Keep expanded content separate from the one set focused in the graph; bulk expansion must not merge alternative sets into a joint support group. Preserve all open sets when returning from evidence reading.
- Unsupported diagnosis is an exploratory bottom detail panel with a small marker on its DC, not a diagnosis on individual candidate edges.
- Use explicitly illustrative fixtures until real saved artifacts are deliberately connected. Never rerun experiments or change frozen BACE environments for this prototype.
- The author authorized loading an existing real BACE case. Serve only the allowlisted completed case through the local read-only adapter, verify consumed stage receipts, preserve original text and saved outcomes, and distinguish case completion from overall run completion. Keep native data and screenshots out of production bundles and Git.
- Source spans can overlap and a DC can have several source quotes. Use the same highlight behavior for single/shared passages: hover previews all mapped DCs; click pins the group. Keep all claim details in the existing bottom review, with compact DC switches for shared passages. Do not add a top chooser or source-text instruction tooltip. Group highlighting never merges assessments or support sets. Never guess a location or infer unsupported from missing assessment data.

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.
