"""Plot exact category counts in selected positive disagreements, with no inference."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
QA = OUT / "qa"
QA.mkdir(exist_ok=True)
sys.path.insert(0, "/home/muwang/.codex/skills/nature-figure/scripts")
from audit_panel_alignment import require_matplotlib_panel_alignment

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"], "font.size": 8,
    "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "axes.linewidth": 0.6,
})
with (OUT / "category_composition.csv").open() as stream:
    rows = list(csv.DictReader(stream))
categories = [r["category"] for r in rows if r["framework"] == "ragas"]
labels = ["Factual boundary distortion", "Evidence conflation", "Inferential inflation",
          "Unsupported novelty", "Non-disclosure statement", "Contradiction"]
assert len(categories) == len(labels) == 6
fig, ax = plt.subplots(figsize=(7.2047244094, 4.5669291339))  # 183 by 116 mm
fig.subplots_adjust(left=0.345, right=0.98, bottom=0.21, top=0.77)
for f, name, offset, color, hollow in [
    ("ragas", "RAGAS (n = 2,010)", -0.19, "#2878A0", False),
    ("ragchecker", "RAGChecker (n = 500)", 0.19, "#BA6A1D", True),
]:
    subset = [r for r in rows if r["framework"] == f]
    assert [r["category"] for r in subset] == categories
    values = [float(r["positive_composition_percent"]) for r in subset]
    assert abs(sum(values) - 100) < 1e-8
    ys = [i + offset for i in range(6)]
    ax.barh(ys, values, height=0.29, color="none" if hollow else color,
            edgecolor=color, linewidth=0.8, label=name)
    for y, v, row in zip(ys, values, subset):
        ax.text(v + 1.2, y, f'{v:.1f}% ({int(row["positive_disagreements"]):,})',
                ha="left", va="center", fontsize=7.5)
ax.set_yticks(range(6), labels)
ax.set_ylim(5.6, -0.6)
ax.set_xlim(0, 104)
ax.set_xticks([0, 20, 40, 60, 80, 100])
ax.set_xlabel("Share of positive disagreements (%)", labelpad=7)
ax.tick_params(axis="y", length=0, pad=8)
ax.tick_params(axis="x", width=0.6, length=3)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.legend(loc="lower left", bbox_to_anchor=(-0.005, 1.02), frameon=False,
          ncol=2, handlelength=1.7, columnspacing=1.5)
fig.text(0.03, 0.955, "Which BACE diagnoses occur in support disagreements?",
         fontsize=11, weight="bold", va="top")
fig.text(0.03, 0.9, "Positive disagreement: BACE unsupported; comparator supported.",
         fontsize=8.5, va="top")
fig.text(0.03, 0.082, "Selected text matches cover 6.0% (RAGAS) and 1.4% (RAGChecker) of BACE claims.",
         fontsize=7.5)
fig.text(0.03, 0.038, "BACE diagnostic labels; different subsets. These shares are not confirmed error rates.",
         fontsize=7.5)
fig.canvas.draw()
require_matplotlib_panel_alignment(
    fig, json_out=str(QA / "category_composition.alignment.json"),
    overlay_svg=str(QA / "category_composition.alignment.svg"), strict=True)
fig.savefig(OUT / "category_composition.pdf")
fig.savefig(OUT / "category_composition.svg")
fig.savefig(OUT / "category_composition.png", dpi=300)
plt.close(fig)
(QA / "plot_provenance.json").write_text(json.dumps({
    "backend": "Python/Matplotlib", "matplotlib_version": matplotlib.__version__,
    "executable": sys.executable,
    "command": "PYTHONDONTWRITEBYTECODE=1 BACE/analysis/.venv/bin/python paper/analysis/support_gap_composition_2026-10-20/plot_gap_composition.py",
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "source_csv_sha256": hashlib.sha256((OUT / "category_composition.csv").read_bytes()).hexdigest(),
    "output_sha256": {s: hashlib.sha256((OUT / f"category_composition.{s}").read_bytes()).hexdigest()
                       for s in ("pdf", "svg", "png")},
}, indent=2) + "\n")
