"""Validated BACE and native framework metric calculations reused from the prior stage."""

from collections import Counter

LABELS = ("non_disclosure_statement", "contradiction", "evidence_conflation", "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty")

def index(records, key):
    result = {r[key]: r for r in records}
    if len(result) != len(records):
        raise ValueError(f"Duplicate {key}")
    return result

def ratio(numerator, denominator):
    return numerator / denominator if denominator else None

def bace_metrics(ec_rows, dc_rows, support_rows, diagnosis_rows, candidate_rows=None):
    ecs, dcs = index(ec_rows, "ec_id"), index(dc_rows, "dc_id")
    support = index(support_rows, "dc_claim_id")
    diagnosis = index(diagnosis_rows, "dc_claim_id")
    if not dcs or not ecs or set(support) != set(dcs):
        raise ValueError("Empty claims or incomplete/foreign support judgments")
    candidates = index(candidate_rows, "dc_claim_id") if candidate_rows is not None else None
    if candidates is not None and set(candidates) != set(dcs):
        raise ValueError("Incomplete/foreign candidate selections")
    used, unsupported = set(), set()
    direct = inferred = multi_required = 0
    for dc_id, record in support.items():
        sets = record["support_sets"]
        if not sets:
            unsupported.add(dc_id)
        elif any(s["support_type"] == "direct" for s in sets):
            direct += 1
        else:
            inferred += 1
        multi_required += bool(sets) and all(len(s["ec_claim_ids"]) > 1 for s in sets)
        if candidates is not None:
            candidate_ids = candidates[dc_id]["candidate_ec_ids"]
            if len(set(candidate_ids)) != len(candidate_ids) or not set(candidate_ids) <= set(ecs):
                raise ValueError("Duplicate or foreign candidate EC")
        for support_set in sets:
            ids = support_set["ec_claim_ids"]
            if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(ecs):
                raise ValueError("Empty, duplicate or foreign support EC")
            if support_set["support_type"] not in ("direct", "inferred"):
                raise ValueError("Unknown support type")
            if any(ecs[e]["generation_case_id"] != dcs[dc_id]["generation_case_id"] for e in ids):
                raise ValueError("Cross-case support edge")
            if candidates is not None and not set(ids) <= set(candidate_ids):
                raise ValueError("Support EC absent from candidates")
            used.update(ids)
    if set(diagnosis) != unsupported:
        raise ValueError("Diagnoses must partition exactly the unsupported DCs")
    labels = Counter(r["unsupported_label"] for r in diagnosis.values())
    if set(labels) - set(LABELS):
        raise ValueError("Unknown diagnosis label")
    supported = direct + inferred
    return {"bace_dc_count": len(dcs), "bace_supported_direct": direct,
            "bace_supported_inferred": inferred, "bace_unsupported": len(unsupported),
            "bace_non_disclosure_statement": labels["non_disclosure_statement"],
            "bace_support_rate_all_dc": supported / len(dcs),
            "bace_support_rate_excluding_non_disclosure_sensitivity": ratio(supported, len(dcs) - labels["non_disclosure_statement"]),
            "bace_multi_ec_required_dc_count": multi_required,
            **{f"bace_{label}": labels[label] for label in LABELS[1:]},
            "bace_ec_count": len(ecs), "bace_used_ec_count": len(used),
            "bace_eccr": len(used) / len(ecs), "bace_inference_rate": ratio(inferred, supported)}

def external_metrics(record, framework, adapted):
    if record["status"] != "success" or record["metric"] != "faithfulness":
        raise ValueError("External result is not a successful faithfulness evaluation")
    for key in ("generation_case_id", "prompt_hash", "response_hash", "context_hash", "evidence_ids", "prompt_labels"):
        if record[key] != adapted[key]:
            raise ValueError(f"External input differs: {key}")
    claims = record["claims"]
    if not claims or len(claims) != record["claim_count"] or any(type(c["supported"]) is not bool for c in claims):
        raise ValueError("Invalid external claim denominator or verdict")
    supported = sum(c["supported"] for c in claims)
    if abs(supported / len(claims) - record["score"]) > 1e-12:
        raise ValueError("External native score does not match verdicts")
    return {f"{framework}_claim_count": len(claims), f"{framework}_supported": supported,
            f"{framework}_faithfulness": record["score"]}
