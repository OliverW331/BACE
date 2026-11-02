# BACE Evidence Explorer: Product Baseline

Date: 2026-10-23  
Version: 1.4
Status: Product target and development baseline established at the author's request. Requirements below are targets, not a claim that all work is complete.

This document governs future product decisions for the [local prototype](../../prototypes/bace-explorer/README.md). It preserves the author's four-column sketch, bidirectional interaction, candidate/support line meanings, and complete original disclosure reader. It supersedes the screen directions in [v1](bace_interaction_design.md) and [v2](bace_interaction_design_v2.md). The bottom review inspector is the current design choice and remains subject to task-based evaluation. New author instructions take precedence.

## 1. Final goal

Build a readable, interactive evidence-review workspace in which a user can start from disclosure text or supplied evidence and understand the recorded BACE assessment without losing the original context.

A user should be able to answer:

1. What does the complete generated disclosure say, and which DCs were extracted from a passage?
2. Which supplied evidence produced an EC, and which ECs became candidates for a particular DC?
3. Which complete evidence-claim sets were accepted as supporting that DC, and was the saved support direct or inferred?
4. If a DC was unsupported, what diagnosis and rationale were recorded, and what candidates and source evidence can be inspected alongside that result?
5. Starting from an evidence record, which ECs and disclosure claims are connected to it?

The product presents support within the supplied evidence. It does not establish external truth, legal compliance, or independent evaluator accuracy. Artifact verification establishes consistency with saved inputs and outputs; it does not establish that a saved assessment is correct.

Initial audience: the author and research collaborators reviewing saved BACE cases. The first release is desktop-first and local. A complete single-case review journey is the release boundary; verified multi-case browsing is the subsequent extension.

## 2. Intended interface and visual result

The main workspace has exactly four semantic columns:

**Generated disclosure | Disclosure claims | Evidence claims | Evidence list**

| Surface | Intended result |
| --- | --- |
| Generated disclosure | Complete original document in natural reading order, including headings and tables. Exact mapped passages can be highlighted inline. Expand to a comfortable reading view without discarding the active review. |
| Disclosure claims | Compact, identifiable DC nodes with a short preview and a small assessment indicator. Complete canonical wording is available in the review inspector. |
| Evidence claims | Compact EC nodes showing distinguishable content. Complete canonical wording and source references are available on demand. |
| Evidence list | Supplied evidence records with concise titles and available source metadata. Each opens its full original supplied text. |
| Relationship canvas | Visible source links and DC–EC candidate/support relationships. Selecting an item emphasizes its bounded trace and reduces unrelated visual competition. |
| Contextual review inspector | Below the graph, show the active DC, support sets or unsupported diagnosis, and the currently inspected evidence. Full-text readers can expand beyond this space. |

The author selected Carbon Studio, the third displayed concept (Canva media MAHY0v9kUAc), on 2026-10-23. Use charcoal neutral surfaces, soft white sans-serif text, blue selection, green support membership, and amber diagnosis. Apply these semantic tokens to the whole application, including full readers, source tables, popovers, and support-set details. Keep borders restrained and original text readable while a trace is active. Do not turn the default screen into a simultaneous display of every rationale, full EC text, metadata field, and diagnostic category.

The neural-network sketch defines the layered topology and interaction concept. It does not imply neural computation, edge weights, or a need for continuously animated connections. Support sets and diagnosis details do not become additional graph columns.

### Relationship language

| Visual treatment | Meaning and constraint |
| --- | --- |
| Neutral middle line | Candidate relationship for that DC–EC pair. It does not, by itself, mean unassessed, rejected, contradictory, or unsupported. |
| Green middle line | Membership in at least one accepted support set for that DC. It does not establish that this EC is sufficient alone. In a selected-set view, emphasize only that set's exact membership. |
| Light outer source line | Saved extraction/provenance relationship between a source and a claim. It does not encode support. |
| Blue outline or emphasis | Interaction focus or selection. It must not erase the meaning of a green support line. |
| Amber DC marker and text | Recorded unsupported result, with diagnosis available in the inspector. Do not apply a DC-level diagnosis to each candidate edge. |

