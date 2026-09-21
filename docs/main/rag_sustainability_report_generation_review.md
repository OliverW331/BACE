# Has RAG been used for sustainability-report generation?

## Direct answer

Yes. Published research has already used retrieval-augmented generation (RAG) to generate environmental, social, and governance (ESG) or sustainability reports. A targeted search identified at least three direct implementations:

1. EcoSmartGuide applies an LLM and RAG to ESG information access and report generation (Yang et al., 2024).
2. SusGen-GPT retrieves evidence from company annual reports and generates reports in a Task Force on Climate-related Financial Disclosures (TCFD) format (Wu et al., 2025).
3. ESGH-RAG retrieves Global Reporting Initiative (GRI) guidance and combines it with company ESG data to generate ESG reports through ChatGPT-4o (Wang et al., 2025).

The literature is recent and still small. It shows that RAG-based sustainability-report generation is feasible, but it does not remove the need for this thesis. Instead, it sharpens the research gap: existing systems do not fully evaluate whether every generated factual claim remains within the boundaries of the company evidence supplied to the model.

## Direct prior work

| Study | RAG role | Generated output | Evaluation and limitation |
|---|---|---|---|
| Yang et al. (2024), EcoSmartGuide | Supports ESG data aggregation, information access, and report generation | ESG reports | The abstract reports 95% citation accuracy and 76.23% coverage of ESG performance. The full paper was not openly accessible during this review, so the claim granularity and annotation protocol could not be verified. |
| Wu et al. (2025), SusGen-GPT | Retrieves relevant information from raw, unstructured annual reports and adds it to predefined prompts | TCFD-formatted sustainability reports | Report generation is evaluated mainly with ROUGE-L, BERTScore, METEOR, and BLEU against reference content. The authors acknowledge hallucination risk and limited expert evaluation. These metrics do not establish claim-level support by the retrieved evidence. |
| Wang et al. (2025), ESGH-RAG | Uses hybrid dense and sparse retrieval to select GRI guidance; company data comes from a Taiwan Stock Exchange ESG platform | GRI-oriented ESG report sections and complete reports | The reported 92.1% accuracy concerns guideline retrieval, not the factual accuracy of generated reports. Report quality includes a feasibility assessment for one company and feedback from five companies. The paper identifies stronger traceability and external validation as future needs. |

SusGen-GPT is the closest technical precedent for this thesis because both systems retrieve company evidence before generating a standards-oriented climate disclosure. ESGH-RAG is less directly comparable because its retrieval module primarily retrieves reporting guidelines rather than factual company evidence.

## Adjacent research that should not be classified as report generation

Several papers apply RAG or retrieval-supported LLMs to existing sustainability reports without drafting a new corporate report:

- ChatReport retrieves passages from an existing sustainability report and generates TCFD-oriented summaries, answers, and conformity analyses with page references (Ni et al., 2023).
- Bronzini et al. (2024) use RAG to extract structured ESG insights from published sustainability reports.
- Garigliotti (2024) uses a RAG pipeline for Sustainable Development Goal target evidence identification and classification in environmental reports.
- Ardic et al. (2024) use RAG to extract ESG information from Turkish sustainability reports.
- Usmanova and Usbeck (2024) use LLMs and an ontology to extract knowledge from sustainability reports and identify gaps relative to ESRS requirements, but they do not present RAG-based report generation.

These studies demonstrate that sustainability reports are already an active RAG application domain. However, their primary tasks are analysis, extraction, classification, or summarization rather than evidence-grounded drafting of new disclosures.

## Implication for the thesis contribution

The thesis should not claim to be the first study to use RAG for sustainability-report generation. That claim would be contradicted by EcoSmartGuide, SusGen-GPT, and ESGH-RAG.

The defensible contribution is narrower and more specific:

> This thesis develops and applies a claim-level, source-grounded evaluation framework for determining whether RAG-generated ESRS E1-style disclosure claims remain within the temporal, organizational, quantitative, methodological, and status boundaries of the company evidence supplied to the generator.

This contribution remains distinguishable from prior work because:

