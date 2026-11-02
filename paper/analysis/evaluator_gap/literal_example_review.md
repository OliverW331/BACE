# What the literal BACE–RAGAS pairs measure

Reviewed: 30 September 2026. This is an explanation of saved judgments with
five deliberately selected illustrations, not independent adjudication or a
representative audit of the matched pool.

## Pair construction and direction of support

Both methods independently extract target assertions from the same generated
disclosure. A pair is retained only when their complete target text matches
after casefolding and whitespace normalization within the same case, with a
unique match on each side. No semantic similarity threshold, shared human
label, or new evaluator run is involved. Unmatched claims remain in the
native analyses.

The 5,709 pairs are target disclosure claims. The judgment asks whether
provided evidence supports the assertion, not whether the assertion supports
another document, an evaluator, or BACE. RAGAS uses all supplied cards joined
as context; BACE's support stage uses its selected EC texts.

The saved count of supported targets is 5,364 for RAGAS and 3,384 for BACE.
Dividing each by 5,709 gives 94.0% and 59.3%. These are pooled rates within
this selected matched subset, not the disclosure-macro rates for the complete
native inventories. Of RAGAS's positive decisions, 3,354 agree with BACE and
2,010 disagree. Thirty pairs have the opposite disagreement, and 315 are
unsupported by both. These automated counts do not establish accuracy.

## Examples and the evidence invoked

### A direct numerical match

Both extracted targets say:

> KLM subsidiaries recorded 53 workplace accidents in 2017.

RAGAS's saved reason cites Evidence 8. The supplied table contains the header
`KLM Subsidiaries 2017 2018 18/17` and the row
`Total workplace accidents(2) 53 75 +41.5%`. BACE's candidate EC retains the
2017 count and BACE also returns direct support. The table separately reports
its reporting coverage; this example does not establish comprehensive coverage
of all subsidiaries or independent real-world correctness.

### A historical practice read as a current practice

Both extracted targets say:

> Air France-KLM incorporates environmental obligations into relevant product or service specifications.

RAGAS cites Evidence 10, which says that suppliers' environmental obligations
are stipulated in product or service specifications. That is a supplied
2016 annual-report passage. BACE's candidate EC retains that attribution,
and its later diagnosis challenges extension to the 2019 reporting year.

RAGAS's reason identifies a substantive textual anchor. BACE's diagnosis
identifies a temporal qualification. Whether the unqualified present-tense
generated passage can use the historical policy as its basis requires an
explicit continuity rule and source review. This illustration does not prove
which binary judgment is correct or establish the frequency of this mechanism.

### A visible source mention absent from the candidate set

Both extracted targets say:

> Social reporting covers HOP!.

RAGAS says the social reporting scope explicitly includes HOP!. Supplied
Evidence 1, from the 2018 annual report, contains the footnote:

> Social: Air France in France, HOP!, KLM in the Netherlands and KLM Catering Services.

BACE's candidate set is empty. Its unsupported result is deterministic in
that condition, and its later novelty diagnosis states that no evidence
establishes the assertion. The diagnosis describes the supplied candidate
inputs, not an exhaustive inspection of the original cards.

This demonstrates an information-path difference. It does not establish that
the complete generated claim is supported for 2019: the footnote's scope in
the source passage and its historical applicability still need review. The
mere presence of the entity name does not resolve those questions.

### A new training channel read as expanded access

Both extracted targets say:

> Air France broadened access to training through Manager Cafés.

RAGAS's reason says Manager Cafes are listed among new training-access methods.
Evidence 4 states that new conditions for access to training were developed,
listing self-service modules, online courses, Manager Cafes and dedicated
days. BACE's candidate ECs preserve the development of new access conditions
and Manager Cafes. Its subsequent diagnosis distinguishes those facts from
an established broadening of access.

The disputed step is whether adding this channel warrants the characterization
"broadened access". This is an interpretation/support-policy issue in the
inspected record, not an absent candidate anchor. Independent review should
retain the complete paragraph, which discusses training in 2018.

### A prospective plan read as actual management

Both extracted targets say:

> Air France-KLM manages fleet capital expenditure under strict capital discipline.

RAGAS cites a statement that an increase in fleet expenditure would be
undertaken under strict expenditure discipline. BACE's candidate ECs preserve
the 2015 source attribution and future plan wording. Its subsequent diagnosis
questions whether this establishes actual management in the 2019 reporting
context. This example involves both temporal extension and prospective versus
actual status; it should not be reduced to a generic matching failure.

## What remains unresolved

These examples show what particular RAGAS positive decisions refer to: direct
measurements, historical policies, reporting scope and descriptions of actions.
They do not explain how often each mechanism produces the overall high rate.
The matched pool is selected and includes both agreements and disagreements.
BACE's later diagnosis is not an independently verified explanation of its
earlier support decision. The two methods' evidence inputs also remain
different despite identical target wording.

All five examples were selected from the first company in the sorted matched
file to make the explanation concrete. They were not selected by a probability
sample and should not be used for mechanism prevalence or comparative accuracy.

Exact target records, native RAGAS reasons, generated disclosures, full supplied
cards, full ECs, selected ECs and source hashes are saved in
[literal_examples.json](literal_examples.json), generated by
[inspect_literal_examples.py](inspect_literal_examples.py). Its raw case
inputs match the prior snapshot source ledger. The matched-pair file matches
the preceding calculation's output hash. No model calls were made.
