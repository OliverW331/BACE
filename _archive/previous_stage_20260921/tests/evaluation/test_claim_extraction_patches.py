from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'script/evaluation'))
from claim_extraction_patches import apply_unit, canonicalize, report_attribution, PatchContractError


def claim(text): return {'claim_text':text,'source_quotes':[text],'unresolved_context':[]}


class PatchContractTests(unittest.TestCase):
    def test_unchanged_claims_are_not_regenerated(self):
        draft=[claim('A measured 5 tonnes in 2021.'),claim('A measured 6 tonnes in 2022.')]
        original=deepcopy(draft)
        result=apply_unit(draft,[],[])
        self.assertEqual(result,draft)
        result[0]['source_quotes'].append('new')
        self.assertEqual(draft,original)

    def test_split_and_add_preserve_unrelated_claims(self):
        draft=[claim('A monitors and reports emissions.'),claim('A set a target in 2018.')]
        edits=[{'replace_indices':[1],'claims':[claim('A monitors emissions.'),claim('A reports emissions.')],'reason':'Independent predicates.'}]
        result=apply_unit(draft,edits,[claim('The target deadline is 2030.')])
        self.assertEqual(result[2],draft[1])
        self.assertEqual(len(result),4)
        self.assertEqual(result[0]['claim_text'],'A monitors emissions.')

    def test_invalid_or_conflicting_indexes_fail_without_deleting_data(self):
        for indexes in [[],[0],[2],[1,1],[True]]:
            with self.subTest(indexes=indexes), self.assertRaises(PatchContractError):
                apply_unit([claim('A acts.')],[{'replace_indices':indexes,'claims':[]}],[])
        with self.assertRaises(PatchContractError):
            apply_unit([claim('A acts.')],[{'replace_indices':[1],'claims':[]},{'replace_indices':[1],'claims':[]}],[])

    def test_report_attribution_does_not_assign_an_event_year(self):
        attribution=report_attribution('opaque_2018_SR.pdf | Page 3')
        row=apply_unit([claim('A planned action in 2019.')],[],[],attribution)[0]
        self.assertEqual(row['claim_text'],'According to the 2018 report, A planned action in 2019.')
        self.assertEqual(report_attribution('Corporate Sustainability Tracker | Source year 2018'),'')
        self.assertEqual(report_attribution('opaque_id_2018_without_report.pdf'),'')

    def test_local_modifier_edits_cannot_change_unedited_siblings(self):
        draft=[claim('A will continue to monitor regulations.'),claim('A will update policies.'),claim('A will conduct training as appropriate.')]
        result=apply_unit(draft,[{'replace_indices':[2],'claims':[claim('A will update its compliance policies.')]}],[])
        self.assertEqual(result[0],draft[0]);self.assertEqual(result[2],draft[2])

    def test_coverage_and_empty_disclosure_contract(self):
        draft={'evidence_results':[{'prompt_label':'Evidence 1','claims':[]}]}
        with self.assertRaises(PatchContractError):canonicalize('ec',{'evidence_results':[]},draft)
        with self.assertRaises(PatchContractError):canonicalize('dc',{'edits':[],'additions':[],'unextracted_spans':[],'no_claim_reason':None},{'claims':[]})


if __name__=='__main__':unittest.main()
