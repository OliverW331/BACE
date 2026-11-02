"""Check final Figure 1 geometry, provenance and manuscript integration."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

import fitz

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
ART = ROOT / "paper/manuscript/figures"
SCRIPTS = Path("/home/muwang/.codex/skills/nature-figure/scripts")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(2**20):
            digest.update(block)
    return digest.hexdigest()


def canonical(text):
    return re.sub(r"\W", "", unicodedata.normalize("NFKC", text))


def tool_json(script, args, output):
    result = subprocess.run([sys.executable, str(SCRIPTS/script), *map(str, args), "--json"],
                            capture_output=True, text=True, check=True)
    value = json.loads(result.stdout)
    (OUT/output).write_text(json.dumps(value, indent=2) + "\n")
    return value


def main():
    pdf = ART/"fig1_study_design.pdf"
    rendering = json.loads((OUT/"provenance.json").read_text())
    assert sha(OUT/"render_fig1.py") == rendering["script_sha256"]
    for relative, expected in rendering["input_files"].items():
        assert sha(ROOT/relative) == expected["sha256"], relative
    for relative, expected in rendering["outputs"].items():
        assert sha(ROOT/relative) == expected, relative
    source = tool_json("validate_figure.py", [OUT/"render_fig1.py"], "source_validation.json")
    assert source["summary"]["counts"]["FAIL"] == 0
    warnings = {f["check_id"]: f for f in source["findings"] if f["level"] == "WARN"}
    reviewed = {
        "EXPORT-RASTER": "The submission artwork is vector PDF/SVG; PNG is a 600 dpi preview. A TIFF copy is unnecessary for this original vector schematic.",
        "FINAL-WIDTH": "The heuristic source parser misreads 180/25.4 as 180 inches. Actual PDF page geometry is measured below and is 180 mm wide, within Nature Sustainability's maximum."
    }
    assert set(warnings) <= set(reviewed)
    glyphs = tool_json("audit_pdf_text.py", [pdf, "--min-pt", 5], "fig1.glyph-audit.json")
    assert glyphs["auditable"] and glyphs["below_minimum_count"] == 0
    collision_command = [sys.executable, str(SCRIPTS/"audit_figure_collisions.py"), str(pdf),
                         "--json-out", str(OUT/"fig1.collision-audit.json"), "--overlay-pdf", str(OUT/"fig1.collision-audit.pdf")]
    collision = subprocess.run(collision_command, capture_output=True, text=True, check=True)
    (OUT/"collision_console.txt").write_text(collision.stdout)
    alignment = json.loads((OUT/"fig1.alignment.json").read_text())
    assert alignment["verdict"] == "PASS"
    document = fitz.open(pdf)
    assert len(document) == 1
    page = document[0]
    dimensions = {"width": page.rect.width*25.4/72, "height": page.rect.height*25.4/72}
    assert abs(dimensions["width"]-180) < .001 and abs(dimensions["height"]-167) < .001
    assert len(page.get_images()) == 0
    extracted = page.get_text()
    for fragment in ["1,800", "1,798", "600", "annotation pending", "local labels blank", "Judgment inputs", "Six ordered categories"]:
        assert fragment in extracted, fragment
    assert "<text" in (ART/"fig1_study_design.svg").read_text()
    png = fitz.Pixmap(ART/"fig1_study_design.png")
    dpi = png.width*25.4/dimensions["width"]
    assert dpi >= 599

    tex_path = ROOT/"paper/manuscript/main.tex"
    tex = tex_path.read_text()
    figure = tex.split(r"\includegraphics[width=\linewidth]{fig1_study_design.pdf}")[1].split(r"\label{fig:1}")[0]
    caption = figure.split(r"\caption{")[1].strip()
    assert caption.endswith("}")
    caption = caption[:-1]
    simplified = caption.replace(r"\textbf", "").replace(r"\(", "").replace(r"\)", "")
    legend = (OUT/"legend.md").read_text().split("## Provenance")[0].split("\n", 2)[2]
    assert canonical(simplified) == canonical(legend), "Caption and working legend differ"
    for value in ["30", "2019", "2023", "12", "1,800", "1,798", "600"]:
        assert value in caption
    caption_words = len(re.sub(r"\\[a-zA-Z]+|[{}]", "", caption).split())

    manuscript_path = ROOT/"paper/manuscript/main.pdf"
    manuscript = fitz.open(manuscript_path)
    matches = [p for p in manuscript if "Study scope and supplied evidence" in p.get_text()]
    assert len(matches) == 1
    embedded = matches[0]
    assert "Figure 1:" in embedded.get_text()
    assert "external corporate truth" in embedded.get_text()
    spans = [span for block in embedded.get_text("dict")["blocks"] if "lines" in block
             for line in block["lines"] for span in line["spans"] if "DejaVu" in span["font"]]
    assert spans
    minimum_embedded_font = min(span["size"] for span in spans)
    assert minimum_embedded_font >= 5
    embedded.get_pixmap(matrix=fitz.Matrix(1.7, 1.7)).save(OUT/"manuscript_figure1_page.png")
    preview_paths = [OUT/"manuscript_figure1_page.png"]
    # Render the final manuscript in Python for a page-by-page layout check.
    previews = OUT/"manuscript_previews"
    previews.mkdir(exist_ok=True)
    for p in manuscript:
        path = previews/f"page-{p.number+1:02}.png"
        p.get_pixmap(matrix=fitz.Matrix(.85, .85)).save(path)
        preview_paths.append(path)

    result = {"status": "PASS", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "figure_sha256": sha(pdf), "script_sha256": sha(Path(__file__)),
              "figure_dimensions_mm": dimensions, "preview_dpi": dpi,
              "minimum_figure_font_pt": glyphs["minimum_found_pt"], "minimum_embedded_font_pt": minimum_embedded_font,
              "source_warnings_reviewed": {key: reviewed[key] for key in warnings},
              "alignment": "PASS", "collision": "PASS", "editable_vector_text": True,
              "caption_words": caption_words, "caption_matches_working_legend": True,
              "caption_sha256": hashlib.sha256(caption.encode()).hexdigest(),
              "manuscript_figure_page": embedded.number+1, "manuscript_pages": len(manuscript),
              "manuscript_pdf_sha256": sha(manuscript_path), "main_tex_sha256": sha(tex_path),
              "python": sys.version, "pymupdf": fitz.VersionBind,
              "previews": {str(path.relative_to(ROOT)): sha(path) for path in preview_paths},
              "limits": "Automated geometry and provenance checks; visual inspection is recorded separately. No author review or human validation is inferred."}
    (OUT/"qa.json").write_text(json.dumps(result, indent=2) + "\n")
    rendering["status"] = "PASS_AUTOMATED_QA"
    rendering["qa_record"] = "paper/analysis/fig1/qa.json"
    (OUT/"provenance.json").write_text(json.dumps(rendering, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "figure_dimensions_mm", "minimum_embedded_font_pt", "caption_words", "manuscript_figure_page", "manuscript_pages"]}))


if __name__ == "__main__":
    main()
