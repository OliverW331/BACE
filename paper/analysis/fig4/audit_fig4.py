"""Audit final Figure 4, its source data and its compiled manuscript placement."""
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
    pdf = ART/"fig4_native_comparison.pdf"
    rendering = json.loads((OUT/"provenance.json").read_text())
    assert sha(OUT/"render_fig4.py") == rendering["script_sha256"]
    for relative, expected in rendering["input_files"].items():
        assert sha(ROOT/relative) == expected["sha256"], relative
    for relative, expected in rendering["outputs"].items():
        assert sha(ROOT/relative) == expected, relative
    source = run_json("validate_figure.py", [OUT/"render_fig4.py"], "source_validation.json")
    warnings = {f["check_id"] for f in source["findings"] if f["level"] == "WARN"}
    reviewed = {
        "EXPORT-RASTER": "The primary artwork is editable vector PDF/SVG. The 600 dpi PNG is a preview; no TIFF is needed for this vector chart.",
        "FINAL-WIDTH": "The static parser does not resolve width_in. Actual PDF width is measured below: 180 mm, within the Nature Sustainability limit."
    }
    assert source["summary"]["counts"]["FAIL"] == 0 and warnings <= set(reviewed)
    glyphs = run_json("audit_pdf_text.py", [pdf, "--min-pt", 5], "fig4.glyph-audit.json")
    assert glyphs["auditable"] and glyphs["below_minimum_count"] == 0
    result = subprocess.run([sys.executable, str(SCRIPTS/"audit_figure_collisions.py"), str(pdf),
                             "--json-out", str(OUT/"fig4.collision-audit.json"),
                             "--overlay-pdf", str(OUT/"fig4.collision-audit.pdf")], capture_output=True, text=True)
    (OUT/"collision_console.txt").write_text(result.stdout+result.stderr)
    assert result.returncode == 0, result.stdout+result.stderr
    collision = json.loads((OUT/"fig4.collision-audit.json").read_text())
    assert collision["auditable"] and collision["summary"]["fail"] == 0
    assert collision["summary"]["warn"] == 0, "Review every collision warning before delivery"
    alignment = json.loads((OUT/"fig4.alignment.json").read_text())
    assert alignment["verdict"] == "PASS"
    document = fitz.open(pdf)
    assert len(document) == 1
    page = document[0]
    dimensions = {"width": page.rect.width*25.4/72, "height": page.rect.height*25.4/72}
    assert abs(dimensions["width"]-180) < .001 and abs(dimensions["height"]-138) < .001
    assert not page.get_images()
    assert "<text" in (ART/"fig4_native_comparison.svg").read_text()
    extracted = page.get_text()
    for fragment in ["1,798", "30", "55.4%", "90.2%", "90.7%", "−34.9", "−35.3", "−36.2", "−33.5", "−36.5", "−34.1", "52", "40", "42"]:
        assert fragment in extracted, fragment
    summaries = list(csv.DictReader((OUT/"method_summaries.csv").open()))
    for row in summaries:
        assert row["method"] in extracted and f"{float(row['mean_score_percent']):.1f}%" in extracted
        assert f"{float(row['median_claim_count']):.0f}" in extracted
    png = fitz.Pixmap(ART/"fig4_native_comparison.png")
    dpi = png.width*25.4/dimensions["width"]
    assert dpi >= 599

    tex_path = ROOT/"paper/manuscript/main.tex"
    tex = tex_path.read_text()
    figure = tex.split(r"\includegraphics[width=\linewidth]{fig4_native_comparison.pdf}")[1].split(r"\label{fig:4}")[0]
    caption = figure.split(r"\caption{")[1].strip()
    assert caption.endswith("}")
    caption = caption[:-1]
    simplified = caption.replace(r"\textbf", "")
    legend = (OUT/"legend.md").read_text().split("## Provenance")[0].split("\n", 2)[2]
    assert canonical(simplified) == canonical(legend), "Caption and working legend differ"
    words = len(re.sub(r"\\[a-zA-Z]+|[{}]", "", caption).split())
    manuscript_path = ROOT/"paper/manuscript/main.pdf"
    manuscript = fitz.open(manuscript_path)
    matches = [p for p in manuscript if "Native score distributions" in p.get_text()]
    assert len(matches) == 1
    embedded = matches[0]
    assert "Figure 4:" in embedded.get_text() and "model-run variability" in embedded.get_text()
    spans = [s for block in embedded.get_text("dict")["blocks"] if "lines" in block
             for line in block["lines"] for s in line["spans"] if "DejaVu" in s["font"]]
    assert spans and min(s["size"] for s in spans) >= 5
    # Confirm all three previously audited artworks remain unchanged.
    prior_figures = {}
    for number, stem, anchor in [
        (1, "fig1_study_design", "Study scope and supplied evidence"),
        (2, "fig2_support", "Support across all disclosure tasks"),
        (3, "fig3_diagnoses_cases", "Original glossary rows")
    ]:
        previous = json.loads((ROOT/f"paper/analysis/fig{number}/qa.json").read_text())
        assert sha(ART/(stem+".pdf")) == previous["figure_sha256"]
        pages = [p.number+1 for p in manuscript if anchor in p.get_text()]
        assert len(pages) == 1
        prior_figures[str(number)] = dict(artwork_unchanged=True, page=pages[0])
    preview_paths = []
    target = OUT/"manuscript_figure4_page.png"
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
                  previous_figures=prior_figures,
                  manuscript_pdf_sha256=sha(manuscript_path), main_tex_sha256=sha(tex_path),
                  python=sys.version, pymupdf=fitz.VersionBind,
                  previews={str(path.relative_to(ROOT)): sha(path) for path in preview_paths},
                  limits="Automated source, geometry and integration checks; assistant visual inspection recorded separately. No author scientific review, completed human validation or new statistical inference is implied.")
    (OUT/"qa.json").write_text(json.dumps(report, indent=2)+"\n")
    rendering["status"] = "PASS_AUTOMATED_QA"
    rendering["qa_record"] = "paper/analysis/fig4/qa.json"
    (OUT/"provenance.json").write_text(json.dumps(rendering, indent=2)+"\n")
    print(json.dumps({key: report[key] for key in ["status", "figure_dimensions_mm", "minimum_embedded_font_pt", "caption_words", "manuscript_figure_page", "manuscript_pages"]}))


if __name__ == "__main__":
    main()
