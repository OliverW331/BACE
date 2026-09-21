from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'script/evaluation'))
from run_claim_patch_refinement import draft_manifest_identity


class DraftManifestIdentityTests(unittest.TestCase):
    def test_parent_resume_counters_do_not_change_extraction_identity(self):
        before={'run_fingerprint':'same','source_hashes':{'input':'hash'},'updated_at_utc':'old','invocation':{'resume_skips':0}}
        after={**before,'updated_at_utc':'new','invocation':{'resume_skips':20}}
        self.assertEqual(draft_manifest_identity(before),draft_manifest_identity(after))

    def test_changed_source_model_prompt_or_case_selection_changes_identity(self):
        original={'source_hashes':{'input':'hash'},'model':{'deployment':'a'},'prompts':{'ec':'v8'},'filters':{'cases':['a']}}
        for key in original:
            revised=deepcopy(original);revised[key]={'different':True}
            with self.subTest(field=key):self.assertNotEqual(draft_manifest_identity(original),draft_manifest_identity(revised))


if __name__=='__main__':unittest.main()
