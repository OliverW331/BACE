# /// script
# requires-python = ">=3.11"
# dependencies = ["XlsxWriter==3.2.5", "openpyxl==3.1.5"]
# ///
"""Export 600 validation units with original BACE labels and saved rationales."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import tempfile

import openpyxl
from openpyxl.utils.escape import unescape
import xlsxwriter

import build_human_validation as source

DEST = source.DEST / "human_validation_600_with_main_results.xlsx"
QA_PATH = source.PRIVATE / "main_results_export_qa.json"
HEADERS = source.HEADERS[:5] + [
    "BACE support label", "BACE unsupported type", "Unedited automatic rationale",
]
WIDTHS = source.WIDTHS + [70]
SHEET = "Main_results"


def result_values(record):
    """Support outputs have no prose rationale; preserve those cells as blank."""
    rationale = record["unedited_automatic_rationale"]
    if record["automated_support_label"] == "Unsupported":
        assert isinstance(rationale, str) and rationale.strip()
    else:
        assert rationale is None
    return [record["automated_support_label"], record["automated_diagnosis"], rationale]


def verify_original_results(records, export_qa):
    """Compare private labels against the receipt-bound experiment output files."""
    source_hashes = {}
    by_case = {}
    for record in records:
        cid = record["generation_case_id"]
        if cid not in by_case:
            tables = {}
            for stage, filename in (("support", "dc_support_sets.jsonl"), ("diagnosis", "dc_unsupported_diagnoses.jsonl")):
                path = source.RUN / "cases" / cid / "bace" / stage / filename
                relative = path.relative_to(source.ROOT).as_posix()
                actual = source.file_sha(path)
                assert actual == export_qa["sources_sha256"][relative], path
                source_hashes[relative] = actual
                tables[stage] = source.keyed(
                    [json.loads(line) for line in path.read_text().splitlines() if line.strip()],
                    "dc_claim_id",
                )
            by_case[cid] = tables
        did = record["dc_id"]
        support = by_case[cid]["support"][did]
        diagnosis = by_case[cid]["diagnosis"].get(did)
        assert source.support_label(support) == record["automated_support_label"]
        assert support["support_sets"] == record["automated_support_sets"]
        assert (diagnosis["unsupported_label"] if diagnosis else None) == record["automated_diagnosis"]
        assert (diagnosis["rationale"] if diagnosis else None) == record["unedited_automatic_rationale"]
        assert source.digest(record["dynamic_input"]) == record["input_sha256"]
    return source_hashes


def write_results(path, records):
    rows, mapping = source.layout_records(records)
    by_sample = {r["sample_id"]: r for r in records}
    workbook = xlsxwriter.Workbook(path, {
        "constant_memory": True, "strings_to_formulas": False, "strings_to_urls": False,
    })
    workbook.set_properties({
        "title": "Main-experiment BACE results for 600 validation samples",
        "subject": "Coordinator result reference; original classifications and unedited diagnosis rationales",
        "author": "BACE", "created": datetime(2026, 9, 25),
        "comments": "Contains original BACE outputs, not human annotations. Do not distribute during independent human review.",
    })
    sheet = workbook.add_worksheet(SHEET)
    sheet.freeze_panes(1, 3)
    sheet.hide_gridlines(2)
    sheet.set_zoom(80)
    base = {"font_name": "Arial", "font_size": 10, "valign": "top", "text_wrap": True}
    boundary = {"top": 1, "top_color": "#B4C8D8"}
    def fmt(**extra):
        return workbook.add_format({**base, **extra})
    plain = fmt(bg_color="#F7FAFD")
    first = fmt(bg_color="#F7FAFD", **boundary)
    number = fmt(bg_color="#F7FAFD", align="center", num_format="0")
    first_number = fmt(bg_color="#F7FAFD", align="center", num_format="0", **boundary)
    sid = fmt(bg_color="#EAF2F8", font_color="#285675", bold=True, **boundary)
    sid_link = fmt(bg_color="#EAF2F8", font_color="#285675", underline=1)
    result_styles = [fmt(bg_color=color, bottom=1, bottom_color="#B4C8D8", **boundary)
                     for color in ("#E2F2E9", "#FFF0DF", "#FFF7EC")]
    continuation = fmt(bg_color="#F2F4F6")
    for col, (width, header) in enumerate(zip(WIDTHS, HEADERS)):
        sheet.set_column(col, col, width)
        colour = "#7AAED6" if col < 5 else "#83C5A3" if col == 5 else "#F3B27A"
        style = fmt(bold=True, valign="vcenter", bg_color=colour, font_color="#203441", bottom=1, bottom_color="#B4C8D8")
        sheet.write_string(0, col, header, style)
    sheet.set_row(0, 34)
    expected = []
    for row_i, entry in enumerate(rows, 1):
        values = list(entry["values"])
        record = by_sample[values[0]]
        if entry["annotation"]:
            values[5:] = result_values(record)
        for value in values:
            if isinstance(value, str):
                assert len(value.encode("utf-16-le")) // 2 <= 32767
        expected.append(values)
        rationale_height = source.visual_lines(values[7] or "", 60) * 15 + 16
        sheet.set_row(row_i, min(409, max(entry["height"], rationale_height)))
        for col, value in enumerate(values):
            if col >= 5:
                style = result_styles[col - 5] if entry["annotation"] else continuation
                if value is None:
                    status = sheet.write_blank(row_i, col, None, style)
                else:
                    status = sheet.write_string(row_i, col, value, style)
            elif col == 0 and not entry["annotation"]:
                status = sheet.write_url(row_i, col, f"internal:'{SHEET}'!F{entry['start']}", sid_link, value)
            elif col == 2 and isinstance(value, (int, float)):
                status = sheet.write_number(row_i, col, value, first_number if entry["annotation"] else number)
            else:
                style = sid if col == 0 else first if entry["annotation"] else plain
                status = sheet.write_string(row_i, col, str(value), style)
            assert status == 0
    sheet.autofilter(0, 0, len(rows), len(HEADERS) - 1)
    sheet.protect("", {"autofilter": True, "format_rows": True, "format_columns": True})
    sheet.set_landscape()
    sheet.set_paper(3)
    sheet.fit_to_pages(1, 0)
    sheet.repeat_rows(0)
    sheet.set_margins(0.2, 0.2, 0.25, 0.25)
    sheet.set_footer("&LMain-experiment results | Coordinator copy&R&P / &N", {"margin": 0.1})
    sheet.print_area(0, 0, len(rows), len(HEADERS) - 1)
    workbook.close()
    return expected, mapping


def verify_results(path, records, expected, mapping):
    book = openpyxl.load_workbook(path, data_only=False)
    assert book.sheetnames == [SHEET]
    ws = book.active
    assert ws.max_column == len(HEADERS) and ws.max_row == len(expected) + 1
    assert [c.value for c in ws[1]] == HEADERS
    assert ws.freeze_panes == "D2" and ws.protection.sheet
    assert ws.auto_filter.ref == f"A1:H{len(expected) + 1}"
    assert ws.max_row == len(records) + 1
    assert not ws.data_validations.dataValidation and not ws.conditional_formatting
    assert not book._external_links and not ws.merged_cells.ranges
    for row_i, wanted in enumerate(expected, 2):
        cells = ws[row_i]
        values = [unescape(c.value) if isinstance(c.value, str) else c.value for c in cells]
        assert values == wanted, (row_i, values, wanted)
        assert not any(c.data_type == "f" or c.comment for c in cells)
        assert all(c.protection.locked for c in cells)
    for record, item in zip(records, mapping):
        assert item["annotation_row"] == record["annotation_row"]
        assert item["last_material_row"] == record["last_material_row"]
        chunks = [expected[r - 2][4] for r in range(item["annotation_row"], item["last_material_row"] + 1)]
        assert "".join(chunks) == source.display_values(record)[4]
        assert expected[item["annotation_row"] - 2][5:] == result_values(record)
    book.close()
    return {
        "workbook_sha256": source.file_sha(path), "sheet": SHEET, "columns": HEADERS,
        "samples": len(records), "material_rows": len(expected),
        "filled_support_labels": sum(row[5] is not None for row in expected),
        "filled_unsupported_types": sum(row[6] is not None for row in expected),
        "filled_original_rationales": sum(row[7] is not None for row in expected),
        "supported_rows_without_recorded_rationale": sum(row[5] != "Unsupported" and row[7] is None for row in expected),
        "rationales_unchanged_from_original_diagnosis_outputs": True,
        "support_counts": dict(Counter(row[5] for row in expected if row[5])),
        "diagnosis_counts": dict(Counter(row[6] for row in expected if row[6])),
        "canonical_material_cells_sha256": source.digest([r[:5] for r in expected]),
        "same_sample_order_and_material_rows_as_reviewer_packets": True,
        "complete_roundtrip_and_evidence_reconstruction": True,
        "one_row_per_sample": True, "complete_candidate_set_in_one_cell": True,
    }


def main(refresh=False):
    previous_qa = None
    if refresh:
        previous_qa = json.loads(QA_PATH.read_text())
        assert source.file_sha(DEST) == previous_qa["workbook_sha256"], "Result workbook changed; refusing overwrite"
    elif DEST.exists() or QA_PATH.exists():
        raise SystemExit("Refusing to overwrite an existing result reference or its QA record.")
    manifest_path = source.PRIVATE / "sample_manifest.json"
    export_qa_path = source.PRIVATE / "export_qa.json"
    export_qa = json.loads(export_qa_path.read_text())
    assert source.file_sha(manifest_path) == export_qa["sample_manifest_sha256"]
    assert source.file_sha(Path(source.__file__)) == export_qa["exporter_sha256"]
    records = json.loads(manifest_path.read_text())["records"]
    assert len(records) == 600 and len({r["sample_id"] for r in records}) == 600
    protected_paths = [source.DEST / f"human_validation_600_reviewer_{r}.xlsx" for r in ("A", "B")]
    protected_paths += [source.DEST / "unsupported_diagnosis_validation_500.xlsx", manifest_path]
    before = {p: source.file_sha(p) for p in protected_paths}
    source_hashes = verify_original_results(records, export_qa)
    temporary = source.PRIVATE / ".main_results.building.xlsx"
    expected, mapping = write_results(temporary, records)
    qa = verify_results(temporary, records, expected, mapping)
    assert qa["filled_support_labels"] == 600 and qa["filled_unsupported_types"] == 380
    assert qa["filled_original_rationales"] == 380
    assert qa["supported_rows_without_recorded_rationale"] == 220
    assert qa["support_counts"] == {"Supported": 145, "Supported by inference": 75, "Unsupported": 380}
    for path, prior in before.items():
        assert source.file_sha(path) == prior, f"Existing file changed during export: {path}"
    if refresh:
        old_book = openpyxl.load_workbook(DEST)
        old_rows = list(old_book.active.iter_rows(min_row=2, max_col=7, values_only=True))
        assert len(old_rows) == len(expected)
        for old_row, new_row in zip(old_rows, expected):
            decoded = [unescape(v) if isinstance(v, str) else v for v in old_row]
            assert decoded == new_row[:7], "Existing source material or classification would change"
        old_book.close()
        archive_root = source.PRIVATE / "layout_archive"
        archive_root.mkdir(exist_ok=True)
        archive = Path(tempfile.mkdtemp(prefix="before_results_rationale_", dir=archive_root))
        for path in (DEST, QA_PATH):
            shutil.copy2(path, archive / path.name)
        assert source.file_sha(DEST) == previous_qa["workbook_sha256"]
        assert source.file_sha(archive / DEST.name) == previous_qa["workbook_sha256"]
        qa["previous_result_archive"] = archive.relative_to(source.ROOT).as_posix()
        qa["existing_columns_A_to_G_unchanged"] = True
    qa.update({
        "manifest_sha256": source.file_sha(manifest_path),
        "source_output_sha256": source_hashes, "source_output_files_checked": len(source_hashes),
        "exporter_sha256": source.file_sha(__file__),
        "layout_helper_sha256": source.file_sha(Path(source.__file__)),
        "preserved_existing_files": {p.relative_to(source.ROOT).as_posix(): v for p, v in before.items()},
        "empty_candidate_sets_without_support_llm_call": sum(not r["support_model_called"] for r in records),
        "layout_revision": "one_sample_one_row_v3",
        "result_schema_revision": "original_diagnosis_rationale_v1",
        "visual_review": {"status": "pending_after_rationale_column"},
        "notes": "Original frozen BACE outputs, not adjudicated human truth. Supported means direct support. Column H copies diagnosis rationale verbatim for 380 unsupported rows. The 220 supported rows have no recorded prose rationale and remain blank in H: the support stage outputs only support sets. The 600 units include 400 primary and 200 diagnosis-supplement units; their unweighted average is not a population estimate.",
    })
    temporary.rename(DEST)
    source.write_json(QA_PATH, qa)
    print(json.dumps({"workbook": str(DEST), "samples": qa["samples"], "columns": len(HEADERS),
                      "support_counts": qa["support_counts"], "source_output_files_checked": len(source_hashes)}, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--refresh"]:
        main(refresh=True)
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit("Usage: export_validation_main_results.py [--refresh]")
