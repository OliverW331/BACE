#!/usr/bin/env python3
"""Run the frozen extraction update and unchanged BACE runners by case.

Each subprocess owns its output directory. Completed stages are reused, failed
stages resume their native logs, and a failed stage never feeds its successor.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "script/evaluation"


def read(path):
    return json.loads(Path(path).read_text())


def check_frozen(plan):
    for name, expected in plan["frozen_files"].items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen file changed: {name}")


def run_stage(script, arguments, output, manifest_name, log_path):
    manifest = output / manifest_name
    if manifest.exists():
        previous = read(manifest)
        if previous.get("run_status", previous.get("status")) == "complete":
            print(f"Reuse complete: {output.relative_to(ROOT)}", flush=True)
            return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        command = [sys.executable, str(SCRIPTS / script), *map(str, arguments),
                   "--output-dir", str(output)]
        if manifest.exists():
            command.append("--resume")
        print(f"Start: {output.relative_to(ROOT)} (invocation {attempt + 1})", flush=True)
        with log_path.open("a") as log:
            log.write(json.dumps({"command": command}) + "\n")
            log.flush()
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        current = read(manifest) if manifest.exists() else {}
        if current.get("run_status", current.get("status")) == "complete":
            print(f"Complete: {output.relative_to(ROOT)}", flush=True)
            return
        if result.returncode or not manifest.exists():
            raise RuntimeError(f"Runner failed; inspect {log_path}")
    raise RuntimeError(f"Stage remains incomplete; inspect {log_path}")


def extraction(plan, output):
    for stage in ("direct", "integrated", "atomic"):
        runner = "run_extraction_repair.py" if stage == "direct" else "run_staged_claim_refinement.py"
        run_stage(runner,
                  ["--plan", output / f"{stage}_plan.json", "--split", "development", "--workers", "4"],
                  output / "extraction" / stage, "claim_extraction_run_manifest.json",
                  output / "logs" / f"extraction_{stage}.log")


def downstream(case, plan, output):
    cid = case["generation_case_id"]
    short = cid.split("stratified_by_evidence_type_n10__", 1)[1]
    base = output / "bace" / short
    source = ROOT / case["extraction_directory"]
    common = ["--case-id", cid, "--run-id", f"bace_comparison_v2_{short}"]
    config_root = ROOT / "config/evaluation/configs"
    run_stage("run_generation_claim_semantic_dedup.py",
              ["--ec-occurrences", source / "ec_claim_occurrences.jsonl",
               "--dc-occurrences", source / "dc_claim_occurrences.jsonl",
               "--config", config_root / "generation_claim_semantic_dedup_config.json", *common],
              base / "dedup", "semantic_dedup_run_manifest.json",
              output / "logs" / f"{short}_dedup.log")
    claims = ["--ec-claims", base / "dedup/ec_claims.jsonl",
              "--dc-claims", base / "dedup/dc_claims.jsonl"]
    run_stage("run_generation_claim_candidate_selection.py",
              [*claims, "--config", config_root / "generation_claim_candidate_selection_config.json", *common],
              base / "candidates", "claim_candidate_run_manifest.json",
              output / "logs" / f"{short}_candidates.log")
    supporting = [*claims, "--candidate-selections", base / "candidates/dc_candidate_ecs.jsonl",
                  "--generation-cases", ROOT / plan["generation_cases"]]
    run_stage("run_generation_claim_support_assessment.py",
              [*supporting, "--config", config_root / "generation_claim_support_config.json", *common],
              base / "support", "claim_support_run_manifest.json",
              output / "logs" / f"{short}_support.log")
    run_stage("run_generation_claim_unsupported_diagnosis.py",
              [*supporting, "--support-assessments", base / "support/dc_support_sets.jsonl",
               "--config", config_root / "generation_claim_unsupported_diagnosis_config.json", *common],
              base / "diagnosis", "claim_unsupported_diagnosis_run_manifest.json",
              output / "logs" / f"{short}_diagnosis.log")
    return cid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    plan = read(args.plan)
    output = args.plan.resolve().parent
    check_frozen(plan)
    if args.check_only:
        print(f"Verified {len(plan['frozen_files'])} frozen files; no model calls.")
        return
    completed, failures = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        pending = {pool.submit(downstream, case, plan, output): case["generation_case_id"]
                   for case in plan["cases"] if case["reuse_extraction"]}
        # Four extraction workers plus three ready downstream cases initially.
        try:
            extraction(plan, output)
        except Exception as exc:
            failures.append({"stage": "extraction", "error": str(exc)})
        else:
            pending.update({pool.submit(downstream, case, plan, output): case["generation_case_id"]
                            for case in plan["cases"] if not case["reuse_extraction"]})
        for future in as_completed(pending):
            try:
                completed.append(future.result())
            except Exception as exc:
                failures.append({"case": pending[future], "error": str(exc)})
    check_frozen(plan)
    status = {"status": "complete" if len(completed) == len(plan["cases"]) and not failures else "incomplete",
              "completed_case_ids": sorted(completed), "failures": failures,
              "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    (output / "execution_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
