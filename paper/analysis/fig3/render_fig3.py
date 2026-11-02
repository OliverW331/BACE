"""Render the verified Figure 3 aggregate and source-linked illustrations.

Python/Matplotlib only. prepare_data.py owns numerical and original-source
verification. This figure does not infer validated error rates from model labels.
"""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.transforms import ScaledTranslation

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
ART = ROOT/"paper/manuscript/figures"
SCRIPTS = Path("/home/muwang/.codex/skills/nature-figure/scripts")
sys.path.insert(0,str(SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment

INK, BLUE, PALE, GREY, AMBER = "#263746", "#38657D", "#8DB6C9", "#B7C2CA", "#996B2E"
DISPLAYED = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap(text, width):
    return "\n".join(textwrap.wrap(text,width=width,break_long_words=False,break_on_hyphens=False))


def text(ax,x,y,value,*,role,source=None,**kwargs):
    opts=dict(fontsize=6.5,color=INK,ha="left",va="top",linespacing=1.25)
    opts.update(kwargs)
    ax.text(x,y,value,**opts)
    DISPLAYED.append(dict(panel=ax.get_label(),role=role,text=value,source=source or "Editorial label or bounded interpretation; see FIGURE_CONTRACT.md"))


def heading(ax,letter,title):
    transform=ax.transAxes+ScaledTranslation(0,7/72,ax.figure.dpi_scale_trans)
    ax.text(0,1,letter,transform=transform,fontsize=8,fontweight="bold",va="baseline",ha="left",color=INK)
    return ax.annotate(title,xy=(0,1),xycoords="axes fraction",xytext=(12,7),textcoords="offset points",
                fontsize=7,fontweight="bold",va="baseline",ha="left",color=INK)


def box(ax,x,y,w,h,fill="#F3F6F8",edge="#BECBD3"):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fill,edgecolor=edge,linewidth=.6,zorder=0))


