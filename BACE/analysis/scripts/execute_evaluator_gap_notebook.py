"""Execute notebook 04 in a fresh kernel without touching earlier outputs."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent.parent
OUT = HERE / "outputs/evaluator_gap"
RUNTIME = OUT / ".runtime"
for name, directory in {"MPLCONFIGDIR": RUNTIME / "matplotlib", "IPYTHONDIR": RUNTIME / "ipython",
                        "JUPYTER_DATA_DIR": RUNTIME / "jupyter", "JUPYTER_RUNTIME_DIR": RUNTIME / "jupyter_runtime"}.items():
    os.environ[name] = str(directory)
    directory.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from evaluator_gap_analysis import sha, save_json
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from bs4 import BeautifulSoup


def environment(python):
    command = "import importlib.metadata as m,json,platform;print(json.dumps({'python':platform.python_version(),'packages':{d.metadata['Name']:d.version for d in m.distributions()}}))"
    return json.loads(subprocess.check_output([str(python), "-B", "-c", command], text=True))


def protected_files():
    paths = set()
    for stem in ("00_data_landscape", "01_evidence_support", "02_failure_patterns", "03_evaluator_comparison"):
        paths.add(HERE / f"{stem}.ipynb")
    for p in (HERE / "outputs").rglob("*"):
        if p.is_file() and not p.is_relative_to(OUT):
            paths.add(p)
    for folder in (HERE / "scripts", HERE):
        for p in folder.glob("*.py"):
            if "evaluator_gap" not in p.name:
                paths.add(p)
    paths.update([ROOT / "BACE/config/freeze.json", ROOT / "BACE/PROTOCOL.md",
                  HERE / "requirements.lock.txt", ROOT / "BACE/requirements.lock.txt"])
    freeze = json.loads((ROOT / "BACE/config/freeze.json").read_text())
    for relative, expected in freeze["files"].items():
        path = ROOT / "BACE" / relative
        assert sha(path) == expected, f"Scientific freeze mismatch before execution: {relative}"
        paths.add(path)
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths) if p.exists()}


def main():
    start = time.monotonic()
    print("Checking the scientific freeze and protected analysis files.", flush=True)
    before = protected_files()
    environments = {name: environment(python) for name, python in {
        "native": ROOT / "BACE/.venv/bin/python", "analysis": HERE / ".venv/bin/python"}.items()}
    freeze = json.loads((ROOT / "BACE/config/freeze.json").read_text())
    assert environments["native"]["python"] == freeze["environment"]["python"], "Native Python changed"
    assert environments["native"]["packages"] == freeze["environment"]["packages"], "Native packages changed"
    baseline_path = OUT / "qa/protected_baseline.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text())
        assert baseline["files"] == before, "Protected files differ from notebook-04 task baseline"
        assert baseline["environments"] == environments, "Protected environment changed"
    else:
        save_json(baseline_path, {"files": before, "environments": environments})
    kernel = RUNTIME / "jupyter/kernels/bace-evaluator-gap"
    kernel.mkdir(parents=True, exist_ok=True)
    save_json(kernel / "kernel.json", {"argv": [sys.executable, "-B", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "BACE evaluator gap (Python)", "language": "python",
        "env": {"PYTHONDONTWRITEBYTECODE": "1"}})
    path = HERE / "04_evaluator_gap_diagnostics.ipynb"
    notebook = nbformat.read(path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    print("Executing notebook 04 in a fresh kernel.", flush=True)
    try:
        NotebookClient(notebook, timeout=1200, kernel_name="bace-evaluator-gap",
                       resources={"metadata": {"path": str(HERE)}}).execute()
    except Exception:
        nbformat.write(notebook, path)
        raise
    nbformat.write(notebook, path)
    exporter = HTMLExporter()
    exporter.exclude_input = True
    exporter.exclude_input_prompt = True
    html, _ = exporter.from_notebook_node(notebook)
    soup = BeautifulSoup(html, "html.parser")
    # Notebook links are relative to BACE/analysis; reading HTML is two levels deeper.
    for element in soup.find_all(href=True):
        href = element["href"]
        url = urlsplit(href)
        if not url.scheme and url.path and not url.path.startswith("/"):
            target = HERE / unquote(url.path)
            if target.exists():
                element["href"] = os.path.relpath(target, OUT) + ("#" + url.fragment if url.fragment else "")
    html_path = OUT / "04_evaluator_gap_diagnostics.html"
    html_path.write_text(str(soup))
    after = {name: sha(ROOT / name) for name in before}
    assert before == after, "A protected file changed during notebook execution"
    after_env = {name: environment(python) for name, python in {
        "native": ROOT / "BACE/.venv/bin/python", "analysis": HERE / ".venv/bin/python"}.items()}
    assert after_env == environments, "An environment changed during notebook execution"
    report = {"notebook": path.name, "notebook_sha256": sha(path), "html_sha256": sha(html_path),
        "seconds": round(time.monotonic() - start, 2), "code_cells": sum(c.cell_type == "code" for c in notebook.cells),
        "errors": 0, "protected_files_unchanged": len(before), "environments_unchanged": True,
        "scientific_freeze_verified": len(freeze["files"]), "python": sys.executable}
    save_json(OUT / "execution.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
