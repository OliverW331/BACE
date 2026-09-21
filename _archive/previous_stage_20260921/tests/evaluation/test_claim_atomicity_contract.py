"""Regressions for unsafe mutations by the final splitting pass."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "script/evaluation"))
from identified_claim_patches import canonicalize, make_claim_index


def validator(kind):
    path = ROOT / "config/evaluation/schemas" / f"generation_{kind}_claim_atomicity_review_response_schema_v1.json"
    return Draft202012Validator(json.loads(path.read_text()))


def claim(text):
    return {"claim_text": text, "source_quotes": [text],
            "context_resolutions": [], "unresolved_context": []}


class AtomicityContractTests(unittest.TestCase):
    def test_empty_unidentified_table_cannot_gain_transcription_claims(self):
        exclusion = {"source_quotes": ["Genmab A/S; 2018 = 96.3"],
                     "reason": "missing_proposition", "explanation": "No metric is identified."}
        draft = {"evidence_results": [{"prompt_label": "Evidence 14", "claims": [],
                                      "unextracted_spans": [exclusion]}]}
        response = {"evidence_results": [{"prompt_label": "Evidence 14", "edits": [],
                                         "additions": [], "exclusion_update": None}]}
        validator("ec").validate(response)
        result = canonicalize("ec", response, draft)
        self.assertEqual(result["evidence_results"][0]["claims"], [])
        self.assertEqual(result["evidence_results"][0]["unextracted_spans"], [exclusion])
        response["evidence_results"][0]["additions"] = [{
            "claim_text": "The table reports a 2018 value of 96.3 for Genmab A/S.",
            "source_quotes": ["Genmab A/S; 2018 = 96.3"],
            "unresolved_context": ["The metric and unit are not supplied."]}]
        with self.assertRaises(ValidationError):
            validator("ec").validate(response)

    def setUp(self):
        self.draft = {"claims": [claim("Company calculated Scope 1 and Scope 2 emissions under Protocol P."),
                                 claim("In 2018, Company allocated CapEx of US$50.8 million.")],
                      "unextracted_spans": [{"source_quotes": ["Actions"],
                                             "reason": "document_structure", "explanation": "Heading."}],
                      "no_claim_reason": None}
        entries = make_claim_index("dc", self.draft)["claims"]
        self.addresses = [{"claim_id": e["claim_id"], "expected_claim_text": e["claim_text"]} for e in entries]
        self.response = {"edits": [{"replaces": [self.addresses[0]],
                                    "claims": [claim("Company calculated Scope 1 emissions under Protocol P."),
                                               claim("Company calculated Scope 2 emissions under Protocol P.")],
                                    "reason": "Separate the two method applications."}],
                         "additions": [], "exclusion_update": None, "no_claim_reason": None}

    def test_valid_split_preserves_unrelated_capex_and_exclusions(self):
        validator("dc").validate(self.response)
        before = deepcopy(self.draft)
        result = canonicalize("dc", self.response, self.draft)
        self.assertEqual(result["claims"][-1], self.draft["claims"][1])
        self.assertEqual(result["unextracted_spans"], self.draft["unextracted_spans"])
        self.assertEqual(self.draft, before)

    def test_splitting_cannot_erase_claims_merge_capex_or_clear_exclusions(self):
        erase = deepcopy(self.response)
        erase["edits"][0]["claims"] = []
        merge = deepcopy(self.response)
        merge["edits"][0]["replaces"].append(self.addresses[1])
        clear = deepcopy(self.response)
        clear["exclusion_update"] = {"unextracted_spans": [], "reason": "Clear old exclusions."}
        for response in (erase, merge, clear):
            with self.subTest(response=response), self.assertRaises(ValidationError):
                validator("dc").validate(response)


if __name__ == "__main__":
    unittest.main()
