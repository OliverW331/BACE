# Paper-wide colour scheme (Figs 1–4, Extended Data Figs 1–3)

The scheme is based on the NPG palette from ggsci (`pal_npg("nrc")`), which is modelled on figures in Nature Reviews journals. Each colour has one meaning across all figures. Every category is also identified by a legend, an axis label or a direct label, so colour is never the only cue, as Nature's figure guide requires.

| Meaning | Colour(s) | Used in |
|---|---|---|
| BACE, disclosure side, direct support | navy `#3C5488` (contour lines `#25355e`) | Figs 1–4 |
| Inferred support | lavender grey `#8491B4` | Figs 1, 3a, 3e, 4 |
| Evidence side (ECs, ECCR, evidence cards, source availability) | teal `#00A087`; ramp `#91D1C2`, `#4fb6a2`, `#00A087`, `#006b5a`; heatmap `#e6f4f1` → `#006b5a` | Figs 1, 3d; ED Figs 1–2 |
| Unsupported, as a whole | light red `#f5b4a8` | Fig. 3a |
| Diagnoses | factual boundary distortion `#E64B35`; evidence conflation `#7E6148`; non-disclosure statement `#B09C85`; inferential inflation `#F39B7F`; unsupported novelty `#4DBBD5`; contradiction `#3B3B3B` | ED Fig. 3 (all six); Fig. 4a (first two coloured, other four `#cfcac3`); Figs 1, 4b–c chips |
| ESRS topics | E olive green `#9bb53a`; S plum `#a24a86`; G cyan `#4DBBD5` | Fig. 3c only |
| Comparators (de-emphasised) | RAGChecker `#6f6d66`; RAGAS `#a9a7a0` | Fig. 2 |
| Neutral | ink `#1f1f1e` / `#52514e`; reference lines and bands `#8a8984`; panels `#f4f3ef` / `#efede8` | all |

Notes:
- Topic colours are kept clear of the other colours in Fig. 3. E (olive green) against the evidence teal gives normal-vision ΔE 16.2. S (plum) against the light red of "Unsupported" in Fig. 3a gives 30.5, against inferred lavender 17.7 and against FBD red 17.3. All are above the floor of 15.
- Text uses ink colours, and coloured marks or icons carry identity.