Within one support set, all listed members are required together (**AND**). Different accepted sets are alternatives (**OR**). Preserve the saved direct/inferred type of each set. Show these meanings in text as well as color.

Support sets expand independently and can all remain open for comparison. Provide a compact Expand all / Collapse all control. Expanded content and graph focus are separate states: opening one set focuses it while retaining other open sets; bulk expansion preserves current focus. A set's graph control changes focus without changing open content. Closing the focused set or collapsing all returns the graph to the DC's candidates. Never interpret several open alternatives as one combined AND group.

Bidirectional means users can navigate and highlight from either side. It does not make logical support symmetric or turn EC-to-DC support into DC-to-EC support.

## 3. Required review journeys

| Journey | User action | Required outcome |
| --- | --- | --- |
| Read and locate | Read a passage, then select it or a DC | Hover highlights every mapped DC with the same treatment for single/shared passages. Click pins the group; compact DC switches in the existing bottom review expose each claim's details. |
| Review support | Pin a DC, then select an accepted set | Keep the DC wording visible while showing all required EC full texts, set type, and links to original evidence. Switching alternatives does not merge their members. |
| Review unsupportedness | Pin an unsupported DC | Show the saved diagnosis and unedited rationale beside reachable candidate full texts and source evidence. Clearly distinguish no candidates from candidates with no accepted support set. |
| Trace backwards | Select an evidence record or EC | Reveal the associated ECs, DCs, and original disclosure spans without recursively adding unrelated co-candidates. |
| Review continuously | Move to previous/next DC or use an unsupported filter | Follow a stable, explained order and retain a clear current position and active filter. Filtering changes the view, not the saved assessment. |

In a pinned DC review, opening an EC or its source must preserve the DC as the review anchor. Offer an explicit action to change the anchor when the user wants to start a reverse review. Closing an expanded reader restores the selection, active support set, filters, and relevant scroll context.

Shared passages do not create a separate chooser above the graph or an instructional tooltip over source text. All claim details stay in the bottom review. The current claim's switch is visibly selected; choosing another switch or navigating within the passage focuses that DC. Combined path highlighting is navigation only: each DC retains its own support sets, outcome, and diagnosis.

Diagnosis is explained locally: a small marker identifies the DC, and the inspector reveals the saved category, rationale, candidate context, and original evidence. Do not add a permanent red network of presumed failure reasons. Do not invent pair-specific rejection reasons or granular text alignments that the artifacts do not contain.

## 4. Interaction and accessibility principles

**Author direction, 2026-10-23:** Reduce secondary labels and unnecessary information. Express structure through layout, grouping, spacing, and interaction whenever those can carry the meaning. Remove duplicate titles, column step numbers, repeated card metadata, and persistent operation tutorials from the default view. Keep original source content, essential scientific distinctions, discoverable controls, and accessible names. Put supplementary explanations and metadata in contextual disclosure or help; do not replace necessary meaning with unexplained icons.

1. **Reading comes first.** Original source text is independent of canonical claims. Preserve paragraphs, tables, and copyable text; do not reconstruct a source by concatenating DCs. Wide readers provide comfortable line lengths and larger text.
2. **Reveal detail progressively.** The overview explains structure; a focused review explains one result. Short previews never replace access to complete canonical wording.
3. **Keep the review anchor stable.** Hover is a temporary preview. Click or keyboard activation pins a selection. Hover exit restores the pinned state. Inspecting related evidence does not silently replace the DC being reviewed.
4. **Keep the map predictable.** Avoid unnecessary node reordering, automatic zoom, and broad transitive highlighting. Explicit filtering or case changes may change layout; preserve context where meaningful.
5. **Make hidden content discoverable.** Show total/filtered counts and clear access to remaining items. Offscreen edges must not appear attached to unrelated visible nodes. A missing rendered edge must not be presented as an absent saved relationship.
6. **Do not depend on color or hover.** Text labels, icons, a support-set list, and an accessible relationship list convey the same meanings. All core tasks need keyboard-accessible controls, visible focus, sensible focus restoration, and reachable full text.
7. **Support reading adaptations.** Target WCAG 2.2 AA for the delivered scope: check contrast, keyboard operation, focus, text enlargement, and dialog behavior. Respect reduced motion. Verify with automated checks and manual tasks before claiming conformance.
8. **Treat narrow layouts deliberately.** Desktop is the primary graph workspace. On narrow screens, keep controls and full-text reading usable, confine necessary horizontal scrolling to the graph, and retain an accessible list route through relationships.

