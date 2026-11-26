# Fig. 4 | Primary diagnoses of unsupported disclosure claims.
# Reads the tidy data written by prep_fig4.py (saved outputs only).
# Run from the repository root:
#   BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_fig4.py
#   Rscript BACE/analysis/figures_v3/fig4.R

.libPaths(c("BACE/analysis/figures_v3/R-lib", .libPaths()))
suppressPackageStartupMessages({
  library(methods); library(ggplot2); library(ggdist); library(patchwork)
  library(ggtext); library(dplyr); library(readr); library(scales)
})

D <- "BACE/analysis/outputs/figures_v3/fig4_data"
OUT <- "BACE/analysis/outputs/figures_v3"
FONT <- "Liberation Sans"
INK <- "#1f1f1e"; INK2 <- "#52514e"; MUTED <- "#8a8984"; GRID <- "#ebeae6"
DCOL <- c(factual_boundary_distortion = "#E64B35", evidence_conflation = "#7E6148",   # NPG scheme (COLOURS.md)
          non_disclosure_statement = "#cfcac3", inferential_inflation = "#cfcac3",
          unsupported_novelty = "#cfcac3", contradiction = "#cfcac3",
          direct = "#3C5488", inferred = "#8491B4")              # support colours as in Fig. 3a
LNAME <- c(factual_boundary_distortion = "Factual boundary distortion", evidence_conflation = "Evidence conflation",
           direct = "Direct support", inferred = "Inferred support")

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
      legend.position = "none",
      plot.tag = element_text(size = 8, face = "bold", family = FONT),
      plot.margin = margin(3, 6, 3, 3)
    )
}
fmt <- function(x) sprintf("%.1f", x)

# ---------------------------------------------------------------- a: diagnosis shares
a <- read_csv(file.path(D, "a_diagnosis_shares.csv"), show_col_types = FALSE) |>
  arrange(share_pct) |> mutate(name = factor(name, levels = name), y = seq_along(name))
top2 <- a |> filter(diagnosis %in% c("factual_boundary_distortion", "evidence_conflation"))
pa <- ggplot(a, aes(y = name)) +
  geom_col(aes(x = share_pct, fill = diagnosis), width = 0.62, alpha = 0.9) +
  geom_errorbarh(aes(xmin = low_pct, xmax = high_pct), height = 0.22, linewidth = 0.35, colour = INK) +
  geom_text(aes(x = high_pct + 1, label = paste0(fmt(share_pct), "% [", fmt(low_pct), ", ", fmt(high_pct), "]  ·  ",
                                                 comma(dcs), " DCs")),
            family = FONT, size = 5.5 / .pt, colour = INK, hjust = 0) +
  annotate("segment", x = 67, xend = 67, y = min(top2$y) - 0.3, yend = max(top2$y) + 0.3, colour = INK2, linewidth = 0.3) +
  annotate("segment", x = c(66.3, 66.3), xend = c(67, 67), y = c(min(top2$y) - 0.3, max(top2$y) + 0.3),
           yend = c(min(top2$y) - 0.3, max(top2$y) + 0.3), colour = INK2, linewidth = 0.3) +
  annotate("text", x = 68, y = mean(top2$y), hjust = 0, family = FONT, size = 5.5 / .pt, colour = INK, lineheight = 1.1,
           label = "Together 73.5%\n[71.5, 75.5]\n31,335 DCs") +
  scale_fill_manual(values = DCOL) +
  scale_x_continuous(limits = c(0, 80), breaks = seq(0, 50, 10), expand = c(0, 0)) +
  labs(x = "Share of unsupported disclosure claims (%), n = 42,646", y = NULL) + theme_bace() +
  theme(panel.grid.major.y = element_blank(), axis.line.y = element_blank(), axis.ticks.y = element_blank(),
        axis.text.y = element_text(size = 6, colour = INK))

# ---------------------------------------------------------------- b, c: case cards
cl <- read_csv(file.path(D, "bc_case_claims.csv"), show_col_types = FALSE)
ev <- read_csv(file.path(D, "bc_case_evidence.csv"), show_col_types = FALSE)
sentences <- function(x) trimws(unlist(strsplit(x, "(?<=[.!?])\\s+", perl = TRUE)))
excerpt <- function(passage, keys, from = NULL) {
  if (!is.null(from)) passage <- substring(passage, regexpr(from, passage, fixed = TRUE))
  s <- sentences(passage); keep <- s[sapply(s, function(z) any(sapply(keys, grepl, x = z, fixed = TRUE)))]
  paste(keep, collapse = " ")
}
DISPLAY <- c(Nestle = "Nestlé")   # company_name is stored without diacritics
doc <- function(t) c(annual_report = "annual report", sustainability_report = "sustainability report")[[t]]
chip <- function(lab) sprintf("<span style='color:%s'>■</span> **%s**", DCOL[[lab]], LNAME[[lab]])
grey <- function(x) paste0("<span style='color:", INK2, "'>", x, "</span>")
box <- function(label, fill, y) tibble::tibble(x = 0, y = y, label = label, fill = fill)

