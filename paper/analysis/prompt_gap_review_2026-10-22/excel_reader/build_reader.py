"""Export the same 18 cases with verified prompt-sensitivity support results.

Run with the independent writing environment. No experiment artifacts are changed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import xlsxwriter
from PIL import ImageFont

OUT = Path(__file__).resolve().parent
NEW = OUT.parent
ROOT = NEW.parents[2]
REVIEW = ROOT / "paper/analysis/residual_gap_review_2026-10-20"
XLSX = OUT / "BACE_Prompt_Comparison_18_Cases.xlsx"
VARIANTS = ("ragas_style", "ragchecker_style")
VARIANT_LABELS = {"original": "Original BACE", "ragas_style": "BACE–RAGAS-style", "ragchecker_style": "BACE–RAGChecker-style"}
OTHER_INDEX = dict(zip((f"R{i:02d}" for i in range(1, 19)),
                      [13, 13, 25, 51, 1, 13, 11, 6, 29, 29, 7, 44, 11, 18, 26, 3, 4, 35]))
EXPECTED_VERDICTS = {
    **{f"R{i:02d}": (False, True, True) for i in range(1, 13)},
    "R10": (False, True, False), "R13": (True, False, True),
    "R14": (True, False, False), "R15": (True, True, False),
    "R16": (True, True, False), "R17": (True, True, True), "R18": (True, True, True),
}
ALIGNMENT_NOTES = {
    "R01": "RAGChecker also includes carbon-reduction measures; BACE and RAGAS target energy efficiency.",
    "R02": "RAGChecker also includes employees with external contacts; BACE and RAGAS target senior employees.",
    "R03": "RAGAS uses past tense; BACE and RAGChecker use present tense.",
    "R05": "The BACE and RAGAS claim texts include 2019; the RAGChecker triple does not include a year.",
    "R06": "RAGAS does not name Hera in its claim text; the company is in the disclosure context.",
    "R07": "RAGChecker says 'ensure compliance'; BACE and RAGAS say 'bring ... into compliance'.",
    "R10": "RAGChecker omits 'in the available information'. Its non-reporting claim has a broader wording.",
    "R15": "RAGAS explicitly adds 'in 2020'; the BACE claim and RAGChecker triple do not include the year.",
    "R16": "RAGAS asserts that Nestle recognizes these effects; BACE and RAGChecker assert the effects themselves.",
}

INPUTS = {}
SOURCE_CELLS = []
TRANSFORMATIONS = []
LINKS = []
FONT = ImageFont.truetype("/usr/share/fonts/truetype/Carlito-Regular.ttf", 15)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    data = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = digest(data)
    return data


LEDGER = json.loads(read(ROOT / "BACE/analysis/outputs/snapshot/sources.json"))
PACKET_PROVENANCE = json.loads(read(REVIEW / "selection_provenance.json"))
NEW_PROVENANCE = json.loads(read(NEW / "provenance.json"))
for name in ("selected_prompt_results.json", "results.json"):
    assert digest(read(NEW / name)) == NEW_PROVENANCE["output_sha256"][name]
PROMPT_RESULTS = json.loads(read(NEW / "selected_prompt_results.json"))
GAPS = json.loads(read(NEW / "results.json"))
INPUTS.update(NEW_PROVENANCE["input_sha256"])


def raw(base, rel):
    path = base / rel
    data = read(path)
    assert digest(data) == LEDGER[str(path.relative_to(ROOT))], path
    return [json.loads(line) for line in data.decode().splitlines() if line.strip()]


def visible(text):
    """Reversibly display control characters that cannot be stored in XML 1.0."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", lambda m: f"\\u{ord(m[0]):04x}", str(text))


def load_cases():
    cases = []
    for i in range(1, 19):
        rid = f"R{i:02d}"
        path = REVIEW / "packets" / f"{rid}.json"
        data = read(path)
        assert digest(data) == PACKET_PROVENANCE["output_sha256"][f"packets/{rid}.json"]
        p = json.loads(data)
        s = p["selection"]
        base = ROOT / "BACE/results/main_v1/cases" / s["generation_case_id"]
        dc_id = s["bace_dc_id"]
        assert p["generated_text"] == raw(base, "generation/generated_disclosures.jsonl")[0]["generated_text"]
        assert p["evidence_cards"] == raw(base, "inputs/generation_cases.jsonl")[0]["prompt_evidence"]
        assert p["target_dc"] == next(x for x in raw(base, "bace/dedup/dc_claims.jsonl") if x["dc_id"] == dc_id)
        ecs = raw(base, "bace/dedup/ec_claims.jsonl")
        candidate_ids = next(x for x in raw(base, "bace/candidates/dc_candidate_ecs.jsonl") if x["dc_claim_id"] == dc_id)["candidate_ec_ids"]
        assert p["candidate_ecs"] == [x for x in ecs if x["ec_id"] in candidate_ids]
        assert len(p["candidate_ecs"]) == int(s["candidate_count"]) == len(candidate_ids)
        assert p["support"] == next(x for x in raw(base, "bace/support/dc_support_sets.jsonl") if x["dc_claim_id"] == dc_id)
        assert p["diagnosis"] == next((x for x in raw(base, "bace/diagnosis/dc_unsupported_diagnoses.jsonl") if x["dc_claim_id"] == dc_id), None)
        p["native"] = {}
        for framework in ("ragas", "ragchecker"):
            idx = int(s["external_claim_index"]) if framework == s["framework"] else OTHER_INDEX[rid]
            result = raw(base, f"evaluation/{framework}/results.jsonl")[-1]
            claim = next(x for x in result["claims"] if x["claim_index"] == idx)
            p["native"][framework] = claim
            if framework == s["framework"]:
                assert claim == p["comparator_claim"]
        actual = (bool(p["support"]["support_sets"]), p["native"]["ragas"]["supported"], p["native"]["ragchecker"]["supported"])
        assert actual == EXPECTED_VERDICTS[rid], (rid, actual)
        assert actual[0] == (s["bace_supported"] == "True")
        assert (p["diagnosis"] is None) == actual[0]
        for card in p["evidence_cards"]:
            assert digest(card["retrieval_text"].encode()) == card["retrieval_text_hash"]
        assert set(p["native"]["ragchecker"]["evidence_verdicts"]) == {e["evidence_id"] for e in p["evidence_cards"]}
        p["aliases"] = {x["ec_id"]: f"EC{n:02d}" for n, x in enumerate(p["candidate_ecs"], 1)}
        for ss in p["support"]["support_sets"]:
            assert set(ss["ec_claim_ids"]) <= set(p["aliases"])
        p["prompt_variants"] = PROMPT_RESULTS[rid]["prompt_variants"]
        for condition, result in p["prompt_variants"].items():
            assert result["supported"] == bool(result["support_sets"])
            assert result["rationale"] is None and result["diagnosis"] is None
            assert result["call_status"] == "success"
            for ss in result["support_sets"]:
                assert set(ss["ec_claim_ids"]) <= set(p["aliases"])
        cases.append(p)
    return cases


