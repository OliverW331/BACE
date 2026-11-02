"""Render Figure 2 using saved BACE results; never mutate experiment artifacts.

Descriptive quantities are independently checked. Bootstrap endpoints are copied
from saved exports, not re-estimated. No model calls or hypothesis tests are run.
"""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import ScaledTranslation
import numpy as np

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
ART = ROOT / "paper/manuscript/figures"
SCRIPTS = Path("/home/muwang/.codex/skills/nature-figure/scripts")
sys.path.insert(0, str(SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment

INPUTS = {}
SNAPSHOT = "BACE/analysis/outputs/snapshot/metrics.csv"
PREFIX = "BACE/analysis/outputs/figures/"
INK, BLUE, PALE_BLUE, AMBER = "#263746", "#38657D", "#8DB6C9", "#C89955"
TOPICS = ["Transition plans", "Climate actions and resources", "Climate targets", "GHG emissions",
          "Workforce policies", "Workforce actions and resources", "Workforce targets", "Health and safety",
          "Business conduct policies", "Supplier relationships", "Anti-corruption controls", "Corruption or bribery incidents"]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(2**20):
            h.update(block)
    return h.hexdigest()


def register(relative):
    path = ROOT / relative
    INPUTS[relative] = {"sha256": sha(path), "bytes": path.stat().st_size}
    return path


def read_csv(relative):
    with register(relative).open(newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(relative):
    return json.loads(register(relative).read_text())


def save_csv(name, rows):
    with (OUT/name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def data():
    rows = read_csv(SNAPSHOT)
    complete = [r for r in rows if r["bace_complete"].lower() == "true"]
    omitted = [r for r in rows if r["bace_complete"].lower() != "true"]
    execution = read_json("BACE/results/main_v1/execution_status.json")
    ids = [r["generation_case_id"] for r in complete]
    assert len(set(ids)) == len(ids) == 1798
    assert len(rows) == 1800 and len(omitted) == 2
    assert set(ids) == set(execution["completed_case_ids"])
    assert len({r["company_id"] for r in complete}) == 30
    assert all(r["bace_support_rate_all_dc"] == "" for r in omitted)
    assert all(r["ragas_faithfulness"] and r["ragchecker_faithfulness"] for r in complete)
    scores = np.array([float(r["bace_support_rate_all_dc"]) for r in complete])
    assert np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()
    exported = read_csv(PREFIX+"01/01_support_distribution__disclosures.csv")
    exported_by_id = {r["generation_case_id"]: r for r in exported}
    assert len(exported) == len(exported_by_id) == len(ids) and set(exported_by_id) == set(ids)
    for r, score in zip(complete, scores):
        saved = exported_by_id[r["generation_case_id"]]
        assert r["company_id"] == saved["company_id"]
        assert abs(score-float(saved["bace_support_rate_all_dc"])) < 1e-12
        counts = [int(float(r[c])) for c in ["bace_supported_direct", "bace_supported_inferred", "bace_unsupported"]]
        assert sum(counts) == int(float(r["bace_dc_count"])) > 0
        assert abs((counts[0]+counts[1])/sum(counts)-score) < 1e-12
    summary = next(r for r in read_csv(PREFIX+"03/03_native_comparison__cohort_summary.csv")
                   if r["method"] == "BACE" and r["cohort"] == "Common")
    assert abs(scores.mean()-float(summary["mean"])) < 1e-12
    assert [int(summary[k]) for k in ["companies", "disclosures", "draws"]] == [30, 1798, 2000]
    claims = read_csv(PREFIX+"01/01_support_distribution__claim_counts.csv")
    total = sum(int(float(r["bace_dc_count"])) for r in complete)
    assert total == 94955
    columns = {"Direct": "bace_supported_direct", "Inferred": "bace_supported_inferred", "Unsupported": "bace_unsupported"}
    assert [r["status"] for r in claims] == list(columns)
    claim_table = []
    for r in claims:
        count = sum(int(float(row[columns[r["status"]]])) for row in complete)
        percent = 100*count/total
        assert count == int(float(r["count"])) and abs(percent-float(r["percent_all_dc"])) < 1e-10
        claim_table.append(dict(category=r["status"], count=count, denominator=total, percent=percent,
                                status="COMPUTED_VERIFIED", source=SNAPSHOT, column=columns[r["status"]]))
    tasks = read_csv(PREFIX+"01/01_task_support__data.csv")
    specs = read_json("BACE/config/tasks.json")["tasks"]
    assert [r["task"] for r in tasks] == [s["esrs_reference"] for s in specs]
    assert len(tasks) == len(TOPICS) == 12
    task_table = []
    for r, spec, topic in zip(tasks, specs, TOPICS):
        cohort = [row for row in complete if row["task"] == r["task"]]
        mean = np.mean([float(row["bace_support_rate_all_dc"]) for row in cohort])
        n = len(cohort)
        assert abs(mean-float(r["mean"])) < 1e-12
        assert len({row["company_id"] for row in cohort}) == int(r["companies"]) == 30
        assert n == int(r["disclosures"]) == (149 if r["task"] in ["S1-1", "S1-5"] else 150)
        assert int(r["draws"]) == 2000 and float(r["low"]) <= mean <= float(r["high"])
        task_table.append(dict(task=r["task"], topic=topic, full_task_name=spec["task_name"],
                               mean_percent=100*mean, low_percent=100*float(r["low"]), high_percent=100*float(r["high"]),
                               disclosures=n, companies=30, bootstrap_draws=2000, seed=20260921,
                               mean_status="COMPUTED_VERIFIED", interval_status="SOURCE_REPORTED",
                               interval_source=PREFIX+"01/01_task_support__data.csv"))
    analysis_code = register("BACE/analysis/analysis_data.py").read_text()
    assert "SEED = 20260921" in analysis_code and "np.quantile(replicates,[.025,.975])" in analysis_code
    register("BACE/analysis/ANALYSIS_SPEC.md")
    verified = read_json("paper/analysis/results_draft/verified_numbers.json")["support"]
    assert abs(verified["macro_pct"]-100*scores.mean()) < 1e-10
    assert verified["total_dc"] == total
    assert verified["counts"] == {r["category"]: r["count"] for r in claim_table}
    assert np.allclose(verified["saved_95_interval_pct"], [100*float(summary["low"]), 100*float(summary["high"])], rtol=0, atol=1e-10)
    # No binning in rounded percent values: use the unrounded saved proportions.
    # Divide integer percentage boundaries rather than multiplying a floating
    # step: linspace can put the 60% edge at 0.6000000000000001 and mis-bin 3/5.
    edges = np.arange(0, 101, 5)/100
    histogram, _ = np.histogram(scores, bins=edges)
    assert int(histogram.sum()) == len(complete)
    exact_bins = [min(19, 20*(int(float(r["bace_supported_direct"])) + int(float(r["bace_supported_inferred"])))
                         // int(float(r["bace_dc_count"]))) for r in complete]
    assert np.array_equal(histogram, np.bincount(exact_bins, minlength=20)), "Bin assignments must match exact integer claim ratios"
    save_csv("histogram.csv", [dict(left_percent=100*edges[i], right_percent=100*edges[i+1],
                                   closure="both" if i == len(histogram)-1 else "left", count=int(count),
                                   status="COMPUTED_VERIFIED") for i, count in enumerate(histogram)])
    save_csv("disclosures.csv", [dict(generation_case_id=r["generation_case_id"], company_id=r["company_id"],
                                      company_name=r["company_name"], year=r["year"], task=r["task"],
                                      support_rate_all_dc=r["bace_support_rate_all_dc"],
                                      dc_count=r["bace_dc_count"], direct=r["bace_supported_direct"],
                                      inferred=r["bace_supported_inferred"], unsupported=r["bace_unsupported"])
                                 for r in complete])
    save_csv("excluded_cases.csv", [dict(generation_case_id=r["generation_case_id"], company=r["company_name"],
                                        year=r["year"], task=r["task"], reason="Incomplete BACE assessment; no score imputation") for r in omitted])
    save_csv("claim_composition.csv", claim_table)
    save_csv("task_estimates.csv", task_table)
    overall = dict(disclosures=len(complete), companies=30, planned=len(rows), incomplete=len(omitted),
                   mean_percent=100*scores.mean(), low_percent=100*float(summary["low"]), high_percent=100*float(summary["high"]),
                   pooled_supported_count=claim_table[0]["count"]+claim_table[1]["count"], pooled_denominator=total,
                   pooled_support_percent=100*(claim_table[0]["count"]+claim_table[1]["count"])/total,
                   mean_status="COMPUTED_VERIFIED", interval_status="SOURCE_REPORTED", bootstrap_draws=2000, seed=20260921,
                   interval_source=PREFIX+"03/03_native_comparison__cohort_summary.csv", interval_locator="method=BACE; cohort=Common; low/high",
                   interval_method="95% percentile company-cluster bootstrap; all disclosures retained within each sampled company",
                   point_source=SNAPSHOT, point_rule="Arithmetic mean of completed disclosure support rates; direct plus inferred divided by all deduplicated DCs",
                   counts_source="claim_composition.csv", counts_rule="Sum DC counts across completed disclosures; denominator is the pooled all-DC count")
    (OUT/"verified_facts.json").write_text(json.dumps(overall, indent=2)+"\n")
    return scores, histogram, edges, overall, claim_table, task_table


def heading(ax, letter, title, subtitle):
    transform = ax.transAxes + ScaledTranslation(0, 25/72, ax.figure.dpi_scale_trans)
    ax.text(0, 1, letter, transform=transform, fontsize=8, fontweight="bold", ha="left", va="baseline", color=INK)
    ax.annotate(title, xy=(0, 1), xycoords="axes fraction", xytext=(12, 25), textcoords="offset points",
                fontsize=7, fontweight="bold", ha="left", va="baseline", color=INK)
    ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction", xytext=(0, 10), textcoords="offset points",
                fontsize=6.5, ha="left", va="baseline", color=INK)


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    for spine in ax.spines.values():
        spine.set_linewidth(.5)
        spine.set_color("#82909B")
    ax.tick_params(length=2.5, width=.5, colors=INK, pad=3)
    ax.set_axisbelow(True)


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    ART.mkdir(exist_ok=True, parents=True)
    scores, histogram, edges, overall, claims, tasks = data()
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
                         "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
                         "axes.labelcolor": INK, "text.color": INK, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "svg.fonttype": "none", "svg.hashsalt": "bace-figure-2", "figure.facecolor": "white"})
    width_in, height_in = 180/25.4, 154/25.4
    fig = plt.figure(figsize=(width_in, height_in))
    grid = fig.add_gridspec(2, 2, left=.09, right=.98, bottom=.075, top=.885,
                           wspace=.27, hspace=.66, height_ratios=[1, 1.48])
    a, b, c = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, :])
    for ax in [a, b, c]:
        style(ax)
    heading(a, "a", "Disclosure-level support",
            f"Mean {overall['mean_percent']:.1f}% (95% CI, {overall['low_percent']:.1f}–{overall['high_percent']:.1f}%)")
    a.bar(100*edges[:-1], histogram, width=5, align="edge", color=BLUE, edgecolor="white", linewidth=.45)
    a.axvline(overall["mean_percent"], color=INK, linewidth=1, linestyle=(0, (3, 2)))
    a.set(xlim=(0, 100), ylim=(0, max(histogram)*1.25), xlabel="BACE-assessed support (%)", ylabel="Disclosures")
    a.set_xticks([0, 20, 40, 60, 80, 100])
    a.text(.025, .95, f"{overall['disclosures']:,} disclosures", transform=a.transAxes, ha="left", va="top", fontsize=6.5)

    heading(b, "b", "Claim-level composition", f"{overall['pooled_denominator']:,} claims across {overall['disclosures']:,} disclosures")
    b.bar(range(3), [r["percent"] for r in claims], color=[BLUE, PALE_BLUE, AMBER], width=.6)
    b.set(ylim=(0, 62), ylabel="Share of all claims (%)", xlim=(-.55, 2.55))
    b.set_yticks([0, 20, 40, 60])
    b.set_xticks(range(3), [r["category"] for r in claims])
    b.tick_params(axis="x", length=0, pad=5)
    for i, row in enumerate(claims):
        b.text(i, row["percent"]+2, f"{row['percent']:.1f}%\n{row['count']:,}", fontsize=7,
               ha="center", va="bottom", linespacing=1.25)

    heading(c, "c", "Support across all disclosure tasks", "Means and 95% company-cluster intervals")
    # A full-width forest table: negative coordinates are reserved for task text;
    # the plotted quantitative scale is explicitly 0–100%, with no negative ticks.
    c.set(xlim=(-90, 140), ylim=(11.75, -1.7))
    c.spines[["left", "right", "top"]].set_visible(False)
    c.spines["bottom"].set_bounds(0, 100)
    c.set_yticks([])
    c.set_xticks([0, 20, 40, 60, 80, 100])
    c.set_xlabel("BACE-assessed support (%)")
    c.xaxis.set_label_coords((50+90)/230, -.15)
    for x in [0, 20, 40, 60, 80, 100]:
        c.plot([x, x], [-.55, 11.6], color="#E5E9EC", linewidth=.45, zorder=0)
    for y in [3.5, 7.5]:
        c.axhline(y, color="#D1D8DE", linewidth=.5, zorder=0)
    for x, label, align in [(-89, "Task", "left"), (116, "Mean (%)", "center"), (139, "n", "right")]:
        c.text(x, -1.13, label, fontsize=6.5, fontweight="bold", ha=align, va="center")
    for i, row in enumerate(tasks):
        c.text(-89, i, row["task"], ha="left", va="center", fontsize=6.5, fontweight="bold")
        c.text(-65, i, row["topic"], ha="left", va="center", fontsize=6.5)
        c.errorbar(row["mean_percent"], i,
                   xerr=[[row["mean_percent"]-row["low_percent"]], [row["high_percent"]-row["mean_percent"]]],
                   fmt="o", markersize=3, color=BLUE, ecolor=BLUE, elinewidth=.9, capsize=2, capthick=.7, zorder=3)
        c.text(116, i, f"{row['mean_percent']:.1f}", ha="center", va="center", fontsize=6.5)
        c.text(139, i, str(row["disclosures"]), ha="right", va="center", fontsize=6.5)
    fig.canvas.draw()
    alignment = require_matplotlib_panel_alignment(fig, panel_ids=["a", "b", "c"],
                    json_out=OUT/"fig2.alignment.json", overlay_svg=OUT/"fig2.alignment.svg",
                    tolerance_pt=1.5, gutter_tolerance_pt=1.5, require_panel_labels=True, strict=True)
    base = ART/"fig2_support"
    fig.savefig(base.with_suffix(".pdf"), dpi=600)
    fig.savefig(base.with_suffix(".svg"), dpi=600)
    fig.savefig(base.with_suffix(".png"), dpi=600)
    for ax, name in [(a, "a"), (b, "b"), (c, "c")]:
        extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(OUT/f"panel_{name}.png", dpi=300, bbox_inches=extent.expanded(1.015, 1.025))
    plt.close(fig)
    outputs = [base.with_suffix("."+ext) for ext in ["pdf", "svg", "png"]]
    outputs += [OUT/name for name in ["disclosures.csv", "excluded_cases.csv", "histogram.csv", "claim_composition.csv", "task_estimates.csv", "verified_facts.json"]]
    record = dict(status="RENDERED_PENDING_PDF_QA", prepared_date="2026-10-02",
                  checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  command="/usr/bin/python3 paper/analysis/fig2/render_fig2.py", script_sha256=sha(Path(__file__)),
                  python=sys.version, matplotlib=matplotlib.__version__, numpy=np.__version__, input_files=INPUTS,
                  geometry_mm=dict(width=180, height=154), minimum_source_font_pt=6.5,
                  alignment_verdict=alignment["verdict"], outputs={str(p.relative_to(ROOT)): sha(p) for p in outputs},
                  aggregation="Panels a/c: equal disclosure weights; panel b: pooled counts, equal DC weights. All-DC denominators throughout.",
                  uncertainty="Saved 95% percentile intervals, resampling 30 companies, 2000 draws, seed 20260921. Endpoints SOURCE_REPORTED; point estimates COMPUTED_VERIFIED.",
                  limits="No new bootstrap run, hypothesis test, model call or completed human validation. Descriptive task variation; no causal or population-representative inference.")
    (OUT/"provenance.json").write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(dict(status=record["status"], alignment=alignment["verdict"], disclosures=len(scores), claims=overall["pooled_denominator"])))


if __name__ == "__main__":
    main()
