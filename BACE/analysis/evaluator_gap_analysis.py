"""Read-only diagnostic statistics for notebook 04; no evaluator/model calls.

Earlier paper diagnostics are hash-verified derived inputs, not a second
implementation of their calculations. New statistics and exports live under
outputs/evaluator_gap. Nothing in the existing snapshot is regenerated.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "outputs/evaluator_gap"
SNAPSHOT = HERE / "outputs/snapshot"
PAPER = ROOT / "paper/analysis/evaluator_gap"
SEED = 20260921
DRAWS = 2000
SUPPORT_LABELS = ["direct", "inferred"]
LABELS = ["non_disclosure_statement", "contradiction", "evidence_conflation",
          "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty"]
INPUTS = {}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path, expected=None):
    path = Path(path).resolve()
    digest = sha(path)
    if expected is not None and digest != expected:
        raise ValueError(f"Input hash mismatch: {path.relative_to(ROOT)}")
    INPUTS[str(path.relative_to(ROOT))] = {"sha256": digest, "bytes": path.stat().st_size}
    return path


def read_json(path):
    return json.loads(record(path).read_text())


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def export_table(name, frame):
    directory = OUT / "tables"
    directory.mkdir(parents=True, exist_ok=True)
    frame.to_csv(directory / f"{name}.csv", index=False)
    return frame


def load_inputs():
    """Validate frozen-snapshot hashes and reconcile the earlier derived inputs."""
    manifest = read_json(SNAPSHOT / "manifest.json")
    snapshot = {name: pd.read_csv(record(SNAPSHOT / f"{name}.csv", manifest["tables"][name]))
                for name in ("metrics", "claims", "external_claims")}
    prior = read_json(PAPER / "provenance.json")
    case = pd.read_csv(record(PAPER / "case_diagnostics.csv", prior["output_sha256"]["case_diagnostics.csv"]))
    pairs = pd.read_csv(record(PAPER / "literal_pairs.csv", prior["output_sha256"]["literal_pairs.csv"]))
    previous = json.loads(record(PAPER / "results.json", prior["output_sha256"]["results.json"]).read_text())
    for name in ("statistical_analysis_plan.md", "literal_example_review.md", "literal_examples.json",
                 "evonik_boundary_recheck.json"):
        record(PAPER / name)
    examples = read_json(PAPER / "literal_examples.json")
    example_ledger = read_json(SNAPSHOT / "sources.json")
    assert sha(SNAPSHOT / "sources.json") == examples["source_ledger_sha256"]
    for name, expected in examples["source_hashes"].items():
        assert expected == example_ledger[name]
        record(ROOT / name, expected)
    execution = read_json(ROOT / "BACE/results/main_v1/execution_status.json")
    assert execution["status"] not in ("running", "finalizing") and not execution.get("active_cases")
    metrics = snapshot["metrics"]
    common = metrics.loc[metrics.bace_complete & metrics.ragchecker_complete & metrics.ragas_complete].copy()
    ids = set(common.generation_case_id)
    assert ids == set(execution["completed_case_ids"]) == set(case.generation_case_id)
    assert case.generation_case_id.is_unique and common.generation_case_id.is_unique
    case = case.sort_values("generation_case_id").reset_index(drop=True)
    common = common.set_index("generation_case_id").loc[case.generation_case_id].reset_index()
    claims = snapshot["claims"]
    assert set(claims.generation_case_id) == ids
    assert not claims.duplicated(["generation_case_id", "dc_id"]).any()
    claims = claims.assign(supported=claims.label.isin(SUPPORT_LABELS),
                           zero_candidates=claims.candidate_count.eq(0))
    assert (claims.supported == claims.support_set_count.gt(0)).all()
    assert not (claims.supported & claims.zero_candidates).any()
    assert claims.label.isin(SUPPORT_LABELS + LABELS).all()
    grouped = claims.groupby("generation_case_id").agg(n=("dc_id", "size"),
                s=("supported", "sum"), z=("zero_candidates", "sum")).loc[case.generation_case_id]
    for derived, grouped_column in [("bace_dc_count", "n"), ("bace_supported", "s"),
                                    ("zero_candidate_dc_count", "z")]:
        assert np.array_equal(case[derived].to_numpy(), grouped[grouped_column].to_numpy())
    assert np.allclose(case.bace_native_rate, common.bace_support_rate_all_dc)
    assert np.allclose(case.bace_excluding_non_disclosure_rate,
                       common.bace_support_rate_excluding_non_disclosure_sensitivity)
    assert np.allclose(case.hypothetical_all_zero_candidate_supported_rate,
                       (case.bace_supported + case.zero_candidate_dc_count) / case.bace_dc_count)
    for method in ("ragchecker", "ragas"):
        erows = snapshot["external_claims"].loc[lambda d: (d.framework == method) & d.generation_case_id.isin(ids)]
        counts = erows.groupby("generation_case_id").supported.agg(["size", "sum"]).loc[case.generation_case_id]
        assert np.array_equal(counts["size"], case[f"{method}_claim_count"])
        assert np.array_equal(counts["sum"], case[f"{method}_supported"])
        assert np.allclose(case[f"{method}_rate"], common[f"{method}_faithfulness"])
    assert pairs.framework.eq("ragas").all()
    assert not pairs.duplicated(["generation_case_id", "bace_dc_id"]).any()
    assert not pairs.duplicated(["generation_case_id", "external_claim_index"]).any()
    normalize = lambda values: values.str.casefold().str.split().str.join(" ")
    assert normalize(pairs.bace_dc_text).equals(normalize(pairs.external_claim_text))
    checked = pairs.merge(claims, left_on=["generation_case_id", "bace_dc_id"],
                          right_on=["generation_case_id", "dc_id"], validate="one_to_one")
    assert len(checked) == len(pairs) and (checked.bace_supported == checked.supported).all()
    assert (checked.bace_dc_text == checked.dc_text).all()
    ext = snapshot["external_claims"].loc[lambda d: d.framework.eq("ragas")]
    checked_external = pairs.merge(ext, left_on=["generation_case_id", "external_claim_index"],
                                  right_on=["generation_case_id", "claim_index"], validate="one_to_one")
    assert len(checked_external) == len(pairs)
    assert (checked_external.external_supported == checked_external.supported).all()
    assert (checked_external.external_claim_text == checked_external.claim_text).all()
    pairs = pairs.merge(case[["generation_case_id", "company_id", "company_name", "task", "year"]],
                        on="generation_case_id", validate="many_to_one")
    assert len(pairs) == previous["literal_alignment"]["ragas"]["pairs"]
    cohorts = pd.DataFrame([
        {"cohort": "Planned", "disclosures": len(metrics), "companies": metrics.company_id.nunique()},
        {"cohort": "Paired completed", "disclosures": len(case), "companies": case.company_id.nunique()},
        {"cohort": "At least one literal pair", "disclosures": pairs.generation_case_id.nunique(),
         "companies": pairs.company_id.nunique()}])
    export_table("cohorts", cohorts)
    export_table("excluded_cases", metrics.loc[~metrics.generation_case_id.isin(ids),
                 ["generation_case_id", "company_name", "year", "task", "state_status"]])
    return {"case": case, "common": common, "claims": claims, "pairs": pairs,
            "previous": previous, "cohorts": cohorts, "examples": examples}


class ClusterBootstrap:
    """Ratio of cluster totals; equal disclosure weights for per-case means.

    All paired contrasts use the same company resamples. Ratios for subgroups
    retain the complete common-cohort company universe, including zero-count
    clusters. This is descriptive cluster-resampling uncertainty, not a
    design-adjusted population estimate or model-run variability.
    """
    def __init__(self, company_ids, draws=DRAWS, seed=SEED):
        self.companies = sorted(set(company_ids))
        self.draws, self.seed = draws, seed
        rng = np.random.default_rng(seed)
        self.take = rng.integers(0, len(self.companies), size=(draws, len(self.companies)))

    def ratio(self, frame, numerator, denominator):
        grouped = frame.groupby("company_id")[[numerator, denominator]].sum().reindex(self.companies, fill_value=0)
        a = grouped[numerator].to_numpy(dtype=float)
        b = grouped[denominator].to_numpy(dtype=float)
        assert np.isfinite(a).all() and np.isfinite(b).all() and (b >= 0).all()
        assert b.sum() > 0
        an, bn = a[self.take].sum(axis=1), b[self.take].sum(axis=1)
        valid = bn > 0
        reps = an[valid] / bn[valid]
        low, high = np.quantile(reps, [0.025, 0.975])
        keep = b.sum() - b > 0
        loo = (a.sum() - a[keep]) / (b.sum() - b[keep])
        return {"estimate": float(a.sum() / b.sum()), "low": float(low), "high": float(high),
                "companies_with_observations": int((b > 0).sum()),
                "resampling_companies": len(b), "denominator": float(b.sum()),
                "valid_draws": int(valid.sum()), "undefined_draws": int((~valid).sum()),
                "leave_one_company_out_min": float(loo.min()),
                "leave_one_company_out_max": float(loo.max())}

    def mean(self, frame, column):
        return self.ratio(frame.assign(_one=1), column, "_one")


def compute_statistics(data):
    case, claims, pairs = data["case"], data["claims"], data["pairs"]
    boot = ClusterBootstrap(case.company_id)
    score_columns = {
        "BACE: all DCs": "bace_native_rate",
        "BACE: exclude non-disclosure": "bace_excluding_non_disclosure_rate",
        "BACE: all empty sets supported": "hypothetical_all_zero_candidate_supported_rate",
        "RAGChecker: native": "ragchecker_rate", "RAGAS: native": "ragas_rate"}
    scores = pd.DataFrame([{"condition": label, "column": column, **boot.mean(case, column)}
                           for label, column in score_columns.items()])
    contrasts = {
        "Non-disclosure exclusion minus all-DC BACE": ("bace_excluding_non_disclosure_rate", "bace_native_rate"),
        "All empty sets supported minus all-DC BACE": ("hypothetical_all_zero_candidate_supported_rate", "bace_native_rate"),
        "BACE minus RAGChecker": ("bace_native_rate", "ragchecker_rate"),
        "BACE minus RAGAS": ("bace_native_rate", "ragas_rate"),
        "Non-disclosure exclusion minus RAGChecker": ("bace_excluding_non_disclosure_rate", "ragchecker_rate"),
        "Non-disclosure exclusion minus RAGAS": ("bace_excluding_non_disclosure_rate", "ragas_rate")}
    effects = pd.DataFrame([{"contrast": label, **boot.mean(case.assign(_delta=case[a] - case[b]), "_delta")}
                            for label, (a, b) in contrasts.items()])
    candidates = claims.groupby("label").agg(claims=("dc_id", "size"), zero_candidates=("zero_candidates", "sum"),
                 median_candidates=("candidate_count", "median"), max_candidates=("candidate_count", "max")).reindex(SUPPORT_LABELS + LABELS).reset_index()
    candidates["zero_candidate_fraction"] = candidates.zero_candidates / candidates.claims
    frequencies = claims.assign(group=np.where(claims.supported, "Supported", "Unsupported")).groupby(
        ["group", "candidate_count"]).size().rename("claims").reset_index()
    frequencies["cumulative_fraction"] = frequencies.groupby("group").claims.cumsum() / frequencies.groupby("group").claims.transform("sum")
    group_rows = []
    for method in ("ragchecker", "ragas"):
        count_gap = case.bace_dc_count - case[f"{method}_claim_count"]
        definitions = {"All paired cases": pd.Series(True, index=case.index),
                       "BACE count no greater": count_gap.le(0),
                       "Exactly equal counts": count_gap.eq(0), "BACE count greater": count_gap.gt(0)}
        for name, mask in definitions.items():
            selected = case.loc[mask].assign(_gap=lambda d: d.bace_native_rate - d[f"{method}_rate"])
            group_rows.append({"method": method, "group": name, "disclosures": len(selected),
                               **boot.mean(selected, "_gap")})
    inventory = pd.DataFrame(group_rows)
    joint = pd.crosstab(pairs.bace_supported, pairs.external_supported).reindex(
        index=[True, False], columns=[True, False], fill_value=0)
    joint_rows = pd.DataFrame([{"bace_supported": bool(b), "ragas_supported": bool(r), "pairs": int(joint.loc[b, r])}
                              for b in [True, False] for r in [True, False]])
    pair_values = pairs.assign(_one=1, _bace=pairs.bace_supported.astype(int),
                                _ragas=pairs.external_supported.astype(int),
                                _difference=pairs.bace_supported.astype(int) - pairs.external_supported.astype(int),
                                _agreement=pairs.bace_supported.eq(pairs.external_supported).astype(int))
    literal = pd.DataFrame([{"quantity": label, **boot.ratio(pair_values, column, "_one")}
                            for label, column in [("BACE support", "_bace"), ("RAGAS support", "_ragas"),
                                                  ("BACE minus RAGAS", "_difference"), ("Binary agreement", "_agreement")]])
    selected_disagreements = pairs.loc[~pairs.bace_supported & pairs.external_supported]
    diagnoses = selected_disagreements.groupby("bace_label").size().reindex(LABELS, fill_value=0).rename("pairs").reset_index()
    diagnoses["fraction_of_selected_disagreements"] = diagnoses.pairs / len(selected_disagreements)
    per_case = pair_values.groupby(["company_id", "generation_case_id"]).agg(
        pairs=("_one", "sum"), bace=("_bace", "mean"), ragas=("_ragas", "mean"),
        difference=("_difference", "mean")).reset_index()
    literal_macro = pd.DataFrame([{"quantity": column, **boot.mean(per_case, column)}
                                 for column in ("bace", "ragas", "difference")])
    readiness = pd.DataFrame([
        ("Native paired scores and arithmetic sensitivities", "COMPUTED_VERIFIED", "Saved scores and claim counts", "Operational score differences"),
        ("Candidate-set and literal-pair diagnostics", "COMPUTED_VERIFIED", "Saved claims, selected sets and verdicts", "Information paths and selected disagreements"),
        ("Full-source / full-EC / candidate-EC loss rates", "COMPUTATION_PENDING", "Independent source-linked sufficiency labels", "Cannot be inferred from candidate counts"),
        ("Neutral proposition coverage and semantic alignment", "COMPUTATION_PENDING", "Independent passage inventory and mapping", "Literal pairs do not establish global coverage"),
        ("Temporal and inference-rule interactions", "COMPUTATION_PENDING", "Independent temporal/rule labels on shared targets", "BACE diagnosis labels cannot supply independent mechanisms"),
        ("Controlled evidence / inventory / judge conditions", "COMPUTATION_PENDING", "Explicitly defined additional evaluations", "No model calls in this notebook")],
        columns=["analysis", "status", "required_evidence", "interpretation_boundary"])
    tables = {"score_conditions": scores, "paired_effects": effects, "candidate_sets": candidates,
              "candidate_count_ecdf": frequencies, "inventory_groups": inventory,
              "literal_joint_counts": joint_rows, "literal_pooled_estimates": literal,
              "literal_case_estimates": literal_macro, "literal_disagreement_diagnoses": diagnoses,
              "analysis_readiness": readiness}
    for name, frame in tables.items():
        export_table(name, frame)
    # Verify numerical continuity with the previously saved diagnostics.
    assert np.isclose(scores.iloc[0].estimate, data["previous"]["native_macro_rates"]["bace"])
    assert np.isclose(literal.iloc[0].estimate, data["previous"]["literal_alignment"]["ragas"]["bace_pooled_support_rate"])
    return tables


def create_review_templates():
    """Header-only schemas for future independent review; never fabricate labels."""
    directory = OUT / "review_templates"
    directory.mkdir(parents=True, exist_ok=True)
    schemas = {
        "evidence_chain_review": ["review_id", "generation_case_id", "dc_id", "reviewer_id",
            "inclusion_probability", "target_fidelity", "raw_support", "pre_dedup_ec_support",
            "all_ec_support", "candidate_ec_support", "raw_source_locators", "sufficient_ec_ids",
            "lost_or_altered_premise", "uncertainty_note", "adjudication_status"],
        "proposition_alignment": ["review_id", "generation_case_id", "neutral_proposition_id",
            "generated_passage_quote", "neutral_proposition", "native_method", "native_claim_ids",
            "mapping_type", "material_qualifiers_preserved", "reviewer_id", "uncertainty_note"],
        "temporal_rule_review": ["review_id", "generation_case_id", "neutral_proposition_id",
            "reviewer_id", "requires_carry_forward", "proposition_type", "claimed_period",
            "relevant_source_period", "source_report_year", "strict_rule_support",
            "continuity_rule_support", "source_locators", "uncertainty_note"]}
    for name, fields in schemas.items():
        target = directory / f"{name}.csv"
        if not target.exists():
            pd.DataFrame(columns=fields).to_csv(target, index=False)
    text = """# Independent review schemas