CASES = load_cases()
PASSAGES = defaultdict(list)
for entry in csv.DictReader(read(REVIEW / "source_passages.csv").decode().splitlines()):
    p = next(x for x in CASES if x["review_id"] == entry["review_id"])
    card = next(e for e in p["evidence_cards"] if e["evidence_id"] == entry["evidence_id"])
    assert entry["quote"] in card["retrieval_text"]
    assert entry["retrieval_text_sha256"] == card["retrieval_text_hash"]
    PASSAGES[entry["review_id"]].append(entry)

wb = xlsxwriter.Workbook(XLSX, {"strings_to_formulas": False, "strings_to_urls": False})
wb.set_properties({"title": "BACE: prompt comparison for 18 existing cases", "author": "BACE project",
                   "subject": "Saved prompt sensitivity results and native score gaps",
                   "comments": "Source-verified export; no new evaluator judgments."})
NAVY = "#19364A"
TEAL = "#137D88"
INK = "#253A47"
MUTED = "#58707C"
PALE = "#F1F6F8"
BORDER = "#D9E3E8"


def fmt(**kw):
    return wb.add_format({"font_name": "Carlito", "font_size": 11, "font_color": INK,
                          "valign": "top", "text_wrap": True, **kw})


F = {
    "title": fmt(bold=True, font_size=20, font_color="white", bg_color=NAVY, valign="vcenter"),
    "section": fmt(bold=True, font_size=12, font_color="white", bg_color=NAVY, valign="vcenter"),
    "head": fmt(bold=True, font_color="white", bg_color=TEAL, valign="vcenter"),
    "body": fmt(bottom=1, bottom_color=BORDER),
    "alt": fmt(bottom=1, bottom_color=BORDER, bg_color=PALE),
    "label": fmt(bold=True, font_color=TEAL, bottom=1, bottom_color=BORDER),
    "note": fmt(font_size=10, font_color=MUTED),
    "warn": fmt(font_size=10, font_color="#76501D", bg_color="#FFF4DF"),
    "link": fmt(font_color="#006C9A", underline=True, bold=True),
    "count": fmt(align="center", valign="vcenter", font_color=TEAL),
    "Supported": fmt(bold=True, font_color="#246347", bg_color="#E7F3EB", valign="vcenter"),
    "Unsupported": fmt(bold=True, font_color="#963D3D", bg_color="#FCEDEE", valign="vcenter"),
    "Entailment": fmt(bold=True, font_color="#246347", bg_color="#E7F3EB"),
    "Neutral": fmt(font_color=MUTED, bg_color=PALE),
    "Contradiction": fmt(bold=True, font_color="#963D3D", bg_color="#FCEDEE"),
}
WIDTHS = [18, 16, 16, 16, 16, 16, 16, 16]


def config(ws, overview=False):
    ws.hide_gridlines(2)
    ws.set_zoom(95 if overview else 100)
    ws.set_tab_color(TEAL)
    ws.set_default_row(22)
    ws.set_paper(9)
    ws.set_margins(0.35, 0.35, 0.4, 0.4)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.set_header("&LBACE | Evidence reader&R18 existing review cases", {"margin": 0.15})
    ws.set_footer("&LSource: main_v1 + prompt_sensitivity_v1&RPage &P of &N", {"margin": 0.15})
    ws.freeze_panes(4, 0)
    if not overview:
        for col, width in enumerate(WIDTHS):
            ws.set_column(col, col, width)
        ws.repeat_rows(0, 2)


def lines(text, width_px):
    n = 0
    for para in visible(text).split("\n"):
        used = 0
        n += 1
        for token in re.findall(r"\S+\s*|\s+", para):
            size = FONT.getlength(token)
            if used and used + size > width_px:
                n += 1
                used = 0
            while size > width_px:
                n += 1
                size -= width_px
            used += size
    return n


