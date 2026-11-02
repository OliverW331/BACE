# Methods: first manuscript draft

Version 1, 1 October 2026. Target: Nature Sustainability, Article. Companion to the [Results draft](08_results_draft.md). This connected draft describes the saved experiment and analysis; the final subsection explicitly describes a prepared human-assessment study with no completed local annotations. HTML paragraph identifiers connect the manuscript to the evidence and Results crosswalk below. Availability, author declarations and outstanding source details remain outside the manuscript text pending verification.

<!-- MANUSCRIPT_START -->
## Methods

### Study design and company selection

<!-- M01 -->
We evaluated one fixed retrieval and generation workflow for corporate sustainability disclosure. The observational unit was a generated disclosure for one company, target reporting year and task. The source register contained 600 companies; 250 met the source-availability criteria. Eligibility required a known latest primary Sustainable Industry Classification System sector at or before 2023, at least one extracted structured-metric record marked valid and containing a nonempty value in every source year from 2015 to 2023, and a locally available PDF with a valid file header in every source year from 2015 to 2022. Subsequent parsing checked annual narrative availability. Eligibility did not depend on task-specific metrics or evaluator scores, but restricted the study to companies with the required source coverage. The manuscript questions and descriptive comparisons were organized after the experiment and were not preregistered hypotheses.

<!-- M02 -->
We selected 30 companies across the 11 eligible sectors. One place was allocated to each sector; the remaining 19 were allocated by Hamilton largest remainders, weighted by eligible sector size minus one, with alphabetical tie-breaking. Within each sector, company identifiers were sorted and shuffled using Python's pseudorandom generator, initialized with the integer SHA-256 digest of the string comprising the sampling seed, 20260916, a colon and the sector name. The first companies up to the sector quota were selected, with the remainder forming an ordered reserve. The protocol permitted replacement by the next same-sector reserve if a required source year proved unusable before generation, but prohibited replacement on generated content or evaluation results. No replacement was recorded for this draw.

### Disclosure tasks and temporal evidence boundaries

<!-- M03 -->
Each company was assigned 12 tasks in each target reporting year from 2019 to 2023, giving a planned matrix of 1,800 cases. Task definitions used the 2023 European Sustainability Reporting Standards as a common framework: climate transition plans, actions and resources, targets, and greenhouse gas emissions (E1-1, E1-3, E1-4 and E1-6); workforce policies, actions and resources, targets, and health and safety metrics (S1-1, S1-4, S1-5 and S1-14); and business conduct policies, supplier relationships, anti-corruption controls, and corruption and bribery incidents (G1-1 to G1-4). Applying these definitions to earlier reporting years specified a generation task; it did not establish a legal obligation for each company and year.

<!-- M04 -->
For target year \(t\), structured metrics were eligible from source years \(t-4\) through \(t\), whereas PDF reports were eligible from \(t-4\) through \(t-1\). These were report-year filters, not publication-date cutoffs. Reports could describe measurements from other periods or prospective commitments, whose temporal qualifiers remained relevant to support. The historical PDF window could therefore limit evidence for claims about current practices, even where current-year structured metrics were available. Disclosures generated for other tasks were not supplied as evidence.

### Evidence preparation and retrieval

<!-- M05 -->
The evidence corpus combined structured-metric cards rendered deterministically from an existing extraction CSV, narrative passages extracted from reports with PyMuPDF, and table rows extracted with pdfplumber. Narrative preparation used the recorded 40–250-word chunking rules. Eligible reports were processed without task-keyword page selection. Stable evidence identifiers, source years, file hashes and source references were retained; PDF cards also retained page locations. Structured-metric cards represented extracted CSV records and were not treated as independently verified quotations from original reports. Flattening narrative and table layouts could alter relationships between labels and values.

<!-- M06 -->
Before generation, a quality gate excluded an entire card if it contained at least ten unmapped private-use or replacement glyphs comprising more than 5% of non-whitespace characters, or exceeded 8,191 tokens under the cl100k_base tokenizer. The preparation record also identifies four quarantined Evonik 2023 metric mappings following source inspection. Original reports and exclusion records were retained, and source-year availability was rechecked after quarantine. These checks addressed specified extraction problems without certifying the remaining source representations. Missing metrics and evidence types were not imputed.

