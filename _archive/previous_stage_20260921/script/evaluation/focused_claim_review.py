"""Bind a small review assignment to an unchanged full source and draft."""

import hashlib
import json

from generation_claims import InputValidationError, render_messages, sha256_json
from identified_claim_patches import make_claim_index, PatchContractError


def prompt_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_focus(task, draft, specification):
    index = make_claim_index(task, draft)
    unit = specification.get("source_unit", "disclosure")
    if task == "ec":
        groups = [g for g in index["evidence_results"] if g["prompt_label"] == unit]
        if len(groups) != 1:
            raise InputValidationError("Focus evidence label is missing or ambiguous")
        entries = groups[0]["claims"]
    else:
        if unit != "disclosure":
            raise InputValidationError("DC focus must refer to the disclosure")
        entries = index["claims"]
    positions = specification["positions"]
    if (not positions or len(set(positions)) != len(positions)
            or any(type(p) is not int or not 1 <= p <= len(entries) for p in positions)):
        raise InputValidationError("Focus positions must uniquely address existing claims")
    return [{"source_unit": unit, **entries[p - 1]} for p in positions]


def effective_prompt(base_prompt, focus):
    return base_prompt + "\nASSIGNED CLAIMS (mandatory, exclusive review scope)\n" + json.dumps(
        focus, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def validate_focus_patch(task, payload, focus):
    """Every assignment gets one result; no unassigned assertion can change."""
    expected = {x["claim_id"]: x for x in focus}
    if len(expected) != len(focus) or not expected:
        raise PatchContractError("Focus must contain distinct existing claims")
    used = []
    groups = ([(g["prompt_label"], g) for g in payload["evidence_results"]]
              if task == "ec" else [("disclosure", payload)])
    for label, unit in groups:
        if unit["additions"] or unit["exclusion_update"] is not None:
            raise PatchContractError("Focused binding cannot add claims or mutate exclusions")
        for edit in unit["edits"]:
            if len(edit["replaces"]) != 1 or len(edit["claims"]) != 1:
                raise PatchContractError("Focused binding requires one parent and one result")
            address = edit["replaces"][0]
            item = expected.get(address["claim_id"])
            if (item is None or item["source_unit"] != label
                    or address["expected_claim_text"] != item["claim_text"]):
                raise PatchContractError("Edit falls outside its exact assigned claim")
            used.append(address["claim_id"])
    if len(used) != len(expected) or set(used) != set(expected):
        raise PatchContractError("Every assigned claim must be reviewed exactly once")


def validate_focus_record(record):
    text = record["effective_prompt"]
    if (not text.endswith(effective_prompt("", record["review_assignment"]))
            or prompt_hash(text) != record["call_identity"]["prompt_sha256"]
            or sha256_json(render_messages(text, record["dynamic_input"])) != record["messages_sha256"]):
        raise PatchContractError("Effective focus prompt or request messages changed")
    validate_focus_patch(record["task"], record["parsed_output"], record["review_assignment"])


def locate_exclusion_quotes(exclusions, source):
    """Read-only quote provenance audit; no semantic-fidelity inference."""
    return [{"exclusion_index": i, "quote_index": j, "quote": quote,
             "exact_match": bool(quote) and quote in source,
             "start": source.find(quote) if quote and quote in source else None}
            for i, item in enumerate(exclusions)
            for j, quote in enumerate(item.get("source_quotes", []))]