- SusGen-GPT relies primarily on reference-text similarity metrics rather than reconstructing claim-to-evidence support.
- ESGH-RAG evaluates retrieval performance and standards-oriented report quality, but not atomic factual support against minimal sufficient company-evidence sets.
- EcoSmartGuide reports citation accuracy, but the accessible evidence does not demonstrate the proposed evidence-claim graph, support-set analysis, or boundary-specific failure taxonomy.
- No directly matching study focused on RAG generation and claim-level evidence auditing for ESRS E1 was identified in the targeted search.

The final absence statement must remain qualified. This was a targeted multi-index search, not a complete systematic review of Scopus, Web of Science, and Google Scholar.

## Search scope

The search was conducted on 3 September 2026 using OpenCite, OpenAlex, Crossref, Semantic Scholar, ACL Anthology, IEEE metadata, Springer Nature, and arXiv. Queries combined RAG or retrieval-augmented generation with sustainability report, ESG report, sustainability disclosure, climate disclosure, TCFD, GRI, CSRD, and ESRS. Candidate papers were classified as direct generation, adjacent analysis or extraction, or unrelated work. Publisher metadata and full texts were checked where available.

## References

Ardic, O., Ozturk, M. U., Demirtas, I., & Arslan, S. (2024). Information extraction from sustainability reports in Turkish through RAG approach. In *2024 32nd Signal Processing and Communications Applications Conference (SIU)* (pp. 1–4). IEEE. https://doi.org/10.1109/SIU61531.2024.10600994

Bronzini, M., Nicolini, C., Lepri, B., Passerini, A., & Staiano, J. (2024). Glitter or gold? Deriving structured insights from sustainability reports via large language models. *EPJ Data Science, 13*, Article 41. https://doi.org/10.1140/epjds/s13688-024-00481-2

de Villiers, C., Dimes, R., & Molinari, M. (2024). How will AI text generation and processing impact sustainability reporting? Critical analysis, a conceptual framework and avenues for future research. *Sustainability Accounting, Management and Policy Journal, 15*(1), 96–118. https://doi.org/10.1108/SAMPJ-02-2023-0097

Garigliotti, D. (2024). SDG target detection in environmental reports using retrieval-augmented generation with LLMs. In *Proceedings of the 1st Workshop on Natural Language Processing Meets Climate Change* (pp. 241–250). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.climatenlp-1.19

Ni, J., Bingler, J., Colesanti-Senni, C., Kraus, M., Gostlow, G., Schimanski, T., Stammbach, D., Ashraf Vaghefi, S., Wang, Q., Webersinke, N., Wekhof, T., Yu, T., & Leippold, M. (2023). ChatReport: Democratizing sustainability disclosure analysis through LLM-based tools. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing: System Demonstrations* (pp. 21–51). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.emnlp-demo.3

Usmanova, A., & Usbeck, R. (2024). Structuring sustainability reports for environmental standards with LLMs guided by ontology. In *Proceedings of the 1st Workshop on Natural Language Processing Meets Climate Change* (pp. 168–177). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.climatenlp-1.13

Wang, J.-F., Zhang, W.-Y., & Tseng, S.-P. (2025). An innovative ESGH-RAG module with ChatGPT-4o for automatic ESG-report generation. *The Journal of Supercomputing, 81*, Article 1103. https://doi.org/10.1007/s11227-025-07604-0

Wu, Q., Xiang, X., Hejia, H., Wang, X., Wei Jie, Y., Satapathy, R., Filho, R. S., & Veeravalli, B. (2025). SusGen-GPT: A data-centric LLM for financial NLP and sustainability report generation. In *Findings of the Association for Computational Linguistics: NAACL 2025* (pp. 1184–1203). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.findings-naacl.66

Yang, J.-Y., Chi, R.-H., Wu, C.-C., Chen, L.-J., Lin, W.-M., Hu, H.-W., & Cheng, H.-R. (2024). EcoSmartGuide: Language Learning Model and retrieval-augmented generation-based platform for streamlined environmental, social, and governance information access and report generation. In *2024 IEEE 6th Eurasia Conference on Biomedical Engineering, Healthcare and Sustainability (ECBIOS)* (pp. 343–347). IEEE. https://doi.org/10.1109/ECBIOS61468.2024.10885500
