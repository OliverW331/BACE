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
from run_generation_claim_unsupported_diagnosis import (
    UNSUPPORTED_LABELS,
    build_jobs,
    execute_job,
    make_quality_summary,
    resolve_model,
    restore_original_ids,
    validate_candidate_selections,
    validate_diagnosis_response,
    validate_support_assessments,
)


class SupportAssessmentInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dc_rows = [{"dc_id": "dc-1"}, {"dc_id": "dc-2"}]
        self.candidates = {
            "dc-1": {"dc_claim_id": "dc-1", "candidate_ec_ids": ["ec-1"]},
            "dc-2": {"dc_claim_id": "dc-2", "candidate_ec_ids": []},
        }

    def test_valid_support_assessments_are_indexed(self) -> None:
        result = validate_support_assessments(
            [
                {
                    "dc_claim_id": "dc-1",
                    "support_sets": [
                        {"ec_claim_ids": ["ec-1"], "support_type": "direct"}
                    ],
                },
                {"dc_claim_id": "dc-2", "support_sets": []},
            ],
            dc_rows=self.dc_rows,
            candidate_by_dc_id=self.candidates,
            path=Path("support.jsonl"),
        )
        self.assertEqual(result["dc-2"]["support_sets"], [])

    def test_missing_unknown_malformed_and_outside_candidate_are_rejected(self) -> None:
        invalid_inputs = [
            [{"dc_claim_id": "dc-1", "support_sets": []}],
            [
                {"dc_claim_id": "dc-1", "support_sets": []},
                {"dc_claim_id": "dc-unknown", "support_sets": []},
            ],
            [
                {"dc_claim_id": "dc-1", "support_sets": "invalid"},
                {"dc_claim_id": "dc-2", "support_sets": []},
            ],
            [
                {
                    "dc_claim_id": "dc-1",
                    "support_sets": [
                        {"ec_claim_ids": ["ec-other"], "support_type": "direct"}
                    ],
                },
                {"dc_claim_id": "dc-2", "support_sets": []},
            ],
        ]
        for rows in invalid_inputs:
            with self.subTest(rows=rows):
                with self.assertRaises(InputValidationError):
                    validate_support_assessments(
                        rows,
                        dc_rows=self.dc_rows,
                        candidate_by_dc_id=self.candidates,
                        path=Path("support.jsonl"),
                    )


class JobConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ec_rows = [
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
        self.dc_rows = [
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
        self.context = {
            "case-1": {
                "case_id": "metadata-1",
                "context_metadata": {
                    "company_name": "Acme plc",
                    "target_reporting_year": 2024,
                },
            }
        }
        self.candidates = {
            "dc-z": {"dc_claim_id": "dc-z", "candidate_ec_ids": ["ec-z"]},
            "dc-a": {"dc_claim_id": "dc-a", "candidate_ec_ids": ["ec-a"]},
        }
        self.support = {
            "dc-z": {"dc_claim_id": "dc-z", "support_sets": []},
            "dc-a": {
                "dc_claim_id": "dc-a",
                "support_sets": [
                    {"ec_claim_ids": ["ec-a"], "support_type": "direct"}
                ],
            },
        }

    def build(self, **overrides: object) -> list[dict]:
        arguments = {
            "ec_rows": self.ec_rows,
            "dc_rows": self.dc_rows,
            "case_context_by_id": self.context,
            "candidate_by_dc_id": self.candidates,
            "support_by_dc_id": self.support,
            "case_ids": ["case-1"],
            "requested_dc_ids": None,
            "max_dcs": None,
            "config": {
                "diagnosis": {
                    "temporary_id_min_width": 3,
                    "max_candidate_claims_per_dc": 10,
                }
            },
            "prompt_spec": {"version": "prompt-v1", "sha256": "prompt-hash"},
            "schema_spec": {"version": "schema-v1", "sha256": "schema-hash"},
            "model_key": "model-key",
            "model": {"model_id": "model-id", "request_parameters": {}},
            "deployment": "deployment",
        }
        arguments.update(overrides)
        return build_jobs(**arguments)

    def test_only_unsupported_dcs_are_sent_with_candidate_claims(self) -> None:
        jobs = self.build()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["dc_id"], "dc-z")
        self.assertEqual(
            jobs[0]["dynamic_input"],
            {
                "context_metadata": {
                    "company_name": "Acme plc",
                    "target_reporting_year": 2024,
                },
                "dc_claim": {"dc_claim_id": "dc_002", "dc_text": "Target Z."},
                "ec_claims": [
                    {"ec_claim_id": "ec_002", "ec_text": "Evidence Z."}
                ],
            },
        )
        self.assertNotIn("provenance", json.dumps(jobs[0]["dynamic_input"]))

    def test_requesting_supported_dc_is_rejected(self) -> None:
        with self.assertRaisesRegex(InputValidationError, "supported"):
            self.build(requested_dc_ids={"dc-a"})

    def test_empty_candidate_set_still_requires_model_judgment(self) -> None:
        candidates = dict(self.candidates)
        candidates["dc-z"] = {"dc_claim_id": "dc-z", "candidate_ec_ids": []}
        jobs = self.build(candidate_by_dc_id=candidates)
        self.assertEqual(jobs[0]["dynamic_input"]["ec_claims"], [])


class DiagnosisResponseValidationTests(unittest.TestCase):
    def test_every_defined_label_is_valid(self) -> None:
        for label in UNSUPPORTED_LABELS:
            with self.subTest(label=label):
                result = validate_diagnosis_response(
                    {
                        "dc_claim_id": "dc_001",
                        "unsupported_label": label,
                        "rationale": "The evidence does not establish the target fact.",
                    },
                    expected_dc_id="dc_001",
                    forbidden_claim_ids=["dc_001", "ec_001"],
                )
                self.assertEqual(result["unsupported_label"], label)

    def test_wrong_id_label_fields_rationale_and_temporary_ids_are_rejected(self) -> None:
        invalid_payloads = [
            {
                "dc_claim_id": "dc_999",
                "unsupported_label": "unsupported_novelty",
                "rationale": "No evidence anchors the target fact.",
            },
            {
                "dc_claim_id": "dc_001",
                "unsupported_label": "other",
                "rationale": "No evidence anchors the target fact.",
            },
            {
                "dc_claim_id": "dc_001",
                "unsupported_label": "unsupported_novelty",
                "rationale": "",
            },
            {
                "dc_claim_id": "dc_001",
                "unsupported_label": "unsupported_novelty",
                "rationale": "ec_001 does not establish the target fact.",
            },
            {
                "dc_claim_id": "dc_001",
                "unsupported_label": "unsupported_novelty",
                "rationale": "No evidence anchors the target fact.",
                "confidence": 0.9,
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(OutputValidationError):
                    validate_diagnosis_response(
                        payload,
                        expected_dc_id="dc_001",
                        forbidden_claim_ids=["dc_001", "ec_001"],
                    )

    def test_restoration_changes_only_dc_identifier(self) -> None:
        restored = restore_original_ids(
            {
                "dc_claim_id": "dc_001",
                "unsupported_label": "inferential_inflation",
                "rationale": "The target draws a stronger conclusion than the evidence.",
            },
            original_dc_id="dc-original",
        )
        self.assertEqual(restored["dc_claim_id"], "dc-original")
        self.assertEqual(restored["unsupported_label"], "inferential_inflation")


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


def make_job(*, with_candidates: bool) -> dict:
    return {
        "call_id": "diagnosis-test",
        "generation_case_id": "case-1",
        "case_id": "metadata-1",
        "generated_disclosure_id": "disclosure-1",
        "dc_id": "dc-original",
        "dc_alias": "dc_001",
        "ec_original_by_alias": {"ec_001": "ec-original"},
        "candidate_ec_aliases": ["ec_001"] if with_candidates else [],
        "call_identity": {
            "test": True,
            "candidate_ec_ids": ["ec-original"] if with_candidates else [],
        },
        "dynamic_input": {
            "context_metadata": {
                "company_name": "Acme plc",
                "target_reporting_year": 2024,
            },
            "dc_claim": {"dc_claim_id": "dc_001", "dc_text": "Target."},
            "ec_claims": (
                [{"ec_claim_id": "ec_001", "ec_text": "Evidence."}]
                if with_candidates
                else []
            ),
        },
        "request_parameters": {"store": False},
    }


class ModelCallContractTests(unittest.TestCase):
    def test_execute_job_uses_schema_and_restores_original_id(self) -> None:
        client = FakeClient(
            FakeResponse(
                {
                    "dc_claim_id": "dc_001",
                    "unsupported_label": "inferential_inflation",
                    "rationale": "The target draws a stronger conclusion than the evidence.",
                }
            )
        )
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "dc_claim_id": {"type": "string"},
                "unsupported_label": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["dc_claim_id", "unsupported_label", "rationale"],
        }
        record = execute_job(
            job=make_job(with_candidates=True),
            client=client,
            deployment="test-deployment",
            prompt_text="Diagnose.",
            schema=schema,
            schema_spec={"structured_output_name": "diagnosis_test", "strict": True},
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
        self.assertEqual(record["restored_output"]["dc_claim_id"], "dc-original")
        self.assertEqual(record["usage"]["total_tokens"], 120)
        api_call = client.responses.calls[0]
        self.assertEqual(api_call["model"], "test-deployment")
        self.assertTrue(api_call["text"]["format"]["strict"])
        self.assertEqual(
            json.loads(api_call["input"][1]["content"]),
            make_job(with_candidates=True)["dynamic_input"],
        )

    def test_empty_candidates_are_classified_by_model(self) -> None:
        client = FakeClient(
            FakeResponse(
                {
                    "dc_claim_id": "dc_001",
                    "unsupported_label": "non_disclosure_statement",
                    "rationale": "The target states that specified information was not disclosed.",
                }
            )
        )
        record = execute_job(
            job=make_job(with_candidates=False),
            client=client,
            deployment="test-deployment",
            prompt_text="Diagnose.",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "dc_claim_id": {"type": "string"},
                    "unsupported_label": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["dc_claim_id", "unsupported_label", "rationale"],
            },
            schema_spec={"structured_output_name": "diagnosis_test", "strict": True},
            model_key="test-model",
            model={"model_id": "gpt-5.6-sol", "model_version": "test"},
            config={
                "runtime": {
                    "max_network_retries": 0,
                    "max_invalid_output_retries": 0,
                }
            },
        )
        self.assertTrue(record["model_called"])
        self.assertEqual(
            record["restored_output"],
            {
                "dc_claim_id": "dc-original",
                "unsupported_label": "non_disclosure_statement",
                "rationale": "The target states that specified information was not disclosed.",
            },
        )
        self.assertEqual(len(client.responses.calls), 1)
        dynamic_input = json.loads(client.responses.calls[0]["input"][1]["content"])
        self.assertEqual(dynamic_input["ec_claims"], [])


class QualitySummaryTests(unittest.TestCase):
    def test_label_counts_are_exclusive_and_complete(self) -> None:
        jobs = [
            {
                "call_id": "one",
                "generation_case_id": "case-1",
                "candidate_ec_aliases": ["ec_001"],
            },
            {
                "call_id": "two",
                "generation_case_id": "case-1",
                "candidate_ec_aliases": [],
            },
        ]
        calls = {
            "one": {"call_status": "success", "model_called": True},
            "two": {"call_status": "success", "model_called": True},
        }
        results = [
            {
                "dc_claim_id": "dc-1",
                "unsupported_label": "inferential_inflation",
                "rationale": "Reason one.",
            },
            {
                "dc_claim_id": "dc-2",
                "unsupported_label": "non_disclosure_statement",
                "rationale": "Reason two.",
            },
        ]
        summary = make_quality_summary(
            jobs=jobs,
            latest_calls=calls,
            all_call_records=[],
            results=results,
            dry_run=False,
        )
        self.assertEqual(summary["diagnosis_result_count"], 2)
        self.assertEqual(summary["model_calls_planned"], 2)
        self.assertNotIn("deterministic_novelty_jobs_planned", summary)
        self.assertEqual(
            summary["unsupported_label_counts"]["non_disclosure_statement"], 1
        )
        self.assertEqual(sum(summary["unsupported_label_counts"].values()), 2)
        self.assertAlmostEqual(sum(summary["unsupported_label_rates"].values()), 1.0)


class AzureRoutingTests(unittest.TestCase):
    def test_diagnosis_model_uses_dedicated_environment_triplet(self) -> None:
        config = {
            "current_primary_model": "fallback",
            "current_primary_model_env": "CLAIM_DIAGNOSIS_MODEL_KEY",
            "models": {
                "azure_gpt_5_6_sol": {
                    "provider": "azure_openai",
                    "api_style": "responses",
                    "deployment_name": None,
                    "deployment_name_env": "CLAIM_DIAGNOSIS_AZURE_OPENAI_DEPLOYMENT",
                    "endpoint_env": "CLAIM_DIAGNOSIS_AZURE_OPENAI_ENDPOINT",
                    "api_key_env": "CLAIM_DIAGNOSIS_AZURE_OPENAI_API_KEY",
                }
            },
        }
        with patch.dict(
            "os.environ",
            {
                "CLAIM_DIAGNOSIS_MODEL_KEY": "azure_gpt_5_6_sol",
                "CLAIM_DIAGNOSIS_AZURE_OPENAI_DEPLOYMENT": "diagnosis-deployment",
            },
            clear=False,
        ):
            model_key, _model, deployment, _base_url = resolve_model(
                config,
                model_key_override=None,
                dry_run=True,
            )
        self.assertEqual(model_key, "azure_gpt_5_6_sol")
        self.assertEqual(deployment, "diagnosis-deployment")


if __name__ == "__main__":
    unittest.main()