<!-- M07 -->
Retrieval combined BM25 with cosine similarity over 3,072-dimensional text-embedding-3-large embeddings. Company and source-year filters were applied before ranking. Each channel retrieved up to 200 candidates per task subquery; reciprocal rank fusion combined subquery rankings within channels and then the channel rankings, using a rank constant of 60. Stored corpus vectors were already normalized; the retrieval configuration disabled additional corpus normalization. Ties were resolved by best individual rank, most recent source year and evidence identifier. The final selection retained up to ten cards from each evidence type, without a reranker or redistribution of unfilled quotas. Evidence entered the generation prompt in narrative, table-row and structured-metric order. Thus, 30 cards was a maximum, not a requirement for every case. The query bundles, selected card order and generation inputs were saved before the main run.

### Disclosure generation and incomplete cases

<!-- M08 -->
Generation used the configured Azure OpenAI gpt-5.6-sol deployment, with recorded model-version label 2026-07-09, medium reasoning effort, no temperature parameter and an output budget of 8,192 tokens. The shared prompt requested a professional disclosure of 300–500 words based on the supplied evidence. The first complete response meeting the length rule was accepted. Incomplete or out-of-range responses triggered up to two retries of the identical prompt per invocation, with rejected attempts retained; response selection did not use evaluator scores. The runtime permitted at most three attempts per stage. These settings and saved outputs document the executed workflow but do not guarantee byte-identical responses from a later remote deployment.

<!-- M09 -->
Generation preceded the BACE, RAGChecker and RAGAS evaluation branches. Stage receipts recorded dependencies and artifact hashes so that verified completed work could be reused after interruption. Unresolved evaluations remained missing. The saved analysis contained 1,798 completed BACE cases, all with available native comparator scores. Banco BPM's 2019 workforce-targets case and Investec's 2023 workforce-policies case had incomplete BACE branches and were excluded without zero imputation. Their exclusion did not imply failure of generation or of every comparator branch. The analysed cohort and saved run status were retained explicitly rather than treating the planned matrix as fully completed.

### BACE claim construction and support judgments

<!-- M10 -->
BACE first constructed evidence claims (ECs) from the complete prompt-visible evidence and disclosure claims (DCs) from the generated disclosure. The fixed sequence comprised direct extraction version 8, identified-patch review version 4 using operational definition version 2, constrained atomicity review version 2, and semantic deduplication within each case. The BACE stage configurations selected Azure gpt-5.6-sol, with model-version label 2026-07-09 and medium reasoning effort. The extraction rules required material qualifiers, including entity, period, population, metric, unit and certainty, to remain attached to their propositions. Each initial EC was attributed to one evidence card, and deduplication retained source-occurrence lineage. The configured schema-only acceptance mode did not require a quoted string to match its source exactly; stored quotation fields consequently did not establish verified attribution.

<!-- M11 -->
Candidate selection operated on the deduplicated EC and DC texts. It did not receive retrieval scores, task definitions or separate source-provenance fields as additional factual premises. For each DC, the support judge received the DC text, selected candidate EC identifiers and texts, company name and target reporting year. It did not receive the original evidence cards or the full unselected EC inventory at this stage. Company and year provided interpretive context but could not supply absent facts. Support decisions were therefore conditional on the preceding extraction and candidate selection.

<!-- M12 -->
The support prompt requested every distinct minimal sufficient EC set that supported the complete DC, including its material qualifiers. Minimality meant that removing any member would leave that set insufficient; it did not require choosing only the smallest set among all alternatives. A set was direct when it explicitly entailed the claim, allowing equivalent wording, and inferred when entailment required a necessary reasoning step rather than a merely plausible assumption. Support type did not depend on the number of ECs in a set. Any accepted direct set produced a direct DC verdict; accepted inferred sets without a direct set produced an inferred verdict; no accepted set produced an unsupported verdict. An empty candidate set yielded an empty support result without a support-model call. The output contained support sets and their types, rather than a prose support rationale. Structural validation checked identifiers and record completeness, but did not independently establish the semantic validity, minimality or exhaustiveness of the returned sets.

