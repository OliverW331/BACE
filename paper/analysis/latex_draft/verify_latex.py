"""Verify the initial LaTeX migration, rendered prose and portable source ZIP.

This audit checks the initial imported version against its dated Markdown
sources. It intentionally requires review if later scientific edits diverge.
It never overwrites main.tex and makes no model calls or external uploads.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata
import zipfile

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PROJECT = ROOT / "paper/manuscript"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(text):
    return re.sub(r"\W", "", unicodedata.normalize("NFKC", text), flags=re.UNICODE)


def pdf_text(path):
    text = subprocess.check_output(["pdftotext", "-enc", "UTF-8", str(path), "-"], text=True)
    # Remove footer page numbers before checking paragraphs split across pages.
    return re.sub(r"(?m)^\s*\d+\s*$", "", text)


def main():
    spec = importlib.util.spec_from_file_location("migration", OUT / "migrate_drafts.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    tex = (PROJECT / "main.tex").read_text()
    manifest = json.loads((OUT / "migration.json").read_text())
    results_prov = json.loads((ROOT / "paper/analysis/results_draft/provenance.json").read_text())
    methods_prov = json.loads((ROOT / "paper/analysis/methods_draft/provenance.json").read_text())
    assert results_prov["status"] == methods_prov["status"] == "PASS"
    pdf = PROJECT / "main.pdf"
    rendered = pdf_text(pdf)
    (OUT / "main.txt").write_text(rendered)
    normalized_pdf = canonical(rendered)
    paragraph_checks = {}
    for name, relative in migration.SOURCES.items():
        source = ROOT / relative
        assert sha(source) == manifest["sources"][relative] == results_prov["outputs"][relative]
        body = migration.manuscript_body(source)
        imported = tex.split("% BEGIN_" + name.upper() + "\n")[1].split("% END_" + name.upper())[0]
        assert imported == migration.convert(body), "Migration changed source content: " + name
        assert not any(heading in imported for heading in ["Working evidence ledger", "Editorial status", "Outstanding facts and integration"])
        for pid, paragraph in re.findall(r"<!-- ([RM]\d\d) -->\s*(.*?)(?=<!-- [RM]\d\d -->|\Z)", body, re.S):
            prose = re.sub(r"(?m)^#+ .*\n?", "", paragraph)
            # Math and citation placements are separately checked in the exact
            # source-to-TeX comparison; confirm every substantial prose fragment
            # appears in the actual compiled PDF, including across page breaks.
            pieces = re.split(r"\\\[.*?\\\]|\\\(.*?\\\)|\[@[^\]]+\]", prose, flags=re.S)
            chunks = [canonical(piece) for piece in pieces if len(canonical(piece)) >= 25]
            assert chunks and all(chunk in normalized_pdf for chunk in chunks), pid
            paragraph_checks[pid] = {"rendered_prose_fragments": len(chunks), "source": relative, "status": "PASS"}
    assert len(paragraph_checks) == 39
    # Preserve signs, percentages and key denominators in the reading copy.
    compact = re.sub(r"\s+", " ", rendered)
    for token in ["1,798", "94,955", "55.4%", "73.5%", "−34.9", "−35.3", "−36.2", "−33.5", "−36.5", "−34.1"]:
        assert token in compact, token

    migrated_occurrences = json.loads((OUT / "citation_occurrences.json").read_text())
    methods_block = tex.split("% BEGIN_METHODS\n")[1].split("% END_METHODS")[0]
    assert re.findall(r"\\cite\{([^}]+)\}", methods_block) == manifest["citation_keys"] == [r["citation_key"] for r in migrated_occurrences]
    intro_dir = ROOT / "paper/analysis/introduction_draft"
    intro_occurrences = json.loads((intro_dir / "citation_occurrences.json").read_text())
    intro_prov = json.loads((intro_dir / "provenance.json").read_text())
    assert intro_prov["status"] == "PASS" and intro_prov["pdf_sha256"] == sha(pdf)
    assert intro_prov["inputs"]["paper/manuscript/main.tex"] == sha(PROJECT / "main.tex")
    paragraph_checks.update(intro_prov["paragraph_checks"])
    assert len(paragraph_checks) == 45
    occurrences = intro_occurrences + migrated_occurrences
    keys = [key for group in re.findall(r"\\cite\{([^}]+)\}", tex) for key in group.split(",")]
    assert keys == [r["citation_key"] for r in occurrences]
    library = (ROOT / "paper/references.bib").read_text()
    entries = {re.match(r"@\w+\{([^,]+),", part).group(1): part.rstrip() for part in re.split(r"(?=^@\w+\{)", library, flags=re.M) if part.startswith("@")}
    assert (PROJECT / "references.bib").read_text() == "\n\n".join(entries[key] for key in dict.fromkeys(keys)) + "\n"
    for occurrence in occurrences:
        fulltext = re.sub(r"\s+", " ", (ROOT / occurrence["fulltext_path"]).read_text())
        assert all(fragment in fulltext for fragment in occurrence["verified_excerpt_fragments"])
    labels = re.findall(r"\\label\{fig:([1-4])\}", tex)
    assert labels == ["1", "2", "3", "4"]
    assert set(re.findall(r"\\ref\{fig:([^}]+)\}", tex)) == set(labels)
    figure_files = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
    placeholders = re.findall(r"DRAFT\\_PENDING: Figure ([1-4])", tex)
    assert figure_files == ["fig1_study_design.pdf", "fig2_support.pdf", "fig3_diagnoses_cases.pdf", "fig4_native_comparison.pdf"] and placeholders == []
    assert all((PROJECT / "figures" / filename).is_file() for filename in figure_files)
    assert "annotation cells blank" in rendered
    assert "UNDEFINED" not in rendered and "??" not in rendered
    assert not re.search(r"\\(?:input|include)\{(?:/|\.\.)", tex)

    build = json.loads((PROJECT / "build/build_manifest.json").read_text())
    assert build["main_pdf_sha256"] == sha(pdf)
    archive = PROJECT / "bace_overleaf.zip"
    assert build["archive_sha256"] == sha(archive)
    for relative, expected in build["source_files"].items():
        assert sha(PROJECT / relative) == expected, relative
    temp_root = OUT / "tmp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="overleaf-check-", dir=temp_root) as folder:
        destination = Path(folder)
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.namelist()
            assert set(members) == set(build["source_files"])
            assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in members)
            for name in members:
                assert hashlib.sha256(bundle.read(name)).hexdigest() == build["source_files"][name]
            bundle.extractall(destination)
        command = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-outdir=build", "main.tex"]
        result = subprocess.run(command, cwd=destination, capture_output=True, text=True)
        (OUT / "portable_compile.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, "Portable compilation failed; inspect portable_compile.log"
        log = (destination / "build/main.log").read_text()
        assert not re.search(r"Warning:|Overfull \\[hv]box|Missing character:|^!", log, re.M)
        assert pdf_text(destination / "build/main.pdf") == rendered, "ZIP renders different text"
    pages = int(re.search(r"Pages:\s+(\d+)", subprocess.check_output(["pdfinfo", str(pdf)], text=True)).group(1))
    inputs = [ROOT / relative for relative in migration.SOURCES.values()] + [
        ROOT / "paper/references.bib", ROOT / "paper/01_paper_blueprint.md",
        ROOT / "paper/analysis/results_draft/provenance.json", ROOT / "paper/analysis/methods_draft/provenance.json",
        OUT / "migration.json", OUT / "citation_occurrences.json", OUT / "migrate_drafts.py",
        PROJECT / "build/build_manifest.json", intro_dir / "provenance.json",
        intro_dir / "citation_occurrences.json", intro_dir / "verify_introduction.py"] + [PROJECT / p for p in members]
    inputs += [ROOT / occurrence["fulltext_path"] for occurrence in occurrences]
    record = {"status": "PASS", "prepared_date": "2026-10-01", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "command": f"{sys.executable} paper/analysis/latex_draft/verify_latex.py", "script_sha256": sha(Path(__file__)),
              "inputs": {str(path.relative_to(ROOT)): sha(path) for path in inputs},
              "paragraph_checks": paragraph_checks, "citation_keys": keys, "figure_labels": labels,
              "figure_artwork": figure_files, "figure_placeholders": placeholders,
              "pdf_pages": pages, "portable_source_compile": "PASS", "portable_pdf_text_matches": True,
              "compilation_warnings": 0, "archive_members": members,
              "outputs": {str(p.relative_to(ROOT)): sha(p) for p in [pdf, archive, OUT / "main.txt", OUT / "portable_compile.log"]},
              "layout_adjustments": "The six-paragraph Introduction and ten unique references are integrated. Figures 1-4 retain their artwork and full legends; imported Results and Methods prose is unchanged.",
              "limits": "Initial conversion and compilation audit, not scientific validation or completed author review. Overleaf compatibility was tested by an isolated local source compile; no external account was accessed. Visual inspection is recorded separately."}
    (OUT / "provenance.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "paragraphs": len(paragraph_checks), "citations": len(keys), "figure_artwork": len(figure_files), "figure_placeholders": len(placeholders), "pages": pages, "portable_compile": "PASS"}))


if __name__ == "__main__":
    main()
