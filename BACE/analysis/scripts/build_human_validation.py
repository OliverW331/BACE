# /// script
# requires-python = ">=3.11"
# dependencies = ["XlsxWriter==3.2.5", "openpyxl==3.1.5"]
# ///
"""Build two blinded 600-claim packets from receipt-verified BACE call inputs.

Run with the separate validation-export environment. Never overwrites a
published reviewer file. Private files must not be distributed to reviewers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unicodedata
import zipfile

import openpyxl
from openpyxl.utils.escape import unescape
import xlsxwriter

ANALYSIS = Path(__file__).resolve().parents[1]
BACE = ANALYSIS.parent
ROOT = BACE.parent
RUN = BACE / "results/main_v1"
DEST = ANALYSIS / "validation"
PRIVATE = DEST / "_private"
STAGING = PRIVATE / ".building"
SEED = "bace-human-validation-v1-20260924"
PRIMARY_N = 400
SUPPLEMENT_N = 200
SUPPORT = ["Supported", "Supported by inference", "Unsupported"]
DIAGNOSES = [
    "non_disclosure_statement", "contradiction", "evidence_conflation",
    "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty",
]
HEADERS = [
    "Sample ID", "Company name", "Reporting year", "Target DC", "Candidate ECs",
    "Human support label", "Human unsupported type",
]
WIDTHS = [12, 19, 11, 55, 90, 24, 31]
SOURCES: dict[str, str] = {}
SOURCE_STATS: dict[str, tuple[int, int]] = {}


def digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def remember(path, actual, before, expected=None):
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), path
    if expected is not None:
        assert actual == expected, f"Source receipt mismatch: {path}"
    key = path.relative_to(ROOT).as_posix()
    if key in SOURCES:
        assert SOURCES[key] == actual, f"Source changed: {path}"
    SOURCES[key] = actual
    SOURCE_STATS[key] = (after.st_size, after.st_mtime_ns)


def read_json(path, expected=None):
    before = path.stat()
    raw = path.read_bytes()
    remember(path, hashlib.sha256(raw).hexdigest(), before, expected)
    return json.loads(raw)


def read_rows(path, expected=None, wanted=None):
    before, h, out = path.stat(), hashlib.sha256(), []
    with path.open("rb") as stream:
        for line in stream:
            h.update(line)
            if line.strip():
                row = json.loads(line)
                if wanted is None or row.get("dc_id") in wanted:
                    out.append(row)
    remember(path, h.hexdigest(), before, expected)
    return out


def stage_rows(cid, receipts, stage, name, wanted=None):
    path = RUN / "cases" / cid / "bace" / stage / name
    expected = receipts[stage]["artifacts"][path.relative_to(BACE).as_posix()]
    return read_rows(path, expected, wanted)


def keyed(rows, field):
    result = {r[field]: r for r in rows}
    assert len(result) == len(rows), f"Duplicate {field}"
    return result


def support_label(record):
    sets = record["support_sets"]
    if not sets:
        return "Unsupported"
    assert all(s["support_type"] in ("direct", "inferred") for s in sets)
    return "Supported" if any(s["support_type"] == "direct" for s in sets) else "Supported by inference"


def rank(purpose, key):
    return hashlib.sha256(f"{SEED}|{purpose}|{key[0]}|{key[1]}".encode()).hexdigest()


def proportional_quotas(counts, total, labels):
    ideals = {label: Fraction(counts[label] * total, sum(counts.values())) for label in labels}
    quotas = {label: int(ideals[label]) for label in labels}
    for label in sorted(labels, key=lambda k: (-(ideals[k] - quotas[k]), labels.index(k)))[
        :total - sum(quotas.values())
    ]:
        quotas[label] += 1
    return quotas


def collect_frame():
    execution = read_json(RUN / "execution_status.json")
    assert not execution.get("active_cases") and execution["status"] not in ("running", "finalizing")
    manifest = read_json(RUN / "manifest.json")
    freeze = read_json(BACE / "config/freeze.json", manifest["freeze_sha256"])
    for name, expected in freeze["files"].items():
        path = BACE / name
        before = path.stat()
        remember(path, file_sha(path), before, expected)

    # Bind company/year to the original generation inputs without retaining all
    # repeated evidence texts in memory.
    path = BACE / "evidence/inputs/generation_cases.jsonl"
    before, h, metadata = path.stat(), hashlib.sha256(), {}
    with path.open("rb") as stream:
        for line in stream:
            h.update(line)
            if not line.strip():
                continue
            row = json.loads(line)
            cid = row["generation_case_id"]
            assert cid not in metadata
            metadata[cid] = {
                "company_name": row["company_name"],
                "target_reporting_year": row["target_reporting_year"],
                "task_id": row["task_id"],
                "generation_case_sha256": digest(row),
            }
    remember(path, h.hexdigest(), before, manifest["generation_input_sha256"])
    assert set(metadata) == set(manifest["case_ids"])

    frame, cases, excluded = {}, {}, []
    for i, cid in enumerate(manifest["case_ids"], 1):
        state = read_json(RUN / "cases" / cid / "state.json")
        receipts = state["stages"]
        if not all(s in receipts for s in ("generation", "dedup", "candidates", "support", "diagnosis")):
            excluded.append(cid)
            continue
        supports = keyed(stage_rows(cid, receipts, "support", "dc_support_sets.jsonl"), "dc_claim_id")
        diagnoses = keyed(stage_rows(cid, receipts, "diagnosis", "dc_unsupported_diagnoses.jsonl"), "dc_claim_id")
        assert set(diagnoses) == {did for did, r in supports.items() if not r["support_sets"]}
        cases[cid] = {"receipts": receipts, "metadata": metadata[cid]}
        for did, record in supports.items():
            diag = diagnoses.get(did)
            if diag:
                assert diag["unsupported_label"] in DIAGNOSES
            frame[cid, did] = {
                "support_label": support_label(record),
                "diagnosis": diag["unsupported_label"] if diag else None,
            }
        if i % 300 == 0:
            print(f"Verified sampling frame: {i}/{len(manifest['case_ids'])} cases", flush=True)
    assert len(cases) == 1798 and len(frame) == 94955
    return frame, cases, excluded


def sample(frame):
    pools = {label: sorted(k for k, v in frame.items() if v["support_label"] == label) for label in SUPPORT}
    populations = {label: len(pool) for label, pool in pools.items()}
    quotas = proportional_quotas(populations, PRIMARY_N, SUPPORT)
    main = set()
    for label in SUPPORT:
        main.update(sorted(pools[label], key=lambda k: rank("primary", k))[:quotas[label]])
    main_diagnoses = Counter(frame[k]["diagnosis"] for k in main if frame[k]["diagnosis"])
    diagnosis_population = Counter(v["diagnosis"] for v in frame.values() if v["diagnosis"])
    remaining = {label: sorted(k for k, v in frame.items() if v["diagnosis"] == label and k not in main) for label in DIAGNOSES}

    # Balance the resulting diagnosis counts, without inspecting human labels.
    # Cap contradiction at 40 total to leave rare units for separate calibration.
    caps = {label: diagnosis_population[label] for label in DIAGNOSES}
    caps["contradiction"] = max(main_diagnoses["contradiction"], min(40, caps["contradiction"]))
    extra_quotas = {label: 0 for label in DIAGNOSES}
    for _ in range(SUPPLEMENT_N):
        eligible = [label for label in DIAGNOSES if (
            extra_quotas[label] < len(remaining[label]) and
            main_diagnoses[label] + extra_quotas[label] < caps[label]
        )]
        assert eligible
        label = min(eligible, key=lambda k: (main_diagnoses[k] + extra_quotas[k], DIAGNOSES.index(k)))
        extra_quotas[label] += 1
    extra = set()
    for label in DIAGNOSES:
        extra.update(sorted(remaining[label], key=lambda k: rank("supplement", k))[:extra_quotas[label]])
    assert len(main) == PRIMARY_N and len(extra) == SUPPLEMENT_N and not main & extra
    selected = sorted(main | extra, key=lambda k: rank("review-order", k))
    design = {
        "seed": SEED, "primary_n": PRIMARY_N, "supplement_n": SUPPLEMENT_N,
        "primary_method": "Proportional allocation by automated support label using largest remainders; seeded SHA-256 ranking without replacement within each stratum.",
        "supplement_method": "Given the primary sample, repeatedly allocate one slot to the least represented automated diagnosis, tie-breaking in frozen diagnosis order. Cap total contradiction units at 40 to retain calibration-eligible units. Uniform seeded ranking within the remaining diagnosis pool.",
        "presentation_order": "Independent seeded SHA-256 ranking across all 600 selected units; group membership is private.",
        "support_population": populations, "primary_support_quotas": quotas,
        "diagnosis_population": dict(diagnosis_population),
        "primary_diagnosis_counts": dict(main_diagnoses),
        "supplement_diagnosis_quotas": extra_quotas,
        "remaining_diagnosis_populations": {k: len(v) for k, v in remaining.items()},
        "diagnosis_total_caps": caps,
        "calibration": "Not conducted or generated. Future calibration must use units outside these 600; at least two automated contradictions remain available.",
        "estimand": "Primary: claim-level agreement within the completed frozen BACE DC inventory, conditional on original candidate EC inputs.",
        "analysis_rule": "Use the 400 primary units and their stratum weights for overall estimates. Supplement inclusion probabilities are conditional on the realized primary sample; do not treat all 600 as an unweighted representative sample or these probabilities as unconditional union probabilities.",
    }
    print("Sampling design: " + json.dumps(design, ensure_ascii=False), flush=True)
    return selected, main, design


def find_call(rows, did, expected):
    matching = [r for r in rows if r["dc_id"] == did and r.get("call_status") == "success"
                and r.get("output_valid") is True and r.get("restored_output") == expected]
    assert matching, f"No receipt-bound successful call matching output: {did}"
    hashes = {digest(r["dynamic_input"]) for r in matching}
    assert len(hashes) == 1, f"Different successful inputs: {did}"
    call = matching[-1]
    assert digest(call["dynamic_input"]) == call["call_identity"]["job_input_hash"]
    return call


def recover_inputs(selected, main, design, frame, cases):
    by_case = defaultdict(set)
    for cid, did in selected:
        by_case[cid].add(did)
    recovered = {}
    for i, (cid, wanted) in enumerate(sorted(by_case.items()), 1):
        receipts = cases[cid]["receipts"]
        ec_rows = stage_rows(cid, receipts, "dedup", "ec_claims.jsonl")
        dc_rows = stage_rows(cid, receipts, "dedup", "dc_claims.jsonl")
        ecs, dcs = keyed(ec_rows, "ec_id"), keyed(dc_rows, "dc_id")
        candidates = keyed(stage_rows(cid, receipts, "candidates", "dc_candidate_ecs.jsonl"), "dc_claim_id")
        supports = keyed(stage_rows(cid, receipts, "support", "dc_support_sets.jsonl"), "dc_claim_id")
        diagnoses = keyed(stage_rows(cid, receipts, "diagnosis", "dc_unsupported_diagnoses.jsonl"), "dc_claim_id")
        assert set(candidates) == set(supports) == set(dcs)
        scalls = stage_rows(cid, receipts, "support", "claim_support_calls.jsonl", wanted)
        dcalls = stage_rows(cid, receipts, "diagnosis", "claim_unsupported_diagnosis_calls.jsonl", wanted)
        for did in wanted:
            call = find_call(scalls, did, supports[did])
            dynamic = call["dynamic_input"]
            assert set(dynamic) == {"context_metadata", "dc_claim", "ec_claims"}
            assert dynamic["context_metadata"] == {
                k: cases[cid]["metadata"][k] for k in ("company_name", "target_reporting_year")
            }
            assert dynamic["dc_claim"] == {"dc_claim_id": call["dc_temporary_id"], "dc_text": dcs[did]["dc_text"]}
            aliases = call["ec_temporary_id_map"]
            expected_ids = candidates[did]["candidate_ec_ids"]
            original_ids = [aliases[ec["ec_claim_id"]] for ec in dynamic["ec_claims"]]
            assert len(original_ids) == len(set(original_ids))
            assert set(original_ids) == set(expected_ids)
            assert original_ids == call["candidate_ec_ids"]
            for ec in dynamic["ec_claims"]:
                assert set(ec) == {"ec_claim_id", "ec_text"}
                assert ec["ec_text"] == ecs[aliases[ec["ec_claim_id"]]]["ec_text"]
            diag_call = None
            if did in diagnoses:
                diag_call = find_call(dcalls, did, diagnoses[did])
                assert diag_call["dynamic_input"] == dynamic, f"Support/diagnosis input difference: {cid}/{did}"
            assert bool(call["model_called"]) == bool(dynamic["ec_claims"])
            label, diagnosis = frame[cid, did]["support_label"], frame[cid, did]["diagnosis"]
            group = "primary" if (cid, did) in main else "diagnosis_supplement"
            p_primary = Fraction(design["primary_support_quotas"][label], design["support_population"][label])
            supplement_p = None
            if group == "diagnosis_supplement":
                supplement_p = Fraction(design["supplement_diagnosis_quotas"][diagnosis], design["remaining_diagnosis_populations"][diagnosis])
            recovered[cid, did] = {
                "generation_case_id": cid, "dc_id": did, "group": group,
                "task_id": cases[cid]["metadata"]["task_id"],
                "automated_support_label": label, "automated_diagnosis": diagnosis,
                "automated_support_sets": supports[did]["support_sets"],
                "unedited_automatic_rationale": diagnoses[did]["rationale"] if did in diagnoses else None,
                "dynamic_input": dynamic, "input_sha256": digest(dynamic),
                "support_call_id": call["call_id"], "support_model_called": call["model_called"],
                "diagnosis_call_id": diag_call["call_id"] if diag_call else None,
                "diagnosis_model_called": diag_call["model_called"] if diag_call else None,
                "same_support_diagnosis_input_verified": True if diag_call else None,
                "primary_inclusion_probability": float(p_primary),
                "primary_probability_fraction": str(p_primary),
                "primary_analysis_weight": float(1 / p_primary) if group == "primary" else None,
                "supplement_probability_conditional_on_primary": float(supplement_p) if supplement_p else None,
                "supplement_conditional_probability_fraction": str(supplement_p) if supplement_p else None,
            }
        if i % 75 == 0 or i == len(by_case):
            print(f"Recovered and cross-checked exact inputs: {i}/{len(by_case)} cases; {len(recovered)}/600 claims", flush=True)
    return [dict(sample_id=f"HV-{i:04d}", **recovered[k]) for i, k in enumerate(selected, 1)]


def visual_lines(text, width):
    lines = []
    # Count explicit line breaks conservatively. Whitespace and all characters
    # remain unchanged in the workbook; this function only estimates row height.
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        units = sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 4 if c == "\t" else 1 for c in line)
        lines.append(max(1, math.ceil(units / width)))
    return sum(lines)


def display_values(record):
    data = record["dynamic_input"]
    target = data["dc_claim"]["dc_claim_id"] + "\n" + data["dc_claim"]["dc_text"]
    evidence = "\n\n".join(e["ec_claim_id"] + "\n" + e["ec_text"] for e in data["ec_claims"])
    if not data["ec_claims"]:
        evidence = "No candidate ECs supplied"
    return [record["sample_id"], data["context_metadata"]["company_name"], data["context_metadata"]["target_reporting_year"], target, evidence]


def layout_records(records):
    """One sample per row; the entire candidate set occupies exactly one cell."""
    rows, mapping = [], []
    for record in records:
        values = display_values(record)
        start = len(rows) + 2
        cells = values + [None, None]
        for value in cells:
            if isinstance(value, str):
                assert len(value.encode("utf-16-le")) // 2 <= 32767, (
                    "Complete candidate sets must fit in one Excel cell; never truncate or split them",
                    record["sample_id"],
                )
        line_count = max(visual_lines(values[3], 46), visual_lines(values[4], 78), visual_lines(values[1], 16))
        # Excel caps row height. Full long-cell text remains available in the
        # expanded formula bar; display height must never change cell contents.
        height = min(409, max(70, line_count * 15 + 16))
        rows.append({"values": cells, "height": height, "annotation": True, "start": start, "last": True})
        mapping.append({"sample_id": record["sample_id"], "annotation_row": start, "last_material_row": start, "material_rows": 1})
    assert len(rows) == len(records) == len({r["sample_id"] for r in records})
    return rows, mapping


def write_workbook(path, records, reviewer, preview=False):
    rows, mapping = layout_records(records)
    workbook = xlsxwriter.Workbook(path, {"constant_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    workbook.set_properties({
        "title": "Claim review", "subject": "Independent classification of supplied claims",
        "author": "BACE", "comments": "Read README.md before annotating. Complete the coloured cells once per Sample ID.",
        "created": datetime(2026, 9, 24), "keywords": f"Reviewer {reviewer}",
    })
    sheet = workbook.add_worksheet("Claim_review")
    sheet.freeze_panes(1, 3)
    sheet.hide_gridlines(2)
    sheet.set_zoom(80)
    base = {"font_name": "Arial", "font_size": 10, "valign": "top", "text_wrap": True}
    def fmt(**extra):
        return workbook.add_format({**base, **extra})
    boundary = {"top": 1, "top_color": "#B4C8D8"}
    source = fmt(bg_color="#F7FAFD")
    source_start = fmt(bg_color="#F7FAFD", **boundary)
    year = fmt(bg_color="#F7FAFD", align="center", num_format="0")
    year_start = fmt(bg_color="#F7FAFD", align="center", num_format="0", **boundary)
    sample = fmt(bg_color="#EAF2F8", font_color="#285675", bold=True, **boundary)
    sample_link = fmt(bg_color="#EAF2F8", font_color="#285675", underline=1)
    label_input = fmt(bg_color="#E2F2E9", locked=False, bottom=1, bottom_color="#B4C8D8", **boundary)
    diagnosis_input = fmt(bg_color="#FFF0DF", locked=False, bottom=1, bottom_color="#B4C8D8", **boundary)
    continuation = fmt(bg_color="#F2F4F6", font_color="#75818B")
    bad = fmt(bg_color="#F8D9D7", font_color="#802B25")
    pending = fmt(bg_color="#FBE2B8")
    headers = [fmt(bold=True, valign="vcenter", bg_color=color, font_color="#203441", bottom=1, bottom_color="#B4C8D8")
               for color in ("#7AAED6", "#7AAED6", "#7AAED6", "#7AAED6", "#7AAED6", "#83C5A3", "#F3B27A")]
    for col, width in enumerate(WIDTHS):
        sheet.set_column(col, col, width)
        sheet.write_string(0, col, HEADERS[col], headers[col])
    sheet.set_row(0, 34)
    for row_i, entry in enumerate(rows, 1):
        excel_row = row_i + 1
        sheet.set_row(row_i, entry["height"])
        for col, value in enumerate(entry["values"]):
            if col >= 5:
                style = (label_input if col == 5 else diagnosis_input) if entry["annotation"] else continuation
                assert sheet.write_blank(row_i, col, None, style) == 0
            elif col == 0 and not entry["annotation"]:
                assert sheet.write_url(row_i, col, f"internal:'Claim_review'!F{entry['start']}", sample_link, value) == 0
            elif col == 2 and isinstance(value, (int, float)):
                assert sheet.write_number(row_i, col, value, year_start if entry["annotation"] else year) == 0
            else:
                style = sample if col == 0 else source_start if entry["annotation"] else source
                assert sheet.write_string(row_i, col, str(value), style) == 0
        if entry["annotation"]:
            sheet.data_validation(row_i, 5, row_i, 5, {
                "validate": "list", "source": SUPPORT, "error_type": "stop",
                "input_title": "Support classification", "input_message": "Review all rows for this Sample ID, then select one label.",
                "error_title": "Select a listed label", "error_message": "Use the dropdown without changing the label text.",
            })
            sheet.data_validation(row_i, 6, row_i, 6, {
                "validate": "list", "source": DIAGNOSES, "error_type": "stop",
                "input_title": "Unsupported type", "input_message": "Select a type only when column F is Unsupported. Otherwise leave blank.",
                "error_title": "Select a listed type", "error_message": "Choose one of the six types in the dropdown.",
            })
            sheet.conditional_format(row_i, 6, row_i, 6, {"type": "formula", "criteria": f'AND($G{excel_row}<>"",$F{excel_row}<>"Unsupported")', "format": bad})
            sheet.conditional_format(row_i, 6, row_i, 6, {"type": "formula", "criteria": f'AND($F{excel_row}="Unsupported",$G{excel_row}="")', "format": pending})
    sheet.autofilter(0, 0, len(rows), 6)
    sheet.protect("", {"autofilter": True, "format_rows": True, "format_columns": True})
    sheet.set_landscape()
    sheet.set_paper(3)  # A3 preview/printing retains legible wide text columns.
    sheet.fit_to_pages(1, 0)
    sheet.repeat_rows(0)
    sheet.set_margins(0.2, 0.2, 0.25, 0.25)
    sheet.set_footer(f"&LReviewer {reviewer}&R&P / &N", {"margin": 0.1})
    sheet.print_area(0, 0, len(rows), 6)
    workbook.close()
    return rows, mapping


def verify_workbook(path, records):
    expected, mapping = layout_records(records)
    wb = openpyxl.load_workbook(path, data_only=False)
    assert wb.sheetnames == ["Claim_review"]
    ws = wb.active
    assert ws.sheet_state == "visible" and ws.max_column == 7 and ws.max_row == len(expected) + 1
    assert [c.value for c in ws[1]] == HEADERS
    assert ws.freeze_panes == "D2" and ws.protection.sheet
    assert ws.auto_filter.ref == f"A1:G{len(expected) + 1}"
    assert ws.max_row == len(records) + 1
    assert not ws.merged_cells.ranges and not wb._external_links
    assert not any(d.hidden for d in ws.row_dimensions.values())
    assert not any(d.hidden for d in ws.column_dimensions.values())
    actual_values, unlocked, input_rows = [], set(), set()
    for excel_row, entry in enumerate(expected, 2):
        cells = ws[excel_row]
        values = [unescape(c.value) if isinstance(c.value, str) else c.value for c in cells]
        assert values == entry["values"], f"Content changed at row {excel_row}"
        assert not any(c.data_type == "f" or c.comment for c in cells)
        assert all(c.protection.locked for c in cells[:5])
        assert ws.row_dimensions[excel_row].height == entry["height"]
        if entry["annotation"]:
            input_rows.add(excel_row)
            assert all(not c.protection.locked and c.value is None for c in cells[5:])
        else:
            assert all(c.protection.locked and c.value is None for c in cells[5:])
            assert cells[0].hyperlink.location == f"'Claim_review'!F{entry['start']}"
        unlocked.update(c.coordinate for c in cells if not c.protection.locked)
        actual_values.append(values)
    assert len(input_rows) == len(records) and len(unlocked) == 2 * len(records)
    validations = list(ws.data_validations.dataValidation)
    assert len(validations) == 2 * len(records)
    for dv in validations:
        coordinate = str(dv.sqref)
        # OOXML omits errorStyle when its default value is stop.
        assert coordinate in unlocked and dv.type == "list" and dv.errorStyle in (None, "stop")
        labels = SUPPORT if coordinate.startswith("F") else DIAGNOSES
        assert dv.formula1 == '"' + ",".join(labels) + '"'
    assert {str(v.sqref) for v in validations} == unlocked
    for record, item in zip(records, mapping):
        chunks = [actual_values[r - 2][4] for r in range(item["annotation_row"], item["last_material_row"] + 1)]
        assert "".join(chunks) == display_values(record)[4]
    with zipfile.ZipFile(path) as z:
        assert not any("vbaProject" in n or "externalLinks/" in n or "comments/" in n for n in z.namelist())
        assert "xl/worksheets/sheet2.xml" not in z.namelist()
    wb.close()
    return {"sha256": file_sha(path), "samples": len(records), "material_rows": len(expected),
            "annotation_cells": len(unlocked), "dropdowns": len(validations),
            "canonical_visible_cells_sha256": digest(actual_values),
            "full_cell_roundtrip": True, "all_candidate_text_reconstructed": True,
            "one_row_per_sample": True, "complete_candidate_set_in_one_cell": True,
            "only_expected_cells_and_one_visible_sheet": True, "row_mapping": mapping}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    paths = [DEST / f"human_validation_600_reviewer_{r}.xlsx" for r in ("A", "B")]
    if any(p.exists() for p in paths) or (PRIVATE / "sample_manifest.json").exists():
        raise SystemExit("Refusing to overwrite published packets or their private manifest. Preserve returned annotations and use a new version directory.")
    PRIVATE.mkdir(exist_ok=True)
    PRIVATE.chmod(0o700)
    STAGING.mkdir(exist_ok=True)
    old = DEST / "unsupported_diagnosis_validation_500.xlsx"
    old_hash = file_sha(old) if old.exists() else None
    frame, cases, excluded = collect_frame()
    selected, primary, design = sample(frame)
    records = recover_inputs(selected, primary, design, frame, cases)
    assert len(records) == 600
    coverage = {
        "companies": len({r["dynamic_input"]["context_metadata"]["company_name"] for r in records}),
        "years": sorted({r["dynamic_input"]["context_metadata"]["target_reporting_year"] for r in records}),
        "tasks": sorted({r["task_id"] for r in records}),
        "cases": len({r["generation_case_id"] for r in records}),
        "combined_support_counts": dict(Counter(r["automated_support_label"] for r in records)),
        "combined_diagnosis_counts": dict(Counter(r["automated_diagnosis"] for r in records if r["automated_diagnosis"])),
        "primary_company_counts": dict(Counter(r["dynamic_input"]["context_metadata"]["company_name"] for r in records if r["group"] == "primary")),
        "empty_candidate_sets": sum(not r["dynamic_input"]["ec_claims"] for r in records),
        "paired_input_checks": sum(r["same_support_diagnosis_input_verified"] is True for r in records),
        "maximum_candidate_count": max(len(r["dynamic_input"]["ec_claims"]) for r in records),
        "maximum_candidate_text_characters": max(len(display_values(r)[4]) for r in records),
    }
    assert coverage["companies"] == 30 and len(coverage["years"]) == 5 and len(coverage["tasks"]) == 12
    assert len(coverage["primary_company_counts"]) == 30
    staged, qa = [], {}
    for reviewer, final in zip(("A", "B"), paths):
        temp = STAGING / final.name
        write_workbook(temp, records, reviewer)
        qa[reviewer] = verify_workbook(temp, records)
        staged.append(temp)
        print(f"Reviewer {reviewer} workbook round-trip verified: {qa[reviewer]['material_rows']} material rows, 600 annotation rows", flush=True)
    assert qa["A"]["canonical_visible_cells_sha256"] == qa["B"]["canonical_visible_cells_sha256"]
    assert old_hash == (file_sha(old) if old.exists() else None)
    for relative, stats in SOURCE_STATS.items():
        stat = (ROOT / relative).stat()
        assert (stat.st_size, stat.st_mtime_ns) == stats, f"Source changed during export: {relative}"

    row_map = {r["sample_id"]: r for r in qa["A"].pop("row_mapping")}
    qa["B"].pop("row_mapping")
    for r in records:
        r.update({k: v for k, v in row_map[r["sample_id"]].items() if k != "sample_id"})
    manifest = {"schema_version": "bace_human_validation_v1", "status": "prepared_not_annotated",
                "study_design": design, "coverage": coverage, "excluded_incomplete_cases": excluded,
                "records": records}
    write_json(STAGING / "sample_manifest.json", manifest)
    qa.update({"sources_sha256": SOURCES, "source_files_checked": len(SOURCES),
               "exporter_sha256": file_sha(__file__), "coverage": coverage,
               "sample_manifest_sha256": file_sha(STAGING / "sample_manifest.json"),
               "old_exploratory_workbook_unchanged_sha256": old_hash,
               "dependencies": {"XlsxWriter": xlsxwriter.__version__, "openpyxl": openpyxl.__version__}})
    write_json(STAGING / "export_qa.json", qa)
    # Commit the files only after both complete read-back checks pass.
    for temp, final in zip(staged, paths):
        assert not final.exists()
        temp.replace(final)
    for name in ("sample_manifest.json", "export_qa.json"):
        (STAGING / name).replace(PRIVATE / name)
    STAGING.rmdir()
    print(json.dumps({"workbooks": [str(p) for p in paths], "coverage": coverage,
                      "private_manifest": str(PRIVATE / 'sample_manifest.json')}, indent=2), flush=True)


def refresh_layout():
    """Reflow pristine packets together; preserve exact inputs, labels and old files."""
    manifest_path = PRIVATE / "sample_manifest.json"
    qa_path = PRIVATE / "export_qa.json"
    manifest = json.loads(manifest_path.read_text())
    records = manifest["records"]
    qa = json.loads(qa_path.read_text())
    assert qa["sample_manifest_sha256"] == file_sha(manifest_path)
    source_semantics = digest([
        {k: v for k, v in record.items() if k not in ("annotation_row", "last_material_row", "material_rows")}
        for record in records
    ])
    for record in records:
        assert digest(record["dynamic_input"]) == record["input_sha256"]

    paths = {r: DEST / f"human_validation_600_reviewer_{r}.xlsx" for r in ("A", "B")}
    expected_hashes = {path: qa[r]["sha256"] for r, path in paths.items()}
    result_path = DEST / "human_validation_600_with_main_results.xlsx"
    results_qa_path = PRIVATE / "main_results_export_qa.json"
    result_qa = None
    if result_path.exists():
        import export_validation_main_results as results
        result_qa = json.loads(results_qa_path.read_text())
        expected_hashes[result_path] = result_qa["workbook_sha256"]
        results.verify_original_results(records, qa)
    for path, expected in expected_hashes.items():
        assert file_sha(path) == expected, "Packet changed; refusing to overwrite possible annotations"

    STAGING.mkdir(exist_ok=True)
    _, mapping = layout_records(records)
    for record, entry in zip(records, mapping):
        assert record["sample_id"] == entry["sample_id"]
        record.update({k: v for k, v in entry.items() if k != "sample_id"})
    assert source_semantics == digest([
        {k: v for k, v in record.items() if k not in ("annotation_row", "last_material_row", "material_rows")}
        for record in records
    ])
    new_qa = {}
    for reviewer, path in paths.items():
        write_workbook(STAGING / path.name, records, reviewer)
        new_qa[reviewer] = verify_workbook(STAGING / path.name, records)
        new_qa[reviewer].pop("row_mapping")
    assert new_qa["A"]["canonical_visible_cells_sha256"] == new_qa["B"]["canonical_visible_cells_sha256"]
    if result_qa is not None:
        expected, result_mapping = results.write_results(STAGING / result_path.name, records)
        result_qa.update(results.verify_results(STAGING / result_path.name, records, expected, result_mapping))
        result_qa["layout_helper_sha256"] = file_sha(__file__)
        result_qa["visual_review"] = {"status": "pending_after_reflow"}

    # Archive the exact pre-revision files before replacing any pristine packet.
    archive_root = PRIVATE / "layout_archive"
    archive_root.mkdir(exist_ok=True)
    archive = Path(tempfile.mkdtemp(prefix="before_one_row_reflow_", dir=archive_root))
    for path in [*expected_hashes, manifest_path, qa_path, results_qa_path,
                 DEST / "README.md", PRIVATE / "README.md", PRIVATE / "visual_qa.json"]:
        if path.exists():
            name = "reviewer_README.md" if path == DEST / "README.md" else "coordinator_README.md" if path == PRIVATE / "README.md" else path.name
            shutil.copy2(path, archive / name)
    for path, expected in expected_hashes.items():
        assert file_sha(path) == expected
        assert file_sha(archive / path.name) == expected

    manifest["layout_revision"] = "one_sample_one_row_v3"
    write_json(STAGING / "sample_manifest.json", manifest)
    new_manifest_hash = file_sha(STAGING / "sample_manifest.json")
    qa.setdefault("layout_history", []).append({
        "revision": "one_sample_one_row_v3", "archive": archive.relative_to(ROOT).as_posix(),
        "old_packet_hashes": {p.name: h for p, h in expected_hashes.items()},
        "previous_manifest_sha256": qa["sample_manifest_sha256"],
        "unchanged_sample_semantics_sha256": source_semantics,
    })
    qa.update(new_qa)
    qa["exporter_sha256"] = file_sha(__file__)
    qa["sample_manifest_sha256"] = new_manifest_hash
    qa["whole_ec_per_cell_verified"] = True
    qa["one_row_per_sample"] = True
    qa["complete_candidate_set_in_one_cell"] = True
    qa["visual_review"] = {"status": "pending_after_reflow"}
    write_json(STAGING / "export_qa.json", qa)
    if result_qa is not None:
        result_qa["manifest_sha256"] = new_manifest_hash
        result_qa["layout_revision"] = "one_sample_one_row_v3"
        result_qa["whole_ec_per_cell_verified"] = True
        result_qa["one_row_per_sample"] = True
        result_qa["complete_candidate_set_in_one_cell"] = True
        result_qa["pre_reflow_archive"] = archive.relative_to(ROOT).as_posix()
        result_qa["preserved_existing_files"] = {
            (archive / p.name).relative_to(ROOT).as_posix(): h for p, h in expected_hashes.items()
        }
        write_json(STAGING / "main_results_export_qa.json", result_qa)
    for path, expected in expected_hashes.items():
        assert file_sha(path) == expected, "Packet changed during preparation; refusing overwrite"
    for path in expected_hashes:
        (STAGING / path.name).replace(path)
    for path in [manifest_path, qa_path] + ([results_qa_path] if result_qa is not None else []):
        (STAGING / path.name).replace(path)
    STAGING.rmdir()
    print(json.dumps({"revision": "one_sample_one_row_v3", "samples": len(records),
                      "material_rows": new_qa["A"]["material_rows"], "archive": str(archive),
                      "source_inputs_and_automated_results_unchanged": True}, indent=2), flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--refresh-layout"]:
        refresh_layout()
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit("Usage: build_human_validation.py [--refresh-layout]")