## 5. Data and engineering principles

| Principle | Development rule |
| --- | --- |
| Saved results are authoritative | Read existing artifacts through a local, read-only adapter. Do not rerun experiments, alter model settings/prompts, or modify frozen environments and outputs to make the UI work. |
| Preserve semantics | Keep source text, canonical claims, candidate membership, support-set boundaries/types, and diagnosis wording intact. Display excerpts and aliases are presentation fields, not replacements for saved data. |
| Preserve uncertainty | Missing, incomplete, invalid, ambiguous, unlocated, and unsupported are distinct states. Never turn missing assessment data into an unsupported result or guess a source location. |
| Verify before displaying | Validate identities, artifact integrity, references, assessment completeness, support/candidate consistency, and source mappings. Surface a clear load error when the selected data contract fails. |
| Keep provenance inspectable | Preserve native identifiers, source records, and exact verified spans, including overlaps and multiple passages per DC. Explain display aliases and distinguish case completion from run completion. |
| Separate responsibilities | Keep artifact adapters, the normalized graph model, interaction state, and rendered components separate. Reuse the existing React/D3 prototype unless a concrete limitation warrants a change. |
| Model state explicitly | Separate pinned review anchor, temporary hover, expanded support sets, graph-focused support set, inspected evidence, filters, and reader state. Changes to one must not accidentally reset the others. Case switching must not retain stale references. |
| Keep behavior deterministic | Stable IDs, reproducible ordering, and bounded trace rules should yield the same result for the same saved case and action. Filters affect visibility only. |
| Keep real material local | Continue using the allowlisted runtime API. Do not bundle native case material into a published build or upload it to design tools. Use explicitly labeled synthetic data for externally shared examples. |
| Test meaningful risks | Test data fidelity, group logic, trace boundaries, failure states, context preservation, and complete user journeys. Use browser checks for interactions and layout; avoid tests that merely duplicate implementation details. |

Empty candidates, unused ECs, overlapping source spans, unlocated mappings, long claims, many support alternatives, and table-bearing documents are required design cases. Add larger real inventories only with explicit performance and usability checks; do not silently drop saved items to simplify the graph.

## 6. Release scope and current state

Status below describes the inspected implementation on 2026-10-23. Previous [design QA](../../prototypes/bace-explorer/design-qa.md) passed its documented engineering scope; it does not establish completion of the targets added here.

| Capability | Current state | First-release requirement |
| --- | --- | --- |
| Four-column graph and complete disclosure reader | Implemented and browser-checked | Preserve and maintain |
| Bidirectional tracing and candidate/support semantics | Implemented and browser-checked | Preserve; provide equivalent accessible relationship access |
| One verified saved case plus labeled synthetic example | Implemented and adapter-checked | Preserve read-only provenance and visible failure states |
| Joint and alternative support sets | Full EC text, exact group selection, AND/OR grouping, and pinned-DC source inspection implemented | Maintain and evaluate with intended users |
| Unsupported diagnosis | Saved rationale plus expandable candidate/source comparison implemented; DC remains pinned | Maintain and evaluate with intended users |
| Expanded source readers and overlapping mappings | Implemented and browser-checked | Preserve selection and extend review-context continuity |
| Previous/next DC and unsupported review queue | Implemented with stable ordering, position, and navigation boundaries | Maintain and evaluate with intended users |
| Reduced secondary information | Duplicate headings, step numbers, repeated card metadata, and persistent tutorials removed; contextual controls retain accessible names | Maintain essential meaning while evaluating discoverability |
| Accessibility | Some controls and responsive behavior checked | Complete scoped keyboard, contrast, text enlargement, and screen-reader task checks |
| Formative usability evaluation | Not conducted | Evaluate the three core tasks below with intended users; record findings and remaining limits |
| Verified multi-case catalog and case search | Beyond the first-release boundary | Subsequent milestone after single-case review acceptance |

