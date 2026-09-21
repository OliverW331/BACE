"""Protect the evidence boundary and run identity of external evaluators."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'script/evaluation/external_evaluation.py'
spec = importlib.util.spec_from_file_location('external_evaluation', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    cards = [
        {'prompt_label': 'Evidence 1', 'evidence_id': 'hidden-id-1', 'source_label': 'Report 2023, p. 8',
         'retrieval_text': 'Scope 1 emissions were 10 tonnes.', 'shown_in_prompt': True, 'secret_score': 99},
        {'prompt_label': 'Evidence 2', 'evidence_id': 'hidden-id-2', 'source_label': 'Published table',
         'retrieval_text': 'Scope 2 emissions were 20 tonnes.', 'shown_in_prompt': True, 'secret_score': 98},
    ]
    blocks = []
    for card, group in zip(cards, ['PDF Narrative Evidence', 'PDF Table Row Evidence']):
        card['retrieval_text_hash'] = module.digest(card['retrieval_text'])
        blocks.append(f"{group}\n\n{card['prompt_label']}\n\nSource:\n{card['source_label']}\n\nText:\n{card['retrieval_text']}")
    instruction = 'Report company emissions for 2023.'
    prompt = 'Instruction\n\n' + instruction + '\n\nEvidence\n\n' + ('\n\n' + '-' * 50 + '\n\n').join(blocks) + '\n'
    case = {'generation_case_id': 'case-1', 'company_name': 'Example', 'target_reporting_year': 2023,
            'task_id': 'E1-6', 'instruction': instruction, 'generation_prompt': prompt,
            'prompt_metadata': {'prompt_hash': module.digest(prompt)}, 'prompt_evidence': cards}
    response = 'Scope 1 and Scope 2 emissions totalled 30 tonnes.'
    output = {'generation_case_id': 'case-1', 'generation_status': 'success', 'prompt_hash': module.digest(prompt),
              'generated_text': response, 'generated_text_hash': module.digest(response)}
    return case, output


class ExternalEvaluationTests(unittest.TestCase):
    def test_visible_context_includes_source_and_group_but_not_hidden_metadata(self):
        case, output = fixture()
        adapted = module.adapt_case(case, output)
        self.assertEqual(len(adapted['contexts']), 2)
        self.assertIn('PDF Table Row Evidence', adapted['contexts'][1])
        self.assertIn('Report 2023, p. 8', adapted['contexts'][0])
        self.assertNotIn('hidden-id', ' '.join(adapted['contexts']))
        self.assertNotIn('secret_score', ' '.join(adapted['contexts']))

    def test_response_change_requires_matching_frozen_hash(self):
        case, output = fixture()
        output['generated_text'] += ' Changed.'
        with self.assertRaisesRegex(ValueError, 'Response hash mismatch'):
            module.adapt_case(case, output)

    def test_card_reordering_is_rejected(self):
        case, output = fixture()
        case['prompt_evidence'].reverse()
        with self.assertRaises(ValueError):
            module.adapt_case(case, output)

    def test_missing_visible_card_cannot_silently_reduce_context(self):
        case, output = fixture()
        case['prompt_evidence'].pop()
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            module.adapt_case(case, output)

    def test_extra_prompt_evidence_cannot_be_ignored(self):
        case, output = fixture()
        case['generation_prompt'] += '\nExtra visible information.'
        case['prompt_metadata']['prompt_hash'] = module.digest(case['generation_prompt'])
        output['prompt_hash'] = case['prompt_metadata']['prompt_hash']
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            module.adapt_case(case, output)

    def test_duplicate_join_keys_are_rejected(self):
        case, _ = fixture()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            module.unique_index([case, copy.deepcopy(case)], 'generation_case_id')

    def test_identity_changes_with_evidence_and_configuration(self):
        case, output = fixture()
        first = module.adapt_case(case, output)
        self.assertNotEqual(module.json_digest(first['contexts']), module.json_digest(first['contexts'][::-1]))
        self.assertNotEqual(module.json_digest({'metric': 'faithfulness'}), module.json_digest({'metric': 'all_metrics'}))

    def test_native_output_schema_is_not_mutated(self):
        schema = {'type': 'object', 'properties': {'statements': {'type': 'array', 'items': {'type': 'string'}}}}
        copied = copy.deepcopy(schema)
        strict = module.strict_schema(schema)
        self.assertEqual(schema, copied)
        self.assertEqual(strict['required'], ['statements'])
        self.assertFalse(strict['additionalProperties'])


if __name__ == '__main__':
    unittest.main()