def height(ws, row, fields, minimum=26):
    h = max(minimum, max((lines(text, max(70, sum(WIDTHS[a:b+1]) * 7 - 24)) * 14.5 + 12
                          for a, b, text in fields), default=minimum))
    assert h <= 409, (ws.name, row + 1, h)
    ws.set_row(row, h)


def put(ws, row, a, b, value, style="body", source=None):
    rendered = visible(value)
    assert len(rendered) <= 32767
    if a == b:
        ws.write_string(row, a, rendered, F[style])
    else:
        ws.merge_range(row, a, row, b, rendered, F[style])
    if source:
        SOURCE_CELLS.append({"sheet": ws.name, "row": row + 1, "col": a + 1,
                             "role": source, "value": rendered})
        if rendered != str(value):
            TRANSFORMATIONS.append({"sheet": ws.name, "cell": xlsxwriter.utility.xl_rowcol_to_cell(row, a),
                                    "rule": "XML-incompatible control characters displayed as literal \\uNNNN",
                                    "original_sha256": digest(str(value).encode())})


def link(ws, row, a, b, label, target_sheet, target_row):
    label = label.replace("\n", " | ")
    if (row, a) not in ws.merged_cells:
        put(ws, row, a, b, label, "link")
    ws.write_url(row, a, f"internal:'{target_sheet}'!A{target_row+1}", F["link"], label)
    LINKS.append((ws.name, row + 1, a + 1, target_sheet, target_row + 1))


def section(ws, row, title):
    put(ws, row, 0, 7, title, "section")
    ws.set_row(row, 28)
    return row + 1


def note(ws, row, text, warning=False):
    put(ws, row, 0, 7, text, "warn" if warning else "note")
    height(ws, row, [(0, 7, text)], minimum=27)
    return row + 1


def chunks(text, limit=1600):
    """Split long cell contents without changing or dropping any characters."""
    result = []
    while len(text) > limit:
        end = max(text.rfind("\n", 0, limit + 1), text.rfind(". ", 0, limit + 1) + 1,
                  text.rfind(" ", 0, limit + 1))
        if end < limit // 2:
            end = limit
        result.append(text[:end])
        text = text[end:]
    result.append(text)
    return result


def location(card):
    p = card.get("page_start")
    end = card.get("page_end")
    return f"{card.get('source_year')}" + (f" | p. {p}" + (f"-{end}" if end != p else "") if p else " | metric")


def saved_support(p, condition="original"):
    ss = p["support"]["support_sets"] if condition == "original" else p["prompt_variants"][condition]["support_sets"]
    if not ss:
        return "No support sets recorded (empty list)."
    return "\n".join(f"Set {i} ({s['support_type']}): " + " + ".join(p["aliases"][x] for x in s["ec_claim_ids"])
                     for i, s in enumerate(ss, 1))


def rc_triple(claim):
    assert isinstance(claim, list) and len(claim) == 3
    return "\n".join(f"{label}: {value}" for label, value in zip(("Subject", "Relation", "Object"), claim))


overview = wb.add_worksheet("Cases")
config(overview, overview=True)
for col, width in enumerate([9, 21, 9, 48, 15, 15, 15, 15, 15]):
    overview.set_column(col, col, width)
overview.freeze_panes(5, 3)
overview.merge_range("A1:I1", "18-case prompt comparison", F["title"])
overview.set_row(0, 38)
overview.merge_range("A2:I2", "Same R01-R18 cases as the earlier reader. Click a case to compare the three BACE conditions, native judgments, candidate ECs and full evidence.", F["note"])
overview.set_row(1, 25)
overview.merge_range("A3:I3", "Style columns change only BACE's support prompt. Native columns retain the original frameworks' own claim inventories. Decisions are not correctness labels.", F["warn"])
overview.set_row(2, 31)
link(overview, 3, 0, 3, "Overall support rates and gaps", "Gap summary", 0)
link(overview, 3, 4, 8, "Reading notes and source information", "About", 0)
headers = ["Case", "Company", "Year / task", "Disclosure claim (BACE)", "Original BACE", "RAGAS-style", "RAGChecker-style", "RAGAS native", "RAGChecker native"]
overview.add_table(4, 0, 22, 8, {"name": "ReviewCases", "style": "Table Style Medium 2",
                              "columns": [{"header": h, "header_format": F["head"]} for h in headers]})
overview.set_row(4, 31)

