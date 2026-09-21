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

from generation_claims import InputValidationError, OutputValidationError
from run_generation_claim_support_assessment import (
    build_jobs,
    execute_job,
    make_temporary_ids,
    render_messages,
    resolve_model,
    restore_original_ids,
    validate_candidate_selections,
    validate_support_response,
)


class TemporaryIdTests(unittest.TestCase):
    def test_ids_are_deterministic_and_sorted_by_original_id(self) -> None:
        alias_by_original, original_by_alias = make_temporary_ids(
            ["ec-z", "ec-a", "ec-m"],
            prefix="ec",
            minimum_width=3,
        )
        self.assertEqual(alias_by_original["ec-a"], "ec_001")
        self.assertEqual(alias_by_original["ec-m"], "ec_002")
        self.assertEqual(alias_by_original["ec-z"], "ec_003")
        self.assertEqual(original_by_alias["ec_002"], "ec-m")

    def test_build_jobs_sends_only_candidate_ecs(self) -> None:
        ec_rows = [
            {
                "generation_case_id": "case-1",
                "case_id": "metadata-1",
                "ec_id": "ec-z",
                "ec_text": "Evidence Z.",
                "provenance": "must not enter model input",
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
            case_context_by_id={
                "case-1": {
                    "case_id": "metadata-1",
                    "context_metadata": {
                        "company_name": "Acme plc",
                        "target_reporting_year": 2024,
                    },
                }
            },
            candidate_by_dc_id={
                "dc-z": {
                    "dc_claim_id": "dc-z",
                    "candidate_ec_ids": ["ec-z"],
                }
            },
            case_ids=["case-1"],
            requested_dc_ids={"dc-z"},
            max_dcs=None,
            config={
                "assessment": {
                    "temporary_id_min_width": 3,
                    "max_candidate_claims_per_dc": 10,
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
        self.assertEqual(
            list(dynamic_input), ["context_metadata", "dc_claim", "ec_claims"]
        )
        self.assertEqual(
            dynamic_input["context_metadata"],
            {
                "company_name": "Acme plc",
                "target_reporting_year": 2024,
            },
        )
        self.assertEqual(
            dynamic_input["ec_claims"],
            [
                {"ec_claim_id": "ec_002", "ec_text": "Evidence Z."},
            ],
        )
        self.assertEqual(
            dynamic_input["dc_claim"],
            {"dc_claim_id": "dc_002", "dc_text": "Target Z."},
        )
        self.assertNotIn("provenance", json.dumps(dynamic_input))
        self.assertEqual(jobs[0]["candidate_ec_aliases"], ["ec_002"])


class CandidateSelectionInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ec_rows = [
            {"ec_id": "ec-1", "generation_case_id": "case-1"},
            {"ec_id": "ec-2", "generation_case_id": "case-2"},
        ]
        self.dc_rows = [
            {"dc_id": "dc-1", "generation_case_id": "case-1"},
            {"dc_id": "dc-2", "generation_case_id": "case-2"},
        ]

    def test_valid_candidate_selection_is_indexed(self) -> None:
        result = validate_candidate_selections(
            [{"dc_claim_id": "dc-1", "candidate_ec_ids": ["ec-1"]}],
            ec_rows=self.ec_rows,
            dc_rows=self.dc_rows,
            path=Path("candidates.jsonl"),
        )
        self.assertEqual(result["dc-1"]["candidate_ec_ids"], ["ec-1"])

    def test_unknown_cross_case_duplicate_and_extra_fields_are_rejected(self) -> None:
        invalid_rows = [
            [{"dc_claim_id": "dc-unknown", "candidate_ec_ids": []}],
            [{"dc_claim_id": "dc-1", "candidate_ec_ids": ["ec-unknown"]}],
            [{"dc_claim_id": "dc-1", "candidate_ec_ids": ["ec-2"]}],
            [{"dc_claim_id": "dc-1", "candidate_ec_ids": ["ec-1", "ec-1"]}],
            [
                {
                    "dc_claim_id": "dc-1",
                    "candidate_ec_ids": [],
                    "rationale": "not allowed",
                }
            ],
        ]
        for rows in invalid_rows:
            with self.subTest(rows=rows):
                with self.assertRaises(InputValidationError):
                    validate_candidate_selections(
                        rows,
                        ec_rows=self.ec_rows,
                        dc_rows=self.dc_rows,
                        path=Path("candidates.jsonl"),
                    )


class SupportResponseValidationTests(unittest.TestCase):
    def test_valid_response_is_normalized(self) -> None:
        result = validate_support_response(
            {
                "dc_claim_id": "dc_001",
                "support_sets": [
                    {
                        "ec_claim_ids": ["ec_003", "ec_001"],
                        "support_type": "inferred",
                    },
                    {"ec_claim_ids": ["ec_002"], "support_type": "direct"},
                ],
            },
            expected_dc_id="dc_001",
            expected_ec_ids=["ec_001", "ec_002", "ec_003"],
        )
        self.assertEqual(
            result,
            {
                "dc_claim_id": "dc_001",
                "support_sets": [
                    {
                        "ec_claim_ids": ["ec_001", "ec_003"],
                        "support_type": "inferred",
                    },
                    {"ec_claim_ids": ["ec_002"], "support_type": "direct"},
                ],
            },
        )

    def test_empty_support_sets_is_valid(self) -> None:
        result = validate_support_response(
            {"dc_claim_id": "dc_001", "support_sets": []},
            expected_dc_id="dc_001",
            expected_ec_ids=["ec_001"],
        )
        self.assertEqual(result["support_sets"], [])

    def test_wrong_dc_unknown_ec_and_repeated_ec_are_rejected(self) -> None:
        invalid_payloads = [
            {"dc_claim_id": "dc_999", "support_sets": []},
            {
                "dc_claim_id": "dc_001",
                "support_sets": [
                    {"ec_claim_ids": ["ec_999"], "support_type": "direct"}
                ],
            },
            {
                "dc_claim_id": "dc_001",
                "support_sets": [
                    {
                        "ec_claim_ids": ["ec_001", "ec_001"],
                        "support_type": "direct",
                    }
                ],
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(OutputValidationError):
                    validate_support_response(
                        payload,
                        expected_dc_id="dc_001",
                        expected_ec_ids=["ec_001", "ec_002"],
                    )

    def test_duplicate_sets_and_strict_supersets_are_rejected(self) -> None:
        invalid_payloads = [
            {
                "dc_claim_id": "dc_001",
                "support_sets": [
                    {
                        "ec_claim_ids": ["ec_001", "ec_002"],
                        "support_type": "inferred",
                    },
                    {
                        "ec_claim_ids": ["ec_002", "ec_001"],
                        "support_type": "direct",
                    },
                ],
            },
            {
                "dc_claim_id": "dc_001",
                "support_sets": [
                    {"ec_claim_ids": ["ec_001"], "support_type": "direct"},
                    {
                        "ec_claim_ids": ["ec_001", "ec_002"],
                        "support_type": "inferred",
                    },
                ],
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(OutputValidationError):
                    validate_support_response(
                        payload,
                        expected_dc_id="dc_001",
                        expected_ec_ids=["ec_001", "ec_002"],
                    )

    def test_restoration_changes_only_identifiers(self) -> None:
        restored = restore_original_ids(
            {
                "dc_claim_id": "dc_001",
                "support_sets": [
                    {"ec_claim_ids": ["ec_001"], "support_type": "direct"},
                    {
                        "ec_claim_ids": ["ec_002", "ec_003"],
                        "support_type": "inferred",
                    },
                ],
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
                "support_sets": [
                    {
                        "ec_claim_ids": ["ec-original-a"],
                        "support_type": "direct",
                    },
                    {
                        "ec_claim_ids": ["ec-original-b", "ec-original-c"],
                        "support_type": "inferred",
                    },
                ],
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
    def test_messages_contain_only_prompt_and_dynamic_input(self) -> None:
        dynamic_input = {
            "context_metadata": {
                "company_name": "Acme plc",
                "target_reporting_year": 2024,
            },
            "dc_claim": {"dc_claim_id": "dc_001", "dc_text": "Target."},
            "ec_claims": [{"ec_claim_id": "ec_001", "ec_text": "Evidence."}],
        }
        messages = render_messages("Judge support.", dynamic_input)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], {"role": "system", "content": "Judge support."})
        self.assertEqual(json.loads(messages[1]["content"]), dynamic_input)
        self.assertTrue(messages[1]["content"].startswith('{"context_metadata"'))

    def test_execute_job_uses_schema_and_restores_original_ids(self) -> None:
        client = FakeClient(
            FakeResponse(
                {
                    "dc_claim_id": "dc_001",
                    "support_sets": [
                        {"ec_claim_ids": ["ec_001"], "support_type": "direct"}
                    ],
                }
            )
        )
        job = {
            "call_id": "support-test",
            "generation_case_id": "case-1",
            "case_id": "metadata-1",
            "generated_disclosure_id": "disclosure-1",
            "dc_id": "dc-original",
            "dc_alias": "dc_001",
            "ec_original_by_alias": {"ec_001": "ec-original"},
            "candidate_ec_aliases": ["ec_001"],
            "call_identity": {
                "test": True,
                "candidate_ec_ids": ["ec-original"],
            },
            "dynamic_input": {
                "context_metadata": {
                    "company_name": "Acme plc",
                    "target_reporting_year": 2024,
                },
                "dc_claim": {"dc_claim_id": "dc_001", "dc_text": "Target."},
                "ec_claims": [
                    {"ec_claim_id": "ec_001", "ec_text": "Evidence."}
                ],
            },
            "request_parameters": {"store": False},
            "requires_model": True,
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "dc_claim_id": {"type": "string"},
                "support_sets": {"type": "array"},
            },
            "required": ["dc_claim_id", "support_sets"],
        }
        record = execute_job(
            job=job,
            client=client,
            deployment="test-deployment",
            prompt_text="Judge support.",
            schema=schema,
            schema_spec={"structured_output_name": "support_test", "strict": True},
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
                "support_sets": [
                    {"ec_claim_ids": ["ec-original"], "support_type": "direct"}
                ],
            },
        )
        self.assertEqual(record["usage"]["total_tokens"], 120)
        api_call = client.responses.calls[0]
        self.assertEqual(api_call["model"], "test-deployment")
        self.assertTrue(api_call["text"]["format"]["strict"])
        self.assertEqual(len(api_call["input"]), 2)

    def test_empty_candidate_set_skips_model_call(self) -> None:
        client = FakeClient(FakeResponse({"unused": True}))
        job = {
            "call_id": "support-empty-test",
            "generation_case_id": "case-1",
            "case_id": "metadata-1",
            "generated_disclosure_id": "disclosure-1",
            "dc_id": "dc-original",
            "dc_alias": "dc_001",
            "ec_original_by_alias": {"ec_001": "ec-original"},
            "candidate_ec_aliases": [],
            "call_identity": {"candidate_ec_ids": []},
            "dynamic_input": {
                "context_metadata": {
                    "company_name": "Acme plc",
                    "target_reporting_year": 2024,
                },
                "dc_claim": {"dc_claim_id": "dc_001", "dc_text": "Target."},
                "ec_claims": [],
            },
            "request_parameters": {"store": False},
            "requires_model": False,
        }
        record = execute_job(
            job=job,
            client=client,
            deployment="test-deployment",
            prompt_text="Judge support.",
            schema={},
            schema_spec={"structured_output_name": "support_test", "strict": True},
            model_key="test-model",
            model={"model_id": "gpt-5.6-sol", "model_version": "test"},
            config={"runtime": {}},
        )
        self.assertEqual(record["call_status"], "success")
        self.assertFalse(record["model_called"])
        self.assertEqual(record["restored_output"]["support_sets"], [])
        self.assertEqual(record["usage"]["total_tokens"], 0)
        self.assertEqual(client.responses.calls, [])


class AzureRoutingTests(unittest.TestCase):
    def test_support_model_uses_dedicated_environment_triplet(self) -> None:
        config = {
            "current_primary_model": "fallback",
            "current_primary_model_env": "CLAIM_SUPPORT_MODEL_KEY",
            "models": {
                "azure_gpt_5_6_sol": {
                    "provider": "azure_openai",
                    "api_style": "responses",
                    "deployment_name": None,
                    "deployment_name_env": "CLAIM_SUPPORT_AZURE_OPENAI_DEPLOYMENT",
                    "endpoint_env": "CLAIM_SUPPORT_AZURE_OPENAI_ENDPOINT",
                    "api_key_env": "CLAIM_SUPPORT_AZURE_OPENAI_API_KEY",
                }
            },
        }
        environment = {
            "CLAIM_SUPPORT_MODEL_KEY": "azure_gpt_5_6_sol",
            "CLAIM_SUPPORT_AZURE_OPENAI_DEPLOYMENT": "support-deployment",
        }
        with patch.dict("os.environ", environment, clear=False):
            model_key, _model, deployment, _base_url = resolve_model(
                config,
                model_key_override=None,
                dry_run=True,
            )
        self.assertEqual(model_key, "azure_gpt_5_6_sol")
        self.assertEqual(deployment, "support-deployment")


if __name__ == "__main__":
    unittest.main()
