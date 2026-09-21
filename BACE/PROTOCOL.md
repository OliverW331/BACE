# Frozen experiment protocol

## Population and stratified selection

The source company register contains 600 companies. A company is eligible if its latest SICS sector at or before 2023 is known, at least one valid nonempty CSV metric exists in every source year 2015–2023, and at least one local file with a PDF header exists in every source year 2015–2022. Full parsing subsequently checks that every required PDF source year provides narrative evidence. There are 250 eligible companies.

These rules precede generation and evaluation. They do not require a particular task metric, favorable report contents, a generation score or agreement between judges. The sampling frame is the complete-source subpopulation; it is not a representative sample of all 600 companies without further assumptions about missingness.

Allocate one company to each eligible sector, then allocate the remaining 19 slots by Hamilton largest remainders proportional to eligible sector size minus one, with alphabetical ties. This guarantees cross-sector representation while respecting stratum capacities. Sort company IDs, derive a sector-specific random seed as the integer SHA256 of `20260916:<sector>`, and shuffle with Python `random.Random`. Select each quota's first companies and retain the remaining order as reserves. Python's version is frozen with the executable environment.

| SICS sector | Companies |
|---|---:|
| Consumer Goods | 3 |
| Extractives & Minerals Processing | 2 |
| Financials | 5 |
| Food & Beverage | 2 |
| Health Care | 2 |
| Infrastructure | 3 |
| Renewable Resources & Alternative Energy | 1 |
| Resource Transformation | 5 |
| Services | 2 |
| Technology & Communications | 3 |
| Transportation | 2 |

The actual names, IDs, register country values and sectors are in `evidence/sample/selected_companies.csv`. `sample.json` records eligible counts, quotas, source hashes, the seed and reserve order. `sampling_frame.json` records inclusion/exclusion conditions for all 600 companies. Country values are retained from the source register and are not used for allocation.

Absent metrics are not imputed. Missing retrieval strata are not filled by increasing another stratum's quota. A source-level failure is recorded; only a company with a wholly unusable required source year may be replaced by its next prespecified same-sector reserve, before any generation. A failed pilot or unfavorable evaluator score never triggers replacement. No replacement has been made during the current draw.

## Tasks and years

Every selected company receives every task for every reporting year 2019–2023. Tasks are independent disclosure sections; generated text from one task is never evidence for another.

| Standard | Four tasks, using the 2023 ESRS edition |
|---|---|
| E1 | E1-1 transition plan; E1-3 actions and resources; E1-4 targets; E1-6 GHG emissions |
| S1 | S1-1 workforce policies; S1-4 workforce actions/resources; S1-5 workforce targets; S1-14 health and safety |
| G1 | G1-1 business conduct policies; G1-2 supplier relationships; G1-3 anti-corruption controls; G1-4 corruption/bribery incidents |

The prior E1 definitions and researched S1/G1 definitions are selected as a common frozen protocol. The 2026 ESRS revision is not silently mixed into these task IDs. All tasks have explicit multi-query retrieval bundles and the same shared generation instruction.

## Evidence and retrieval

For target year `t`, CSV source years are `t-4` through `t`, inclusive. PDF report years are `t-4` through `t-1`, inclusive. These are report-year boundaries, not publication-date cutoffs. A historical PDF may contain earlier measurements or future commitments; source text and labels preserve those distinctions.

Reuse the prior deterministic metric-card builder, PyMuPDF narrative extraction and pdfplumber table-row extraction. Narrative blocks follow the existing 40–250-word chunking rules. Entire eligible reports are processed; no task keywords or evaluator scores select PDF pages. Table markdown is excluded. Each card records the source file, source hash, company, year and stable evidence ID; PDF cards record page locations. CSV provenance points to the extracted source table and its stable metric key, not a falsely asserted PDF quotation. All 32 reports reused from the previous stage were also independently re-extracted from the current hashed PDFs: card IDs, text, source years and locations matched exactly. The existing PDF build report records this check on each reused source.

