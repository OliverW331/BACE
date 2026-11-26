"""Data preparation for Fig. 4 (saved outputs only; no model calls).

Writes tidy CSVs (also the per-panel Source Data) to
BACE/analysis/outputs/figures_v3/fig4_data/.
  a  primary-diagnosis shares of unsupported DCs with company-cluster bootstrap
     intervals (2,000 draws, numpy default_rng(20260921)); must reproduce
     revision_2026-11/06_intervals.csv.
  b, c  case cards read verbatim from the saved per-case outputs of the two
     examples drawn in BACE/analysis/assets/failure_example_selection.json.

    BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_fig4.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SNAP = ROOT / "BACE/analysis/outputs/snapshot"
REV = ROOT / "BACE/analysis/outputs/revision_2026-11"
CASES = ROOT / "BACE/results/main_v1/cases"
SEL = ROOT / "BACE/analysis/assets/failure_example_selection.json"
OUT = ROOT / "BACE/analysis/outputs/figures_v3/fig4_data"
OUT.mkdir(parents=True, exist_ok=True)
SEED, DRAWS = 20260921, 2000
DIAG = ["non_disclosure_statement", "contradiction", "evidence_conflation",
        "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty"]
NAME = {"non_disclosure_statement": "Non-disclosure statement", "contradiction": "Contradiction",
        "evidence_conflation": "Evidence conflation", "factual_boundary_distortion": "Factual boundary distortion",
        "inferential_inflation": "Inferential inflation", "unsupported_novelty": "Unsupported novelty"}


def replicates(companies, values):
    grouped = {}
    for c, v in zip(companies, values):
        grouped.setdefault(c, []).append(float(v))
    ordered = [grouped[c] for c in sorted(grouped)]
    tot = np.array([sum(v) for v in ordered]); cnt = np.array([len(v) for v in ordered])
    pos = np.random.default_rng(SEED).integers(0, len(ordered), size=(DRAWS, len(ordered)))
    return tot.sum() / cnt.sum(), tot[pos].sum(1) / cnt[pos].sum(1)


def jl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


# ---------------------------------------------------------------- a: diagnosis shares
m = pd.read_csv(SNAP / "metrics.csv")
m = m[(m.bace_complete == True) & (m.ragchecker_complete == True) & (m.ragas_complete == True)]
assert len(m) == 1798
claims = pd.read_csv(SNAP / "claims.csv").merge(m[["generation_case_id", "company_id"]], on="generation_case_id")
un = claims[claims.label.isin(DIAG)]
assert len(un) == 42646
ref = pd.read_csv(REV / "06_intervals.csv").set_index("measure")
rows, reps = [], []
for lab in DIAG:
    est, r = replicates(un.company_id, 100 * (un.label == lab))
    lo, hi = np.quantile(r, [0.025, 0.975])
    k = ref.loc[f"diagnosis_share_{lab}"]
    assert np.allclose([est, lo, hi], 100 * k[["estimate", "low", "high"]].astype(float))
    rows.append({"diagnosis": lab, "name": NAME[lab], "rule_order": DIAG.index(lab) + 1,
                 "dcs": int((un.label == lab).sum()), "share_pct": est, "low_pct": lo, "high_pct": hi})
    reps.append(pd.DataFrame({"diagnosis": lab, "replicate_pct": r}))
a = pd.DataFrame(rows)
assert a.set_index("diagnosis").loc[["factual_boundary_distortion", "evidence_conflation", "unsupported_novelty"], "dcs"].tolist() == [19130, 12205, 1698]
a.to_csv(OUT / "a_diagnosis_shares.csv", index=False)
pd.concat(reps).to_csv(OUT / "a_diagnosis_bootstrap.csv", index=False)

# ---------------------------------------------------------------- b, c: case cards
sel = {s["label"]: s for s in json.loads(SEL.read_text())}
CARDS = {
    "b": ("factual_boundary_distortion", ["identification", "assessment", "monitoring"], "online solution for supply-chain risk "),
    "c": ("evidence_conflation", ["addressing animal-welfare", "assessing animal-welfare", "reporting animal-welfare"], "approach to "),
}
card_rows, ev_rows = [], []
for panel, (lab, keys, stem) in CARDS.items():
    s = sel[lab]; d = CASES / s["case_id"]
    case = json.loads(open(d / "inputs/generation_cases.jsonl").readline())
    gen = jl(d / "generation/generated_disclosures.jsonl")[0]
    dcs = {r["dc_id"]: r for r in jl(d / "bace/dedup/dc_claims.jsonl")}
    ecs = {r["ec_id"]: r for r in jl(d / "bace/dedup/ec_claims.jsonl")}
    sup = {r["dc_claim_id"]: r["support_sets"] for r in jl(d / "bace/support/dc_support_sets.jsonl")}
    dia = {r["dc_claim_id"]: r for r in jl(d / "bace/diagnosis/dc_unsupported_diagnoses.jsonl")}
    labels = claims[claims.generation_case_id == s["case_id"]].set_index("dc_id").label
    focal = dcs[s["dc_id"]]
    text = next(v for v in gen.values() if isinstance(v, str) and focal["dc_provenance"][0]["source_spans"][0]["quote"] in v)
    sp = focal["dc_provenance"][0]["source_spans"][0]
    s0 = text.rfind(".", 0, sp["start"]) + 1; s1 = text.find(".", sp["end"] - 1) + 1
    sentence = text[s0:s1].strip()
    for k in keys:
        hit = [i for i, r in dcs.items() if r["dc_text"].endswith((stem + k + ".", stem + k + " risks.")) and
               any(x["start"] < s1 and x["end"] > s0 for p in r["dc_provenance"] for x in p["source_spans"])]
        assert len(hit) == 1, (k, hit)
        i = hit[0]
        card_rows.append({"panel": panel, "company": gen["company_name"], "target_year": gen["target_reporting_year"],
                          "task_id": gen["task_id"], "task_title": gen["task_title"], "generated_sentence": sentence,
                          "dc_id": i, "focal": i == s["dc_id"], "dc_text": dcs[i]["dc_text"], "label": labels[i],
                          "rationale": dia[i]["rationale"] if i in dia else "",
                          "support_ec_ids": ";".join(e for ss in sup.get(i, []) if ss["support_type"] == labels[i]
                                                     for e in ss["ec_claim_ids"]),
                          "selection_seed": s["seed"], "selection_pool_size": s["pool_size"]})
    # evidence passages behind the focal DC's candidate ECs
    cand = next(r["candidate_ec_ids"] for r in jl(d / "bace/candidates/dc_candidate_ecs.jsonl") if r["dc_claim_id"] == s["dc_id"])
    cards = sorted({c for e in cand for c in ecs[e]["evidence_card_ids"]})
    shown = {}
    def walk(o):
        if isinstance(o, dict):
            if o.get("evidence_id") in cards:
                shown[o["evidence_id"]] = o
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(case)
    for cid in cards:
        o = shown[cid]
        ev_rows.append({"panel": panel, "evidence_id": cid, "document_type": o["document_type"],
                        "source_year": o["source_year"], "page": o["page_start"], "prompt_label": o["prompt_label"],
                        "passage": o["retrieval_text"]})
cards = pd.DataFrame(card_rows)
assert cards.set_index("dc_id").loc[sel["factual_boundary_distortion"]["dc_id"], "label"] == "factual_boundary_distortion"
assert cards.label.tolist() == ["factual_boundary_distortion", "direct", "direct",
                                "evidence_conflation", "inferred", "factual_boundary_distortion"], cards.label.tolist()
cards.to_csv(OUT / "bc_case_claims.csv", index=False)
pd.DataFrame(ev_rows).to_csv(OUT / "bc_case_evidence.csv", index=False)
print(a[["name", "dcs", "share_pct", "low_pct", "high_pct"]].round(1).to_string(index=False))
print(pd.DataFrame(ev_rows)[["panel", "document_type", "source_year", "page"]].to_string(index=False))
