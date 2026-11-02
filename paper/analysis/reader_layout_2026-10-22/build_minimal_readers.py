"""Build concise case readers from saved records, without new judgments."""
import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import xlsxwriter
from PIL import ImageFont

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OLD = ROOT / "paper/analysis/residual_gap_review_2026-10-20"
NEW = ROOT / "paper/analysis/prompt_gap_review_2026-10-22"
INPUTS = {}
KEY_ECS = {"R01": [1, 3, 4], "R02": [3, 7, 11], "R03": [10, 12, 13],
           "R04": [1], "R05": [1, 2], "R06": [1], "R07": [], "R08": [], "R09": [],
           "R10": [4], "R11": [1, 2], "R12": [1], "R13": [1], "R14": [6],
           "R15": [3, 4, 5], "R16": [4], "R17": [29], "R18": [2]}
OTHER = [13, 13, 25, 51, 1, 13, 11, 6, 29, 29, 7, 44, 11, 18, 26, 3, 4, 35]
NOTES = {"R01": "RAGChecker's claim also includes carbon-reduction measures.",
         "R02": "RAGChecker's claim also includes employees with external contacts.",
         "R10": "RAGChecker's claim omits 'in the available information'.",
         "R16": "RAGAS's claim says that Nestle recognizes these effects on food production systems."}
FONT = ImageFont.truetype("/usr/share/fonts/truetype/Carlito-Regular.ttf", 15)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(path, expected=None):
    b = path.read_bytes()
    h = sha(b)
    if expected:
        assert h == expected, path
    INPUTS[str(path.relative_to(ROOT))] = h
    return b


def load(path, expected=None):
    return json.loads(read(path, expected))


def visible(s):
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", lambda m: f"\\u{ord(m[0]):04x}", str(s))


prov = load(OLD / "selection_provenance.json")
ledger = load(ROOT / "BACE/analysis/outputs/snapshot/sources.json")
new_prov = load(NEW / "provenance.json")
new_results = load(NEW / "selected_prompt_results.json", new_prov["output_sha256"]["selected_prompt_results.json"])
gaps = load(NEW / "results.json", new_prov["output_sha256"]["results.json"])
passages = defaultdict(list)
for r in csv.DictReader(io.StringIO(read(OLD / "source_passages.csv").decode())):
    passages[r["review_id"]].append(r)

cases = []
for i in range(1, 19):
    rid = f"R{i:02d}"
    p = load(OLD / f"packets/{rid}.json", prov["output_sha256"][f"packets/{rid}.json"])
    s = p["selection"]
    p["native"] = {}
    for name in ("ragas", "ragchecker"):
        path = ROOT / "BACE/results/main_v1/cases" / s["generation_case_id"] / f"evaluation/{name}/results.jsonl"
        data = read(path, ledger[str(path.relative_to(ROOT))])
        results = json.loads(data.decode().splitlines()[-1])
        index = int(s["external_claim_index"]) if s["framework"] == name else OTHER[i - 1]
        p["native"][name] = next(x for x in results["claims"] if x["claim_index"] == index)
    p["variants"] = new_results[rid]["prompt_variants"]
    ecs = p["candidate_ecs"]
    p["aliases"] = {e["ec_id"]: f"EC{n:02d}" for n, e in enumerate(ecs, 1)}
    preferred = {ecs[n - 1]["ec_id"] for n in KEY_ECS[rid]}
    p["example_sets"] = {}
    for condition, sets in [("original", p["support"]["support_sets"]), *[(c, v["support_sets"]) for c, v in p["variants"].items()]]:
        if sets:
            chosen = min(sets, key=lambda x: (len(set(x["ec_claim_ids"]) - preferred), len(x["ec_claim_ids"])))
            assert set(chosen["ec_claim_ids"]) <= preferred, (rid, condition)
            p["example_sets"][condition] = chosen
    p["key_ecs"] = [e for e in ecs if e["ec_id"] in preferred]
    cards = {e["prompt_label"]: e for e in p["evidence_cards"]}
    selected = defaultdict(list)
    for entry in passages[rid]:
        assert entry["quote"] in cards[entry["prompt_label"]]["retrieval_text"]
        selected[entry["prompt_label"]].append(entry["quote"])
    if rid == "R01":
        selected["Evidence 6"] = ["200 green solutions delivered via IHG Green Engage."]
    elif rid == "R04":
        text = cards["Evidence 5"]["retrieval_text"]
        selected["Evidence 5"] = [text[text.index("Suppliers and contractors"):text.index("Conferences")].rstrip()]
    elif rid == "R09":
        text = cards["Evidence 4"]["retrieval_text"]
        selected["Evidence 4"] = [text[:text.index("• Interactive careers")].rstrip()]
    elif rid == "R16":
        selected.pop("Evidence 5", None)
        selected["Evidence 4"] = [cards["Evidence 4"]["retrieval_text"].split(". Details")[0] + "."]
    elif rid == "R18":
        selected.pop("Evidence 10", None)
    p["evidence_excerpt_groups"] = []
    for lab, quotes in selected.items():
        card = cards[lab]
        assert all(q in card["retrieval_text"] for q in quotes), (rid, lab, quotes)
        assert sha(card["retrieval_text"].encode()) == card["retrieval_text_hash"]
        p["evidence_excerpt_groups"].append({"card": card, "quotes": quotes})
    p["disclosure_quotes"] = list(dict.fromkeys(q for x in p["target_dc"]["dc_provenance"] for q in x["source_quotes"]))
    assert all(q in p["generated_text"] for q in p["disclosure_quotes"])
    cases.append(p)


