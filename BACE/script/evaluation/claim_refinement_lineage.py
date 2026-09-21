"""Validate a native or compiled extraction before a further review stage."""
from audit_identified_claim_extraction import extraction_view
from generation_claims import InputValidationError


def original_source_input(record):
    return {key: value for key, value in record["dynamic_input"].items()
            if key not in ("draft_extraction", "draft_claim_index")}


def checked_draft(record, source_input, deployment, parameters):
    if record.get("call_status") != "success" or (record.get("api_response") or {}).get("status") != "completed":
        raise InputValidationError("Draft response is not successfully completed")
    if original_source_input(record) != source_input:
        raise InputValidationError("Draft original source differs")
    if record["deployment_name"] != deployment or record["request_parameters"] != parameters:
        raise InputValidationError("Draft model settings differ")
    # extraction_view replays and verifies identified/native patch outputs.
    return extraction_view(record)
