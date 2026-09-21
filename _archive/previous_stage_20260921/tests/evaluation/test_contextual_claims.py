from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'script/evaluation'))
from contextual_claims import canonicalize, ContextContractError
from run_contextual_claim_extraction import canonical_call, bind_output
from generation_claims import make_dc_occurrences


def payload():
    return {'claim_groups': [{'context': 'For 2021',
        'stem': 'Mercedes-Benz figures covering Scope 1, Scope 2 and selected Scope 3',
        'source_quotes': ['figures covering Scope 1, Scope 2 and selected Scope 3'],
        'unresolved_context': ['The selected Scope 3 categories are not identified.'],
        'claims': [{'completion': action + ' under Standard X', 'source_quotes': [action],
                    'unresolved_context': []} for action in ('are recorded', 'are published')]}],
        'no_claim_reason': None, 'unextracted_spans': []}


class ContextContractTests(unittest.TestCase):
    def test_each_independent_predicate_inherits_scope_time_and_ambiguity(self):
        native = payload()
        original = deepcopy(native)
        claims = canonicalize('dc', native)['claims']
        self.assertEqual(len(claims), 2)
        for claim in claims:
            self.assertIn('For 2021, Mercedes-Benz figures covering Scope 1, Scope 2 and selected Scope 3', claim['claim_text'])
            self.assertNotIn('Mercedes-Benz Group', claim['claim_text'])
            self.assertEqual(claim['unresolved_context'], native['claim_groups'][0]['unresolved_context'])
            self.assertIn(native['claim_groups'][0]['source_quotes'][0], claim['source_quotes'])
        self.assertEqual(native, original)

    def test_plan_identity_and_modality_survive_every_split(self):
        native = payload()
        native['claim_groups'][0].update(context='Under the 2014–2017 Growth Plan',
            stem='Company A historically intended to')
        for claim in canonicalize('dc', native)['claims']:
            self.assertTrue(claim['claim_text'].startswith('Under the 2014–2017 Growth Plan, Company A historically intended to'))

    def test_ec_source_attribution_does_not_replace_distinct_event_time(self):
        native = {'evidence_results': [{'prompt_label': 'Evidence 1',
            'source_attribution': 'According to the 2018 annual report',
            'claim_groups': payload()['claim_groups'], 'unextracted_spans': []}]}
        for claim in canonicalize('ec', native)['evidence_results'][0]['claims']:
            self.assertIn('According to the 2018 annual report, For 2021,', claim['claim_text'])

    def test_malformed_group_is_not_silently_omitted(self):
        for field, value in [('claims', []), ('stem', None), ('context', None), ('source_quotes', 'bad')]:
            native = payload()
            native['claim_groups'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ContextContractError):
                canonicalize('dc', native)

    def test_empty_shared_stem_preserves_complete_child_sentences(self):
        native = payload()
        native['claim_groups'][0]['stem'] = ''
        native['claim_groups'][0]['claims'][0]['completion'] = 'Company A recorded emissions'
        self.assertEqual(canonicalize('dc', native)['claims'][0]['claim_text'], 'For 2021, Company A recorded emissions.')

    def test_complete_stem_is_retained_and_empty_proposition_is_rejected(self):
        native = payload()
        native['claim_groups'][0]['stem'] = 'Company A recorded emissions'
        native['claim_groups'][0]['claims'][0]['completion'] = ''
        self.assertEqual(canonicalize('dc', native)['claims'][0]['claim_text'], 'For 2021, Company A recorded emissions.')
        native['claim_groups'][0]['stem'] = ''
        with self.assertRaises(ContextContractError): canonicalize('dc', native)

    def test_empty_disclosure_requires_an_explanation(self):
        native = {'claim_groups': [], 'no_claim_reason': None, 'unextracted_spans': []}
        with self.assertRaises(ContextContractError): canonicalize('dc', native)
        native['no_claim_reason'] = 'Only a document heading is present.'
        self.assertEqual(canonicalize('dc', native)['claims'], [])

    def test_legacy_occurrence_keeps_rendered_context_and_native_record(self):
        native = payload()
        record = {'call_id': 'call', 'parsed_output': native, 'canonical_output': canonicalize('dc', native)}
        original = deepcopy(record)
        job = {'call_id': 'call', 'source_text': 'figures covering Scope 1, Scope 2 and selected Scope 3 are recorded and are published',
               'generation_case_id': 'case', 'case_id': 'case', 'generation_output_id': 'output', 'generated_text_hash': 'hash'}
        rows = make_dc_occurrences([job], {'call': canonical_call(record)}, use_parsed_output=True)
        self.assertEqual([r['claim_text'] for r in rows], [c['claim_text'] for c in record['canonical_output']['claims']])
        self.assertEqual(record, original)

    def test_incomplete_provider_response_and_missing_ec_label_fail(self):
        record = {'call_status': 'success', 'parsed_output': payload(), 'api_response': {'status': 'incomplete'}}
        self.assertEqual(bind_output(record, {'task': 'dc'}, {})['call_status'], 'invalid_output')
        record = {'call_status': 'success', 'parsed_output': {'evidence_results': []}, 'api_response': {'status': 'completed'}}
        self.assertEqual(bind_output(record, {'task': 'ec', 'evidence_records': [{'prompt_label': 'Evidence 1'}]}, {})['call_status'], 'invalid_output')


if __name__ == '__main__': unittest.main()
