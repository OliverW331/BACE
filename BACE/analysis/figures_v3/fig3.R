# Fig. 3 | Evidence support varies across disclosures, disclosure tasks and claim types.
# Reads the tidy data written by prep_fig3.py (saved outputs only).
# Run from the repository root:
#   BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_fig3.py
#   Rscript BACE/analysis/figures_v3/fig3.R

.libPaths(c("BACE/analysis/figures_v3/R-lib", .libPaths()))
suppressPackageStartupMessages({
  library(methods); library(ggplot2); library(ggdist); library(patchwork)
  library(ggtext); library(dplyr); library(readr); library(scales)
})

D <- "BACE/analysis/outputs/figures_v3/fig3_data"
OUT <- "BACE/analysis/outputs/figures_v3"
FONT <- "Liberation Sans"
BLUE <- "#3C5488"                                       # BACE, as in Fig. 2
LAB <- c(direct = "#3C5488", inferred = "#8491B4", unsupported = "#f5b4a8")   # NPG scheme; unsupported = light tint of FBD red
TOP <- c(E = "#9bb53a", S = "#a24a86", G = "#4DBBD5")   # topic colours; kept clear of evidence teal and unsupported red
REF <- "#8a8984"
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
no_y <- theme(panel.grid.major.y = element_blank(), axis.line.y = element_blank(),
              axis.ticks.y = element_blank(), axis.text.y = element_blank())
fmt <- function(x) sprintf("%.1f", x)
txt <- function(...) annotate("text", family = FONT, size = 5.5 / .pt, colour = INK, ...)

# ---------------------------------------------------------------- a: composition of all DCs
a <- read_csv(file.path(D, "a_label_composition.csv"), show_col_types = FALSE) |>
  mutate(label = factor(label, levels = rev(c("direct", "inferred", "unsupported"))),
         end = rev(cumsum(rev(share_pct))), start = end - share_pct, mid = (start + end) / 2,
         name = c(direct = "Direct support", inferred = "Inferred support",
                  unsupported = "Unsupported")[as.character(label)],
         text = paste0("**", name, "**<br>", comma(dcs), " (", fmt(share_pct), "%)"))
a <- a |> arrange(desc(end))   # direct occupies the left end
a$start <- c(0, cumsum(a$share_pct)[-3]); a$end <- cumsum(a$share_pct); a$mid <- (a$start + a$end) / 2
sup_end <- a$end[a$label == "inferred"]
pa <- ggplot(a) +
  geom_rect(aes(xmin = start, xmax = end, ymin = 0, ymax = 1, fill = label), colour = "white", linewidth = 0.5) +
  geom_richtext(aes(x = mid, y = 0.5, label = text,
                    colour = ifelse(label == "direct", "white", INK)),
                family = FONT, size = 5.8 / .pt, fill = NA, label.colour = NA, lineheight = 1.25) +
  annotate("segment", x = 0.2, xend = sup_end - 0.2, y = 1.22, yend = 1.22, colour = INK2, linewidth = 0.3) +
  annotate("segment", x = c(0.2, sup_end - 0.2), xend = c(0.2, sup_end - 0.2), y = 1.22, yend = 1.08,
           colour = INK2, linewidth = 0.3) +
  txt(x = sup_end / 2, y = 1.42, label = paste0("Accepted support set identified: ",
                                                 comma(sum(a$dcs[a$label != "unsupported"])), " DCs (",
                                                 fmt(sup_end), "%)")) +
  txt(x = 100, y = 1.42, hjust = 1, colour = INK2,
      label = paste0("All deduplicated disclosure claims, n = ", comma(sum(a$dcs)))) +
  scale_fill_manual(values = LAB) + scale_colour_identity() +
  scale_x_continuous(limits = c(0, 100), breaks = seq(0, 100, 20), labels = function(x) paste0(x, "%"),
                     expand = expansion(mult = c(0, 0.005))) +
  scale_y_continuous(limits = c(0, 1.55), expand = c(0, 0)) +
  labs(x = "Share of disclosure claims", y = NULL) + theme_bace() + no_y +
  theme(panel.grid.major = element_blank(), axis.line.x = element_blank())

