"""Reorder both Excel builders into disclosure, evidence, then results.

This one-time presentation migration leaves all scientific input files unchanged.
"""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BUILDERS = [
    ROOT / "paper/analysis/residual_gap_review_2026-10-20/excel_reader/build_reader.py",
    ROOT / "paper/analysis/prompt_gap_review_2026-10-22/excel_reader/build_reader.py",
]

CLAIMS = '''    row = note(ws, row, "The passages above locate the target. Native claims and the full disclosure follow before the evidence and results.")
    for a, b, title in [(0, 1, "Claim source"), (2, 7, "Disclosure claim — exact saved text")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 30)
    row += 1
    for name, claim in [("BACE", p["target_dc"]["dc_text"]), ("RAGAS native", p["native"]["ragas"]["claim"]), ("RAGChecker native", rc_triple(p["native"]["ragchecker"]["claim"]))]:
        put(ws, row, 0, 1, name, "label")
        put(ws, row, 2, 7, claim, source="disclosure_native_claim")
        height(ws, row, [(0, 1, name), (2, 7, claim)])
        row += 1
    if rid in ALIGNMENT_NOTES:
        row = note(ws, row, "Wording note: " + ALIGNMENT_NOTES[rid], warning=True)
'''

RESULT_DETAILS = '''    row = section(ws, row, "Results  |  Candidate EC use in saved support sets")
    row = note(ws, row, "Click an EC alias to revisit its exact candidate text. Membership below is copied from the saved support sets.")
    for a, b, title in [(0, 0, "Candidate EC"), (1, 7, "Saved support-set membership")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 30)
    row += 1
    if not p["candidate_ecs"]:
        row = note(ws, row, "No candidate ECs: the saved candidate list is empty.")
    for ec in p["candidate_ecs"]:
        alias = p["aliases"][ec["ec_id"]]
        membership = ec_usage[ec["ec_id"]]
        link(ws, row, 0, 0, alias, rid, ec_row_map[ec["ec_id"]])
        put(ws, row, 1, 7, membership, source="saved_ec_membership_display")
        height(ws, row, [(1, 7, membership)])
        row += 1
    row = section(ws, row, "Results  |  RAGChecker per-evidence labels")
    row = note(ws, row, "These are the saved native RAGChecker labels for its claim shown above. Click a card to revisit the full evidence.")
    for a, b, title in [(0, 1, "Evidence card"), (2, 3, "Saved label"), (4, 7, "Source locator")]:
        put(ws, row, a, b, title, "head")
    ws.set_row(row, 30)
    row += 1
    for card in p["evidence_cards"]:
        eid = card["evidence_id"]
        label = p["native"]["ragchecker"]["evidence_verdicts"][eid]
        link(ws, row, 0, 1, card["prompt_label"], rid, card_rows[eid])
        put(ws, row, 2, 3, label, label, source="ragchecker_evidence_verdict")
        put(ws, row, 4, 7, location(card))
        height(ws, row, [(4, 7, location(card))])
        row += 1
'''

