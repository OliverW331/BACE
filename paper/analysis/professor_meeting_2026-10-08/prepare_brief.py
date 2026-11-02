"""Build a meeting brief from saved results, without changing experiment artifacts."""
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INPUTS = {}


def source(path):
    p = ROOT / path
    INPUTS[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


def read_json(path):
    return json.loads(source(path).read_text())


def read_csv(path):
    with source(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def link(label, path):
    return f"[{label}]({ROOT / path})"


def close(actual, expected):
    assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10), (actual, expected)


main = read_csv("BACE/analysis/outputs/snapshot/metrics.csv")
complete = [r for r in main if r["bace_complete"] == "True"]
saved = read_json("paper/analysis/results_draft/verified_numbers.json")
prior = read_json("paper/analysis/results_draft/provenance.json")
status = read_json("BACE/results/main_v1/execution_status.json")
assert len(main) == status["expected_cases"] == 1800
assert len(complete) == len(status["completed_case_ids"]) == 1798
assert len({r["company_id"] for r in complete}) == 30
assert all(r["ragas_complete"] == r["ragchecker_complete"] == "True" for r in complete)
counts = {k: sum(int(float(r[col])) for r in complete) for k, col in {
    "Direct": "bace_supported_direct", "Inferred": "bace_supported_inferred",
    "Unsupported": "bace_unsupported"}.items()}
assert counts == saved["support"]["counts"]
assert sum(counts.values()) == 94955
for label, col in {"BACE": "bace_support_rate_all_dc", "RAGAS": "ragas_faithfulness",
                   "RAGChecker": "ragchecker_faithfulness"}.items():
    close(100 * mean(float(r[col]) for r in complete), saved["comparators"]["means_pct"][label])
for task in saved["tasks"]:
    rows = [r for r in complete if r["task"] == task["task"]]
    assert len(rows) == int(task["disclosures"])
    close(mean(float(r["bace_support_rate_all_dc"]) for r in rows), float(task["mean"]))
for label, n in saved["diagnoses"]["counts"].items():
    assert sum(int(float(r["bace_" + label])) for r in complete) == n

stable_files = ["BACE/analysis/outputs/snapshot/metrics.csv",
                "BACE/results/main_v1/execution_status.json"]
stable_files += [f"BACE/analysis/validation/human_validation_600_reviewer_{x}.xlsx" for x in "AB"]
for p in stable_files:
    source(p)
    assert INPUTS[p] == prior["input_files"][p]["sha256"]

base = "BACE/analysis/outputs/evaluator_gap"
experiments = {}
for name, expected_n, expected_claims in [("prompt_sensitivity", 1796, 94854),
                                         ("evidence_chain_sample", 89, 4746)]:
    prefix = f"{base}/{name}"
    pairs = read_csv(f"{prefix}/tables/paired_cases.csv")
    scores = read_csv(f"{prefix}/tables/scores.csv")
    effects = read_csv(f"{prefix}/tables/effects.csv")
    provenance = read_json(f"{prefix}/provenance.json")
    assert len(pairs) == expected_n
    assert sum(int(r["claims"]) for r in pairs) == expected_claims
    assert len({r["company_id"] for r in pairs}) == 30
    for s in scores:
        close(mean(float(r[s["condition"]]) for r in pairs), float(s["estimate"]))
    for e in effects:
        left = e.get("left", e.get("condition"))
        reference = e.get("reference", "original")
        close(mean(float(r[left]) - float(r[reference]) for r in pairs), float(e["estimate"]))
    if name == "prompt_sensitivity":
        for filename, expected_hash in provenance["tables"].items():
            p = f"{prefix}/tables/{filename}"
            source(p)
            assert INPUTS[p] == expected_hash
    experiments[name] = {"scores": scores, "effects": effects,
                         "disclosures": len(pairs), "claims": expected_claims}
    read_json(f"{prefix}/qa/final_statistics.json")
    read_json(f"{prefix}/readiness.json")

for name in ["prompt_sensitivity_v1", "evidence_chain_v1", "evidence_chain_sample_v1"]:
    read_json(f"BACE/results/{name}/status.json")
    source(f"BACE/experiments/{name}/PROTOCOL.md")
review = read_csv(f"{base}/evidence_chain_sample/review/annotations.csv")
assert len(review) == 160
assert all(not value.strip() for row in review for key, value in row.items() if key != "review_id")
gap = read_json("paper/analysis/evaluator_gap/results.json")
source("paper/analysis/evaluator_gap/analyze_saved_gap.py")
source(f"{base}/prompt_sensitivity/findings.md")
source(f"{base}/prompt_sensitivity/tables/repeat_effects.csv")
source(f"{base}/prompt_sensitivity/tables/repeat_transitions.csv")
source("BACE/PROTOCOL.md")
source("BACE/analysis/ANALYSIS_SPEC.md")
source("BACE/analysis/evaluator_gap_prompt_sensitivity.py")
source("BACE/analysis/evaluator_gap_evidence_chain.py")
source("paper/manuscript/main.tex")
source("BACE/analysis/04_evaluator_gap_diagnostics.ipynb")

groups = [("Main manuscript", ROOT / "paper/manuscript/figures"),
          *[(f"Notebook {i:02d}", ROOT / f"BACE/analysis/outputs/figures/{i:02d}") for i in range(4)],
          ("Notebook 04", ROOT / f"{base}/figures")]
inventory = []
for group, folder in groups:
    for png in sorted(folder.glob("*.png")):
        p = str(png.relative_to(ROOT))
        source(p)
        metadata_path = png.with_suffix(".metadata.json")
        metadata = read_json(str(metadata_path.relative_to(ROOT))) if metadata_path.exists() else {}
        inventory.append({"group": group, "figure": png.stem, "png": p,
                          "pdf": str(png.with_suffix(".pdf").relative_to(ROOT)) if png.with_suffix(".pdf").exists() else "",
                          "caption": metadata.get("caption", "See the manuscript figure legend.")})
group_counts = Counter(r["group"] for r in inventory)
index = ["# Current figure inventory", "", "Checked: 8 October 2026 (Europe/Zurich).",
         "", "Counts refer to figure bundles, not panels. PNG/PDF/SVG versions are counted once. "
         "Main figures recompose existing analyses and are not additional experiments. "
         "Archives, QA previews and synthetic fixtures are excluded.", "",
         "| Collection | Figure bundles |", "|---|---:|"]
index += [f"| {k} | {v} |" for k, v in group_counts.items()]
index += ["", "| Collection | Figure | Exports |", "|---|---|---|"]
for item in inventory:
    exports = link("PNG", item["png"])
    if item["pdf"]:
        exports += " · " + link("PDF", item["pdf"])
    index.append(f"| {item['group']} | {item['figure']} | {exports} |")
(OUT / "FIGURE_INDEX.md").write_text("\n".join(index) + "\n")


def score_table(name):
    lines = ["| Condition | Mean support | Saved 95% interval |", "|---|---:|---:|"]
    for row in experiments[name]["scores"]:
        lines.append(f"| {row.get('label', row['condition'])} | {100*float(row['estimate']):.2f}% | "
                     f"{100*float(row['low']):.2f}–{100*float(row['high']):.2f}% |")
    return "\n".join(lines)


brief = f"""# BACE results for the professor meeting

Snapshot checked: 8 October 2026 (Europe/Zurich).

The project now has a main descriptive study, native evaluator comparisons, diagnostic analyses, a completed support-prompt sensitivity experiment, and completed statistics for a sampled evidence-chain experiment. The two sensitivity experiments extend the results currently presented in the manuscript. Independent human validation remains pending in the inspected local materials.

## Suggested opening

“We observe a large difference between BACE and two native faithfulness evaluators. Controlled sensitivity experiments show that both judgment instructions and the evidence supplied to the judge affect BACE's support rates. Our next question is which disagreements reflect inadequate evidence, losses during processing, or different interpretation rules. Current automated scores alone cannot establish which evaluator is more accurate.”

## Completed results and their interpretation

### 1. Main study: support within supplied evidence

The planned design is 30 companies × 5 reporting years (2019–2023) × 12 ESRS tasks. The analysed and native paired cohort contains 1,798 disclosures; 2 BACE cases remain incomplete. These are generated company–year–task sections, not 1,798 independent companies. The main run's saved status remains `incomplete`.

The disclosure-macro support rate is **55.4%** (saved 95% company-cluster interval, **53.9–56.8%**). Across **94,955 DCs**, the claim-pooled composition is **34,430 direct (36.3%)**, **17,879 inferred (18.8%)**, and **42,646 unsupported (44.9%)**. Pooled support is 55.1%; it uses a different weighting from the disclosure mean. An unsupported judgment is not an independently verified factual error.

Task means range from **43.9% for workforce targets (S1-5)** to **62.5% for business conduct policies (G1-1)**. Treat these as descriptive heterogeneity, not an established causal task effect.

Show: {link('Figure 1: study design', 'paper/manuscript/figures/fig1_study_design.pdf')} and {link('Figure 2: support and task differences', 'paper/manuscript/figures/fig2_support.pdf')}.

Source: {link('current case metrics', 'BACE/analysis/outputs/snapshot/metrics.csv')} and {link('saved numerical ledger', 'paper/analysis/results_draft/verified_numbers.json')}. Point estimates and counts were reconciled again for this brief.

### 2. Unsupported-claim diagnoses

Of the 42,646 unsupported claims, BACE assigns **19,130 (44.9%)** to factual boundary distortion and **12,205 (28.6%)** to evidence conflation: **73.5% together**. These are outputs of an ordered automated diagnosis procedure. The denominator here is unsupported claims, unlike the all-claim composition above.

{link('Figure 3', 'paper/manuscript/figures/fig3_diagnoses_cases.pdf')} includes a historical-to-current policy interpretation and an ASML source-row association problem that challenges BACE's contradiction rationale. Present both the potential reporting problem and the evaluator's own limitation. The examples do not establish error prevalence.

### 3. Native evaluators disagree substantially

On the same 1,798 disclosures, mean native scores are **BACE 55.4%, RAGChecker 90.2%, and RAGAS 90.7%**. BACE-minus-comparator paired differences are **−34.9 pp** (95% interval −36.2 to −33.5) and **−35.3 pp** (−36.5 to −34.1), respectively.

Median claim counts are 52, 40 and 42, respectively. The methods use different inventories, evidence representations and judgment procedures; the difference is not an accuracy ranking.

Show: {link('Figure 4: native comparisons', 'paper/manuscript/figures/fig4_native_comparison.pdf')}. Source: {link('paired differences', 'BACE/analysis/outputs/figures/03/03_native_comparison__paired_differences.csv')}.

### 4. Existing diagnostics narrow the explanations

- Removing only unsupported claims diagnosed as non-disclosure statements raises the macro score to **59.7%**, a **4.35 pp** change. A large native gap remains.
- Even hypothetically accepting every zero-candidate DC raises the score by at most **2.05 pp**. This bounds only that subset; nonempty candidate sets can still miss decisive evidence. This scenario overlaps the preceding sensitivity and the effects must not be added.
- In **5,709 uniquely matched BACE–RAGAS claims with identical normalized wording**, the pooled support rates are **59.3% and 94.0%**. The subset covers only **6.01% of BACE claims** and is not representative semantic alignment.

Sources and figures: {link('diagnostic results', 'paper/analysis/evaluator_gap/results.json')}, {link('score sensitivity', base + '/figures/04_score_sensitivity.pdf')}, and {link('identical-wording judgments', base + '/figures/04_literal_pairs.pdf')}. These saved diagnostic values are `SOURCE_REPORTED` here; their original analysis and provenance remain linked in the diagnostic workspace.

### 5. New result: judgment instructions affect support

The completed prompt experiment has **1,796 fully paired disclosures and 94,854 DCs from 30 companies**. Three failed condition-level records affect two disclosures, excluded as whole units. Targets, candidate ECs, model settings and output requirements are fixed; the judgment instructions change. These are adapted prompts within BACE, not native RAGAS or RAGChecker reruns.

{score_table('prompt_sensitivity')}

The paired increases are **+7.66 pp** (95% interval **+6.84 to +8.46**) for RAGAS-style and **+4.97 pp** (**+4.14 to +5.79**) for RAGChecker-style. Both additions and removals of support occur. On the fixed 60-disclosure repeat subset, the original prompt's net change is **−0.49 pp**, while **9.95% of claims flip**; small net change does not imply stable individual judgments.

Show: {link('prompt effects', base + '/figures/04_prompt_sensitivity_effects.pdf')} and {link('bidirectional transitions', base + '/figures/04_prompt_sensitivity_transitions.pdf')}. Sources: {link('scores', base + '/prompt_sensitivity/tables/scores.csv')}, {link('effects', base + '/prompt_sensitivity/tables/effects.csv')}, and {link('completed findings', base + '/prompt_sensitivity/findings.md')}.

Interpretation: support is sensitive to the bundled instructions. These changes do not quantify the fraction of the native evaluator gap caused by prompts, nor validate the changed judgments.

### 6. New result: evidence selection and representation affect support

The sampled evidence-chain experiment selected **90 disclosures**, one per company × E/S/G stratum. One failed record excludes one entire disclosure, leaving **89 paired disclosures and 4,746 DCs across 30 companies**. The original full-cohort evidence-chain run was stopped for sampling; it is not a completed full-cohort experiment.

The current three conditions use the same BACE judgment criterion and fixed targets. “Raw cards” means all originally supplied prompt-visible cards, not complete source PDFs. “All ECs” means the full deduplicated evidence-claim pool. “Candidate ECs” means the original selected subset, judged again under the common interface.

{score_table('evidence_chain_sample')}

Paired differences are **raw cards − all ECs: +2.37 pp** (95% interval **+0.27 to +4.36**); **all ECs − candidates: +15.58 pp** (**+13.72 to +17.50**); and **raw cards − candidates: +17.94 pp** (**+15.81 to +19.92**).

The larger observed contrast is between all ECs and candidates. This makes candidate selection a priority for independent source review. It does not establish a 15.58% evidence-loss rate: changing the input also changes context quantity and may change judge behavior. The sampled-cohort rates must not replace the full-cohort main result. Prompt and evidence-chain effects cannot be added across their different designs.

Sources: {link('sampled scores', base + '/evidence_chain_sample/tables/scores.csv')}, {link('paired effects', base + '/evidence_chain_sample/tables/effects.csv')}, and {link('sample protocol', 'BACE/experiments/evidence_chain_sample_v1/PROTOCOL.md')}. The saved statistical audit passes. A dedicated figure and integration into the inspected Notebook 04 are still absent; use this table for the meeting.

## What needs a decision from the professor

1. **Scientific emphasis:** foreground sensitivity of evidence-grounded evaluation, while treating comparative accuracy as unresolved until independent validation.
2. **Validation priority:** review the same DC against raw cards, all ECs and candidates, especially judgments changed by selection. The existing 600-claim formal workbooks assess judgments conditional on candidate ECs; they cannot by themselves validate upstream extraction or selection.
3. **Temporal and inference rules:** agree how historical policy evidence supports a target-year statement and what combinations of separate facts are admissible. The evidence window makes these questions central.
4. **Presentation:** incorporate the two completed sensitivity experiments into Results and Methods, and create a figure for the sampled evidence-chain comparison before treating the current manuscript as up to date.

Local reviewer A/B workbooks still match the hashes of the inspected blank 600-row versions. The separate evidence-chain packet has **160 review rows and no filled annotation fields**. Annotated copies elsewhere are `AUTHOR_INPUT_NEEDED`; no human agreement or accuracy result is available from these local files. Abstract and Discussion also remain incomplete in the current manuscript.

## Meeting route and backup material

Suggested 15-minute route: study design → main support result → native score gap → prompt sensitivity → sampled evidence-chain table → validation decisions. Use Figure 3 as a concrete illustration if the discussion turns to what a support judgment means.

There are **{group_counts['Main manuscript']} manuscript figure bundles** and **{sum(v for k, v in group_counts.items() if k != 'Main manuscript')} analysis figure bundles** across notebooks 00–04. These overlap in content. {link('Complete figure index', str((OUT / 'FIGURE_INDEX.md').relative_to(ROOT)))} lists each PNG/PDF.

- {link('Notebook 00: data and evidence landscape', 'BACE/analysis/outputs/00_data_landscape.html')}: selection, geography, sectors, source availability and time windows.
- {link('Notebook 01: support', 'BACE/analysis/outputs/01_evidence_support.html')}: distributions, task/company/year differences and secondary metrics.
- {link('Notebook 02: failure patterns', 'BACE/analysis/outputs/02_failure_patterns.html')}: diagnosis composition, task patterns, pipeline checks and examples.
- {link('Notebook 03: evaluator comparison', 'BACE/analysis/outputs/03_evaluator_comparison.html')}: native scores, inventories, rank agreement and source-linked cases.
- {link('Notebook 04: evaluator-gap diagnostics', base + '/04_evaluator_gap_diagnostics.html')}: arithmetic controls, identical-wording comparisons and the completed prompt experiment; sampled evidence-chain statistics remain separate.

## Verification scope

This brief recomputes main-study counts and means, and both sensitivity experiments' paired means and effects, from saved disclosure-level tables. It checks the prompt tables against their saved hashes and confirms the main metrics and formal workbooks match the prior verification. Saved 95% intervals are `SOURCE_REPORTED`, using 2,000 company-cluster percentile draws and seed 20260921; no bootstrap was rerun. They condition on observed model outputs and do not capture all model-run or annotation uncertainty. Sample intervals are not exact finite-population intervals for the original full cohort.

Input hashes, result values, code, and figure counts are saved alongside this file. Raw model histories, full extraction lineage and every source passage were not re-audited for this meeting inventory. No experiment, frozen environment, manuscript or existing figure was changed.
"""
(OUT / "MEETING_BRIEF.md").write_text(brief)
(OUT / "verified_results.json").write_text(json.dumps({
    "main": saved, "sensitivity_experiments": experiments, "figure_counts": dict(group_counts),
    "evidence_chain_review_rows": len(review), "completed_local_evidence_chain_annotations": 0,
    "point_estimates": "COMPUTED_VERIFIED", "intervals": "SOURCE_REPORTED",
}, indent=2) + "\n")
(OUT / "provenance.json").write_text(json.dumps({
    "checked_at": datetime.now(ZoneInfo("Europe/Zurich")).isoformat(),
    "command": "python paper/analysis/professor_meeting_2026-10-08/prepare_brief.py",
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "inputs_sha256": INPUTS, "status": "PASS", "bootstrap_rerun": False,
    "model_calls": 0, "new_human_annotations": 0,
    "visually_inspected": ["fig1_study_design", "fig2_support", "fig3_diagnoses_cases",
                           "fig4_native_comparison", "04_prompt_sensitivity_effects"],
    "scope": "Saved-table arithmetic and artifact inventory; not a full raw-run or citation re-audit.",
}, indent=2) + "\n")
print(json.dumps({"status": "PASS", "figure_counts": dict(group_counts), "output": str(OUT)}))
