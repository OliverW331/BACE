# Complete saved EC and DC extraction examples

Access date: 2026-10-26. Run: `main_v1`.

Generation case: `w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets`.

These are literal saved model outputs from the active direct-v8, integrated-v4 and atomicity-v2 pipeline. No model call or experiment was run. EC covers one complete supplied evidence record; DC covers the complete generated disclosure. All stages are before semantic deduplication. Stage-local list numbers are display positions, not immutable claim IDs.

The generated disclosure and extracted claims can be unsupported or mistaken. Values inside them are reproduced source assertions, not independently verified company measurements. Successful schema validation and patch replay do not establish semantic correctness. The supplied EC excerpt was checked locally; the original publisher PDF was not independently audited for this example.

## Stage counts

| Unit | Direct claims | Integrated claims | Atomic claims | Final exclusions |
| --- | ---: | ---: | ---: | ---: |
| EC | 6 | 6 | 7 | 0 |
| DC | 36 | 37 | 40 | 1 |

Counts are computed from the exact inventories in `examples.json`; no deduplication is applied. DC may retain repeated underlying assertions produced by relationship-preserving splits.

## Reading guide

- EC: Integrated review changes an inferred possession-of-target claim into a source-faithful prospective outcome and records unresolved governing language. Atomicity review then separates approval from confirmation of temperature-pathway alignment.
- DC: Integrated review expands the identity of the principal target in dependent claims. Atomicity review separates an absolute reduction assertion, the classification of an intensity target, and the explicit distinction between those metrics, preserving the relationship rather than replacing it with only two facts.
- This is a 2023 task with a selected EC record attributed to a 2022 annual report. The extraction retains the 2022 report attribution; the task year does not create a 2023 measurement or action date.
- The final EC wording is retained exactly, including generic references to submitted targets and the absence of an explicit November 2022 date in the confirmation child. This reproduction is not a certification that every output satisfies every prompt rule.

## EC example

### Supplied source

Record: `Evidence 6`. Source: `28367af8-ef59-4ce7-a851-2c0535aea0ce_2022_AR.pdf | Page 243`.

The source display below removes the PDF bullet control character U+0007 only. The raw input is preserved unchanged in `examples.json`.

> achieve Net Zero emissions by 2050 for the Air France – KLM Group. The Air France – KLM Group, Air France and KLM submitted their CO₂ emissions reduction targets to the SBTi which have been approved in November 2022 by the SBTi’s Target Validation Team confirming that they are in line with a well-below 2°C objective, as determined by the Paris Agreement signed in 2015.

### Direct extraction result

Prompt: `generation_ec_claim_extraction_prompt_v8`.

Complete resulting inventory (claim text unchanged):

1. According to the 2022 report, the Air France-KLM Group has a target to achieve net zero emissions by 2050.
2. According to the 2022 report, the Air France-KLM Group submitted its CO2 emissions reduction targets to the SBTi.
3. According to the 2022 report, Air France submitted its CO2 emissions reduction targets to the SBTi.
4. According to the 2022 report, KLM submitted its CO2 emissions reduction targets to the SBTi.
5. According to the 2022 report, the SBTi Target Validation Team approved in November 2022 the CO2 emissions reduction targets submitted by the Air France-KLM Group, Air France and KLM, confirming that they were in line with a well-below 2°C objective as determined by the Paris Agreement.
6. According to the 2022 report, the Paris Agreement was signed in 2015.

Exclusions:

- None.

### Integrated extraction result

Prompt: `generation_ec_claim_patch_review_prompt_v4`.

Applied patch (verbatim parsed JSON):

```json
{
  "prompt_label": "Evidence 6",
  "edits": [
    {
      "claims": [
        {
          "claim_text": "According to the 2022 report, Net Zero emissions are to be achieved by 2050 for the Air France-KLM Group.",
          "source_quotes": [
            "achieve Net Zero emissions by 2050 for the Air France – KLM Group."
          ],
          "unresolved_context": [
            "The supplied text is an infinitive fragment and does not include the governing language that would clarify the precise status or actor of this objective."
          ]
        }
      ],
      "reason": "The draft inferred that the Group possesses a target, although the supplied fragment only states the intended Net Zero outcome and deadline for the Group.",
      "replaces": [
        {
          "claim_id": "claim_23136cf7c6db3a9c",
          "expected_claim_text": "According to the 2022 report, the Air France-KLM Group has a target to achieve net zero emissions by 2050."
        }
      ]
    }
  ],
  "additions": [],
  "exclusion_update": null
}
```

Complete resulting inventory (claim text unchanged):

1. According to the 2022 report, Net Zero emissions are to be achieved by 2050 for the Air France-KLM Group.
   - Unresolved context: The supplied text is an infinitive fragment and does not include the governing language that would clarify the precise status or actor of this objective.
