"""Compile the editable manuscript and package a portable Overleaf project.

Requires a local LaTeX distribution providing latexmk, pdfLaTeX and BibTeX.
Uses only the Python standard library; never migrates or rewrites main.tex.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if shutil.which("latexmk") is None:
        raise SystemExit("latexmk is unavailable. Upload the source project to Overleaf and select pdfLaTeX.")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    command = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-outdir=build", "main.tex"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (build / "compile_console.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit("Compilation failed; inspect build/compile_console.log.")
    log = (build / "main.log").read_text()
    problems = [line for line in log.splitlines() if re.search(r"Warning:|Overfull \\[hv]box|Missing character:|^!", line)]
    if problems:
        raise SystemExit("Resolve compilation warnings before packaging:\n" + "\n".join(problems))
    shutil.copyfile(build / "main.pdf", ROOT / "main.pdf")
    members = [ROOT / name for name in ["main.tex", "references.bib", "README.md", "build.py", ".gitignore"]]
    members += sorted(path for path in (ROOT / "figures").rglob("*") if path.is_file() and not path.is_symlink())
    archive = ROOT / "bace_overleaf.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in members:
            output.write(path, path.relative_to(ROOT).as_posix())
    record = {"status": "PASS", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "command": command, "warnings": problems,
              "source_files": {p.relative_to(ROOT).as_posix(): sha(p) for p in members},
              "main_pdf_sha256": sha(ROOT / "main.pdf"), "archive_sha256": sha(archive),
              "compiler": subprocess.check_output(["pdflatex", "--version"], text=True).splitlines()[0],
              "scope": "Local compilation and source packaging. No Overleaf upload or journal submission."}
    (build / "build_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "pdf": str(ROOT / "main.pdf"), "overleaf_zip": str(archive), "source_files": len(members), "warnings": 0}))


if __name__ == "__main__":
    main()
