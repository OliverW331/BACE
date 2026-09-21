#!/usr/bin/env python3
"""Prepare a frozen, blinded human-review packet without model calls.

Example (paths are relative to the project root unless absolute):
    python script/human_validation/prepare_materials.py --seed 42

The six outputs are deterministic. An identical rerun is a no-op; any existing
changed file, including a filled annotation, prevents replacement. The private
sample_manifest.json must never be distributed to annotators.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import random
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "script/evaluation"))
from external_evaluation import adapt_case

VERSION = "human_validation_packet_v1"
CLASSES = ("supported_direct", "supported_inferred", "unsupported")
TYPES = ("narrative", "pdf_table_row", "csv_metric")
FILES = ("instructions.md", "sample_manifest.json", "materials.jsonl",
         "reviewer_a.csv", "reviewer_b.csv", "adjudicated.csv")
INPUT_COLUMNS = ("unit_id", "case_id", "unit_type", "source_refs", "target_text")
ANNOTATION_COLUMNS = (
    "reviewer_id", "review_status", "claim_fidelity", "atomicity", "claim_type",
    "support_verdict", "support_type", "evidence_refs", "evidence_quotes",
    "human_claims", "reason",
)
ADJUDICATION_COLUMNS = (
    "adjudicator_id", "adjudication_reason", "post_review_support_set_correct",
    "post_review_diagnosis_correct", "post_review_reason",
)


def digest(data: str | bytes) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def resolve(root: Path, path: str | Path) -> Path:
    return (root / path).resolve()


def index(rows, key):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ValueError(f"Duplicate {key}: {row[key]}")
        result[row[key]] = row
    return result


def rng(seed: int, *namespace: str) -> random.Random:
    # Independent streams prevent a quota change in one task from changing others.
    return random.Random(int(digest(json.dumps([seed, *namespace])), 16))


@dataclass(frozen=True)
class Options:
    seed: int = 42
    claims_per_class: int = 5
    cards_per_case: int = 2
    paragraphs_per_case: int = 2
    expected_embedding_model: str = "text-embedding-3-large"
    expected_generation_model: str = "gpt-5.6-sol"

    def validate(self):
        if min(self.claims_per_class, self.cards_per_case, self.paragraphs_per_case) < 1:
            raise ValueError("All sample quotas must be positive integers.")


class Sources:
    """Check recorded fingerprints and retain a complete input fingerprint ledger."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.hashes: dict[Path, str] = {}

    def check(self, path, expected=None):
        path = resolve(self.root, path)
        actual = digest(path.read_bytes())
        prior = self.hashes.get(path)
        if (expected is not None and actual != expected) or (prior and actual != prior):
            raise ValueError(f"Source hash mismatch: {path}")
        self.hashes[path] = actual
        return path

    def json(self, path):
        return json.loads(self.check(path).read_text(encoding="utf-8"))

    def rows(self, path):
        return [json.loads(line) for line in self.check(path).read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def verify_again(self):
        for path, expected in list(self.hashes.items()):
            self.check(path, expected)

    def ledger(self):
        return {str(p.relative_to(self.root)) if p.is_relative_to(self.root) else str(p): h
                for p, h in sorted(self.hashes.items())}


def paragraphs(text: str) -> list[dict]:
    """Blank-line Markdown blocks, preserving exact offsets and table/list blocks.

    Heading-only and separator-only blocks are excluded. No semantic judgment or
    model output is used to decide which substantive source blocks are eligible.
    """
    result = []
    for match in re.finditer(r"\S[\s\S]*?(?=\n[ \t]*\n|\Z)", text):
        raw = match.group().rstrip()
        if not raw:
            continue
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if all(re.fullmatch(r"#{1,6}\s+.*|[-*_]{3,}", line) for line in lines):
            continue
        result.append({"ref": f"Paragraph {len(result) + 1:02d}", "text": raw,
                       "start": match.start(), "end": match.start() + len(raw)})
    return result


def support_class(record, ec_ids):
    sets = record["support_sets"]
    if not isinstance(sets, list):
        raise ValueError("Support sets must be a list.")
    for item in sets:
        ids = item["ec_claim_ids"]
        if not ids or len(ids) != len(set(ids)) or not set(ids) <= ec_ids:
            raise ValueError("Empty, duplicate or foreign EC in a support set.")
        if item["support_type"] not in ("direct", "inferred"):
            raise ValueError("Unknown support type.")
    if not sets:
        return "unsupported"
    return "supported_direct" if any(s["support_type"] == "direct" for s in sets) else "supported_inferred"


def quote_locations(claim, disclosure, blocks):
    quotes = sorted({q for p in claim["dc_provenance"] for q in p.get("source_quotes", [])})
    if not quotes or any(not q.strip() or q not in disclosure for q in quotes):
        raise ValueError(f"Missing/unlocatable source quote for {claim['dc_id']}")
    locations = []
    for quote in quotes:
        for match in re.finditer(re.escape(quote), disclosure):
            locations.append({"quote": quote, "start": match.start(), "end": match.end()})
    refs = [b["ref"] for b in blocks
            if any(q["start"] < b["end"] and b["start"] < q["end"] for q in locations)]
    return quotes, locations, refs


def load_run(root: Path, run_dir: Path, options: Options):
    options.validate()
    sources = Sources(root)
    summary = sources.json(run_dir / "summary.json")
    frozen = set()
    for info in summary["source_files"].values():
        frozen.add(sources.check(info["path"], info["sha256"]))
    plan = sources.json(run_dir / "plan.json")
    if resolve(root, run_dir / "plan.json") not in frozen:
        raise ValueError("The run plan is not anchored in the summary source hashes.")
    for path, expected in plan["frozen_files"].items():
        frozen.add(sources.check(path, expected))
    execution = sources.json(run_dir / "execution_status.json")
    selected_ids = [c["generation_case_id"] for c in plan["cases"]]
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ValueError("Empty or duplicate run case IDs.")
    if execution["status"] != "complete" or set(execution["completed_case_ids"]) != set(selected_ids):
        raise ValueError("The selected run is not complete.")
    if summary["case_count"] != len(selected_ids):
        raise ValueError("Case count differs from the run summary.")

    def frozen_rows(path):
        if resolve(root, path) not in frozen:
            raise ValueError(f"Input is not anchored in run hashes: {path}")
        return sources.rows(path)

    inputs = index(frozen_rows(plan["generation_cases"]), "generation_case_id")
    outputs = index(frozen_rows(plan["generated_disclosures"]), "generation_case_id")
    # Locate native case directories by their records, not by a hardcoded run-name split.
    native_dirs = {}
    for directory in sorted((run_dir / "bace").iterdir()):
        if not directory.is_dir():
            continue
        records = frozen_rows(directory / "dedup/dc_claims.jsonl")
        ids = {r["generation_case_id"] for r in records}
        if len(ids) != 1:
            raise ValueError(f"Empty/mixed native case: {directory}")
        cid = ids.pop()
        if cid in native_dirs:
            raise ValueError(f"Duplicate native case directory: {cid}")
        native_dirs[cid] = (directory, records)
    if set(native_dirs) != set(selected_ids):
        raise ValueError("Native case directories do not match the run plan.")

    cases, population = [], Counter()
    for i, cid in enumerate(sorted(selected_ids), 1):
        case, output = inputs[cid], outputs[cid]
        adapted = adapt_case(case, output)
        model = output["generation_model"]["model"]
        embedding = case["retrieval_setting"]["embedding_model"]
        if model != options.expected_generation_model:
            raise ValueError(f"Unexpected generation model in {cid}: {model}")
        if embedding.replace("_", "-") != options.expected_embedding_model.replace("_", "-"):
            raise ValueError(f"Unexpected embedding model in {cid}: {embedding}")
        for key, value in (("company_name", case["company_name"]),
                           ("target_reporting_year", str(case["target_reporting_year"])),
                           ("task_title", case["task_title"])):
            if value not in case["instruction"]:
                raise ValueError(f"Case metadata not visible in the generation instruction: {key}")
        directory, dc_rows = native_dirs[cid]
        dc = index(dc_rows, "dc_id")
        ec = index(frozen_rows(directory / "dedup/ec_claims.jsonl"), "ec_id")
        support = index(frozen_rows(directory / "support/dc_support_sets.jsonl"), "dc_claim_id")
        if not ec or set(dc) != set(support):
            raise ValueError(f"Incomplete claim/support coverage: {cid}")
        if any(r["generation_case_id"] != cid for r in ec.values()):
            raise ValueError(f"Cross-case EC records: {cid}")
        classes = {key: support_class(record, set(ec)) for key, record in support.items()}
        population.update(classes.values())
        cards = [card for card in case["prompt_evidence"] if card["shown_in_prompt"]]
        if len({c["evidence_id"] for c in cards}) != len(cards):
            raise ValueError(f"Duplicate supplied evidence IDs: {cid}")
        if {c["evidence_type"] for c in cards} != set(TYPES):
            raise ValueError(f"The balanced card design requires all three evidence types: {cid}")
        for record in dc.values():
            if record["generated_disclosure_id"] != output["generation_output_id"]:
                raise ValueError(f"DC points to a different generated disclosure: {record['dc_id']}")
            for provenance in record["dc_provenance"]:
                if provenance["generated_text_hash"] != output["generated_text_hash"]:
                    raise ValueError(f"DC provenance has a different response hash: {record['dc_id']}")
        cases.append({"cid": cid, "case_id": f"Case {i:02d}", "input": case,
                      "output": output, "adapted": adapted, "dc": dc, "ec": ec,
                      "classes": classes, "cards": cards, "paragraphs": paragraphs(adapted["response"]),
                      "native_dir": str(directory.relative_to(root))})
    counts = summary["aggregates"]["bace"]
    expected = {"supported_direct": counts["bace_supported_direct"],
                "supported_inferred": counts["bace_supported_inferred"],
                "unsupported": counts["bace_unsupported"]}
    if dict(population) != expected or sum(population.values()) != counts["bace_dc_count"]:
        raise ValueError("Native support counts do not match the frozen summary.")
    return cases, sources, plan


def sample_units(cases, options):
    """Sample native DCs and independent source units; keep allocation private."""
    options.validate()
    case_order = sorted(c["cid"] for c in cases)
    rng(options.seed, "card-type-case-order").shuffle(case_order)
    type_order = list(TYPES)
    rng(options.seed, "card-type-order").shuffle(type_order)
    quotas = {}
    for i, cid in enumerate(case_order):
        quotas[cid] = Counter(type_order[(i * options.cards_per_case + j) % len(TYPES)]
                              for j in range(options.cards_per_case))
    materials, mappings = [], []
    for case in sorted(cases, key=lambda c: c["cid"]):
        cid = case["cid"]
        source_units, claim_units = [], []

        def add(target, kind, text, refs, private, quotes=None):
            target.append(({"unit_type": kind, "target_text": text,
                            "source_refs": refs, "source_quotes": quotes or []}, private))

        for label in CLASSES:
            pool = sorted(key for key, value in case["classes"].items() if value == label)
            n = options.claims_per_class
            if len(pool) < n:
                raise ValueError(f"Insufficient {label} DCs in {cid}: need {n}, have {len(pool)}")
            for key in rng(options.seed, cid, "claims", label).sample(pool, n):
                claim = case["dc"][key]
                quotes, locations, refs = quote_locations(claim, case["adapted"]["response"], case["paragraphs"])
                add(claim_units, "claim_support", claim["dc_text"], refs,
                    {"dc_id": key, "bace_support_class": label, "population_count": len(pool),
                     "sample_count": n, "inclusion_probability": n / len(pool),
                     "inverse_probability_weight": len(pool) / n, "quote_locations": locations}, quotes)

        for kind in TYPES:
            pool = sorted((card for card in case["cards"] if card["evidence_type"] == kind),
                          key=lambda c: c["evidence_id"])
            # Every type must support every possible randomized allocation.
            if len(pool) < (options.cards_per_case + len(TYPES) - 1) // len(TYPES):
                raise ValueError(f"Insufficient {kind} evidence cards in {cid}")
            n = quotas[cid][kind]
            for card in rng(options.seed, cid, "cards", kind).sample(pool, n):
                probability = options.cards_per_case / (len(TYPES) * len(pool))
                add(source_units, "ec_source_audit", card["retrieval_text"], [card["prompt_label"]],
                    {"evidence_id": card["evidence_id"], "evidence_type": kind,
                     "population_count": len(pool), "assigned_type_quota": n,
                     "inclusion_probability": probability,
                     "inverse_probability_weight": 1 / probability,
                     "system_claim_ids": sorted(key for key, r in case["ec"].items()
                                                if card["evidence_id"] in r["evidence_card_ids"])})
        blocks = case["paragraphs"]
        n = options.paragraphs_per_case
        if len(blocks) < n:
            raise ValueError(f"Insufficient source paragraphs in {cid}: need {n}, have {len(blocks)}")
        for block in rng(options.seed, cid, "paragraphs").sample(blocks, n):
            add(source_units, "dc_source_audit", block["text"], [block["ref"]],
                {"start": block["start"], "end": block["end"], "population_count": len(blocks),
                 "sample_count": n, "inclusion_probability": n / len(blocks),
                 "inverse_probability_weight": len(blocks) / n})
        rng(options.seed, cid, "source-presentation").shuffle(source_units)
        rng(options.seed, cid, "claim-presentation").shuffle(claim_units)
        public_units = []
        for public, private in source_units + claim_units:
            unit_id = f"HV{len(mappings) + 1:04d}"
            public = {"unit_id": unit_id, **public}
            mappings.append({"unit_id": unit_id, "case_id": case["case_id"],
                             "generation_case_id": cid, "unit_type": public["unit_type"],
                             "native_case_directory": case["native_dir"],
                             "target_text_sha256": digest(public["target_text"]), **private})
            public_units.append(public)
        # Whitelist only prompt-visible content; do not serialize native records.
        materials.append({"case_id": case["case_id"], "company_name": case["input"]["company_name"],
                          "reporting_year": case["input"]["target_reporting_year"],
                          "task": case["input"]["task_title"],
                          "disclosure_text": case["adapted"]["response"],
                          "paragraphs": [{"ref": b["ref"], "text": b["text"]} for b in blocks],
                          "evidence": [{"label": label, "context": context} for label, context in
                                       zip(case["adapted"]["prompt_labels"], case["adapted"]["contexts"], strict=True)],
                          "units": public_units})
    return materials, mappings


def validate_packet(materials, mappings, options):
    """Reject unexpected fields and invalid links before any file is written."""
    case_fields = {"case_id", "company_name", "reporting_year", "task", "disclosure_text",
                   "paragraphs", "evidence", "units"}
    unit_fields = {"unit_id", "unit_type", "target_text", "source_refs", "source_quotes"}
    mapping = index(mappings, "unit_id")
    seen = set()
    for case in materials:
        if set(case) != case_fields:
            raise ValueError("Unexpected field in blinded case material.")
        for evidence in case["evidence"]:
            if set(evidence) != {"label", "context"}:
                raise ValueError("Unexpected field in blinded evidence.")
        for block in case["paragraphs"]:
            if set(block) != {"ref", "text"} or block["text"] not in case["disclosure_text"]:
                raise ValueError("Invalid disclosure paragraph.")
        valid_refs = {b["ref"] for b in case["paragraphs"]} | {e["label"] for e in case["evidence"]}
        counts = Counter()
        for unit in case["units"]:
            if set(unit) != unit_fields or unit["unit_id"] in seen:
                raise ValueError("Unexpected field or duplicate unit in blinded material.")
            seen.add(unit["unit_id"])
            record = mapping[unit["unit_id"]]
            if record["case_id"] != case["case_id"] or not set(unit["source_refs"]) <= valid_refs:
                raise ValueError("Invalid case/source link.")
            if digest(unit["target_text"]) != record["target_text_sha256"]:
                raise ValueError("Unit text does not match its sampling manifest.")
            if any(q not in case["disclosure_text"] for q in unit["source_quotes"]):
                raise ValueError("Source quotation is not in the original disclosure.")
            if not 0 < record["inclusion_probability"] <= 1:
                raise ValueError("Invalid sampling probability.")
            counts[unit["unit_type"]] += 1
        if counts != {"claim_support": options.claims_per_class * 3,
                      "ec_source_audit": options.cards_per_case,
                      "dc_source_audit": options.paragraphs_per_case}:
            raise ValueError("Unexpected per-case sample counts.")
    if seen != set(mapping):
        raise ValueError("Sampling manifest and reviewer units differ.")


GUIDE = """# Human validation instructions

## Files and review order

Each annotator receives this file, materials.jsonl, and only their own blank
reviewer CSV. This Markdown file is the readable casebook; JSONL contains the
same material for software use. Find a unit ID with your editor's search.
The coordinator retains sample_manifest.json and adjudicated.csv. Do not open
the private manifest, original evaluator outputs, prior assistant reviews, or
another annotator's sheet during independent review.

Complete Stage 1 source audits across all cases before inspecting the Stage 2
target-claim section. Submit or otherwise lock the Stage 1 answers with the
coordinator before moving on. Stage 2 contains model-extracted propositions,
so source-first order is a procedural blinding requirement; the casebook does
not provide a technical access barrier between stages. CSV rows follow the
same stage order. Do not inspect later rows early.

Before either stage, calibrate the rules using separate practice material that
will not enter validation statistics. The present packet contains evaluation
units only. Preserve both independent sheets before adjudication. Count
agreement on the original answers, then resolve disagreements, using a third
reviewer when necessary. Human correctness labels are not supplied here.

## Evidence boundary

Use the complete original disclosure and ALL supplied evidence shown under the
same case. Source labels and headings can resolve attribution, but do not
establish facts absent from the source text. Do not search external reports or
use unshown company information to establish support. A claim can be true in
the world yet unsupported by this supplied evidence.

Keep report year, measurement year, action year, baseline and deadline distinct.
Preserve entity, scope, quantity, unit, negation, intention and implementation
status. Plans do not establish execution. A correct sum still requires matching
periods, units, entities, categories and non-overlapping accounting boundaries.
One silent card does not establish absence from all evidence or a whole report.
Do not turn a genuine scope ambiguity into a confident unsupported verdict.

## Stage 1: Independent source extraction

For ec_source_audit, enumerate every substantive atomic proposition asserted
by the selected card, using all visible evidence only to resolve context. For
dc_source_audit, enumerate every substantive atomic proposition asserted by the
selected disclosure block, using the complete disclosure for context. Do not
use the evidence to repair errors in what the disclosure itself asserts.

Use human_claims for a numbered list, one proposition per line, with exact
source quotes. Preserve negative, prospective, uncertain and off-topic claims.
Record non-propositional material or genuinely unresolved meaning in reason.
Write NONE explicitly if there are no extractable propositions. Do not inspect
system ECs or DCs first. These answers will later identify omissions and semantic
changes, including source material the system never represented.

## Stage 2: Target-claim assessment

For claim_support, first compare target_text against its original disclosure.
Source quotes are locators, not endorsements of the extraction. Then assess the
literal target_text against ALL supplied evidence, preserving its full meaning.
If the target differs from the original, record that difference separately in
claim_fidelity and human_claims; never silently replace it and score the replacement
as the native claim. Compound propositions may need several human claims and
component-level verdicts in reason; do not copy one verdict to every component.

For entailed, record a sufficient set of evidence labels and exact quotes.
Remove unnecessary evidence, and note alternative sufficient sets if found.
Record a transparent reasoning step for inferred support. Several evidence
items do not automatically make support inferred. For contradicted, cite the
incompatible evidence at matching boundaries. For insufficient_evidence, explain
the missing premise; relevant evidence is not necessarily supporting evidence.

## CSV fields

Do not change unit_id, case_id, unit_type, source_refs or target_text. Multiline
cells are valid CSV: use a spreadsheet application that preserves UTF-8. Evidence
references always refer to the same case. There are source-audit units as well
as claim units; a source unit may contain multiple human propositions.

| Field | Allowed values or content |
|---|---|
| reviewer_id | Your stable pseudonym |
| review_status | completed; needs_adjudication |
| claim_fidelity | faithful; meaning_changed; context_missing; not_a_claim; unclear |
| atomicity | atomic; compound; unclear |
| claim_type | substantive_factual; evidence_absence; report_non_disclosure; other |
| support_verdict | entailed; contradicted; insufficient_evidence; scope_ambiguous |
| support_type | direct; inferred; not_applicable |
| evidence_refs | Evidence labels, e.g. Evidence 2; Evidence 19 |
| evidence_quotes | Exact evidence quotations, labelled by card |
| human_claims | Independent source propositions or proposed corrections, with quotes |
| reason | Explanation, uncertainty and component-level details |

On source-audit rows, fill reviewer_id, review_status, human_claims and reason;
leave target-claim classification fields empty. On target-claim rows, complete
the classification fields and justify the verdict. Use not_applicable for
support_type unless entailed. Ambiguous propositions remain explicitly unresolved.

## Adjudication and interpretation

The coordinator completes adjudicated.csv after preserving independent answers.
Its final labels use the same fields. adjudicator_id and adjudication_reason
record how the final decision was reached. Only after blind judgments are locked
may the coordinator disclose native support sets and diagnoses. Record their
correctness separately using post_review_support_set_correct and
post_review_diagnosis_correct (yes; no; unclear; not_applicable), with an explanation
in post_review_reason. These optional later checks do not replace blind judgments.

Separate extraction fidelity, native-claim support, source-proposition coverage,
and explanation correctness. Restrict support accuracy on source-faithful aligned
propositions as appropriate, while reporting distorted, compound, ambiguous and
unmatched items separately; do not silently drop pipeline errors. Claim-type labels
apply to both supported and unsupported propositions. Different evaluators can
split claims differently, so alignment must precede any cross-framework comparison.

This is validation within a previously examined engineering pilot, not a fresh
held-out benchmark. The coordinator uses the private sampling probabilities for
weighted within-run summaries; neither an unweighted sample mean nor this pilot
establishes performance across all generation cases, companies or standards.
Keep source-audit and claim-support results separate. Source blocks are the audit
sampling units; their embedded propositions are not independent random samples.

## Readable casebook

The original disclosure and evidence below are quoted verbatim. Paragraph numbers
are navigation aids; heading-only blocks are excluded from paragraph sampling.
All evidence cards are retained in original prompt order with visible headings
and source labels. Only the selected source units require Stage 1 extraction.
"""


def fenced(text):
    longest = max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}\n"