<!-- M13 -->
Each unsupported DC received one diagnosis, assigned in a fixed precedence order. A non-disclosure statement asserted an absence of disclosure or evidence within a specified scope. Contradiction required an incompatible proposition at matching material boundaries. Evidence conflation combined elements from multiple ECs into an unsupported relationship or attribution. Factual boundary distortion transferred an anchored fact across a material qualifier, such as entity, time, population, metric or unit. Inferential inflation strengthened meaning, status, certainty or conclusion beyond the evidence while retaining the relevant factual boundaries. Unsupported novelty applied when no candidate EC anchored the core proposition. These mutually exclusive outputs characterized the automated diagnostic procedure. Assertions about absent information entered support assessment first and were not automatically assigned an unsupported diagnosis.

### Outcomes and native comparator procedures

<!-- M14 -->
For disclosure \(d\), let \(N_d\) be the number of deduplicated DCs, and \(A_d\) and \(I_d\) the numbers receiving direct and inferred support. The primary support rate was

\[
s_d=\frac{A_d+I_d}{N_d}.
\]

The disclosure-level mean gave each completed disclosure equal weight, whereas the pooled estimate divided total supported claims by total DCs:

\[
\bar{s}=\frac{1}{n}\sum_{d=1}^{n}s_d,
\qquad
s_{\mathrm{pooled}}=\frac{\sum_d(A_d+I_d)}{\sum_d N_d}.
\]

Diagnosis proportions used all unsupported DCs as their denominator. The metric implementation required nonempty EC and DC inventories, complete support records and diagnoses that exactly partitioned unsupported DCs; invalid or incomplete cases did not receive fabricated scores.

<!-- M15 -->
For sensitivity analysis, \(Z_d\) denoted the number of unsupported DCs diagnosed as non-disclosure statements. The alternative rate was \((A_d+I_d)/(N_d-Z_d)\), and its change from \(s_d\) was summarized within disclosures in percentage points. This removed only claims assigned that diagnosis. Additional saved metrics were evidence-claim coverage, defined as the number of distinct ECs appearing in any accepted support set divided by the total deduplicated EC inventory, and inference rate, defined as \(I_d/(A_d+I_d)\). Zero denominators produced missing values. Inference rate differed from the inferred share of all DCs reported in Results; coverage described use of supplied extracted evidence, not completeness of corporate reporting.

<!-- M16 -->
RAGChecker evaluates claim-level entailment and defines faithfulness through support in retrieved context [@ragchecker2024]. RAGAS assesses faithfulness by extracting response statements and checking their support in the supplied context [@ragas2024]. We used RAGChecker 0.1.9 with RefChecker 0.2.13 and RAGAS 0.4.3. A common adapter supplied the same generated response and ordered prompt-visible evidence, checking prompt, response and context hashes. Each comparator retained its native extraction prompts, checking procedure and claim denominator. Only faithfulness was evaluated; no reference answers were supplied. The configured Azure gpt-5.6-sol judge used medium reasoning. The transport adapter supplied these reasoning and output-budget settings in place of package-default request parameters while preserving native prompts and scoring.

<!-- M17 -->
In the recorded RAGChecker procedure, extracted response triplets were checked against individual evidence cards; a claim counted as supported if at least one card received an entailment verdict. The joint-checking group size was five claims, not five merged evidence cards. RAGAS checked its extracted statements against the combined supplied contexts and calculated their supported fraction. Invalid extraction, response or statement-alignment outputs were subject to the recorded retry policy and remained missing if unresolved. Matching source inputs at the adapter level did not align the evaluated propositions or make either comparator's checking context identical to BACE's candidate ECs. Native score differences could therefore reflect multiple stages and did not isolate evaluator accuracy.

### Aggregation and uncertainty

