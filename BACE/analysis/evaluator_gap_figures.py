"""Python figures and source-linked readings for notebook 04.

Style-only inheritance from the existing analysis palette and typography;
the data transformations and figures are specific to the gap diagnostics.
"""
from pathlib import Path
import os
import subprocess
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from IPython.display import Markdown, SVG, display

from evaluator_gap_analysis import OUT, HERE, sha, save_json

SKILL = Path(os.environ.get("NATURE_FIGURE_SKILL", Path.home() / ".codex/skills/nature-figure"))
sys.path.insert(0, str(SKILL / "scripts"))
from audit_panel_alignment import require_matplotlib_panel_alignment

BLUE, GREEN, ORANGE, GREY, INK = "#7AAED6", "#83C5A3", "#F3B27A", "#B7BDC5", "#283440"
mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 9,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.spines.right": False, "axes.spines.top": False, "axes.linewidth": .65,
    "legend.frameon": False, "svg.fonttype": "none", "pdf.fonttype": 42,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})


def note(text):
    display(Markdown(text))


def canvas(height=95, left=.30, top=.85, bottom=.18):
    width = 183
    fig, ax = plt.subplots(figsize=(width / 25.4, height / 25.4))
    fig.subplots_adjust(left=left, right=.96, top=top, bottom=bottom)
    return fig, ax


def percent_interval(row):
    return f"{100 * row.estimate:.1f}% (95% interval {100 * row.low:.1f}–{100 * row.high:.1f}%)"


def save_figure(fig, name, data, question, caption, pattern, meaning, limits):
    directory = OUT / "figures"
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / name
    source = base.with_name(name + "__data.csv")
    data.to_csv(source, index=False)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig, json_out=str(base) + ".alignment.json",
                                       tolerance_pt=1.5, strict=True)
    fig.savefig(str(base) + ".pdf", dpi=600)
    fig.savefig(str(base) + ".svg", dpi=600)
    fig.savefig(str(base) + ".png", dpi=600)
    audits = {}
    for key, arguments in {
        "text": [str(SKILL / "scripts/audit_pdf_text.py"), str(base) + ".pdf", "--json"],
        "collision": [str(SKILL / "scripts/audit_figure_collisions.py"), str(base) + ".pdf",
                      "--json-out", str(base) + ".collision-audit.json"]}.items():
        result = subprocess.run([sys.executable, *arguments], capture_output=True, text=True)
        audits[key] = result.returncode
        if key == "text":
            Path(str(base) + ".text-audit.json").write_text(result.stdout)
        else:
            Path(str(base) + ".collision-audit.txt").write_text(result.stdout + result.stderr)
    save_json(str(base) + ".metadata.json", {
        "figure": name, "question": question, "caption": caption,
        "archetype": "Quantitative paired-panel diagnostic" if len(fig.axes) > 1 else "Quantitative single-panel diagnostic",
        "width_mm": 183, "height_mm": fig.get_figheight() * 25.4, "png_dpi": 600,
        "data_file": source.name, "data_sha256": sha(source), "audit_exit_codes": audits,
        "exports": {ext: sha(str(base) + "." + ext) for ext in ("pdf", "svg", "png")}})
    save_json(str(base) + ".reading.json", {"question": question, "caption": caption, "pattern": pattern,
        "meaning": meaning, "limits": limits, "source_sha256": sha(source), "plotting_source_sha256": sha(__file__)})
    note(f"**Figure question.** {question}")
    display(SVG(filename=str(base) + ".svg"))
    plt.close(fig)
    relative = base.relative_to(HERE).as_posix()
    links = " · ".join(f"[{ext.upper()}]({relative}.{ext})" for ext in ("pdf", "svg", "png"))
    note(caption + "\n\n" + links + f" · [Source data]({relative}__data.csv)")
    note(f"**Pattern and evidence.** {pattern}\n\n**Interpretation.** {meaning}\n\n**Limits.** {limits}")
    if any(audits.values()):
        raise RuntimeError(f"Figure {name} needs rendered QA repair: {audits}")


