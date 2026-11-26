"""Data preparation for Fig. 3 (saved outputs only; no model calls).

Writes tidy CSVs (also the per-panel Source Data) to
BACE/analysis/outputs/figures_v3/fig3_data/. Intervals use the main report's
procedure exactly: company clusters, 2,000 draws, numpy default_rng(20260921),
ratio of sums. The quantity classifier is read from the frozen
coding_rules_v1.json (checked by hash) and must reproduce 05_importance_strata.csv.

    BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_fig3.py
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SNAP = ROOT / "BACE/analysis/outputs/snapshot"
REV = ROOT / "BACE/analysis/outputs/revision_2026-11"
RULES_PATH = ROOT / "BACE/analysis/revision_2026-11/coding_rules_v1.json"
RULES_SHA = "dda4981fff550c3bbac4e37a19c0a835f116f70a6f793f9d66a33ae02715adbc"
OUT = ROOT / "BACE/analysis/outputs/figures_v3/fig3_data"
OUT.mkdir(parents=True, exist_ok=True)
SEED, DRAWS = 20260921, 2000


def replicates(companies, values):
    grouped = {}
    for c, v in zip(companies, values):
        grouped.setdefault(c, []).append(float(v))
    ordered = [grouped[c] for c in sorted(grouped)]
    tot = np.array([sum(v) for v in ordered]); cnt = np.array([len(v) for v in ordered])
    pos = np.random.default_rng(SEED).integers(0, len(ordered), size=(DRAWS, len(ordered)))
    return tot.sum() / cnt.sum(), tot[pos].sum(1) / cnt[pos].sum(1)


def summary(companies, values):
    est, r = replicates(companies, values)
    lo, hi = np.quantile(r, [0.025, 0.975])
    return est, lo, hi, r


m = pd.read_csv(SNAP / "metrics.csv")
m = m[(m.bace_complete == True) & (m.ragchecker_complete == True) & (m.ragas_complete == True)].copy()
assert len(m) == 1798
m["topic"] = m.task_id.str[0]

# a: DC label composition
claims = pd.read_csv(SNAP / "claims.csv")
claims = claims[claims.generation_case_id.isin(m.generation_case_id)].copy()
assert len(claims) == 94955
grp = claims.label.map(lambda l: l if l in ("direct", "inferred") else "unsupported")
a = grp.value_counts().rename_axis("label").reset_index(name="dcs")
a["share_pct"] = 100 * a.dcs / a.dcs.sum()
a = a.set_index("label").loc[["direct", "inferred", "unsupported"]].reset_index()
assert a.dcs.tolist() == [34430, 17879, 42646]
a.to_csv(OUT / "a_label_composition.csv", index=False)

# b, d: disclosure-level support rate and ECCR
bd = m[["generation_case_id", "company_id", "task_id", "topic"]].copy()
bd["support_pct"] = 100 * m.bace_support_rate_all_dc
bd["eccr_pct"] = 100 * m.bace_eccr
bd.to_csv(OUT / "bd_disclosure_metrics.csv", index=False)
q = bd.support_pct.quantile([.25, .5, .75]).round(1).tolist()
assert q == [45.2, 55.6, 65.9], q
est, lo, hi, _ = summary(m.company_id, 100 * m.bace_eccr)
assert [round(x, 1) for x in (est, lo, hi)] == [34.3, 31.8, 36.7], (est, lo, hi)
assert bd.eccr_pct.quantile([.25, .5, .75]).round(1).tolist() == [23.7, 32.3, 42.9]
ds = []
for k, col in [("support", "support_pct"), ("eccr", "eccr_pct")]:
    est, lo, hi, _ = summary(bd.company_id, bd[col])
    qq = bd[col].quantile([.25, .5, .75]).tolist()
    ds.append({"metric": k, "mean_pct": est, "low_pct": lo, "high_pct": hi,
               "q25_pct": qq[0], "median_pct": qq[1], "q75_pct": qq[2], "disclosures": len(bd)})
pd.DataFrame(ds).to_csv(OUT / "bd_summary.csv", index=False)

# c: task means with company-cluster intervals; topic means for reference lines
c, cr = [], []
for (tid, title), g in m.groupby(["task_id", "task_title"]):
    est, lo, hi, r = summary(g.company_id, 100 * g.bace_support_rate_all_dc)
    c.append({"task_id": tid, "task_title": title, "topic": tid[0], "disclosures": len(g),
              "mean_pct": est, "low_pct": lo, "high_pct": hi})
    cr.append(pd.DataFrame({"task_id": tid, "topic": tid[0], "replicate_pct": r}))
c = pd.DataFrame(c)
assert round(c.mean_pct.min(), 1) == 43.9 and round(c.mean_pct.max(), 1) == 62.5
c.to_csv(OUT / "c_task_means.csv", index=False)
pd.concat(cr).to_csv(OUT / "c_task_bootstrap.csv", index=False)
topic = pd.read_csv(REV / "05_topic_results.csv")
topic = topic[topic.metric == "bace_support_rate_all_dc"].copy()
for k in ["mean", "low", "high"]:
    topic[k + "_pct"] = 100 * topic[k]
topic[["topic", "disclosures", "mean_pct", "low_pct", "high_pct"]].to_csv(OUT / "c_topic_means.csv", index=False)

# e: quantitative versus narrative DCs (pooled support)
assert hashlib.sha256(RULES_PATH.read_bytes()).hexdigest() == RULES_SHA
qt = json.loads(RULES_PATH.read_text())["importance_strata"]["Q_text"]
REMOVE = [re.compile(p) for p in qt["remove_patterns"]]
QUANT = re.compile(qt["quantity_pattern"])


def q_text(text):
    t = " ".join(unicodedata.normalize("NFKC", str(text)).casefold().split())
    for p in REMOVE:
        t = p.sub(" ", t)
    return bool(QUANT.search(t))


claims = claims.merge(m[["generation_case_id", "company_id"]], on="generation_case_id")
claims["quant"] = claims.dc_text.map(q_text)
claims["supported"] = claims.label.isin(["direct", "inferred"]).astype(int)
ref = pd.read_csv(REV / "05_importance_strata.csv").query("stratum == 'Q_text'").set_index("level")
e, er = [], []
for lev, lab in [(True, "Quantity stated"), (False, "No quantity stated")]:
    g = claims[claims.quant == lev]
    est, lo, hi, r = summary(g.company_id, 100 * g.supported)
    row = ref.loc[lev]
    assert len(g) == row.dcs and np.allclose([est, lo, hi], 100 * row[["pooled_support", "low", "high"]].astype(float))
    comp = g.label.map(lambda l: l if l in ("direct", "inferred") else "unsupported").value_counts(normalize=True)
    e.append({"group": lab, "dcs": len(g), "supported_pct": est, "low_pct": lo, "high_pct": hi,
              "direct_pct": 100 * comp.get("direct", 0), "inferred_pct": 100 * comp.get("inferred", 0)})
    er.append(pd.DataFrame({"group": lab, "replicate_pct": r}))
pd.DataFrame(e).to_csv(OUT / "e_quantity_support.csv", index=False)
pd.concat(er).to_csv(OUT / "e_quantity_bootstrap.csv", index=False)
print("ok", OUT)