card <- function(p, ev_keys, vary, ys, from = list(NULL, NULL)) {
  k <- cl |> filter(panel == p); e <- ev |> filter(panel == p)
  co <- if (k$company[1] %in% names(DISPLAY)) DISPLAY[[k$company[1]]] else k$company[1]
  head <- paste0("**", co, ", ", k$target_year[1], " · ", sub("_.*", "", k$task_id[1]), " ",
                 sub("^\\S+ ", "", k$task_title[1]), "**")
  ev_txt <- if (n_distinct(sapply(e$passage, excerpt, keys = ev_keys[[1]])) == 1 && length(ev_keys) == 1) {
    paste0(grey(paste0("Supplied evidence · ", e$source_year[1], " ", doc(e$document_type[1]), ", p. ", e$page[1],
                       " (same passage in the ", e$source_year[2], " ", doc(e$document_type[2]), ", p. ", e$page[2], ")")),
           "<br>“", excerpt(e$passage[1], ev_keys[[1]]), "”")
  } else {
    paste(sapply(seq_len(nrow(e)), function(i)
      paste0(grey(paste0("Supplied evidence · ", e$source_year[i], " ", doc(e$document_type[i]), ", p. ", e$page[i])),
             "<br>“… ", excerpt(e$passage[i], ev_keys[[i]], from[[i]]), " …”")), collapse = "<br>")
  }
  gen <- paste0(grey(paste0("Generated sentence · simulated ", k$target_year[1], " disclosure")), "<br>*“",
                k$generated_sentence[1], "”*")
  rows <- sapply(seq_len(nrow(k)), function(i) {
    t <- k$dc_text[i]
    t <- sub(vary[i], paste0("**", vary[i], "**"), t, fixed = TRUE)
    r <- paste0(chip(k$label[i]), "<br>“", t, "”")
    if (k$focal[i]) r <- paste0(r, "<br>", grey(paste0("*Rationale:* ", k$rationale[i])))
    r
  })
  dcs <- paste0(grey("Disclosure claims extracted from this sentence (the randomly drawn example first)"), "<br>",
                paste(rows, collapse = "<br><br>"))
  bind_rows(box(paste0(head, "<br>", ev_txt), "#f4f3ef", ys[1]), box(gen, "white", ys[2]), box(dcs, "white", ys[3]))
}
draw_card <- function(d) {
  ggplot(d) +
    geom_textbox(aes(x = x, y = y, label = label, fill = fill), hjust = 0, vjust = 1, halign = 0,
                 width = unit(1, "npc"), family = FONT, size = 5.6 / .pt, colour = INK, box.colour = "#d6d5cf",
                 box.size = 0.25, box.r = unit(2, "pt"), box.padding = unit(c(3, 4, 3, 4), "pt"), lineheight = 1.25) +
    scale_fill_identity() +
    scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) + scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
    theme_void(base_family = FONT) +
    theme(plot.tag = element_text(size = 8, face = "bold", family = FONT), plot.margin = margin(14, 6, 0, 3))
}
YB <- c(1, 0.84, 0.705); YC <- c(1, 0.745, 0.595)
pb <- draw_card(card("b", list(c("online solution", "2,000 suppliers")),
                     c("identification", "assessment", "monitoring"), YB))
pc <- draw_card(card("c", list(c("raising the bar"), c("between 2010 and 2017")),
                     c("addressing", "assessing", "reporting"), YC, from = list("we are now raising", NULL)))

# ---------------------------------------------------------------- layout
fig <- pa / (wrap_elements(full = pb) + wrap_elements(full = pc) + plot_layout(widths = c(1, 1))) + plot_layout(heights = c(0.5, 1.45)) +
  plot_annotation(tag_levels = "a") &
  theme(plot.tag = element_text(size = 8, face = "bold", family = FONT, colour = INK))
ggsave(file.path(OUT, "fig4.pdf"), fig, width = 183, height = 140, units = "mm", device = cairo_pdf)
ggsave(file.path(OUT, "fig4.png"), fig, width = 183, height = 140, units = "mm", dpi = 300,
       device = ragg::agg_png, bg = "white")
cat("written", file.path(OUT, "fig4.pdf"), "\n")