Live generation, model evaluation, manual relabeling of research results, formal blinded annotation, collaborative accounts, cloud publication, and a full PDF annotation editor are outside this baseline. Aggregate dashboards are not part of the default reading workspace. These require separate product decisions.

## 7. Acceptance criteria

| ID | Acceptance condition | Evidence required |
| --- | --- | --- |
| A1 — Source fidelity | Original documents and canonical claims remain complete; exact source links preserve overlaps and explicitly handle unlocated mappings. | Adapter fixtures and browser checks against saved text, including a table and shared passages |
| A2 — Relationship fidelity | Candidates, accepted set members, required-together logic, alternatives, and direct/inferred labels match saved data. | Model checks plus a browser review of joint and alternative sets |
| A3 — Support review | Starting from a DC, a user can inspect a full accepted set and original source, then return with the DC and selected set retained. | Recorded end-to-end browser scenario and intended-user task observation |
| A4 — Diagnosis review | An unsupported DC exposes the exact saved diagnosis/rationale and candidate context, including the empty-candidate case, without invented edge-level explanations. | Saved-output comparison and end-to-end review scenario |
| A5 — Reverse review | Starting from evidence, the user can find its ECs, connected DCs, and disclosure passages; unrelated co-candidates do not contaminate the trace. | Fixture checks and intended-user task observation |
| A6 — Context and navigation | Hover restoration, reader close, set switching, previous/next, filtering, and case changes produce explicit, predictable state. | Browser interaction checks, including stale-state and empty-filter cases |
| A7 — Readability and access | Core tasks work by keyboard; full text, focus, and labels remain usable at tested sizes and text enlargement. An accessible list provides relationship parity. | Manual task checks, automated accessibility results, and documented viewport/text-scale coverage |
| A8 — Honest data boundaries | Missing/invalid data is visible; assessment absence is not diagnosed; native material remains local and excluded from production assets. | Adapter failure checks and transport/bundle checks |
| A9 — Usability evidence | Intended users can perform support review, diagnosis review, and reverse review, and explain the candidate/support distinction and AND/OR groups without being taught the answers. | A small formative study with task observations, completion/assistance records, misunderstandings, and resulting revisions |

For A9, plan an initial round with approximately 3–5 intended users; this is a proposed formative sample, not a completed study or a basis for population-level success claims. Record task time as an observation, not as an invented benchmark. Resolve observed blocking navigation issues and semantic misunderstandings, then recheck the affected tasks. Any untested criteria remain explicitly pending. Recruiting or contacting participants is a separate action, not authorized by this document.

Measure load and interaction responsiveness on declared hardware and case sizes before setting performance claims. Do not label a one-case prototype as scalable without testing larger inventories.

The release is accepted only when the criteria have recorded evidence and unresolved limitations are explicit. Passing a build, producing an attractive screenshot, or passing the earlier engineering QA alone does not establish product usability.

## 8. Development sequence and change control

1. **Specify the focused review states — implemented.** Separate the pinned DC, selected set, inspected EC/source, and return behavior. Use synthetic material in external tools.
2. **Complete one DC review — implemented.** Full support-set EC text and unsupported candidate comparison preserve the anchor. The four-column overview remains intact.
3. **Complete continuous review — implemented.** Previous/next and an unsupported filter retain a clear current position, with empty and boundary states.
4. **Verify the implementation.** Run relevant adapter/model/browser checks, inspect real browser renders, and complete the scoped accessibility checks. Record what was actually tested.
5. **Evaluate real tasks.** Conduct the planned formative review when participants are arranged; revise observed problems and recheck them. This is usability evaluation, not BACE assessment-accuracy validation.
6. **Extend the catalog.** Only after the single-case journey meets its criteria, expand verified case access and validate different inventory sizes and document shapes.

For each meaningful change, record the user task it improves, affected acceptance IDs, visible behavior, and verification evidence. Use Figma/FigJam when they clarify layout or state transitions; use the runnable React/D3 prototype to judge tracing, density, scrolling, and review continuity. Static artwork does not substitute for interaction testing.

Update this baseline when the author changes the product direction. Keep the prototype README factual about implemented behavior and the QA record factual about completed checks. Do not mark a target complete simply because it appears in this document.
