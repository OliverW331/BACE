from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'script/evaluation'))
from generation_claims import InputValidationError
from run_claim_extraction_refinement import attach_draft


class DraftLineageTests(unittest.TestCase):
    def setUp(self):
        self.job = {'task': 'dc', 'generation_case_id': 'case-1', 'job_input_hash': 'source-hash',
                    'dynamic_input': {'context_metadata': {'company_name': 'Acme'},
                                      'disclosure_text': 'Acme planned to reduce emissions.'}}
        self.draft = {'task': 'dc', 'job_summary': {'generation_case_id': 'case-1'},
                      'call_id': 'draft-call-1', 'call_status': 'success',
                      'api_response': {'status': 'completed'},
                      'dynamic_input': deepcopy(self.job['dynamic_input']),
                      'parsed_output': {'claims': [{'claim_text': 'Acme reduced emissions.'}]}}

    def test_wrong_source_or_case_cannot_be_used_as_draft(self):
        for mutate in ('source', 'case'):
            draft = deepcopy(self.draft)
            if mutate == 'source': draft['dynamic_input']['disclosure_text'] = 'Different source.'
            else: draft['job_summary']['generation_case_id'] = 'case-2'
            with self.subTest(mutate=mutate), self.assertRaises(InputValidationError):
                attach_draft(self.job, draft)

    def test_incomplete_provider_output_is_not_a_successful_draft(self):
        self.draft['api_response']['status'] = 'incomplete'
        with self.assertRaises(InputValidationError): attach_draft(self.job, self.draft)

    def test_draft_changes_invalidate_job_identity_without_altering_source(self):
        original = deepcopy(self.job)
        first = attach_draft(self.job, self.draft)
        self.draft['parsed_output']['claims'][0]['claim_text'] = 'Acme planned to reduce emissions.'
        second = attach_draft(self.job, self.draft)
        self.assertNotEqual(first['job_input_hash'], second['job_input_hash'])
        self.assertEqual(self.job, original)
        self.assertEqual(second['dynamic_input']['disclosure_text'], original['dynamic_input']['disclosure_text'])
        self.assertIn('draft_extraction', second['dynamic_input'])


if __name__ == '__main__':
    unittest.main()