def plot_sensitivity(tables):
    frame = tables["score_conditions"]
    fig, ax = canvas(height=97, left=.39)
    labels = ["BACE: all DCs", "BACE: non-disclosure\nexclusion", "BACE: all empty sets\nhypothetically supported",
              "RAGChecker: native", "RAGAS: native"]
    for i, row in enumerate(frame.itertuples()):
        color = [BLUE, BLUE, BLUE, GREEN, ORANGE][i]
        ax.errorbar(100 * row.estimate, i,
                    xerr=[[100 * (row.estimate - row.low)], [100 * (row.high - row.estimate)]],
                    fmt=["o", "s", "D", "^", "v"][i], color=color, capsize=3, markersize=6, elinewidth=1.2)
    ax.set_yticks(range(len(frame)), labels)
    ax.set_ylim(4.65, -.65)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Mean disclosure support score (%)")
    ax.set_title("Specified arithmetic changes leave a large score difference", loc="left", pad=15)
    effects = tables["paired_effects"]
    exclusion = effects.loc[effects.contrast.eq("Non-disclosure exclusion minus all-DC BACE")].iloc[0]
    empty = effects.loc[effects.contrast.eq("All empty sets supported minus all-DC BACE")].iloc[0]
    save_figure(fig, "04_score_sensitivity", frame,
        "Can these two specified arithmetic changes remove the native score gap?",
        "Points are disclosure-macro scores on 1,798 paired cases. Bars are 95% percentile company-cluster intervals "
        "(2,000 draws; seed 20260921). The two sensitivity conditions change only BACE and are not model reruns.",
        f"BACE's native mean is {percent_interval(frame.iloc[0])}. Removing its unsupported non-disclosure statements gives "
        f"{percent_interval(frame.iloc[1])}, a paired increase of {100 * exclusion.estimate:.2f} points. "
        f"Relabelling every zero-candidate DC supported gives {percent_interval(frame.iloc[2])}, an increase of "
        f"{100 * empty.estimate:.2f} points. Native comparator means remain {100 * frame.iloc[3].estimate:.1f}% and "
        f"{100 * frame.iloc[4].estimate:.1f}%.",
        "Neither specified arithmetic condition eliminates the difference. They narrow two simple explanations without "
        "establishing the source of the remaining disagreement.",
        "Non-disclosure exclusion changes the denominator and removes only BACE-unsupported statements with that diagnosis. "
        "The empty-set condition is an extreme bound for that subset alone, not an accuracy correction or a bound for all "
        "upstream losses. The conditions overlap and must not be added. Native target inventories remain different.")


def plot_candidates(tables):
    frame = tables["candidate_count_ecdf"]
    summary = tables["candidate_sets"]
    fig, ax = canvas(height=91, left=.13, top=.84)
    for group, color, style in [("Supported", BLUE, "-"), ("Unsupported", GREY, "--")]:
        rows = frame.loc[frame.group.eq(group)]
        assert (rows.candidate_count >= 0).all()
        ax.step(rows.candidate_count, rows.cumulative_fraction, where="post", label=group,
                color=color, linestyle=style, linewidth=1.6)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xticks([0, 1, 5, 10, 25, 50, 100, 234], ["0", "1", "5", "10", "25", "50", "100", "234"])
    ax.set_xlim(-.05, 250)
    ax.set_ylim(0, 1.03)
    ax.set_xlabel("Candidate ECs per DC (linear near zero; logarithmic above 1)")
    ax.set_ylabel("Cumulative fraction of DCs")
    ax.legend(loc="lower right")
    ax.set_title("Nonempty candidate sets also accompany unsupported judgments", loc="left", pad=14)
    nzero = int(summary.zero_candidates.sum())
    unsupported = int(summary.loc[~summary.label.isin(["direct", "inferred"]), "claims"].sum())
    save_figure(fig, "04_candidate_sets", frame,
        "Does complete candidate absence describe most BACE rejections?",
        "ECDFs use all saved BACE DCs, separated by their saved support labels. Every observation contributes; no thinning "
        "or smoothing is applied. These are finite-cohort distributions without uncertainty bands. The axis retains zero explicitly.",
        f"There are {nzero:,} zero-candidate DCs among {int(summary.claims.sum()):,} DCs, or "
        f"{100 * nzero / unsupported:.2f}% of the {unsupported:,} unsupported DCs. All zero-candidate cases are unsupported "
        "by the pipeline's deterministic rule. Both groups also contain nonempty candidate sets.",
        "Completely empty sets are a limited subset of the rejections. The presence of candidate evidence is not evidence "
        "that the decisive premise was extracted or selected.",
        "Candidate count measures inventory size, not relevance, sufficiency or recall. The labels on the curves are automated "
        "outcomes, not independent reference judgments. Missing qualifiers inside nonempty sets remain unmeasured.")