2. According to the 2022 report, the Air France-KLM Group submitted its CO2 emissions reduction targets to the SBTi.
3. According to the 2022 report, Air France submitted its CO2 emissions reduction targets to the SBTi.
4. According to the 2022 report, KLM submitted its CO2 emissions reduction targets to the SBTi.
5. According to the 2022 report, the SBTi Target Validation Team approved in November 2022 the CO2 emissions reduction targets submitted by the Air France-KLM Group, Air France and KLM, confirming that they were in line with a well-below 2°C objective as determined by the Paris Agreement.
6. According to the 2022 report, the Paris Agreement was signed in 2015.

Exclusions:

- None.

### Atomic extraction result

Prompt: `generation_ec_claim_atomicity_review_prompt_v2`.

Applied patch (verbatim parsed JSON):

```json
{
  "prompt_label": "Evidence 6",
  "edits": [
    {
      "claims": [
        {
          "claim_text": "According to the 2022 report, the SBTi Target Validation Team approved in November 2022 the CO2 emissions reduction targets submitted by the Air France-KLM Group, Air France and KLM.",
          "source_quotes": [
            "The Air France – KLM Group, Air France and KLM submitted their CO₂ emissions reduction targets to the SBTi which have been approved in November 2022 by the SBTi’s Target Validation Team"
          ],
          "unresolved_context": []
        },
        {
          "claim_text": "According to the 2022 report, the SBTi Target Validation Team confirmed that the CO2 emissions reduction targets submitted by the Air France-KLM Group, Air France and KLM were in line with a well-below 2°C objective as determined by the Paris Agreement.",
          "source_quotes": [
            "The Air France – KLM Group, Air France and KLM submitted their CO₂ emissions reduction targets to the SBTi which have been approved in November 2022 by the SBTi’s Target Validation Team confirming that they are in line with a well-below 2°C objective, as determined by the Paris Agreement signed in 2015."
          ],
          "unresolved_context": []
        }
      ],
      "reason": "The parent combines the Target Validation Team's approval of the submitted targets with its confirmation that those targets align with the stated temperature objective.",
      "replaces": [
        {
          "claim_id": "claim_e0b19ce8e8fc8fbb",
          "expected_claim_text": "According to the 2022 report, the SBTi Target Validation Team approved in November 2022 the CO2 emissions reduction targets submitted by the Air France-KLM Group, Air France and KLM, confirming that they were in line with a well-below 2°C objective as determined by the Paris Agreement."
        }
      ]
    }
  ],
  "additions": [],
  "exclusion_update": null
}
```

Complete resulting inventory (claim text unchanged):

1. According to the 2022 report, Net Zero emissions are to be achieved by 2050 for the Air France-KLM Group.
   - Unresolved context: The supplied text is an infinitive fragment and does not include the governing language that would clarify the precise status or actor of this objective.
2. According to the 2022 report, the Air France-KLM Group submitted its CO2 emissions reduction targets to the SBTi.
3. According to the 2022 report, Air France submitted its CO2 emissions reduction targets to the SBTi.
4. According to the 2022 report, KLM submitted its CO2 emissions reduction targets to the SBTi.
5. According to the 2022 report, the SBTi Target Validation Team approved in November 2022 the CO2 emissions reduction targets submitted by the Air France-KLM Group, Air France and KLM.
6. According to the 2022 report, the SBTi Target Validation Team confirmed that the CO2 emissions reduction targets submitted by the Air France-KLM Group, Air France and KLM were in line with a well-below 2°C objective as determined by the Paris Agreement.
7. According to the 2022 report, the Paris Agreement was signed in 2015.

Exclusions:

- None.

## DC example

### Supplied source

### E1-4 – Climate-related targets

Air France–KLM has established climate targets to support the management of its climate-related impacts, risks and opportunities. The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year. The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.

The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM. The Group, Air France and KLM submitted their emissions-reduction targets to the Science Based Targets initiative (SBTi). In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement. This external validation provides the principal scientific reference for the target’s level of ambition and methodology.

In addition to its 2030 target, Air France–KLM has set an objective of achieving net-zero emissions by 2050. The Group had also committed to establishing additional CO₂-reduction targets for 2035. No quantified 2035 target is included in the information reported here.

For 2023, the Group reported E1-4 scope-related target indicators of 10% for Scope 1 greenhouse gas emissions and 20% for Scope 3 greenhouse gas emissions, measured with reference to base-year emissions. The reported absolute value of total greenhouse gas emissions reduction was 800,000 tonnes of CO₂ equivalent. This absolute reduction metric is distinct from the Group’s principal SBTi-validated target, which is an emissions-intensity target based on well-to-wake jet-fuel emissions per RTK.

The boundary and methodology applied to climate metrics should be considered when interpreting performance. In particular, the scope of CO₂-equivalent emissions reported in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances. Consequently, comparisons between those reporting bases are not meaningful. Progress against the 2030 target should therefore be assessed using the defined 2019 baseline, the well-to-wake Scope 1 and Scope 3 jet-fuel boundary, and the RTK intensity denominator.