CASE_META = []
for i, p in enumerate(CASES):
    rid = p["review_id"]
    s = p["selection"]
    company = s["company_name"].replace("\u00ad", "")
    ws = wb.add_worksheet(rid)
    config(ws)
    ec_cards = {e["evidence_id"]: e for e in p["evidence_cards"]}
    put(ws, 0, 0, 7, f"{rid}  |  {company}", "title")
    ws.set_row(0, 37)
    put(ws, 1, 0, 7, f"Reporting year {s['year']}   |   {s['task']}   |   {len(p['candidate_ecs'])} candidate ECs   |   {len(p['evidence_cards'])} evidence cards", "note")
    ws.set_row(1, 24)
    link(ws, 2, 0, 1, "Back to Cases", "Cases", i + 5)
    ws.set_row(2, 25)
    note(ws, 3, "DC = disclosure claim; EC = evidence claim. Blue links jump within this workbook. Each framework's native claim is preserved.")
    row = section(ws, 4, "1  |  Disclosure related — passages and claims")
    quotes = list(dict.fromkeys(q for prov in p["target_dc"]["dc_provenance"] for q in prov["source_quotes"]))
    assert all(q in p["generated_text"] for q in quotes)
    for n, q in enumerate(quotes, 1):
        put(ws, row, 0, 0, f"Passage {n}", "label")
        put(ws, row, 1, 7, q, source="disclosure_source_quote")
        height(ws, row, [(1, 7, q)])
        row += 1
    row = note(ws, row, "The passages above locate the target. Native claims and the full disclosure follow before the evidence and results.")
    for a, b, title in [(0, 1, "Claim source"), (2, 7, "Disclosure claim — exact saved text")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 30)
    row += 1
    for name, claim in [("BACE", p["target_dc"]["dc_text"]), ("RAGAS native", p["native"]["ragas"]["claim"]), ("RAGChecker native", rc_triple(p["native"]["ragchecker"]["claim"]))]:
        put(ws, row, 0, 1, name, "label")
        put(ws, row, 2, 7, claim, source="disclosure_native_claim")
        height(ws, row, [(0, 1, name), (2, 7, claim)])
        row += 1
    if rid in ALIGNMENT_NOTES:
        row = note(ws, row, "Wording note: " + ALIGNMENT_NOTES[rid], warning=True)
    disclosure_section = row
    row = section(ws, row, "1.1  |  Full generated disclosure — exact saved text")
    disclosure_cells = []
    for n, part in enumerate(chunks(p["generated_text"], 1400), 1):
        put(ws, row, 0, 0, f"Part {n}", "label")
        put(ws, row, 1, 7, part, source="full_disclosure_text")
        height(ws, row, [(1, 7, part)])
        disclosure_cells.append((row + 1, 2))
        row += 1
    excerpt_section = row
    row = section(ws, row, "2  |  Evidence related — selected source passages")
    row = note(ws, row, "These are selected excerpts, not the complete input. All supplied evidence cards appear below, including cards with no BACE candidate EC.")
    excerpt_links = []
    for entry in PASSAGES[rid]:
        card = ec_cards[entry["evidence_id"]]
        put(ws, row, 0, 1, card["prompt_label"] + "\n" + location(card), "label")
        put(ws, row, 2, 7, entry["quote"], source="evidence_excerpt")
        height(ws, row, [(0, 1, card["prompt_label"] + "\n" + location(card)), (2, 7, entry["quote"])])
        excerpt_links.append((row, entry["evidence_id"]))
        row += 1
    candidate_section = row
    row = section(ws, row, f"2.1  |  Candidate ECs — complete, identical input to all three BACE conditions ({len(p['candidate_ecs'])})")
    row = note(ws, row, "EC aliases match the previous reader. This is the complete candidate input. Saved support-set membership is listed later in Results.")
    for a, b, title in [(0, 0, "EC"), (1, 5, "Candidate EC — exact saved text"), (6, 7, "Source card(s)")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 31)
    row += 1
    ec_links = []
    ec_row_map = {}
    ec_usage = {}
    if not p["candidate_ecs"]:
        row = note(ws, row, "No candidate ECs: the saved candidate list is empty.")
    for ec in p["candidate_ecs"]:
        alias = p["aliases"][ec["ec_id"]]
        labels = [ec_cards[x]["prompt_label"] for x in ec["evidence_card_ids"]]
        membership = []
        for condition, short in (("original", "Original"), ("ragas_style", "RA-style"), ("ragchecker_style", "RC-style")):
            sets = p["support"]["support_sets"] if condition == "original" else p["prompt_variants"][condition]["support_sets"]
            indexes = [f"S{j}" for j, ss in enumerate(sets, 1) if ec["ec_id"] in ss["ec_claim_ids"]]
            if indexes:
                membership.append(short + ": " + ", ".join(indexes))
        put(ws, row, 0, 0, alias, "label")
        put(ws, row, 1, 5, ec["ec_text"], source="candidate_ec_text")
        put(ws, row, 6, 7, "\n".join(labels), "link")
        ec_usage[ec["ec_id"]] = "\n".join(membership) or "Not in a support set"
        height(ws, row, [(1, 5, ec["ec_text"]), (6, 7, "\n".join(labels))])
        ws.write_comment(row, 0, json.dumps({"ec_id": ec["ec_id"], "evidence_card_ids": ec["evidence_card_ids"]}, ensure_ascii=False, indent=2), {"author": "Saved EC identifiers", "x_scale": 2})
        ec_links.append((row, ec["evidence_card_ids"][0], "\n".join(labels)))
        ec_row_map[ec["ec_id"]] = row
        row += 1
    evidence_section = row
    row = section(ws, row, f"2.2  |  Full supplied evidence — all {len(p['evidence_cards'])} cards, in prompt order")
    row = note(ws, row, "Texts below are the exact retrieval_text values supplied to the experiment. OCR wording and numbers are preserved; \u005cuNNNN displays otherwise unrenderable control characters.")
    for a, b, title in [(0, 0, "Card / source"), (1, 7, "Full evidence text")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 37)
    row += 1
    card_rows = {}
    full_card_checks = []
    for card in p["evidence_cards"]:
        eid = card["evidence_id"]
        card_rows[eid] = row
        parts = chunks(card["retrieval_text"])
        part_cells = []
        for n, part in enumerate(parts, 1):
            tag = card["prompt_label"] + (f"\nPart {n}/{len(parts)}" if len(parts) > 1 else "") + "\n" + location(card)
            put(ws, row, 0, 0, tag, "label")
            put(ws, row, 1, 7, part, source="full_evidence_text")
            height(ws, row, [(0, 0, tag), (1, 7, part)])
            part_cells.append((row + 1, 2))
            ws.write_comment(row, 0, json.dumps({k: card.get(k) for k in ["evidence_id", "source_file", "source_year", "page_start", "page_end", "source_label", "retrieval_text_hash"]}, ensure_ascii=False, indent=2), {"author": "Saved evidence source", "x_scale": 2, "y_scale": 2})
            row += 1
        full_card_checks.append({"evidence_id": eid, "cells": part_cells, "expected": visible(card["retrieval_text"])})
        put(ws, row, 0, 0, "Source", "note")
        put(ws, row, 1, 7, card["source_label"], "note", source="evidence_source_label")
        height(ws, row, [(1, 7, card["source_label"])], minimum=22)
        row += 1
    result_section = row
    row = section(ws, row, "3  |  Results — three support prompts")
    put(ws, row, 0, 1, "Target DC", "label")
    put(ws, row, 2, 7, p["target_dc"]["dc_text"], source="fixed_bace_dc")
    height(ws, row, [(2, 7, p["target_dc"]["dc_text"])])
    row += 1
    for a, b, title in [(0, 1, "Condition"), (2, 2, "Decision"), (3, 7, "Actual saved support sets (EC aliases above)")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 30)
    row += 1
    for condition in ("original", *VARIANTS):
        supported = bool(p["support"]["support_sets"]) if condition == "original" else p["prompt_variants"][condition]["supported"]
        label = "Supported" if supported else "Unsupported"
        text = saved_support(p, condition)
        put(ws, row, 0, 1, VARIANT_LABELS[condition], "label")
        put(ws, row, 2, 2, label, label, source=condition + "_verdict")
        put(ws, row, 3, 7, text, source=condition + "_support_sets_display")
        record = p["support"] if condition == "original" else p["prompt_variants"][condition]
        ws.write_comment(row, 3, json.dumps(record, ensure_ascii=False, indent=2), {"author": "Verified saved record", "x_scale": 2, "y_scale": 2})
        height(ws, row, [(0, 1, VARIANT_LABELS[condition]), (3, 7, text)], minimum=42)
        row += 1
    row = note(ws, row, "The adapted runs saved support sets only: no textual rationale and no new unsupported diagnosis. The original BACE reason below belongs to the original run.")
    if not p["candidate_ecs"]:
        assert all(not p["prompt_variants"][c]["model_called"] for c in VARIANTS)
        row = note(ws, row, "Both adapted conditions are deterministic unsupported for this empty candidate list; no model call was made.", warning=True)
    else:
        changed = [VARIANT_LABELS[c] for c in VARIANTS if p["prompt_variants"][c]["supported"] != bool(p["support"]["support_sets"])]
        row = note(ws, row, "Decision changes relative to original BACE: " + (", ".join(changed) if changed else "none") + ".", warning=bool(changed))
    row = section(ws, row, "3.1  |  Results — original BACE and native frameworks")
    for a, b, title in [(0, 0, "Framework"), (1, 1, "Decision"), (2, 4, "Native claim"), (5, 7, "Saved reason / support record")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 32)
    row += 1
    bace_rationale = p["diagnosis"]["rationale"] if p["diagnosis"] else "No textual rationale recorded; see the saved support set(s) below."
    rc_counts = Counter(p["native"]["ragchecker"]["evidence_verdicts"].values())
    rc_reason = "No textual rationale recorded.\n" + "\n".join(f"{label}: {rc_counts[label]} evidence card(s)" for label in ["Entailment", "Neutral", "Contradiction"] if rc_counts[label]) + "\nPer-card labels are listed in the results section below."
    judge_rows = [
        ("BACE", bool(p["support"]["support_sets"]), p["target_dc"]["dc_text"], bace_rationale),
        ("RAGAS", p["native"]["ragas"]["supported"], p["native"]["ragas"]["claim"], p["native"]["ragas"]["reason"]),
        ("RAGChecker", p["native"]["ragchecker"]["supported"], rc_triple(p["native"]["ragchecker"]["claim"]), rc_reason),
    ]
    for name, supported, claim, reason in judge_rows:
        label = "Supported" if supported else "Unsupported"
        put(ws, row, 0, 0, name, "label")
        put(ws, row, 1, 1, label, label, source=f"{name}_verdict")
        put(ws, row, 2, 4, claim, source=f"{name}_native_claim")
        put(ws, row, 5, 7, reason, source=f"{name}_saved_reason" if name == "RAGAS" or (name == "BACE" and p["diagnosis"]) else None)
        ws.write_comment(row, 0, json.dumps(p["target_dc"]["dc_id"] if name == "BACE" else p["native"][name.lower()], ensure_ascii=False, indent=2), {"author": "Saved source record", "x_scale": 2, "y_scale": 2})
        height(ws, row, [(2, 4, claim), (5, 7, reason)], minimum=60)
        row += 1
    type_label = p["diagnosis"]["unsupported_label"] if p["diagnosis"] else s["bace_label"]
    put(ws, row, 0, 1, "BACE saved label", "label")
    put(ws, row, 2, 7, type_label, source="bace_label")
    ws.set_row(row, 27)
    row += 1
    support_text = saved_support(p)
    put(ws, row, 0, 1, "BACE support sets", "label")
    put(ws, row, 2, 7, support_text)
    ws.write_comment(row, 2, json.dumps(p["support"], ensure_ascii=False, indent=2), {"author": "Saved support record"})
    height(ws, row, [(2, 7, support_text)])
    row += 1
    if p["diagnosis"]:
        row = note(ws, row, "BACE's reason above is the saved unsupported-diagnosis rationale, produced after the support decision.")
    judgment_end = row
    row = section(ws, row, "Results  |  Candidate EC use in saved support sets")
    row = note(ws, row, "Click an EC alias to revisit its exact candidate text. Membership below is copied from the saved support sets.")
    for a, b, title in [(0, 0, "Candidate EC"), (1, 7, "Saved support-set membership")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 30)
    row += 1
    if not p["candidate_ecs"]:
        row = note(ws, row, "No candidate ECs: the saved candidate list is empty.")
    for ec in p["candidate_ecs"]:
        alias = p["aliases"][ec["ec_id"]]
        membership = ec_usage[ec["ec_id"]]
        link(ws, row, 0, 0, alias, rid, ec_row_map[ec["ec_id"]])
        put(ws, row, 1, 7, membership, source="saved_ec_membership_display")
        height(ws, row, [(1, 7, membership)])
        row += 1
    row = section(ws, row, "Results  |  RAGChecker per-evidence labels")
    row = note(ws, row, "These are the saved native RAGChecker labels for its claim shown above. Click a card to revisit the full evidence.")
    for a, b, title in [(0, 1, "Evidence card"), (2, 3, "Saved label"), (4, 7, "Source locator")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 30)
    row += 1
    for card in p["evidence_cards"]:
        eid = card["evidence_id"]
        label = p["native"]["ragchecker"]["evidence_verdicts"][eid]
        link(ws, row, 0, 1, card["prompt_label"], rid, card_rows[eid])
        put(ws, row, 2, 3, label, label, source="ragchecker_evidence_verdict")
        put(ws, row, 4, 7, location(card))
        height(ws, row, [(4, 7, location(card))])
        row += 1
    row = note(ws, row, "Source IDs and hashes are available in cell notes and the Source map sheet. No new human adjudication is asserted in this workbook.")
    link(ws, row, 0, 3, "Back to Cases", "Cases", i + 5)
    link(ws, row, 4, 7, "Back to this case's results", rid, result_section)
    ws.print_area(0, 0, row, 7)
    link(ws, 2, 2, 3, "Disclosure", rid, 4)
    link(ws, 2, 4, 5, "Evidence and ECs", rid, excerpt_section)
    link(ws, 2, 6, 7, "Results", rid, result_section)
    for rr, eid in excerpt_links:
        card = ec_cards[eid]
        link(ws, rr, 0, 1, card["prompt_label"] + "\n" + location(card), rid, card_rows[eid])
    for rr, eid, label in ec_links:
        link(ws, rr, 6, 7, label, rid, card_rows[eid])
    rr = i + 5
    overview.set_row(rr, 64)
    link(overview, rr, 0, 0, rid, rid, 0)
    overview.write_string(rr, 1, company, F["body"])
    overview.write_string(rr, 2, f"{s['year']}\n{s['task']}", F["body"])
    overview.write_string(rr, 3, p["target_dc"]["dc_text"], F["body"])
    display_verdicts = (EXPECTED_VERDICTS[rid][0], p["prompt_variants"]["ragas_style"]["supported"], p["prompt_variants"]["ragchecker_style"]["supported"], *EXPECTED_VERDICTS[rid][1:])
    for j, supported in enumerate(display_verdicts, 4):
        decision = "Supported" if supported else "Unsupported"
        overview.write_string(rr, j, decision, F[decision])
    CASE_META.append({"review_id": rid, "generation_case_id": s["generation_case_id"],
                      "bace_dc_id": s["bace_dc_id"], "native_claim_indices": {f: p["native"][f]["claim_index"] for f in ("ragas", "ragchecker")},
                      "verdicts": display_verdicts, "candidate_ec_count": len(p["candidate_ecs"]),
                      "prompt_variants": p["prompt_variants"],
                      "evidence_card_count": len(p["evidence_cards"]), "support_sets": p["support"]["support_sets"],
                      "ec_aliases": p["aliases"], "judgment_end_row": judgment_end,
                      "candidate_section_row": candidate_section + 1, "evidence_section_row": evidence_section + 1,
                      "disclosure_section_row": disclosure_section + 1, "excerpt_section_row": excerpt_section + 1, "result_section_row": result_section + 1,
                      "full_evidence_checks": full_card_checks, "disclosure_cells": disclosure_cells,
                      "disclosure_expected": visible(p["generated_text"])})

