from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SCRIPT_DIR = REPO_ROOT / "script" / "evaluation"
if str(EVALUATION_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_SCRIPT_DIR))

from generation_claims import OutputValidationError
from run_generation_claim_semantic_dedup import (
    build_jobs,
    execute_job,
    make_exact_units,
    make_semantic_claim_records,
    normalize_claim_text,
    resolve_model,
    validate_partition_response,
)


class ExactGroupingTests(unittest.TestCase):
    def test_normalization_is_conservative_and_exact_units_keep_occurrences(self) -> None:
        rows = [
            {
                "generation_case_id": "case-1",
                "ec_occurrence_id": "eco-2",
                "claim_text": "  Admiral\u00a0Group reports emissions. ",
            },
            {
                "generation_case_id": "case-1",
                "ec_occurrence_id": "eco-1",
                "claim_text": "admiral group reports emissions.",
            },
        ]
        self.assertEqual(
            normalize_claim_text(rows[0]["claim_text"]),
            "admiral group reports emissions.",
        )
        units = make_exact_units(rows, kind="ec", generation_case_id="case-1")
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["occurrence_ids"], ["eco-1", "eco-2"])
        self.assertEqual(units[0]["occurrence_count"], 2)

    def test_llm_dynamic_input_contains_only_opaque_ids_and_claim_text(self) -> None:
        rows = [
            {
                "generation_case_id": "case-1",
                "ec_occurrence_id": "eco-1",
                "claim_text": "Claim one.",
            },
            {
                "generation_case_id": "case-1",
                "ec_occurrence_id": "eco-2",
                "claim_text": "Claim two.",
            },
        ]
        jobs = build_jobs(
            rows_by_kind={"ec": rows},
            case_ids=["case-1"],
            config={
                "deduplication": {"max_claim_units_per_case_and_kind": 400}
            },
            prompt_spec={"version": "prompt-v2", "sha256": "prompt-hash"},
            schema_spec={"version": "schema-v1", "sha256": "schema-hash"},
            model_key="model-key",
            model={"model_id": "model-id", "request_parameters": {}},
            deployment="deployment",
        )
        self.assertEqual(set(jobs[0]["dynamic_input"]), {"claim_units"})
        self.assertTrue(jobs[0]["dynamic_input"]["claim_units"])
        for unit in jobs[0]["dynamic_input"]["claim_units"]:
            self.assertEqual(set(unit), {"unit_id", "claim_text"})


class PartitionValidationTests(unittest.TestCase):
    def test_valid_partition_is_sorted_and_complete(self) -> None:
        result = validate_partition_response(
            {
                "groups": [
                    {
                        "canonical_unit_id": "u2",
                        "member_unit_ids": ["u2", "u1"],
                    },
                    {
                        "canonical_unit_id": "u3",
                        "member_unit_ids": ["u3"],
                    },
                ]
            },
            expected_unit_ids=["u1", "u2", "u3"],
        )
        self.assertEqual(result["groups"][0]["member_unit_ids"], ["u1", "u2"])

    def test_partition_rejects_missing_or_repeated_units(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_partition_response(
                {
                    "groups": [
                        {"canonical_unit_id": "u1", "member_unit_ids": ["u1"]}
                    ]
                },
                expected_unit_ids=["u1", "u2"],
            )
        with self.assertRaises(OutputValidationError):
            validate_partition_response(
                {
                    "groups": [
                        {"canonical_unit_id": "u1", "member_unit_ids": ["u1"]},
                        {"canonical_unit_id": "u1", "member_unit_ids": ["u1"]},
                    ]
                },
                expected_unit_ids=["u1"],
            )


class MaterializationTests(unittest.TestCase):
    def test_ec_merge_preserves_all_evidence_provenance(self) -> None:
        rows = []
        for index in (1, 2):
            rows.append(
                {
                    "generation_case_id": "case-1",
                    "case_id": "case-metadata-1",
                    "ec_occurrence_id": f"eco-{index}",
                    "claim_text": (
                        "Admiral Group reports emissions."
                        if index == 1
                        else "Emissions are reported by Admiral Group."
                    ),
                    "evidence_id": f"evidence-{index}",
                    "prompt_label": f"Evidence {index}",
                    "retrieval_text_hash": f"hash-{index}",
                    "source_spans": [{"quote": "source", "start": 0, "end": 6}],
                    "context_resolutions": [],
                    "evidence_provenance": {"evidence_id": f"evidence-{index}"},
                }
            )
        job = {
            "claim_kind": "ec",
            "generation_case_id": "case-1",
            "call_id": "ecdup-test",
            "units": [
                {
                    "unit_id": "u1",
                    "claim_text": rows[0]["claim_text"],
                    "representative_occurrence_id": "eco-1",
                    "occurrence_ids": ["eco-1"],
                },
                {
                    "unit_id": "u2",
                    "claim_text": rows[1]["claim_text"],
                    "representative_occurrence_id": "eco-2",
                    "occurrence_ids": ["eco-2"],
                },
            ],
        }
        records = make_semantic_claim_records(
            job=job,
            validated_output={
                "groups": [
                    {
                        "canonical_unit_id": "u1",
                        "member_unit_ids": ["u1", "u2"],
                    }
                ]
            },
            occurrence_rows=rows,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["ec_text"], rows[0]["claim_text"])
        self.assertEqual(records[0]["evidence_card_ids"], ["evidence-1", "evidence-2"])
        self.assertEqual(len(records[0]["ec_provenance"]), 2)
        self.assertEqual(records[0]["semantic_dedup"]["merge_type"], "semantic_merge")


class FakeResponse:
    def __init__(self, output: dict) -> None:
        self.output_text = json.dumps(output)

    def model_dump(self) -> dict:
        return {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            }
        }


