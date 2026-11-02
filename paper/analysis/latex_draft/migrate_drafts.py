"""One-time, non-overwriting migration of verified manuscript prose to LaTeX.

The resulting main.tex is editable. Subsequent compilation never invokes this
script or replaces author edits. This converter supports only the Markdown and
math constructs present in the two source drafts; unexpected syntax fails.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "paper/manuscript"
OUT = Path(__file__).resolve().parent
SOURCES = {"results": "paper/08_results_draft.md", "methods": "paper/10_methods_draft.md"}
TITLE = "Evidence boundaries in AI-generated corporate sustainability disclosures"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manuscript_body(path):
    text = path.read_text()
    assert text.count("<!-- MANUSCRIPT_START -->") == text.count("<!-- MANUSCRIPT_END -->") == 1
    return text.split("<!-- MANUSCRIPT_START -->")[1].split("<!-- MANUSCRIPT_END -->")[0].strip()


def inline(text):
    # Preserve already-authored math and translate citations/references before
    # escaping literal prose. Protected TeX is never escaped a second time.
    special = re.compile(r"\\\(.*?\\\)|\[@[a-z0-9_]+\]|Fig\.\s+[1-4][abc]?(?:–[abc])?", re.S)
    mapping = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "–": "--", "−": r"\ensuremath{-}"}
    result, cursor = [], 0
    for match in special.finditer(text):
        result.append("".join(mapping.get(c, c) for c in text[cursor:match.start()]))
        token = match.group()
        if token.startswith("[@"):
            result.append(r"\cite{" + token[2:-1] + "}")
        elif token.startswith("Fig."):
            number = re.search(r"([1-4])(.*)", token).groups()
            result.append(r"Fig.~\ref{fig:" + number[0] + "}" + number[1].replace("–", "--"))
        else:
            result.append(token)
        cursor = match.end()
    result.append("".join(mapping.get(c, c) for c in text[cursor:]))
    return "".join(result)


def convert(body):
    output, in_math = [], False
    for line in body.splitlines():
        if line.strip() in [r"\[", r"\]"]:
            in_math = line.strip() == r"\["
            output.append(line)
        elif in_math:
            output.append(line)
        elif re.fullmatch(r"<!-- [RM]\d\d -->", line):
            output.append("% " + line[5:8])
        elif line.startswith("### "):
            output.append(r"\subsection*{" + inline(line[4:]) + "}")
        elif line.startswith("## "):
            output.append(r"\section*{" + inline(line[3:]) + "}")
        else:
            assert not re.search(r"\*\*|`|\]\(|^\||<!--", line), line
            output.append(inline(line))
    assert not in_math
    return "\n".join(output) + "\n"


PREAMBLE = r"""% Working manuscript for Nature Sustainability (Article).
% main.tex is the editable manuscript. Migration is not run during compilation.
% Paragraph IDs preserve links to the dated Markdown evidence ledgers.
\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[margin=25mm]{geometry}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{microtype}
\usepackage[super,sort&compress,numbers]{natbib}
\usepackage[hidelinks]{hyperref}
\hypersetup{pdftitle={Evidence boundaries in AI-generated corporate sustainability disclosures},pdfauthor={}}
\graphicspath{{figures/}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.5em}
\setlength{\emergencystretch}{2em}
\linespread{1.08}
\raggedbottom

\title{Evidence boundaries in AI-generated corporate sustainability disclosures}
\author{\normalsize AUTHOR\_INPUT\_NEEDED: authors and affiliations}
\date{\small Working draft --- 1 October 2026}

\begin{document}
\maketitle
\begin{center}
\small\textbf{Draft status.} Working title; Results and Methods imported from verified drafting records.
Abstract, Introduction, Discussion, declarations and figures remain incomplete.
\end{center}

\begin{abstract}
\textbf{DRAFT\_PENDING.} Write the abstract after the main argument and validation scope are settled.
The journal limit is 150 words, without references.
\end{abstract}

% Introduction has no printed section heading under the journal's Article structure.
\textbf{DRAFT\_PENDING: Introduction.} Develop the sustainability-disclosure problem,
the verified research gap and the study question using original-source citations.

% BEGIN_RESULTS
"""

BRIDGE = r"""% END_RESULTS

\section*{Discussion}
\textbf{DRAFT\_PENDING.} Interpret the results in relation to disclosure evidence credibility,
the literature and the study's measurement boundaries. Preserve the source-extraction
counterexample, native-comparator limitations and the actual human-assessment status.

% BEGIN_METHODS
"""

END_MATTER = r"""% END_METHODS

\section*{Data availability}
\textbf{AUTHOR\_INPUT\_NEEDED.} Verify the repository, release identifier and access
conditions for the minimum supporting dataset, including third-party input restrictions.

\section*{Code availability}
\textbf{AUTHOR\_INPUT\_NEEDED.} Verify the code release, persistent identifier and
review-access route before making a deposit or availability claim.

\bibliographystyle{unsrtnat}
\bibliography{references}

\section*{Acknowledgements}
\textbf{AUTHOR\_INPUT\_NEEDED.} Confirm acknowledgements and funding information.

\section*{Author contributions}
\textbf{AUTHOR\_INPUT\_NEEDED.} Confirm the author list and actual contributions.

