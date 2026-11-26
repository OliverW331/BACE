"""Fig. 1 | The BACE framework, drawn as a vector schematic with a worked example.

Icons: Lucide (lucide-static 0.460.0, ISC licence; copies in ./icons), embedded as vector paths.
Panel b text is read verbatim from the saved outputs of one evaluated case and
checked against the snapshot tables. Output: SVG, PDF (Inkscape) and PNG.

    BACE/.venv/bin/python -B BACE/analysis/figures_v3/fig1_svg.py
"""
import json
import re
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ICONS = HERE / "icons"
CASES = ROOT / "BACE/results/main_v1/cases"
SNAP = ROOT / "BACE/analysis/outputs/snapshot"
OUT = ROOT / "BACE/analysis/outputs/figures_v3"
(OUT / "fig1_data").mkdir(parents=True, exist_ok=True)

CASE = "w2__text_embedding_3_large__stratified_by_evidence_type_n10__grafton_group__2021__s1_1_workforce_policies"
DC_FBD = "dc_fa569dae663e38ff5cd6abccf8599b0a"
DC_INF = "dc_9edd319450f90c02cea311c3dbdbe57b"

# ---------------------------------------------------------------- example data (verbatim)
def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]

d = CASES / CASE
dcs = {r["dc_id"]: r for r in jl(d / "bace/dedup/dc_claims.jsonl")}
ecs = {r["ec_id"]: r for r in jl(d / "bace/dedup/ec_claims.jsonl")}
sup = {r["dc_claim_id"]: r["support_sets"] for r in jl(d / "bace/support/dc_support_sets.jsonl")}
dia = {r["dc_claim_id"]: r for r in jl(d / "bace/diagnosis/dc_unsupported_diagnoses.jsonl")}
cand = {r["dc_claim_id"]: r["candidate_ec_ids"] for r in jl(d / "bace/candidates/dc_candidate_ecs.jsonl")}
gen = jl(d / "generation/generated_disclosures.jsonl")[0]
text = next(v for v in gen.values() if isinstance(v, str) and dcs[DC_FBD]["dc_provenance"][0]["source_spans"][0]["quote"] in v)
sp = dcs[DC_FBD]["dc_provenance"][0]["source_spans"][0]
s0 = text.rfind(".", 0, sp["start"]) + 1
sentence = text[s0:text.find(".", sp["end"] - 1) + 1].strip()
claims = pd.read_csv(SNAP / "claims.csv").query("generation_case_id == @CASE").set_index("dc_id")
assert claims.loc[DC_FBD, "label"] == "factual_boundary_distortion" and claims.loc[DC_INF, "label"] == "inferred"
assert sup[DC_FBD] == [] and all(s["support_type"] == "inferred" and len(s["ec_claim_ids"]) == 2 for s in sup[DC_INF])
set_ecs = sorted({e for s in sup[DC_INF] for e in s["ec_claim_ids"]})
assert set(cand[DC_FBD]) <= set(set_ecs) and len(set_ecs) == 4 and len(sup[DC_INF]) == 4
met = pd.read_csv(SNAP / "metrics.csv").set_index("generation_case_id").loc[CASE]
ex = {
    "case": CASE, "company": gen["company_name"], "target_year": gen["target_reporting_year"],
    "task": gen["task_title"], "sentence": sentence,
    "ecs": [{"ec_id": e, "text": ecs[e]["ec_text"], "card": ecs[e]["evidence_card_ids"][0],
             "candidate_for_fbd_dc": e in cand[DC_FBD]} for e in set_ecs],
    "dc_fbd": {"dc_id": DC_FBD, "text": dcs[DC_FBD]["dc_text"], "rationale": dia[DC_FBD]["rationale"]},
    "dc_inf": {"dc_id": DC_INF, "text": dcs[DC_INF]["dc_text"], "support_sets": sup[DC_INF]},
    "disclosure": {k: (float(met[k]) if not isinstance(met[k], str) else met[k]) for k in
                   ["bace_dc_count", "bace_supported_direct", "bace_supported_inferred", "bace_support_rate_all_dc",
                    "bace_ec_count", "bace_used_ec_count", "bace_eccr", "ragchecker_faithfulness", "ragas_faithfulness"]},
}
(OUT / "fig1_data/b_example_case.json").write_text(json.dumps(ex, indent=1, ensure_ascii=False))
# order ECs: 2018 before 2019, "adheres" before "recognised"
ex["ecs"].sort(key=lambda e: (e["card"].split("::")[3], "recognised" in e["text"]))

# ---------------------------------------------------------------- drawing primitives (1 unit = 0.1 mm)
import math
from decimal import Decimal, ROUND_HALF_UP
from PIL import ImageFont

