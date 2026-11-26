"""Revision analyses (2026-11) computed from saved main_v1 outputs only.

No model calls. Reads the frozen snapshot CSVs and the per-case saved BACE outputs,
writes everything to BACE/analysis/outputs/revision_2026-11/. Boundary-type and
importance rules come from coding_rules_v1.json, frozen before this script first ran.

Run from the repository root:
    BACE/.venv/bin/python -B BACE/analysis/revision_2026-11/run_revision_analyses.py
"""
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
BACE = ROOT / "BACE"
SNAP = BACE / "analysis/outputs/snapshot"
CASES = BACE / "results/main_v1/cases"
HERE = Path(__file__).resolve().parent
OUT = BACE / "analysis/outputs/revision_2026-11"
OUT.mkdir(parents=True, exist_ok=True)
RULES_PATH = HERE / "coding_rules_v1.json"
RULES_SHA = "dda4981fff550c3bbac4e37a19c0a835f116f70a6f793f9d66a33ae02715adbc"
SEED, DRAWS = 20260921, 2000  # identical to the main report's bootstrap
SAMPLE_SEED = 20261125
SUPPORTED = {"direct", "inferred"}
DIAG = ["non_disclosure_statement", "contradiction", "evidence_conflation",
        "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if sha(RULES_PATH) != RULES_SHA:
    sys.exit("coding_rules_v1.json changed after freezing; create a new version instead.")
RULES = json.loads(RULES_PATH.read_text())


def norm(text):
    return " ".join(unicodedata.normalize("NFKC", str(text)).casefold().split())


YEAR = re.compile(RULES["year_pattern"])


def years(text):
    return {int(y) for y in YEAR.findall(str(text))}


# ---------------------------------------------------------------- bootstrap
def interval(companies, values):
    """Company-cluster percentile bootstrap, mirroring prepare_report.interval()."""
    grouped = defaultdict(list)
    for company, value in zip(companies, values):
        grouped[company].append(float(value))
    ordered = [grouped[c] for c in sorted(grouped)]
    totals = np.array([sum(v) for v in ordered])
    counts = np.array([len(v) for v in ordered])
    positions = np.random.default_rng(SEED).integers(0, len(ordered), size=(DRAWS, len(ordered)))
    reps = totals[positions].sum(axis=1) / counts[positions].sum(axis=1)
    low, high = np.quantile(reps, [0.025, 0.975])
    return {"estimate": totals.sum() / counts.sum(), "low": low, "high": high,
            "companies": len(ordered), "n": int(counts.sum())}


def write(name, rows):
    pd.DataFrame(rows).to_csv(OUT / name, index=False)


# ---------------------------------------------------------------- load
metrics = pd.read_csv(SNAP / "metrics.csv")
cohort = metrics[(metrics.bace_complete == True) & (metrics.ragchecker_complete == True)
                 & (metrics.ragas_complete == True)].copy()
assert len(cohort) == 1798, len(cohort)
case_info = cohort.set_index("generation_case_id")[["company_id", "year", "task_id"]]
claims = pd.read_csv(SNAP / "claims.csv")
claims = claims[claims.generation_case_id.isin(cohort.generation_case_id)].copy()
assert len(claims) == 94955, len(claims)
ext = pd.read_csv(SNAP / "external_claims.csv")
ext = ext[ext.generation_case_id.isin(cohort.generation_case_id)].copy()

# Per-case saved outputs: candidate EC card types/years and diagnosis rationales.
cand_rows, rationale = {}, {}
for case in cohort.generation_case_id:
    d = CASES / case
    ec = {}
    with open(d / "bace/dedup/ec_claims.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            ec[r["ec_id"]] = ([c.split("::")[0] for c in r["evidence_card_ids"]],
                              {int(p) for c in r["evidence_card_ids"] for p in c.split("::") if re.fullmatch(r"(19|20)\d\d", p)})
    with open(d / "bace/candidates/dc_candidate_ecs.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            types, yrs = set(), set()
            for e in r["candidate_ec_ids"]:
                types.update(ec[e][0]); yrs.update(ec[e][1])
            cand_rows[(case, r["dc_claim_id"])] = (types, yrs)
    with open(d / "bace/diagnosis/dc_unsupported_diagnoses.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            rationale[(case, r["dc_claim_id"])] = (r["unsupported_label"], r["rationale"])

# ---------------------------------------------------------------- per-DC derived table
qt = RULES["importance_strata"]["Q_text"]
REMOVE = [re.compile(p) for p in qt["remove_patterns"]]
QUANT = re.compile(qt["quantity_pattern"])


def q_text(text):
    t = norm(text)
    for p in REMOVE:
        t = p.sub(" ", t)
    return bool(QUANT.search(t))


rows = []
for r in claims.itertuples(index=False):
    info = case_info.loc[r.generation_case_id]
    ty = int(info.year)
    types, cyears = cand_rows.get((r.generation_case_id, r.dc_id), (set(), set()))
    ys = years(r.dc_text)
    lab_rat = rationale.get((r.generation_case_id, r.dc_id))
    if r.label not in SUPPORTED:
        assert lab_rat and lab_rat[0] == r.label, (r.generation_case_id, r.dc_id)
    rows.append({
        "generation_case_id": r.generation_case_id, "dc_id": r.dc_id, "dc_text": r.dc_text,
        "company_id": info.company_id, "task_id": info.task_id, "topic": info.task_id[0],
        "target_year": ty, "label": r.label, "supported": r.label in SUPPORTED,
        "candidate_count": int(r.candidate_count),
        "year_in_text": "target_year" if ty in ys else ("other_year_only" if ys else "no_year"),
        "cand_years": "no_candidates" if int(r.candidate_count) == 0 else (
            "includes_target_year" if ty in cyears else ("only_earlier_years" if cyears and max(cyears) < ty else "other")),
        "Q_text": q_text(r.dc_text),
        "Q_evidence": bool(types & {"csv", "pdf_table_row"}),
        "rationale": lab_rat[1] if lab_rat else "",
    })
dc = pd.DataFrame(rows)
assert dc.label.isin(DIAG).sum() == 42646

# ---------------------------------------------------------------- 1. exact-text pairs
left = dc.copy()
left["key"] = left.dc_text.map(lambda t: " ".join(str(t).casefold().split()))  # notebook 03 normalisation
summary, breakdown = [], []
for fw in ["ragchecker", "ragas"]:
    right = ext[ext.framework == fw].copy()
    right["key"] = right.claim_text.map(lambda t: " ".join(str(t).casefold().split()))
    keys = ["generation_case_id", "key"]
    lu = left[~left.duplicated(keys, keep=False)]
    ru = right[~right.duplicated(keys, keep=False)]
    m = lu.merge(ru[keys + ["supported"]].rename(columns={"supported": "ext_supported"}), on=keys, validate="one_to_one")
    m["ext_supported"] = m.ext_supported.astype(str) == "True"
    cell = Counter(zip(m.supported, m.ext_supported))
    gap = interval(m.company_id, (m.ext_supported.astype(int) - m.supported.astype(int)))
    summary.append({"framework": fw, "bace_dcs": len(left), "matched_pairs": len(m),
                    "coverage": len(m) / len(left), "bace_supported_rate": m.supported.mean(),
                    "external_supported_rate": m.ext_supported.mean(), "gap_pp": 100 * gap["estimate"],
                    "gap_low_pp": 100 * gap["low"], "gap_high_pp": 100 * gap["high"],
                    "agreement": (m.supported == m.ext_supported).mean(),
                    "both_supported": cell[(True, True)], "bace_only_unsupported": cell[(False, True)],
                    "external_only_unsupported": cell[(True, False)], "both_unsupported": cell[(False, False)]})
    for dim in ["label", "year_in_text", "cand_years", "Q_text", "Q_evidence", "topic", "task_id"]:
        for lev, g in m.groupby(dim):
            breakdown.append({"framework": fw, "dimension": dim, "level": lev, "pairs": len(g),
                              "bace_supported_rate": g.supported.mean(),
                              "external_supported_rate": g.ext_supported.mean(),
                              "gap_pp": 100 * (g.ext_supported.mean() - g.supported.mean()),
                              "bace_only_unsupported": int((~g.supported & g.ext_supported).sum()),
                              "external_only_unsupported": int((g.supported & ~g.ext_supported).sum())})
    m[["generation_case_id", "dc_id", "dc_text", "label", "supported", "ext_supported", "year_in_text", "cand_years"]].to_csv(
        OUT / f"01_exact_pairs_{fw}.csv", index=False)
write("01_exact_pairs_summary.csv", summary)
write("01_exact_pairs_breakdown.csv", breakdown)

# ---------------------------------------------------------------- 2. year in DC text
yr = []
for lab, g in dc.groupby("label"):
    c = g.year_in_text.value_counts()
    yr.append({"label": lab, "dcs": len(g), **{k: int(c.get(k, 0)) for k in ["target_year", "other_year_only", "no_year"]},
               **{f"share_{k}": c.get(k, 0) / len(g) for k in ["target_year", "other_year_only", "no_year"]}})
for name, g in [("ALL_SUPPORTED", dc[dc.supported]), ("ALL_UNSUPPORTED", dc[~dc.supported]), ("ALL", dc)]:
    c = g.year_in_text.value_counts()
    yr.append({"label": name, "dcs": len(g), **{k: int(c.get(k, 0)) for k in ["target_year", "other_year_only", "no_year"]},
               **{f"share_{k}": c.get(k, 0) / len(g) for k in ["target_year", "other_year_only", "no_year"]}})
write("02_year_in_text_by_label.csv", yr)
sup_by_year = []
for lev, g in dc.groupby("year_in_text"):
    ci = interval(g.company_id, g.supported.astype(int))
    sup_by_year.append({"year_in_text": lev, "dcs": len(g), "pooled_support": ci["estimate"], "low": ci["low"], "high": ci["high"]})
write("02_support_by_year_in_text.csv", sup_by_year)

# ---------------------------------------------------------------- 3. diagnosis by candidate count
bins = pd.cut(dc.candidate_count, [-1, 0, 1, 4, 9, 10**6], labels=["0", "1", "2-4", "5-9", "10+"])
dc["cand_bin"] = bins.astype(str)
cb = []
for lev in ["0", "1", "2-4", "5-9", "10+"]:
    g = dc[dc.cand_bin == lev]; u = g[~g.supported]; c = u.label.value_counts()
    cb.append({"candidate_bin": lev, "dcs": len(g), "support_rate": g.supported.mean(), "unsupported": len(u),
               **{lab: int(c.get(lab, 0)) for lab in DIAG}, **{f"share_{lab}": c.get(lab, 0) / max(len(u), 1) for lab in DIAG}})
write("03_diagnosis_by_candidate_bin.csv", cb)

# ---------------------------------------------------------------- 4. boundary-type coding
bt = RULES["boundary_types"]
TEMP = re.compile(bt["period_broad"]["temporal_phrase_pattern"])
PAT = {k: re.compile(bt[k]["pattern"]) for k in ["entity", "scope", "metric"]}


def code(rat, ty):
    t = norm(rat); ys = years(t)
    strict = ty in ys and any(y != ty for y in ys)
    out = {"period_strict": strict, "period_broad": strict or any(y != ty for y in ys) or bool(TEMP.search(t))}
    out.update({k: bool(p.search(t)) for k, p in PAT.items()})
    return out


coded = []
for lab in ["factual_boundary_distortion", "evidence_conflation"]:
    g = dc[dc.label == lab].copy()
    codes = pd.DataFrame([code(r, t) for r, t in zip(g.rationale, g.target_year)], index=g.index)
    g = pd.concat([g, codes], axis=1)
    for k in ["period_strict", "period_broad", "entity", "scope", "metric"]:
        ci = interval(g.company_id, g[k].astype(int))
        coded.append({"diagnosis": lab, "code": k, "dcs": len(g), "count": int(g[k].sum()),
                      "share": ci["estimate"], "low": ci["low"], "high": ci["high"]})
    non_period = ~g.period_broad & (g.entity | g.scope | g.metric)
    for name, mask in [("period_strict_only_no_other_code", g.period_strict & ~(g.entity | g.scope | g.metric)),
                       ("no_period_broad_but_other_code", non_period),
                       ("no_code", ~(g.period_broad | g.entity | g.scope | g.metric)),
                       ("cand_only_earlier_years", g.cand_years == "only_earlier_years"),
                       ("cand_includes_target_year", g.cand_years == "includes_target_year")]:
        coded.append({"diagnosis": lab, "code": name, "dcs": len(g), "count": int(mask.sum()), "share": mask.mean()})
    if lab == "factual_boundary_distortion":
        combo = g[["period_strict", "entity", "scope", "metric"]].apply(
            lambda r: "+".join([k for k in ["period_strict", "entity", "scope", "metric"] if r[k]]) or "none", axis=1)
        write("04_fbd_code_combinations.csv",
              [{"combination": k, "count": int(v), "share": v / len(g)} for k, v in combo.value_counts().items()])
        idx = np.random.default_rng(SAMPLE_SEED).choice(len(g), size=200, replace=False)
        s = g.iloc[sorted(idx)][["generation_case_id", "dc_id", "target_year", "dc_text", "rationale",
                                 "period_strict", "period_broad", "entity", "scope", "metric", "cand_years"]].copy()
        for k in ["check_period", "check_entity", "check_scope", "check_metric", "check_note"]:
            s[k] = ""
        s.to_csv(OUT / "04_validation_sample_fbd200.csv", index=False)
write("04_boundary_coding_shares.csv", coded)

# ---------------------------------------------------------------- 5. importance strata and topics
imp = []
for dim in ["Q_text", "Q_evidence"]:
    for lev, g in dc.groupby(dim):
        ci = interval(g.company_id, g.supported.astype(int)); u = g[~g.supported]; c = u.label.value_counts()
        imp.append({"stratum": dim, "level": lev, "dcs": len(g), "pooled_support": ci["estimate"], "low": ci["low"],
                    "high": ci["high"], **{f"share_{lab}": c.get(lab, 0) / max(len(u), 1) for lab in DIAG}})
ct = pd.crosstab(dc.Q_text, dc.Q_evidence)
write("05_importance_strata.csv", imp)
ct.to_csv(OUT / "05_importance_crosstab.csv")
topic = []
for t, g in cohort.groupby(cohort.task_id.str[0]):
    for col in ["bace_support_rate_all_dc", "ragchecker_faithfulness", "ragas_faithfulness", "bace_eccr"]:
        ci = interval(g.company_id, g[col])
        topic.append({"topic": t, "metric": col, "disclosures": len(g), "mean": ci["estimate"], "low": ci["low"], "high": ci["high"]})
    gd = dc[dc.topic == t]; ci = interval(gd.company_id, gd.supported.astype(int))
    topic.append({"topic": t, "metric": "pooled_dc_support", "disclosures": len(g), "mean": ci["estimate"], "low": ci["low"], "high": ci["high"]})
write("05_topic_results.csv", topic)

# ---------------------------------------------------------------- 6. intervals and secondary measures
iv = []
def add(name, companies, values, note=""):
    ci = interval(companies, values)
    iv.append({"measure": name, "estimate": ci["estimate"], "low": ci["low"], "high": ci["high"], "n": ci["n"], "note": note})

add("mean_eccr", cohort.company_id, cohort.bace_eccr, "unweighted disclosure mean")
add("mean_direct_only_support", cohort.company_id, cohort.bace_supported_direct / cohort.bace_dc_count, "direct DCs / all DCs")
inf = cohort.dropna(subset=["bace_inference_rate"])
add("mean_inference_rate", inf.company_id, inf.bace_inference_rate, "inferred / supported; undefined excluded")
add("pooled_inferred_share_of_supported", dc[dc.supported].company_id, (dc[dc.supported].label == "inferred").astype(int))
add("mean_support_excl_non_disclosure", cohort.dropna(subset=["bace_support_rate_excluding_non_disclosure_sensitivity"]).company_id,
    cohort.dropna(subset=["bace_support_rate_excluding_non_disclosure_sensitivity"]).bace_support_rate_excluding_non_disclosure_sensitivity)
un = dc[~dc.supported]
for lab in DIAG:
    add(f"diagnosis_share_{lab}", un.company_id, (un.label == lab).astype(int), "share of unsupported DCs")
add("diagnosis_share_fbd_plus_conflation", un.company_id, un.label.isin(["factual_boundary_distortion", "evidence_conflation"]).astype(int))
add("diagnosis_share_anchor_presupposing_81", un.company_id,
    un.label.isin(["factual_boundary_distortion", "evidence_conflation", "inferential_inflation", "contradiction"]).astype(int),
    "FBD + conflation + inflation + contradiction")
iv.append({"measure": "multi_ec_required_dc_count", "estimate": int(cohort.bace_multi_ec_required_dc_count.sum()), "note": "count; no interval"})

# Spearman rho with company-cluster bootstrap (resample companies, recompute rho on pooled disclosures)
comp_sorted = sorted(cohort.company_id.unique())
by_comp = {c: cohort[cohort.company_id == c] for c in comp_sorted}
pos = np.random.default_rng(SEED).integers(0, len(comp_sorted), size=(DRAWS, len(comp_sorted)))
pairs = [("bace_support_rate_all_dc", "ragchecker_faithfulness"), ("bace_support_rate_all_dc", "ragas_faithfulness"),
         ("ragchecker_faithfulness", "ragas_faithfulness")]
arrays = {c: by_comp[c][[p for pr in pairs for p in pr]].to_numpy() for c in comp_sorted}
cols = [p for pr in pairs for p in pr]
for i, (a, b) in enumerate(pairs):
    point = spearmanr(cohort[a], cohort[b]).correlation
    reps = []
    for draw in pos:
        stack = np.vstack([arrays[comp_sorted[j]] for j in draw])
        reps.append(spearmanr(stack[:, cols.index(a)], stack[:, cols.index(b)]).correlation)
    lo, hi = np.quantile(reps, [0.025, 0.975])
    iv.append({"measure": f"spearman_{a}__{b}", "estimate": point, "low": lo, "high": hi, "n": len(cohort)})
write("06_intervals.csv", iv)

# FBD as most frequent diagnosis per task, under company resampling
tasks = sorted(cohort.task_id.unique())
cidx = {c: i for i, c in enumerate(comp_sorted)}
C = np.zeros((len(comp_sorted), len(tasks), len(DIAG)))
for r in un.itertuples():
    C[cidx[r.company_id], tasks.index(r.task_id), DIAG.index(r.label)] += 1
fbd = DIAG.index("factual_boundary_distortion")
obs = (C.sum(0).argmax(1) == fbd)
draw_counts = np.array([(C[d].sum(0).argmax(1) == fbd).sum() for d in pos])
per_task = np.array([(C[d].sum(0).argmax(1) == fbd) for d in pos]).mean(0)
write("06_fbd_top_tasks.csv",
      [{"task_id": t, "observed_fbd_top": bool(o), "bootstrap_share_fbd_top": p} for t, o, p in zip(tasks, obs, per_task)]
      + [{"task_id": "ALL", "observed_fbd_top": int(obs.sum()),
          "bootstrap_share_fbd_top": f"P(>=11)={np.mean(draw_counts >= 11):.3f}; P(12)={np.mean(draw_counts == 12):.3f}; "
                                     f"P(<=10)={np.mean(draw_counts <= 10):.3f}; median={np.median(draw_counts)}"}])

# ---------------------------------------------------------------- manifest
manifest = {"created_by": "BACE/analysis/revision_2026-11/run_revision_analyses.py",
            "script_sha256": sha(__file__), "rules": str(RULES_PATH.relative_to(ROOT)), "rules_sha256": RULES_SHA,
            "inputs_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [SNAP / "metrics.csv", SNAP / "claims.csv", SNAP / "external_claims.csv"]},
            "per_case_inputs": "results/main_v1/cases/<case>/bace/{dedup/ec_claims.jsonl,candidates/dc_candidate_ecs.jsonl,diagnosis/dc_unsupported_diagnoses.jsonl}",
            "cohort_disclosures": len(cohort), "dcs": len(dc), "bootstrap": {"seed": SEED, "draws": DRAWS, "unit": "company"},
            "model_calls": 0, "outputs": sorted(p.name for p in OUT.glob("*.csv"))}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
print("done", len(dc))