records = []
for path in BUILDERS:
    original = path.read_text()
    assert "ec_usage = {}" not in original, "Migration already applied"
    a = original.index('    row = section(ws, 4, "1  |  Disclosure')
    b = original.index('    row = section(ws, row, "2  |', a)
    c = original.index('  |  Evidence excerpts', b)
    c = original.rfind('    row = section(ws, row, ', b, c)
    d = original.index('    candidate_section = row\n', c)
    e = original.index('    evidence_section = row\n', d)
    f = original.index('    disclosure_section = row\n', e)
    g = original.index('    row = note(ws, row, "Source IDs and hashes', f)
    disclosure, judgments, excerpts, candidates, evidence, full_disclosure = (
        original[a:b], original[b:c], original[c:d], original[d:e], original[e:f], original[f:g]
    )
    adapted = "prompt_gap_review" in str(path)
    disclosure = disclosure.replace('1  |  Disclosure — exact target passage', '1  |  Disclosure related — passages and claims')
    old_note = '    row = note(ws, row, "These passages locate the target claim in the generated disclosure. The full disclosure is included at the end of this sheet.")\n'
    assert old_note in disclosure
    disclosure = disclosure.replace(old_note, CLAIMS)
    full_disclosure = full_disclosure.replace('7  |  Full generated disclosure' if adapted else '6  |  Full generated disclosure', '1.1  |  Full generated disclosure')
    excerpts = '    excerpt_section = row\n' + excerpts.replace('4  |  Evidence excerpts' if adapted else '3  |  Evidence excerpts', '2  |  Evidence related — selected excerpts')
    candidates = candidates.replace('5  |  Candidate ECs' if adapted else '4  |  Candidate ECs', '2.1  |  Candidate ECs')
    if adapted:
        candidates = candidates.replace("EC aliases match the previous reader. 'Original', 'RA-style' and 'RC-style' identify each condition's actual support sets. S1 = Set 1; set types are shown above.", "EC aliases match the previous reader. This is the complete candidate input. Saved support-set membership is listed later in Results.")
    else:
        candidates = candidates.replace("EC01, EC02, ... are local reading labels. 'Used in' preserves membership of the saved BACE support sets. Candidate status alone does not mean support.", "EC01, EC02, ... are local reading labels. This is the complete candidate input. Saved support-set membership is listed later in Results.")
    candidates = candidates.replace('(6, 6, "Source card(s)"), (7, 7, "Used in")', '(6, 7, "Source card(s)")')
    candidates = candidates.replace('    ec_row_map = {}\n', '    ec_row_map = {}\n    ec_usage = {}\n')
    candidates = candidates.replace('        put(ws, row, 6, 6, "\\n".join(labels), "link")\n', '        put(ws, row, 6, 7, "\\n".join(labels), "link")\n')
    candidates = candidates.replace('        put(ws, row, 7, 7, "\\n".join(membership) or "Not in a support set", "alt")\n', '        ec_usage[ec["ec_id"]] = "\\n".join(membership) or "Not in a support set"\n')
    candidates = candidates.replace('        height(ws, row, [(1, 5, ec["ec_text"]), (6, 6, "\\n".join(labels)), (7, 7, "\\n".join(membership) or "Not in a support set")])', '        height(ws, row, [(1, 5, ec["ec_text"]), (6, 7, "\\n".join(labels))])')
    evidence = evidence.replace('6  |  Full supplied evidence' if adapted else '5  |  Full supplied evidence', '2.2  |  Full supplied evidence')
    evidence = evidence.replace('(1, 6, "Full evidence text"), (7, 7, "RAGChecker\\nper-card label")', '(1, 7, "Full evidence text")')
    evidence = evidence.replace('        label = p["native"]["ragchecker"]["evidence_verdicts"][eid]\n', '')
    evidence = evidence.replace('            put(ws, row, 1, 6, part, source="full_evidence_text")', '            put(ws, row, 1, 7, part, source="full_evidence_text")')
    evidence = evidence.replace('            put(ws, row, 7, 7, label, label, source="ragchecker_evidence_verdict")\n', '')
    evidence = evidence.replace('[(0, 0, tag), (1, 6, part), (7, 7, label)]', '[(0, 0, tag), (1, 7, part)]')
    judgments = '    result_section = row\n' + judgments
    judgments = judgments.replace('2  |  Same BACE claim and candidate ECs — three support prompts', '3  |  Results — three support prompts')
    judgments = judgments.replace('3  |  Original BACE and native frameworks — saved claims and reasons', '3.1  |  Results — original BACE and native frameworks')
    judgments = judgments.replace('2  |  Three frameworks — native claim, decision and saved reason', '3  |  Results — framework decisions and saved reasons')
    judgments = judgments.replace('Actual saved support sets (EC aliases below)', 'Actual saved support sets (EC aliases above)')
    judgments = judgments.replace('Per-card labels appear beside the full evidence.', 'Per-card labels are listed in the results section below.')
    judgments = judgments.replace('    if rid in ALIGNMENT_NOTES:\n        row = note(ws, row, "Wording note: " + ALIGNMENT_NOTES[rid], warning=True)\n', '')
    result = original[:a] + disclosure + full_disclosure + excerpts + candidates + evidence + judgments + RESULT_DETAILS + original[g:]
    result = result.replace('"Back to this case\'s judgments", rid, 4', '"Back to this case\'s results", rid, result_section')
    result = result.replace('link(ws, 2, 2, 3, "Candidate ECs", rid, candidate_section)', 'link(ws, 2, 2, 3, "Disclosure", rid, 4)')
    result = result.replace('link(ws, 2, 4, 5, "All evidence", rid, evidence_section)', 'link(ws, 2, 4, 5, "Evidence and ECs", rid, excerpt_section)')
    result = result.replace('link(ws, 2, 6, 7, "Full disclosure", rid, disclosure_section)', 'link(ws, 2, 6, 7, "Results", rid, result_section)')
    result = result.replace('link(ws, rr, 6, 6, label, rid, card_rows[eid])', 'link(ws, rr, 6, 7, label, rid, card_rows[eid])')
    result = result.replace('"candidate_section_row": candidate_section + 1, "evidence_section_row": evidence_section + 1,', '"candidate_section_row": candidate_section + 1, "evidence_section_row": evidence_section + 1,\n                      "disclosure_section_row": disclosure_section + 1, "excerpt_section_row": excerpt_section + 1, "result_section_row": result_section + 1,')
    result = result.replace('Every case has the same six sections; navigation links stay visible when scrolling.', 'Each case follows Disclosure, Evidence, then Results; navigation links stay visible when scrolling.')
    result = result.replace('Click a case for its seven-section reading page.', 'Each case follows Disclosure, Evidence, then Results.')
    result = result.replace('Per-card labels appear next to every full evidence card.', 'Per-card labels are listed in the Results section after all source evidence.')
    result = result.replace('row = 4\nnotes = [', 'row = 4\nnotes = [\n    ("Reading order", "Updated 2026-10-22: disclosure passages, native claims and full disclosure come first; evidence excerpts, candidate ECs and all supplied cards come next; decisions, reasons, support-set membership and per-card verdicts come last."),')
    compile(result, str(path), "exec")
    path.write_text(result)
    records.append({"builder": str(path.relative_to(ROOT)), "before_sha256": hashlib.sha256(original.encode()).hexdigest(), "after_sha256": hashlib.sha256(result.encode()).hexdigest()})

(OUT / "migration.json").write_text(json.dumps({"status": "presentation_only", "builders": records, "experiment_inputs_changed": False}, indent=2) + "\n")
print("Updated both builders: Disclosure -> Evidence -> Results.")
