---
name: citation-management
description: "Search and maintain BACE references, retrieve DOI metadata and format simple BibTeX while preserving citation keys and original-source verification status."
metadata:
  upstream-commit: "065b734670d7d990627dbc06a05b5a99be33f1f1"
  adaptation: "BACE Codex subset, 2026-09-29"
---

# Citation Management

This is a project-specific English adaptation of [the pinned upstream skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/065b734670d7d990627dbc06a05b5a99be33f1f1/skills/citation-management/SKILL.md).
Read [BACE writing rules](../../../paper/WRITING_RULES.md) before use and follow
[the official journal profile](../../../paper/NATURE_SUSTAINABILITY_GUIDELINES.md)
when journal requirements matter. Conversation is Chinese; saved outputs are English.
Keep the frozen experiment and analysis environments unchanged.

## Bibliography workflow

Search appropriate sources across sustainability and computing (for example
Crossref, OpenAlex, publisher sites and relevant repositories). PubMed is useful
when the subject warrants it, not a mandatory database for every BACE search.
Record queries and provenance. Verify metadata against the original publication
and distinguish online-first, issue and preprint dates. Missing page ranges may
be legitimate for article-number or online-first publications; do not fill them
with invented data. Never impose a minimum reference count or cite a skill's
authors automatically.

Retrieve DOI metadata using the bundled `scripts/doi_to_bibtex.py`; its success
means a BibTeX record was retrieved, not that the paper supports a claim. Review
returned metadata and use the citation-verification workflow before manuscript use.
The DOI helper rejects non-BibTeX responses and exits nonzero for partial batches.

Run helpers with `/home/muwang/.local/share/bace-writing-skills/venv/bin/python`
and absolute paths to this skill's scripts. Use `--help` for arguments. Pass
metadata as data, never interpolated shell code. The DOI helper makes public
metadata requests; it must not receive manuscript text or credentials.

`scripts/format_bibtex.py INPUT --no-fix` prints a proposed formatting to stdout.
Use a separate output file for review. The restricted formatter rejects macros,
parenthesized entries and unparsed content instead of silently losing them.
It is not a complete BibTeX engine. Preserve existing cite keys; inspect every
duplicate and update all citation occurrences before an intentional key change.
Do not use automatic deduplication or rekeying on an active manuscript without
checking the affected keys and metadata conflicts.

Search tools and per-field checking remain agent workflows. The upstream Google
Scholar scraper, multi-provider extraction and venue validator are not installed
in this reviewed subset. Do not invoke their paths or install their dependencies
implicitly. Their absence does not justify pretending a lookup succeeded.