<!-- M18 -->
We reported disclosure-level and task-level means, pooled claim counts and diagnosis composition using the completed cohort. Paired comparisons used the intersection of available BACE, RAGChecker and RAGAS scores. For each comparator, its score was subtracted from BACE's support rate within each disclosure before averaging; differences were expressed in percentage points. Native claim-count medians used the same paired disclosures. No sector population weights were applied, and claims from different native inventories were not treated as matched measurement units.

<!-- M19 -->
The saved analysis used 2,000 company-cluster bootstrap draws with NumPy's default random generator and seed 20260921. Each draw sampled companies with replacement and retained every observed disclosure from each sampled company, including multiplicities. For each mean or paired difference, the statistic divided the sum of the resampled disclosure values by their resampled count. Thus, clustering accommodated repeated years and tasks within companies while preserving disclosure weighting. The 2.5th and 97.5th percentiles formed the reported 95% intervals. Task-specific calculations used the observed disclosures for that task. The analysis was descriptive and did not perform significance tests. These intervals did not include uncertainty from additional model runs, extraction, human annotation or unresolved cases, and did not implement a sector-design-adjusted extrapolation to the register.

### Selection and source inspection of illustrative cases

<!-- M20 -->
The fixed diagnostic illustrations originated in within-label candidate pools that required a localizable quotation in the generated text. The Wärtsilä temporal case and ASML contradiction case used the recorded selection seeds 20260924 and 20260922, respectively. These case identifiers were retained during manuscript preparation. Source inspection assessed whether their particular rationales preserved the evidence's temporal or tabular relationships; it did not validate the complete disclosures. The ASML example was retained because the original glossary challenged the recorded contradiction rationale.

<!-- M21 -->
Additional comparator disagreements were discovered through targeted screening of saved outputs. The initial screen considered BACE contradictions and other unsupported DCs with an exact normalized match to a supported RAGAS statement. It then identified the nearest native claims by token-set Jaccard overlap and retained candidates with positive judgments from both comparators. A supplementary screen searched unsupported quantitative DCs containing a digit and a specified unit or status keyword, excluded non-disclosure statements, and required both nearest native claims to be supported with Jaccard overlap of at least 0.65. Exact normalization used Unicode NFKC, case folding and word-token joining. These lexical operations retrieved candidates; they did not establish semantic equivalence or representative error frequencies.

<!-- M22 -->
For the selected SCA, Continental and Banco BPM cases, inspection compared the complete generated passage, all supplied evidence cards, the disputed DC, its candidate ECs and the exact native statements and verdicts. Candidates were not promoted as clear shared disagreements when a native statement omitted the disputed qualifier, another supplied card established support, or the complete passage qualified the apparent overstatement. The original Banco BPM report was inspected after evaluation to resolve column headings missing from the supplied table row; those restored headings were not evaluator inputs. Its BACE candidate ECs omitted the numerical cells, so an unsupported verdict did not demonstrate recovery of the original structure. These source-linked inspections were part of manuscript preparation, with AI assistance, and were not independent human annotation or estimates of evaluator accuracy.

### Prepared independent human assessment

<!-- M23 -->
An independent assessment package was prepared to examine BACE judgments conditional on their actual DC and candidate EC inputs. The formal design documented on 25 September 2026 replaced the broader source-review scope described in the original protocol. It selected 600 unique DCs from the completed inventory: 400 primary units, allocated proportionally across automated direct, inferred and unsupported strata using largest remainders, and 200 supplementary units from the remaining unsupported pool. Primary quotas were 145, 75 and 180, respectively. Selection used seeded SHA-256 ranking without replacement, with seed bace-human-validation-v1-20260924. Supplementary allocation successively favoured the least represented diagnosis, breaking ties in the fixed diagnostic order and capping total contradiction units at 40 to retain calibration-eligible units. An independent seeded ranking set the presentation order, with group membership withheld from reviewer workbooks.

<!-- M24 -->
Two workbooks contained the same 600 sample identifiers and supplied company name, target year, complete DC text and the exact candidate EC membership, order, identifiers and wording. Automated answers were omitted, and the instructions required independent review without access to the other reviewer's answers. As of the local file check on 1 October 2026, both workbooks had blank support and diagnosis cells; the manifest recorded prepared, not annotated, and calibration had not been conducted. No reviewer agreement, adjudication or accuracy estimates were available from these files. This status describes the inspected local copies and does not establish whether completed annotations exist elsewhere.