def main():
    data_prov=json.loads((OUT/"data_provenance.json").read_text())
    assert data_prov["status"]=="PASS" and data_prov["script_sha256"]==sha(OUT/"prepare_data.py")
    for path,expected in data_prov["outputs"].items():
        assert sha(ROOT/path)==expected,path
    facts=json.loads((OUT/"verified_facts.json").read_text())
    cases=json.loads((OUT/"case_evidence.json").read_text())
    with (OUT/"diagnosis_composition.csv").open() as stream:
        composition=list(csv.DictReader(stream))
    plt.rcParams.update({"font.family":"sans-serif","font.sans-serif":["DejaVu Sans"],"font.size":7,
                         "xtick.labelsize":6.5,"ytick.labelsize":6.5,"axes.labelsize":6.5,
                         "text.color":INK,"axes.labelcolor":INK,"pdf.fonttype":42,"ps.fonttype":42,
                         "svg.fonttype":"none","svg.hashsalt":"bace-figure-3","figure.facecolor":"white"})
    width_in,height_in=180/25.4,170/25.4
    fig=plt.figure(figsize=(width_in,height_in))
    grid=fig.add_gridspec(3,1,left=.045,right=.98,bottom=.027,top=.963,hspace=.34,height_ratios=[.86,1,1.37])
    a,b,c=[fig.add_subplot(grid[i,0],label=letter) for i,letter in enumerate(["a","b","c"])]

    heading(a,"a","Automated diagnosis composition")
    text(a,72,-1.60,f"{facts['combined_percent']:.1f}% boundary distortion + conflation",role="Combined share",
         source="verified_facts.json: combined_percent",ha="right",fontsize=7,fontweight="bold",color=BLUE)
    text(a,-51,-1.60,f"{facts['unsupported_dc']:,} unsupported claims",role="Denominator",source="verified_facts.json: unsupported_dc")
    a.set(xlim=(-52,72),ylim=(5.65,-1.65))
    a.spines[["top","left","right"]].set_visible(False)
    a.spines["bottom"].set_bounds(0,50)
    a.spines["bottom"].set_color("#82909B")
    a.spines["bottom"].set_linewidth(.5)
    a.set_yticks([])
    a.set_xticks([0,10,20,30,40,50])
    a.tick_params(axis="x",length=2.5,width=.5,pad=2,colors=INK)
    a.set_xlabel("Share of unsupported claims (%)",labelpad=4)
    a.xaxis.set_label_coords((25+52)/124,-.12)
    for x,label in [(57,"Share"),(72,"Count")]:
        text(a,x,-.94,label,role="Column heading",fontsize=6.5,ha="right",fontweight="bold")
    for i,row in enumerate(composition):
        percent=float(row["percent"])
        color=BLUE if row["label"]=="factual_boundary_distortion" else PALE if row["label"]=="evidence_conflation" else GREY
        a.barh(i,percent,height=.54,color=color)
        text(a,-51,i,row["display_label"],role="Diagnosis label",source="diagnosis_composition.csv: "+row["label"],va="center")
        text(a,57,i,f"{percent:.1f}%",role="Diagnosis share",source="diagnosis_composition.csv: "+row["label"],ha="right",va="center")
        text(a,72,i,f"{int(row['count']):,}",role="Diagnosis count",source="diagnosis_composition.csv: "+row["label"],ha="right",va="center")

    w=cases["wartsila"]
    b_heading=heading(b,"b","Wärtsilä: historical evidence and the target reporting year")
    b.set(xlim=(0,174),ylim=(0,48));b.axis("off")
    box(b,0,13,77,31)
    box(b,98,13,76,31,fill="#F7F8F9")
    text(b,3,41,"Supplied evidence · source year 2019",role="Evidence stage",source="case_evidence.json: wartsila.supplied_card",fontweight="bold",fontsize=7)
    text(b,3,33,wrap('“'+w["display_card_excerpt"]+'”',49),role="Supplied evidence quotation",source="case_evidence.json: wartsila.display_card_excerpt",fontsize=7)
    text(b,3,17,"Annual Report 2019, p. 132 · Evidence 7",role="Source locator",source="original_source_checks.json: wartsila",fontsize=6.5)
    text(b,101,41,"Extracted disclosure claim · target 2022",role="Disclosure stage",source="case_evidence.json: wartsila.target_year",fontweight="bold",fontsize=7)
    text(b,101,33,wrap('“'+w["dc_text"]+'”',48),role="DC quotation",source="case_evidence.json: wartsila.dc_text",fontsize=7)
    text(b,101,17,"G1-2 · Supplier relationships",role="Task",source="case_evidence.json: wartsila.task")
    b.add_patch(FancyArrowPatch((79,27),(96,27),arrowstyle="-|>",mutation_scale=8,linewidth=.9,color=BLUE))
    text(b,87.5,36,"Temporal\ncarry-forward",role="Disputed boundary",ha="center",fontsize=6.5)
    text(b,0,9,"BACE diagnosis: Factual boundary distortion",role="Recorded automatic diagnosis",source="case_evidence.json: wartsila.diagnosis",fontweight="bold",color=BLUE,fontsize=7)
    text(b,0,3,"Historical evidence does not establish discontinuation of the practice.",role="Interpretation limit",source="case_evidence.json: wartsila.interpretation_limit")

    s=cases["asml"]
    heading(c,"c","ASML: source-row association challenges an automated contradiction")
    c.set(xlim=(0,174),ylim=(0,66));c.axis("off")
    text(c,0,64,"Extracted DC (target 2019):",role="Disclosure stage",fontweight="bold",source="case_evidence.json: asml.target_year")
    text(c,44,64,'“'+s["dc_text"]+'”',role="DC quotation",source="case_evidence.json: asml.dc_text",fontsize=6.5)
    text(c,0,54,"Original glossary rows · typeset transcription",role="Original-source stage",fontweight="bold",fontsize=7)
    text(c,0,49,"ASML Integrated Report 2018, p. 209 (PDF p. 216)",role="Source locator",source="original_source_checks.json: asml")
    text(c,108,54,"Selected candidate evidence claim",role="EC stage",fontweight="bold",fontsize=7)
    text(c,108,49,"Extracted from the flattened supplied card",role="EC provenance",source="case_evidence.json: asml.selected_ec_id")
    box(c,0,13,92,30,fill="#F3F6F8")
    c.plot([0,92],[28,28],color="#BECBD3",linewidth=.6)
    c.plot([28,28],[13,43],color="#BECBD3",linewidth=.6)
    for row,y in zip(s["glossary_rows"],[40,25]):
        label=row["label"].replace("CO2","CO₂").replace(" - "," –\n")
        description=row["description"].replace("CO2","CO₂")
        text(c,2,y,label,role="Original glossary term",source="original_source_checks.json: asml.glossary_rows",fontsize=6.5)
        text(c,30,y,wrap(description,48),role="Original glossary description",source="original_source_checks.json: asml.glossary_rows",fontsize=6.5)
    box(c,108,13,66,30,fill="#FCF5E8",edge=AMBER)
    text(c,111,40,wrap('“'+s["selected_ec_text"].replace("CO2","CO₂")+'”',45),role="Selected EC quotation",
         source="case_evidence.json: asml.selected_ec_text",fontsize=6.5)
    c.add_patch(FancyArrowPatch((94,27),(106,27),arrowstyle="-|>",mutation_scale=8,linewidth=.9,color=AMBER))
    text(c,100,38,"Text\nextraction",role="Source transformation",ha="center",fontsize=6.5,color=AMBER)
    text(c,0,9,"BACE: Contradiction. Source check: electricity belongs to Scope 2.",role="Recorded diagnosis and source check",
         source="case_evidence.json: asml.diagnosis; original_source_checks.json: asml.glossary_rows",fontweight="bold",fontsize=7,color=AMBER)
    text(c,0,3,s["interpretation_limit"],role="Interpretation limit",source="case_evidence.json: asml.interpretation_limit")

    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    interpanel_text_gap=(a.xaxis.label.get_window_extent(renderer).y0-b_heading.get_window_extent(renderer).y1)*72/fig.dpi
    assert interpanel_text_gap >= 3, "Keep panel a's axis label clear of panel b's heading"
    alignment=require_matplotlib_panel_alignment(fig,panel_ids=["a","b","c"],json_out=OUT/"fig3.alignment.json",
                     overlay_svg=OUT/"fig3.alignment.svg",tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True)
    ART.mkdir(exist_ok=True,parents=True)
    base=ART/"fig3_diagnoses_cases"
    fig.savefig(base.with_suffix(".pdf"),dpi=600)
    fig.savefig(base.with_suffix(".svg"),dpi=600)
    fig.savefig(base.with_suffix(".png"),dpi=600)
    for ax,name in [(a,"a"),(b,"b"),(c,"c")]:
        extent=ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(OUT/f"panel_{name}.png",dpi=300,bbox_inches=extent.expanded(1.015,1.025))
    plt.close(fig)
    with (OUT/"displayed_text.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(DISPLAYED[0]));writer.writeheader();writer.writerows(DISPLAYED)
    inputs=[OUT/f for f in ["prepare_data.py","data_provenance.json","diagnosis_composition.csv","verified_facts.json","case_evidence.json","original_source_checks.json","FIGURE_CONTRACT.md"]]
    outputs=[base.with_suffix('.'+ext) for ext in ['pdf','svg','png']]+[OUT/"displayed_text.csv"]
    record=dict(status="RENDERED_PENDING_QA",prepared_date="2026-10-02",checked_at_utc=datetime.now(timezone.utc).isoformat(),
                command="/usr/bin/python3 paper/analysis/fig3/render_fig3.py",script_sha256=sha(Path(__file__)),
                python=sys.version,matplotlib=matplotlib.__version__,geometry_mm=dict(width=180,height=170),minimum_source_font_pt=6.5,
                input_files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in inputs},
                outputs={str(p.relative_to(ROOT)):sha(p) for p in outputs},alignment_verdict=alignment['verdict'],
                panel_a_axis_label_to_b_heading_gap_pt=interpanel_text_gap,
                scope="Pooled diagnostic counts plus two fixed source-linked illustrations; no validated error prevalence or human assessment result")
    (OUT/"provenance.json").write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(status=record['status'],alignment=alignment['verdict'],figure=str(base.with_suffix('.pdf')))))


if __name__ == "__main__":
    main()
