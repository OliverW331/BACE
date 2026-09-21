"""Replay inherited native extraction lineage checks for new experiment runs."""

from pathlib import Path
from common import ROOT, read, rows, digest
from generation_claims import sha256_json
from audit_staged_claim_extraction import extraction_view
from claim_refinement_lineage import original_source_input

def file_info(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}

def audit_extraction(directory, cid, task, source_job, source_files, chain=None):
    """Replay every accepted stage and verify source/model lineage to direct v8."""
    chain = [] if chain is None else chain
    manifest_path = directory / "claim_extraction_run_manifest.json"
    manifest = read(manifest_path)
    if manifest["run_status"] != "complete":
        raise ValueError("Incomplete extraction source")
    call_path = directory / f"{task}_extraction_calls.jsonl"
    selected = [r for r in rows(call_path) if r["job_summary"]["generation_case_id"] == cid]
    record = selected[-1]
    if record["call_status"] != "success" or record["api_response"]["status"] != "completed":
        raise ValueError("Incomplete native extraction")
    if original_source_input(record) != source_job["dynamic_input"]:
        raise ValueError("Extraction source changed")
    for path, expected in manifest["code_hashes"].items():
        if file_info(ROOT / path)["sha256"] != expected:
            from acceptance import validate_completed_script
            validate_completed_script(path,expected)
    canonical = extraction_view(record)
    if record.get("canonical_output") != canonical:
        raise ValueError("Canonical extraction differs from native replay")
    source_files[str(call_path.relative_to(ROOT))] = file_info(call_path)
    source_files[str(manifest_path.relative_to(ROOT))] = file_info(manifest_path)
    chain.append({"directory": str(directory.relative_to(ROOT)), "call_id": record["call_id"],
                  "prompt_version": manifest["prompts"][task]["version"]})
    if manifest.get("draft_run"):
        draft_dir = Path(manifest["draft_run"]["directory"])
        draft_manifest = read(draft_dir / "claim_extraction_run_manifest.json")
        identity = {key: draft_manifest.get(key) for key in manifest["draft_run"]["identity_fields"]}
        if identity != manifest["draft_run"]["identity"] or sha256_json(identity) != manifest["source_hashes"]["draft_manifest"]:
            raise ValueError("Draft manifest identity changed")
        if file_info(draft_dir / f"{task}_extraction_calls.jsonl")["sha256"] != manifest["source_hashes"][f"draft_{task}_calls"]:
            raise ValueError("Draft native calls changed")
        draft, draft_canonical, _ = audit_extraction(draft_dir, cid, task, source_job, source_files, chain)
        if record["draft_call_id"] != draft["call_id"] or record["dynamic_input"]["draft_extraction"] != draft_canonical:
            raise ValueError("Draft-to-review linkage differs")
        for key in ("deployment_name", "request_parameters"):
            if record[key] != draft[key]:
                raise ValueError("Extraction model settings differ across stages")
    return record, canonical, chain
