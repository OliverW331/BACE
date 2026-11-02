"""Discover candidate disagreements; lexical matching is not adjudication."""
import collections
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SNAP = ROOT / "BACE/analysis/outputs/snapshot"


def normalized(text):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def main():
    def read(name):
        with (SNAP / name).open() as f:
            return list(csv.DictReader(f))
    claims = read("claims.csv")
    external = read("external_claims.csv")
    by_case = collections.defaultdict(lambda: collections.defaultdict(list))
    exact_ragas = collections.defaultdict(list)
    for e in external:
        e["tokens"] = set(normalized(e["claim_text"]).split())
        by_case[e["generation_case_id"]][e["framework"]].append(e)
        if e["framework"] == "ragas":
            exact_ragas[(e["generation_case_id"], normalized(e["claim_text"]))].append(e)
    screened, eligible = [], []
    for c in claims:
        if c["label"] in {"direct", "inferred"}:
            continue
        exact = exact_ragas.get((c["generation_case_id"], normalized(c["dc_text"])), [])
        if c["label"] != "contradiction" and not any(e["supported"] == "True" for e in exact):
            continue
        tokens = set(normalized(c["dc_text"]).split())
        entry = dict(c, exact_supported_ragas=any(e["supported"] == "True" for e in exact))
        for framework in ["ragchecker", "ragas"]:
            def sim(e):
                return len(tokens & e["tokens"]) / max(1, len(tokens | e["tokens"]))
            best = max(by_case[c["generation_case_id"]][framework], key=sim)
            entry[framework] = {k: v for k, v in best.items() if k != "tokens"}
            entry[framework]["token_jaccard"] = sim(best)
        screened.append(entry)
        if all(entry[m]["supported"] == "True" for m in ["ragchecker", "ragas"]):
            eligible.append(entry)
    eligible.sort(key=lambda e: (-e["ragchecker"]["token_jaccard"], e["generation_case_id"], e["dc_id"]))
    (OUT / "candidate_screen.json").write_text(json.dumps(screened, ensure_ascii=False, indent=2) + "\n")
    (OUT / "both_supported_candidates.json").write_text(json.dumps(eligible, ensure_ascii=False, indent=2) + "\n")
    report = {"procedure": "Screen every BACE contradiction and other unsupported DCs having an exact normalized supported RAGAS statement; retain nearest token-overlap native claims and both positive labels. Manual equivalence and full evidence review are still required.",
              "normalization": "Unicode NFKC, casefold, word-token whitespace joining; this can erase punctuation and is only a retrieval heuristic.",
              "screened": len(screened), "both_positive_nearest_claims": len(eligible),
              "not_a_population_estimate": True,
              "input_sha256": {name: hashlib.sha256((SNAP/name).read_bytes()).hexdigest() for name in ["claims.csv", "external_claims.csv"]},
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT / "screen_provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"input_sha256", "procedure", "normalization", "script_sha256"}}, indent=2))


if __name__ == "__main__":
    main()