overview.repeat_rows(0, 4)
overview.print_area(0, 0, 22, 8)
overview.fit_to_pages(1, 2)
gap = wb.add_worksheet("Gap summary")
config(gap)
put(gap, 0, 0, 7, "Support rates and remaining native score gaps", "title")
gap.set_row(0, 38)
put(gap, 1, 0, 7, "1,796 matched disclosures | 30 companies | 94,854 BACE claims | Saved prompt experiment completed 2 October 2026", "note")
gap.set_row(1, 28)
link(gap, 2, 0, 3, "Open the same 18 review cases", "Cases", 0)
link(gap, 2, 4, 7, "Definitions and source information", "About", 0)
gap.set_row(2, 27)
row = note(gap, 3, "Gap = native framework score minus BACE-condition support rate. All means give equal weight to each of the same 1,796 disclosures.")
for scope, title in (("all_claims", "1  |  All BACE claims — primary comparison"),
                     ("excluding_original_boundary", "2  |  Excluding original-BACE factual boundary distortion claims")):
    row = section(gap, row, title)
    values = GAPS[scope]
    native = GAPS["all_claims"]["mean_support_percent"]
    row = note(gap, row, f"Native reference scores on this same cohort: RAGAS {native['ragas_native']:.2f}%; RAGChecker {native['ragchecker_native']:.2f}%.")
    for a, b, label in [(0, 2, "BACE condition"), (3, 3, "Support rate (%)"), (4, 5, "Gap to RAGAS native (pp)"), (6, 7, "Gap to RAGChecker native (pp)")]:
        put(gap, row, a, b, label, "head")
    gap.set_row(row, 36)
    row += 1
    for condition in ("original", *VARIANTS):
        put(gap, row, 0, 2, VARIANT_LABELS[condition], "label")
        put(gap, row, 3, 3, f"{values['mean_support_percent'][condition]:.2f}", source=scope + "_support_percent")
        put(gap, row, 4, 5, f"{values['native_minus_bace_gap_pp'][condition]['ragas']:.2f}", source=scope + "_gap_to_ragas_pp")
        put(gap, row, 6, 7, f"{values['native_minus_bace_gap_pp'][condition]['ragchecker']:.2f}", source=scope + "_gap_to_ragchecker_pp")
        gap.set_row(row, 32)
        row += 1
    if scope == "all_claims":
        effects = {e["condition"]: e for e in GAPS["saved_prompt_effects"]}
        for c in VARIANTS:
            e = effects[c]
            row = note(gap, row, f"{VARIANT_LABELS[c]} minus original BACE: +{float(e['estimate'])*100:.2f} pp (saved 95% company-cluster interval +{float(e['low'])*100:.2f} to +{float(e['high'])*100:.2f} pp).")
    else:
        row = note(gap, row, f"The same {GAPS['original_boundary_claim_count']:,} DCs labelled factual_boundary_distortion by original BACE are removed from each BACE condition's numerator and denominator; {GAPS['remaining_claim_count_excluding_original_boundary']:,} DCs remain. Native claim inventories are unchanged.", warning=True)
