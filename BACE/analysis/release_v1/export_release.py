"""Export the public derived-data release (release_v1) from the saved main_v1 results.

Read-only with respect to the experiment: it reads results/main_v1/cases/* and the
frozen config, and writes only to analysis/outputs/release_v1/. Run from the repo root:
    BACE/.venv/bin/python -B BACE/analysis/release_v1/export_release.py

Released tables (gzip-compressed CSV, UTF-8):
  generated_disclosures  one row per generated disclosure (1,800)
  evidence_claims        deduplicated evidence claims (ECs) per disclosure
  disclosure_claims      deduplicated disclosure claims (DCs) with BACE label
  support_sets           one row per accepted support set, with its EC identifiers
  diagnoses              primary diagnosis and rationale for each unsupported DC

Not released (third-party source content, see Data availability): evidence-card text,
retrieval inputs, prompts, the exact source quotes used to ground ECs and the raw
model-call records. Local file paths and encrypted reasoning blobs are dropped.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BACE = HERE.parent.parent
CASES = BACE / "results/main_v1/cases"
SNAP = BACE / "analysis/outputs/snapshot"
OUT = BACE / "analysis/outputs/release_v1"
EXPERIMENT = json.loads((BACE / "config/experiment.json").read_text())
GEN_VERSION = EXPERIMENT["generation"]["model_version"]

TABLES = {
    "generated_disclosures": [
        "generation_case_id", "company_id", "company_name", "target_reporting_year", "task_id", "task_title",
        "generated_text", "generated_text_sha256", "generated_word_count", "length_within_requested_range",
        "generation_status", "retry_attempts", "model", "configured_model_version", "deployment_name",
        "reasoning_effort", "max_output_tokens", "returned_temperature", "returned_top_p", "service_tier",
        "provider_response_id", "created_at_utc", "input_tokens", "output_tokens", "reasoning_tokens",
        "evidence_card_count"],
    "evidence_claims": [
        "generation_case_id", "ec_id", "ec_text", "evidence_card_ids", "evidence_types", "source_files",
        "document_types", "source_years", "pages", "metrics", "grounding_status"],
    "disclosure_claims": ["generation_case_id", "dc_id", "dc_text", "bace_label", "grounding_status"],
    "support_sets": ["generation_case_id", "dc_id", "support_set_index", "support_type", "set_size", "ec_ids"],
    "diagnoses": ["generation_case_id", "dc_id", "primary_diagnosis", "rationale"],
}
DIAGNOSES = {"factual_boundary_distortion", "evidence_conflation", "non_disclosure_statement",
             "inferential_inflation", "unsupported_novelty", "contradiction"}


def jl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def uniq(values) -> str:
    out = []
    for v in values:
        if v is not None and str(v) not in out:
            out.append(str(v))
    return ";".join(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {k: [] for k in TABLES}
    cases = sorted(p for p in CASES.iterdir() if p.is_dir())
    assert len(cases) == EXPERIMENT["expected_case_count"] == 1800

    for case in cases:
        cid = case.name
        gens = list(jl(case / "generation/generated_disclosures.jsonl"))
        assert len(gens) == 1, cid
        g = gens[0]
        assert g["generation_case_id"] == cid
        r, m = g["provider_response"], g["generation_model"]
        assert m["model"] == EXPERIMENT["generation"]["model"] and m["temperature"] is None
        assert hashlib.sha256(g["generated_text"].encode()).hexdigest() == g["generated_text_hash"]
        rows["generated_disclosures"].append(dict(
            generation_case_id=cid, company_id=g["company_id"], company_name=g["company_name"],
            target_reporting_year=g["target_reporting_year"], task_id=g["task_id"], task_title=g["task_title"],
            generated_text=g["generated_text"], generated_text_sha256=g["generated_text_hash"],
            generated_word_count=g["generated_word_count"],
            length_within_requested_range=g["length_within_requested_range"],
            generation_status=g["generation_status"], retry_attempts=g["retry_attempts"],
            model=m["model"], configured_model_version=GEN_VERSION, deployment_name=m["deployment_name"],
            reasoning_effort=m["reasoning_effort"], max_output_tokens=m["max_output_tokens"],
            returned_temperature=r["temperature"], returned_top_p=r["top_p"], service_tier=r["service_tier"],
            provider_response_id=g["provider_response_id"], created_at_utc=g["created_at_utc"],
            input_tokens=r["usage"]["input_tokens"], output_tokens=r["usage"]["output_tokens"],
            reasoning_tokens=r["usage"]["output_tokens_details"]["reasoning_tokens"],
            evidence_card_count=g["evidence_count"]))

        dc_file = case / "bace/dedup/dc_claims.jsonl"
        if not dc_file.exists():          # the two cases without completed BACE
            continue
        ecs = list(jl(case / "bace/dedup/ec_claims.jsonl"))
        ec_ids = {e["ec_id"] for e in ecs}
        assert len(ec_ids) == len(ecs), cid
        for e in ecs:
            prov = [p["evidence_provenance"] for p in e["ec_provenance"]]
            rows["evidence_claims"].append(dict(
                generation_case_id=cid, ec_id=e["ec_id"], ec_text=e["ec_text"],
                evidence_card_ids=uniq(e["evidence_card_ids"]),
                evidence_types=uniq(p["evidence_type"] for p in prov),
                source_files=uniq(p["source_file"] for p in prov),
                document_types=uniq(p["document_type"] for p in prov),
                source_years=uniq(p["source_year"] for p in prov),
                pages=uniq(f'{p["page_start"]}' if p["page_start"] == p["page_end"] else f'{p["page_start"]}-{p["page_end"]}'
                           for p in prov if p.get("page_start") is not None),
                metrics=uniq(p.get("metric") for p in prov),
                grounding_status=uniq(p["grounding_status"] for p in e["ec_provenance"])))

        dcs = list(jl(dc_file))
        dc_ids = {d["dc_id"] for d in dcs}
        assert len(dc_ids) == len(dcs), cid
        sets = {s["dc_claim_id"]: s["support_sets"] for s in jl(case / "bace/support/dc_support_sets.jsonl")}
        diag = {d["dc_claim_id"]: d for d in jl(case / "bace/diagnosis/dc_unsupported_diagnoses.jsonl")}
        assert set(sets) == dc_ids, cid
        assert set(diag) <= dc_ids, cid
        for d in dcs:
            ss = sets[d["dc_id"]]
            types = {s["support_type"] for s in ss}
            assert types <= {"direct", "inferred"}, (cid, types)
            if not ss:
                label = diag[d["dc_id"]]["unsupported_label"]
                assert label in DIAGNOSES, (cid, label)
            else:
                assert d["dc_id"] not in diag, cid
                label = "direct" if "direct" in types else "inferred"
            rows["disclosure_claims"].append(dict(
                generation_case_id=cid, dc_id=d["dc_id"], dc_text=d["dc_text"], bace_label=label,
                grounding_status=uniq(p["grounding_status"] for p in d["dc_provenance"])))
            for i, s in enumerate(ss, 1):
                assert s["ec_claim_ids"] and set(s["ec_claim_ids"]) <= ec_ids, (cid, d["dc_id"])
                rows["support_sets"].append(dict(
                    generation_case_id=cid, dc_id=d["dc_id"], support_set_index=i, support_type=s["support_type"],
                    set_size=len(s["ec_claim_ids"]), ec_ids=";".join(s["ec_claim_ids"])))
            if d["dc_id"] in diag:
                rows["diagnoses"].append(dict(
                    generation_case_id=cid, dc_id=d["dc_id"], primary_diagnosis=diag[d["dc_id"]]["unsupported_label"],
                    rationale=diag[d["dc_id"]]["rationale"]))

    # ---------------------------------------------------------------- cross-checks
    snap = {(x["generation_case_id"], x["dc_id"]): x for x in csv.DictReader(open(SNAP / "claims.csv", encoding="utf-8"))}
    mine = {(x["generation_case_id"], x["dc_id"]): x for x in rows["disclosure_claims"]}
    assert snap.keys() == mine.keys(), "DC identifiers differ from snapshot/claims.csv"
    for k, x in mine.items():
        assert x["bace_label"] == snap[k]["label"], k
        assert x["dc_text"] == snap[k]["dc_text"], k
    nsets = Counter((s["generation_case_id"], s["dc_id"]) for s in rows["support_sets"])
    for k, x in snap.items():
        assert nsets.get(k, 0) == int(x["support_set_count"]), k
    labels = Counter(x["bace_label"] for x in rows["disclosure_claims"])
    expect = {"generated_disclosures": 1800, "disclosure_claims": 94955, "diagnoses": 42646}
    for k, n in expect.items():
        assert len(rows[k]) == n, (k, len(rows[k]), n)
    assert labels["direct"] == 34430 and labels["inferred"] == 17879, labels

    # ---------------------------------------------------------------- write
    manifest = {"release": "release_v1", "source_run": "results/main_v1", "experiment_id": EXPERIMENT["experiment_id"],
                "builder": "BACE/analysis/release_v1/export_release.py",
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "bace_label_counts": dict(sorted(labels.items())), "tables": {}}
    for name, cols in TABLES.items():
        path = OUT / f"{name}.csv.gz"
        with gzip.GzipFile(path, "wb", mtime=0) as raw, \
                __import__("io").TextIOWrapper(raw, encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows[name])
        manifest["tables"][f"{name}.csv.gz"] = {"rows": len(rows[name]), "columns": cols,
                                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        print(f"{name:22s} {len(rows[name]):>8,d} rows  {path.stat().st_size / 1e6:6.1f} MB")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # ---------------------------------------------------------------- leakage scan
    for p in OUT.glob("*.csv.gz"):
        text = gzip.open(p, "rt", encoding="utf-8").read()
        for bad in ("/home/", "encrypted_content", "gAAAAA", "openai.azure.com", "api_key"):
            assert bad not in text, (p.name, bad)
    print("checks passed; manifest written")


if __name__ == "__main__":
    main()
