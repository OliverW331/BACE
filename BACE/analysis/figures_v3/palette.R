# Shared colour system for all BACE figures (main and Extended Data): candy palette.
# One meaning per hue across the paper:
#   blue   = BACE / disclosure claims / identified support (direct mid blue, inferred pale blue)
#   aqua   = evidence: sources, evidence claims, ECCR
#   stone  = comparators (RAGChecker darker, RAGAS lighter), unsupported share, context
#   six candy hues = primary diagnoses (fixed order, never reused)
# Candy fills are light, so text never sits in a fill colour: labels use ink, and lines,
# outlines and headings use the *_dark step of the same hue. Diagnosis hues validated with the
# dataviz validate_palette.js (adjacent pairs): CVD dE >= 11, normal-vision dE >= 17; the
# lightness-band check fails by design (candy tints), mitigated by ink labels and white gaps.
PAL <- list(
  ink = "#1f1f1e", ink2 = "#52514e", muted = "#8a8984", grid = "#eeece8", line = "#c9c6c1",
  panel = "#f7f5f2", card_border = "#dedad4",
  # BACE / support
  bace = "#60a5fa", bace_dark = "#2563eb", direct = "#60a5fa", inferred = "#bfdbfe", bace_tint = "#eef5ff",
  unsupported = "#e7e5e4",
  # evidence (aqua ramp, dark -> light)
  ev = "#5fd0e3", ev_dark = "#0e9cb8", ev_mid = "#8fe0ee", ev_light = "#c6f1f8", ev_tint = "#ebfbfd",
  # comparators
  ragchecker = "#a8a29e", ragas = "#d6d3d1", ragchecker_dark = "#78716c", ragas_dark = "#a8a29e",
  # diagnoses (candy) and their dark steps for outlines/text
  fbd = "#ff8a65", conflation = "#9f8bfa", nds = "#f7a1cf", inflation = "#f9cb3e",
  novelty = "#4fd9a6", contradiction = "#f25c7a",
  fbd_dark = "#e8603a", conflation_dark = "#6d55e0"
)
FRAMEWORK_COL <- c(BACE = PAL$bace, RAGChecker = PAL$ragchecker, RAGAS = PAL$ragas)
FRAMEWORK_DARK <- c(BACE = PAL$bace_dark, RAGChecker = PAL$ragchecker_dark, RAGAS = PAL$ragas_dark)
SUPPORT_COL <- c(direct = PAL$direct, inferred = PAL$inferred, unsupported = PAL$unsupported)
DIAG_COL <- c(factual_boundary_distortion = PAL$fbd, evidence_conflation = PAL$conflation,
              non_disclosure_statement = PAL$nds, inferential_inflation = PAL$inflation,
              unsupported_novelty = PAL$novelty, contradiction = PAL$contradiction)