<!-- M25 -->
The prepared design specifies primary-stratum weights for overall estimates from the 400 primary units. Supplementary inclusion probabilities are conditional on the realized primary sample; the combined 600 units must not be analysed as an unweighted representative sample. Reviewers are to assign direct, inferred or unsupported labels and one diagnosis only when selecting unsupported. Any future calibration must use separate units. The supplied material permits assessment of conditional support and diagnosis decisions, but not independent validation of extraction, candidate selection, original-source completeness, real-world truth or comparative evaluator accuracy. Reviewer qualifications, completed calibration, agreement procedures and adjudication outcomes require documentation before reporting human-assessment results.
<!-- MANUSCRIPT_END -->

## Evidence ledger and Results–Methods crosswalk — not manuscript text

Methods paragraphs describe recorded procedures unless explicitly marked as prepared or future. The [Methods verification record](analysis/methods_draft/provenance.json) records source hashes, configuration checks, citation occurrences and this crosswalk. The [Results verification record](analysis/results_draft/provenance.json) recomputes point estimates from saved analysis inputs and preserves the distinction between recalculated values and saved bootstrap endpoints. Neither check reruns model evaluations or supplies human adjudication.

| Methods paragraphs | Source and locator | Results correspondence |
|---|---|---|
| M01–M02 | [Protocol](../BACE/PROTOCOL.md), Population and stratified selection; [sample manifest](../BACE/evidence/sample/sample.json), population, eligibility, quotas, seed and selected records; [sampling implementation](../BACE/script/select_sample.py), `allocate` and `select`. | R01: sampled companies and inferential scope. |
| M03–M04 | [Task definitions](../BACE/config/tasks.json); [experiment configuration](../BACE/config/experiment.json), target years and windows. | R01, R04, R07: task counts and temporal boundary. |
| M05–M06 | [Evidence preparation](../BACE/script/prepare_evidence.py); [quality gate](../BACE/script/evidence_quality.py); protocol, Evidence and retrieval; experiment configuration, `source_quality`. | R01, R08, R13: evidence forms and source-transformation limits. |
| M07 | [Retrieval configuration](../BACE/config/retrieval/retrieval_algorithm_config_text_embedding_3_large_top200_v1.json); [input preparation](../BACE/script/prepare_inputs.py); [embedding manifest](../BACE/evidence/embeddings/manifest.json), normalization. | R01–R02: fixed supplied-evidence boundary. |
| M08–M09 | Experiment configuration, `generation` and `runtime`; [generation templates](../BACE/config/prompts/generation_prompt_templates.json); [execution status](../BACE/results/main_v1/execution_status.json); [case metrics](../BACE/analysis/outputs/snapshot/metrics.csv). | R01, R03–R05, R09–R10: completion and common cohort. |
| M10–M13 | [Method definition](../docs/generation_evaluation.md); [extraction](../BACE/config/evaluation/configs/generation_claim_extraction_config_v8.json), [patch review](../BACE/config/evaluation/configs/generation_claim_patch_review_config_v4.json), [atomicity review](../BACE/config/evaluation/configs/generation_claim_atomicity_review_config_v2.json) and [candidate selection](../BACE/config/evaluation/configs/generation_claim_candidate_selection_config.json) configurations; [support prompt](../BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt); [diagnosis prompt](../BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt). | R02, R06–R08, R11–R13: operational labels and conditional judgments. |
| M14–M15 | [Metric implementation](../BACE/script/evaluation/metrics.py); [analysis contract](../BACE/analysis/ANALYSIS_SPEC.md); [verified Results numbers](analysis/results_draft/verified_numbers.json), support, sensitivity and diagnoses. | R03, R05–R06: denominators and aggregation. |
| M16–M17 | [Native configuration](../BACE/config/evaluation/configs/external_evaluation_config.json); [common adapter](../BACE/script/evaluation/external_evaluation.py); [RAGChecker wrapper](../BACE/script/evaluation/run_ragchecker.py); [RAGAS wrapper](../BACE/script/evaluation/run_ragas.py); [full-text citation occurrences](analysis/methods_draft/citation_occurrences.json), M16. | R09–R13: native inputs, claims and verdicts. |
| M18–M19 | [Bootstrap implementation](../BACE/analysis/analysis_data.py), `company_bootstrap`; analysis contract, Statistical contract; Results numbers, comparators and inventory medians. | R03–R04, R09–R10: means, intervals and paired comparisons. |
| M20 | [Fixed examples](analysis/storyline/example_candidates.json); [original ASML page](../BACE/analysis/outputs/figures/02/02_asml_source_layout.png) and [page record](../BACE/analysis/outputs/figures/02/02_asml_source_layout__data.csv). | R07–R08, R14: fixed selection and counterexample. |
| M21–M22 | [Initial screening](analysis/disagreement_cases/screen_candidates.py); [quantitative screening](analysis/disagreement_cases/screen_numerical_candidates.py); [source bundle provenance](analysis/disagreement_cases/bundle_provenance.json); [expanded case review](07_expanded_disagreement_examples.md); [SCA](analysis/disagreement_cases/sca_incidents_workers.json), [Continental](analysis/disagreement_cases/continental_coverage.json) and [Banco BPM](analysis/disagreement_cases/banco_bpm_actual_as_target.json) bundles. | R10–R14: targeted discovery, source inspection and limits. |
| M23–M25 | [Formal review guide](../BACE/analysis/validation/README.md); [private sample manifest](../BACE/analysis/validation/_private/sample_manifest.json), status and study design; Results numbers, `validation`, based on workbook contents. | R14 and pending human-assessment subsection: preparation is not validation. |

