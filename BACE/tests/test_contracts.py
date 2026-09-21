"""Failure-oriented checks for sample, boundary, native scores, and resume safety."""
from collections import Counter
from pathlib import Path
import json
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'script'),str(ROOT/'script/rag'),str(ROOT/'script/evaluation'),str(ROOT/'script/generation')]
from select_sample import allocate
from pipeline import immutable_json, repair_interrupted_tail
from common import read
import run_w2_retrieval_sanity_check as retrieval
import build_w2_generation_inputs as generation
from external_evaluation import adapt_case, digest
from metrics import bace_metrics, external_metrics
from run_extraction_repair import bind_output
import run_w2_generation as generator


class Contracts(unittest.TestCase):
    def test_noncontiguous_table_quote_keeps_verbatim_source_lines(self):
        from summarize import review_quote_locations, human
        text = '| Indicator | Year |\n|---|---|\n| Incidents | 1 |\n| Fines | 0 |'
        claim = {'dc_id':'table','dc_provenance':[{'source_quotes':['| Indicator | Year |\n|---|---|\n| Fines | 0 |']}]}
        original = json.dumps(claim)
        quotes,refs,status = review_quote_locations(claim,text,human.paragraphs(text))
        self.assertEqual(status['mode'],'verbatim_line_segments')
        self.assertEqual(refs,['Paragraph 01'])
        self.assertIn('| Fines | 0 |',quotes)
        self.assertTrue(all(q in text for q in quotes))
        self.assertEqual(json.dumps(claim),original)

    def test_unlocatable_claim_retains_full_disclosure_for_human_review(self):
        from summarize import review_quote_locations, human
        text = 'First original paragraph.\n\nSecond original paragraph.'
        claim = {'dc_id':'unlocated','dc_provenance':[{'source_quotes':['Invented quotation.','First original paragraph.']}]}
        quotes,refs,status = review_quote_locations(claim,text,human.paragraphs(text))
        self.assertEqual(quotes,['First original paragraph.'])
        self.assertEqual(refs,['Paragraph 01','Paragraph 02'])
        self.assertEqual(status['mode'],'full_disclosure')
        self.assertEqual(status['unresolved_quote_count'],1)
        claim['dc_provenance'] = []
        quotes,refs,status = review_quote_locations(claim,text,human.paragraphs(text))
        self.assertEqual(quotes,[])
        self.assertEqual(len(refs),2)

    def test_postprocessing_revision_cannot_authorize_scientific_changes(self):
        import acceptance
        from common import write
        original = {'schema_version':'bace_freeze_v1','files':{'script/summarize.py':'old','config/tasks.json':'unchanged'},'environment':{'model':'fixed'}}
        before = hashlib.sha256((json.dumps(original,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()).hexdigest()
        revised = json.loads(json.dumps(original))
        revised['files']['script/summarize.py'] = 'new'
        revised['postprocessing_revision'] = {'previous_freeze_sha256':before,'changed_files':{'script/summarize.py':{'before':'old','after':'new'}}}
        self.assertEqual(acceptance.validate_postprocessing_revision(revised),before)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);write(root/'config/freeze.json',revised)
            with patch.object(acceptance,'ROOT',root):
                acceptance.validate_run_freeze(before)
                with self.assertRaises(ValueError):
                    acceptance.validate_run_freeze('unrelated')
        revised['files']['config/tasks.json'] = 'changed'
        with self.assertRaises(ValueError):
            acceptance.validate_postprocessing_revision(revised)
        revised['postprocessing_revision']['changed_files']['config/tasks.json'] = {'before':'unchanged','after':'changed'}
        with self.assertRaises(ValueError):
            acceptance.validate_postprocessing_revision(revised)

    def test_allocation_capacity_and_total(self):
        q=allocate({'a':1,'b':2,'c':47},30)
        self.assertEqual(sum(q.values()),30)
        self.assertEqual(q['a'],1)
        self.assertLessEqual(q['b'],2)
        self.assertEqual(q,allocate({'c':47,'b':2,'a':1},30))

    def test_cannot_hide_sector(self):
        with self.assertRaises(ValueError):
            allocate({'a':2,'b':2,'c':2},2)

    def test_frozen_sample_has_all_sectors(self):
        m=read(ROOT/'evidence/sample/sample.json')
        self.assertFalse(m['selection_uses_experiment_scores'])
        self.assertEqual(len({r['company_id'] for r in m['selected']}),30)
        self.assertEqual(Counter(r['primary_sics_sector'] for r in m['selected']),m['quotas'])

    def test_all_twelve_explicit_query_bundles(self):
        tasks=retrieval.load_task_specs(ROOT/'config/tasks.json')
        templates=retrieval.load_query_templates(ROOT/'config/queries.json')
        self.assertEqual(Counter(t.split('-')[0].lower() for t in tasks),{'e1':4,'s1':4,'g1':4})
        case={'company_name':'Test Company','company_id':'test','target_reporting_year':2023,'case_id':'test'}
        for tid,t in tasks.items():
            self.assertIn(tid,templates)
            bundle=retrieval.render_query_bundle({**case,'task_id':tid},t,templates)
            self.assertGreaterEqual(len(bundle['subqueries']),2)
            self.assertTrue(all('{' not in s['query_text'] for s in bundle['subqueries']))

    def test_no_cross_company_or_future_evidence(self):
        manifest={'evidence_card_ids':{'pdf_narrative':['one']},'included_source_years':{'pdf':[2019,2020,2021,2022],'csv':[2019,2020,2021,2022,2023]}}
        case={'case_id':'x','company_id':'a','manifest':manifest}
        card={'evidence_id':'one','company_id':'b','source_type':'pdf','evidence_type':'narrative','source_year':2022}
        with self.assertRaises(RuntimeError):
            retrieval.validate_candidate_pool(case,{'one':card},False)
        card.update(company_id='a',source_year=2023)
        with self.assertRaises(RuntimeError):
            retrieval.validate_candidate_pool(case,{'one':card},False)

    def test_no_evidence_type_deficit_redistribution(self):
        cards={str(i):{'evidence_type':'narrative'} for i in range(35)}
        ranked=[{'evidence_id':str(i)} for i in range(35)]
        selected=retrieval.select_final_evidence(ranked,cards,{'selection_mode':'stratified_by_evidence_type','per_evidence_type_top_n':10})
        self.assertEqual(len(selected),10)

    def test_bm25_cache_invalidates_on_source_text_and_order(self):
        cards=[{'evidence_id':'a','retrieval_text':'emissions climate'},
               {'evidence_id':'b','retrieval_text':'workforce safety safety'}]
        retrieval._BM25_POOL_CACHE=(None,None)
        first=retrieval.rank_bm25('climate',cards,2)
        self.assertEqual(first,retrieval.rank_bm25('climate',cards,2))
        self.assertEqual(first[0]['evidence_id'],'a')
        cards[0]['retrieval_text']='workforce safety'
        cards[1]['retrieval_text']='climate emissions'
        self.assertEqual(retrieval.rank_bm25('climate',cards,2)[0]['evidence_id'],'b')
        self.assertEqual(retrieval.rank_bm25('climate',list(reversed(cards)),2),retrieval.rank_bm25('climate',cards,2))

    def test_dense_cache_handles_new_query_pool_and_normalization(self):
        import numpy as np
        from types import SimpleNamespace
        artifacts=SimpleNamespace(embedding_matrix=np.array([[2,0],[0,1]],dtype=np.float32),evidence_id_to_index={'a':0,'b':1})
        cards=[{'evidence_id':'a'},{'evidence_id':'b'},{'evidence_id':'missing'}]
        with patch.object(retrieval,'embed_query',side_effect=lambda text,config:np.array([1,0] if text=='a' else [0,1],dtype=np.float32)):
            retrieval._DENSE_POOL_CACHE=(None,None)
            first,missing=retrieval.rank_dense('a',cards,artifacts,{},2)
            self.assertEqual((first[0]['evidence_id'],first[0]['score'],missing),('a',2.0,1))
            self.assertEqual(retrieval.rank_dense('b',cards,artifacts,{},2)[0][0]['evidence_id'],'b')
            self.assertEqual(retrieval.rank_dense('a',cards,artifacts,{'normalize_corpus_embeddings':True},2)[0][0]['score'],1.0)
            self.assertEqual(retrieval.rank_dense('a',cards[1:],artifacts,{},2)[0][0]['evidence_id'],'b')

    def test_changed_resume_input_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.json'
            immutable_json(p,{'a':1});immutable_json(p,{'a':1})
            with self.assertRaises(ValueError):
                immutable_json(p,{'a':2})
            self.assertEqual(read(p),{'a':1})

    def test_one_checkpoint_preserves_multiple_stages_and_reuses_outputs(self):
        import pipeline
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d);(root/'script').mkdir();(root/'config').mkdir()
            (root/'config/experiment.json').write_text(json.dumps({'runtime':{'max_stage_attempts':1}}))
            (root/'script/fixture.py').write_text('import argparse,json\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument("--output-dir");a=p.parse_args()\no=Path(a.output_dir);o.mkdir(parents=True,exist_ok=True)\n(o/"result.txt").write_text("retained result")\n(o/"manifest.json").write_text(json.dumps({"status":"complete"}))\n')
            base=root/'case'
            with patch.object(pipeline,'ROOT',root):
                for label in ['first','second']:
                    pipeline.stage(base,label,'fixture.py',[],base/label,'manifest.json')
                state=(base/'state.json').read_bytes()
                self.assertEqual(set(read(base/'state.json')['stages']),{'first','second'})
                with patch.object(pipeline.subprocess,'Popen',side_effect=AssertionError('Completed stages must not execute again')):
                    pipeline.stage(base,'first','fixture.py',[],base/'first','manifest.json')
                self.assertEqual((base/'state.json').read_bytes(),state)
                (base/'first/result.txt').write_text('modified')
                with self.assertRaises(ValueError):
                    pipeline.stage(base,'first','fixture.py',[],base/'first','manifest.json')

    def test_interrupted_tail_preserves_completed_calls(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'calls.jsonl'
            p.write_bytes(b'{"a": 1}\n{"a":')
            repair_interrupted_tail(p)
            self.assertEqual(p.read_bytes(),b'{"a": 1}\n')
            self.assertEqual(next(Path(d).glob('*.interrupted_tail.*')).read_bytes(),b'{"a":')

    def test_external_score_must_match_native_claims(self):
        adapted={k:'x' for k in ['generation_case_id','prompt_hash','response_hash','context_hash','evidence_ids','prompt_labels']}
        record={**adapted,'status':'success','metric':'faithfulness','claims':[{'supported':True},{'supported':False}],'claim_count':2,'score':1.0}
        with self.assertRaises(ValueError):
            external_metrics(record,'ragas',adapted)
        record['score']=0.5
        self.assertEqual(external_metrics(record,'ragas',adapted)['ragas_faithfulness'],0.5)

    def test_bace_rejects_cross_case_support(self):
        ec=[{'ec_id':'e','generation_case_id':'a'}]
        dc=[{'dc_id':'d','generation_case_id':'b'}]
        support=[{'dc_claim_id':'d','support_sets':[{'support_type':'direct','ec_claim_ids':['e']}]}]
        with self.assertRaises(ValueError):
            bace_metrics(ec,dc,support,[])

    def test_direct_extraction_rejects_incomplete_provider_response(self):
        record={'task':'dc','call_status':'success','parsed_output':{'claims':[],'no_claim_reason':'No claim.'},'api_response':{'status':'incomplete'}}
        result=bind_output(record,{'task':'dc'},{'type':'object'})
        self.assertEqual(result['call_status'],'invalid_output')

    def test_four_known_mapping_rules(self):
        from prepare_evidence import CORRECTIONS
        self.assertEqual(len(CORRECTIONS),4)

    def test_unmapped_pdf_fonts_cannot_enter_model_inputs(self):
        import tiktoken
        from evidence_quality import unusable_reason
        encoder=tiktoken.get_encoding('cl100k_base')
        bad='Corporate governance '+('\ue001\ue002\ue003 ' * 80)
        self.assertEqual(unusable_reason(bad,encoder)[0],'unmapped_font_glyphs')
        self.assertIsNone(unusable_reason('Reported emissions fell 5% (Scope 1). \uf0b7',encoder)[0])
        self.assertEqual(unusable_reason(' token'*9000,encoder)[0],'over_embedding_token_limit')

    def test_every_active_prompt_and_schema_matches_its_hash(self):
        def visit(value,parent):
            if isinstance(value,dict):
                if 'file' in value and 'sha256' in value:
                    source=(parent/value['file']).resolve()
                    self.assertTrue(source.is_relative_to(ROOT))
                    self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),value['sha256'])
                for child in value.values():
                    visit(child,parent)
            elif isinstance(value,list):
                for child in value:
                    visit(child,parent)
        for path in (ROOT/'config/evaluation/configs').glob('*.json'):
            visit(read(path),path.parent)

    def test_failed_generation_resumes_without_counting_old_attempt_as_failure(self):
        prompt='A frozen test prompt.'
        case={'generation_case_id':'fixture','workflow':'W2','company_id':'fixture','company_name':'Fixture',
              'target_reporting_year':2023,'task_id':'E1-1_transition_plan','task_title':'Climate transition',
              'generation_prompt':prompt,'prompt_metadata':{'prompt_hash':digest(prompt),'evidence_count':0},'retrieval_setting':{},'prompt_evidence':[]}
        manifest={'schema_version':'test','script_version':'test','generation_case_count':1,'instruction_template':prompt,
                  'evidence_id_in_prompt':False,'prompt_label_maps_to_evidence_id':True,'citation_required':False}
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            base=Path(d);(base/'cases.jsonl').write_text(json.dumps(case)+'\n');(base/'manifest.json').write_text(json.dumps(manifest))
            argv=['--generation-cases',str(base/'cases.jsonl'),'--generation-input-manifest',str(base/'manifest.json'),
                  '--output-dir',str(base/'output'),'--run-id','fixture','--model','fixture','--azure-deployment','fixture','--omit-temperature']
            with patch.object(generator,'generate_disclosure',return_value={'generated_text':'Too short.','response_status':'completed','usage':{}}):
                generator.main(argv)
            self.assertEqual(read(base/'output/generation_run_manifest.json')['case_count_failed'],1)
            with patch.object(generator,'generate_disclosure',return_value={'generated_text':' '.join(['evidence']*350),'response_status':'completed','usage':{}}):
                generator.main(argv+['--resume'])
            result=read(base/'output/generation_run_manifest.json')
            self.assertEqual(result['case_count_success'],1)
            self.assertEqual(result['case_count_failed'],0)
            self.assertEqual(result['failed_attempt_count_total'],1)
            self.assertTrue((base/'output/rejected_attempts.jsonl').exists())


if __name__=='__main__':
    unittest.main()