row = section(gap, row, "3  |  What changed in these 18 existing cases")
for c in VARIANTS:
    ids = GAPS["changed_selected_cases"][c]
    row = note(gap, row, f"{VARIANT_LABELS[c]}: {len(ids)}/18 binary decisions changed: {', '.join(ids)}. All of these changes are unsupported to supported.")
row = note(gap, row, "All 18 source cases and candidate EC lists are retained. These illustrative cases were not selected as a representative sample of the prompt experiment.")
row = section(gap, row, "4  |  Scope and missingness")
for text in [
    "Three failed condition-level records affect two disclosures. Those entire disclosures are excluded from every mean above; failed outputs are not treated as unsupported.",
    "The adapted conditions change support instructions within BACE while holding DCs, candidate ECs and other frozen inputs fixed. They are not native RAGAS or RAGChecker reruns.",
    "A smaller score gap does not establish greater accuracy or identify the fraction of the native gap caused by prompts. Native claim inventories and evidence interfaces differ.",
    "Rates and gaps are recomputed from saved paired records. Effect intervals above are verified saved estimates (2,000 company bootstrap draws, seed 20260921). No new significance test or interval is used for the descriptive native gaps.",
]:
    row = note(gap, row, text)
gap.print_area(0, 0, row - 1, 7)