### Direct extraction result

Prompt: `generation_dc_claim_extraction_prompt_v8`.

Complete resulting inventory (claim text unchanged):

1. Air France–KLM has established climate targets.
2. Air France–KLM's climate targets are intended to support the management of its climate-related impacts.
3. Air France–KLM's climate targets are intended to support the management of its climate-related risks.
4. Air France–KLM's climate targets are intended to support the management of its climate-related opportunities.
5. Air France–KLM Group's principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
6. The Scope 1 component is covered by Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
7. The Scope 3 component is covered by Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
8. Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is expressed in grams of CO₂ equivalent per revenue tonne-kilometre.
9. Air France–KLM Group's principal medium-term target measures emissions intensity relative to transport activity.
10. Air France–KLM Group's principal medium-term target applies to the Air France–KLM Group.
11. Air France–KLM Group's principal medium-term target is supported by a corresponding target for Air France.
12. Air France–KLM Group's principal medium-term target is supported by a corresponding target for KLM.
13. Air France–KLM Group submitted its emissions-reduction target to the Science Based Targets initiative.
14. Air France submitted its emissions-reduction target to the Science Based Targets initiative.
15. KLM submitted its emissions-reduction target to the Science Based Targets initiative.
16. In November 2022, the Science Based Targets initiative Target Validation Team approved Air France–KLM Group's emissions-reduction target.
17. In November 2022, the Science Based Targets initiative Target Validation Team approved Air France's emissions-reduction target.
18. In November 2022, the Science Based Targets initiative Target Validation Team approved KLM's emissions-reduction target.
19. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France–KLM Group's emissions-reduction target is aligned with a well-below 2°C pathway under the Paris Agreement.
20. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France's emissions-reduction target is aligned with a well-below 2°C pathway under the Paris Agreement.
21. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that KLM's emissions-reduction target is aligned with a well-below 2°C pathway under the Paris Agreement.
22. The external validation by the Science Based Targets initiative provides the principal scientific reference for the level of ambition of Air France–KLM Group's principal medium-term emissions-reduction target.
23. The external validation by the Science Based Targets initiative provides the principal scientific reference for the methodology of Air France–KLM Group's principal medium-term emissions-reduction target.
24. In addition to its 2030 target, Air France–KLM has set an objective of achieving net-zero emissions by 2050.
25. Air France–KLM Group had committed to establishing additional CO₂-reduction targets for 2035.
26. No quantified Air France–KLM Group target for 2035 is included in the information reported in the disclosure.
27. For 2023, Air France–KLM Group reported an E1-4 scope-related target indicator of 10% for Scope 1 greenhouse gas emissions, measured with reference to emissions from an unspecified base year.
   - Unresolved context: The base year for the 2023 Scope 1 target indicator is not specified.
28. For 2023, Air France–KLM Group reported an E1-4 scope-related target indicator of 20% for Scope 3 greenhouse gas emissions, measured with reference to emissions from an unspecified base year.
   - Unresolved context: The base year for the 2023 Scope 3 target indicator is not specified.
29. For 2023, Air France–KLM Group reported an absolute total greenhouse gas emissions reduction of 800,000 tonnes of CO₂ equivalent.
30. Air France–KLM Group's reported absolute total greenhouse gas emissions reduction metric of 800,000 tonnes of CO₂ equivalent for 2023 is distinct from its principal Science Based Targets initiative-validated target, which is an emissions-intensity target based on well-to-wake jet-fuel emissions per revenue tonne-kilometre.
31. The boundary applied to Air France–KLM's climate metrics should be considered when interpreting performance.
32. The methodology applied to Air France–KLM's climate metrics should be considered when interpreting performance.
33. The scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances, and consequently comparisons between those reporting bases are not meaningful.
34. Progress against Air France–KLM Group's 2030 target should therefore be assessed using the defined 2019 baseline.
35. Progress against Air France–KLM Group's 2030 target should therefore be assessed using the well-to-wake Scope 1 and Scope 3 jet-fuel boundary.
36. Progress against Air France–KLM Group's 2030 target should therefore be assessed using the revenue tonne-kilometre intensity denominator.

Exclusions:

- `document_structure`: This is a section heading rather than a substantive proposition.
  - Source span: ### E1-4 – Climate-related targets

### Integrated extraction result

Prompt: `generation_dc_claim_patch_review_prompt_v4`.

Applied patch (verbatim parsed JSON):