W, H = 1830, 1290
FONT = "Liberation Sans, Arial, Helvetica, sans-serif"
INK, INK2, MUTED, LINE = "#1f1f1e", "#52514e", "#8a8984", "#bdbbb4"
EC, DC, DIRECT, INFERRED, DIAG = "#00A087", "#3C5488", "#3C5488", "#8491B4", "#E64B35"   # NPG scheme (COLOURS.md)
BROWN, NAVY, GREEN = "#52514e", "#3C5488", "#3C5488"   # drafting system neutral; both BACE modules navy
PT = 0.3528 * 10                              # units per point
FONTS = {(w, st): ImageFont.truetype(f"/usr/share/fonts/truetype/LiberationSans-{n}.ttf", 1000)
         for (w, st), n in {("normal", "normal"): "Regular", ("bold", "normal"): "Bold",
                            ("normal", "italic"): "Italic"}.items()}
el = []


def r1(x):
    return str(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def width(s, size, weight="normal", style="normal"):
    return FONTS[(weight, style)].getlength(s) / 1000 * size * PT


def icon(name, x, y, size, colour, sw=2.0):
    raw = (ICONS / f"{name}.svg").read_text()
    inner = raw[raw.index(">", raw.index("<svg")) + 1:raw.rindex("</svg>")]
    el.append(f'<g transform="translate({x:.1f},{y:.1f}) scale({size / 24:.4f})" fill="none" stroke="{colour}" '
              f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{inner}</g>')


def rect(x, y, w, h, fill="white", stroke=LINE, sw=1.2, rx=14, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
              f'stroke-width="{sw}"{da}/>')


def t(x, y, s, size=6, colour=INK, weight="normal", anchor="start", style="normal", maxw=None):
    if maxw is not None:
        assert width(s, size, weight, style) <= maxw + 0.5, (s, width(s, size, weight, style), maxw)
    el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size * PT:.2f}" fill="{colour}" '
              f'font-weight="{weight}" font-style="{style}" text-anchor="{anchor}">{escape(s)}</text>')


def para(x, y, s, maxw, size=6, colour=INK, lead=1.3, weight="normal", style="normal", anchor="start"):
    out, cur = [], ""
    for w in s.split():
        if cur and width(cur + " " + w, size, weight, style) > maxw:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    out.append(cur)
    for i, ln in enumerate(out):
        t(x, y + i * size * PT * lead, ln, size, colour, weight, anchor, style)
    return y + (len(out) - 1) * size * PT * lead


def arrow(x1, y1, x2, y2, colour=INK2, sw=2.2, head=9):
    a = math.atan2(y2 - y1, x2 - x1)
    xe, ye = x2 - head * 0.8 * math.cos(a), y2 - head * 0.8 * math.sin(a)
    el.append(f'<line x1="{x1}" y1="{y1}" x2="{xe:.1f}" y2="{ye:.1f}" stroke="{colour}" stroke-width="{sw}"/>')
    p1 = (x2 - head * math.cos(a - 0.45), y2 - head * math.sin(a - 0.45))
    p2 = (x2 - head * math.cos(a + 0.45), y2 - head * math.sin(a + 0.45))
    el.append(f'<polygon points="{x2},{y2} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" fill="{colour}"/>')


def curve(x1, y1, x2, y2, colour, sw=2, dash=None, head=False):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    xe = x2 - (8 if head else 0)
    el.append(f'<path d="M{x1},{y1} C{(x1 + xe) / 2},{y1} {(x1 + xe) / 2},{y2} {xe},{y2}" fill="none" '
              f'stroke="{colour}" stroke-width="{sw}"{da}/>')
    if head:
        arrow(xe - 1, y2, x2, y2, colour, sw)


def chip(x, y, label, colour, size=5.6, maxw=None):
    el.append(f'<rect x="{x}" y="{y - 13}" width="13" height="13" rx="2" fill="{colour}"/>')
    t(x + 19, y, label, size, INK, "bold", maxw=maxw)


def module(x, y, w, h, title, fill, accent):
    rect(x, y, w, h, fill=fill, stroke="none", rx=26)
    t(x + w / 2, y + 36, title, 6.6, accent, "bold", "middle", maxw=w - 30)


def item(cx, y, name, colour, label, sub, colw, isize=56):
    """Icon centred at cx with a bold label and grey sub-lines below."""
    icon(name, cx - isize / 2, y, isize, colour)
    yy = y + isize + 26
    for ln in label:
        t(cx, yy, ln, 6, INK, "bold", "middle", maxw=colw); yy += 22
    for ln in sub:
        t(cx, yy, ln, 5.4, INK2, anchor="middle", maxw=colw); yy += 20
    return yy


