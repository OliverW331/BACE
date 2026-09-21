from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'script/evaluation'))
from claim_refinement_lineage import checked_draft, original_source_input
from identified_claim_patches import canonicalize, make_claim_index
from generation_claims import InputValidationError


class StagedDraftLineageTests(unittest.TestCase):
    def setUp(self):
        self.source = {'disclosure_text': 'A reports emissions.', 'context_metadata': {}}
        self.draft = {'claims': [{'claim_text': 'A reports emissions.', 'source_quotes': ['A reports emissions.'], 'unresolved_context': []}], 'no_claim_reason': None, 'unextracted_spans': []}
        self.record = {'task': 'dc', 'dynamic_input': deepcopy(self.source), 'parsed_output': deepcopy(self.draft), 'call_status': 'success', 'api_response': {'status': 'completed'}, 'deployment_name': 'deployment', 'request_parameters': {'store': False}}

    def test_direct_draft_keeps_original_source(self):
        self.assertEqual(checked_draft(self.record, self.source, 'deployment', {'store': False}), self.draft)

    def test_compiled_draft_must_replay_and_keep_original_source(self):
        patch = {'edits': [], 'additions': [], 'exclusion_update': None, 'no_claim_reason': None}
        self.record.update(output_processing_mode='schema_only_identified_patch', parsed_output=patch, canonical_output=canonicalize('dc', patch, self.draft))
        self.record['dynamic_input'].update(draft_extraction=self.draft, draft_claim_index=make_claim_index('dc', self.draft))
        self.assertEqual(original_source_input(self.record), self.source)
        self.assertEqual(checked_draft(self.record, self.source, 'deployment', {'store': False}), self.draft)
        self.record['canonical_output']['claims'][0]['claim_text'] = 'An unrecorded manual correction.'
        with self.assertRaisesRegex(ValueError, 'differs from identified edits'):
            checked_draft(self.record, self.source, 'deployment', {'store': False})

    def test_source_model_and_completion_changes_are_rejected(self):
        for field, value in [('deployment_name', 'other'), ('request_parameters', {}), ('api_response', {'status': 'incomplete'}), ('dynamic_input', {'disclosure_text': 'Changed.'})]:
            with self.subTest(field=field):
                changed = deepcopy(self.record)
                changed[field] = value
                with self.assertRaises(InputValidationError):
                    checked_draft(changed, self.source, 'deployment', {'store': False})


if __name__ == '__main__':
    unittest.main()