```json
{
  "edits": [
    {
      "claims": [
        {
          "claim_text": "Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year measures emissions intensity relative to transport activity.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The target reference must retain its full material identity, including scope, magnitude, baseline and deadline.",
      "replaces": [
        {
          "claim_id": "claim_9f79c446b8c252d1",
          "expected_claim_text": "Air France–KLM Group's principal medium-term target measures emissions intensity relative to transport activity."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year applies to the Air France–KLM Group.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The applicable target must be fully identified.",
      "replaces": [
        {
          "claim_id": "claim_078ddb5e991120c0",
          "expected_claim_text": "Air France–KLM Group's principal medium-term target applies to the Air France–KLM Group."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Air France has a corresponding target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The corresponding Air France target must identify the fully specified Group target it supports.",
      "replaces": [
        {
          "claim_id": "claim_461a23236ffaca72",
          "expected_claim_text": "Air France–KLM Group's principal medium-term target is supported by a corresponding target for Air France."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "KLM has a corresponding target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The corresponding KLM target must identify the fully specified Group target it supports.",
      "replaces": [
        {
          "claim_id": "claim_b42e27df5afac841",
          "expected_claim_text": "Air France–KLM Group's principal medium-term target is supported by a corresponding target for KLM."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Air France–KLM Group submitted to the Science Based Targets initiative its principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "The Group, Air France and KLM submitted their emissions-reduction targets to the Science Based Targets initiative (SBTi)."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The submitted Group target must retain its complete identity.",
      "replaces": [
        {
          "claim_id": "claim_4e5206e1287b1717",
          "expected_claim_text": "Air France–KLM Group submitted its emissions-reduction target to the Science Based Targets initiative."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Air France submitted to the Science Based Targets initiative its corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM.",
            "The Group, Air France and KLM submitted their emissions-reduction targets to the Science Based Targets initiative (SBTi)."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The submitted Air France target must be tied to the fully identified target to which it corresponds.",
      "replaces": [
        {
          "claim_id": "claim_348a1cf7b667771b",
          "expected_claim_text": "Air France submitted its emissions-reduction target to the Science Based Targets initiative."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "KLM submitted to the Science Based Targets initiative its corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM.",
            "The Group, Air France and KLM submitted their emissions-reduction targets to the Science Based Targets initiative (SBTi)."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The submitted KLM target must be tied to the fully identified target to which it corresponds.",
      "replaces": [
        {
          "claim_id": "claim_591b08ff545e7ba2",
          "expected_claim_text": "KLM submitted its emissions-reduction target to the Science Based Targets initiative."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team approved Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The Group, Air France and KLM submitted their emissions-reduction targets to the Science Based Targets initiative (SBTi).",
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The approved Group target must retain its complete identity.",
      "replaces": [
        {
          "claim_id": "claim_5f5154b4e27494b5",
          "expected_claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team approved Air France–KLM Group's emissions-reduction target."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team approved Air France's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM.",
            "The Group, Air France and KLM submitted their emissions-reduction targets to the Science Based Targets initiative (SBTi).",
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The approved Air France target must be tied to the fully identified target to which it corresponds.",
      "replaces": [
        {
          "claim_id": "claim_3d6d49cfa65d95e0",
          "expected_claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team approved Air France's emissions-reduction target."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team approved KLM's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM.",
            "The Group, Air France and KLM submitted their emissions-reduction targets to the Science Based Targets initiative (SBTi).",
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The approved KLM target must be tied to the fully identified target to which it corresponds.",
      "replaces": [
        {
          "claim_id": "claim_094ba151d2638988",
          "expected_claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team approved KLM's emissions-reduction target."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The alignment confirmation must identify the complete Group target.",
      "replaces": [
        {
          "claim_id": "claim_0eb7639535c88241",
          "expected_claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France–KLM Group's emissions-reduction target is aligned with a well-below 2°C pathway under the Paris Agreement."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.",
          "source_quotes": [
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM.",
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The alignment confirmation must identify the Air France target through its stated correspondence to the complete Group target.",
      "replaces": [
        {
          "claim_id": "claim_9667e07a9ef05151",
          "expected_claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France's emissions-reduction target is aligned with a well-below 2°C pathway under the Paris Agreement."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team confirmed that KLM's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.",
          "source_quotes": [
            "The target applies to the Air France–KLM Group and is supported by corresponding targets for Air France and KLM.",
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The alignment confirmation must identify the KLM target through its stated correspondence to the complete Group target.",
      "replaces": [
        {
          "claim_id": "claim_51edc6ecb4ae676a",
          "expected_claim_text": "In November 2022, the Science Based Targets initiative Target Validation Team confirmed that KLM's emissions-reduction target is aligned with a well-below 2°C pathway under the Paris Agreement."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "The external validation by the Science Based Targets initiative provides the principal scientific reference for the level of ambition of Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement.",
            "This external validation provides the principal scientific reference for the target’s level of ambition and methodology."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The target whose ambition is referenced must retain its complete identity.",
      "replaces": [
        {
          "claim_id": "claim_b2ba12defade98e2",
          "expected_claim_text": "The external validation by the Science Based Targets initiative provides the principal scientific reference for the level of ambition of Air France–KLM Group's principal medium-term emissions-reduction target."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "The external validation by the Science Based Targets initiative provides the principal scientific reference for the methodology of Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "In November 2022, the SBTi Target Validation Team approved these targets and confirmed that they are aligned with a well-below 2°C pathway under the Paris Agreement.",
            "This external validation provides the principal scientific reference for the target’s level of ambition and methodology."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The target whose methodology is referenced must retain its complete identity.",
      "replaces": [
        {
          "claim_id": "claim_ddd1f49d478e382c",
          "expected_claim_text": "The external validation by the Science Based Targets initiative provides the principal scientific reference for the methodology of Air France–KLM Group's principal medium-term emissions-reduction target."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "In addition to its principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year, Air France–KLM has set an objective of achieving net-zero emissions by 2050.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "In addition to its 2030 target, Air France–KLM has set an objective of achieving net-zero emissions by 2050."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The referenced 2030 target must be fully resolved while preserving its relation to the additional 2050 objective.",
      "replaces": [
        {
          "claim_id": "claim_0770b2652b7fc01f",
          "expected_claim_text": "In addition to its 2030 target, Air France–KLM has set an objective of achieving net-zero emissions by 2050."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Air France–KLM Group's reported absolute total greenhouse gas emissions reduction metric of 800,000 tonnes of CO₂ equivalent for 2023 is distinct from its Science Based Targets initiative-validated principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year, which is an emissions-intensity target.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "The reported absolute value of total greenhouse gas emissions reduction was 800,000 tonnes of CO₂ equivalent.",
            "This absolute reduction metric is distinct from the Group’s principal SBTi-validated target, which is an emissions-intensity target based on well-to-wake jet-fuel emissions per RTK."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The comparison must preserve the complete identity of the SBTi-validated target.",
      "replaces": [
        {
          "claim_id": "claim_9503073164a77c0f",
          "expected_claim_text": "Air France–KLM Group's reported absolute total greenhouse gas emissions reduction metric of 800,000 tonnes of CO₂ equivalent for 2023 is distinct from its principal Science Based Targets initiative-validated target, which is an emissions-intensity target based on well-to-wake jet-fuel emissions per revenue tonne-kilometre."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "The scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances.",
          "source_quotes": [
            "In particular, the scope of CO₂-equivalent emissions reported in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        },
        {
          "claim_text": "Because the scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances, comparisons between those reporting bases are not meaningful.",
          "source_quotes": [
            "In particular, the scope of CO₂-equivalent emissions reported in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances.",
            "Consequently, comparisons between those reporting bases are not meaningful."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The source separately asserts the scope difference and its consequence; the underlying fact and causal relationship should both be retained atomically.",
      "replaces": [
        {
          "claim_id": "claim_d69af9434e0fcaaa",
          "expected_claim_text": "The scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances, and consequently comparisons between those reporting bases are not meaningful."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the defined 2019 baseline.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "Progress against the 2030 target should therefore be assessed using the defined 2019 baseline, the well-to-wake Scope 1 and Scope 3 jet-fuel boundary, and the RTK intensity denominator."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The progress-assessment claim must fully identify the 2030 target.",
      "replaces": [
        {
          "claim_id": "claim_5d76044a83b49595",
          "expected_claim_text": "Progress against Air France–KLM Group's 2030 target should therefore be assessed using the defined 2019 baseline."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the well-to-wake Scope 1 and Scope 3 jet-fuel boundary.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "Progress against the 2030 target should therefore be assessed using the defined 2019 baseline, the well-to-wake Scope 1 and Scope 3 jet-fuel boundary, and the RTK intensity denominator."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The progress-assessment claim must fully identify the 2030 target.",
      "replaces": [
        {
          "claim_id": "claim_d4cf4e5b023fce02",
          "expected_claim_text": "Progress against Air France–KLM Group's 2030 target should therefore be assessed using the well-to-wake Scope 1 and Scope 3 jet-fuel boundary."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the revenue tonne-kilometre intensity denominator.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "Progress against the 2030 target should therefore be assessed using the defined 2019 baseline, the well-to-wake Scope 1 and Scope 3 jet-fuel boundary, and the RTK intensity denominator."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The progress-assessment claim must fully identify the 2030 target.",
      "replaces": [
        {
          "claim_id": "claim_0d448945e982a272",
          "expected_claim_text": "Progress against Air France–KLM Group's 2030 target should therefore be assessed using the revenue tonne-kilometre intensity denominator."
        }
      ]
    }
  ],
  "additions": [],
  "no_claim_reason": null,
  "exclusion_update": null
}
```