# ---------------------------------------------------------------- a: pipeline
t(0, 30, "a", 8, INK, "bold")
# module 1: the evaluated drafting system (two columns)
module(20, 44, 470, 486, "Retrieval-augmented drafting", "#efede8", BROWN)
L, R = 140, 372
item(L, 92, "file-text", BROWN, ["Company reports", "and metrics"], ["metrics: t−4 to t", "PDFs: t−4 to t−1"], 210)
arrow(L, 298, L, 330, BROWN)
item(L, 356, "search", BROWN, ["Hybrid retrieval"], ["BM25 and dense,", "rank fusion"], 210)
item(R, 92, "file-pen-line", BROWN, ["Simulated disclosure"], ["target reporting year t"], 220, 48)
arrow(R, 254, R, 222, BROWN)
item(R, 260, "sparkles", BROWN, ["LLM generator"], [], 210, 48)
arrow(R, 384, R, 348, BROWN)
item(R, 390, "layers", BROWN, ["Retrieved evidence"], ["up to 10 cards per type"], 220, 48)
arrow(L + 36, 412, R - 36, 414, BROWN)

# module 2: atomic claim construction
module(545, 44, 380, 486, "Atomic claim construction", "#eceef5", NAVY)
for (y0, lab, sub, col) in [(96, "Disclosure claims (DCs)", "from the disclosure", DC),
                            (356, "Evidence claims (ECs)", "from the retrieved evidence", EC)]:
    rect(568, y0, 334, 110, fill="white", stroke=col, sw=1.6)
    icon("list", 584, y0 + 30, 50, col)
    t(648, y0 + 48, lab, 6, col, "bold", maxw=245); t(648, y0 + 74, sub, 5.4, INK2, maxw=245)
para(735, 256, "Extraction, patch review, atomicity review and deduplication; each claim keeps its period, "
     "entity, scope and metric definition", 330, 5.3, INK2, anchor="middle")
arrow(428, 116, 568, 116, INK2)                    # simulated disclosure -> DCs
arrow(428, 414, 568, 414, INK2)                    # retrieved evidence -> ECs

# module 3: support assessment
module(980, 44, 380, 486, "Support assessment", "#e1e5ef", GREEN)
rect(1003, 96, 334, 120, fill="white", stroke="#b3bbd3", sw=1.6)
icon("filter", 1019, 128, 50, GREEN)
t(1083, 148, "Candidate selection", 6, INK, "bold", maxw=245)
para(1083, 174, "materially relevant ECs for each DC", 245, 5.4, INK2)
arrow(1170, 218, 1170, 252, GREEN)
rect(1003, 254, 334, 252, fill="white", stroke="#b3bbd3", sw=1.6)
icon("link", 1019, 290, 50, GREEN)
para(1083, 310, "Every minimal sufficient support set", 245, 6, INK, weight="bold")
para(1083, 362, "ECs that jointly establish the complete DC", 245, 5.4, INK2)
chip(1083, 466, "direct", DIRECT, 5.5); chip(1190, 466, "inferred", INFERRED, 5.5)
curve(902, 151, 1003, 156, INK2, 2.2, head=True)
curve(902, 411, 1003, 156, INK2, 2.2)

# outputs
outs = [("list-checks", DC, "Disclosure support rate", ["share of DCs with an accepted set"]),
        ("list-checks", EC, "Evidence Claim Coverage Ratio", ["share of ECs in any accepted set"]),
        ("triangle-alert", DIAG, "Primary diagnosis", ["for each unsupported DC,", "from six ordered rules"])]
for i, (nm, col, l1, l2) in enumerate(outs):
    y0 = 84 + i * 128
    icon(nm, 1410, y0 + 6, 54, col)
    t(1480, y0 + 30, l1, 6.1, INK, "bold", maxw=338)
    for j, ln in enumerate(l2):
        t(1480, y0 + 58 + j * 25, ln, 5.4, INK2, maxw=335)
    arrow(1360, 290, 1402, y0 + 34, INK2, 2.2)
# comparator note
rect(1405, 456, 415, 74, fill="white", stroke=LINE, sw=1.4, rx=37, dash="8,6")
icon("git-compare-arrows", 1424, 475, 36, MUTED)
t(1474, 488, "Comparators: RAGChecker and RAGAS,", 5.2, INK2, maxw=335)
t(1474, 512, "same inputs, their own claims and scores", 5.2, INK2, maxw=335)

