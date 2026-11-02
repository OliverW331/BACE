"""Record manually reviewed Introduction evidence; does not draft manuscript text.

Semantic judgments below were made by reading original source passages. The
fragment checks only preserve their identity; they do not automate verification.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

tex = (ROOT / 'paper/manuscript/main.tex').read_text()
body = tex.split('% BEGIN_INTRODUCTION\n')[1].split('% END_INTRODUCTION')[0]
paragraphs = dict(re.findall(r'% (I\d\d)\n(.*?)(?=\n% I\d\d|\Z)', body, re.S))
catalog = {r['key']: r for r in json.loads((ROOT / 'paper/literature/source_catalog.json').read_text())}
# Each row identifies the exact assertion preceding a citation, its original
# passage and short verbatim fragments. Multiple keys jointly support I04b.
reviews = [
('I01', 'esrs2023', "Corporate sustainability reporting is intended to help users understand companies' material impacts on people and the environment, and how sustainability matters affect their business. The 2023 European Sustainability Reporting Standards (ESRS) articulate this purpose and require information to be complete, neutral and accurate. They describe verifiability as the possibility of corroborating information or the inputs used to derive it", 'Annex I, ESRS 1 paragraph 2 (PDF p. 5); Appendix B, QC 5 (p. 30), QC 13–14 (p. 31)', ['material impacts on people and environment', 'complete, (ii) neutral and (iii) accurate', 'information is verifiable if it is possible to corroborate'], 'The original 2023 edition supports reporting purpose and qualitative characteristics, not current legal applicability, legal compliance of generated text, or equivalence between BACE support and ESRS verifiability.'),
('I02', 'chatreport2023', 'ChatReport retrieves passages from corporate reports to answer questions and analyse climate-related disclosures', 'Section 3.1, Report Summarization and Customized Question Answering, PDF p. 3 (printed p. 23)', ['report’s disclosure on that TCFD', 'retrieves the relevant part from the report', 'the retrieved relevant contexts'], 'Describes this system and application; does not establish widespread corporate adoption or drafting performance.'),
('I02', 'susgen2025', 'SusGen-GPT uses retrieval-augmented generation (RAG) for sustainability report generation, incorporating information retrieved from annual reports into drafting prompts', 'Section 3.1, PDF p. 3 (printed p. 1186); Figure 2, PDF p. 4', ['the system employs RAG', 'is then combined into pre-defined prompts'], 'Describes the SusGen system incorporating SusGen-GPT. Does not establish fidelity of every generated report or production adoption.'),
('I04', 'factscore2023', 'FActScore decomposes generated text into atomic facts and measures their support against a specified knowledge source', 'Section 3.1, Key ideas 1–2 and Definition, PDF p. 3 (printed p. 12078)', ['Atomic fact as a unit', 'a given source of knowledge'], 'The specified knowledge source is not necessarily the context supplied during generation. No claim of introducing atomic or source-relative assessment is made for BACE.'),
('I04', 'ragas2024', 'RAGAS and RAGChecker assess the support of response statements or claims in retrieved context', 'Section 3, Faithfulness, PDF p. 3 (printed p. 152)', ['To estimate faithfulness, we first use an LLM', 'to extract a set of statements', 'are supported by the information present'], 'Supports the RAGAS component of this joint assertion. Original metric definition, not a verification of the frozen package implementation or comparative accuracy.'),
('I04', 'ragchecker2024', 'RAGAS and RAGChecker assess the support of response statements or claims in retrieved context', 'Sections 3.2 and 3.3.3, PDF pp. 4–5', ['a text-to-claim extractor that decomposes a given text T', 'This metric is faithfulness, as it describes how faithful the generator is'], 'Supports the RAGChecker component of this joint assertion. Concerns native faithfulness, not all ground-truth-dependent metrics in the framework.'),
('I04', 'veriscore2024', 'VeriScore retains necessary spatial and temporal modifiers in verifiable claims', 'Section 2.1.2, definition of verifiable claims; Section 2.3, PDF p. 3 (printed p. 9449)', ['with all necessary modifiers (e.g., spatial,', 'temporal, or relative clauses)'], 'Acknowledges an established principle. Its web-retrieved verification evidence differs from the supplied-evidence universe here.'),
('I04', 'claimify2025', 'Claimify uses context to resolve ambiguity during claim extraction', 'Section 3.3, Disambiguation, PDF p. 4 (printed p. 6999)', ['a clear resolution based on the question and the con-', 'referential ambiguity'], 'Describes the ambiguity-resolution design; it does not guarantee resolution of every ambiguity or validate BACE extraction.'),
('I04', 'alce2023', 'ALCE evaluates whether concatenated cited passages support a statement', 'Section 3.3, Citation recall, PDF p. 4 (printed p. 6468)', ['concat(Ci ) concatenates all', 'passages in Ci together'], 'Joint support is prior work. ALCE explicitly does not require a minimal citation set; no BACE priority or superiority claim follows.'),
('I05', 'chatreport2023', 'ChatReport evaluates answer support and source attribution with human annotators and documents an erroneous concatenation of separate retrieved chunks', 'Section 5, Content and Source annotation, PDF p. 5; Section 5.2, erroneous concatenation, PDF p. 6 (printed pp. 25–26)', ['We conduct a human evaluation', 'covered information is supported by the report', 'example where the answer falsely concatenates two'], 'Domain-specific support evaluation and erroneous synthesis are precedents. This example is not an error-rate estimate for the present experiment.'),
('I05', 'esgbench2026', 'ESG-Bench provides human annotations of support and hallucination in ESG question answering', 'Human Annotation, Annotation Procedure and Benchmark Analysis and Usage, PDF p. 4 (printed p. 39325)', ['independently reviewed by two annotators', 'information that is fabricated or not supported by the source'], 'Question answering and its annotation criteria differ from the present disclosure-drafting workflow. Does not establish absence of other domain benchmarks.'),
]
records=[]
for i,(pid,key,claim,locator,fragments,limits) in enumerate(reviews,1):
    assert claim in paragraphs[pid], (pid,key,'Claim not in manuscript')
    folder=ROOT/'paper/literature/sources'/key
    fulltext=folder/'fulltext.txt'
    normalized=re.sub(r'\s+',' ',fulltext.read_text())
    assert all(f in normalized for f in fragments),(key,[f for f in fragments if f not in normalized])
    retrieval=json.loads((folder/'retrieval.json').read_text())
    old=catalog.get(key,{})
    if old:
        assert sha(fulltext)==old['fulltext_sha256'] and sha(folder/'original.pdf')==old['pdf_sha256']
    records.append({'id':f'{pid}-{key}-{i:02}', 'document':'paper/manuscript/main.tex','location':pid,'citation_key':key,'claim':claim,'canonical_identifier':old.get('canonical_identifier','http://data.europa.eu/eli/reg_del/2023/2772/oj'),'source_version':old.get('source_version',retrieval.get('version')),'source_url':old.get('source_url',retrieval.get('final_url')),'fulltext_path':str(fulltext.relative_to(ROOT)),'original_pdf':str((folder/'original.pdf').relative_to(ROOT)),'retrieval_record':str((folder/'retrieval.json').relative_to(ROOT)),'locator':locator,'verified_excerpt_fragments':fragments,'original_retrieval_at_utc':retrieval['retrieved_at_utc'],'local_fulltext_review_date':'2026-10-02','review_timezone':'Europe/Zurich','verdict':'DIRECT','status':'VERIFIED_FULL_TEXT_FOR_STATED_CLAIM','limits':limits,'source_hashes':{p.name:sha(p) for p in [fulltext,folder/'original.pdf',folder/'retrieval.json']},'metadata_note':old.get('metadata_status','Issuing body, title, adoption date and publication date verified against original Official Journal PDF p. 1; citation is to the original edition, without a claim about subsequent amendments.'),'access_note':'Original passage reviewed locally on the stated date. Existing scholarly source metadata review is dated 29 September 2026; no fresh publisher notice search is implied.'})
assert [k for group in re.findall(r'\\cite\{([^}]+)\}',body) for k in group.split(',')]==[r['citation_key'] for r in records]
save('citation_occurrences.json',records)
facts=json.loads((ROOT/'paper/analysis/methods_draft/verified_method_facts.json').read_text())['cohort']
fields={'1,798':'completed','1,800':'planned','30':'companies','2019--2023':'years','12':'tasks'}
ledger=[{'location':'I06','printed_value':p,'value':facts[f],'status':'COMPUTED_VERIFIED','result_file':'paper/analysis/methods_draft/verified_method_facts.json','result_locator':'cohort.'+f,'source_calculation':'paper/analysis/methods_draft/verify_methods.py; paper/analysis/results_draft/verify_draft.py','upstream_provenance':'paper/analysis/methods_draft/provenance.json','cohort':'One fixed workflow; complete BACE assessments with both native comparator scores. Two planned cases remain incomplete.','unit':{'completed':'disclosures','planned':'company-year-task design cells','companies':'unique companies','years':'reporting years','tasks':'distinct reporting tasks'}[f],'aggregation':'Counts or set of distinct design values; no rounding or imputation. Planned = 30 × 5 × 12; completed = paired = 1,798.','denominator':'Design scope, not a rate; planned and completed counts distinguished.'} for p,f in fields.items()]
ledger.append({'location':'I01 and I06','printed_value':'2023 ESRS edition','status':'SOURCE_REPORTED','source':'paper/literature/sources/esrs2023/original.pdf, p. 1; BACE/config/tasks.json','meaning':'Edition identifier, not current legal applicability or a measured quantity.'})
save('numeric_ledger.json',ledger)
save('argument_map.json',{
'framing':'Disclosure evidence credibility and factual boundaries; BACE supplies the operational method and empirical comparison.',
'paragraphs':{'I01':{'function':'Reporting purpose and evidentiary motivation','evidence':'Original 2023 ESRS; final two sentences are the study rationale.'},'I02':{'function':'AI-assisted analysis and drafting as the study setting','evidence':'ChatReport and SusGen; last two sentences state the study motivation, not adoption prevalence.'},'I03':{'function':'Define factual boundaries through conceptual examples','evidence':'docs/generation_evaluation.md, Sections 3, 5 and 7; examples are logical illustrations, not sampled findings.'},'I04':{'function':'Acknowledge prior atomic support, context preservation and joint evidence','evidence':'Occurrence-level original-source ledger; no exclusive-priority claim.'},'I05':{'function':'Domain precedents and a narrower measurement question','evidence':'ChatReport and ESG-Bench; question and inspectability rationale are author synthesis.'},'I06':{'function':'Aim, operational method, empirical scope and contribution limits','evidence':'Results R01–R14; Methods M01–M25; numeric ledger; method definition; completed validation is not asserted.'}},
'research_question_mapping':{'RQ1':'I06 support patterns → Results R01–R05','RQ2':'I06 automated diagnoses and inspected cases → Results R06–R08','RQ3':'I06 native evaluator comparison → Results R09–R14','RQ4':'Not claimed as completed; independent human validation remains outstanding.'},
'qualifications':['Retrospective organizing questions, not preregistered hypotheses.','Source-relative support is not external truth, legal compliance or downstream sustainability performance.','Native score differences are not an accuracy ranking.','Targeted literature comparison does not establish exclusive novelty.','Two inaccessible close comparisons remain documented in the dated gap review; not used as positive evidence.'],
'background_L1_resolution':'The Introduction wording is supported directly by the original 2023 ESRS. Christensen et al. remains an unused lead and was not verified in this step. Earlier foundation/gap documents retain their dated pending status; this record supersedes that status for the actual Introduction wording.'})
save('draft_record.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'local_date':'2026-10-02','manuscript':'paper/manuscript/main.tex','introduction_sha256':hashlib.sha256(body.encode()).hexdigest(),'paragraph_sha256':{pid:hashlib.sha256(p.encode()).hexdigest() for pid,p in paragraphs.items()},'citation_occurrences':len(records),'unique_references':len(set(r['citation_key'] for r in records)),'scope':'Introduction drafting and local integration only; no completed human-validation claim.'})
print(json.dumps({'status':'PASS','paragraphs':len(paragraphs),'introduction_citation_occurrences':len(records),'unique_references':len(set(r['citation_key'] for r in records))}))