Complete resulting inventory (claim text unchanged):

1. Air France–KLM has established climate targets.
2. Air France–KLM's climate targets are intended to support the management of its climate-related impacts.
3. Air France–KLM's climate targets are intended to support the management of its climate-related risks.
4. Air France–KLM's climate targets are intended to support the management of its climate-related opportunities.
5. Air France–KLM Group's principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
6. The Scope 1 component is covered by Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
7. The Scope 3 component is covered by Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
8. Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is expressed in grams of CO₂ equivalent per revenue tonne-kilometre.
9. Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year measures emissions intensity relative to transport activity.
10. Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year applies to the Air France–KLM Group.
11. Air France has a corresponding target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
12. KLM has a corresponding target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
13. Air France–KLM Group submitted to the Science Based Targets initiative its principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
14. Air France submitted to the Science Based Targets initiative its corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
15. KLM submitted to the Science Based Targets initiative its corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
16. In November 2022, the Science Based Targets initiative Target Validation Team approved Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
17. In November 2022, the Science Based Targets initiative Target Validation Team approved Air France's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
18. In November 2022, the Science Based Targets initiative Target Validation Team approved KLM's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
19. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.
20. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.
21. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that KLM's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.
22. The external validation by the Science Based Targets initiative provides the principal scientific reference for the level of ambition of Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
23. The external validation by the Science Based Targets initiative provides the principal scientific reference for the methodology of Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
24. In addition to its principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year, Air France–KLM has set an objective of achieving net-zero emissions by 2050.
25. Air France–KLM Group had committed to establishing additional CO₂-reduction targets for 2035.
26. No quantified Air France–KLM Group target for 2035 is included in the information reported in the disclosure.
27. For 2023, Air France–KLM Group reported an E1-4 scope-related target indicator of 10% for Scope 1 greenhouse gas emissions, measured with reference to emissions from an unspecified base year.
   - Unresolved context: The base year for the 2023 Scope 1 target indicator is not specified.