class FakeResponses:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> FakeResponse:
        self.calls.append(dict(kwargs))
        return self.response


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.responses = FakeResponses(response)


class ModelCallContractTests(unittest.TestCase):
    def test_execute_job_uses_strict_schema_and_validates_partition(self) -> None:
        output = {
            "groups": [
                {"canonical_unit_id": "u1", "member_unit_ids": ["u1", "u2"]}
            ]
        }
        client = FakeClient(FakeResponse(output))
        job = {
            "claim_kind": "dc",
            "generation_case_id": "case-1",
            "call_id": "dcdup-test",
            "call_identity": {"test": True},
            "dynamic_input": {
                "claim_units": [],
            },
            "units": [
                {"unit_id": "u1"},
                {"unit_id": "u2"},
            ],
            "request_parameters": {"store": False},
            "requires_model": True,
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"groups": {"type": "array"}},
            "required": ["groups"],
        }
        record = execute_job(
            job=job,
            client=client,
            deployment="test-deployment",
            prompt_text="Partition claims.",
            schema=schema,
            schema_spec={
                "structured_output_name": "dedup_test",
                "strict": True,
            },
            model_key="test-model",
            model={"model_id": "gpt-5.6-sol", "model_version": "test"},
            config={
                "runtime": {
                    "max_network_retries": 0,
                    "max_invalid_output_retries": 0,
                }
            },
        )
        self.assertEqual(record["call_status"], "success")
        self.assertEqual(record["usage"]["total_tokens"], 150)
        api_call = client.responses.calls[0]
        self.assertEqual(api_call["model"], "test-deployment")
        self.assertTrue(api_call["text"]["format"]["strict"])


class AzureRoutingTests(unittest.TestCase):
    def test_dedup_model_uses_dedicated_environment_triplet(self) -> None:
        config = {
            "current_primary_model": "fallback",
            "current_primary_model_env": "CLAIM_DEDUP_MODEL_KEY",
            "models": {
                "azure_gpt_5_6_sol": {
                    "provider": "azure_openai",
                    "api_style": "responses",
                    "deployment_name": None,
                    "deployment_name_env": "CLAIM_DEDUP_AZURE_OPENAI_DEPLOYMENT",
                    "endpoint_env": "CLAIM_DEDUP_AZURE_OPENAI_ENDPOINT",
                    "api_key_env": "CLAIM_DEDUP_AZURE_OPENAI_API_KEY",
                }
            },
        }
        environment = {
            "CLAIM_DEDUP_MODEL_KEY": "azure_gpt_5_6_sol",
            "CLAIM_DEDUP_AZURE_OPENAI_DEPLOYMENT": "dedup-deployment",
        }
        with patch.dict("os.environ", environment, clear=False):
            model_key, _model, deployment, _base_url = resolve_model(
                config,
                model_key_override=None,
                dry_run=True,
            )
        self.assertEqual(model_key, "azure_gpt_5_6_sol")
        self.assertEqual(deployment, "dedup-deployment")


if __name__ == "__main__":
    unittest.main()
