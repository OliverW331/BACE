from pathlib import Path
from html import escape

from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/main/experimental_framework_evolution_executive_report.md"
OUTPUT = ROOT / "output/pdf/experimental_framework_evolution_executive_report.pdf"
for name, filename in [
    ("Liberation", "LiberationSans-Regular.ttf"),
    ("Liberation-Bold", "LiberationSans-Bold.ttf"),
    ("Liberation-Italic", "LiberationSans-Italic.ttf"),
    ("Liberation-BoldItalic", "LiberationSans-BoldItalic.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, "/usr/share/fonts/truetype/" + filename))
pdfmetrics.registerFontFamily(
    "Liberation", normal="Liberation", bold="Liberation-Bold",
    italic="Liberation-Italic", boldItalic="Liberation-BoldItalic",
)
NAVY = colors.HexColor("#183347")
TEAL = colors.HexColor("#176E78")
INK = colors.HexColor("#24313B")
GRAY = colors.HexColor("#586975")
BASE = dict(fontName="Liberation", textColor=INK, alignment=TA_LEFT)
STYLES = {
    "body": ParagraphStyle("body", fontSize=10.5, leading=14.4, spaceAfter=8, **BASE),
    "title": ParagraphStyle("title", fontSize=21, leading=24, spaceAfter=11,
                            fontName="Liberation-Bold", textColor=NAVY),
    "h2": ParagraphStyle("h2", fontSize=16.5, leading=20.5, spaceAfter=12,
                         fontName="Liberation-Bold", textColor=NAVY, keepWithNext=True),
    "h3": ParagraphStyle("h3", fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=6,
                         fontName="Liberation-Bold", textColor=TEAL, keepWithNext=True),
    "table": ParagraphStyle("table", fontSize=9.7, leading=12.6, **BASE),
    "tablehead": ParagraphStyle("tablehead", fontSize=9.7, leading=12.6,
                                fontName="Liberation-Bold", textColor=colors.white),
    "source": ParagraphStyle("source", fontSize=8.2, leading=10.8,
                             spaceBefore=8, spaceAfter=0,
                             fontName="Liberation", textColor=GRAY),
    "subtitle": ParagraphStyle("subtitle", fontSize=9.2, leading=12,
                               spaceAfter=14, fontName="Liberation", textColor=GRAY),
    "list": ParagraphStyle("list", fontSize=10.5, leading=14.4,
                           spaceAfter=6, leftIndent=15, firstLineIndent=-15, **BASE),
    "quote": ParagraphStyle("quote", fontSize=11.2, leading=15.5,
                            spaceBefore=12, spaceAfter=20, leftIndent=12, rightIndent=9,
                            borderColor=TEAL, borderWidth=1, borderPadding=9,
                            backColor=colors.HexColor("#F2F7F8"), **BASE),
}


def inline(token):
    parts = []
    for t in token.children or []:
        if t.type == "text":
            parts.append(escape(t.content))
        elif t.type in ("softbreak", "hardbreak"):
            parts.append(" " if t.type == "softbreak" else "<br/>")
        elif t.type == "strong_open": parts.append("<b>")
        elif t.type == "strong_close": parts.append("</b>")
        elif t.type == "em_open": parts.append("<i>")
        elif t.type == "em_close": parts.append("</i>")
        elif t.type == "code_inline":
            parts.append('<font name="Courier" size="9">' + escape(t.content) + '</font>')
        elif t.type == "link_open": parts.append('<font color="#176E78">')
        elif t.type == "link_close": parts.append('</font>')
    return "".join(parts)


def footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(colors.HexColor("#D4DFE4"))
    canvas.setLineWidth(0.5)
    canvas.line(46, 35, w - 46, 35)
    canvas.setFont("Liberation", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(46, 23, "Research progress | Supervisory update | 10 September 2026")
    canvas.drawRightString(w - 46, 23, f"{doc.page} / 6")
    canvas.restoreState()


tokens = MarkdownIt("commonmark").enable("table").parse(SOURCE.read_text())
story = []
page = 1
table_on_page = 0
width = A4[0] - 92
widths = {
    (1, 1): [.37, .63],
    (2, 1): [.49, .23, .28],
    (2, 2): [.55, .18, .27],
    (3, 1): [.29, .71],
    (4, 1): [.20, .80],
    (5, 1): [.19, .81],
    (6, 1): [.24, .31, .45],
}
heading = None
list_stack = []
in_quote = False
i = 0
while i < len(tokens):
    t = tokens[i]
    if t.type == "html_block" and 'class="page-break"' in t.content:
        story.append(PageBreak())
        page += 1
        table_on_page = 0
    elif t.type == "heading_open": heading = t.tag
    elif t.type == "heading_close": heading = None
    elif t.type == "blockquote_open": in_quote = True
    elif t.type == "blockquote_close": in_quote = False
    elif t.type in ("bullet_list_open", "ordered_list_open"):
        list_stack.append({"ordered": t.type == "ordered_list_open", "n": 0})
    elif t.type in ("bullet_list_close", "ordered_list_close"):
        list_stack.pop()
    elif t.type == "list_item_open": list_stack[-1]["n"] += 1
    elif t.type == "table_open":
        table_on_page += 1
        data, row, in_head = [], [], False
        i += 1
        while tokens[i].type != "table_close":
            x = tokens[i]
            if x.type == "thead_open": in_head = True
            elif x.type == "thead_close": in_head = False
            elif x.type == "tr_open": row = []
            elif x.type == "tr_close": data.append(row)
            elif x.type == "inline":
                row.append(Paragraph(inline(x), STYLES["tablehead" if in_head else "table"]))
            i += 1
        proportions = widths[(page, table_on_page)]
        table = Table(data, colWidths=[width * x for x in proportions], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F2F6F8"), colors.white]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, -1), (-1, -1), .5, colors.HexColor("#D4DFE4")),
        ]))
        story.extend([table, Spacer(1, 9)])
    elif t.type == "inline":
        text = inline(t)
        style = "body"
        if heading: style = {"h1": "title", "h2": "h2", "h3": "h3"}[heading]
        elif t.content.startswith("Source:"): style = "source"
        elif t.content.startswith("**Asynchronous update"): style = "subtitle"
        elif in_quote: style = "quote"
        elif list_stack:
            style = "list"
            n = list_stack[-1]["n"]
            prefix = f"{n}. " if list_stack[-1]["ordered"] else "- "
            text = prefix + text
        story.append(Paragraph(text, STYLES[style]))
    i += 1

assert page == 6
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=A4, leftMargin=46, rightMargin=46,
    topMargin=42, bottomMargin=47,
    title="Research Progress and Revised Experimental Design",
    author="", subject="Six-page supervisory update on W2 results, W1 feasibility and the revised study",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
