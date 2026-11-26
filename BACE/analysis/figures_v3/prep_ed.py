"""Data preparation for Extended Data Figs 1–3 (saved outputs only; no model calls).

Writes tidy CSVs (Source Data) to BACE/analysis/outputs/figures_v3/ed_data/.
  ED Fig. 1  sample composition: sector eligibility and allocation, countries,
             source availability of the 30 selected companies by source year.
  ED Fig. 2  evidence time windows: admissible source years by target year and the
             evidence cards actually supplied to the 1,798 evaluated cases.
  ED Fig. 3  primary diagnoses by disclosure task.

    BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_ed.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SNAP = ROOT / "BACE/analysis/outputs/snapshot"
REV = ROOT / "BACE/analysis/outputs/revision_2026-11"
OUT = ROOT / "BACE/analysis/outputs/figures_v3/ed_data"
OUT.mkdir(parents=True, exist_ok=True)
DIAG = ["non_disclosure_statement", "contradiction", "evidence_conflation",
        "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty"]

m = pd.read_csv(SNAP / "metrics.csv")
m = m[(m.bace_complete == True) & (m.ragchecker_complete == True) & (m.ragas_complete == True)].copy()
assert len(m) == 1798

# ---------------------------------------------------------------- ED Fig. 1
sample = json.loads((SNAP / "sample.json").read_text())
sel = pd.read_csv(SNAP / "selection.csv")
assert len(sel) == sample["population_count"] == 600 and sel.eligible.sum() == sample["eligible_count"] == 250
sec = pd.DataFrame({"sector": list(sample["eligible_counts"]),
                    "eligible": list(sample["eligible_counts"].values()),
                    "quota": [sample["quotas"][k] for k in sample["eligible_counts"]]})
sec["selected"] = sec.sector.map(sel[sel.selected].groupby("primary_sics_sector").size())
sec["population"] = sec.sector.map(sel.groupby("primary_sics_sector").size())
assert (sec.selected == sec.quota).all() and sec.selected.sum() == 30
sec.to_csv(OUT / "ed1a_sectors.csv", index=False)
cty = sel[sel.selected].country.value_counts().rename_axis("country").reset_index(name="companies")
cty.to_csv(OUT / "ed1b_countries.csv", index=False)
cov = pd.read_csv(SNAP / "coverage.csv")
cov = cov[cov.selected].merge(sel[["company_id", "primary_sics_sector"]], on="company_id")
assert cov.company_id.nunique() == 30 and cov.year.between(2015, 2023).all()
cov.to_csv(OUT / "ed1c_source_coverage.csv", index=False)

# ---------------------------------------------------------------- ED Fig. 2
win = []
for t in range(2019, 2024):
    for y in range(2015, 2024):
        metric = t - 4 <= y <= t
        pdf = t - 4 <= y <= t - 1
        win.append({"target_year": t, "source_year": y, "metric_admissible": metric, "pdf_admissible": pdf})
pd.DataFrame(win).to_csv(OUT / "ed2a_windows.csv", index=False)
vis = pd.read_csv(SNAP / "visible.csv")
vis = vis[vis.generation_case_id.isin(m.generation_case_id)].copy()
vis["lag"] = vis.target_year - vis.source_year
assert vis.lag.between(0, 4).all()
assert (vis[vis.type != "CSV metric"].lag >= 1).all()       # PDF cards never come from the target year
lag = vis.groupby(["type", "lag"]).size().rename("cards").reset_index()
lag.to_csv(OUT / "ed2b_supplied_by_lag.csv", index=False)
per = vis.groupby(["generation_case_id", "type"]).size().unstack(fill_value=0)
per = per.reindex(m.generation_case_id, fill_value=0).stack().rename("cards").reset_index()
cnt = per.groupby(["type", "cards"]).size().rename("cases").reset_index()
cnt.to_csv(OUT / "ed2c_cards_per_case.csv", index=False)
tgt = vis.assign(target_metric=(vis.lag == 0) & (vis.type == "CSV metric")).groupby("generation_case_id").target_metric.any()
print("cases with >=1 target-year metric card:", tgt.sum(), "of", len(m))

# ---------------------------------------------------------------- ED Fig. 3
claims = pd.read_csv(SNAP / "claims.csv").merge(m[["generation_case_id", "task_id", "task_title"]], on="generation_case_id")
un = claims[claims.label.isin(DIAG)]
assert len(un) == 42646
d = un.groupby(["task_id", "task_title", "label"]).size().rename("dcs").reset_index()
d["share_pct"] = 100 * d.dcs / d.groupby("task_id").dcs.transform("sum")
top = d.loc[d.groupby("task_id").dcs.idxmax()].set_index("task_id").label
ref = pd.read_csv(REV / "06_fbd_top_tasks.csv").query("task_id != 'ALL'").set_index("task_id")
assert ((top == "factual_boundary_distortion") == ref.observed_fbd_top.astype(str).eq("True")).all()
assert (top == "factual_boundary_distortion").sum() == 11
d["top_in_task"] = d.task_id.map(top) == d.label
d.to_csv(OUT / "ed3_diagnosis_by_task.csv", index=False)
print(top.to_string())