# ---------------------------------------------------------------- b, d: rainclouds of disclosure-level measures
bd <- read_csv(file.path(D, "bd_disclosure_metrics.csv"), show_col_types = FALSE)
bds <- read_csv(file.path(D, "bd_summary.csv"), show_col_types = FALSE)
raincloud <- function(col, metric, xlab, fill) {
  s <- bds[bds$metric == metric, ]
  ggplot(bd, aes(x = .data[[col]], y = "all")) +
    stat_slab(adjust = 0.7, height = 0.95, alpha = 0.35, fill = fill, colour = NA,
              position = position_nudge(y = 0.04)) +
    stat_dots(side = "bottom", quantiles = 150, height = 0.62, dotsize = 1.05, fill = fill, colour = fill,
              position = position_nudge(y = -0.04)) +
    stat_pointinterval(.width = c(0.5, 0.95), point_interval = "median_qi", point_size = 1,
                       interval_size_range = c(0.4, 1.1), colour = INK, position = position_nudge(y = -0.02)) +
    annotate("point", x = s$mean_pct, y = 1.2, shape = 23, size = 1.7, fill = "white", colour = INK, stroke = 0.45) +
    txt(x = s$median_pct, y = 0.3, vjust = 1,
        label = paste0("median ", fmt(s$median_pct), "%  ·  IQR ", fmt(s$q25_pct), "–", fmt(s$q75_pct), "%")) +
    txt(x = s$mean_pct + 2.5, y = 1.2, hjust = 0,
        label = paste0("mean ", fmt(s$mean_pct), "% [", fmt(s$low_pct), ", ", fmt(s$high_pct), "]")) +
    scale_x_continuous(breaks = seq(0, 100, 20), expand = c(0, 0)) +
    coord_cartesian(xlim = c(0, 101), ylim = c(0.1, 2.0), expand = FALSE) +
    labs(x = xlab, y = NULL) + theme_bace() + no_y
}
pb <- raincloud("support_pct", "support", "Disclosure support rate, *S*<sub>d</sub> (%)", BLUE) +
  theme(axis.title.x = element_markdown())
pd_ <- raincloud("eccr_pct", "eccr", "Evidence Claim Coverage Ratio, ECCR (%)", "#00A087")

# ---------------------------------------------------------------- c: task means with company-cluster intervals
short <- c(
  "E1-1_transition_plan" = "E1-1 Transition plan", "E1-3_actions_resources" = "E1-3 Climate actions and resources",
  "E1-4_targets" = "E1-4 Climate targets", "E1-6_ghg_emissions" = "E1-6 GHG emissions",
  "S1-1_workforce_policies" = "S1-1 Workforce policies", "S1-4_workforce_actions_resources" = "S1-4 Workforce actions",
  "S1-5_workforce_targets" = "S1-5 Workforce targets", "S1-14_health_safety_metrics" = "S1-14 Health and safety metrics",
  "G1-1_business_conduct_policies" = "G1-1 Business conduct policies", "G1-2_supplier_relationships" = "G1-2 Supplier relationships",
  "G1-3_anti_corruption_controls" = "G1-3 Anti-corruption controls", "G1-4_corruption_bribery_incidents" = "G1-4 Corruption and bribery incidents")
topic_name <- c(E = "Climate change (E1)", S = "Own workforce (S1)", G = "Business conduct (G1)")
cm <- read_csv(file.path(D, "c_task_means.csv"), show_col_types = FALSE)
cr <- read_csv(file.path(D, "c_task_bootstrap.csv"), show_col_types = FALSE)
ct <- read_csv(file.path(D, "c_topic_means.csv"), show_col_types = FALSE) |>
  mutate(topic = factor(topic, levels = c("E", "S", "G"), labels = topic_name[c("E", "S", "G")]))
ord <- cm |> mutate(topic = factor(topic, levels = c("E", "S", "G"))) |> arrange(topic, mean_pct) |> pull(task_id)
prep_c <- function(d) d |> mutate(task = factor(short[task_id], levels = short[ord]),
                                  tcol = topic, topic = factor(topic, levels = c("E", "S", "G"),
                                                               labels = topic_name[c("E", "S", "G")]))
cm <- prep_c(cm); cr <- prep_c(cr)
ct$tcol <- c(E = "E", S = "S", G = "G")[substr(as.character(ct$topic), nchar(as.character(ct$topic)) - 2,
                                                nchar(as.character(ct$topic)) - 2)]