about = wb.add_worksheet("About")
config(about)
put(about, 0, 0, 7, "How to read this workbook", "title")
about.set_row(0, 38)
link(about, 2, 0, 3, "Open case overview", "Cases", 0)
row = 4
notes = [
    ("Reading order", "Updated 2026-10-22: disclosure passages, native claims and full disclosure come first; evidence excerpts, candidate ECs and all supplied cards come next; decisions, reasons, support-set membership and per-card verdicts come last."),
    ("Start", "The Cases sheet is a filterable overview of the same R01-R18 examples. Each case follows Disclosure, Evidence, then Results. Gap summary compares the saved results on the same complete cohort; case navigation stays visible when scrolling."),
    ("What is shown", "The disclosure passages, all candidate ECs, all supplied evidence cards, native claims and saved framework decisions are taken from existing artifacts. Selected evidence excerpts help locate the discussion; the full cards follow in prompt order."),
    ("BACE reasons", "For unsupported claims, the displayed reason is the saved diagnosis rationale from the stage after the support decision. Supported claims have no saved prose reason: the workbook displays the actual direct/inferred support sets, with local EC aliases."),
    ("Adapted prompts", "BACE–RAGAS-style and BACE–RAGChecker-style reuse the exact BACE claim and candidate EC input. Their outputs contain only support sets, with no textual rationale or new diagnosis. Original BACE diagnosis reasons are retained as original-run records, not attributed to the adapted runs. Empty-candidate jobs are deterministic unsupported with no model call."),
    ("RAGAS / RAGChecker", "RAGAS includes its saved textual reason. RAGChecker stores a subject-relation-object triple and per-card categorical labels; no prose reason is invented. The triple components are displayed separately. Per-card labels are listed in the Results section after all source evidence."),
    ("Claim correspondence", "The original 18 review examples paired BACE with one comparator. Corresponding claims from the third framework have been retrieved from its saved output. Native wording is preserved; these are not necessarily identical propositions. Prominent wording differences are flagged on the case pages."),
    ("Evidence boundary", "Evidence means the exact text supplied to this experiment, not the full company report. Support decisions are not independently established correctness, external truth or legal compliance. This workbook adds no human adjudication."),
    ("Display conventions", "EC01, EC02, ... are local aliases; cell notes retain original EC IDs and sources. Long evidence/disclosure text is split across consecutive rows without omissions. XML-incompatible control characters are displayed as literal \\uNNNN tokens; all other source text, including OCR artifacts, is preserved. Soft hyphens are removed only from display company names."),
    ("Source verification", "Packet hashes and raw main_v1 files were checked against their saved ledgers. Both full raw prompt-output files were hashed and every paired binary verdict was reconciled with the saved tables; all 18 target inputs and support sets were compared with frozen jobs and raw outputs. Source cells, long text and links were checked after export. The hidden Source map sheet retains paths and hashes."),
    ("Prepared", "2026-10-22. This is a new workbook for the existing 18 cases, adding the completed prompt-sensitivity results. The earlier Excel workbook and all experiment artifacts remain unchanged."),
]
for label, content in notes:
    put(about, row, 0, 1, label, "label")
    put(about, row, 2, 7, content)
    height(about, row, [(2, 7, content)], minimum=42)
    row += 1
