"""Data preparation for Fig. 2 (saved outputs only; no model calls).

Writes tidy CSVs (also the per-panel Source Data) to
BACE/analysis/outputs/figures_v3/fig2_data/. Bootstrap replicates use the main
report's procedure exactly: company clusters, 2,000 draws, numpy default_rng(20260921).

    BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_fig2.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SNAP = ROOT / "BACE/analysis/outputs/snapshot"
REV = ROOT / "BACE/analysis/outputs/revision_2026-11"
OUT = ROOT / "BACE/analysis/outputs/figures_v3/fig2_data"
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


m = pd.read_csv(SNAP / "metrics.csv")
m = m[(m.bace_complete == True) & (m.ragchecker_complete == True) & (m.ragas_complete == True)].copy()
assert len(m) == 1798

# a: disclosure scores
a = m[["generation_case_id", "company_id"]].copy()
a["BACE"] = 100 * m.bace_support_rate_all_dc
a["RAGChecker"] = 100 * m.ragchecker_faithfulness
a["RAGAS"] = 100 * m.ragas_faithfulness
a.melt(id_vars=["generation_case_id", "company_id"], var_name="framework", value_name="score_pct").to_csv(
    OUT / "a_scores.csv", index=False)

# b: paired differences with bootstrap replicates (must reproduce the reported intervals)
rows, reps = [], []
for k, col in [("RAGChecker", "ragchecker_faithfulness"), ("RAGAS", "ragas_faithfulness")]:
    est, r = replicates(m.company_id, 100 * (m.bace_support_rate_all_dc - m[col]))
    lo, hi = np.quantile(r, [0.025, 0.975])
    rows.append({"comparison": f"BACE − {k}", "comparator": k, "mean_pp": est, "low_pp": lo, "high_pp": hi})
    reps.append(pd.DataFrame({"comparison": f"BACE − {k}", "comparator": k, "replicate_pp": r}))
b = pd.DataFrame(rows)
assert np.allclose(b.mean_pp.round(1), [-34.9, -35.3]) and np.allclose(b.low_pp.round(1), [-36.2, -36.5])
b.to_csv(OUT / "b_paired_summary.csv", index=False)
pd.concat(reps).to_csv(OUT / "b_paired_bootstrap.csv", index=False)

# c: disclosure-level pairs
c = []
for k in ["RAGChecker", "RAGAS"]:
    d = pd.DataFrame({"generation_case_id": a.generation_case_id, "comparator": k,
                      "comparator_pct": a[k], "bace_pct": a.BACE})
    d["full_native_low_bace"] = (d.comparator_pct >= 99.999) & (d.bace_pct < 50)
    c.append(d)
pd.concat(c).to_csv(OUT / "c_scatter.csv", index=False)

# e: identical claims by stated year
pairs = pd.read_csv(REV / "01_exact_pairs_ragas.csv").merge(m[["generation_case_id", "company_id"]], on="generation_case_id")
assert len(pairs) == 5709
labels = {"no_year": "No year stated", "target_year": "Target year stated", "other_year_only": "Other year only"}
e, er = [], []
for g, lab in labels.items():
    sub = pairs[pairs.year_in_text == g]
    for k, col in [("BACE", "supported"), ("RAGAS", "ext_supported")]:
        est, r = replicates(sub.company_id, 100 * sub[col].astype(int))
        lo, hi = np.quantile(r, [0.025, 0.975])
        e.append({"group": lab, "framework": k, "n_pairs": len(sub), "supported_pct": est, "low_pct": lo, "high_pct": hi})
        er.append(pd.DataFrame({"group": lab, "framework": k, "replicate_pct": r}))
    est, r = replicates(sub.company_id, 100 * (sub.ext_supported.astype(int) - sub.supported.astype(int)))
    lo, hi = np.quantile(r, [0.025, 0.975])
    e.append({"group": lab, "framework": "Difference", "n_pairs": len(sub), "supported_pct": est, "low_pct": lo, "high_pct": hi})
pd.DataFrame(e).to_csv(OUT / "e_identical_claims.csv", index=False)
pd.concat(er).to_csv(OUT / "e_identical_bootstrap.csv", index=False)
print("written", OUT)