\section*{Competing interests}
\textbf{AUTHOR\_INPUT\_NEEDED.} Obtain and record the authors' declarations.

\section*{AI-use statement (draft)}
AI assistance was used in manuscript drafting and formatting.\par
\textbf{AUTHOR\_INPUT\_NEEDED.} Specify the tools and the authors' completed oversight
and verification, and integrate the disclosure in the appropriate manuscript location.

\clearpage
\section*{Figures (draft placeholders)}
These spaces preserve the planned figure order and cross-references.
Figure artwork and complete legends remain to be prepared from the saved analyses.
"""

FIGURES = [
    ("Study design and evidence boundaries", "Study cohort, evidence inputs and the BACE assessment workflow."),
    ("Evidentiary support across disclosure tasks", "Disclosure-score distribution, pooled claim support and task estimates."),
    ("Automated diagnoses and source-linked cases", "Diagnosis composition, the temporal example and the ASML source-extraction counterexample."),
    ("Native evaluator scores and claim inventories", "Native score distributions, paired differences and claim inventories."),
]


def main():
    PROJECT.mkdir(parents=True, exist_ok=True)
    assert not (PROJECT / "main.tex").exists(), "main.tex already exists; preserve author edits."
    assert not (PROJECT / "references.bib").exists(), "references.bib already exists; preserve edits."
    converted = {name: convert(manuscript_body(ROOT / source)) for name, source in SOURCES.items()}
    tex = PREAMBLE + converted["results"] + BRIDGE + converted["methods"] + END_MATTER
    for number, (title, description) in enumerate(FIGURES, 1):
        if number == 3:
            tex += "\n\\clearpage\n"
        tex += r"""
\begin{figure}[!htbp]
\centering
\fbox{\begin{minipage}[c][38mm][c]{0.92\linewidth}
\centering
\textbf{DRAFT\_PENDING: Figure NUMBER}\par
\medskip
DESCRIPTION
\end{minipage}}
\caption{\textbf{TITLE.} Draft placeholder; artwork and the full legend are pending.}
\label{fig:NUMBER}
\end{figure}
""".replace("NUMBER", str(number)).replace("TITLE", inline(title)).replace("DESCRIPTION", inline(description))
    tex += "\n\\clearpage\n\\end{document}\n"
    (PROJECT / "main.tex").write_text(tex)

    keys = re.findall(r"\\cite\{([^}]+)\}", tex)
    library = (ROOT / "paper/references.bib").read_text()
    entries = {re.match(r"@\w+\{([^,]+),", part).group(1): part.rstrip() for part in re.split(r"(?=^@\w+\{)", library, flags=re.M) if part.startswith("@")}
    assert set(keys) <= entries.keys()
    subset = "\n\n".join(entries[key] for key in dict.fromkeys(keys)) + "\n"
    (PROJECT / "references.bib").write_text(subset)

    paragraphs = {}
    for name, source in SOURCES.items():
        for pid, content in re.findall(r"<!-- ([RM]\d\d) -->\s*(.*?)(?=<!-- [RM]\d\d -->|\Z)", manuscript_body(ROOT / source), re.S):
            paragraphs[pid] = {"source": source, "source_body_sha256": hashlib.sha256(content.strip().encode()).hexdigest(),
                               "tex_line": next(i for i, line in enumerate(tex.splitlines(), 1) if line == "% " + pid)}
    occurrences = json.loads((ROOT / "paper/analysis/methods_draft/citation_occurrences.json").read_text())
    for occurrence in occurrences:
        occurrence["previous_document"] = occurrence["document"]
        occurrence["document"] = "paper/manuscript/main.tex"
        occurrence["location"] = "M16; migrated unchanged from Methods draft; citation key preserved"
        occurrence["migration_date"] = "2026-10-01"
    (OUT / "citation_occurrences.json").write_text(json.dumps(occurrences, ensure_ascii=False, indent=2) + "\n")
    (OUT / "migration.json").write_text(json.dumps({
        "prepared_date": "2026-10-01", "title_status": "WORKING_PROPOSAL_FROM_BLUEPRINT",
        "script_sha256": digest(Path(__file__)), "sources": {s: digest(ROOT / s) for s in SOURCES.values()},
        "bibliography_source": {"path": "paper/references.bib", "sha256": digest(ROOT / "paper/references.bib")},
        "paragraphs": paragraphs, "citation_keys": keys,
        "transformations": ["Manuscript-marker extraction only; working ledgers excluded", "Markdown headings to unnumbered LaTeX headings", "Paragraph IDs retained as comments", "TeX escaping of prose and Unicode punctuation", "Existing inline/display mathematics preserved", "Citation keys retained with numeric citation commands", "Figure numbers replaced with cross-references to explicit placeholders"],
        "main_tex_sha256": digest(PROJECT / "main.tex"), "references_bib_sha256": digest(PROJECT / "references.bib"),
        "scope": "Formatting migration and partial-manuscript scaffold; no new scientific findings or completed author declarations."
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"main_tex": str(PROJECT / "main.tex"), "migrated_paragraphs": len(paragraphs), "citations": keys, "figure_placeholders": len(FIGURES)}))


if __name__ == "__main__":
    main()