These are empty schema templates, not sampled, blinded reviewer packets and
not completed annotations. Preserve any returned data in a separate directory;
notebook execution never reads these files as a human reference or overwrites
existing templates. No automatic human-agreement results are produced.

Support fields allow `Supported`, `Unsupported`, or `Unresolved`; direct and
permitted inferred support both count as Supported here. Empty means not
reviewed. Pre-dedup review is optional and must remain unfilled if not performed.
Every positive support judgment needs a source locator or sufficient premise
set. Record target-fidelity problems before attributing evidence loss.

Mapping types are `one_to_one`, `one_to_many`, `many_to_one`, `missing`, or
`incompatible`. Do not propagate a composite unsupported label to all its
constituents. Temporal fields distinguish asserted period from report year.
Define strict and continuity rules before annotation and keep uncertainty.

Sampling, reviewer blinding, calibration, adjudication and weighting require
their own documented design before these schemas become review materials.
Existing 400 primary / 200 supplementary units must not be pooled unweighted.
No model/evaluator calls are supplied by these schemas.
"""
    if not (directory / "README.md").exists():
        (directory / "README.md").write_text(text)
    return pd.DataFrame([{"template": name, "columns": len(fields), "status": "COMPUTATION_PENDING"}
                         for name, fields in schemas.items()])


def finalize_provenance():
    for name, info in INPUTS.items():
        assert sha(ROOT / name) == info["sha256"], f"Input changed during analysis: {name}"
    packages = {name: importlib.metadata.version(name) for name in
                ("numpy", "pandas", "matplotlib", "nbformat", "nbclient", "nbconvert", "ipykernel", "pymupdf")}
    save_json(OUT / "provenance.json", {
        "analysis_date": "2026-09-30", "analysis_status": "Post-experiment exploratory diagnostics",
        "inputs": INPUTS, "python": platform.python_version(), "executable": sys.executable,
        "packages": packages, "statistical_code_sha256": sha(__file__),
        "bootstrap": {"draws": DRAWS, "seed": SEED, "unit": "Company",
            "method": "95% percentile intervals of ratios of resampled company totals",
            "pairing": "All conditions retain paired records and share company resamples",
            "limits": "Conditional descriptive resampling uncertainty; not representative of all companies, model-run variability, annotation uncertainty or missing-case uncertainty"},
        "data_reuse": "Historical paper diagnostics reused as verified derived inputs and reconciled against the snapshot; no parallel rewritten calculation of their point estimates",
        "verification_scope": "Snapshot hashes and consumed original example artifacts checked; counts, scores and matched verdicts reconciled. Entire raw call histories and extraction lineage not re-audited.",
        "source_tables": {p.name: sha(p) for p in sorted((OUT / "tables").glob("*.csv"))},
        "model_calls": 0, "human_annotations_created": 0, "experiment_changes": "None"})