A pre-generation source-quality gate quarantines whole cards containing at least ten unmapped private-use/replacement glyphs that exceed 5% of non-whitespace characters, or more than 8191 cl100k_base tokens. This was prompted by two D’Ieteren 2018 narrative chunks whose font encoding produced over 10,000 tokens of unreadable glyphs. The PDF page itself remains readable; the original source PDF remains available. Apply the rule uniformly to all companies and tasks, retain excluded IDs and source locations, and recheck annual availability after exclusions. Do not truncate, guess character mappings or change company selection using scores. `quality_exclusions.json` records every affected card and source location.

Four independently verified Evonik 2023 CSV mappings are quarantined: eight alleged corruption cases mislabeled as confirmed incidents; twelve dismissed employees mislabeled as corruption incidents; three terminated general-compliance relationships mislabeled as corruption incidents; and approximately 90% of invoices settled within 60 days mislabeled as a 60-day mean. The source PDF pages 124 and 130 were checked in text and visually. No replacement values are invented. The shared source CSV remains unchanged. All other model-extracted metric cells remain subject to source-quality uncertainty.

Retrieval uses BM25 and normalized `text-embedding-3-large` vectors (3072 dimensions), 200 candidates per subquery/channel, two-level reciprocal rank fusion with `k=60`, and up to ten cards per evidence type. Presentation order is narrative, PDF table row, CSV metric. No reranker or type-deficit redistribution is used. Vectors are copied from the earlier build only when the exact embedding text hash matches and the model/dimension/prefix identity is compatible. New vectors and query vectors use the same deployment. The normalized matrix and evidence-ID row mapping form the exact cosine vector index. The inherited ranking function scores only the company/year candidate pool; an unused duplicate FAISS serialization is not retained.

All 1,800 query bundles, selected evidence records and generation prompts are prepared before the main run. They therefore require no additional retrieval requests at main-experiment startup.

## Generation and evaluations

Generation uses the configured Azure `gpt-5.6-sol` deployment, medium reasoning, no temperature parameter, 8192 maximum output tokens, and `store=false`. The prior configuration records model version `2026-07-09`; routing is frozen by deployment/endpoint hashes, and provider-returned identity is retained where available. Remote service immutability is not guaranteed by a client-side version label.

The shared prompt requests a professional 300–500-word disclosure based solely on supplied evidence. Use the first complete output in that range. Retry the same prompt when the provider response is incomplete or the word count is outside the range; retain rejected attempts. There is no selection on BACE or external scores. All model randomness and retry variation are retained as part of the execution record; reproducible inputs do not imply byte-identical future model responses.

BACE uses direct extraction v8, integrated identified-patch review v4 with operational definition v2, constrained atomicity review v2, then the prior semantic deduplication, candidate selection, support-set assessment and unsupported-diagnosis configurations. Native replies, compiled claim occurrences, source hashes and review lineage are retained. Completed direct extraction feeds review; failed stages cannot feed later stages.

RAGChecker 0.1.9/RefChecker 0.2.13 and RAGAS 0.4.3 run their native faithfulness metrics. They receive exactly the prompt-visible evidence and generated text through the checked common adapter. Reference answers are absent; reference-dependent metrics are not reported. Native prompts and claim denominators are retained. RAGChecker checks each evidence card and RAGAS checks its combined supplied contexts, consistent with their native methods. The Azure transport fixes the judge deployment and request settings without replacing native scoring.

BACE all-DC support rate is the primary support rate. Excluding non-disclosure statements is a separately labeled sensitivity metric. Evidence-claim coverage and inference rate retain explicit denominators. Framework macro averages and native claim-micro averages are both reported; differing claim decompositions do not establish evaluator accuracy.

The prior extraction repair did not establish universal production-quality extraction: some fidelity and atomicity defects remained. This protocol fixes the selected research evaluator and requires executable, auditable processing, while retaining extraction audits and subsequent human validation. Engineering readiness is not proof that all claims or evaluator decisions are correct.

