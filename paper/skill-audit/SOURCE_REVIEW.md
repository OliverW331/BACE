# Source and compatibility review

Review date: 29 September 2026. Scope: the requested skill entrypoints, their
relevant workflows, dependency declarations and the scripts selected for active
installation. This is not a security certification of every file in five repositories.

## Source acquisition

All five requested GitHub repositories resolved under the named owner/repository,
without a canonical-repository rename. The malformed Nature URL was normalized
to `https://github.com/Yuan1z0825/nature-skills`. Public GitHub API metadata and
commit archives were fetched over HTTPS without project credentials. Exact
commits, commit dates, archive hashes, selected-directory file inventories and
upstream SKILL.md hashes are in `manifest.json`.

Archives were checked for absolute/traversal members and symlinks before
extraction. The system `skill-installer` helper and its GitHub utility were read
before use. It staged each selected skill at its pinned commit outside discovery
roots; the staged entrypoints and retained helpers were hash-matched against the
inspected archives. No repository installer, package hook, Claude setup script,
cron job, sleep/research loop or experiment command was executed.

The active installation contains English adaptations, not complete upstream
copies. Full original sources remain in the external cache
`/home/muwang/.cache/bace-skills-2026-09-29/`. Active adapters have provenance
records and upstream licence files. MIT applies to the first four sources;
Apache-2.0 applies to the Nature source. Source identity and pinned content were
verified; independent author-identity or cryptographic commit-signature
certification was not performed.

## Findings and disposition

| Source | Relevant findings | Active disposition |
|---|---|---|
| `ruichenrui/citation-verification` | Instruction-only. Abstract-first relevance and dropping unresolved/contrary records are too coarse for BACE's original-text requirement. | Preserve existence/relevance workflow, require original supporting passages, distinguish retrieval failure from fabrication, retain contrary evidence honestly. |
| K-Dense `citation-management` | Claude/OpenClaw-specific metadata, required network/provider paths, optional Scholar scraper, generic venue rules, automatic scholarly self-citation request. DOI helper accepted arbitrary HTTP-200 bodies and returned success for partial batches. Formatter could silently discard unparsed BibTeX content. | Remove unsupported metadata and automatic citation quota/self-citation rules. Retain three reviewed helpers; patch DOI validation/partial failure and bounded formatter preflight. Search and semantic checks use available Codex tools. |
| K-Dense `scientific-critical-thinking` | Instruction-only appraisal is portable; diagram paths require another skill and OpenRouter. Clinical evidence hierarchies do not automatically apply to BACE. | Preserve bias, design, validity and proportional critique; remove unneeded service dependency and medical-grading default. |
| K-Dense `statistical-analysis` | General instructions require adaptation to paired, nested BACE data. Upstream text overstates p values as establishing an effect's existence and includes broad automatic test-switching advice. `assumption_checks.py` loses original outlier indices after NaN removal, assumes normality from non-rejection, gives an "all assumptions met" message without testing independence, and lacks robust empty/constant input handling. | Install an instruction adapter with cluster-aware design and reproducible computation requirements. Withhold the diagnostic script and its scientific stack. No numerical execution or scientific validation is claimed for that upstream helper. |
| `sayonari/paper_writing` | Japanese/speech-domain instructions, Claude project creation, prescribed Elsevier compile/cleanup scripts, per-section approval gates, Harvard-like citation defaults. Useful provenance categories and dependent-claim checks. Some "safe" statistical substitutes (CI width / beyond sampling variability) are not evidence-free substitutes. | Normalize name to `paper-writing`, translate/distil the applicable workflow, retain traceability, remove domain/tool gates and unsupported significance substitutes. Recognize sufficient paired summaries rather than requiring raw files for every possible statistic. |
| ARIS Codex `citation-audit` | Actual Codex mirror exists. Retains `argument-hint`/Claude tool names, fixed model, one fresh reviewer per entry, external shared-references, trace scripts and HTML dependencies. Model-family identity is not proof of scientific acceptance. | Preserve existence/metadata/context layers and auditable occurrence records; replace missing infrastructure with direct Codex workflows and honest coverage/independence labels. No autonomous research loop installed. |
| Nature writing/polishing | Routers depend on sibling `nature-shared` and journal fragments. No Sustainability-specific journal profile was present. Corpus-derived NMI/Nature advice must not become a Sustainability mandate. | Distil applicable guidance into self-contained BACE adapters and route all journal requirements to a freshly verified official Sustainability profile. No broken sibling references remain. |
| Nature reviewer | Upstream defaults to three mutually blind reports and a broad flagship-Nature source hierarchy. | Internal author-side critique by default, official Sustainability sources first, no fabricated independence, consensus or editorial decision. |
| Nature response | Source includes a standard-library mechanical consistency checker; it expands static LaTeX includes, compares recognized quote macros and normalized text, and does not compile. | Retain the inspected checker and document its coverage and local-input boundary. Replace manifest/sibling dependencies with direct project instructions. |
| Nature data/statistics | Mostly portable reporting guidance, with sibling flagship/NMI rules and some language-routing defaults. | Use verified Sustainability data/code/reporting rules, BACE units and evidence boundaries. Unknown repository/access/ethics/statistical facts remain explicit. |

## Nature selection and existing skills

Selected six workflows for the paper lifecycle: writing, polishing, internal
review, revision response, availability statements and statistical reporting.
The prefix `bace-nature-` distinguishes them from the existing global skills.
Five selected global entrypoints matched the pinned upstream entrypoints; the
existing global `nature-reviewer` differed. None was overwritten. The exact
comparison hashes are in `global-nature-comparison.json`.

The other 14 upstream skill entrypoints were not installed in this project:
academic search, citation, downloader, experiment log, figure, image-to-PPT,
literature pipeline, paper card, paper-to-patent, paper-to-PPT, proposal writer,
reader, reference verifier and shared router. Several overlap the requested
citation tools or existing global capabilities; others are outside the immediate
writing/submission setup. In particular, Nature figure includes plotting/R and
image-service workflows beyond this reviewed subset. Their full runtimes were
not audited or enabled by this installation.

## Dependencies and runtime

The independently created environment is
`/home/muwang/.local/share/bace-writing-skills/venv` (Python 3.13.14).
Only `requests` (DOI metadata) and `PyYAML` (Codex skill validation), plus their
resolved transitive dependencies, were added. Installation used the public PyPI
index, isolated pip configuration and wheels only. Exact installed versions are
in `requirements.lock.txt`; `pip check` passed. Third-party package internals
were not claimed to have received a full source-code security audit.

The retained formatter/shared parser and revision checker use the standard
library. No `scholarly`, NumPy/SciPy/Pingouin/PyMC/ArviZ stack, R, LaTeX engine,
OpenRouter client, new MCP server, credential or global skill was installed.
If later numerical work needs new packages, add them to a separate environment
and record the exact version/API checks; do not change either BACE environment.

## Remaining limits

- Metadata retrieval and structural tests do not establish semantic citation
  support; original source reading is still required for each manuscript claim.
- The formatter deliberately rejects unsupported BibTeX syntax (including
  string macros, concatenation, parenthesized entries and malformed content).
  It preserves the input; a full BibTeX parser is needed for those cases.
- The revision checker is mechanical and macro-limited, not a TeX renderer or
  scientific reviewer. Its pass does not verify arbitrary quotes or all includes.
- The statistical adapter provides a usable instruction workflow; the flawed
  upstream automatic diagnostics and optional numerical stacks remain uninstalled.
- Official rules were verified as retrieved on 29 September 2026. A publisher
  page revision date was not established, and submission-day/editor-specific
  requirements still need a current check.
