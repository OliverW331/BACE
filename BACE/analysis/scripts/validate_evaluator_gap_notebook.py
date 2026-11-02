"""Check notebook 04 statistics, execution, exports and artifact boundaries."""
from pathlib import Path
import json
import os
import subprocess
import sys
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "outputs/evaluator_gap"
os.environ["MPLCONFIGDIR"] = str(OUT / ".runtime/matplotlib")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import nbformat
import numpy as np
import pandas as pd
from PIL import Image
from bs4 import BeautifulSoup
from evaluator_gap_analysis import ROOT, ClusterBootstrap, sha, save_json, load_inputs, compute_statistics


def main():
    path = HERE / "04_evaluator_gap_diagnostics.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    assert [c.execution_count for c in cells] == list(range(1, len(cells) + 1))
    assert not any(o.output_type == "error" for c in cells for o in c.outputs)
    saved_figures = sum("image/svg+xml" in o.get("data", {}) for c in cells for o in c.outputs)
    prompt_readiness = json.loads((OUT / 'prompt_sensitivity/readiness.json').read_text())
    expected_figures = 6 if prompt_readiness['ready'] else 4
    assert saved_figures == expected_figures
    execution = json.loads((OUT / "execution.json").read_text())
    assert execution["notebook_sha256"] == sha(path)
    assert execution["errors"] == 0 and execution["environments_unchanged"]
    baseline = json.loads((OUT / "qa/protected_baseline.json").read_text())
    for name, digest in baseline["files"].items():
        assert sha(ROOT / name) == digest, name

    # Meaningful estimand checks: unbalanced clusters, paired shifts and zero-denominator resamples.
    fixture = pd.DataFrame({"company_id": ["a"] * 9 + ["b"], "value": [1.] * 9 + [0.]})
    boot = ClusterBootstrap(fixture.company_id, draws=1000)
    unbalanced = boot.mean(fixture, "value")
    assert unbalanced["estimate"] == .9 and unbalanced["low"] == 0 and unbalanced["high"] == 1
    paired = boot.mean(fixture.assign(delta=.25), "delta")
    assert paired["estimate"] == paired["low"] == paired["high"] == .25
    subgroup = boot.mean(fixture.loc[fixture.company_id.eq("a")], "value")
    assert subgroup["undefined_draws"] > 0 and subgroup["low"] == subgroup["high"] == 1

    # Independently check point estimates and reproduce all new numerical tables.
    before = {p.name: sha(p) for p in (OUT / "tables").glob("*.csv")}
    data = load_inputs()
    tables = compute_statistics(data)
    assert before == {p.name: sha(p) for p in (OUT / "tables").glob("*.csv")}
    saved = pd.read_csv(HERE / "outputs/figures/03/03_native_comparison__cohort_summary.csv")
    scores = tables["score_conditions"].set_index("condition")
    for method, condition in [("BACE", "BACE: all DCs"), ("RAGChecker", "RAGChecker: native"), ("RAGAS", "RAGAS: native")]:
        row = saved.loc[(saved.method == method) & (saved.cohort == "Common")].iloc[0]
        assert np.allclose(scores.loc[condition, ["estimate", "low", "high"]].astype(float), row[["mean", "low", "high"]].astype(float), atol=1e-12)
    pair_values = data["pairs"].bace_supported.astype(int) - data["pairs"].external_supported.astype(int)
    pooled = tables["literal_pooled_estimates"].set_index("quantity")
    assert np.isclose(pooled.loc["BACE minus RAGAS", "estimate"], pair_values.mean())
    assert tables["literal_joint_counts"].pairs.sum() == len(data["pairs"])
    assert tables["candidate_sets"].claims.sum() == len(data["claims"])
    for frame in [tables[n] for n in ("score_conditions", "paired_effects", "inventory_groups", "literal_pooled_estimates", "literal_case_estimates")]:
        assert frame.undefined_draws.eq(0).all()
        assert np.isfinite(frame[["estimate", "low", "high"]].to_numpy()).all()

    skill = Path(os.environ.get("NATURE_FIGURE_SKILL", Path.home() / ".codex/skills/nature-figure"))
    audit = subprocess.run([sys.executable, str(skill / "scripts/validate_figure.py"),
                            str(HERE / "evaluator_gap_figures.py"), "--json"], capture_output=True, text=True)
    static = json.loads(audit.stdout)
    save_json(OUT / "qa/plotting_source_audit.json", static)
    assert not [r for r in static["findings"] if r["level"] == "FAIL"]
    # The additional renderer delegates fonts, exports and panel alignment to
    # the shared helper. Audit both sources together so static checks see the
    # actual imported implementation instead of treating the helper as absent.
    bundle = OUT / 'qa/prompt_plotting_source_bundle.py'
    plotting_sources = [HERE / 'evaluator_gap_figures.py', HERE / 'evaluator_gap_prompt_figures.py']
    bundle.write_text('\n\n'.join('# Static audit source: ' + str(p) + '\n' + p.read_text()
                                 for p in plotting_sources))
    prompt_audit = subprocess.run([sys.executable, str(skill / 'scripts/validate_figure.py'),
                                  str(bundle), '--json'], capture_output=True, text=True)
    prompt_static = json.loads(prompt_audit.stdout)
    prompt_static['composed_source_files'] = {str(p.relative_to(ROOT)):sha(p) for p in plotting_sources}
    save_json(OUT / 'qa/prompt_plotting_source_audit.json', prompt_static)
    assert not [r for r in prompt_static['findings'] if r['level'] == 'FAIL']
    if prompt_readiness['ready']:
        subprocess.run([sys.executable, str(HERE / 'scripts/validate_evaluator_gap_prompt_results.py')], check=True)
    figure_checks = []
    for meta_path in sorted((OUT / "figures").glob("*.metadata.json")):
        meta = json.loads(meta_path.read_text())
        base = meta_path.with_name(meta["figure"])
        assert not any(meta["audit_exit_codes"].values()), meta["figure"]
        assert abs(meta["width_mm"] - 183) < 1e-8
        for ext, digest in meta["exports"].items():
            assert sha(str(base) + "." + ext) == digest
        assert sha(base.parent / meta["data_file"]) == meta["data_sha256"]
        with Image.open(str(base) + ".png") as raster:
            assert all(abs(dpi - 600) < .1 for dpi in raster.info["dpi"])
            assert abs(raster.width - 183 / 25.4 * 600) < 2
        assert "<text" in Path(str(base) + ".svg").read_text()
        text = json.loads(Path(str(base) + ".text-audit.json").read_text())
        collision = json.loads(Path(str(base) + ".collision-audit.json").read_text())
        alignment = json.loads(Path(str(base) + ".alignment.json").read_text())
        assert text["auditable"] and text["below_minimum_count"] == 0
        assert collision["auditable"] and collision["summary"]["fail"] == 0
        assert alignment["summary"]["fail"] == 0
        reading = json.loads(Path(str(base) + ".reading.json").read_text())
        assert reading["source_sha256"] == meta["data_sha256"]
        assert all(reading[k] for k in ("question", "caption", "pattern", "meaning", "limits"))
        figure_checks.append({"figure": meta["figure"], "minimum_font_pt": text["minimum_found_pt"],
                              "collision_warnings": collision["summary"]["warn"], "alignment": alignment["verdict"]})
    assert len(figure_checks) == saved_figures
    html_path = OUT / "04_evaluator_gap_diagnostics.html"
    assert sha(html_path) == execution["html_sha256"]
    soup = BeautifulSoup(html_path.read_text(), "html.parser")
    assert not soup.select(".jp-CodeCell .jp-InputArea"), "Reading HTML must hide code inputs"
    for element in soup.find_all(href=True):
        url = urlsplit(element["href"])
        if not url.scheme and url.path and not url.path.startswith("/"):
            assert (OUT / unquote(url.path)).exists(), element["href"]
    assert soup.get_text().count("COMPUTATION_PENDING") >= 3
    for path in (OUT / "review_templates").glob("*.csv"):
        assert len(pd.read_csv(path)) == 0, "Delivered templates must not contain invented annotations"
    save_json(OUT / "qa/acceptance.json", {"status": "PASS", "code_cells": len(cells),
        "prompt_sensitivity_ready": prompt_readiness['ready'],
        "figures": figure_checks, "numerical_reproduction": "Byte-identical source tables",
        "bootstrap_checks": ["Disclosure-weighted unbalanced clusters", "Paired constant shift", "Explicit undefined subgroup resamples"],
        "prior_native_intervals_reproduced": True, "protected_files_unchanged": len(baseline["files"]),
        "source_warnings": [r for r in static["findings"] if r["level"] == "WARN"],
        "limits": "Automated validation does not replace panel-by-panel visual and scientific review."})
    print(f"PASS: {len(cells)} executed cells, {saved_figures} figure bundles, numerical repetition and protected-file checks.")
    subprocess.run([sys.executable,str(HERE/'scripts/refresh_evaluator_gap_manifest.py')],check=True)


if __name__ == "__main__":
    main()