28. For 2023, Air France–KLM Group reported an E1-4 scope-related target indicator of 20% for Scope 3 greenhouse gas emissions, measured with reference to emissions from an unspecified base year.
   - Unresolved context: The base year for the 2023 Scope 3 target indicator is not specified.
29. For 2023, Air France–KLM Group reported an absolute total greenhouse gas emissions reduction of 800,000 tonnes of CO₂ equivalent.
30. Air France–KLM Group's reported absolute total greenhouse gas emissions reduction metric of 800,000 tonnes of CO₂ equivalent for 2023 is distinct from its Science Based Targets initiative-validated principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year, which is an emissions-intensity target.
31. The boundary applied to Air France–KLM's climate metrics should be considered when interpreting performance.
32. The methodology applied to Air France–KLM's climate metrics should be considered when interpreting performance.
33. The scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances.
34. Because the scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances, comparisons between those reporting bases are not meaningful.
35. Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the defined 2019 baseline.
36. Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the well-to-wake Scope 1 and Scope 3 jet-fuel boundary.
37. Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the revenue tonne-kilometre intensity denominator.

Exclusions:

- `document_structure`: This is a section heading rather than a substantive proposition.
  - Source span: ### E1-4 – Climate-related targets

### Atomic extraction result

Prompt: `generation_dc_claim_atomicity_review_prompt_v2`.

Applied patch (verbatim parsed JSON):

```json
{
  "edits": [
    {
      "claims": [
        {
          "claim_text": "For 2023, Air France–KLM Group reported an absolute total greenhouse gas emissions reduction of 800,000 tonnes of CO₂ equivalent.",
          "source_quotes": [
            "The reported absolute value of total greenhouse gas emissions reduction was 800,000 tonnes of CO₂ equivalent."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        },
        {
          "claim_text": "Air France–KLM Group's Science Based Targets initiative-validated principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is an emissions-intensity target based on well-to-wake jet-fuel emissions per revenue tonne-kilometre.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "This absolute reduction metric is distinct from the Group’s principal SBTi-validated target, which is an emissions-intensity target based on well-to-wake jet-fuel emissions per RTK."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        },
        {
          "claim_text": "Air France–KLM Group's reported absolute total greenhouse gas emissions reduction metric of 800,000 tonnes of CO₂ equivalent for 2023 is distinct from its Science Based Targets initiative-validated principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.",
          "source_quotes": [
            "The Group’s principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre (RTK) by 2030, compared with a 2019 base year.",
            "The target covers Scope 1 and Scope 3 jet-fuel emissions and is expressed in grams of CO₂ equivalent per RTK, thereby measuring emissions intensity relative to transport activity.",
            "The reported absolute value of total greenhouse gas emissions reduction was 800,000 tonnes of CO₂ equivalent.",
            "This absolute reduction metric is distinct from the Group’s principal SBTi-validated target, which is an emissions-intensity target based on well-to-wake jet-fuel emissions per RTK."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The parent combines the explicitly reported absolute reduction, the classification of the SBTi-validated target as an emissions-intensity target, and the asserted distinction between the two metrics. The split preserves both underlying facts and their relationship.",
      "replaces": [
        {
          "claim_id": "claim_6500c79a141db3e8",
          "expected_claim_text": "Air France–KLM Group's reported absolute total greenhouse gas emissions reduction metric of 800,000 tonnes of CO₂ equivalent for 2023 is distinct from its Science Based Targets initiative-validated principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year, which is an emissions-intensity target."
        }
      ]
    },
    {
      "claims": [
        {
          "claim_text": "The scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances.",
          "source_quotes": [
            "In particular, the scope of CO₂-equivalent emissions reported in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        },
        {
          "claim_text": "Because the scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances, comparisons between those reporting bases are not meaningful.",
          "source_quotes": [
            "In particular, the scope of CO₂-equivalent emissions reported in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances.",
            "Consequently, comparisons between those reporting bases are not meaningful."
          ],
          "context_resolutions": [],
          "unresolved_context": []
        }
      ],
      "reason": "The parent contains both an explicitly asserted difference between reporting scopes and the causal conclusion that comparisons between those bases are not meaningful. The split retains the underlying fact and the full causal relationship.",
      "replaces": [
        {
          "claim_id": "claim_2e6cb069ffc288d4",
          "expected_claim_text": "Because the scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances, comparisons between those reporting bases are not meaningful."
        }
      ]
    }
  ],
  "additions": [],
  "no_claim_reason": null,
  "exclusion_update": null
}
```