about.print_area(0, 0, row - 1, 7)

sources = wb.add_worksheet("Source map")
sources.hide_gridlines(2)
sources.set_tab_color("#A8BBC3")
sources.set_column("A:A", 110)
sources.set_column("B:B", 70)
sources.freeze_panes(1, 0)
sources.write_row(0, 0, ["Input path (relative to project root)", "SHA-256"], F["head"])
for rr, (path, sha) in enumerate(sorted(INPUTS.items()), 1):
    sources.write_string(rr, 0, path, F["body"])
    sources.write_string(rr, 1, sha, F["body"])
    sources.set_row(rr, 50)
sources.autofilter(0, 0, len(INPUTS), 1)
sources.hide()
overview.activate()
overview.set_first_sheet()
wb.close()

# Verify exported values, all complete long texts, native decisions and navigation.
check = openpyxl.load_workbook(XLSX, data_only=False)
for cell in SOURCE_CELLS:
    assert check[cell["sheet"]].cell(cell["row"], cell["col"]).value == cell["value"], cell
for case in CASE_META:
    sheet = check[case["review_id"]]
    for card in case["full_evidence_checks"]:
        assert "".join(sheet.cell(r, c).value or "" for r, c in card["cells"]) == card["expected"]
    assert "".join(sheet.cell(r, c).value or "" for r, c in case["disclosure_cells"]) == case["disclosure_expected"]
for sheet, row, col, target, target_row in LINKS:
    assert check[sheet].cell(row, col).hyperlink is not None
    assert check[target].cell(target_row, 1).value is not None
assert len(check["Cases"].tables) == 1
assert len(CASE_META) == 18
assert all(c.data_type != "f" for sheet in check for row in sheet for c in row)
for sheet in check:
    assert all((dim.height or 22) <= 409 for dim in sheet.row_dimensions.values())

manifest = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "workbook": XLSX.name, "workbook_sha256": digest(XLSX.read_bytes()),
    "script_sha256": digest(Path(__file__).read_bytes()),
    "input_sha256": INPUTS,
    "case_count": len(CASES), "evidence_card_rows_by_case": {x["review_id"]: len(x["evidence_cards"]) for x in CASES},
    "candidate_ec_rows_by_case": {x["review_id"]: len(x["candidate_ecs"]) for x in CASES},
    "verified_source_cells": len(SOURCE_CELLS), "verified_internal_links": len(LINKS),
    "display_transformations": TRANSFORMATIONS,
    "cases": [{k: v for k, v in x.items() if k not in ("full_evidence_checks", "disclosure_expected")} for x in CASE_META],
    "validation": {"packet_hashes": "passed", "frozen_input_hashes": "passed", "packet_raw_equality": "passed",
                   "exported_source_cells": "passed", "complete_evidence_and_disclosures": "passed", "native_verdicts": "passed",
                   "internal_links": "passed", "no_formulas": "passed"},
    "external_model_calls": 0, "new_human_adjudications": 0,
    "reproduction_command": "/home/muwang/.local/share/bace-writing-skills/venv/bin/python " + str(Path(__file__).relative_to(ROOT)),
}
(OUT / "export_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"workbook": str(XLSX), "size_bytes": XLSX.stat().st_size, "cases": len(CASES),
                  "evidence_cards_across_cases": sum(len(p["evidence_cards"]) for p in CASES),
                  "candidate_ecs_across_cases": sum(len(p["candidate_ecs"]) for p in CASES),
                  "verified_source_cells": len(SOURCE_CELLS), "verified_links": len(LINKS),
                  "control_character_cells": len(TRANSFORMATIONS)}, indent=2))
