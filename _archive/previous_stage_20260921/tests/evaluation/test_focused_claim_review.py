from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "script/evaluation"))
from focused_claim_review import (effective_prompt, make_focus, prompt_hash,
                                  validate_focus_patch, validate_focus_record,
                                  locate_exclusion_quotes)
from generation_claims import render_messages, sha256_json
from identified_claim_patches import canonicalize, PatchContractError


class FocusedClaimReviewTests(unittest.TestCase):
    def setUp(self):
        self.draft = {"claims": [
            {"claim_text": "Company allocated CapEx of US$50.8 million.", "source_quotes": [], "unresolved_context": []},
            {"claim_text": "The Scope 2 target component represented 9%.", "source_quotes": [], "unresolved_context": []}],
            "unextracted_spans": [], "no_claim_reason": None}
        self.focus = make_focus("dc", self.draft, {"positions": [2]})
        entry = self.focus[0]
        self.patch = {"edits": [{"replaces": [{"claim_id": entry["claim_id"],
                      "expected_claim_text": entry["claim_text"]}],
                      "claims": [{**self.draft["claims"][1], "claim_text": "Company's identified Scope 2 target component represented 9%."}],
                      "reason": "Resolve the company."}],
                      "additions": [], "exclusion_update": None, "no_claim_reason": None}

    def test_assignment_correction_cannot_touch_unrelated_capex(self):
        validate_focus_patch("dc", self.patch, self.focus)
        result = canonicalize("dc", self.patch, self.draft)
        self.assertEqual(result["claims"][0], self.draft["claims"][0])
        wrong = deepcopy(self.patch)
        capex = make_focus("dc", self.draft, {"positions": [1]})[0]
        wrong["edits"][0]["replaces"] = [{"claim_id": capex["claim_id"], "expected_claim_text": capex["claim_text"]}]
        with self.assertRaises(PatchContractError):
            validate_focus_patch("dc", wrong, self.focus)

    def test_missing_or_repeated_assignment_is_not_accepted_as_reviewed(self):
        for edits in ([], self.patch["edits"] * 2):
            with self.subTest(edits=edits), self.assertRaises(PatchContractError):
                validate_focus_patch("dc", {**self.patch, "edits": edits}, self.focus)

    def test_focus_is_bound_to_the_actual_request_without_changing_source(self):
        dynamic = {"context_metadata": {"company_name": "Company"}, "disclosure_text": "Original complete source",
                   "draft_extraction": self.draft}
        text = effective_prompt("Base prompt", self.focus)
        record = {"task": "dc", "effective_prompt": text, "review_assignment": self.focus,
                  "call_identity": {"prompt_sha256": prompt_hash(text)}, "dynamic_input": dynamic,
                  "messages_sha256": sha256_json(render_messages(text, dynamic)), "parsed_output": self.patch}
        before = deepcopy(dynamic)
        validate_focus_record(record)
        self.assertEqual(dynamic, before)
        record["review_assignment"] = make_focus("dc", self.draft, {"positions": [1]})
        with self.assertRaises(PatchContractError):
            validate_focus_record(record)

    def test_absent_exclusion_quote_is_flagged_without_rewriting_native_data(self):
        source = "A damaged table row."
        exclusions = [{"source_quotes": ["table row", "Table extraction requires manual review."]}]
        original = deepcopy(exclusions)
        result = locate_exclusion_quotes(exclusions, source)
        self.assertTrue(result[0]["exact_match"])
        self.assertFalse(result[1]["exact_match"])
        self.assertIsNone(result[1]["start"])
        self.assertEqual(exclusions, original)


if __name__ == "__main__":
    unittest.main()
