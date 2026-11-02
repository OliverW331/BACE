"""Verify saved common-cohort results and render BACE manuscript Figure 4.

No model calls, bootstrap reruns or experiment mutations. Exact ECDFs represent
all observations, and saved paired uncertainty is kept distinct from accuracy.
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
ART = ROOT/"paper/manuscript/figures"
SCRIPTS = Path("/home/muwang/.codex/skills/nature-figure/scripts")
sys.path.insert(0,str(SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment

METHODS = {
    "BACE": ("bace_support_rate_all_dc", "bace_dc_count"),
    "RAGChecker": ("ragchecker_faithfulness", "ragchecker_claim_count"),
    "RAGAS": ("ragas_faithfulness", "ragas_claim_count")
}
COLORS = {"BACE":"#38657D", "RAGChecker":"#B0772F", "RAGAS":"#826699"}
STYLES = {"BACE":"-", "RAGChecker":"--", "RAGAS":":"}
INK = "#263746"
INPUTS = {}
PREFIX = "BACE/analysis/outputs/figures/03/"


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        while block:=stream.read(2**20): h.update(block)
    return h.hexdigest()


def register(relative):
    path=ROOT/relative
    INPUTS[relative]=dict(sha256=sha(path),bytes=path.stat().st_size)
    return path


def read_csv(relative):
    with register(relative).open(newline="") as stream: return list(csv.DictReader(stream))


def read_json(relative):
    return json.loads(register(relative).read_text())


def save_csv(name,rows):
    with (OUT/name).open("w",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def data():
    snapshot=read_csv("BACE/analysis/outputs/snapshot/metrics.csv")
    complete=[r for r in snapshot if r["bace_complete"].lower()=="true"]
    excluded=[r for r in snapshot if r["bace_complete"].lower()!="true"]
    assert len(snapshot)==1800 and len(complete)==1798 and len(excluded)==2
    ids=[r["generation_case_id"] for r in complete]
    assert len(set(ids))==len(ids)
    assert len({r["company_id"] for r in complete})==30
    execution=read_json("BACE/results/main_v1/execution_status.json")
    assert set(ids)==set(execution["completed_case_ids"])
    assert all(r["bace_support_rate_all_dc"]=="" for r in excluded)
    columns=[column for pair in METHODS.values() for column in pair]
    for r in complete:
        assert all(r[column]!="" for column in columns)
    for filename in ["03_native_comparison__scores.csv","03_claim_inventories__data.csv"]:
        exported=read_csv(PREFIX+filename)
        mapped={r["generation_case_id"]:r for r in exported}
        assert len(mapped)==len(exported)==len(complete) and set(mapped)==set(ids)
        for r in complete:
            saved=mapped[r["generation_case_id"]]
            assert saved["company_id"]==r["company_id"]
            for col in columns:
                if col in saved: assert abs(float(saved[col])-float(r[col]))<1e-12,(filename,col)
    summaries=read_csv(PREFIX+"03_native_comparison__cohort_summary.csv")
    contrasts=read_csv(PREFIX+"03_native_comparison__paired_differences.csv")
    verified=read_json("paper/analysis/results_draft/verified_numbers.json")
    scores,counts,method_rows,ecdfs={},{},[],[]
    for method,(score_col,count_col) in METHODS.items():
        scores[method]=np.array([float(r[score_col]) for r in complete])
        counts[method]=np.array([float(r[count_col]) for r in complete])
        assert np.isfinite(scores[method]).all() and ((scores[method]>=0)&(scores[method]<=1)).all()
        assert np.isfinite(counts[method]).all() and (counts[method]>0).all()
        assert np.array_equal(counts[method],counts[method].astype(int))
        saved=next(r for r in summaries if r["method"]==method and r["cohort"]=="Common")
        mean=100*float(np.mean(scores[method]));median=float(np.median(counts[method]))
        assert abs(mean-100*float(saved["mean"]))<1e-10
        assert [int(saved[k]) for k in ["companies","disclosures","draws"]]==[30,1798,2000]
        assert abs(mean-verified["comparators"]["means_pct"][method])<1e-10
        assert median==verified["inventory_medians"][count_col]
        method_rows.append(dict(method=method,disclosures=1798,companies=30,mean_score_percent=mean,
                                median_claim_count=median,minimum_claim_count=int(counts[method].min()),
                                maximum_claim_count=int(counts[method].max()),status="COMPUTED_VERIFIED",
                                source="BACE/analysis/outputs/snapshot/metrics.csv",score_column=score_col,count_column=count_col,
                                aggregation="Arithmetic mean of native disclosure scores; median native claim count on the identical completed cohort"))
        for kind,values,multiplier in [("score",scores[method],100),("claim_count",counts[method],1)]:
            unique,frequencies=np.unique(values,return_counts=True)
            cumulative=np.cumsum(frequencies)
            assert frequencies.sum()==1798 and cumulative[-1]==1798
            assert (np.diff(unique)>0).all() and (np.diff(cumulative)>0).all()
            for value,frequency,total in zip(unique,frequencies,cumulative):
                assert int(total)==int(np.count_nonzero(values<=value))
                ecdfs.append(dict(measure=kind,method=method,native_value=float(value),plot_x=float(multiplier*value),
                                   frequency=int(frequency),cumulative_disclosures=int(total),denominator=1798,
                                   cumulative_percent=100*int(total)/1798,status="COMPUTED_VERIFIED"))
    contrast_rows=[]
    for method in ["RAGChecker","RAGAS"]:
        values=100*(scores["BACE"]-scores[method])
        mean=float(np.mean(values))
        saved=next(r for r in contrasts if r["contrast"]=="BACE − "+method)
        assert abs(mean-100*float(saved["mean"]))<1e-10
        assert [int(saved[k]) for k in ["companies","disclosures","draws"]]==[30,1798,2000]
        low,high=100*float(saved["low"]),100*float(saved["high"])
        prior=next(r for r in verified["comparators"]["paired_differences"] if r["comparator"]==method)
        assert abs(mean-prior["mean_pp"])<1e-10
        assert np.allclose([low,high],prior["saved_95_interval_pp"],atol=1e-10,rtol=0)
        assert low<=mean<=high
        contrast_rows.append(dict(comparator=method,contrast="BACE − "+method,mean_pp=mean,low_pp=low,high_pp=high,
                                  disclosures=1798,companies=30,bootstrap_draws=2000,seed=20260921,
                                  mean_status="COMPUTED_VERIFIED",interval_status="SOURCE_REPORTED",
                                  interval_source=PREFIX+"03_native_comparison__paired_differences.csv",
                                  aggregation="Within-disclosure native score subtraction followed by equal-weight disclosure mean",
                                  uncertainty="Saved 95% percentile company-cluster bootstrap; all disclosures retained within each sampled company"))
    code=register("BACE/analysis/analysis_data.py").read_text()
    assert "SEED = 20260921" in code and "np.quantile(replicates,[.025,.975])" in code
    original=register("BACE/analysis/scripts/build_notebooks.py").read_text()
    assert "common[column]=common[METHODS['BACE']]-common[METHODS[other]]" in original
    register("BACE/analysis/ANALYSIS_SPEC.md")
    register("paper/analysis/fig4/FIGURE_CONTRACT.md")
    paired=[]
    for r in complete:
        row={k:r[k] for k in ["generation_case_id","company_id","company_name","year","task",*columns]}
        for method in ["RAGChecker","RAGAS"]:
            row["bace_minus_"+method.lower()+"_pp"]=100*(float(r[METHODS["BACE"][0]])-float(r[METHODS[method][0]]))
        paired.append(row)
    save_csv("paired_disclosures.csv",paired)
    save_csv("excluded_cases.csv",[dict(generation_case_id=r["generation_case_id"],company=r["company_name"],year=r["year"],task=r["task"],
                                        reason="Incomplete BACE assessment; excluded from all panels without zero imputation") for r in excluded])
    save_csv("method_summaries.csv",method_rows)
    save_csv("paired_differences.csv",contrast_rows)
    save_csv("ecdf_coordinates.csv",ecdfs)
    facts=dict(planned=1800,completed=1798,companies=30,incomplete=2,method_summaries=method_rows,paired_differences=contrast_rows,
               cohort="Identical completed disclosures across all three panels; no comparator-only additions",
               ecdf="Exact right-continuous empirical cumulative distributions with tied values counted together; all observations represented",
               uncertainty="Saved paired 95% company-cluster percentile intervals; 2000 draws; seed 20260921; no bootstrap rerun or hypothesis test")
    (OUT/"verified_facts.json").write_text(json.dumps(facts,indent=2)+'\n')
    return scores,counts,method_rows,contrast_rows,ecdfs


def heading(ax,letter,title,subtitle):
    transform=ax.transAxes+ScaledTranslation(0,25/72,ax.figure.dpi_scale_trans)
    ax.text(0,1,letter,transform=transform,fontsize=8,fontweight="bold",va="baseline",ha="left",color=INK)
    ax.annotate(title,xy=(0,1),xycoords="axes fraction",xytext=(12,25),textcoords="offset points",
                fontsize=7,fontweight="bold",va="baseline",ha="left",color=INK)
    ax.annotate(subtitle,xy=(0,1),xycoords="axes fraction",xytext=(0,10),textcoords="offset points",
                fontsize=6.5,va="baseline",ha="left",color=INK)


def style(ax):
    ax.spines[["top","right"]].set_visible(False)
    for spine in ax.spines.values():spine.set_color("#82909B");spine.set_linewidth(.5)
    ax.tick_params(colors=INK,length=2.5,width=.5,pad=3)


def ecdf_plot(ax,rows,kind,method,label):
    selected=[r for r in rows if r["measure"]==kind and r["method"]==method]
    x=[0]+[r["plot_x"] for r in selected]
    y=[0]+[r["cumulative_percent"] for r in selected]
    assert x[-1]<=100 and y[-1]==100
    if x[-1]<100:x.append(100);y.append(100)
    ax.step(x,y,where="post",color=COLORS[method],linestyle=STYLES[method],linewidth=1.15,label=label)


def signed(value):
    return f"{value:.1f}".replace("-","−")


def main():
    OUT.mkdir(exist_ok=True,parents=True);ART.mkdir(exist_ok=True,parents=True)
    scores,counts,summary,contrasts,ecdfs=data()
    plt.rcParams.update({"font.family":"sans-serif","font.sans-serif":["DejaVu Sans"],"font.size":7,
                         "axes.labelsize":7,"xtick.labelsize":6.5,"ytick.labelsize":6.5,"axes.labelcolor":INK,"text.color":INK,
                         "legend.fontsize":6.5,"legend.title_fontsize":6.5,"legend.frameon":False,
                         "pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none","svg.hashsalt":"bace-figure-4",
                         "figure.facecolor":"white"})
    width_in,height_in=180/25.4,138/25.4
    fig=plt.figure(figsize=(width_in,height_in))
    grid=fig.add_gridspec(2,2,left=.10,right=.985,bottom=.10,top=.875,wspace=.30,hspace=.60)
    a=fig.add_subplot(grid[:,0]);b=fig.add_subplot(grid[0,1]);c=fig.add_subplot(grid[1,1])
    for ax in [a,b,c]:style(ax)
    heading(a,"a","Native score distributions","1,798 matched disclosures · 30 companies")
    for row in summary:
        ecdf_plot(a,ecdfs,"score",row["method"],f"{row['method']}  {row['mean_score_percent']:.1f}%")
    a.set(xlim=(0,100),ylim=(0,102),xlabel="Native score (%)",ylabel="Cumulative disclosures (%)")
    a.set_xticks([0,20,40,60,80,100]);a.set_yticks([0,20,40,60,80,100])
    a.legend(title="Mean score",loc="upper left",borderaxespad=.7,handlelength=2.1,labelspacing=.55)

    heading(b,"b","Paired score differences","BACE minus comparator; mean [95% CI]")
    b.set(xlim=(-45,5),ylim=(-.2,2.65))
    b.set_yticks([]);b.spines["left"].set_visible(False)
    b.set_xticks([-40,-20,0]);b.axvline(0,color="#8E979E",linestyle=(0,(3,3)),linewidth=.6,zorder=0)
    b.set_xlabel("Difference (percentage points)")
    for row,y,marker in zip(contrasts,[1.65,.30],["s","^"]):
        method=row["comparator"];mean=row["mean_pp"]
        b.errorbar(mean,y,xerr=[[mean-row["low_pp"]],[row["high_pp"]-mean]],fmt=marker,
                   markersize=4,color=COLORS[method],ecolor=COLORS[method],elinewidth=1,capsize=2.5,capthick=.8)
        b.text(-44, y+.55, f"{method}: {signed(mean)} [{signed(row['low_pp'])}, {signed(row['high_pp'])}]",
               fontsize=6.5,ha="left",va="center",color=INK)

    heading(c,"c","Native claim inventories","Same 1,798 disclosures; distinct claim sets")
    for row in summary:
        ecdf_plot(c,ecdfs,"claim_count",row["method"],f"{row['method']}  {row['median_claim_count']:.0f}")
    c.set(xlim=(0,100),ylim=(0,102),xlabel="Native claims per disclosure",ylabel="Cumulative disclosures (%)")
    c.set_xticks([0,25,50,75,100]);c.set_yticks([0,50,100])
    c.legend(title="Median claims",loc="lower right",borderaxespad=.6,handlelength=2.1,labelspacing=.4)

    fig.canvas.draw()
    alignment=require_matplotlib_panel_alignment(fig,panel_ids=["a","b","c"],json_out=OUT/"fig4.alignment.json",
                    overlay_svg=OUT/"fig4.alignment.svg",tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True)
    base=ART/"fig4_native_comparison"
    fig.savefig(base.with_suffix(".pdf"),dpi=600)
    fig.savefig(base.with_suffix(".svg"),dpi=600)
    fig.savefig(base.with_suffix(".png"),dpi=600)
    for ax,name in [(a,"a"),(b,"b"),(c,"c")]:
        extent=ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(OUT/f"panel_{name}.png",dpi=300,bbox_inches=extent.expanded(1.015,1.025))
    plt.close(fig)
    outputs=[base.with_suffix('.'+ext) for ext in ['pdf','svg','png']]
    outputs += [OUT/name for name in ['paired_disclosures.csv','excluded_cases.csv','method_summaries.csv','paired_differences.csv','ecdf_coordinates.csv','verified_facts.json']]
    record=dict(status="RENDERED_PENDING_QA",prepared_date="2026-10-02",checked_at_utc=datetime.now(timezone.utc).isoformat(),
                command="/usr/bin/python3 paper/analysis/fig4/render_fig4.py",script_sha256=sha(Path(__file__)),
                python=sys.version,matplotlib=matplotlib.__version__,numpy=np.__version__,input_files=INPUTS,
                outputs={str(p.relative_to(ROOT)):sha(p) for p in outputs},geometry_mm=dict(width=180,height=138),minimum_source_font_pt=6.5,
                alignment_verdict=alignment['verdict'],
                numerical_status="All descriptive quantities recomputed and checked; paired interval endpoints SOURCE_REPORTED",
                limits="Exact common-cohort native comparisons; no new bootstrap run, hypothesis test, accuracy ranking or human validation")
    (OUT/"provenance.json").write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(status=record['status'],alignment=alignment['verdict'],cohort=1798,figure=str(base.with_suffix('.pdf')))))


if __name__=="__main__":main()