Complete resulting inventory (claim text unchanged):

1. Air France–KLM has established climate targets.
2. Air France–KLM's climate targets are intended to support the management of its climate-related impacts.
3. Air France–KLM's climate targets are intended to support the management of its climate-related risks.
4. Air France–KLM's climate targets are intended to support the management of its climate-related opportunities.
5. Air France–KLM Group's principal medium-term target is to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
6. The Scope 1 component is covered by Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
7. The Scope 3 component is covered by Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
8. Air France–KLM Group's principal medium-term target to reduce well-to-wake greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is expressed in grams of CO₂ equivalent per revenue tonne-kilometre.
9. Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year measures emissions intensity relative to transport activity.
10. Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year applies to the Air France–KLM Group.
11. Air France has a corresponding target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
12. KLM has a corresponding target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
13. Air France–KLM Group submitted to the Science Based Targets initiative its principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
14. Air France submitted to the Science Based Targets initiative its corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
15. KLM submitted to the Science Based Targets initiative its corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
16. In November 2022, the Science Based Targets initiative Target Validation Team approved Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
17. In November 2022, the Science Based Targets initiative Target Validation Team approved Air France's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
18. In November 2022, the Science Based Targets initiative Target Validation Team approved KLM's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
19. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.
20. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that Air France's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.
21. In November 2022, the Science Based Targets initiative Target Validation Team confirmed that KLM's corresponding emissions-reduction target supporting Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is aligned with a well-below 2°C pathway under the Paris Agreement.
22. The external validation by the Science Based Targets initiative provides the principal scientific reference for the level of ambition of Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
23. The external validation by the Science Based Targets initiative provides the principal scientific reference for the methodology of Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
24. In addition to its principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year, Air France–KLM has set an objective of achieving net-zero emissions by 2050.
25. Air France–KLM Group had committed to establishing additional CO₂-reduction targets for 2035.
26. No quantified Air France–KLM Group target for 2035 is included in the information reported in the disclosure.
27. For 2023, Air France–KLM Group reported an E1-4 scope-related target indicator of 10% for Scope 1 greenhouse gas emissions, measured with reference to emissions from an unspecified base year.
   - Unresolved context: The base year for the 2023 Scope 1 target indicator is not specified.
28. For 2023, Air France–KLM Group reported an E1-4 scope-related target indicator of 20% for Scope 3 greenhouse gas emissions, measured with reference to emissions from an unspecified base year.
   - Unresolved context: The base year for the 2023 Scope 3 target indicator is not specified.
29. For 2023, Air France–KLM Group reported an absolute total greenhouse gas emissions reduction of 800,000 tonnes of CO₂ equivalent.
30. For 2023, Air France–KLM Group reported an absolute total greenhouse gas emissions reduction of 800,000 tonnes of CO₂ equivalent.
31. Air France–KLM Group's Science Based Targets initiative-validated principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year is an emissions-intensity target based on well-to-wake jet-fuel emissions per revenue tonne-kilometre.
32. Air France–KLM Group's reported absolute total greenhouse gas emissions reduction metric of 800,000 tonnes of CO₂ equivalent for 2023 is distinct from its Science Based Targets initiative-validated principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year.
33. The boundary applied to Air France–KLM's climate metrics should be considered when interpreting performance.
34. The methodology applied to Air France–KLM's climate metrics should be considered when interpreting performance.
35. The scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances.
36. The scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances.
37. Because the scope of CO₂-equivalent emissions reported by Air France–KLM in the Extra-Financial Performance Statement differs from the scope used under the EU Emissions Trading System for greenhouse gas emission allowances, comparisons between those reporting bases are not meaningful.
38. Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the defined 2019 baseline.
39. Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the well-to-wake Scope 1 and Scope 3 jet-fuel boundary.
40. Progress against Air France–KLM Group's principal medium-term target to reduce well-to-wake Scope 1 and Scope 3 greenhouse gas emissions from jet fuel by 30% per revenue tonne-kilometre by 2030 compared with a 2019 base year should be assessed using the revenue tonne-kilometre intensity denominator.