# ---------------------------------------------------------------- b: worked example
Y = 575
t(0, Y + 8, "b", 8, INK, "bold")
rect(20, Y, 1800, 705, fill="white", stroke="#9a9893", sw=1.6, rx=22, dash="10,7")
t(50, Y + 52, f"Example · {ex['company']}, {ex['target_year']} · {ex['task']}", 7, INK, "bold")
t(50, Y + 96, "Evidence claims (ECs) from the supplied annual reports", 5.8, EC, "bold")
ec_y = []
for i, e in enumerate(ex["ecs"]):
    y0 = Y + 112 + i * 106 + (14 if i >= 2 else 0)
    rect(50, y0, 640, 92, fill="#e6f4f1", stroke="none", rx=10)
    t(68, y0 + 33, f"EC{i + 1}", 5.6, EC, "bold")
    para(130, y0 + 33, e["text"], 545, 5.5, INK)
    ec_y.append(y0 + 46)
# disclosure side
X2 = 1050
t(X2, Y + 96, f"Generated sentence ({ex['target_year']} disclosure)", 5.8, INK2, "bold")
rect(X2, Y + 112, 740, 92, fill="#f4f3ef", stroke="none", rx=10)
para(X2 + 18, Y + 146, "“" + ex["sentence"] + "”", 700, 5.6, INK, style="italic")
t(X2, Y + 246, "Disclosure claims (DCs) and BACE verdicts", 5.8, DC, "bold")
y1 = Y + 262
rect(X2, y1, 740, 162, fill="white", stroke=DIAG, sw=1.8, rx=10)
chip(X2 + 18, y1 + 32, "Unsupported · factual boundary distortion", DIAG)
para(X2 + 18, y1 + 62, "“" + ex["dc_fbd"]["text"] + "”", 705, 5.6, INK)
para(X2 + 18, y1 + 94, "Rationale: " + ex["dc_fbd"]["rationale"], 705, 5.3, INK2, style="italic")
y2 = Y + 444
rect(X2, y2, 740, 150, fill="white", stroke=DC, sw=1.8, rx=10)
chip(X2 + 18, y2 + 32, "Inferred support", INFERRED)
para(X2 + 18, y2 + 62, "“" + ex["dc_inf"]["text"] + "”", 705, 5.6, INK)
para(X2 + 18, y2 + 116, "Four minimal sufficient support sets: {EC1 or EC3} with {EC2 or EC4}", 705, 5.3, INK2)
# connectors (inferred support-set membership; candidate without support)
for e, y in zip(ex["ecs"], ec_y):
    curve(690, y, X2, y2 + 75, INFERRED, 3)
    if e["candidate_for_fbd_dc"]:
        curve(690, y, X2, y1 + 81, DIAG, 2.2, "7,6")
# connector legend
yl = Y + 590
el.append(f'<line x1="60" y1="{yl}" x2="110" y2="{yl}" stroke="{INFERRED}" stroke-width="3"/>')
t(122, yl + 7, "member of an accepted support set", 5.3, INK2)
el.append(f'<line x1="480" y1="{yl}" x2="530" y2="{yl}" stroke="{DIAG}" stroke-width="2.2" stroke-dasharray="7,6"/>')
t(542, yl + 7, "candidate EC, no accepted support set", 5.3, INK2)
# disclosure-level outcome strip
q = ex["disclosure"]
yb = Y + 618
rect(50, yb, 1740, 62, fill="#f4f3ef", stroke="none", rx=10)
icon("list-checks", 66, yb + 13, 36, INK2)
summary = (f"Whole disclosure:  Sd {r1(100 * q['bace_support_rate_all_dc'])}% "
           f"({int(q['bace_supported_direct'] + q['bace_supported_inferred'])} of {int(q['bace_dc_count'])} DCs)   ·   "
           f"ECCR {r1(100 * q['bace_eccr'])}% ({int(q['bace_used_ec_count'])} of {int(q['bace_ec_count'])} ECs)   ·   "
           f"RAGChecker {r1(100 * q['ragchecker_faithfulness'])}%   ·   RAGAS {r1(100 * q['ragas_faithfulness'])}%")
t(118, yb + 39, summary, 5.8, INK, "bold", maxw=1650)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" height="{H / 10}mm" viewBox="0 0 {W} {H}">'
       f'<rect width="{W}" height="{H}" fill="white"/>' + "".join(el) + "</svg>")
svg = re.sub(r"Sd (\d)", r'S<tspan baseline-shift="sub" font-size="70%">d</tspan> \1', svg)
(OUT / "fig1.svg").write_text(svg)
for typ, extra in [("pdf", []), ("png", ["--export-dpi=300"])]:
    subprocess.run(["inkscape", str(OUT / "fig1.svg"), f"--export-type={typ}", *extra,
                    f"--export-filename={OUT / ('fig1.' + typ)}"], check=True, capture_output=True)
print("written fig1.svg/pdf/png")
