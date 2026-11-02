"""Prepare a layout-only workbook using the final export's original formatting."""
import json
from pathlib import Path

import openpyxl

OUT = Path(__file__).resolve().parent
READER = OUT.parent
workbook = openpyxl.load_workbook(READER / "BACE_18_Case_Reader.xlsx")
manifest = json.loads((READER / "export_manifest.json").read_text())
keep = ["Cases", "R01", "R12", "R17"]
for name in list(workbook.sheetnames):
    if name not in keep:
        del workbook[name]
for name in keep[1:]:
    case = next(c for c in manifest["cases"] if c["review_id"] == name)
    workbook[name].print_area = f"A1:H{case['evidence_section_row'] - 1}"

longest = workbook.copy_worksheet(workbook["R12"])
longest.title = "Longest evidence"
packet = json.loads((READER.parent / "packets/R12.json").read_text())
card = max(packet["evidence_cards"], key=lambda e: len(e["retrieval_text"]))
start = next(c.row for row in longest for c in row if c.column == 1 and isinstance(c.value, str)
             and c.value.startswith(card["prompt_label"] + "\nPart 1/"))
end = start
while isinstance(longest.cell(end + 1, 1).value, str) and "Part " in longest.cell(end + 1, 1).value:
    end += 1
longest.print_area = f"A{start}:H{end}"
longest.print_title_rows = None
workbook.save(OUT / "layout_preview.xlsx")
print(f"Preview prepared; longest evidence: {card['prompt_label']}, {len(card['retrieval_text'])} characters, rows {start}-{end}.")
