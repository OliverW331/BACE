# BACE style exploration

Date: 2026-10-23

Status: the author selected the third displayed concept, Carbon Studio (MAHY0v9kUAc), on 2026-10-23. Implementation and verification are recorded in the prototype's design-qa.md.

## Generated concepts

All three Canva jobs succeeded. Display order in the conversation is Graphite White, Warm Paper, then Carbon Studio. Each generated asset is 1712 x 1104 pixels; the connector returned 200 x 128 pixel inline previews.

| Direction | Palette and typography | Generated asset |
| --- | --- | --- |
| Graphite White | #F7F7F5 background, #FFFFFF surface, #242424 text; restrained sans-serif throughout | [Open generated image](https://www.canva.com/M/MAHY0g_WkLk?utm_source=OC-AaBlKrqBJJNF&utm_campaign=agent_connector_create_image_asset_opened) |
| Warm Paper | #F5F2EB background, #FFFEFA surface, #302E2A text; serif reading content with sans-serif controls | [Open generated image](https://www.canva.com/M/MAHY0odpXmg?utm_source=OC-AaBlKrqBJJNF&utm_campaign=agent_connector_create_image_asset_opened) |
| Carbon Studio | #18191B background, #222326 surface, #E9E9E7 text; clear sans-serif typography, subdued blue and green states | [Open generated image](https://www.canva.com/M/MAHY0v9kUAc?utm_source=OC-AaBlKrqBJJNF&utm_campaign=agent_connector_create_image_asset_opened) |

Review limit: the returned previews show the intended four-column structure, bottom inspector, and three palette directions. Fine text fidelity and exact edge membership cannot be verified at thumbnail size. The browser attempt to open the original Canva media viewer encountered its access challenge, so no full-resolution inspection is claimed. These are visual concepts, not verified interactive implementations.

Three directions: Graphite White, Warm Paper, and Carbon Studio. Each uses the same synthetic case, four-column topology, selected DC-01, and a single joint inferred support set. Green means support membership, neutral gray means candidate, blue means selection, and amber marks unsupported claims.

Generation provider: Canva, using the author's previously authorized fallback. Only the synthetic-demo screenshot was uploaded; no saved research artifacts were sent. The direct one-use upload endpoint returned HTTP 403; the connector's supported local-file import succeeded (media MAHY0hEAktE).

Reference: `prototypes/bace-explorer/qa/style-reference-demo.png`, 1710 x 1100 pixels. The capture was opened and visually inspected before generation. The reference has excess graph whitespace and a partially visible inspector; the brief explicitly requests fitting both in the concept image.

## Shared generation brief

Create one realistic, production-quality image of the BACE Evidence Explorer desktop web application. This is a UI style exploration, not a landing page or a presentation slide. Target canvas 1710 x 1100 pixels. Current date 2026-10-23; preserve the synthetic reporting years 2022/2023 below. All visible interface copy is English. Attachments show the CURRENT application using explicitly synthetic fixtures. Use the attachment as a hard reference for the four-column topology and product anatomy. Improve visual polish, balance, readable contrast and compact layout. Fit both the graph and the bottom inspector comfortably in this frame; remove the attachment's excessive blank space above the graph. No browser/device frame, perspective, decorative illustrations, large hero title, dashboard statistics, extra navigation, gradients or glowing lines.

HARD PRODUCT CONSTRAINTS: Four columns in this exact left-to-right order: Generated disclosure | Disclosure claims | Evidence claims | Evidence list. The left column is a complete readable original document in natural paragraphs, NEVER six separate numbered claim cards. Middle columns have compact rectangular claim nodes connected by thin curved lines. Original document maps into DCs; evidence documents map into ECs from the right. Middle neutral gray lines mean Candidate, green lines mean Support membership. Blue is reserved for selection and source highlighting; no wholesale green-tinted interface. Unsupported DCs have a tiny amber indicator; diagnosis belongs in the bottom inspector and NEVER on individual candidate edges. No fifth graph column. Keep original source readable when selected. Bottom review is the only detailed information area.

COMMON EXACT SYNTHETIC CONTENT for this and its sibling images: Small top bar: BACE, Evidence explorer, Illustrative data. Document: 'During 2023, Scope 1 emissions fell by 20% compared with 2022. All manufacturing sites used renewable electricity, with renewable sources accounting for 60% of the group’s purchased electricity.' Second paragraph: 'The group has committed to achieving net-zero emissions by 2030. Our solar programme drove the reduction in Scope 2 emissions.' Last paragraph: 'No environmental fines were received during the reporting year.'
DC nodes: DC-01 Lower Scope 1 emissions; DC-02 Renewables at all sites; DC-03 60% renewable electricity; DC-04 A net-zero commitment; DC-05 Solar drove the reduction; DC-06 No environmental fines.
EC nodes: EC-01 Scope 1 · 2022; EC-02 Scope 1 · 2023; EC-03 Pilot facility; EC-04 Renewable share; EC-05 Solar programme; EC-06 Scope 2 change; EC-07 Environmental fines; EC-08 Water withdrawal.
Evidence list: EV-01 Emissions inventory; EV-02 Energy programme; EV-03 Water data; EV-04 Compliance statement.
SELECTED STATE: DC-01 has blue selection border, the matching source sentence has a restrained blue text highlight, green middle curves reach EC-01 and EC-02, and one neutral gray candidate curve reaches EC-06. These three ECs link to EV-01. Other nodes remain legible but recede modestly. A tiny legend shows Candidate and Support membership.
BOTTOM INSPECTOR: Header DC-01, small green check and Supported, compact previous/next and close controls. Left full canonical claim: 'Scope 1 emissions decreased by 20% between 2022 and 2023.' Right has one expanded support set, small header 'Set 1 · Inferred', full member 'EC-01  Scope 1 emissions were 100,000 tCO2e in 2022.', a small AND separator, then 'EC-02  Scope 1 emissions were 80,000 tCO2e in 2023.' Small EV-01 links. This is a joint inferred support group, not two alternative proofs.

Design with grouping, alignment, spacing and typography before borders. Avoid nested cards and repeated secondary labels. Primary reading text 16–18 px, UI labels 13–14 px with strong legibility. No invented features. Preserve this exact use case across all directions.
