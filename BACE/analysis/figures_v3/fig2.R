# Fig. 2 | Evidence-support assessments diverge across evaluation frameworks.
# Reads the tidy data written by prep_fig2.py (saved outputs only).
# Run from the repository root:
#   BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_fig2.py
#   Rscript BACE/analysis/figures_v3/fig2.R

.libPaths(c("BACE/analysis/figures_v3/R-lib", .libPaths()))
suppressPackageStartupMessages({
  library(methods); library(ggplot2); library(ggdist); library(patchwork)
  library(ggtext); library(dplyr); library(readr); library(scales)
})

D <- "BACE/analysis/outputs/figures_v3/fig2_data"
OUT <- "BACE/analysis/outputs/figures_v3"
FONT <- "Liberation Sans"
COL <- c(BACE = "#3C5488", RAGChecker = "#6f6d66", RAGAS = "#a9a7a0")  # NPG scheme (COLOURS.md): BACE navy; comparators grey
INK <- "#1f1f1e"; INK2 <- "#52514e"; MUTED <- "#8a8984"; GRID <- "#ebeae6"

theme_bace <- function() {
  theme_minimal(base_size = 6, base_family = FONT) +
    theme(
      text = element_text(colour = INK),
      axis.text = element_text(colour = INK2, size = 5.5),
      axis.title = element_text(size = 6),
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(colour = GRID, linewidth = 0.25),
      axis.line = element_line(colour = INK2, linewidth = 0.3),
      axis.ticks = element_line(colour = INK2, linewidth = 0.3),
      axis.ticks.length = unit(1.2, "pt"),
      strip.text = element_text(size = 6, hjust = 0, colour = INK, margin = margin(b = 2)),
      legend.position = "none",
      plot.tag = element_text(size = 8, face = "bold", family = FONT),
      plot.margin = margin(3, 6, 3, 3)
    )
}
fmt <- function(x) gsub("-", "−", sprintf("%.1f", x))

# ---------------------------------------------------------------- a: rainclouds of disclosure scores
a <- read_csv(file.path(D, "a_scores.csv"), show_col_types = FALSE) |>
  mutate(framework = factor(framework, levels = c("RAGAS", "RAGChecker", "BACE")))
a_mean <- a |> group_by(framework) |> summarise(mean = mean(score_pct), .groups = "drop")
pa <- ggplot(a, aes(x = score_pct, y = framework, fill = framework, colour = framework)) +
  stat_slab(adjust = 0.7, height = 0.62, alpha = 0.35, colour = NA, normalize = "groups") +
  stat_dots(side = "bottom", quantiles = 120, height = 0.5, dotsize = 1.05,
            position = position_nudge(y = -0.04)) +
  stat_pointinterval(.width = c(0.5, 0.95), point_size = 0.9, interval_size_range = c(0.35, 1),
                     colour = INK, position = position_nudge(y = -0.02)) +
  geom_point(data = a_mean, aes(x = mean, y = framework), inherit.aes = FALSE, shape = 23, size = 1.6,
             fill = "white", colour = INK, stroke = 0.45, position = position_nudge(y = 0.2)) +
  geom_text(data = a_mean, aes(x = mean, y = framework, label = paste0("mean ", fmt(mean), "%")),
            inherit.aes = FALSE, family = FONT, size = 5.5 / .pt, colour = INK, hjust = 1,
            nudge_x = -2.2, nudge_y = 0.2) +
  scale_fill_manual(values = COL) + scale_colour_manual(values = COL) +
  scale_x_continuous(limits = c(0, 100), breaks = seq(0, 100, 20), expand = expansion(mult = c(0, 0.01))) +
  labs(x = "Disclosure score (%)", y = NULL) + theme_bace() +
  theme(panel.grid.major.y = element_blank(), axis.line.y = element_blank(), axis.ticks.y = element_blank(),
        axis.text.y = element_text(size = 6, colour = INK, face = "bold"))

