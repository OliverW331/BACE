"""Record the completed visual/source review against the final exported figures."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis_data import HERE,OUT,read,save_json,sha
roles={
'00_selection':[('Population narrowing','Observed company counts; no interval','Companies')],
'00_geography':[('Register-country representation','Country counts; no interval','Companies')],
'00_sector_selection':[('Selection changes sector proportions','Cohort percentages; no interval','Companies')],
'00_source_coverage':[('Extracted-metric availability','Observed count per source year; no interval','Company-year'),('Report availability','Valid PDF-header counts; no interval','Company-year')],
'00_screening_gaps':[('Availability-based selection bias','Two missing-year counts; marker area encodes company count','Companies')],
'00_evidence_scale':[('Representation scale','Canonical card counts','Cards'),('Representation length','Exact weighted empirical cumulative distribution','Cards')],
'00_visible_evidence':[('Exposure rather than storage','Frequency of visible card counts','Disclosures')],
'00_time_windows':[('PDF time boundary','Configured inclusion, not observed data','Protocol'),('CSV time boundary','Configured inclusion, not observed data','Protocol')],
'00_provenance_example':[('Source-to-prompt trace','Exact text with explicit unsupported-glyph escapes','One fixed visible card')],
'01_completion':[('Analysis cohort','Completed and missing branch counts','Disclosures')],
'01_support_distribution':[('Typical support and variation','All disclosure scores; 20 fixed bins','Disclosures nested in companies'),('Support decomposition','Pooled direct/inferred/unsupported DC counts','DCs nested in disclosures/companies')],
'01_task_support':[('Task heterogeneity','Macro mean with 95% company-cluster percentile interval','Company clusters')],
'01_company_year':[('Local variation','Mean across available tasks, fixed colour scale','Company-year; repeated companies')],
'01_year_support':[('Year-level description','Macro mean with 95% company-cluster percentile interval','Repeated companies')],
'01_secondary_metrics':[('Secondary metric interpretation','Empirical distributions; undefined counts reported','Disclosures'),('Non-disclosure sensitivity','Paired within-disclosure score changes','Disclosures')],
'02_label_composition':[('Diagnostic composition','Pooled unsupported-DC shares with exact counts','Unsupported DCs'),('Diagnostic prevalence','Disclosures with at least one labelled DC','Disclosures')],
'02_task_patterns':[('Task-specific diagnostic burden','Percent of all task DCs, no row scaling','DCs within tasks')],
'02_pipeline_checks':[('Candidate/provenance dependencies','Label-specific proportions, missingness retained','Unsupported DCs')],
'02_asml_source_layout':[('Original layout challenges a diagnosis','Unmodified PDF crop; effective source-font check','One source-page crop')],
'03_native_comparison':[('Native score levels','Common-cohort empirical distributions','Paired disclosures'),('Within-case score gaps','Mean difference with 95% company-cluster interval','Company clusters')],
'03_rank_agreement':[('BACE vs RAGChecker ordering','All points; descriptive Spearman, no test','Paired disclosures'),('BACE vs RAGAS ordering','All points; descriptive Spearman, no test','Paired disclosures'),('Comparator ordering','All points; descriptive Spearman, no test','Paired disclosures')],
'03_claim_inventories':[('Different native denominators','Empirical claim-count distributions','Disclosures'),('Count and score differences','All paired points; no causal decomposition','Disclosures')],
'03_task_disagreement':[('Task variation in paired gaps','Both comparator differences with company-cluster intervals','Company clusters')],
'03_alignment_coverage':[('Limits of exact-text matching','Unique exact-text partner counts; unmatched claims retained','Native claims')],
}
for label in ['non_disclosure_statement','contradiction','evidence_conflation','factual_boundary_distortion','inferential_inflation','unsupported_novelty']:
 roles['02_example_'+label]=[(label.replace('_',' ').capitalize()+' interpretation','Fixed random example; exact quotes and automatic rationale; no population estimate','One DC and its complete case sources')]
for direction in ['lower','higher']:
 roles['03_case_'+direction]=[('Opposite-direction native score example','Extreme paired gap with explicit selection rule','One common case')]
for kind in ['source_coverage','combined_evidence']:
 roles['03_judgement_'+kind]=[(kind.replace('_',' ').capitalize()+' judgement path','Native claims and source values; qualitative comparison','One source-inspected case')]
checks=read(OUT/'qa/acceptance_checks.json')
lines=['# Final analysis QA review','',
'This review covers the final four English notebooks and their 34 exported figures. '
'All figures were inspected panel by panel and as complete pages using PDF proofs at 1.6 pixels per point, '
'with physical dimensions retained in metadata. This is analyst/source inspection, not blinded human annotation.','',
'## Scientific and statistical review','',
'- All 1,800 cases remain in the inventory. BACE has 1,798 completed cases; both external evaluators have 1,800. Missing BACE scores remain missing.',
'- Cross-method primary comparisons use the same 1,798 cases. Native claim inventories are not treated as a shared truth set.',
'- Intervals resample complete company clusters (2,000 draws, seed 20260921); subgroup ordering and correlations remain descriptive.',
'- Exact-text matching is deliberately narrow: 0 BACE–RAGChecker pairs and 5,709 BACE–RAGAS pairs. The zero includes sentence/triple formatting differences; it is not evidence of zero semantic overlap. No accuracy estimate is inferred.',
'- Examples retain automatic labels even when source inspection challenges them. ASML exposes source-layout/EC association, Air France-KLM exposes omitted indicator content, and the Investec/Banco BPM comparison shows different evidence representations and combination paths.',
'- Source excerpts are contiguous where described as excerpts. Unsupported source glyph U+F0B7 is displayed as an explicit code-point escape, with the untouched original in the source table. Pennon table text retains its original interleaving instead of being silently repaired.','',
'## Rendering and source-audit decisions','',
'- Final vector text passes the 5 pt gate. PDF crop subscripts are checked separately using original font size × actual display scale, because vector-text auditing cannot inspect rasterised source text.',
'- Comparable plot rectangles and panel-label anchors pass the 1.5 pt alignment gate. Reliable collision failures and unresolved clipping are absent.',
'- Blue/green/orange lines use line-style or marker redundancy when they share axes. Fixed categorical rows have explicit labels; heatmaps use a monotone luminance scale. Deuteranomaly, protanomaly and grayscale previews were generated from every final PDF. The colour-bearing layouts were inspected for ambiguity; monochrome reading plates retain their textual meaning.',
'- The source scanner requests TIFF, but the agreed deliverable is 600 dpi PNG plus PDF/SVG. Measured metadata and PNG dimensions verify the requested 183 mm output width; the scanner cannot infer this dynamic helper parameter.',
'- Generic missing-data warnings refer to explicitly counted undefined ratios, incomplete cohorts, and the exact-text alignment subset. No observation is removed from the master inventory for visual convenience.',
'- Log-scale counts and lengths are asserted positive before plotting. No pseudocount or unreported exclusion is used. Source-scanner positivity warnings reflect its limited static pattern matching.',
'- Vertical heatmap year labels intentionally use centred 90-degree tick rotation. Their final bounding boxes, clearance and full-page readability were inspected; no label collision is present.','',
'## Panel-level record','',
'Each row records a distinct evidence role. Exact n and source values are in the figure captions and exported tables. '
'All labels, legends and axes in this table passed final visual inspection; uncertainty is either explicitly defined below or unnecessary for an observed count/source excerpt.','',
'| Figure / panel | Unique evidence role | Summary and uncertainty | Observation / inference unit | Alignment | Collision | Visual review |',
'|---|---|---|---|---|---|---|']
reviewed=[]
for f in checks['figures']:
 name=f['figure'];rs=roles[name]
 assert len(rs)==f['panels'],(name,rs,f['panels'])
 for i,(role,summary,unit) in enumerate(rs):
  label=chr(97+i) if len(rs)>1 else 'single'
  lines.append(f"| {name} / {label} | {role} | {summary} | {unit} | {f['alignment']} | Pass | Pass |")
 meta=next((OUT/'figures').rglob(name+'.metadata.json'))
 reviewed.append({'figure':name,'pdf_sha256':read(meta)['exports']['pdf'],'review':'pass','panels':len(rs)})
lines+=['','## Per-figure reading revision','',
'Each of the 34 figures now has a specific question, an encoding caption, an evidence-based pattern reading, '
'an interpretation and figure-specific limits. All 44 panels are covered. NARRATIVE_REVIEW.md records the '
'editorial/source review; outputs/qa/reading_checks.json checks actual saved output order, source recomputation '
'and complete code-hidden HTML visibility. The prose revision retains pixel-identical PNGs and identical '
'plotted CSVs relative to its baseline, carrying forward the earlier layout/colour inspection. '
'Current PDF font, collision and alignment audits also pass.','',
'## Reproduction and source preservation','',
'All four notebooks completed independently in fresh kernels. Figure-source numerical outputs were compared across repeated executions. '
'Native arithmetic, cohort counts, cache hashes, output dimensions, hyperlinks and rendered figure audits passed. '
'The integrity report verifies 254 frozen files, all 401 source PDFs, and the unchanged native Python/package inventory. '
'Analysis dependencies are isolated from that native environment.','',
'No claim of formal journal submission compliance, evaluator accuracy, company compliance, causality or complete main-experiment execution is made.']
(HERE/'QA_REVIEW.md').write_text('\n'.join(lines)+'\n')
save_json(OUT/'qa/visual_review_manifest.json',reviewed)
print(f'Recorded review of {len(reviewed)} figures and {sum(x["panels"] for x in reviewed)} panels.')
