"""Audit final Figure 3, its source data and its compiled manuscript placement."""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

import pymupdf as fitz

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
ART = ROOT / "paper/manuscript/figures"
SCRIPTS = Path("/home/muwang/.codex/skills/nature-figure/scripts")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(2**20):
            h.update(block)
    return h.hexdigest()


def canonical(text):
    return re.sub(r"\W", "", unicodedata.normalize("NFKC", text))


def run_json(script, args, filename):
    result = subprocess.run([sys.executable, str(SCRIPTS/script), *map(str, args), "--json"],
                            capture_output=True, text=True)
    (OUT/filename).write_text(result.stdout)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def main():
    pdf = ART/"fig3_diagnoses_cases.pdf"
    rendering = json.loads((OUT/"provenance.json").read_text())
    assert sha(OUT/"render_fig3.py") == rendering["script_sha256"]
    for relative, expected in rendering["input_files"].items():
        assert sha(ROOT/relative) == expected["sha256"], relative
    for relative, expected in rendering["outputs"].items():
        assert sha(ROOT/relative) == expected, relative
    data = json.loads((OUT/"data_provenance.json").read_text())
    assert data["status"] == "PASS" and data["script_sha256"] == sha(OUT/"prepare_data.py")
    for relative, expected in data["input_files"].items():
        assert sha(ROOT/relative) == expected["sha256"], relative
    for relative, expected in data["outputs"].items():
        assert sha(ROOT/relative) == expected, relative
    source = run_json("validate_figure.py", [OUT/"render_fig3.py"], "source_validation.json")
    warnings = {f["check_id"] for f in source["findings"] if f["level"] == "WARN"}
    reviewed = {
        "EXPORT-RASTER": "The primary artwork is editable vector PDF/SVG. The 600 dpi PNG is a preview; no TIFF is needed for this vector chart.",
        "FINAL-WIDTH": "The static parser does not resolve width_in. Actual PDF width is measured below: 180 mm, within the Nature Sustainability limit."
    }
    assert source["summary"]["counts"]["FAIL"] == 0 and warnings <= set(reviewed)
    glyphs = run_json("audit_pdf_text.py", [pdf, "--min-pt", 5], "fig3.glyph-audit.json")
    assert glyphs["auditable"] and glyphs["below_minimum_count"] == 0
    result = subprocess.run([sys.executable, str(SCRIPTS/"audit_figure_collisions.py"), str(pdf),
                             "--json-out", str(OUT/"fig3.collision-audit.json"),
                             "--overlay-pdf", str(OUT/"fig3.collision-audit.pdf")], capture_output=True, text=True)
    (OUT/"collision_console.txt").write_text(result.stdout+result.stderr)
    assert result.returncode == 0, result.stdout+result.stderr
    collision = json.loads((OUT/"fig3.collision-audit.json").read_text())
    assert collision["auditable"] and collision["summary"]["fail"] == 0
    assert collision["summary"]["warn"] == 0, "Review every collision warning before delivery"
    alignment = json.loads((OUT/"fig3.alignment.json").read_text())
    assert alignment["verdict"] == "PASS"
    document = fitz.open(pdf)
    assert len(document) == 1
    page = document[0]
    dimensions = {"width": page.rect.width*25.4/72, "height": page.rect.height*25.4/72}
    assert abs(dimensions["width"]-180) < .001 and abs(dimensions["height"]-170) < .001
    assert not page.get_images()
    assert "<text" in (ART/"fig3_diagnoses_cases.svg").read_text()
    extracted = page.get_text()
    for fragment in ["42,646", "73.5%", "19,130", "12,205", "6,378", "3,193", "1,698", "2019", "2022", "209", "216"]:
        assert fragment in extracted, fragment
    displayed = list(csv.DictReader((OUT/"displayed_text.csv").open()))
    for row in displayed:
        assert canonical(row["text"]) in canonical(extracted), row["role"]
    png = fitz.Pixmap(ART/"fig3_diagnoses_cases.png")
    dpi = png.width*25.4/dimensions["width"]
    assert dpi >= 599

    tex_path = ROOT/"paper/manuscript/main.tex"
    tex = tex_path.read_text()
    figure = tex.split(r"\includegraphics[width=\linewidth]{fig3_diagnoses_cases.pdf}")[1].split(r"\label{fig:3}")[0]
    caption = figure.split(r"\caption{")[1].strip()
    assert caption.endswith("}")
    caption = caption[:-1]
    simplified = caption.replace(r"\textbf", "")
    legend = (OUT/"legend.md").read_text().split("## Provenance")[0].split("\n", 2)[2]
    assert canonical(simplified) == canonical(legend), "Caption and working legend differ"
    words = len(re.sub(r"\\[a-zA-Z]+|[{}]", "", caption).split())
    manuscript_path = ROOT/"paper/manuscript/main.pdf"
    manuscript = fitz.open(manuscript_path)
    matches = [p for p in manuscript if "Original glossary rows" in p.get_text()]
    assert len(matches) == 1
    embedded = matches[0]
    assert "Figure 3:" in embedded.get_text() and "independent human validation" in embedded.get_text()
    spans = [s for block in embedded.get_text("dict")["blocks"] if "lines" in block
             for line in block["lines"] for s in line["spans"] if "DejaVu" in s["font"]]
    assert spans and min(s["size"] for s in spans) >= 5
    # Confirm Figure 1's already audited artwork is unchanged after repackaging.
    fig1 = json.loads((ROOT/"paper/analysis/fig1/qa.json").read_text())
    assert sha(ART/"fig1_study_design.pdf") == fig1["figure_sha256"]
    fig1_pages = [p.number+1 for p in manuscript if "Study scope and supplied evidence" in p.get_text()]
    assert len(fig1_pages) == 1
    fig2 = json.loads((ROOT/"paper/analysis/fig2/qa.json").read_text())
    assert sha(ART/"fig2_support.pdf") == fig2["figure_sha256"]
    fig2_pages = [p.number+1 for p in manuscript if "Support across all disclosure tasks" in p.get_text()]
    assert len(fig2_pages) == 1
    preview_paths = []
    target = OUT/"manuscript_figure3_page.png"
    embedded.get_pixmap(matrix=fitz.Matrix(1.7, 1.7)).save(target)
    preview_paths.append(target)
    previews = OUT/"manuscript_previews"
    previews.mkdir(exist_ok=True)
    for p in manuscript:
        path = previews/f"page-{p.number+1:02}.png"
        p.get_pixmap(matrix=fitz.Matrix(.85, .85)).save(path)
        preview_paths.append(path)
    report = dict(status="PASS", checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  figure_sha256=sha(pdf), script_sha256=sha(Path(__file__)), figure_dimensions_mm=dimensions,
                  preview_dpi=dpi, minimum_figure_font_pt=glyphs["minimum_found_pt"],
                  minimum_embedded_font_pt=min(s["size"] for s in spans),
                  source_warnings_reviewed={key: reviewed[key] for key in warnings},
                  alignment="PASS", collision="PASS", editable_vector_text=True,
                  caption_words=words, caption_matches_working_legend=True,
                  caption_sha256=hashlib.sha256(caption.encode()).hexdigest(), legend_sha256=sha(OUT/"legend.md"),
                  manuscript_figure_page=embedded.number+1, manuscript_pages=len(manuscript),
                  figure1_artwork_unchanged=True, figure1_page=fig1_pages[0],
                  figure2_artwork_unchanged=True, figure2_page=fig2_pages[0],
                  original_case_and_report_inputs_unchanged=True, displayed_text_verified=True,
                  manuscript_pdf_sha256=sha(manuscript_path), main_tex_sha256=sha(tex_path),
                  python=sys.version, pymupdf=fitz.VersionBind,
                  previews={str(path.relative_to(ROOT)): sha(path) for path in preview_paths},
                  limits="Automated source, geometry and integration checks; assistant visual inspection recorded separately. No author scientific review, completed human validation or new statistical inference is implied.")
    (OUT/"qa.json").write_text(json.dumps(report, indent=2)+"\n")
    rendering["status"] = "PASS_AUTOMATED_QA"
    rendering["qa_record"] = "paper/analysis/fig3/qa.json"
    (OUT/"provenance.json").write_text(json.dumps(rendering, indent=2)+"\n")
    print(json.dumps({key: report[key] for key in ["status", "figure_dimensions_mm", "minimum_embedded_font_pt", "caption_words", "manuscript_figure_page", "manuscript_pages"]}))


if __name__ == "__main__":
    main()
