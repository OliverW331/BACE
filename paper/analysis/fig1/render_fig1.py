"""Render BACE Figure 1 from saved cohort/configuration records.

All original experiment and annotation files are read-only. This is a workflow
schematic, not an evaluator-accuracy plot or a new experiment.
"""
from datetime import datetime, timezone
import ast
import csv
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.transforms import ScaledTranslation

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
ART = ROOT / "paper/manuscript/figures"
QA_SCRIPTS = Path("/home/muwang/.codex/skills/nature-figure/scripts")
sys.path.insert(0, str(QA_SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment

INPUTS = {}
FACTS = []
INK, BLUE, AMBER = "#263746", "#38657D", "#996B2E"
BLUE_FILL, NEUTRAL_FILL, AMBER_FILL = "#EEF4F7", "#F5F6F7", "#FCF5E8"


def register(relative):
    path = ROOT / relative
    key = str(path.relative_to(ROOT))
    if key not in INPUTS:
        h = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(2**20):
                h.update(block)
        INPUTS[key] = {"sha256": h.hexdigest(), "bytes": path.stat().st_size}
    return path


def read_json(relative):
    return json.loads(register(relative).read_text())


def fact(name, value, units, source, locator, aggregation, status="COMPUTED_VERIFIED"):
    FACTS.append(dict(name=name, value=value, units=units, source=source, locator=locator,
                      aggregation=aggregation, status=status))
    return value


def reviewer_rows(path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as workbook:
        shared = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            shared = ["".join(node.itertext()) for node in ET.fromstring(workbook.read("xl/sharedStrings.xml"))]
        root = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in root.findall("m:sheetData/m:row", ns)[1:]:
            cells = {}
            for cell in row.findall("m:c", ns):
                column = "".join(c for c in cell.attrib["r"] if c.isalpha())
                value = cell.find("m:v", ns)
                if cell.attrib.get("t") == "s":
                    text = shared[int(value.text)] if value is not None else ""
                elif cell.attrib.get("t") == "inlineStr":
                    text = "".join(n.text or "" for n in cell.findall(".//m:t", ns))
                else:
                    text = value.text if value is not None and value.text else ""
                cells[column] = text
            rows.append(cells)
    return rows


def data():
    source = "BACE/analysis/outputs/snapshot/metrics.csv"
    with register(source).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    complete = [r for r in rows if r["bace_complete"].lower() == "true"]
    columns = ["bace_support_rate_all_dc", "ragchecker_faithfulness", "ragas_faithfulness"]
    paired = [r for r in rows if all(r[c] != "" for c in columns)]
    execution = read_json("BACE/results/main_v1/execution_status.json")
    assert {r["generation_case_id"] for r in complete} == {r["generation_case_id"] for r in paired} == set(execution["completed_case_ids"])
    values = {}
    for name, value, units, locator, rule in [
        ("companies", len({r["company_id"] for r in rows}), "companies", "company_id", "Distinct company IDs in the planned matrix"),
        ("years", len({r["year"] for r in rows}), "years", "year", "Distinct target reporting years"),
        ("tasks", len({r["task"] for r in rows}), "tasks", "task", "Distinct task identifiers"),
        ("planned", len(rows), "cases", "generation_case_id", "All planned company-year-task rows"),
        ("analysed", len(paired), "disclosures", ", ".join(columns), "Intersection of available scores; matches all completed BACE cases"),
        ("excluded", len(rows)-len(complete), "cases", "bace_complete", "Planned minus completed BACE cases; no zero imputation"),
    ]:
        values[name] = fact(name, value, units, source, locator, rule)
    assert [values[k] for k in ["companies", "years", "tasks", "planned", "analysed", "excluded"]] == [30, 5, 12, 1800, 1798, 2]
    assert values["companies"] * values["years"] * values["tasks"] == values["planned"]
    values["year_values"] = sorted({int(r["year"]) for r in rows})
    assert values["year_values"] == list(range(2019, 2024))
    fact("target_years", "2019–2023", "reporting years", source, "year", "Minimum and maximum of observed planned years")

    config_source = "BACE/config/experiment.json"
    config = read_json(config_source)
    windows = config["windows"]
    for kind in ["pdf", "csv"]:
        newest = -windows[kind + "_lag_years"]
        oldest = newest - windows[kind + "_window_years"] + 1
        assert (oldest, newest) == ((-4, -1) if kind == "pdf" else (-4, 0))
        values[kind + "_window"] = (oldest, newest)
        fact(kind + "_source_year_offsets", f"{oldest} through {newest}", "years relative to target t", config_source,
             "windows", "Newest = -lag; oldest = newest - window length + 1")
    retrieval_source = "BACE/config/retrieval/retrieval_algorithm_config_text_embedding_3_large_top200_v1.json"
    retrieval = read_json(retrieval_source)["final_selection"]["stratified_by_evidence_type"]
    for name, key in [("per_type", "main_generation_per_evidence_type_top_n"), ("maximum_cards", "max_main_generation_cards")]:
        values[name] = fact(name, retrieval[key], "cards", retrieval_source, "final_selection.stratified_by_evidence_type." + key,
                            "Configured maximum, not observed count per case", "SOURCE_REPORTED")
    assert values["per_type"] == 10 and values["maximum_cards"] == 30

    human_source = "BACE/analysis/validation/_private/sample_manifest.json"
    human = read_json(human_source)
    assert human["status"] == "prepared_not_annotated"
    ids = {r["sample_id"] for r in human["records"]}
    values["human_n"] = fact("prepared_human_sample", len(ids), "unique DCs", human_source, "records.sample_id", "Distinct formal sample IDs shared by both workbooks")
    assert len(ids) == len(human["records"]) == 600
    materials, workbook_status = [], {}
    for reviewer in ["A", "B"]:
        relative = f"BACE/analysis/validation/human_validation_600_reviewer_{reviewer}.xlsx"
        sample = reviewer_rows(register(relative))
        assert len(sample) == 600 and {r["A"] for r in sample} == ids
        count = sum(bool(r.get(c, "").strip()) for r in sample for c in ["F", "G"])
        assert count == 0
        materials.append([{c: r.get(c, "") for c in "ABCDE"} for r in sample])
        workbook_status[reviewer] = {"sample_rows": len(sample), "filled_label_cells": count}
        fact("reviewer_" + reviewer + "_filled_label_cells", count, "cells", relative, "Claim_review!F2:G601", "Nonempty human support and diagnosis cells")
    assert materials[0] == materials[1]
    values["reviewers"] = fact("prepared_reviewer_workbooks", len(materials), "workbooks", "BACE/analysis/validation/README.md",
                               "Which file to use; A/B workbook inspection", "Distinct prepared formal workbooks, not completed reviewers")
    values["workbook_status"] = workbook_status
    diagnosis_source = "BACE/script/evaluation/metrics.py"
    tree = ast.parse(register(diagnosis_source).read_text())
    labels = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "LABELS" for target in node.targets))
    values["diagnoses"] = fact("diagnosis_categories", len(labels), "ordered categories", diagnosis_source,
                               "LABELS", "Count of the ordered diagnosis labels in the metric implementation")
    assert values["diagnoses"] == 6
    for relative in ["docs/generation_evaluation.md", "BACE/PROTOCOL.md", "BACE/analysis/validation/README.md",
                     "BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt",
                     "BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt",
                     "paper/NATURE_SUSTAINABILITY_GUIDELINES.md", "paper/analysis/fig1/FIGURE_CONTRACT.md"]:
        register(relative)
    return values


def box(ax, x, y, w, h, title, body="", fill=BLUE_FILL, stroke=BLUE, dashed=False, title_size=7, body_size=6.5):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.7",
                          facecolor=fill, edgecolor=stroke, linewidth=0.65,
                          linestyle=(0, (3, 2)) if dashed else "solid", zorder=2)
    ax.add_patch(patch)
    if body:
        ax.text(x+w/2, y+h-4.4, title, fontsize=title_size, fontweight="bold", ha="center", va="center", color=INK, zorder=3)
        ax.text(x+w/2, y+(h-5.8)/2, body, fontsize=body_size, ha="center", va="center", linespacing=1.4, color=INK, zorder=3)
    else:
        ax.text(x+w/2, y+h/2, title, fontsize=title_size, fontweight="bold", ha="center", va="center", color=INK, zorder=3)


