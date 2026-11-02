"""Supplement the exact-statement screen with quantitative lexical matches."""
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SNAP = ROOT / "BACE/analysis/outputs/snapshot"


def main():
    ext = collections.defaultdict(lambda: collections.defaultdict(list))
    token = lambda s: set(re.findall(r"\w+", s.casefold()))
    with (SNAP / "external_claims.csv").open() as f:
        for e in csv.DictReader(f):
            e["tokens"] = token(e["claim_text"])
            ext[e["generation_case_id"]][e["framework"]].append(e)
    candidates, count = [], 0
    with (SNAP / "claims.csv").open() as f:
        for r in csv.DictReader(f):
            if r["label"] in {"direct", "inferred", "non_disclosure_statement"} or not re.search(r"\d", r["dc_text"]):
                continue
            if not re.search(r"hours|employees|workers|suppliers|%|percent|million|tonnes|adopt", r["dc_text"], re.I):
                continue
            count += 1
            tokens, matches = token(r["dc_text"]), {}
            for framework in ["ragchecker", "ragas"]:
                sim = lambda e: len(tokens & e["tokens"]) / max(1, len(tokens | e["tokens"]))
                best = max(ext[r["generation_case_id"]][framework], key=sim)
                matches[framework] = {k: v for k, v in best.items() if k != "tokens"}
                matches[framework]["similarity"] = sim(best)
            if all(x["supported"] == "True" and x["similarity"] >= .65 for x in matches.values()):
                candidates.append(dict(r, **matches))
    candidates.sort(key=lambda r: -(r["ragchecker"]["similarity"] + r["ragas"]["similarity"]))
    result = dict(screened=count, selection="Unsupported quantitative DCs containing a digit and a units/status keyword; nearest native claims both supported with token Jaccard >=0.65. Heuristic only; manual review required.", candidates=candidates,
                  input_sha256={n: hashlib.sha256((SNAP / n).read_bytes()).hexdigest() for n in ["claims.csv", "external_claims.csv"]},
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT / "numerical_candidates.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"screened": count, "candidates": len(candidates)}))


if __name__ == "__main__":
    main()
