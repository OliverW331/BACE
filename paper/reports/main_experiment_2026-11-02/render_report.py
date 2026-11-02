"""Render the verified English Markdown report and result figures as a PDF."""

import hashlib
import html
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent
FIGURES = OUT / "figures"
FIGURES.mkdir(exist_ok=True)
LEDGER = json.loads((OUT / "numeric_ledger.json").read_text())
BLUE = "#487CA0"
GREEN = "#4F9472"
ORANGE = "#C27F42"
GREY = "#4D5863"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "savefig.facecolor": "white"})


def workflow():
    figure, axis = plt.subplots(figsize=(10.8, 6.1))
    axis.set_xlim(0, 10.8)
    axis.set_ylim(0, 6.1)
    axis.axis("off")
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    def box(left, bottom, width, height, title, detail, fill="#EEF4F8"):
        axis.add_patch(FancyBboxPatch((left, bottom), width, height, boxstyle="round,pad=0.08,rounding_size=0.07", facecolor=fill, edgecolor="#B8C7D1", linewidth=1))
        axis.text(left + width / 2, bottom + height * 0.70, title, ha="center", va="center", weight="bold", fontsize=10, color="#223A4A")
        axis.text(left + width / 2, bottom + height * 0.30, detail, ha="center", va="center", fontsize=9, color=GREY)

    def arrow(start, finish):
        axis.add_patch(FancyArrowPatch(start, finish, arrowstyle="-|>", mutation_scale=12, color="#677C8C", linewidth=1.25))

    box(0.15, 4.9, 3.0, 0.9, "SOURCE-ELIGIBLE SAMPLE", "600 registered -> 250 eligible -> 30 selected")
    box(3.8, 4.9, 3.0, 0.9, "CANONICAL EVIDENCE", "CSV metrics + PDF narrative + table rows")
    box(7.45, 4.9, 3.0, 0.9, "FROZEN CASE INPUTS", "Company/year filters + hybrid RRF\nUp to 10 cards per evidence type")
    arrow((3.23, 5.35), (3.70, 5.35))
    arrow((6.88, 5.35), (7.35, 5.35))
    box(3.45, 3.42, 3.8, 0.98, "DISCLOSURE GENERATION", "One 300-500-word section per case\nFirst complete length-valid response")
    arrow((8.95, 4.82), (7.1, 4.0))
    box(0.35, 1.68, 3.5, 1.10, "BACE", "Extract -> review -> atomicity -> dedup\nCandidate ECs -> minimal support sets\nDirect / inferred / unsupported + diagnosis", "#EEF5F1")
    box(4.12, 1.68, 2.8, 1.10, "RAGCHECKER", "Native claim extraction\nPer-card entailment checks\nNative faithfulness", "#F8F2EC")
    box(7.22, 1.68, 2.8, 1.10, "RAGAS", "Native statement extraction\nCombined-context checks\nNative faithfulness", "#F8F2EC")
    for endpoint in [(2.1, 2.86), (5.52, 2.86), (8.62, 2.86)]:
        arrow((5.35, 3.34), endpoint)
    axis.text(5.45, 3.05, "Same accepted disclosure and exact prompt-visible evidence", ha="center", fontsize=9, color=GREY, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
    box(3.08, 0.13, 4.55, 0.85, "MATCHED DESCRIPTIVE ANALYSIS", "1,798 complete disclosures; company-cluster intervals", "#F0F0F3")
    for start in [(2.1, 1.6), (5.52, 1.6), (8.62, 1.6)]:
        arrow(start, (5.35, 1.06))
    figure.tight_layout(pad=0.1)
    for extension in ["png", "pdf", "svg"]:
        figure.savefig(FIGURES / f"workflow.{extension}", dpi=220, bbox_inches="tight")
    plt.close(figure)


def main_results():
    figure, axes = plt.subplots(1, 2, figsize=(10.7, 5.0), gridspec_kw={"width_ratios": [1, 1.55]})
    methods = LEDGER["methods"]
    positions = range(len(methods))
    axes[0].barh(list(positions), [record["mean"] * 100 for record in methods], color=[BLUE, ORANGE, GREEN], height=0.5)
    axes[0].errorbar([record["mean"] * 100 for record in methods], list(positions), xerr=[[100 * (record["mean"] - record["low"]) for record in methods], [100 * (record["high"] - record["mean"]) for record in methods]], fmt="none", color="#28343D", capsize=4)
    for position, record in enumerate(methods):
        axes[0].text(2, position, f"{record['mean'] * 100:.1f}%", color="white", va="center", weight="bold")
    axes[0].set_yticks(list(positions), [record["method"] for record in methods])
    axes[0].invert_yaxis()
    axes[0].set_xlim(0, 100)
    axes[0].set_xlabel("Mean native rate (%)")
    axes[0].set_title("A  Same disclosures, different native metrics", loc="left", fontsize=10, pad=17)
    axes[0].spines["left"].set_visible(False)
    diagnoses = LEDGER["diagnoses"]
    label_text = {"Factual boundary distortion": "Boundary distortion", "Non-disclosure statement": "Non-disclosure", "Inferential inflation": "Inferential inflation"}
    axes[1].barh(list(range(len(diagnoses))), [record["share"] * 100 for record in diagnoses], color=[BLUE, GREEN, ORANGE, "#889CAA", "#B7C5CD", "#D9DFE3"], height=0.64)
    for position, record in enumerate(diagnoses):
        axes[1].text(record["share"] * 100 + 0.7, position, f"{record['share'] * 100:.1f}%", va="center", fontsize=9)
    axes[1].set_yticks(list(range(len(diagnoses))), [label_text.get(record["name"], record["name"]) for record in diagnoses], fontsize=9)
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, 53)
    axes[1].set_xlabel("Share of unsupported BACE DCs (%)")
    axes[1].set_title("B  Automated unsupported diagnoses", loc="left", fontsize=10, pad=17)
    axes[1].spines["left"].set_visible(False)
    figure.subplots_adjust(left=0.10, right=0.99, top=0.88, bottom=0.16, wspace=0.86)
    figure.text(0.5, 0.025, "Native scores and diagnoses are not independent estimates of factual truth or evaluator accuracy.", ha="center", color=GREY, fontsize=8.5)
    for extension in ["png", "pdf", "svg"]:
        figure.savefig(FIGURES / f"main_results.{extension}", dpi=250, bbox_inches="tight")
    plt.close(figure)


