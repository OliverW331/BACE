"""Check score denominators and lineage guards with explicit support graphs."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "script/evaluation"))
from summarize_bace_comparison import bace_metrics, external_metrics
from run_bace_comparison_pilot import run_stage


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.ec = [{"ec_id": f"e{i}", "generation_case_id": "case"} for i in range(1, 6)]
        self.dc = [{"dc_id": f"d{i}", "generation_case_id": "case"} for i in range(1, 6)]
        self.support = [
            {"dc_claim_id": "d1", "support_sets": [{"ec_claim_ids": ["e1"], "support_type": "direct"}, {"ec_claim_ids": ["e2", "e3"], "support_type": "inferred"}]},
            {"dc_claim_id": "d2", "support_sets": [{"ec_claim_ids": ["e2", "e3"], "support_type": "inferred"}]},
            {"dc_claim_id": "d3", "support_sets": [{"ec_claim_ids": ["e1", "e4"], "support_type": "direct"}]},
            {"dc_claim_id": "d4", "support_sets": []},
            {"dc_claim_id": "d5", "support_sets": []},
        ]
        self.diagnosis = [{"dc_claim_id": "d4", "unsupported_label": "non_disclosure_statement"},
                          {"dc_claim_id": "d5", "unsupported_label": "factual_boundary_distortion"}]

    def test_support_types_denominators_and_alternative_paths(self):
        result = bace_metrics(self.ec, self.dc, self.support, self.diagnosis)
        self.assertEqual(result["bace_supported_direct"], 2)
        self.assertEqual(result["bace_supported_inferred"], 1)
        self.assertEqual(result["bace_multi_ec_required_dc_count"], 2)
        self.assertAlmostEqual(result["bace_support_rate_all_dc"], 3 / 5)
        self.assertAlmostEqual(result["bace_support_rate_excluding_non_disclosure_sensitivity"], 3 / 4)
        self.assertAlmostEqual(result["bace_eccr"], 4 / 5)
        self.assertAlmostEqual(result["bace_inference_rate"], 1 / 3)

    def test_missing_and_duplicate_support_are_rejected(self):
        for support in (self.support[:-1], self.support + self.support[:1]):
            with self.assertRaises(ValueError):
                bace_metrics(self.ec, self.dc, support, self.diagnosis)

    def test_foreign_support_or_supported_diagnosis_is_rejected(self):
        support = copy.deepcopy(self.support)
        support[0]["support_sets"][0]["ec_claim_ids"] = ["foreign"]
        with self.assertRaises(ValueError):
            bace_metrics(self.ec, self.dc, support, self.diagnosis)
        with self.assertRaises(ValueError):
            bace_metrics(self.ec, self.dc, self.support, self.diagnosis + [{"dc_claim_id": "d1", "unsupported_label": "contradiction"}])

    def test_candidate_stage_cannot_drop_accepted_support(self):
        candidates = [{"dc_claim_id": d["dc_id"], "candidate_ec_ids": []} for d in self.dc]
        with self.assertRaises(ValueError):
            bace_metrics(self.ec, self.dc, self.support, self.diagnosis, candidates)

    def test_zero_sensitivity_denominator_is_missing_not_zero(self):
        result = bace_metrics(self.ec, self.dc[3:4], self.support[3:4], self.diagnosis[:1])
        self.assertEqual(result["bace_support_rate_all_dc"], 0)
        self.assertIsNone(result["bace_support_rate_excluding_non_disclosure_sensitivity"])
        self.assertIsNone(result["bace_inference_rate"])

    def test_external_native_denominator_and_input_hash(self):
        adapted = {key: key for key in ("generation_case_id", "prompt_hash", "response_hash", "context_hash")}
        adapted.update(evidence_ids=["e1"], prompt_labels=["Evidence 1"])
        record = {**adapted, "status": "success", "metric": "faithfulness", "claim_count": 2,
                  "claims": [{"supported": True}, {"supported": False}], "score": 0.5}
        self.assertEqual(external_metrics(record, "ragas", adapted)["ragas_faithfulness"], 0.5)
        with self.assertRaises(ValueError):
            external_metrics({**record, "score": 0.9}, "ragas", adapted)
        with self.assertRaises(ValueError):
            external_metrics({**record, "context_hash": "changed"}, "ragas", adapted)

    def test_failed_subprocess_cannot_feed_next_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("run_bace_comparison_pilot.ROOT", root), patch("run_bace_comparison_pilot.subprocess.run") as run:
                run.return_value.returncode = 1
                with self.assertRaises(RuntimeError):
                    run_stage("runner.py", [], root / "output", "manifest.json", root / "run.log")
                self.assertEqual(run.call_count, 1)

    def test_completed_stage_makes_no_subprocess_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"status": "complete"}))
            with patch("run_bace_comparison_pilot.ROOT", root), patch("run_bace_comparison_pilot.subprocess.run") as run:
                run_stage("runner.py", [], root, "manifest.json", root / "run.log")
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
