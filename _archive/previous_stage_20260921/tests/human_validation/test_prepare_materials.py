"""Exercise sampling, source visibility and preservation of human annotations."""
import copy
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "script/human_validation"))
import prepare_materials as prep


def example_case(number):
    cid = f"case-{number}"
    text = ("# Disclosure\n\nCompany A reported 10 units in 2020.\n\n"
            "Company A planned an action in 2021.\n\n"
            "No baseline was provided in the supplied evidence.\n\n"
            "Company A reported 8 units in 2022.")
    blocks = prep.paragraphs(text)
    cards, ec, dc, classes = [], {}, {}, {}
    for kind in prep.TYPES:
        for j in range(3):
            eid = f"{cid}-{kind}-{j}"
            card = {"evidence_id": eid, "evidence_type": kind,
                    "prompt_label": f"Evidence {len(cards) + 1}",
                    "retrieval_text": f"Visible source {kind} {j}.",
                    "hidden_model_reason": "HIDDEN_EVIDENCE_CANARY"}
            cards.append(card)
            ec[eid] = {"evidence_card_ids": [eid], "ec_text": "HIDDEN_EC_CANARY"}
    for label in prep.CLASSES:
        for j in range(6):
            key = f"{cid}-{label}-{j}"
            dc[key] = {"dc_id": key, "dc_text": f"Target proposition {j}.",
                       "dc_provenance": [{"source_quotes": [blocks[j % len(blocks)]["text"]],
                                          "unresolved_context": ["HIDDEN_CONTEXT_CANARY"]}],
                       "rationale": "HIDDEN_JUDGMENT_CANARY"}
            classes[key] = label
    return {"cid": cid, "case_id": f"Case {number:02d}",
            "input": {"company_name": "Company A", "target_reporting_year": 2022,
                      "task_title": "E1 task", "secret": "HIDDEN_METADATA_CANARY"},
            "adapted": {"response": text,
                        "prompt_labels": [c["prompt_label"] for c in cards],
                        "contexts": [c["prompt_label"] + "\n" + c["retrieval_text"] for c in cards]},
            "dc": dc, "ec": ec, "classes": classes, "cards": cards,
            "paragraphs": blocks, "native_dir": f"native/{cid}"}


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.cases = [example_case(1), example_case(2)]
        self.options = prep.Options()

    def sample(self, cases=None, options=None):
        return prep.sample_units(cases or self.cases, options or self.options)

    def test_reordered_native_records_do_not_change_sample_or_presentation(self):
        expected = self.sample()
        reordered = copy.deepcopy(self.cases[::-1])
        for c in reordered:
            c["dc"] = dict(reversed(list(c["dc"].items())))
            c["classes"] = dict(reversed(list(c["classes"].items())))
            c["cards"].reverse()
        self.assertEqual(expected, self.sample(reordered))
        alternate = self.sample(options=prep.Options(seed=43))
        self.assertNotEqual(expected, alternate)

    def test_strata_counts_and_inclusion_probabilities(self):
        public, private = self.sample()
        prep.validate_packet(public, private, self.options)
        for c in self.cases:
            units = [u for u in private if u["generation_case_id"] == c["cid"]]
            claims = [u for u in units if u["unit_type"] == "claim_support"]
            self.assertEqual(len({u['dc_id'] for u in claims}), 15)
            for label in prep.CLASSES:
                selected = [u for u in claims if u['bace_support_class'] == label]
                self.assertEqual(len(selected), 5)
                self.assertTrue(all(u['inclusion_probability'] == 5 / 6 for u in selected))
            cards = [u for u in units if u["unit_type"] == "ec_source_audit"]
            self.assertEqual(len(cards), 2)
            self.assertTrue(all(u['inclusion_probability'] == 2 / 9 for u in cards))
            blocks = [u for u in units if u["unit_type"] == "dc_source_audit"]
            self.assertEqual(len(blocks), 2)
            self.assertTrue(all(u['inclusion_probability'] == 0.5 for u in blocks))
        counts = prep.Counter(u['evidence_type'] for u in private if 'evidence_type' in u)
        self.assertEqual(set(counts), set(prep.TYPES))
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_card_randomization_uses_marginal_not_realized_type_probability(self):
        # One card per case assigns zero cards to two types, but every type still
        # has a positive probability across the randomized allocation design.
        observed = set()
        for seed in range(12):
            _, units = self.sample(options=prep.Options(seed=seed, cards_per_case=1))
            chosen = [u for u in units if u['unit_type'] == 'ec_source_audit']
            self.assertTrue(all(u['inclusion_probability'] == 1 / 9 for u in chosen))
            observed.update(u['evidence_type'] for u in chosen if u['generation_case_id'] == 'case-1')
        self.assertEqual(observed, set(prep.TYPES))

    def test_insufficient_strata_do_not_fall_back_or_redistribute(self):
        for options in [prep.Options(claims_per_class=7), prep.Options(cards_per_case=10),
                        prep.Options(paragraphs_per_case=5), prep.Options(claims_per_class=0)]:
            with self.assertRaises(ValueError):
                self.sample(options=options)

    def test_private_fields_never_enter_reviewer_files(self):
        public, private = self.sample()
        serialized = json.dumps(public) + prep.render_instructions(public) + prep.csv_text(public)
        self.assertNotIn("HIDDEN_", serialized)
        self.assertNotIn("bace_support_class", serialized)
        self.assertNotIn("inclusion_probability", serialized)
        self.assertNotIn("native/case", serialized)
        self.assertTrue(any("bace_support_class" in u for u in private))
        for source, exported in zip(self.cases, public):
            self.assertEqual(exported['disclosure_text'], source['adapted']['response'])
            self.assertEqual([e['context'] for e in exported['evidence']], source['adapted']['contexts'])

    def test_unexpected_public_fields_and_broken_references_are_rejected(self):
        public, private = self.sample()
        public[0]['units'][0]['rationale'] = 'leaked reasoning'
        with self.assertRaises(ValueError):
            prep.validate_packet(public, private, self.options)
        public, private = self.sample()
        public[0]['units'][0]['source_refs'] = ['Evidence 999']
        with self.assertRaises(ValueError):
            prep.validate_packet(public, private, self.options)

    def test_csv_round_trip_is_blank_and_source_audits_precede_target_claims(self):
        public, _ = self.sample()
        # Multiline text and commas must survive spreadsheet interchange.
        public[0]['units'][0]['target_text'] = 'A, B\n"quoted"'
        for adjudication in [False, True]:
            rows = list(csv.DictReader(io.StringIO(prep.csv_text(public, adjudication))))
            self.assertEqual(len(rows), 38)
            self.assertEqual(rows[0]['target_text'], 'A, B\n"quoted"')
            self.assertTrue(all(r['unit_type'] != 'claim_support' for r in rows[:8]))
            self.assertTrue(all(r['unit_type'] == 'claim_support' for r in rows[8:]))
            answer_fields = prep.ANNOTATION_COLUMNS + (prep.ADJUDICATION_COLUMNS if adjudication else ())
            self.assertTrue(all(row[field] == '' for row in rows for field in answer_fields))

    def test_paragraphs_preserve_offsets_and_table_blocks(self):
        text = '# Heading\n\nFirst paragraph.\nContinued.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n---\n\nLast.'
        blocks = prep.paragraphs(text)
        self.assertEqual(len(blocks), 3)
        self.assertTrue(all(text[b['start']:b['end']] == b['text'] for b in blocks))
        self.assertIn('| 1 | 2 |', blocks[1]['text'])

    def test_quote_locations_keep_duplicates_and_reject_fabricated_quotes(self):
        text = 'Repeated fact.\n\nRepeated fact.'
        claim = {'dc_id': 'd', 'dc_provenance': [{'source_quotes': ['Repeated fact.']}]}
        _, locations, refs = prep.quote_locations(claim, text, prep.paragraphs(text))
        self.assertEqual(len(locations), 2)
        self.assertEqual(refs, ['Paragraph 01', 'Paragraph 02'])
        claim['dc_provenance'][0]['source_quotes'] = ['A fabricated quote.']
        with self.assertRaises(ValueError):
            prep.quote_locations(claim, text, prep.paragraphs(text))

    def test_native_support_alternatives_and_invalid_sets(self):
        record = {'support_sets': [{'ec_claim_ids': ['e1', 'e2'], 'support_type': 'inferred'},
                                   {'ec_claim_ids': ['e3'], 'support_type': 'direct'}]}
        self.assertEqual(prep.support_class(record, {'e1', 'e2', 'e3'}), 'supported_direct')
        record['support_sets'].pop()
        self.assertEqual(prep.support_class(record, {'e1', 'e2'}), 'supported_inferred')
        with self.assertRaises(ValueError):
            prep.support_class(record, {'e1'})
        for ids, label in [([], 'direct'), (['e1', 'e1'], 'direct'), (['e1'], 'unknown')]:
            with self.assertRaises(ValueError):
                prep.support_class({'support_sets': [{'ec_claim_ids': ids, 'support_type': label}]}, {'e1'})
        self.assertEqual(prep.support_class({'support_sets': []}, set()), 'unsupported')

    def test_source_changes_detected_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'source.json'
            path.write_text('{"value": 1}')
            sources = prep.Sources(root)
            expected = prep.digest(path.read_bytes())
            sources.check(path, expected)
            path.write_text('{"value": 2}')
            with self.assertRaises(ValueError):
                sources.verify_again()
            with self.assertRaises(ValueError):
                prep.Sources(root).check(path, expected)

    def test_case_adapter_rejects_unshown_extra_evidence_and_reordered_prompt(self):
        cards = []
        for j in [1, 2]:
            text = f'Visible fact {j}.'
            cards.append({'prompt_label': f'Evidence {j}', 'evidence_id': str(j),
                          'source_label': 'Report', 'retrieval_text': text,
                          'retrieval_text_hash': prep.digest(text), 'shown_in_prompt': True})
        blocks = [f"{c['prompt_label']}\n\nSource:\nReport\n\nText:\n{c['retrieval_text']}" for c in cards]
        prompt = 'Instruction\n\nTask\n\nEvidence\n\nPDF Narrative Evidence\n\n' + '\n\n'.join(blocks)
        case = {'generation_case_id': 'case', 'generation_prompt': prompt,
                'prompt_metadata': {'prompt_hash': prep.digest(prompt)}, 'instruction': 'Task',
                'prompt_evidence': cards, 'company_name': 'A', 'target_reporting_year': 2023, 'task_id': 'E1'}
        output = {'generation_case_id': 'case', 'generation_status': 'success',
                  'prompt_hash': prep.digest(prompt), 'generated_text': 'Answer', 'generated_text_hash': prep.digest('Answer')}
        adapted = prep.adapt_case(case, output)
        self.assertEqual(len(adapted['contexts']), 2)
        case['prompt_evidence'].reverse()
        with self.assertRaises(ValueError):
            prep.adapt_case(case, output)
        case['prompt_evidence'].reverse()
        case['prompt_evidence'].append({**cards[0], 'evidence_id': 'unshown', 'prompt_label': 'Evidence 3'})
        with self.assertRaises(ValueError):
            prep.adapt_case(case, output)

    def test_written_annotations_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'packet'
            files = {name: name + '\n' for name in prep.FILES}
            self.assertEqual(prep.write_packet(output, files), 'created')
            self.assertEqual(prep.write_packet(output, files), 'unchanged')
            annotation = output / 'reviewer_a.csv'
            annotation.write_text('Human work must survive.\n')
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(ValueError):
                prep.write_packet(output, files)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_partial_or_unrelated_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'packet'
            output.mkdir()
            files = {name: name + '\n' for name in prep.FILES}
            (output / 'notes.txt').write_text('Existing notes.')
            with self.assertRaises(ValueError):
                prep.write_packet(output, files)
            self.assertEqual(list(output.iterdir()), [output / 'notes.txt'])

    def test_empty_output_directory_can_receive_complete_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'packet'
            output.mkdir()
            self.assertEqual(prep.write_packet(output, {name: '' for name in prep.FILES}), 'created')
            self.assertEqual({p.name for p in output.iterdir()}, set(prep.FILES))


if __name__ == '__main__':
    unittest.main()
