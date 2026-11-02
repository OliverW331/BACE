import hashlib
import json
from pathlib import Path


MODEL_IDS = [
    "Qwen/Qwen3.8-27B",
    "google/gemma-4-31B-it",
    "meta-models/Muse-Glimmer-30B",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
]


def main():
    directory = Path(__file__).resolve().parent
    metadata_path = directory / "latest_family_access_checks.json"
    snapshot_path = directory / "SERVER_SNAPSHOT.json"
    metadata_bytes = metadata_path.read_bytes()
    snapshot_bytes = snapshot_path.read_bytes()
    metadata = json.loads(metadata_bytes)
    snapshot = json.loads(snapshot_bytes)
    records = {record["model_id"]: record for record in metadata["records"]}
    gib_bytes = 2**30
    tib_bytes = 2**40
    quota = snapshot["home_quota"]
    remaining_home_bytes = (quota["hard_limit_kib"] - quota["used_kib"]) * 1024
    estimates = []
    for model_id in MODEL_IDS:
        record = records[model_id]
        tensor_count = record["safetensors_total"]
        bf16_bytes = tensor_count * 2
        int4_bytes = tensor_count / 2
        estimates.append(
            {
                "model_id": model_id,
                "revision": record["revision"],
                "source_tensor_count": tensor_count,
                "bf16_payload_bytes": bf16_bytes,
                "bf16_payload_gib": bf16_bytes / gib_bytes,
                "uniform_int4_payload_lower_bound_gib": int4_bytes / gib_bytes,
                "bf16_payload_fits_observed_available_host_ram": bf16_bytes < snapshot["memory"]["mem_available_kib"] * 1024,
                "uniform_int4_payload_fits_remaining_home_quota": int4_bytes < remaining_home_bytes,
                "inference_test_status": "NOT_RUN",
            }
        )
    result = {
        "classification": "COMPUTED_VERIFIED_WEIGHT_PAYLOAD_ESTIMATES_NOT_RUNTIME_MEASUREMENTS",
        "inputs": {
            "model_metadata": {"path": str(metadata_path), "sha256": hashlib.sha256(metadata_bytes).hexdigest()},
            "server_snapshot": {"path": str(snapshot_path), "sha256": hashlib.sha256(snapshot_bytes).hexdigest()},
        },
        "formulas": {
            "bf16_payload_gib": "source_tensor_count * 2 / 2**30",
            "uniform_int4_payload_lower_bound_gib": "source_tensor_count * 0.5 / 2**30",
            "remaining_home_quota_gib": "(hard_limit_kib - used_kib) * 1024 / 2**30",
        },
        "limitations": "Uniform payload estimates only: exclude quantization metadata, mixed-precision tensors, tokenizer/vision files, file headers, KV cache, activations, runtime allocations, concurrency, download duplication and conversion overhead. No throughput or end-to-end BACE runtime estimate is possible without a benchmark.",
        "host_memory_total_tib": snapshot["memory"]["mem_total_kib"] * 1024 / tib_bytes,
        "host_memory_available_tib": snapshot["memory"]["mem_available_kib"] * 1024 / tib_bytes,
        "remaining_home_quota_gib": remaining_home_bytes / gib_bytes,
        "tmp_available_tib": snapshot["disk"]["tmp_available_bytes"] / tib_bytes,
        "models": estimates,
    }
    output_path = directory / "WEIGHT_MEMORY_ESTIMATES.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