## Pilot, failures and human materials

The engineering pilot contains exactly one case per task. In frozen task order, cycle through alphabetically ordered sectors and reporting years; choose companies in frozen ID order within each sector. This covers all twelve tasks, all eleven sectors and all five years without examining generated text or scores.

The same per-case orchestration is used for pilot and main. The parallel runtime revision uses 16 case workers, native request retries and up to three stage invocations. Generation precedes three independent concurrent branches: BACE, RAGChecker and RAGAS. BACE retains all data dependencies between its seven stages; EC/DC extraction and semantic deduplication run their independent jobs concurrently. A process lock prevents two runs from owning one case, and a thread lock serializes receipt updates from independent branches. Each case has one state file binding completed stages to their command, code and outputs. Interrupted native calls resume from existing records. Successful branches and stages are reused after verification. Failed cases remain excluded from a completed comparison until resolved.

Candidate selection, support assessment and unsupported diagnosis use up to eight claim workers per case. Global ceilings are 16 generation, 32 extraction/review, 32 deduplication, 64 candidate, 48 shared support/RAGChecker/RAGAS, and 32 diagnosis requests. A shared resource-and-endpoint gate honors provider `Retry-After`, halves effective capacity once per 429 cooldown, and gradually restores it after successful responses. These limits are local scheduling controls, not Azure quota claims. Request payloads and scoring remain unchanged. The parent stage alone appends native call records and materializes results in the original deterministic order. Request starts are paced and initial shared limits are four for generation/candidates and eight for other resources. The coordinator uses local ephemeral storage rather than NFS and retains only current resource state and live leases, not an audit history.

The original twelve-case pilot keeps its original execution identity. The verified freeze chain records the scheduling-only changes and allows reuse of its completed outputs. Native-response replay checks prompt, parameter, result and resume invariants; bounded live validation executes eight predetermined pilot claim jobs in each of three stages, for 24 job executions. This integration check generates no main-study disclosures and does not establish a full-study speedup. The previous interrupted main outputs were cleared at the user's request; the next main invocation starts all 1,800 cases from scratch using the retained frozen inputs.

The scheduler maintains only a bounded set of active cases. Ctrl+C/SIGTERM stops new submissions and terminates stage process groups, preserving saved outputs. The terminal uses eight fixed rows on an alternate screen and rotates four visible case rows through the active set. Final completion is reported only after frozen-input verification, result aggregation and human-material preparation succeed.

Human materials contain the full disclosure and its visible evidence, plus uniform samples of up to five DCs, two evidence cards and two disclosure paragraphs per case. Samples do not require every automated support class to exist. Each unit's inclusion probability is retained in the private coordinator manifest. Review sheets are blank and hide automated verdicts, scores, diagnoses and support paths. Source extraction review precedes target-claim review. Existing changed annotations cannot be overwritten. Preparing these materials does not constitute formal human annotation.

Only verbatim excerpts are displayed as source quotations. Noncontiguous table quotations are located as separate literal lines. A missing or unlocatable extractor quotation does not exclude or replace the sampled claim: reviewers receive references to the full disclosure, and the private sampling manifest records the localization status. Excerpt availability is not a human fidelity verdict.

The completed pilot exposed one noncontiguous table quotation during material preparation. The `bace_postprocessing_v1_1` revision fixes that preparation step. Its four-file delta is retained inside the existing freeze and reconstructs the previous freeze hash. The pilot keeps its original run identity; summaries and human materials identify the revised postprocessing freeze. Model stages, evidence, prompts, selection and scoring are unchanged, and all completed case artifacts must remain byte-identical when reused.

The acceptance command checks the frozen files/environment, full 30 × 5 × 12 matrix, 150 packages, vector integrity, known exclusions, company/year boundaries, tests, complete real twelve-task pilot, native score denominators and blank review materials. Unresolved critical items appear in the generated readiness report and block the main command.
