# Search record

Targeted discovery conducted 29 September 2026. Exact raw responses are retained. Result totals are provider-reported; returned hit sets are bounded and are not an exhaustive screened corpus. A failed request is not zero matches. Queries with Boolean-looking syntax returned broad ranked sets and are not treated as strict intersections.

| ID | Provider | Exact query | HTTP status | Returned records | Record |
|---|---|---|---|---|---|
| s01 | crossref | RAGChecker | 200 | 1 | [record](searches/s01.json) |
| s02 | crossref | RefChecker | 429 | 0 | [record](searches/s02.json) |
| s03 | crossref | Claimify | 429 | 0 | [record](searches/s03.json) |
| s04 | openalex | "sustainability" "RAG" | 200 | 20 | [record](searches/s04.json) |
| s05 | openalex | "ESG" "hallucination" | 200 | 15 | [record](searches/s05.json) |
| s06 | openalex | "sustainability reporting" "evaluation" "language" | 200 | 15 | [record](searches/s06.json) |
| s07 | crossref | ESGH-RAG | 200 | 5 | [record](searches/s07.json) |
| s08 | crossref | EcoSmartGuide | 429 | 0 | [record](searches/s08.json) |
| s09 | openalex | "claim" "decontextualization" "factuality" | 200 | 15 | [record](searches/s09.json) |
| s10 | crossref | sustainability disclosure hallucination evaluation | 429 | 0 | [record](searches/s10.json) |
| s11 | openalex | "ESRS" "faithfulness" | 200 | 15 | [record](searches/s11.json) |
| s12 | openalex | "Claimify" | 200 | 5 | [record](searches/s12.json) |
| s13 | openalex | sustainability AND ("retrieval augmented generation" OR "large language models") AND evaluation | 200 | 25 | [record](searches/s13.json) |
| s14 | openalex | ESRS AND (hallucination OR faithfulness OR entailment) | 200 | 20 | [record](searches/s14.json) |
| s15 | openalex | "RefChecker" | 200 | 5 | [record](searches/s15.json) |
| s16 | openalex | "RAGChecker" | 200 | 5 | [record](searches/s16.json) |
| s17 | openalex | "EcoSmartGuide" | 200 | 4 | [record](searches/s17.json) |
| s18 | openalex | "sustainability reporting" AND "claim" AND (factuality OR hallucination) | 200 | 20 | [record](searches/s18.json) |
| s19 | openalex | "Towards Effective Extraction and Evaluation of Factual Claims" | 200 | 5 | [record](searches/s19.json) |

Consensus attempts failed because the connector was not connected: [attempt record](consensus_attempts.json).

The initial connectivity/routing probes preceded the logged query batches and are not treated as a reproducible search corpus. The recorded NeurIPS index lookup resolved RAGChecker to the official published paper.

Selection dispositions identify the works examined for this bounded comparison. Unassessed records are not scientific exclusions. See [search hit dispositions](search_hit_dispositions.json).
