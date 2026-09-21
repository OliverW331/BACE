from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "script/evaluation"))
from identified_claim_patches import canonicalize, make_claim_index, PatchContractError


class IdentifiedPatchTests(unittest.TestCase):
    def setUp(self):
        self.draft = {
            "claims": [
                {"claim_text": "In 2018, Evonik allocated CapEx of US$50.8 million.", "source_quotes": ["CapEx"], "unresolved_context": []},
                {"claim_text": "Evonik expected cost savings of US$236.3 million.", "source_quotes": ["savings"], "unresolved_context": []},
            ],
            "no_claim_reason": None,
            "unextracted_spans": [{"source_quotes": ["Actions"], "reason": "document_structure", "explanation": "Section title."}],
        }
        self.index = make_claim_index("dc", self.draft)["claims"]

    def patch(self, position=1):
        return {"edits": [{"replaces": [{"claim_id": self.index[position]["claim_id"],
                    "expected_claim_text": self.index[position]["claim_text"]}],
                "claims": [{**self.draft["claims"][1], "unresolved_context": ["Savings period is unspecified."]}],
                "reason": "Record missing savings period."}],
                "additions": [], "exclusion_update": None, "no_claim_reason": None}

    def test_wrong_address_cannot_replace_capex_with_expected_savings(self):
        patch = self.patch()
        patch["edits"][0]["replaces"][0]["claim_id"] = self.index[0]["claim_id"]
        original = deepcopy(self.draft)
        with self.assertRaisesRegex(PatchContractError, "Expected old text"):
            canonicalize("dc", patch, self.draft)
        self.assertEqual(self.draft, original)

    def test_valid_savings_edit_keeps_capex_and_exclusion_trace(self):
        result = canonicalize("dc", self.patch(), self.draft)
        self.assertEqual(result["claims"][0], self.draft["claims"][0])
        self.assertEqual(result["claims"][1]["unresolved_context"], ["Savings period is unspecified."])
        self.assertEqual(result["unextracted_spans"], self.draft["unextracted_spans"])
        result["unextracted_spans"].clear()
        self.assertEqual(len(self.draft["unextracted_spans"]), 1)

    def test_id_binds_original_content_and_keeps_identical_occurrences_distinct(self):
        changed = deepcopy(self.draft)
        changed["claims"][1]["claim_text"] += " Changed."
        with self.assertRaisesRegex(PatchContractError, "Unknown claim ID"):
            canonicalize("dc", self.patch(), changed)
        repeated = {**self.draft, "claims": [self.draft["claims"][0]] * 2}
        ids = make_claim_index("dc", repeated)["claims"]
        self.assertNotEqual(ids[0]["claim_id"], ids[1]["claim_id"])

    def test_conflicting_edits_are_rejected(self):
        patch = self.patch()
        patch["edits"].append(deepcopy(patch["edits"][0]))
        with self.assertRaises(PatchContractError):
            canonicalize("dc", patch, self.draft)

    def test_exclusion_removal_requires_an_explicit_reason(self):
        patch = self.patch()
        patch["exclusion_update"] = {"unextracted_spans": [], "reason": ""}
        with self.assertRaisesRegex(PatchContractError, "needs a reason"):
            canonicalize("dc", patch, self.draft)
        patch["exclusion_update"]["reason"] = "The supposed heading is a substantive assertion, now represented."
        self.assertEqual(canonicalize("dc", patch, self.draft)["unextracted_spans"], [])

    def test_ec_id_cannot_target_another_evidence_card(self):
        draft = {"evidence_results": [{"prompt_label": label, **self.draft} for label in ("Evidence 1", "Evidence 2")]}
        index = make_claim_index("ec", draft)["evidence_results"]
        patch = {"evidence_results": [{"prompt_label": label, "edits": [], "additions": [], "exclusion_update": None} for label in ("Evidence 1", "Evidence 2")]}
        edit = self.patch()["edits"][0]
        edit["replaces"][0]["claim_id"] = index[1]["claims"][1]["claim_id"]
        patch["evidence_results"][0]["edits"] = [edit]
        with self.assertRaisesRegex(PatchContractError, "Unknown claim ID"):
            canonicalize("ec", patch, draft)


if __name__ == "__main__":
    unittest.main()
