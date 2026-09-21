from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SCRIPT_DIR = REPO_ROOT / "script" / "evaluation"
sys.path.insert(0, str(EVALUATION_SCRIPT_DIR))

from generation_claims import (  # noqa: E402
    InputValidationError,
    OutputValidationError,
    annotate_source_quotes,
    build_dc_jobs,
    build_ec_jobs,
    make_dc_occurrences,
    make_ec_occurrences,
    normalize_azure_base_url,
    select_cases,
    sha256_text,
    validate_ec_extraction_response,
    validate_extraction_response,
)
from run_generation_claim_extraction import (  # noqa: E402
    execute_job,
    format_duration,
    load_latest_call_records,
    output_paths,
    prepare_output_directory,
    resolve_model,
    should_skip_on_resume,
)


def make_card(
    *,
    evidence_id: str = "evidence-1",
    prompt_label: str = "Evidence 1",
    text: str | None = None,
) -> dict:
    text = text or "The Group cut emissions by 10% in 2023."
    return {
        "prompt_label": prompt_label,
        "evidence_id": evidence_id,
        "evidence_type": "narrative",
        "source_type": "pdf",
        "source_year": 2023,
        "source_label": "report.pdf | Page 1",
        "source_file": "report.pdf",
        "document_type": "sustainability_report",
        "page_start": 1,
        "page_end": 1,
        "metric": None,
        "value_text": None,
        "unit": None,
        "prompt_rank_from_retrieval": 1,
        "retrieval_text": text,
        "retrieval_text_hash": sha256_text(text),
        "shown_in_prompt": True,
    }


def make_case(
    generation_case_id: str = "generation-case-1",
    *,
    case_id: str = "case-1",
    company_id: str = "company-1",
    company_name: str = "Acme plc",
    card: dict | None = None,
    cards: list[dict] | None = None,
) -> dict:
    evidence_cards = cards or [card or make_card()]
    evidence_blocks = []
    for evidence_card in evidence_cards:
        evidence_blocks.append(
            "\n\n".join(
                [
                    evidence_card["prompt_label"],
                    f"Source:\n{evidence_card['source_label']}",
                    f"Text:\n{evidence_card['retrieval_text']}",
                ]
            )
        )
    generation_prompt = (
        "Instruction\n\nWrite a disclosure.\n\nEvidence\n\n"
        "PDF Narrative Evidence\n\n"
        + "\n\n".join(evidence_blocks)
        + "\n"
    )
    return {
        "schema_version": "w2_generation_cases_v1",
        "generation_case_id": generation_case_id,
        "case_id": case_id,
        "company_id": company_id,
        "company_name": company_name,
        "target_reporting_year": 2023,
        "task_id": "E1-1_transition_plan",
        "task_title": "E1-1 Transition plan for climate change mitigation",
        "prompt_evidence": evidence_cards,
        "generation_prompt": generation_prompt,
        "prompt_metadata": {
            "evidence_count": len(evidence_cards),
            "prompt_hash": sha256_text(generation_prompt),
        },
    }


def make_disclosure(
    generation_case_id: str = "generation-case-1",
    *,
    output_id: str = "output-1",
    text: str = "Acme plc cut emissions by 10% in 2023.",
) -> dict:
    return {
        "schema_version": "generated_disclosure_v1",
        "generation_case_id": generation_case_id,
        "generation_output_id": output_id,
        "generation_status": "success",
        "generated_text": text,
        "generated_text_hash": sha256_text(text),
    }