workflow()
main_results()
font_root = Path(matplotlib.__file__).parent / "mpl-data/fonts/ttf"
for name, filename in [("ReportSans", "DejaVuSans.ttf"), ("ReportSans-Bold", "DejaVuSans-Bold.ttf"), ("ReportSans-Oblique", "DejaVuSans-Oblique.ttf"), ("ReportMono", "DejaVuSansMono.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(font_root / filename)))
pdfmetrics.registerFontFamily("ReportSans", normal="ReportSans", bold="ReportSans-Bold", italic="ReportSans-Oblique", boldItalic="ReportSans-Bold")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportBody", fontName="ReportSans", fontSize=9.1, leading=13.1, textColor=colors.HexColor("#263743"), spaceAfter=7, splitLongWords=True))
styles.add(ParagraphStyle(name="ReportTitle", parent=styles["ReportBody"], fontName="ReportSans-Bold", fontSize=24, leading=30, textColor=colors.HexColor("#244B65"), spaceAfter=17))
styles.add(ParagraphStyle(name="ReportHeading", parent=styles["ReportBody"], fontName="ReportSans-Bold", fontSize=15, leading=20, spaceBefore=10, spaceAfter=10, keepWithNext=True))
styles.add(ParagraphStyle(name="ReportSubheading", parent=styles["ReportBody"], fontName="ReportSans-Bold", fontSize=11.1, leading=15, spaceBefore=9, spaceAfter=7, keepWithNext=True))
styles.add(ParagraphStyle(name="ReportTable", parent=styles["ReportBody"], fontSize=7.2, leading=10.1, spaceAfter=0))
styles.add(ParagraphStyle(name="ReportTableHead", parent=styles["ReportTable"], fontName="ReportSans-Bold", textColor=colors.white))
styles.add(ParagraphStyle(name="ReportCaption", parent=styles["ReportBody"], fontSize=8.2, leading=11.8, textColor=colors.HexColor("#526572")))
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 42
WIDTH = PAGE_WIDTH - 2 * MARGIN


def formatted(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="ReportMono" size="7.4">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def widths(headers):
    if headers[0] == "Evaluator":
        weights = [0.14, 0.13, 0.22, 0.22, 0.16, 0.13]
    elif headers[0] == "Source ID":
        weights = [0.08, 0.57, 0.35]
    elif headers[0] == "Company":
        weights = [0.28, 0.16, 0.56]
    elif headers[0] == "SICS sector":
        weights = [0.60, 0.20, 0.20]
    elif headers[0] == "Task":
        weights = [0.16, 0.19, 0.65]
    elif headers[0] == "Stage" and len(headers) == 3:
        weights = [0.22, 0.40, 0.38]
    elif headers[0] == "Order":
        weights = [0.07, 0.27, 0.66]
    elif headers[0] == "Definition stage":
        weights = [0.18, 0.40, 0.42]
    elif headers[0] == "Retained canonical evidence type":
        weights = [0.25, 0.15, 0.60]
    elif headers[0] == "Topic family":
        weights = [0.26, 0.13, 0.61]
    elif len(headers) == 2:
        weights = [0.40, 0.60]
    else:
        weights = [1 / len(headers)] * len(headers)
    return [WIDTH * weight for weight in weights]


def make_table(lines):
    records = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    records.pop(1)
    cells = [[Paragraph(formatted(cell), styles["ReportTableHead"] if row_number == 0 else styles["ReportTable"]) for cell in record] for row_number, record in enumerate(records)]
    table = Table(cells, colWidths=widths(records[0]), repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#315B77")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#315B77")), ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#D7E0E6")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")])]))
    if records[0][0] in ["Company", "Source ID"]:
        table.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    if records[0][0] == "Source ID":
        table.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return table


lines = (OUT / "REPORT.md").read_text().splitlines()
story = []
position = 0
major_sections = {"6.", "Appendix"}
while position < len(lines):
    line = lines[position]
    if not line.strip():
        position += 1
        continue
    if line.startswith("# "):
        story.append(Paragraph(formatted(line[2:]), styles["ReportTitle"]))
    elif line.startswith("## "):
        title = line[3:]
        if title.split()[0] in major_sections:
            story.append(PageBreak())
        story.append(Paragraph(formatted(title), styles["ReportHeading"]))
    elif line.startswith("### "):
        story.append(Paragraph(formatted(line[4:]), styles["ReportSubheading"]))
    elif line.startswith("| "):
        table_lines = []
        while position < len(lines) and lines[position].startswith("| "):
            table_lines.append(lines[position])
            position += 1
        story.extend([make_table(table_lines), Spacer(1, 10)])
        continue
    elif line.startswith("!["):
        image_path = OUT / re.match(r"!\[.*?\]\((.*?)\)", line).group(1)
        image_width, image_height = ImageReader(str(image_path)).getSize()
        story.append(Image(str(image_path), width=WIDTH, height=WIDTH * image_height / image_width))
        story.append(Spacer(1, 7))
    elif line.startswith("- "):
        items = []
        while position < len(lines) and lines[position].startswith("- "):
            items.append(ListItem(Paragraph(formatted(lines[position][2:]), styles["ReportBody"]), leftIndent=12))
            position += 1
        story.append(ListFlowable(items, bulletType="bullet", leftIndent=12, bulletFontName="ReportSans", bulletFontSize=6))
        continue
    else:
        paragraph = [line]
        position += 1
        while position < len(lines) and lines[position].strip() and not lines[position].startswith(("#", "| ", "![", "- ")):
            paragraph.append(lines[position])
            position += 1
        text = " ".join(paragraph)
        story.append(Paragraph(formatted(text), styles["ReportCaption"] if text.startswith("**Figure") else styles["ReportBody"]))
        continue
    position += 1


def page_frame(canvas, document):
    canvas.saveState()
    canvas.setFont("ReportSans", 7.3)
    canvas.setFillColor(colors.HexColor("#607480"))
    canvas.drawString(MARGIN, PAGE_HEIGHT - 25, "BACE | Main experiment workflow and results")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 25, "Evidence checked 2 November 2026")
    canvas.setStrokeColor(colors.HexColor("#D5DFE5"))
    canvas.line(MARGIN, 31, PAGE_WIDTH - MARGIN, 31)
    canvas.drawString(MARGIN, 20, "Internal technical report | Automated support, not verified truth")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 20, str(document.page))
    canvas.restoreState()


document = SimpleDocTemplate(str(OUT / "BACE_main_experiment_report.pdf"), pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN, topMargin=43, bottomMargin=43, title="BACE Main Experiment: End-to-End Workflow and Principal Results", author="", subject="Verified main_v1 workflow and descriptive experimental results")
document.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
metadata = {"source": "REPORT.md", "source_sha256": hashlib.sha256((OUT / "REPORT.md").read_bytes()).hexdigest(), "numeric_ledger_sha256": hashlib.sha256((OUT / "numeric_ledger.json").read_bytes()).hexdigest(), "pdf": "BACE_main_experiment_report.pdf", "pdf_sha256": hashlib.sha256((OUT / "BACE_main_experiment_report.pdf").read_bytes()).hexdigest(), "figures": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in FIGURES.iterdir()}, "renderer": "reportlab; locally available system packages, without environment changes", "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT / "render_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
print("Rendered", OUT / "BACE_main_experiment_report.pdf")