Exclusions:

- `document_structure`: This is a section heading rather than a substantive proposition.
  - Source span: ### E1-4 – Climate-related targets

## Reproduction checks

- ec: direct -> integrated: draft, IDs, call lineage and patch replay match.
- ec: integrated -> atomic: draft, IDs, call lineage and patch replay match.
- dc: direct -> integrated: draft, IDs, call lineage and patch replay match.
- dc: integrated -> atomic: draft, IDs, call lineage and patch replay match.
- All selected-stage claim and exclusion quotations occur literally in their supplied source.
- Selected final EC inventory matches saved occurrence rows in order.

## Provenance

- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/direct/ec_extraction_calls.jsonl:1`; SHA-256: `c25550a4644ad4f994539894cd66f8e9a0b7d5c2294485643180bf05be0a3ed0`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/integrated/ec_extraction_calls.jsonl:1`; SHA-256: `d69d89af7dc6d8aa591236cac3097f9a3aa64645437c667e1d1ea1281ed0816b`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/atomic/ec_extraction_calls.jsonl:1`; SHA-256: `98ff61c44296c0481eb1b1812945b5d4cb7ccd86fc1f09d26eb8a3c0f0514af6`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/direct/dc_extraction_calls.jsonl:1`; SHA-256: `6fe270ef13c04058cc19c98951d19d8234526790b84279f308f9008bb3e00f56`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/integrated/dc_extraction_calls.jsonl:1`; SHA-256: `9a3740abe17dd5a5624285a3e8be47b62b60fa00863423674cfec13c621592bd`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/atomic/dc_extraction_calls.jsonl:1`; SHA-256: `b169dfe06b71ddafdd483e5eeb7147bda83e35c9fa95e83a5fd9d0c797b2067a`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/direct/claim_extraction_run_manifest.json`; SHA-256: `ab0d7fde262bbcac68bf7d5f7eb510133c6a8fcaf331de69577cf4b3d8cbfcdc`.
- `/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_ec_claim_extraction_prompt_v8.txt`; SHA-256: `c16eb19e8f739e6f54d8169e844a84e06112813f7cb9f25ceccb7647f9084d22`.
- `/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_dc_claim_extraction_prompt_v8.txt`; SHA-256: `9b09bd62e05a77e4182c2e070f34531561a5aa8be77eb10020c93a5d5cd92f0f`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/integrated/claim_extraction_run_manifest.json`; SHA-256: `71188480c269cbe7f955e90791b83baafb7d786c5d53f4b02c53338c7a8e5435`.
- `/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_ec_claim_patch_review_prompt_v4.txt`; SHA-256: `f1ec61f6416d4a30a32bda4a91371a8c68aa064417493d0373c66612d6185ba5`.
- `/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_dc_claim_patch_review_prompt_v4.txt`; SHA-256: `1d51a196f1561a1e82fbb8a3c900f2c9af743293ca1097ace40f0dd9cc22ad87`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/atomic/claim_extraction_run_manifest.json`; SHA-256: `c0a36972fb9af247bfb41c816f5aa2d5adb4cc1012362b2ea44c5fffc9b5d29a`.
- `/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_ec_claim_atomicity_review_prompt_v2.txt`; SHA-256: `423fbf4624cdb2c999ac303837e4dd46d858d8a017a14c2a027d10922c71d9c6`.
- `/home/muwang/master_thesis/BACE/config/evaluation/prompts/generation_dc_claim_atomicity_review_prompt_v2.txt`; SHA-256: `e6d02cd6bd331287153b483816809f4e79ebb206494cdf32c34a1ee29f8f41d2`.
- `/home/muwang/master_thesis/BACE/results/main_v1/cases/w2__text_embedding_3_large__stratified_by_evidence_type_n10__air_france_klm__2023__e1_4_targets/extraction/atomic/ec_claim_occurrences.jsonl`; SHA-256: `4eea4b0ef578b9f2ce92b95c5520da265417d7dbbe44a100b3de5803ef81ed9c`.

`examples.json` preserves all selected inventory fields, source quotations, uncertainties, exclusions, immutable patch references and source hashes. This report does not include or infer support-assessment verdicts. Rebuild with the independent system Python: `python paper/analysis/extraction_examples_2026-10-26/build_examples.py` from the repository root.