def render_instructions(materials):
    parts = [GUIDE, "\n# Stage 1 casebook\n"]
    for case in materials:
        case_id = case["case_id"]
        parts.append(f"\n## {case_id}\n\n{case['company_name']} | {case['reporting_year']} | {case['task']}\n")
        parts.append("\n### Original disclosure\n\n" + fenced(case["disclosure_text"]))
        parts.append("\n### Selected source units\n")
        for unit in case["units"]:
            if unit["unit_type"] == "claim_support":
                continue
            parts.append(f"\n#### {unit['unit_id']}\n\n{unit['unit_type']} | {', '.join(unit['source_refs'])}\n\n"
                         + fenced(unit["target_text"]))
        parts.append("\n### Complete supplied evidence\n")
        for evidence in case["evidence"]:
            parts.append("\n" + fenced(evidence["context"]))
    parts.append("\n# Stage 2 target claims\n\nBegin only after submitting the independent source-audit answers.\n")
    for case in materials:
        parts.append(f"\n## {case['case_id']} target claims\n\nUse the full disclosure and evidence in {case['case_id']} above.\n")
        for unit in case["units"]:
            if unit["unit_type"] != "claim_support":
                continue
            parts.append(f"\n### {unit['unit_id']}\n\nOriginal location: {', '.join(unit['source_refs']) or 'Disclosure heading/context'}\n\n"
                         + fenced(unit["target_text"]) + "\nDisclosure source quotes:\n")
            for quote in unit["source_quotes"]:
                parts.append("\n" + fenced(quote))
    return "".join(parts)