pc <- ggplot(cr, aes(x = replicate_pct, y = task)) +
  geom_rect(data = ct, aes(xmin = low_pct, xmax = high_pct, ymin = -Inf, ymax = Inf),
            inherit.aes = FALSE, fill = REF, alpha = 0.12) +
  geom_vline(data = ct, aes(xintercept = mean_pct), colour = REF, linewidth = 0.35, linetype = "22") +
  stat_halfeye(aes(fill = tcol), .width = 0.95, point_interval = "mean_qi", height = 0.85, alpha = 0.6,
               slab_colour = NA, point_size = 1, interval_size = 0.8, colour = INK, adjust = 1.1) +
  geom_text(data = cm, aes(x = 70.8, y = task, label = fmt(mean_pct)), family = FONT,
            size = 5.5 / .pt, colour = INK, hjust = 0, vjust = 0.2) +
  geom_text(data = ct, colour = INK2, aes(x = mean_pct, y = Inf,
                           label = paste0("topic mean ", fmt(mean_pct), " [", fmt(low_pct), ", ", fmt(high_pct), "]")),
            inherit.aes = FALSE, family = FONT, size = 5 / .pt, hjust = -0.04, vjust = 1.3) +
  facet_grid(topic ~ ., scales = "free_y", space = "free_y", switch = "y") +
  scale_fill_manual(values = TOP) + scale_colour_manual(values = TOP) +
  geom_text(data = ct[1, ], aes(x = 70.8, y = Inf, label = "Mean"), inherit.aes = FALSE, family = FONT,
            size = 5.5 / .pt, colour = INK2, fontface = "bold", hjust = 0, vjust = 1.3) +
  scale_x_continuous(limits = c(40, 70), breaks = seq(40, 70, 5), oob = oob_keep, expand = c(0, 0)) +
  scale_y_discrete(expand = expansion(add = c(0.6, 1.15))) +
  coord_cartesian(clip = "off") +
  labs(x = "Mean disclosure support rate (%)", y = NULL) + theme_bace() +
  theme(panel.grid.major.y = element_blank(), axis.line.y = element_blank(), axis.ticks.y = element_blank(),
        axis.text.y = element_text(size = 5.6, colour = INK, hjust = 1),
        strip.placement = "outside", strip.text.y.left = element_text(angle = 90, face = "bold", hjust = 0.5,
                                                                       size = 5.8, margin = margin(r = 3)),
        panel.spacing.y = unit(3, "pt"), plot.margin = margin(3, 16, 3, 3))

# ---------------------------------------------------------------- e: quantitative versus narrative claims
es <- read_csv(file.path(D, "e_quantity_support.csv"), show_col_types = FALSE)
er <- read_csv(file.path(D, "e_quantity_bootstrap.csv"), show_col_types = FALSE)
lv <- c("No quantity stated", "Quantity stated")
es$group <- factor(es$group, levels = lv); er$group <- factor(er$group, levels = lv)
es$ylab <- paste0("**", es$group, "**<br><span style='color:", INK2, "'>", comma(es$dcs), " DCs</span>")
er <- er |> left_join(es |> select(group, ylab), by = "group")
er$ylab <- factor(er$ylab, levels = es$ylab[match(lv, es$group)])
es$ylab <- factor(es$ylab, levels = levels(er$ylab))
pe <- ggplot(er, aes(x = replicate_pct, y = ylab)) +
  stat_halfeye(aes(fill = group), .width = 0.95, point_interval = "mean_qi", height = 0.8, alpha = 0.6,
               slab_colour = NA, point_size = 1.1, interval_size = 0.9, colour = INK, adjust = 1.6) +
  geom_text(data = es, aes(x = high_pct + 0.8, y = ylab,
                           label = paste0(fmt(supported_pct), "% [", fmt(low_pct), ", ", fmt(high_pct), "]")),
            family = FONT, size = 5.5 / .pt, colour = INK, hjust = 0, vjust = 0.1) +
  annotate("segment", x = es$supported_pct[es$group == lv[1]], xend = es$supported_pct[es$group == lv[2]],
           y = 1.5, yend = 1.5, colour = INK2, linewidth = 0.3,
           arrow = arrow(length = unit(2.5, "pt"), ends = "both", type = "closed")) +
  txt(x = mean(es$supported_pct), y = 1.5, vjust = -0.6, colour = INK2,
      label = paste0("+", fmt(diff(es$supported_pct[match(lv, es$group)])), " pp")) +
  scale_fill_manual(values = c("No quantity stated" = "#8491B4", "Quantity stated" = BLUE)) +
  scale_x_continuous(limits = c(45, 90), breaks = seq(45, 90, 5), oob = oob_keep, expand = c(0, 0)) +
  scale_y_discrete(expand = expansion(add = c(0.35, 0.9))) +
  labs(x = "Pooled DC support rate (%)", y = NULL) + theme_bace() +
  theme(panel.grid.major.y = element_blank(), axis.line.y = element_blank(), axis.ticks.y = element_blank(),
        axis.text.y = element_markdown(size = 5.8, colour = INK, hjust = 1, lineheight = 1.2))

# ---------------------------------------------------------------- layout
design <- "
AAAA
BBCC
DDCC
EECC
"
fig <- pa + pb + pc + pd_ + pe +
  plot_layout(design = design, heights = c(0.42, 1, 1, 0.95), widths = c(1, 1, 1.15, 1.15)) +
  plot_annotation(tag_levels = "a")
# tag order follows the design letters: a=A, b=B, c=C, d=D, e=E
ggsave(file.path(OUT, "fig3.pdf"), fig, width = 183, height = 150, units = "mm", device = cairo_pdf)
ggsave(file.path(OUT, "fig3.png"), fig, width = 183, height = 150, units = "mm", dpi = 300,
       device = ragg::agg_png, bg = "white")
cat("written", file.path(OUT, "fig3.pdf"), "\n")
