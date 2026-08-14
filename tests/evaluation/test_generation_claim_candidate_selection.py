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
from run_generation_claim_candidate_selection import (
    build_jobs,
    execute_job,
    resolve_model,
    restore_original_ids,
    validate_candidate_response,
)


class JobConstructionTests(unittest.TestCase):
    def test_job_contains_one_dc_and_complete_ec_set_only(self) -> None:
        ec_rows = [
            {
                "generation_case_id": "case-1",
                "case_id": "metadata-1",
                "ec_id": "ec-z",
                "ec_text": "Evidence Z.",
                "ec_provenance": ["must not enter model input"],
            },
            {
                "generation_case_id": "case-1",
                "case_id": "metadata-1",
                "ec_id": "ec-a",
                "ec_text": "Evidence A.",
            },
        ]
        dc_rows = [
            {
                "generation_case_id": "case-1",
                "case_id": "metadata-1",
                "generated_disclosure_id": "disclosure-1",
                "dc_id": "dc-z",
                "dc_text": "Target Z.",
            },
            {
                "generation_case_id": "case-1",
                "case_id": "metadata-1",
                "generated_disclosure_id": "disclosure-1",
                "dc_id": "dc-a",
                "dc_text": "Target A.",
            },
        ]
        jobs = build_jobs(
            ec_rows=ec_rows,
            dc_rows=dc_rows,
            case_ids=["case-1"],
            requested_dc_ids={"dc-z"},
            max_dcs=None,
            config={
                "selection": {
                    "temporary_id_min_width": 3,
                    "max_evidence_claims_per_case": 10,
                }
            },
            prompt_spec={"version": "prompt-v1", "sha256": "prompt-hash"},
            schema_spec={"version": "schema-v1", "sha256": "schema-hash"},
            model_key="model-key",
            model={"model_id": "model-id", "request_parameters": {}},
            deployment="deployment",
        )
        self.assertEqual(len(jobs), 1)
        dynamic_input = jobs[0]["dynamic_input"]
        self.assertEqual(list(dynamic_input), ["ec_claims", "dc_claim"])
        self.assertEqual(
            dynamic_input["ec_claims"],
            [
                {"ec_claim_id": "ec_001", "ec_text": "Evidence A."},
                {"ec_claim_id": "ec_002", "ec_text": "Evidence Z."},
            ],
        )
        self.assertEqual(
            dynamic_input["dc_claim"],
            {"dc_claim_id": "dc_002", "dc_text": "Target Z."},
        )
        self.assertNotIn("provenance", json.dumps(dynamic_input))