def line_count(text, pixels):
    n = 0
    for paragraph in visible(text).split("\n"):
        n += 1
        used = 0
        for word in re.findall(r"\S+\s*|\s+", paragraph):
            size = FONT.getlength(word)
            if used and used + size > pixels:
                n += 1
                used = 0
            while size > pixels:
                n += 1
                size -= pixels
            used += size
    return n


def set_text(p, condition):
    ss = p["example_sets"].get(condition)
    if ss is None:
        return "Empty support-set list"
    return " + ".join(p["aliases"][x] for x in ss["ec_claim_ids"]) + f" ({ss['support_type']})"


reports = []
for adapted, folder, filename in [(False, OLD, "BACE_18_Case_Reader.xlsx"), (True, NEW, "BACE_Prompt_Comparison_18_Cases.xlsx")]:
    dest = folder / "excel_reader"
    target = dest / filename
    before = sha(target.read_bytes())
    wb = xlsxwriter.Workbook(target, {"strings_to_formulas": False, "strings_to_urls": False})
    wb.set_properties({"title": "18 cases — concise prompt comparison" if adapted else "18 cases — concise evidence reader", "author": "BACE project"})
    def fmt(**kw):
        return wb.add_format({"font_name": "Carlito", "font_size": 11, "font_color": "#223A49", "text_wrap": True, "valign": "top", **kw})
    fs = {
        "title": fmt(font_size=17, bold=True, bg_color="#19364A", font_color="white", valign="vcenter"),
        "section": fmt(bold=True, bg_color="#19364A", font_color="white", valign="vcenter"),
        "label": fmt(bold=True, font_color="#137D88"),
        "body": fmt(bottom=1, bottom_color="#E1E9ED"),
        "head": fmt(bold=True, bg_color="#EAF2F4"),
        "note": fmt(font_size=10, font_color="#59707E"),
        "link": fmt(font_color="#006C9A", underline=True, bold=True),
        "S": fmt(bold=True, bg_color="#E7F3EB", font_color="#246347", valign="vcenter"),
        "U": fmt(bold=True, bg_color="#FCEDEE", font_color="#963D3D", valign="vcenter"),
    }
    widths = [17, 18, 18, 18, 18, 18]
    tracked = []
    links = []
    metadata = []

    def put(ws, row, a, b, value, style="body", source=False):
        text = visible(value)
        if a == b:
            ws.write_string(row, a, text, fs[style])
        else:
            ws.merge_range(row, a, row, b, text, fs[style])
        if source:
            tracked.append((ws.name, row + 1, a + 1, text))

    def height(ws, row, fields, minimum=24):
        h = max(minimum, max(line_count(t, sum(widths[a:b+1]) * 7 - 16) * 13.5 + 7 for a, b, t in fields))
        assert h <= 409
        ws.set_row(row, h)

    def field(ws, row, label, text, source=True):
        put(ws, row, 0, 0, label, "label")
        put(ws, row, 1, 5, text, source=source)
        height(ws, row, [(0, 0, label), (1, 5, text)])
        return row + 1

    def note(ws, row, text):
        put(ws, row, 0, 5, text, "note")
        height(ws, row, [(0, 5, text)], minimum=20)
        return row + 1

    def heading(ws, row, text):
        put(ws, row, 0, 5, text, "section")
        ws.set_row(row, 25)
        return row + 1

    def link(ws, row, col, text, sheet):
        ws.write_url(row, col, f"internal:'{sheet}'!A1", fs["link"], text)
        links.append((ws.name, row+1, col+1, sheet))

    overview = wb.add_worksheet("Cases")
    overview.hide_gridlines(2)
    overview.freeze_panes(4, 3)
    names = ["Case", "Company", "Year", "Target claim", "BACE", "RAGAS", "RAGChecker"]
    if adapted:
        names = names[:4] + ["Original BACE", "RAGAS-style", "RAGChecker-style", "RAGAS native", "RAGChecker native"]
    last = len(names)-1
    overview.merge_range(0, 0, 0, last, "18 cases — only the essentials", fs["title"])
    overview.set_row(0, 34)
    overview.merge_range(1, 0, 1, last, "Click a case. Each page contains the target sentence, claim, selected evidence, key ECs and saved results.", fs["note"])
    overview.set_row(1, 24)
    overview.merge_range(2, 0, 2, last, "Evidence and ECs are selected excerpts. Native claim wording and RAGAS's saved reason are available in result-cell notes.", fs["note"])
    overview.set_row(2, 24)
    for j, width in enumerate([8, 20, 8, 49] + [15] * (len(names)-4)):
        overview.set_column(j, j, width)
    overview.add_table(3, 0, 21, last, {"name": "ConciseCases", "columns": [{"header": name, "header_format": fs["head"]} for name in names], "style": "Table Style Medium 2"})
    overview.set_row(3, 31)

    for i, p in enumerate(cases, 4):
        rid = p["review_id"]
        s = p["selection"]
        company = s["company_name"].replace("\u00ad", "")
        ws = wb.add_worksheet(rid)
        ws.hide_gridlines(2)
        ws.set_zoom(100)
        ws.freeze_panes(2, 0)
        for col, width in enumerate(widths):
            ws.set_column(col, col, width)
        put(ws, 0, 0, 5, f"{rid}  |  {company}  |  {s['year']}  |  {s['task']}", "title")
        ws.set_row(0, 32)
        link(ws, 1, 0, "All cases", "Cases")
        ws.set_row(1, 22)
        row = heading(ws, 2, "1  |  Disclosure and claim")
        row = field(ws, row, "Disclosure", "\n".join(p["disclosure_quotes"]))
        row = field(ws, row, "Claim", p["target_dc"]["dc_text"])
        if rid in NOTES:
            row = note(ws, row, NOTES[rid])
        row = heading(ws, row, "2  |  Evidence and key candidate ECs")
        for group in p["evidence_excerpt_groups"]:
            card = group["card"]
            label = f"{card['source_year']} | {card['prompt_label']}"
            row = field(ws, row, label, "\n".join(group["quotes"]))
        key_count = len(p["key_ecs"])
        all_count = len(p["candidate_ecs"])
        put(ws, row, 0, 5, f"Key candidate ECs — {key_count} of {all_count} shown", "head")
        ws.set_row(row, 24)
        row += 1
        if not all_count:
            row = field(ws, row, "Candidate ECs", "Empty candidate list (0).", source=False)
        for ec in p["key_ecs"]:
            row = field(ws, row, p["aliases"][ec["ec_id"]], ec["ec_text"])
        if rid in ("R10", "R11"):
            row = note(ws, row, "These excerpts alone cannot verify absence across all supplied evidence.")
        result_row = row + 1
        row = heading(ws, row, "3  |  Saved results")
        flags = [bool(p["support"]["support_sets"]), p["native"]["ragas"]["supported"], p["native"]["ragchecker"]["supported"]]
        labels = ["BACE", "RAGAS", "RAGChecker"]
        cols = [(0, 1), (2, 3), (4, 5)]
        if adapted:
            flags = [flags[0], p["variants"]["ragas_style"]["supported"], p["variants"]["ragchecker_style"]["supported"], flags[1], flags[2]]
            labels = ["Original BACE", "RAGAS-style", "RAGChecker-style", "RAGAS native", "RAGChecker native"]
            cols = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 5)]
        original_type = p["diagnosis"]["unsupported_label"] if p["diagnosis"] else None
        assert not (flags[0] and original_type), rid
        unsupported_types = [original_type] + [None] * (len(flags) - 1)
        result_fields = []
        for (a, b), label, flag, unsupported_type in zip(cols, labels, flags, unsupported_types):
            put(ws, row, a, b, label, "head")
            verdict = "Supported"
            if not flag:
                type_text = unsupported_type.replace("_", " ").capitalize() if unsupported_type else "Type not recorded"
                verdict = "Unsupported\n" + type_text
            put(ws, row+1, a, b, verdict, "S" if flag else "U", source=True)
            result_fields.append((a, b, verdict))
        ws.set_row(row, 31)
        height(ws, row+1, result_fields, minimum=25)
        if original_type:
            ws.write_comment(row+1, 0, "Saved original BACE unsupported_label:\n" + original_type,
                             {"author": "Saved record"})
        for framework, pos in [("ragas", cols[-2][0]), ("ragchecker", cols[-1][0])]:
            native = p["native"][framework]
            claim = json.dumps(native["claim"], ensure_ascii=False) if isinstance(native["claim"], list) else native["claim"]
            comment = "Exact native claim:\n" + claim
            if framework == "ragas":
                comment += "\n\nSaved RAGAS reason:\n" + native["reason"]
            ws.write_comment(row+1, pos, comment, {"author": "Saved record", "x_scale": 2, "y_scale": 2})
        row += 2
        if p["diagnosis"]:
            row = field(ws, row, "BACE reason", p["diagnosis"]["rationale"])
        conditions = ["original", "ragas_style", "ragchecker_style"] if adapted else ["original"]
        positive = [c for c in conditions if c in p["example_sets"]]
        if positive:
            labels_by_condition = {"original": "BACE", "ragas_style": "RAGAS-style", "ragchecker_style": "RAGChecker-style"}
            support = "\n".join(labels_by_condition[c] + ": " + set_text(p, c) for c in positive)
            row = field(ws, row, "Example support sets", support)
        if adapted:
            row = note(ws, row, "Styles = BACE prompt variants. They saved support sets, not written reasons; one set per supported condition is shown.")
        elif positive:
            row = note(ws, row, "One actual BACE support set is shown; no written reason was recorded for this supported decision.")
        else:
            row = note(ws, row, "Evidence and ECs above are selected excerpts. BACE reason is its saved diagnosis rationale.")
        ws.set_paper(9)
        ws.set_portrait()
        ws.set_margins(0.3, 0.3, 0.3, 0.3)
        ws.fit_to_pages(1, 1)
        ws.print_area(0, 0, row-1, 5)
        ws.set_footer("&L" + rid + " | Selected source excerpts&R&P", {"margin": 0.12})
        metadata.append({"review_id": rid, "shown_ec_ids": [e["ec_id"] for e in p["key_ecs"]],
                         "total_candidate_ecs": all_count, "example_support_sets": {c: p["example_sets"][c] for c in positive},
                         "unsupported_types": {label: {"saved_label": kind, "status": "not_applicable" if flag else "recorded" if kind else "not_recorded"}
                                               for label, flag, kind in zip(labels, flags, unsupported_types)},
                         "result_section_row": result_row, "last_row": row,
                         "row_heights_total_pt": sum(x[0] for x in ws.set_rows.values())})
        overview.set_row(i, 56)
        link(overview, i, 0, rid, rid)
        for j, val in [(1, company), (2, s["year"]), (3, p["target_dc"]["dc_text"])]:
            overview.write_string(i, j, val, fs["body"])
        for j, flag in enumerate(flags, 4):
            overview.write_string(i, j, "Supported" if flag else "Unsupported", fs["S" if flag else "U"])

    if adapted:
        ws = wb.add_worksheet("Gap summary")
        ws.hide_gridlines(2)
        ws.set_column("A:A", 29)
        ws.set_column("B:D", 23)
        ws.merge_range("A1:D1", "Support rates and gaps", fs["title"])
        ws.set_row(0, 34)
        ws.merge_range("A2:D2", "Same 1,796 disclosures; gap = native score minus BACE-condition score (percentage points).", fs["note"])
        ws.set_row(1, 30)
        row = 3
        for scope, title in [("all_claims", "All claims"), ("excluding_original_boundary", "Original boundary-labelled claims excluded")]:
            ws.merge_range(row, 0, row, 3, title, fs["section"]); ws.set_row(row, 26); row += 1
            ws.write_row(row, 0, ["BACE condition", "Support (%)", "Gap to native RAGAS", "Gap to native RAGChecker"], fs["head"])
            ws.set_row(row, 31); row += 1
            for condition, label in [("original", "Original"), ("ragas_style", "RAGAS-style"), ("ragchecker_style", "RAGChecker-style")]:
                x = gaps[scope]
                ws.write_row(row, 0, [label, round(x["mean_support_percent"][condition], 2), round(x["native_minus_bace_gap_pp"][condition]["ragas"], 2), round(x["native_minus_bace_gap_pp"][condition]["ragchecker"], 2)], fs["body"])
                ws.set_row(row, 29); row += 1
            row += 1
        ws.merge_range(row, 0, row, 3, "Native inventories remain unchanged. Three failed records exclude two entire disclosures. These score gaps do not establish accuracy.", fs["note"])
        ws.set_row(row, 42)
        ws.set_paper(9);ws.fit_to_pages(1, 1);ws.print_area(0, 0, row, 3)

    overview.activate()
    wb.close()
    check = openpyxl.load_workbook(target)
    for sheet, row, col, value in tracked:
        assert check[sheet].cell(row, col).value == value
    for sheet, row, col, dest_sheet in links:
        assert dest_sheet in check.sheetnames
        assert check[sheet].cell(row, col).hyperlink is not None
    assert all(c.data_type != "f" for ws in check for row in ws for c in row)
    manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "workbook": filename,
                "workbook_sha256": sha(target.read_bytes()), "previous_workbook_sha256": before,
                "builder": str(Path(__file__).relative_to(ROOT)), "script_sha256": sha(Path(__file__).read_bytes()),
                "reading_order": ["Disclosure and claim", "Evidence and key ECs", "Saved results"],
                "selection": "Editorial selection of exact passages and key candidate ECs. This is not the complete input. One actual support set is displayed per supported condition; all its EC texts are shown.",
                "input_sha256": INPUTS, "verified_source_cells": len(tracked), "verified_internal_links": len(links),
                "cases": metadata, "model_calls": 0, "new_judgments": 0,
                "reproduction_command": "/home/muwang/.local/share/bace-writing-skills/venv/bin/python " + str(Path(__file__).relative_to(ROOT))}
    (dest / "export_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    reports.append(manifest)
    print(filename, "verified cells", len(tracked), "max case height", max(c["row_heights_total_pt"] for c in metadata), flush=True)

(OUT / "minimal_reader_manifest.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