class ResponseValidationTests(unittest.TestCase):
    def test_quote_annotation_never_rejects_repeated_or_unmatched_text(self) -> None:
        quotes, spans, status = annotate_source_quotes(
            "reporting and reporting", ["reporting", "not in source"]
        )
        self.assertEqual(quotes, ["reporting", "not in source"])
        self.assertEqual(spans[0]["match_count"], 2)
        self.assertEqual(spans[0]["match_status"], "exact_ambiguous")
        self.assertEqual(spans[1]["match_count"], 0)
        self.assertEqual(spans[1]["match_status"], "unmatched")
        self.assertEqual(status, "contains_unmatched_quote")

    def test_valid_response_builds_exact_half_open_offsets(self) -> None:
        source = "The Group cut emissions by 10% in 2023."
        quote = "The Group cut emissions by 10% in 2023"
        payload = {
            "claims": [
                {
                    "claim_text": "Acme plc cut emissions by 10% in 2023.",
                    "source_quotes": [quote],
                    "context_resolutions": [
                        {
                            "surface_form": "The Group",
                            "resolved_value": "Acme plc",
                            "metadata_field": "company_name",
                        }
                    ],
                }
            ],
            "no_claim_reason": None,
        }
        validated = validate_extraction_response(
            payload,
            source_text=source,
            context_metadata={"company_name": "Acme plc", "source_year": "2023"},
            require_unique_quotes=True,
        )
        span = validated["claims"][0]["source_spans"][0]
        self.assertEqual(span["start"], 0)
        self.assertEqual(span["end"], len(quote))
        self.assertEqual(source[span["start"] : span["end"]], quote)

    def test_empty_claims_require_permitted_reason(self) -> None:
        validated = validate_extraction_response(
            {
                "claims": [],
                "no_claim_reason": "insufficient_context_or_extraction_noise",
            },
            source_text="@@ 12 13 @@",
            context_metadata={"company_name": "Acme plc"},
            require_unique_quotes=True,
        )
        self.assertEqual(validated["claims"], [])

        with self.assertRaises(OutputValidationError):
            validate_extraction_response(
                {"claims": [], "no_claim_reason": None},
                source_text="@@ 12 13 @@",
                context_metadata={"company_name": "Acme plc"},
                require_unique_quotes=True,
            )

    def test_non_exact_or_non_unique_quotes_are_rejected(self) -> None:
        base_claim = {
            "claim_text": "A target was stated.",
            "context_resolutions": [],
        }
        with self.assertRaises(OutputValidationError):
            validate_extraction_response(
                {
                    "claims": [{**base_claim, "source_quotes": ["Target"]}],
                    "no_claim_reason": None,
                },
                source_text="target",
                context_metadata={},
                require_unique_quotes=True,
            )

        with self.assertRaises(OutputValidationError):
            validate_extraction_response(
                {
                    "claims": [{**base_claim, "source_quotes": ["target"]}],
                    "no_claim_reason": None,
                },
                source_text="target and target",
                context_metadata={},
                require_unique_quotes=True,
            )

    def test_metadata_resolution_must_match_supplied_value(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_extraction_response(
                {
                    "claims": [
                        {
                            "claim_text": "Another company set a target.",
                            "source_quotes": ["The Group set a target"],
                            "context_resolutions": [
                                {
                                    "surface_form": "The Group",
                                    "resolved_value": "Another company",
                                    "metadata_field": "company_name",
                                }
                            ],
                        }
                    ],
                    "no_claim_reason": None,
                },
                source_text="The Group set a target.",
                context_metadata={"company_name": "Acme plc"},
                require_unique_quotes=True,
            )

    def test_duplicate_claim_occurrence_is_rejected(self) -> None:
        claim = {
            "claim_text": "Acme plc set a target.",
            "source_quotes": ["Acme plc set a target"],
            "context_resolutions": [],
        }
        with self.assertRaises(OutputValidationError):
            validate_extraction_response(
                {"claims": [claim, dict(claim)], "no_claim_reason": None},
                source_text="Acme plc set a target.",
                context_metadata={"company_name": "Acme plc"},
                require_unique_quotes=True,
            )


class GroupedEcResponseValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = build_ec_jobs(
            [
                make_case(
                    cards=[
                        make_card(text="The Committee reviews targets."),
                        make_card(
                            evidence_id="evidence-2",
                            prompt_label="Evidence 2",
                            text="DFSS awards may be reduced.",
                        ),
                    ]
                )
            ]
        )[0]["evidence_records"]

    def test_all_labels_are_validated_in_input_order(self) -> None:
        validated = validate_ec_extraction_response(
            {
                "evidence_results": [
                    {
                        "prompt_label": "Evidence 1",
                        "claims": [
                            {
                                "claim_text": "The Committee reviews targets.",
                                "source_quotes": ["The Committee reviews targets"],
                            }
                        ],
                    },
                    {"prompt_label": "Evidence 2", "claims": []},
                ]
            },
            evidence_records=self.records,
            require_unique_quotes=True,
        )
        self.assertEqual(
            [result["evidence_id"] for result in validated["evidence_results"]],
            ["evidence-1", "evidence-2"],
        )
        self.assertEqual(
            validated["evidence_results"][0]["claims"][0]["source_spans"][0]["start"],
            0,
        )

    def test_missing_reordered_or_unknown_labels_are_rejected(self) -> None:
        invalid_payloads = [
            {"evidence_results": [{"prompt_label": "Evidence 1", "claims": []}]},
            {
                "evidence_results": [
                    {"prompt_label": "Evidence 2", "claims": []},
                    {"prompt_label": "Evidence 1", "claims": []},
                ]
            },
            {
                "evidence_results": [
                    {"prompt_label": "Evidence 1", "claims": []},
                    {"prompt_label": "Evidence 99", "claims": []},
                ]
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(OutputValidationError):
                validate_ec_extraction_response(
                    payload,
                    evidence_records=self.records,
                    require_unique_quotes=True,
                )

    def test_quote_must_belong_to_the_attributed_record(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_ec_extraction_response(
                {
                    "evidence_results": [
                        {
                            "prompt_label": "Evidence 1",
                            "claims": [
                                {
                                    "claim_text": "DFSS awards may be reduced.",
                                    "source_quotes": ["DFSS awards may be reduced"],
                                }
                            ],
                        },
                        {"prompt_label": "Evidence 2", "claims": []},
                    ]
                },
                evidence_records=self.records,
                require_unique_quotes=True,
            )


class JobConstructionTests(unittest.TestCase):
    def test_ec_builds_one_job_per_case_even_when_cards_repeat(self) -> None:
        shared_card = make_card()
        cases = [
            make_case("generation-case-1", case_id="case-1", card=dict(shared_card)),
            make_case("generation-case-2", case_id="case-2", card=dict(shared_card)),
        ]
        jobs = build_ec_jobs(cases)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(len({job["job_input_hash"] for job in jobs}), 2)
        self.assertEqual(
            set(jobs[0]["dynamic_input"]),
            {"context_metadata", "evidence_section"},
        )
        self.assertEqual(
            jobs[0]["dynamic_input"]["context_metadata"],
            {
                "company_name": "Acme plc",
                "target_reporting_year": 2023,
                "task_title": "E1-1 Transition plan for climate change mitigation",
            },
        )

    def test_ec_job_preserves_prompt_order_labels_and_exact_evidence_section(self) -> None:
        cards = [
            make_card(text="First factual statement."),
            make_card(
                evidence_id="evidence-2",
                prompt_label="Evidence 2",
                text="Second factual statement.",
            ),
        ]
        case = make_case(cards=cards)
        job = build_ec_jobs([case])[0]
        self.assertEqual(
            [record["prompt_label"] for record in job["evidence_records"]],
            ["Evidence 1", "Evidence 2"],
        )
        expected_section = case["generation_prompt"].split(
            "\n\nEvidence\n\n", 1
        )[1]
        self.assertEqual(
            job["dynamic_input"]["evidence_section"],
            "Evidence\n\n" + expected_section,
        )
    def test_ec_job_rejects_prompt_card_mismatch(self) -> None:
        case = make_case()
        case["prompt_evidence"][0]["retrieval_text"] = "A different statement."
        case["prompt_evidence"][0]["retrieval_text_hash"] = sha256_text(
            "A different statement."
        )
        with self.assertRaises(InputValidationError):
            build_ec_jobs([case])

    def test_dc_job_uses_one_complete_disclosure(self) -> None:
        case = make_case()
        disclosure = make_disclosure()
        jobs = build_dc_jobs([case], {case["generation_case_id"]: disclosure})
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["dynamic_input"]["disclosure_text"], disclosure["generated_text"])
        self.assertNotIn("prompt_evidence", jobs[0]["dynamic_input"])

    def test_selection_keeps_only_cases_with_successful_disclosures(self) -> None:
        cases = [
            make_case("generation-case-1", case_id="case-1"),
            make_case("generation-case-2", case_id="case-2"),
        ]
        selected, disclosure_map, counts = select_cases(
            cases,
            [make_disclosure("generation-case-1")],
        )
        self.assertEqual([row["generation_case_id"] for row in selected], ["generation-case-1"])
        self.assertEqual(list(disclosure_map), ["generation-case-1"])
        self.assertEqual(counts["matching_cases_without_successful_disclosure"], 1)


class OccurrenceConstructionTests(unittest.TestCase):
    def test_schema_only_occurrences_preserve_unresolved_context_in_both_tasks(self) -> None:
        case = make_case(card=make_card(text="This year, the boundary expanded."))
        disclosure = make_disclosure(text="This year, the boundary expanded.")
        ec_job = build_ec_jobs([case])[0]
        dc_job = build_dc_jobs([case], {case["generation_case_id"]: disclosure})[0]
        claim = {
            "claim_text": "This year, the boundary expanded.",
            "source_quotes": ["This year, the boundary expanded."],
            "context_resolutions": [],
            "unresolved_context": ["The year referred to by 'This year' is unresolved."],
        }
        for task, job, builder in [
            ("ec", ec_job, make_ec_occurrences),
            ("dc", dc_job, make_dc_occurrences),
        ]:
            with self.subTest(task=task):
                job["call_id"] = f"{task}-context-test"
                payload = (
                    {"evidence_results": [{"prompt_label": "Evidence 1", "claims": [claim]}]}
                    if task == "ec" else {"claims": [claim], "no_claim_reason": None}
                )
                result = builder(
                    [job], {job["call_id"]: {"parsed_output": payload}},
                    use_parsed_output=True,
                )[0]
                self.assertEqual(result["unresolved_context"], claim["unresolved_context"])
                self.assertEqual(result["claim_text"], claim["claim_text"])
                self.assertNotIn("2023", result["claim_text"])

    def test_occurrence_ids_and_provenance_are_deterministic(self) -> None:
        ec_job = build_ec_jobs([make_case()])[0]
        ec_job["call_id"] = "ecx-test"
        ec_call = {
            "validated_output": {
                "evidence_results": [
                    {
                        "prompt_label": "Evidence 1",
                        "evidence_id": "evidence-1",
                        "claims": [
                            {
                                "claim_text": "The Group cut emissions by 10% in 2023.",
                                "source_quotes": [
                                    "The Group cut emissions by 10% in 2023"
                                ],
                                "source_spans": [
                                    {
                                        "quote_index": 0,
                                        "quote": "The Group cut emissions by 10% in 2023",
                                        "start": 0,
                                        "end": 42,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        first = make_ec_occurrences([ec_job], {"ecx-test": ec_call})
        second = make_ec_occurrences([ec_job], {"ecx-test": ec_call})
        self.assertEqual(first, second)
        self.assertEqual(first[0]["evidence_id"], "evidence-1")
        self.assertEqual(first[0]["prompt_label"], "Evidence 1")
        self.assertEqual(first[0]["context_resolutions"], [])
        self.assertNotIn("unresolved_context", first[0])

        case = make_case()
        dc_job = build_dc_jobs(
            [case], {case["generation_case_id"]: make_disclosure()}
        )[0]
        dc_job["call_id"] = "dcx-test"
        dc_call = {
            "validated_output": {
                "claims": [
                    {
                        "claim_text": "Acme plc cut emissions by 10% in 2023.",
                        "source_quotes": ["Acme plc cut emissions by 10% in 2023"],
                        "source_spans": [
                            {
                                "quote_index": 0,
                                "quote": "Acme plc cut emissions by 10% in 2023",
                                "start": 0,
                                "end": 42,
                            }
                        ],
                        "context_resolutions": [],
                    }
                ],
                "no_claim_reason": None,
            }
        }
        dc_rows = make_dc_occurrences([dc_job], {"dcx-test": dc_call})
        self.assertEqual(dc_rows[0]["generation_output_id"], "output-1")
        self.assertTrue(dc_rows[0]["dc_occurrence_id"].startswith("dco_"))
        self.assertNotIn("unresolved_context", dc_rows[0])


class AzureEndpointTests(unittest.TestCase):
    def test_azure_endpoint_normalization(self) -> None:
        self.assertEqual(
            normalize_azure_base_url("https://example.cognitiveservices.azure.com/"),
            "https://example.cognitiveservices.azure.com/openai/v1/",
        )
        self.assertEqual(
            normalize_azure_base_url(
                "https://example.openai.azure.com/openai/responses?api-version=preview"
            ),
            "https://example.openai.azure.com/openai/v1/",
        )

    def test_claim_model_and_deployment_can_be_selected_by_environment(self) -> None:
        config = {
            "current_primary_model": "fallback",
            "current_primary_model_env": "CLAIM_EXTRACTION_MODEL_KEY",
            "models": {
                "azure_gpt_5_6_sol": {
                    "provider": "azure_openai",
                    "api_style": "responses",
                    "deployment_name": None,
                    "deployment_name_env": "CLAIM_EXTRACTION_AZURE_OPENAI_DEPLOYMENT",
                    "endpoint_env": "CLAIM_EXTRACTION_AZURE_OPENAI_ENDPOINT",
                    "api_key_env": "CLAIM_EXTRACTION_AZURE_OPENAI_API_KEY",
                }
            },
        }
        environment = {
            "CLAIM_EXTRACTION_MODEL_KEY": "azure_gpt_5_6_sol",
            "CLAIM_EXTRACTION_AZURE_OPENAI_DEPLOYMENT": "claim-deployment",
        }
        with patch.dict("os.environ", environment, clear=False):
            model_key, _model, deployment, _base_url, _endpoint_env = resolve_model(
                config,
                model_key_override=None,
                dry_run=True,
            )
        self.assertEqual(model_key, "azure_gpt_5_6_sol")
        self.assertEqual(deployment, "claim-deployment")


class FakeResponse:
    def __init__(self, output: dict) -> None:
        import json

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
    def test_schema_only_mode_accepts_semantically_unvalidated_output(self) -> None:
        output = {
            "evidence_results": [
                {
                    "prompt_label": "Evidence 1",
                    "claims": [
                        {
                            "claim_text": "A model-produced claim.",
                            "source_quotes": ["not present in the source"],
                        }
                    ],
                }
            ]
        }
        client = FakeClient(FakeResponse(output))
        job = build_ec_jobs([make_case()])[0]
        job["call_id"] = "ecx-schema-only-test"
        job["call_identity"] = {"test": True}
        record = execute_job(
            job=job,
            client=client,
            deployment="test-deployment",
            prompt_text="Extract claims.",
            schema={
                "type": "object",
                "properties": {"evidence_results": {"type": "array"}},
                "required": ["evidence_results"],
            },
            schema_spec={
                "structured_output_name": "claim_response",
                "strict": True,
            },
            model_key="azure_test",
            model={
                "model_id": "gpt-5.6-sol",
                "model_version": "test",
                "request_parameters": {"store": False},
            },
            config={
                "runtime": {"max_network_retries": 0},
                "output_validation": {"mode": "schema_only"},
            },
        )
        self.assertEqual(record["call_status"], "success")
        self.assertEqual(record["validated_output"], output)
        self.assertEqual(record["output_processing_mode"], "schema_only")
        self.assertIsNone(record["validation_error"])

    def test_execute_job_uses_strict_schema_and_validates_output(self) -> None:
        output = {
            "evidence_results": [
                {
                    "prompt_label": "Evidence 1",
                    "claims": [
                        {
                            "claim_text": "Acme plc set a target.",
                            "source_quotes": ["Acme plc set a target"],
                        }
                    ],
                }
            ]
        }
        client = FakeClient(FakeResponse(output))
        job = build_ec_jobs(
            [make_case(card=make_card(text="Acme plc set a target."))]
        )[0]
        job["call_id"] = "ecx-test"
        job["call_identity"] = {"test": True}
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "evidence_results": {"type": "array"},
            },
            "required": ["evidence_results"],
        }
        config = {
            "runtime": {"max_network_retries": 0},
            "output_validation": {"require_unique_source_quotes": True},
        }
        model = {
            "model_id": "gpt-5.6-sol",
            "model_version": "test",
            "request_parameters": {"store": False},
            "task_request_parameters": {"ec": {"max_output_tokens": 4096}},
        }
        record = execute_job(
            job=job,
            client=client,
            deployment="test-deployment",
            prompt_text="Extract claims.",
            schema=schema,
            schema_spec={
                "structured_output_name": "claim_response",
                "strict": True,
            },
            model_key="azure_test",
            model=model,
            config=config,
        )
        self.assertEqual(record["call_status"], "success")
        self.assertEqual(record["usage"]["total_tokens"], 150)
        request = client.responses.calls[0]
        self.assertEqual(request["model"], "test-deployment")
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertEqual(request["max_output_tokens"], 4096)
        self.assertFalse(request["store"])


class ResumeTests(unittest.TestCase):
    def test_resume_skips_only_successful_calls(self) -> None:
        self.assertTrue(should_skip_on_resume({"call_status": "success"}))
        self.assertFalse(should_skip_on_resume({"call_status": "invalid_output"}))
        self.assertFalse(should_skip_on_resume({"call_status": "api_error"}))
        self.assertFalse(should_skip_on_resume(None))

    def test_resume_requires_manifest_and_latest_call_record_wins(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            paths = output_paths(output_dir)
            with self.assertRaises(InputValidationError):
                prepare_output_directory(
                    output_dir=output_dir,
                    paths=paths,
                    resume=True,
                )

            paths["manifest"].write_text(
                json.dumps({"run_fingerprint": "fingerprint"}) + "\n",
                encoding="utf-8",
            )
            previous = prepare_output_directory(
                output_dir=output_dir,
                paths=paths,
                resume=True,
            )
            self.assertEqual(previous["run_fingerprint"], "fingerprint")

            records = [
                {"call_id": "ecx-1", "call_status": "api_error"},
                {"call_id": "ecx-1", "call_status": "success"},
            ]
            paths["ec_calls"].write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            latest, all_records = load_latest_call_records(paths)
            self.assertEqual(latest["ecx-1"]["call_status"], "success")
            self.assertEqual(len(all_records), 2)


class ProgressFormattingTests(unittest.TestCase):
    def test_duration_formatting(self) -> None:
        self.assertEqual(format_duration(9.6), "10s")
        self.assertEqual(format_duration(65), "1m 05s")
        self.assertEqual(format_duration(3661), "1h 01m 01s")


if __name__ == "__main__":
    unittest.main()
