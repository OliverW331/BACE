"""Apply claim edits only after checking explicit IDs and expected old text."""
from copy import deepcopy
import hashlib
import json

from claim_extraction_patches import PatchContractError, apply_unit


def unit_index(claims, label):
    result = []
    for position, claim in enumerate(claims, 1):
        identity = json.dumps([label, position, claim], sort_keys=True, ensure_ascii=False)
        claim_id = "claim_" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        result.append({"claim_id": claim_id, "claim_text": claim["claim_text"]})
    if len({row["claim_id"] for row in result}) != len(result):
        raise PatchContractError("Claim ID collision")
    return result


def make_claim_index(task, draft):
    if task == "ec":
        return {"evidence_results": [
            {"prompt_label": row["prompt_label"],
             "claims": unit_index(row["claims"], row["prompt_label"])}
            for row in draft["evidence_results"]
        ]}
    return {"claims": unit_index(draft["claims"], "disclosure")}


def patch_unit(old, patch, label):
    lookup = {row["claim_id"]: (i, row["claim_text"])
              for i, row in enumerate(unit_index(old["claims"], label), 1)}
    edits = []
    for edit in patch["edits"]:
        positions = []
        for reference in edit["replaces"]:
            match = lookup.get(reference["claim_id"])
            if match is None:
                raise PatchContractError("Unknown claim ID for this source unit")
            position, text = match
            if reference["expected_claim_text"] != text:
                raise PatchContractError("Expected old text does not match the addressed claim")
            positions.append(position)
        edits.append({"replace_indices": positions, "claims": edit["claims"]})
    # apply_unit checks duplicate references, including conflicts between edits.
    claims = apply_unit(old["claims"], edits, patch["additions"])
    update = patch["exclusion_update"]
    if update is None:
        exclusions = deepcopy(old.get("unextracted_spans", []))
    else:
        if not isinstance(update.get("reason"), str) or not update["reason"].strip():
            raise PatchContractError("An explicit exclusion update needs a reason")
        exclusions = deepcopy(update["unextracted_spans"])
    return {"claims": claims, "unextracted_spans": exclusions}


def canonicalize(task, patch, draft, attributions=None):
    if attributions:
        raise PatchContractError("Report attribution must remain in the draft/replacement text")
    if task == "ec":
        originals = draft["evidence_results"]
        if [r["prompt_label"] for r in patch["evidence_results"]] != [r["prompt_label"] for r in originals]:
            raise PatchContractError("Missing, duplicate or reordered evidence labels")
        return {"evidence_results": [
            {"prompt_label": old["prompt_label"], **patch_unit(old, new, old["prompt_label"])}
            for old, new in zip(originals, patch["evidence_results"])
        ]}
    result = patch_unit(draft, patch, "disclosure")
    reason = patch["no_claim_reason"]
    if bool(result["claims"]) != (reason is None):
        raise PatchContractError("No-claim reason contradicts patched claims")
    return {**result, "no_claim_reason": reason}