def csv_text(materials, adjudication=False):
    stream = io.StringIO(newline="")
    fields = INPUT_COLUMNS + ANNOTATION_COLUMNS + (ADJUDICATION_COLUMNS if adjudication else ())
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for source_stage in (True, False):
        for case in materials:
            for unit in case["units"]:
                if (unit["unit_type"] != "claim_support") != source_stage:
                    continue
                writer.writerow({"unit_id": unit["unit_id"], "case_id": case["case_id"],
                                 "unit_type": unit["unit_type"], "source_refs": "; ".join(unit["source_refs"]),
                                 "target_text": unit["target_text"]})
    return stream.getvalue()


def build_packet(root: Path, run_dir: Path, options: Options):
    cases, sources, plan = load_run(root, run_dir, options)
    materials, mappings = sample_units(cases, options)
    validate_packet(materials, mappings, options)
    sources.check(Path(__file__))
    sources.check(ROOT / "script/evaluation/external_evaluation.py")
    sources.verify_again()
    files = {
        "instructions.md": render_instructions(materials),
        "materials.jsonl": "".join(json.dumps(c, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for c in materials),
        "reviewer_a.csv": csv_text(materials), "reviewer_b.csv": csv_text(materials),
        "adjudicated.csv": csv_text(materials, adjudication=True),
    }
    manifest = {
        "schema_version": VERSION, "access": "COORDINATOR ONLY - contains automated sampling labels",
        "run_directory": str(run_dir.relative_to(root)) if run_dir.is_relative_to(root) else str(run_dir),
        "options": vars(options), "source_hashes": sources.ledger(),
        "case_count": len(cases), "population_dc_count": sum(len(c["dc"]) for c in cases),
        "sample_counts": dict(Counter(m["unit_type"] for m in mappings)),
        "sample_support_classes": dict(Counter(m["bace_support_class"] for m in mappings if "bace_support_class" in m)),
        "sample_evidence_types": dict(Counter(m["evidence_type"] for m in mappings if "evidence_type" in m)),
        "extraction_pipeline": plan["extraction_pipeline"],
        "sampling_design": {
            "claims": "SRS without replacement within each case x native support class; pi = n_h / N_h. Classes derived from native support sets, not review CSVs.",
            "cards": "Uniformly shuffled case order and type order; cyclic type allocation balances total quotas. SRS without replacement within each assigned case/type. Marginal pi = cards_per_case / (3 * N_case_type), including randomized type assignment; do not use the realized type quota as the marginal inclusion probability.",
            "paragraphs": "SRS without replacement within each case's blank-line Markdown blocks after excluding heading-only and separator-only blocks; pi = n / N. Exact offsets preserved.",
            "rng": "Python random.Random seeded independently by SHA256 of JSON [seed, namespace...]; sorted source IDs before draws. Output order does not group native support labels.",
            "claim_estimand": "Within each case, sum(y / pi) / N_case; average case estimates equally for a disclosure-macro estimate. Pool weighted totals separately for a claim-micro estimate. Precision/recall use weighted confusion totals. Report alignment and ambiguity exclusions.",
            "source_estimand": "Source-block audit only, separately by EC/DC source; embedded human claims are not independent equal-probability samples.",
            "scope": "Existing ten-case engineering pilot; no independent held-out validation or population generalization is claimed.",
            "practice": "No calibration units are included. Use separate practice material and freeze the rubric before annotating these samples.",
        },
        "case_populations": [{"case_id": c["case_id"], "generation_case_id": c["cid"],
                              "dc_count": len(c["dc"]), "support_classes": dict(Counter(c["classes"].values())),
                              "card_types": dict(Counter(e["evidence_type"] for e in c["cards"])),
                              "paragraph_count": len(c["paragraphs"]),
                              "generation_run_id": c["output"]["run_id"],
                              "generation_model": c["output"]["generation_model"],
                              "retrieval_setting": c["input"]["retrieval_setting"],
                              "prompt_sha256": c["adapted"]["prompt_hash"],
                              "disclosure_sha256": c["adapted"]["response_hash"]} for c in cases],
        "units": mappings,
        "distribution": {"reviewer_a": ["instructions.md", "materials.jsonl", "reviewer_a.csv"],
                         "reviewer_b": ["instructions.md", "materials.jsonl", "reviewer_b.csv"],
                         "coordinator_only": ["sample_manifest.json", "adjudicated.csv"]},
        "pristine_output_sha256": {name: digest(text) for name, text in files.items()},
        "validation": {"source_hashes": "verified", "prompt_visible_evidence": "verified",
                       "native_population_counts": "verified", "sample_links_and_counts": "verified",
                       "blinded_field_allowlist": "verified", "human_annotations": 0},
    }
    files["sample_manifest.json"] = json_text(manifest)
    return files, manifest


def write_packet(output_dir: Path, files):
    """Publish only a complete packet; preserve every pre-existing changed file."""
    if set(files) != set(FILES):
        raise ValueError("A packet must contain exactly the six declared files.")
    if output_dir.is_symlink():
        raise ValueError("Output directory must not be a symlink.")
    encoded = {name: value.encode("utf-8") for name, value in files.items()}
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError("Output path is not a directory.")
        entries = {p.name for p in output_dir.iterdir()}
        if entries:
            if entries == set(FILES) and all((output_dir / name).is_file()
                                            and not (output_dir / name).is_symlink()
                                            and (output_dir / name).read_bytes() == value
                                            for name, value in encoded.items()):
                return "unchanged"
            raise ValueError("Output directory contains existing or changed files. Nothing was overwritten; use a new output directory.")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.prepare-", dir=output_dir.parent))
    try:
        for name, value in encoded.items():
            with (staging / name).open("xb") as stream:
                stream.write(value)
        staging.rename(output_dir)  # Atomic; fails if another writer populated the directory.
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return "created"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--run-dir", type=Path, default=Path("evidence_pilot/evaluation/external_comparison/pilot_v2"))
    parser.add_argument("--output-dir", type=Path, default=Path("evidence_pilot/evaluation/human_validation/pilot_v2"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--claims-per-class", type=int, default=5)
    parser.add_argument("--cards-per-case", type=int, default=2)
    parser.add_argument("--paragraphs-per-case", type=int, default=2)
    parser.add_argument("--expected-embedding-model", default="text-embedding-3-large")
    parser.add_argument("--expected-generation-model", default="gpt-5.6-sol")
    parser.add_argument("--check-only", action="store_true", help="Validate and construct in memory; write no files.")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    run_dir = resolve(root, args.run_dir)
    raw_output = root / args.output_dir
    output = raw_output.resolve()
    try:
        if raw_output.is_symlink() or output.is_relative_to(run_dir) or run_dir.is_relative_to(output):
            raise ValueError("Output must be separate from the source run and cannot be a symlink.")
        options = Options(args.seed, args.claims_per_class, args.cards_per_case,
                          args.paragraphs_per_case, args.expected_embedding_model, args.expected_generation_model)
        files, manifest = build_packet(root, run_dir, options)
        status = "validated_no_files_written" if args.check_only else write_packet(output, files)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json_text({"status": status, "output_directory": str(output),
                     "cases": manifest["case_count"], "sample_counts": manifest["sample_counts"],
                     "sample_support_classes": manifest["sample_support_classes"],
                     "sample_evidence_types": manifest["sample_evidence_types"],
                     "verified_source_files": len(manifest["source_hashes"])}), end="")


if __name__ == "__main__":
    main()
