# BACE Storyboard v2

Date: 2026-10-22

Status: Three generated static concept frames. They illustrate one interface at different levels of detail, not competing visual options. Interactions described below are proposed behavior, not working controls.

## Design direction

The disclosure occupies the main surface. A selected claim opens a contextual inspector; deeper evidence inspection uses a dedicated trace view. Preserve comfortable typography, restrained status color, and visible routes back to the disclosure.

The frames were generated with Canva using synthetic data, following the author's explicit authorization. Each actual image is 1456 × 1088 pixels. The connector exposed thumbnail previews and Canva links; only those previews were visually inspected. Full-resolution typography, precise text fidelity, and interaction behavior have not been validated.

The first frame uses the earlier rejected concept as a negative layout reference. The second and third frames both use the new reading frame as their visual reference. Public reference-product images were not attached; the brief incorporates the researched principles recorded in [the v2 specification](bace_interaction_design_v2.md).

## Frames

| Frame | Screen state | Canva image |
| --- | --- | --- |
| Read | Disclosure with no inspector open | [Open generated image](https://www.canva.com/M/MAHYujRqKAk?utm_source=OC-AaBlKrqBJJNF&utm_campaign=agent_connector_create_image_asset_opened) |
| Inspect | Selected unsupported DC with diagnosis and candidate evidence | [Open generated image](https://www.canva.com/M/MAHYuo2rvGE?utm_source=OC-AaBlKrqBJJNF&utm_campaign=agent_connector_create_image_asset_opened) |
| Trace | A supported DC with two ECs required together | [Open generated image](https://www.canva.com/M/MAHYumNV1-g?utm_source=OC-AaBlKrqBJJNF&utm_campaign=agent_connector_create_image_asset_opened) |

## Proposed walkthrough

1. Open the Read frame. The reader sees the disclosure and a lightweight summary. No claim inventory or assessment sidebar occupies the screen by default.
2. Select the second sentence or activate `Review unsupported`. Open the Inspect state, keeping the disclosure visible and emphasizing its selected passage. Show the diagnosis and explanation before more detailed evidence records.
3. Close the inspector or navigate to the first claim, then activate `View trace`. Open the Trace state for that supported claim. The trace deliberately uses the other claim to cover the joint-support scenario; it is not the evidence path of the previously selected unsupported claim.
4. Activate `Back to disclosure` to return to the selected passage. Source inspection and extraction history remain available from the trace.

This storyboard samples both outcomes within one case. A future prototype should support the same Inspect and Trace transitions for either claim, including the unsupported claim's empty support result.

## Illustrative fixture

Company: Example Manufacturing. Reporting year: 2023. These are UI examples, not saved experiment results or independent evaluator findings.

### Supported claim

DC-01:

> Scope 1 emissions decreased by 20% between 2022 and 2023.

Candidate ECs:

- EC-01: Scope 1 emissions were 100,000 tCO2e in 2022.
- EC-02: Scope 1 emissions were 80,000 tCO2e in 2023.

The illustrative accepted support set is `{EC-01, EC-02}`, with inferred support. Both members are required together. The displayed reduction follows the synthetic values `(100000 - 80000) / 100000 = 0.20`; it is not a research statistic.

### Unsupported claim

DC-02:

> All manufacturing sites used renewable electricity in 2023.

Candidate EC-03:

> The pilot facility used renewable electricity in 2023.

Illustrative outcome: Unsupported. Accepted support sets: empty. Diagnosis: Factual boundary distortion.

Illustrative explanation:

> The evidence covers the pilot facility; the disclosure expands this to all manufacturing sites.

The numbers, outcomes, and explanation were specified for the visual fixture. They were not produced by running BACE.

## Handoff

- [Current interaction specification](bace_interaction_design_v2.md)
- [Exact generation prompts and reference media identifiers](bace_storyboard_v2_prompts.json)

Before implementation, inspect the full-size frames for comfortable reading and sufficient source context. Verify all rendered text against the fixture when converting the concepts into code. Preserve the complete support-set group and the distinction between candidate membership and accepted support.

The useful next evaluation is whether opening and closing details reduces effort while preserving access to the full trace. Static images alone do not establish that improvement.