# ---------------------------------------------------------------- b: bootstrap distributions of paired differences
b_rep <- read_csv(file.path(D, "b_paired_bootstrap.csv"), show_col_types = FALSE)
b_sum <- read_csv(file.path(D, "b_paired_summary.csv"), show_col_types = FALSE)
lv <- c("BACE − RAGAS", "BACE − RAGChecker")
b_rep$comparison <- factor(b_rep$comparison, levels = lv); b_sum$comparison <- factor(b_sum$comparison, levels = lv)
pb <- ggplot(b_rep, aes(x = replicate_pp, y = comparison, fill = comparator)) +
  stat_halfeye(.width = 0.95, point_interval = "mean_qi", adjust = 1, height = 0.8, alpha = 0.55,
               slab_colour = NA, point_size = 1.1, interval_size = 0.9, colour = INK) +
  geom_text(data = b_sum, aes(x = high_pp + 0.25, y = comparison,
                              label = paste0(fmt(mean_pp), "\n[", fmt(low_pp), ", ", fmt(high_pp), "]")),
            inherit.aes = FALSE, family = FONT, size = 5.3 / .pt, colour = INK, hjust = 0, vjust = 1.2,
            lineheight = 0.95) +
  scale_fill_manual(values = COL) +
  scale_x_continuous(limits = c(-38.2, -31.6), breaks = seq(-38, -32, 1), labels = function(x) fmt(x) |> sub("\\.0$", "", x = _)) +
  labs(x = "Paired difference, BACE minus comparator (pp)", y = NULL) + theme_bace() +
  theme(panel.grid.major.y = element_blank(), axis.line.y = element_blank(), axis.ticks.y = element_blank(),
        axis.text.y = element_text(size = 5.8, colour = INK))

# ---------------------------------------------------------------- c: disclosure-level agreement
cdat <- read_csv(file.path(D, "c_scatter.csv"), show_col_types = FALSE) |>
  mutate(comparator = factor(comparator, levels = c("RAGChecker", "RAGAS")))
c_note <- cdat |> group_by(comparator) |>
  summarise(n_full = sum(comparator_pct >= 99.999), n_low = sum(full_native_low_bace), .groups = "drop") |>
  mutate(label = paste0("Open circles: ", n_low, " of ", n_full, "\ndisclosures at 100%\nwith BACE <50%"))
pc <- ggplot(cdat, aes(x = comparator_pct, y = bace_pct)) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = -Inf, ymax = 50, fill = "#f4f3ef") +
  geom_point(data = ~ filter(.x, !full_native_low_bace), size = 0.35, alpha = 0.28, colour = COL[["BACE"]], stroke = 0) +
  geom_density_2d(colour = "#25355e", linewidth = 0.25, bins = 7, alpha = 0.9) +
  geom_point(data = ~ filter(.x, full_native_low_bace), shape = 21, size = 0.9, stroke = 0.35,
             fill = "white", colour = "#25355e") +
  geom_text(data = c_note, aes(x = 31, y = 99, label = label), family = FONT, size = 5 / .pt, colour = INK2,
            hjust = 0, vjust = 1, lineheight = 0.95) +
  facet_wrap(~comparator, labeller = as_labeller(c(RAGChecker = "BACE vs RAGChecker", RAGAS = "BACE vs RAGAS"))) +
  scale_x_continuous(limits = c(30, 101), breaks = c(40, 70, 100)) +
  scale_y_continuous(limits = c(0, 100), breaks = c(0, 50, 100)) +
  labs(x = "Comparator native score (%)", y = "BACE support rate (%)") + theme_bace() +
  theme(panel.spacing.x = unit(8, "pt"))

# ---------------------------------------------------------------- d: Svenska Cellulosa case card
chip <- function(k, v, bold = FALSE) {
  v <- if (bold) paste0("**", v, "**") else v
  sprintf("<span style='color:%s'>■</span> %s: %s", COL[[k]], k, v)
}
card <- tibble::tibble(
  x = 0, y = c(0.98, 0.70, 0.36),
  label = c(
    paste0("**Svenska Cellulosa (SCA), 2022 · G1-4 Incidents of corruption or bribery**<br>",
           "<span style='color:", INK2, "'>Supplied evidence: structured metric, 2022</span><br>",
           "Confirmed incidents in which own workers were dismissed or disciplined for corruption or bribery: **5**"),
    paste0("<span style='color:", INK2, "'>Generated claim 1</span><br>",
           "*“Five of SCA’s own workers were dismissed or subjected to disciplinary measures.”*<br>",
           chip("RAGChecker", "supported"), " &nbsp; ", chip("RAGAS", "supported"), " &nbsp; ",
           chip("BACE", "unsupported", TRUE), "<br>",
           "<span style='color:", INK2, "'>BACE: factual boundary distortion — an incident count became a worker count.</span>"),
    paste0("<span style='color:", INK2, "'>Generated claim 2</span><br>",
           "*“The five disciplinary or dismissal outcomes describe SCA’s response to the five confirmed incidents.”*<br>",
           chip("RAGAS", "unsupported", TRUE), " &nbsp; ", chip("BACE", "direct support"), "<br>",
           "<span style='color:", INK2, "'>Disagreement in the opposite direction.</span>")),
  fill = c("#f4f3ef", "white", "white"))
