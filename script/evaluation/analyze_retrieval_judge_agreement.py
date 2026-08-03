#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


CONTRIBUTION_LABELS = [
    "direct",
    "contextual",
    "no_meaningful",
]

USABILITY_LABELS = [
    "usable",
    "unusable",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare human and automated retrieval-judge labels."
        )
    )
    parser.add_argument(
        "--results",
        required=True,
        type=Path,
        help="Resolved retrieval-judge results CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Output directory. Defaults to the results CSV parent."
        ),
    )
    return parser.parse_args()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fields = list(reader.fieldnames or [])

    if not rows:
        raise ValueError("Results CSV contains no rows.")

    return rows, fields


def is_valid(value: str | None) -> bool:
    return str(value or "").strip().lower() in {
        "true",
        "1",
        "yes",
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def cohen_kappa(
    human: list[str],
    model: list[str],
    labels: list[str],
) -> float:
    n = len(human)

    observed = sum(
        human_label == model_label
        for human_label, model_label in zip(human, model)
    ) / n

    human_counts = Counter(human)
    model_counts = Counter(model)

    expected = sum(
        (human_counts[label] / n)
        * (model_counts[label] / n)
        for label in labels
    )

    if expected == 1:
        return 1.0

    return (observed - expected) / (1 - expected)


def confusion_matrix(
    human: list[str],
    model: list[str],
    labels: list[str],
) -> dict[str, dict[str, int]]:
    matrix = {
        human_label: {
            model_label: 0
            for model_label in labels
        }
        for human_label in labels
    }

    for human_label, model_label in zip(human, model):
        matrix[human_label][model_label] += 1

    return matrix


def print_matrix(
    title: str,
    matrix: dict[str, dict[str, int]],
    labels: list[str],
) -> None:
    print(f"\n{title}")
    print("Human \\ GPT".ljust(20), end="")

    for label in labels:
        print(label.rjust(18), end="")

    print()

    for human_label in labels:
        print(human_label.ljust(20), end="")

        for model_label in labels:
            print(
                str(
                    matrix[human_label][model_label]
                ).rjust(18),
                end="",
            )

        print()


def validate_labels(
    values: list[str],
    allowed_labels: list[str],
    field_name: str,
) -> None:
    invalid = sorted(
        set(values) - set(allowed_labels)
    )

    if invalid:
        raise ValueError(
            f"Invalid labels in {field_name}: {invalid}"
        )


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or args.results.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    rows, original_fields = read_csv(args.results)

    required_fields = [
        "sample_id",
        "evidence_type",
        "human_contribution_classification",
        "contribution_classification",
        "contribution_output_valid",
        "human_usability_classification",
        "usability_classification",
        "usability_output_valid",
    ]

    for field in required_fields:
        if field not in original_fields:
            raise KeyError(f"Missing required field: {field}")

    if not all(
        is_valid(row["contribution_output_valid"])
        for row in rows
    ):
        raise ValueError(
            "At least one contribution output is invalid."
        )

    if not all(
        is_valid(row["usability_output_valid"])
        for row in rows
    ):
        raise ValueError(
            "At least one usability output is invalid."
        )

    human_contribution = [
        row["human_contribution_classification"].strip()
        for row in rows
    ]
    gpt_contribution = [
        row["contribution_classification"].strip()
        for row in rows
    ]
    human_usability = [
        row["human_usability_classification"].strip()
        for row in rows
    ]
    gpt_usability = [
        row["usability_classification"].strip()
        for row in rows
    ]

    validate_labels(
        human_contribution,
        CONTRIBUTION_LABELS,
        "human_contribution_classification",
    )
    validate_labels(
        gpt_contribution,
        CONTRIBUTION_LABELS,
        "contribution_classification",
    )
    validate_labels(
        human_usability,
        USABILITY_LABELS,
        "human_usability_classification",
    )
    validate_labels(
        gpt_usability,
        USABILITY_LABELS,
        "usability_classification",
    )

    contribution_correct = sum(
        human == model
        for human, model in zip(
            human_contribution,
            gpt_contribution,
        )
    )
    usability_correct = sum(
        human == model
        for human, model in zip(
            human_usability,
            gpt_usability,
        )
    )

    n = len(rows)

    contribution_agreement = contribution_correct / n
    usability_agreement = usability_correct / n

    contribution_kappa = cohen_kappa(
        human_contribution,
        gpt_contribution,
        CONTRIBUTION_LABELS,
    )
    usability_kappa = cohen_kappa(
        human_usability,
        gpt_usability,
        USABILITY_LABELS,
    )

    contribution_matrix = confusion_matrix(
        human_contribution,
        gpt_contribution,
        CONTRIBUTION_LABELS,
    )
    usability_matrix = confusion_matrix(
        human_usability,
        gpt_usability,
        USABILITY_LABELS,
    )

    print("OVERALL AGREEMENT")
    print(
        f"Contribution: {contribution_correct}/{n} "
        f"= {contribution_agreement:.3f}"
    )
    print(
        "Contribution Cohen's kappa: "
        f"{contribution_kappa:.3f}"
    )
    print(
        f"Usability: {usability_correct}/{n} "
        f"= {usability_agreement:.3f}"
    )
    print(
        "Usability Cohen's kappa: "
        f"{usability_kappa:.3f}"
    )

    print("\nLABEL DISTRIBUTIONS")
    print(
        "Human contribution:",
        Counter(human_contribution),
    )
    print(
        "GPT contribution:",
        Counter(gpt_contribution),
    )
    print(
        "Human usability:",
        Counter(human_usability),
    )
    print(
        "GPT usability:",
        Counter(gpt_usability),
    )

    print_matrix(
        "CONTRIBUTION CONFUSION MATRIX",
        contribution_matrix,
        CONTRIBUTION_LABELS,
    )
    print_matrix(
        "USABILITY CONFUSION MATRIX",
        usability_matrix,
        USABILITY_LABELS,
    )

    by_type = defaultdict(list)

    for row in rows:
        by_type[row["evidence_type"]].append(row)

    by_type_summary = {}

    print("\nAGREEMENT BY EVIDENCE TYPE")

    for evidence_type, type_rows in sorted(by_type.items()):
        type_n = len(type_rows)

        contribution_type_correct = sum(
            row[
                "human_contribution_classification"
            ].strip()
            == row["contribution_classification"].strip()
            for row in type_rows
        )

        usability_type_correct = sum(
            row[
                "human_usability_classification"
            ].strip()
            == row["usability_classification"].strip()
            for row in type_rows
        )

        by_type_summary[evidence_type] = {
            "n": type_n,
            "contribution_correct": (
                contribution_type_correct
            ),
            "contribution_agreement": (
                contribution_type_correct / type_n
            ),
            "usability_correct": usability_type_correct,
            "usability_agreement": (
                usability_type_correct / type_n
            ),
        }

        print(
            f"{evidence_type}: n={type_n}, "
            f"contribution="
            f"{contribution_type_correct}/{type_n} "
            f"({contribution_type_correct / type_n:.3f}), "
            f"usability="
            f"{usability_type_correct}/{type_n} "
            f"({usability_type_correct / type_n:.3f})"
        )

    disagreements = []

    for row in rows:
        contribution_disagreement = (
            row[
                "human_contribution_classification"
            ].strip()
            != row["contribution_classification"].strip()
        )

        usability_disagreement = (
            row[
                "human_usability_classification"
            ].strip()
            != row["usability_classification"].strip()
        )

        if (
            contribution_disagreement
            or usability_disagreement
        ):
            output_row = dict(row)
            output_row[
                "contribution_disagreement"
            ] = str(
                contribution_disagreement
            ).lower()
            output_row[
                "usability_disagreement"
            ] = str(
                usability_disagreement
            ).lower()
            disagreements.append(output_row)

    disagreement_path = (
        output_dir
        / "retrieval_judge_disagreements.csv"
    )

    disagreement_fields = list(original_fields)

    for field in [
        "contribution_disagreement",
        "usability_disagreement",
    ]:
        if field not in disagreement_fields:
            disagreement_fields.append(field)

    with disagreement_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=disagreement_fields,
        )
        writer.writeheader()
        writer.writerows(disagreements)

    technical_retries = sum(
        row.get(
            "contribution_retry_applied",
            "",
        ).strip().lower() == "true"
        or row.get(
            "usability_retry_applied",
            "",
        ).strip().lower() == "true"
        for row in rows
    )

    summary = {
        "results_file": str(args.results),
        "results_sha256": sha256(args.results),
        "sample_size": n,
        "technical_retry_cases": technical_retries,
        "contribution": {
            "correct": contribution_correct,
            "agreement": contribution_agreement,
            "cohen_kappa": contribution_kappa,
            "human_distribution": dict(
                Counter(human_contribution)
            ),
            "gpt_distribution": dict(
                Counter(gpt_contribution)
            ),
            "confusion_matrix": contribution_matrix,
        },
        "usability": {
            "correct": usability_correct,
            "agreement": usability_agreement,
            "cohen_kappa": usability_kappa,
            "human_distribution": dict(
                Counter(human_usability)
            ),
            "gpt_distribution": dict(
                Counter(gpt_usability)
            ),
            "confusion_matrix": usability_matrix,
        },
        "agreement_by_evidence_type": by_type_summary,
        "cases_with_any_disagreement": len(
            disagreements
        ),
    }

    summary_path = (
        output_dir
        / "retrieval_judge_agreement_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print("\nDISAGREEMENTS")
    print(
        "Cases with at least one disagreement:",
        len(disagreements),
    )
    print("Disagreement file:", disagreement_path)
    print("Summary file:", summary_path)


if __name__ == "__main__":
    main()
