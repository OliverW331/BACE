"""Read saved Genmab-2019 calls; write a scoped flow inventory under paper/ only."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BACE = ROOT / "BACE"
CONFIG = BACE / "config/evaluation/configs"
RUN = BACE / "results/main_v1"
SOURCES = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    data = path.read_bytes()
    SOURCES[str(path)] = {"sha256": digest(data), "bytes": len(data)}
    return json.loads(data)


def rows(path):
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for line in stream:
            h.update(line)
            size += len(line)
            if line.strip():
                yield json.loads(line)
    SOURCES[str(path)] = {"sha256": h.hexdigest(), "bytes": size}


STAGES = {
    "direct": ("generation_claim_extraction_config_v8.json", "extraction/direct", ["ec_extraction_calls.jsonl", "dc_extraction_calls.jsonl"]),
    "integrated": ("generation_claim_patch_review_config_v4.json", "extraction/integrated", ["ec_extraction_calls.jsonl", "dc_extraction_calls.jsonl"]),
    "atomic": ("generation_claim_atomicity_review_config_v2.json", "extraction/atomic", ["ec_extraction_calls.jsonl", "dc_extraction_calls.jsonl"]),
    "dedup": ("generation_claim_semantic_dedup_config.json", "bace/dedup", ["semantic_dedup_calls.jsonl"]),
    "candidates": ("generation_claim_candidate_selection_config.json", "bace/candidates", ["claim_candidate_calls.jsonl"]),
    "support": ("generation_claim_support_config.json", "bace/support", ["claim_support_calls.jsonl"]),
    "diagnosis": ("generation_claim_unsupported_diagnosis_config.json", "bace/diagnosis", ["claim_unsupported_diagnosis_calls.jsonl"]),
}
inventory = {}
for stage, (config_name, _, _) in STAGES.items():
    config = read(CONFIG / config_name)
    specs = config.get("prompts") or {"shared": config["prompt"]}
    schemas = config.get("response_schemas") or {"shared": config["response_schema"]}
    resolved = {}
    for side, spec in specs.items():
        path = (CONFIG / spec["file"]).resolve()
        data = path.read_bytes()
        SOURCES[str(path)] = {"sha256": digest(data), "bytes": len(data)}
        assert digest(data) == spec["sha256"], path
        schema = schemas[side]
        schema_path = (CONFIG / schema["file"]).resolve()
        read(schema_path)
        assert SOURCES[str(schema_path)]["sha256"] == schema["sha256"]
        resolved[side] = {**spec, "path": str(path), "response_schema_path": str(schema_path)}
    inventory[stage] = {"config_path": str(CONFIG / config_name), "prompts": resolved,
                        "configured_model": config["models"][config["current_primary_model"]]}

manifest = read(RUN / "manifest.json")
ids = [cid for cid in manifest["case_ids"] if "__genmab__2019__" in cid]
ids.sort(key=lambda cid: ("esg".index(cid.rsplit("__", 1)[-1][0]), int(cid.rsplit("__", 1)[-1].split("_")[1])))
assert len(ids) == 12 and len(set(ids)) == 12
counts = []
observed = defaultdict(lambda: defaultdict(set))
verification = Counter()

for cid in ids:
    base = RUN / "cases" / cid
    case = list(rows(base / "inputs/generation_cases.jsonl"))[0]
    outputs = list(rows(base / "generation/generated_disclosures.jsonl"))
    assert len(outputs) == 1
    output = outputs[0]
    assert digest(case["generation_prompt"].encode()) == output["prompt_hash"]
    assert output["generation_status"] == "success"
    gm = output["generation_model"]
    for key, value in {"model_id": gm["model"], "deployment": gm["deployment_name"], "reasoning_effort": gm["reasoning_effort"], "provider_returned_model": output["provider_response"]["model"]}.items():
        observed["generation"][key].add(value)
    counts.append({"task": case["task_id"], "stage": "generation", "successful_model_records": 1, "deterministic_records": 0, "failed_records": 0})
    for stage, (_, folder, files) in STAGES.items():
        tally = Counter()
        for filename in files:
            for call in rows(base / folder / filename):
                called = call.get("model_called", True)
                ok = call["call_status"] == "success"
                tally["successful_model_records" if called and ok else "deterministic_records" if not called and ok else "failed_records"] += 1
                identity = call["call_identity"]
                side = call.get("task", "shared")
                spec = inventory[stage]["prompts"][side]
                assert identity["prompt_sha256"] == spec["sha256"]
                verification["call_prompt_hash_matches"] += 1
                if called:
                    observed[stage]["model_id"].add(call["model_id"])
                    observed[stage]["deployment"].add(call["deployment_name"])
                    observed[stage]["reasoning_effort"].add(call["request_parameters"]["reasoning"]["effort"])
                canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                user = json.dumps(call["dynamic_input"], ensure_ascii=False, sort_keys=stage in ("direct", "integrated", "atomic", "dedup"), separators=(",", ":"))
                messages = [{"role": "system", "content": Path(spec["path"]).read_text()}, {"role": "user", "content": user}]
                recorded_hash = call.get("messages_sha256")
                attempts = call.get("attempts", [])
                if attempts:
                    recorded_hash = attempts[0].get("messages_sha256")
                if recorded_hash:
                    assert digest(canonical(messages).encode()) == recorded_hash, (cid, stage)
                    verification["base_messages_hash_matches"] += 1
        counts.append({"task": case["task_id"], "stage": stage, **{k: tally[k] for k in ["successful_model_records", "deterministic_records", "failed_records"]}})
    for framework in ("ragchecker", "ragas"):
        tallies = defaultdict(Counter)
        for call in rows(base / "evaluation" / framework / "calls.jsonl"):
            assert digest(call["prompt"].encode()) == call["prompt_hash"]
            verification["external_prompt_hash_matches"] += 1
            observed[framework]["deployment"].add(call["model"])
            observed[framework]["reasoning_effort"].add(call["request_parameters"]["reasoning"]["effort"])
            if isinstance(call.get("provider_response"), dict):
                observed[framework]["provider_returned_model"].add(call["provider_response"].get("model"))
            tallies[call["stage"]]["successful_model_records" if call["status"] == "success" else "failed_records"] += 1
        for stage, tally in tallies.items():
            counts.append({"task": case["task_id"], "stage": framework + "/" + stage,
                           **{k: tally[k] for k in ["successful_model_records", "deterministic_records", "failed_records"]}})

for relative in ["config/experiment.json", "config/prompts/generation_prompt_templates.json", "config/tasks.json", "config/queries.json", "config/retrieval/retrieval_algorithm_config_text_embedding_3_large_top200_v1.json", "evidence/embeddings/manifest.json", "config/evaluation/configs/external_evaluation_config.json"]:
    read(BACE / relative)
code_paths = list((BACE / "script/evaluation").glob("*.py")) + [BACE / "script/pipeline.py", BACE / "script/prepare_inputs.py", BACE / "script/prepare_evidence.py", BACE / "script/generation/run_w2_generation.py", Path(__file__).resolve()]
site = BACE / ".venv/lib/python3.11/site-packages"
code_paths += [site / relative for relative in ["refchecker/extractor/extractor_prompts.py", "refchecker/checker/checker_prompts.py", "ragas/metrics/collections/faithfulness/util.py", "ragas/metrics/collections/faithfulness/metric.py", "ragas/prompt/metrics/base_prompt.py"]]
for path in code_paths:
    data = path.read_bytes()
    SOURCES[str(path)] = {"sha256": digest(data), "bytes": len(data)}

summary = {
    "inspection_date": "2026-10-26", "scope": "All saved call records for the twelve Genmab 2019 main-run tasks; not all 1,800 cases.",
    "selection_rule": "Fixed company and year, all twelve tasks; no selection on scores.",
    "counting_rule": "One saved successful record per stage/job; external calls.jsonl records are recorded attempts. Deterministic bypasses are separate. These are not a reconstructed total of network requests or provider-billed calls.",
    "case_ids": ids, "stages": inventory,
    "observed_models": {stage: {key: sorted(v, key=str) for key, v in values.items()} for stage, values in observed.items()},
    "verification": dict(verification), "counts": counts,
}
(OUT / "saved_flow_inventory.json").write_text(json.dumps(summary, indent=2) + "\n")
(OUT / "input_manifest.json").write_text(json.dumps(SOURCES, indent=2) + "\n")
with (OUT / "call_counts.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(counts[0]))
    writer.writeheader()
    writer.writerows(counts)
print(json.dumps({"verification": dict(verification), "observed_models": summary["observed_models"], "first_task_counts": [x for x in counts if x["task"] == "E1-1_transition_plan"]}, indent=2))