class CandidateResponseValidationTests(unittest.TestCase):
    def test_valid_candidates_are_sorted(self) -> None:
        result = validate_candidate_response(
            {
                "dc_claim_id": "dc_001",
                "candidate_ec_ids": ["ec_003", "ec_001"],
            },
            expected_dc_id="dc_001",
            expected_ec_ids=["ec_001", "ec_002", "ec_003"],
        )
        self.assertEqual(result["candidate_ec_ids"], ["ec_001", "ec_003"])

    def test_empty_candidates_are_valid(self) -> None:
        result = validate_candidate_response(
            {"dc_claim_id": "dc_001", "candidate_ec_ids": []},
            expected_dc_id="dc_001",
            expected_ec_ids=["ec_001"],
        )
        self.assertEqual(result["candidate_ec_ids"], [])

    def test_wrong_dc_unknown_duplicate_and_extra_fields_are_rejected(self) -> None:
        invalid_payloads = [
            {"dc_claim_id": "dc_999", "candidate_ec_ids": []},
            {"dc_claim_id": "dc_001", "candidate_ec_ids": ["ec_999"]},
            {
                "dc_claim_id": "dc_001",
                "candidate_ec_ids": ["ec_001", "ec_001"],
            },
            {
                "dc_claim_id": "dc_001",
                "candidate_ec_ids": [],
                "rationale": "not allowed",
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(OutputValidationError):
                    validate_candidate_response(
                        payload,
                        expected_dc_id="dc_001",
                        expected_ec_ids=["ec_001"],
                    )

    def test_restoration_changes_only_identifiers(self) -> None:
        restored = restore_original_ids(
            {
                "dc_claim_id": "dc_001",
                "candidate_ec_ids": ["ec_001", "ec_003"],
            },
            original_dc_id="dc-original",
            ec_original_by_alias={
                "ec_001": "ec-original-a",
                "ec_002": "ec-original-b",
                "ec_003": "ec-original-c",
            },
        )
        self.assertEqual(
            restored,
            {
                "dc_claim_id": "dc-original",
                "candidate_ec_ids": ["ec-original-a", "ec-original-c"],
            },
        )


class FakeResponse:
    def __init__(self, output: dict) -> None:
        self.output_text = json.dumps(output)

    def model_dump(self) -> dict:
        return {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
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
    def test_execute_job_uses_schema_and_restores_original_ids(self) -> None:
        client = FakeClient(
            FakeResponse(
                {
                    "dc_claim_id": "dc_001",
                    "candidate_ec_ids": ["ec_002", "ec_001"],
                }
            )
        )
        job = {
            "call_id": "candidate-test",
            "generation_case_id": "case-1",
            "case_id": "metadata-1",
            "generated_disclosure_id": "disclosure-1",
            "dc_id": "dc-original",
            "dc_alias": "dc_001",
            "ec_original_by_alias": {
                "ec_001": "ec-original-a",
                "ec_002": "ec-original-b",
            },
            "call_identity": {"test": True},
            "dynamic_input": {
                "ec_claims": [
                    {"ec_claim_id": "ec_001", "ec_text": "Evidence A."},
                    {"ec_claim_id": "ec_002", "ec_text": "Evidence B."},
                ],
                "dc_claim": {"dc_claim_id": "dc_001", "dc_text": "Target."},
            },
            "request_parameters": {"store": False},
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "dc_claim_id": {"type": "string"},
                "candidate_ec_ids": {"type": "array"},
            },
            "required": ["dc_claim_id", "candidate_ec_ids"],
        }
        record = execute_job(
            job=job,
            client=client,
            deployment="test-deployment",
            prompt_text="Select candidates.",
            schema=schema,
            schema_spec={"structured_output_name": "candidate_test", "strict": True},
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
        self.assertEqual(
            record["restored_output"],
            {
                "dc_claim_id": "dc-original",
                "candidate_ec_ids": ["ec-original-a", "ec-original-b"],
            },
        )
        self.assertEqual(record["usage"]["total_tokens"], 120)
        api_call = client.responses.calls[0]
        self.assertEqual(api_call["model"], "test-deployment")
        self.assertTrue(api_call["text"]["format"]["strict"])
        self.assertEqual(len(api_call["input"]), 2)


class AzureRoutingTests(unittest.TestCase):
    def test_candidate_model_uses_dedicated_environment_triplet(self) -> None:
        config = {
            "current_primary_model": "fallback",
            "current_primary_model_env": "CLAIM_CANDIDATE_MODEL_KEY",
            "models": {
                "azure_gpt_5_6_sol": {
                    "provider": "azure_openai",
                    "api_style": "responses",
                    "deployment_name": None,
                    "deployment_name_env": "CLAIM_CANDIDATE_AZURE_OPENAI_DEPLOYMENT",
                    "endpoint_env": "CLAIM_CANDIDATE_AZURE_OPENAI_ENDPOINT",
                    "api_key_env": "CLAIM_CANDIDATE_AZURE_OPENAI_API_KEY",
                }
            },
        }
        environment = {
            "CLAIM_CANDIDATE_MODEL_KEY": "azure_gpt_5_6_sol",
            "CLAIM_CANDIDATE_AZURE_OPENAI_DEPLOYMENT": "candidate-deployment",
        }
        with patch.dict("os.environ", environment, clear=False):
            model_key, _model, deployment, _base_url = resolve_model(
                config,
                model_key_override=None,
                dry_run=True,
            )
        self.assertEqual(model_key, "azure_gpt_5_6_sol")
        self.assertEqual(deployment, "candidate-deployment")


if __name__ == "__main__":
    unittest.main()