pd_ <- ggplot(card) +
  geom_textbox(aes(x = x, y = y, label = label, fill = fill), hjust = 0, vjust = 1, halign = 0,
               width = unit(1, "npc"), family = FONT, size = 5.6 / .pt, colour = INK, box.colour = "#d6d5cf",
               box.size = 0.25, box.r = unit(2, "pt"), box.padding = unit(c(3, 4, 3, 4), "pt"),
               lineheight = 1.25) +
  scale_fill_identity() +
  scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) + scale_y_continuous(limits = c(-0.05, 1.0), expand = c(0, 0)) +
  theme_void(base_family = FONT) +
  theme(plot.title = element_text(size = 6, face = "bold", colour = INK, margin = margin(b = 3, l = 15)),
        plot.tag = element_text(size = 8, face = "bold", family = FONT), plot.margin = margin(3, 6, 3, 3))

# ---------------------------------------------------------------- e: identical claims, dumbbell with intervals
e <- read_csv(file.path(D, "e_identical_claims.csv"), show_col_types = FALSE)
glv <- c("Other year only", "Target year stated", "No year stated")
nlab <- e |> distinct(group, n_pairs) |> mutate(lab = paste0(group, "<br><span style='color:", MUTED, "'>n = ",
                                                              format(n_pairs, big.mark = ","), "</span>"))
ep <- e |> filter(framework != "Difference") |> mutate(group = factor(group, levels = glv))
ed <- e |> filter(framework == "Difference") |> mutate(group = factor(group, levels = glv))
seg <- ep |> select(group, framework, supported_pct) |> tidyr::pivot_wider(names_from = framework, values_from = supported_pct)
pe <- ggplot(ep, aes(y = group)) +
  geom_segment(data = seg, aes(x = BACE, xend = RAGAS, y = group, yend = group), inherit.aes = FALSE, colour = "#c9c8c2", linewidth = 1.6, lineend = "round") +
  geom_errorbarh(aes(xmin = low_pct, xmax = high_pct, colour = framework), height = 0, linewidth = 0.6) +
  geom_point(aes(x = supported_pct, fill = framework), shape = 21, size = 2.1, colour = "white", stroke = 0.5) +
  geom_text(data = ed, aes(x = 101.5, y = group, label = paste0("Δ ", fmt(supported_pct), " pp\n[", fmt(low_pct), ", ", fmt(high_pct), "]")),
            family = FONT, size = 5.4 / .pt, colour = INK, hjust = 0, lineheight = 0.95, fontface = "bold") +
  annotate("text", x = c(55.9, 95.5), y = 3.42, label = c("BACE", "RAGAS"), family = FONT, size = 5.5 / .pt,
           colour = c(COL[["BACE"]], COL[["RAGChecker"]]), fontface = "bold") +
  scale_colour_manual(values = COL) + scale_fill_manual(values = COL) +
  scale_y_discrete(labels = setNames(nlab$lab, nlab$group)) +
  scale_x_continuous(limits = c(40, 118), breaks = seq(40, 100, 20), expand = c(0, 0)) +
  coord_cartesian(clip = "off") +
  labs(x = "Identical claims supported (%)", y = NULL) + theme_bace() +
  theme(axis.text.y = element_markdown(size = 5.8, colour = INK, lineheight = 1.1),
        panel.grid.major.y = element_blank(), axis.line.y = element_blank(), axis.ticks.y = element_blank())

# ---------------------------------------------------------------- assemble
fig <- (pa + pb + plot_layout(widths = c(1.35, 1))) /
  (pc + pd_ + plot_layout(widths = c(1.1, 1))) /
  pe +
  plot_layout(heights = c(1, 1.05, 0.55)) +
  plot_annotation(tag_levels = "a") &
  theme(plot.tag.position = c(0, 1))

W <- 183; H <- 175
ggsave(file.path(OUT, "fig2.pdf"), fig, width = W, height = H, units = "mm", device = cairo_pdf)
ragg::agg_png(file.path(OUT, "fig2.png"), width = W, height = H, units = "mm", res = 300); print(fig); invisible(dev.off())
cat("saved", file.path(OUT, "fig2.pdf"), "\n")