def plot_inventory(tables):
    frame = tables["inventory_groups"]
    fig, ax = canvas(height=123, left=.43, top=.89, bottom=.12)
    labels = []
    for i, row in enumerate(frame.itertuples()):
        method = "RAGChecker" if row.method == "ragchecker" else "RAGAS"
        labels.append(f"{method} · {row.group}\n(n = {row.disclosures:,})")
        ax.errorbar(100 * row.estimate, i,
                    xerr=[[100 * (row.estimate - row.low)], [100 * (row.high - row.estimate)]],
                    fmt="o" if row.method == "ragchecker" else "s", color=GREEN if row.method == "ragchecker" else ORANGE,
                    markersize=5, capsize=3, elinewidth=1.2)
    ax.set_yticks(range(len(frame)), labels)
    ax.set_ylim(7.65, -.65)
    ax.set_xlim(-50, 0)
    ax.set_xlabel("BACE minus comparator (percentage points)")
    ax.set_title("A larger claim count is not required for a lower score", loc="left", pad=14)
    groups = frame.loc[frame.group.eq("BACE count no greater")]
    save_figure(fig, "04_inventory_groups", frame,
        "Does the score difference disappear when BACE extracts no more claims than the comparator?",
        "Points show disclosure-macro paired differences within each named count-defined subset. Bars use the same "
        "company-cluster bootstrap as the main sensitivity analysis. Equal-count cases are nested within the no-greater subset; "
        "these rows are not mutually exclusive samples.",
        f"When BACE has no more claims, its score remains {abs(100 * groups.iloc[0].estimate):.2f} points lower than RAGChecker "
        f"in {int(groups.iloc[0].disclosures)} cases and {abs(100 * groups.iloc[1].estimate):.2f} points lower than RAGAS "
        f"in {int(groups.iloc[1].disclosures)} cases. Exactly equal counts also retain negative mean differences.",
        "More BACE claims are not necessary for the observed direction of the gap. Counting claims alone is insufficient "
        "to explain the comparison.",
        "Equal counts do not mean equal propositions. These outcome-defined subsets are selected, and their intervals do "
        "not identify a causal effect of claim splitting or omission. All comparisons remain native judgments.")


def plot_literal(tables):
    frame = tables["literal_joint_counts"]
    matrix = frame.pairs.to_numpy().reshape(2, 2)
    fig, ax = canvas(height=91, left=.25, top=.78, bottom=.18)
    cmap = LinearSegmentedColormap.from_list("gap_counts", ["#F2F5F8", BLUE])
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=matrix.max(), aspect="auto", interpolation="nearest")
    for (row, col), count in np.ndenumerate(matrix):
        ax.text(col, row, f"{count:,}", ha="center", va="center", fontsize=12, color=INK)
    ax.set_xticks([0, 1], ["Supported", "Unsupported"])
    ax.set_yticks([0, 1], ["Supported", "Unsupported"])
    ax.set_xlabel("RAGAS judgment")
    ax.set_ylabel("BACE judgment")
    ax.set_title("Identical target wording still leaves asymmetric disagreement", loc="left", pad=16)
    for spine in ax.spines.values():
        spine.set_visible(False)
    estimates = tables["literal_pooled_estimates"]
    a, b, delta = estimates.iloc[0], estimates.iloc[1], estimates.iloc[2]
    save_figure(fig, "04_literal_pairs", frame,
        "What happens when both methods extracted the same target wording?",
        "Cells count unique case-specific literal matches after casefolding and whitespace normalization. The axes are "
        "two automated judgments, not prediction and ground truth. Counts are exact for this subset; uncertainty for its "
        "pooled rates and paired difference is reported in the accompanying table.",
        f"The {int(matrix.sum()):,} pairs contain {int(matrix[1, 0]):,} BACE-unsupported/RAGAS-supported decisions and "
        f"{int(matrix[0, 1]):,} opposite decisions. Pooled support is {percent_interval(a)} for BACE and "
        f"{percent_interval(b)} for RAGAS. Their paired pooled difference is {100 * delta.estimate:.2f} points "
        f"(95% interval {100 * delta.low:.2f} to {100 * delta.high:.2f}).",
        "Different target wording cannot account for these specific paired verdicts. Evidence representation, the context "
        "accompanying that wording, and judgment procedures remain different.",
        "Only about 6% of BACE DCs have these literal partners, so neither the support levels nor disagreement proportions "
        "represent all claims. RAGChecker's absence of literal matches is a representation issue, not absence of semantic "
        "overlap. No accuracy or independent mechanism label is established.")