def arrow(ax, points, dashed=False, color=BLUE):
    path = MplPath(points, [MplPath.MOVETO] + [MplPath.LINETO]*(len(points)-1))
    ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=7,
                                linewidth=0.75, color=color, linestyle=(0, (3, 2)) if dashed else "solid", zorder=1))


def panel_heading(ax, letter, title, fig):
    transform = ax.transAxes + ScaledTranslation(0, 4/72, fig.dpi_scale_trans)
    ax.text(0, 1, letter, transform=transform, fontsize=8, fontweight="bold", va="bottom", ha="left", color=INK)
    transform = ax.transAxes + ScaledTranslation(13/72, 4/72, fig.dpi_scale_trans)
    ax.text(0, 1, title, transform=transform, fontsize=7.5, fontweight="bold", va="bottom", ha="left", color=INK)


def main():
    values = data()
    ART.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"], "font.size": 7,
                         "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "bace-fig1-v1",
                         "axes.linewidth": 0.65, "figure.facecolor": "white", "savefig.facecolor": "white"})
    fig = plt.figure(figsize=(180/25.4, 167/25.4))
    grid = fig.add_gridspec(2, 1, height_ratios=[52, 100], left=.03, right=.98, bottom=.018, top=.959, hspace=.16)
    a, b = fig.add_subplot(grid[0]), fig.add_subplot(grid[1])
    for ax, height in [(a, 52), (b, 100)]:
        ax.set_xlim(0, 176)
        ax.set_ylim(0, height)
        ax.set_axis_off()
    panel_heading(a, "a", "Study scope and supplied evidence", fig)
    panel_heading(b, "b", "BACE assessment and the human-review boundary", fig)

    cohort = [(f"{values['companies']} companies", "Selected sample"),
              (f"{values['years']} reporting years", "2019–2023"),
              (f"{values['tasks']} ESRS tasks", "E1 · S1 · G1"),
              (f"{values['planned']:,} planned", "Cases"),
              (f"{values['analysed']:,} analysed", "Paired disclosures")]
    for i, (title, body) in enumerate(cohort):
        box(a, 35*i, 38, 30, 13, title, body, NEUTRAL_FILL, "#96A1AA", title_size=6.8)
    for x, symbol in [(32.5, "×"), (67.5, "×"), (102.5, "=")]:
        a.text(x, 44.5, symbol, fontsize=7.5, ha="center", va="center", color=INK)
    arrow(a, [(135, 44.5), (139.4, 44.5)])
    a.text(170, 33.5, f"{values['excluded']} incomplete BACE cases excluded; no zero imputation", fontsize=6.5,
           ha="right", va="center", color=INK)
    box(a, 0, 0, 60, 27, "Source material",
        "Reports → narrative and table rows\nReport years: t−4 through t−1\nExtracted metric records\nSource years: t−4 through t", body_size=6.5)
    box(a, 70, 0, 44, 27, "Hybrid retrieval",
        f"BM25 + dense embeddings\nCompany and year filters\nUp to {values['per_type']} cards per type")
    box(a, 126, 0, 44, 27, "Supplied evidence (E)",
        f"Up to {values['maximum_cards']} ordered cards\nNarrative · Table · Metric")
    arrow(a, [(60, 13.5), (69.5, 13.5)])
    arrow(a, [(114, 13.5), (125.5, 13.5)])

    box(b, 0, 78, 48, 18, "Supplied evidence (E)", "Prompt-visible cards")
    box(b, 74, 78, 48, 18, "Generated disclosure", "One company–year–task case")
    arrow(b, [(48, 86), (73.5, 86)])
    b.text(61, 90.3, "Generation", fontsize=6.5, ha="center", va="center", color=INK)
    box(b, 0, 52, 48, 18, "Evidence claims (ECs)", "Extracted evidence propositions")
    box(b, 74, 52, 48, 18, "Disclosure claims (DCs)", "Extracted disclosure propositions")
    for x in [24, 98]:
        arrow(b, [(x, 78), (x, 70.5)])
        b.text(x+4, 74, "Extract, review,\ndeduplicate", fontsize=6.5, va="center", ha="left", color=INK, linespacing=1.2)
    box(b, 0, 25, 48, 18, "Candidate selection", "EC and DC texts")
    arrow(b, [(24, 52), (24, 43.5)])
    arrow(b, [(98, 52), (98, 48), (44, 48), (44, 43.5)])
    box(b, 74, 25, 48, 18, "Judgment inputs", "One DC + candidate ECs\nCompany + reporting year")
    arrow(b, [(48, 34), (73.5, 34)])
    b.text(61, 38, "Per DC", fontsize=6.5, ha="center", va="center", color=INK)
    box(b, 138, 25, 36, 18, "Support verdict", "Direct / Inferred /\nUnsupported")
    arrow(b, [(122, 34), (137.5, 34)])
    box(b, 138, 0, 36, 17, "Diagnosis", "Six ordered categories")
    arrow(b, [(156, 25), (156, 17.5)])
    b.text(152, 21.1, "If unsupported", fontsize=6.5, ha="right", va="center", color=INK)

    box(b, 0, 0, 122, 17, "Prepared human assessment — annotation pending",
        f"Same DC, candidate ECs, company and reporting year\n{values['human_n']} sampled claims; {values['reviewers']} workbooks; local labels blank",
        fill=AMBER_FILL, stroke=AMBER, dashed=True)
    arrow(b, [(98, 25), (98, 17.5)], dashed=True, color=AMBER)
    b.text(138, 92.5, "Material qualifiers", fontsize=7, fontweight="bold", ha="left", va="center", color=INK)
    b.text(138, 81.2, "Entity · Period\nPopulation · Scope\nMetric · Unit\nStatus · Certainty", fontsize=6.5,
           ha="left", va="center", color=INK, linespacing=1.6)
    b.text(138, 60, "Support is conditional\non extracted claims\nand candidate selection", fontsize=6.5,
           ha="left", va="center", color=BLUE, linespacing=1.4)

    fig.canvas.draw()
    alignment = require_matplotlib_panel_alignment(fig, panel_ids=["a", "b"], json_out=OUT/"fig1.alignment.json",
                                                   overlay_svg=OUT/"fig1.alignment.svg", tolerance_pt=1.5,
                                                   gutter_tolerance_pt=1.5, require_panel_labels=True, strict=True)
    base = ART / "fig1_study_design"
    for extension in ["pdf", "svg", "png"]:
        fig.savefig(base.with_suffix("." + extension), dpi=600)
    # Matplotlib generates previews for the complete figure and each panel.
    for ax, name in [(a, "a"), (b, "b")]:
        extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(OUT / f"panel_{name}.png", dpi=300, bbox_inches=extent.expanded(1.025, 1.045))
    plt.close(fig)

    with (OUT / "source_data.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(FACTS[0]))
        writer.writeheader()
        writer.writerows(FACTS)
    (OUT / "verified_facts.json").write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n")
    record = {"status": "RENDERED_PENDING_PDF_QA", "prepared_date": "2026-10-01",
              "checked_at_utc": datetime.now(timezone.utc).isoformat(), "command": "/usr/bin/python3 paper/analysis/fig1/render_fig1.py",
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "python": sys.version, "matplotlib": matplotlib.__version__, "input_files": INPUTS,
              "facts": FACTS, "geometry_mm": {"width": 180, "height": 167}, "minimum_source_font_pt": 6.5,
              "minimum_font_at_160mm_pt": 6.5*160/180, "alignment_verdict": alignment["verdict"],
              "outputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                          [base.with_suffix("."+ext) for ext in ["pdf", "svg", "png"]] + [OUT/"source_data.csv", OUT/"verified_facts.json"]},
              "scope": "Original scripted schematic with observed cohort counts and configured evidence limits. No model calls, hypothesis tests or completed human validation."}
    (OUT / "provenance.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "alignment": alignment["verdict"], "cohort": values["analysed"], "figure": str(base.with_suffix('.pdf'))}))


if __name__ == "__main__":
    main()