### Citation support

M16 contains two literature citations, each tied to the exact methodological claim immediately preceding it. The [occurrence ledger](analysis/methods_draft/citation_occurrences.json) records original-source version, identifier, full-text locator, source retrieval date, local review date and short supporting fragments. The papers establish methodological precedents; saved implementation records establish this experiment's package versions, transport and parameters. The task paragraph describes the recorded operational task definitions. **`UNVERIFIED`:** the exact official ESRS passages for any regulatory claim or final standards citation must still be checked; this draft does not assert legal compliance.

### Outstanding facts and integration

- **`AUTHOR_INPUT_NEEDED` — source provenance and access:** document the origin and permitted sharing conditions of the company register, report corpus and pre-existing structured-metric extraction, including the extraction procedure needed to reproduce those inputs. Local file paths and hashes establish identity, not licensing or a public acquisition route.
- **`AUTHOR_INPUT_NEEDED` — human assessment:** establish whether completed annotation copies exist elsewhere; record actual reviewer selection and qualifications, independence, calibration, disagreement handling, ethics or exemption where applicable, and completed procedures before changing M23–M25 to a completed-study account. **`COMPUTATION_PENDING`:** agreement and adjudication analyses. Preserve original labels and report missing or unresolved assessments explicitly; do not infer comparator accuracy from this conditional BACE design.
- **`AUTHOR_INPUT_NEEDED` — availability and declarations:** verify an actual data/code repository, release identifier and access conditions before drafting final availability statements; confirm author contributions, funding, competing interests and relevant permissions. No deposit, permission or declaration is established here.
- **`AUTHOR_INPUT_NEEDED` — author oversight and AI disclosure:** the current writing work includes AI-assisted Methods drafting, Results editing, code-assisted checks and source inspection. Describe the authors' actual subsequent verification and responsibility; do not state that author review has already occurred.
- **Manuscript integration:** M23–M25 deliberately retain prepared-study language. Update or relocate them when validation status is settled. Compose planned Figs. 1–4 and their legends next, retaining the ASML counterexample and the Banco BPM extraction qualification. The linked outline remains the earlier planning record.

The [dated Nature Sustainability profile](NATURE_SUSTAINABILITY_GUIDELINES.md) places Methods outside the 3,500-word main-text limit. This draft is not a submission-ready package; final evidence, declarations, displays and current journal requirements still need integration.
