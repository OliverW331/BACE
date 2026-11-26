# Extended Data Figs 1–3. Reads the tidy data written by prep_ed.py (saved outputs only).
# Run from the repository root:
#   BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_ed.py
#   Rscript BACE/analysis/figures_v3/ed_figs.R

.libPaths(c("BACE/analysis/figures_v3/R-lib", .libPaths()))
suppressPackageStartupMessages({
  library(methods); library(ggplot2); library(patchwork); library(ggtext)
  library(dplyr); library(readr); library(scales); library(forcats)
})

D <- "BACE/analysis/outputs/figures_v3/ed_data"
OUT <- "BACE/analysis/outputs/figures_v3"
FONT <- "Liberation Sans"
INK <- "#1f1f1e"; INK2 <- "#52514e"; MUTED <- "#8a8984"; GRID <- "#ebeae6"
SL <- c("#91D1C2", "#4fb6a2", "#00A087", "#006b5a")      # NPG teal ramp (evidence side)
TYPE <- c("Structured metric" = SL[4], "PDF narrative passage" = SL[3], "PDF table row" = SL[1])
TYPE_FROM <- c("CSV metric" = "Structured metric", "PDF narrative" = "PDF narrative passage", "PDF table row" = "PDF table row")
DCOL <- c(factual_boundary_distortion = "#E64B35", evidence_conflation = "#7E6148",
          non_disclosure_statement = "#B09C85", inferential_inflation = "#F39B7F",
          unsupported_novelty = "#4DBBD5", contradiction = "#3B3B3B")
DNAME <- c(factual_boundary_distortion = "Factual boundary distortion", evidence_conflation = "Evidence conflation",
           non_disclosure_statement = "Non-disclosure statement", inferential_inflation = "Inferential inflation",
           unsupported_novelty = "Unsupported novelty", contradiction = "Contradiction")

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
      strip.text = element_text(size = 6, hjust = 0, colour = INK, face = "bold", margin = margin(b = 2)),
      legend.position = "none",
      legend.text = element_text(size = 5.5), legend.title = element_text(size = 5.8),
      legend.key.size = unit(6, "pt"),
      plot.tag = element_text(size = 8, face = "bold", family = FONT),
      plot.margin = margin(3, 6, 3, 3)
    )
}
no_ygrid <- theme(panel.grid.major.y = element_blank(), axis.line.y = element_blank(), axis.ticks.y = element_blank())
save_fig <- function(fig, name, h) {
  ggsave(file.path(OUT, paste0(name, ".pdf")), fig, width = 183, height = h, units = "mm", device = cairo_pdf)
  ggsave(file.path(OUT, paste0(name, ".png")), fig, width = 183, height = h, units = "mm", dpi = 300,
         device = ragg::agg_png, bg = "white")
  cat("written", name, "\n")
}

# ================================================================ ED Fig. 1 | sample composition
sec <- read_csv(file.path(D, "ed1a_sectors.csv"), show_col_types = FALSE) |>
  mutate(sector = fct_reorder(sector, eligible))
p1a <- ggplot(sec, aes(y = sector)) +
  geom_col(aes(x = eligible), fill = "#d3ece6", width = 0.66) +
  geom_col(aes(x = selected), fill = SL[3], width = 0.66) +
  geom_text(aes(x = eligible + 1, label = paste0(selected, " of ", eligible)), family = FONT, size = 5.5 / .pt,
            colour = INK, hjust = 0) +
  scale_x_continuous(limits = c(0, 58), breaks = seq(0, 50, 10), expand = c(0, 0)) +
  labs(x = "Companies (light, eligible; dark, selected)", y = NULL,
       subtitle = "250 of 600 companies eligible; 30 selected") +
  theme_bace() + no_ygrid + theme(plot.subtitle = element_text(size = 5.8, colour = INK2, margin = margin(b = 3)))

cty <- read_csv(file.path(D, "ed1b_countries.csv"), show_col_types = FALSE) |>
  mutate(country = fct_reorder(country, companies))
p1b <- ggplot(cty, aes(x = companies, y = country)) +
  geom_col(fill = SL[3], width = 0.66) +
  geom_text(aes(label = companies, x = companies + 0.15), family = FONT, size = 5.5 / .pt, hjust = 0, colour = INK) +
  scale_x_continuous(limits = c(0, 8), breaks = 0:7, expand = c(0, 0)) +
  labs(x = "Selected companies", y = NULL) + theme_bace() + no_ygrid

SICS <- c("Consumer Goods" = "CG", "Extractives & Minerals Processing" = "EM", "Financials" = "FN",
          "Food & Beverage" = "FB", "Health Care" = "HC", "Infrastructure" = "IF",
          "Renewable Resources & Alternative Energy" = "RR", "Resource Transformation" = "RT", "Services" = "SV",
          "Technology & Communications" = "TC", "Transportation" = "TR")
NAMEFIX <- c("Nestle" = "Nestlé", "D'IeterenGroup" = "D'Ieteren Group")
cov <- read_csv(file.path(D, "ed1c_source_coverage.csv"), show_col_types = FALSE) |>
  mutate(company = ifelse(company_name %in% names(NAMEFIX), NAMEFIX[company_name], company_name),
         sic = factor(SICS[primary_sics_sector], levels = sort(unname(SICS))))
heat_theme <- theme(panel.grid = element_blank(), axis.line = element_blank(), axis.ticks = element_blank(),
                    strip.text.x = element_text(size = 5.5, face = "bold", hjust = 0.5, colour = INK2),
                    panel.spacing.x = unit(1.5, "pt"), legend.position = "right",
                    legend.key.height = unit(5, "pt"), legend.key.width = unit(6, "pt"))
p1c <- ggplot(cov, aes(x = company, y = factor(year, levels = 2023:2015), fill = csv_valid_metrics)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  facet_grid(. ~ sic, scales = "free_x", space = "free_x") +
  scale_fill_gradient(low = "#e6f4f1", high = SL[4], limits = c(0, 300), breaks = c(0, 100, 200, 300),
                      name = "Valid metric\nvalues") +
  labs(x = NULL, y = "Source year", title = "Structured metrics with valid values, by source year") +
  theme_bace() + heat_theme +
  theme(axis.text.x = element_blank(), plot.title = element_text(size = 6, face = "bold", margin = margin(b = 1)))
p1d <- ggplot(cov |> filter(year <= 2022),
              aes(x = company, y = factor(year, levels = 2022:2015), fill = factor(pdf_valid_headers))) +
  geom_tile(colour = "white", linewidth = 0.3) +
  facet_grid(. ~ sic, scales = "free_x", space = "free_x") +
  scale_fill_manual(values = c(`1` = SL[1], `2` = SL[3], `3` = SL[4]), name = "Report\nPDFs") +
  labs(x = NULL, y = "Source year", title = "Annual and sustainability report PDFs, by source year") +
  theme_bace() + heat_theme +
  theme(axis.text.x = element_text(angle = 50, hjust = 1, vjust = 1, size = 5.2, colour = INK),
        strip.text.x = element_blank(), plot.title = element_text(size = 6, face = "bold", margin = margin(b = 1)))
sec <- sec |> mutate(sector = fct_reorder(paste0(as.character(sector), " (", SICS[as.character(sector)], ")"), eligible))
p1a <- p1a %+% sec
tagt <- theme(plot.tag = element_text(size = 8, face = "bold", family = FONT))
ed1 <- ((p1a + labs(tag = "a") + tagt) | (p1b + labs(tag = "b") + tagt)) /
  wrap_elements(full = (p1c + labs(tag = "c", y = NULL) + tagt) / (p1d + labs(tag = "d", y = NULL) + tagt) +
                  plot_layout(heights = c(9, 8))) +
  plot_layout(heights = c(1.15, 1.45))
save_fig(ed1, "ed_fig1", 165)

# ================================================================ ED Fig. 2 | evidence time windows
win <- read_csv(file.path(D, "ed2a_windows.csv"), show_col_types = FALSE) |>
  mutate(kind = case_when(pdf_admissible ~ "Metrics and report PDFs", metric_admissible ~ "Metrics only",
                          TRUE ~ "Not admissible"),
         lab = ifelse(kind == "Not admissible", "", ifelse(target_year == source_year, "t", paste0("t−", target_year - source_year))))
p2a <- ggplot(win, aes(x = factor(source_year), y = factor(target_year, levels = 2023:2019), fill = kind)) +
  geom_tile(colour = "white", linewidth = 0.6) +
  geom_text(aes(label = lab, colour = kind == "Metrics and report PDFs"), family = FONT, size = 5 / .pt) +
  scale_fill_manual(values = c("Metrics and report PDFs" = SL[3], "Metrics only" = SL[1],
                               "Not admissible" = "#f2f1ed"), name = NULL) +
  scale_colour_manual(values = c(`TRUE` = "white", `FALSE` = INK), guide = "none") +
  guides(fill = guide_legend(ncol = 2)) +
  labs(x = "Source year", y = "Target reporting year") + theme_bace() +
  theme(panel.grid = element_blank(), axis.line = element_blank(), legend.position = "bottom",
        legend.margin = margin(t = -2))

lag <- read_csv(file.path(D, "ed2b_supplied_by_lag.csv"), show_col_types = FALSE) |>
  mutate(lagl = factor(ifelse(lag == 0, "t", paste0("t−", lag)), levels = c("t", paste0("t−", 1:4))),
         type = factor(TYPE_FROM[type], levels = rev(names(TYPE))))
lag_tot <- lag |> group_by(lagl) |> summarise(cards = sum(cards), .groups = "drop")
p2b <- ggplot(lag, aes(x = lagl, y = cards / 1000, fill = type)) +
  geom_col(width = 0.68, colour = "white", linewidth = 0.3) +
  geom_text(data = lag_tot, aes(x = lagl, y = cards / 1000 + 0.25, label = comma(cards)), inherit.aes = FALSE,
            family = FONT, size = 5.3 / .pt, colour = INK, vjust = 0) +
  scale_fill_manual(values = TYPE, name = NULL, breaks = names(TYPE)) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
  guides(fill = guide_legend(ncol = 2)) +
  labs(x = "Source year relative to target year", y = "Supplied evidence cards (thousands)") +
  theme_bace() + theme(panel.grid.major.x = element_blank(), legend.position = "bottom", legend.margin = margin(t = -2))

cnt <- read_csv(file.path(D, "ed2c_cards_per_case.csv"), show_col_types = FALSE) |>
  mutate(type = TYPE_FROM[type],
         bin = factor(case_when(cards == 10 ~ "10", cards >= 5 ~ "5–9", cards >= 1 ~ "1–4", TRUE ~ "0"),
                      levels = c("0", "1–4", "5–9", "10"))) |>
  group_by(type, bin) |> summarise(cases = sum(cases), .groups = "drop") |>
  group_by(type) |> mutate(share = 100 * cases / sum(cases)) |> ungroup() |>
  mutate(type = factor(type, levels = rev(names(TYPE))))
full <- cnt |> filter(bin == "10")
p2c <- ggplot(cnt, aes(y = type, x = share, fill = bin)) +
  geom_col(width = 0.62, position = position_stack(reverse = TRUE), colour = "white", linewidth = 0.3) +
  geom_text(data = full, aes(y = type, x = 98.5, label = paste0(fmt1(share), "% with 10")), inherit.aes = FALSE,
            family = FONT, size = 5.3 / .pt, colour = "white", hjust = 1) +
  scale_fill_manual(values = c("0" = SL[1], "1–4" = SL[2], "5–9" = SL[3], "10" = SL[4]),
                    name = "Cards per case (maximum 10)") +
  scale_x_continuous(limits = c(0, 100.5), breaks = seq(0, 100, 25), expand = c(0, 0)) +
  guides(fill = guide_legend(title.position = "top", nrow = 1)) +
  labs(x = "Share of the 1,798 evaluated cases (%)", y = NULL) + theme_bace() + no_ygrid +
  theme(legend.position = "bottom", legend.margin = margin(t = -2), axis.text.y = element_text(size = 5.8, colour = INK))
fmt1 <- function(x) sprintf("%.1f", x)
ed2 <- (p2a | p2b | p2c) + plot_layout(widths = c(1.05, 0.95, 1)) + plot_annotation(tag_levels = "a") &
  theme(plot.tag = element_text(size = 8, face = "bold", family = FONT))
save_fig(ed2, "ed_fig2", 78)

# ================================================================ ED Fig. 3 | diagnoses by task
short <- c(
  "E1-1_transition_plan" = "E1-1 Transition plan", "E1-3_actions_resources" = "E1-3 Climate actions and resources",
  "E1-4_targets" = "E1-4 Climate targets", "E1-6_ghg_emissions" = "E1-6 GHG emissions",
  "S1-1_workforce_policies" = "S1-1 Workforce policies", "S1-4_workforce_actions_resources" = "S1-4 Workforce actions",
  "S1-5_workforce_targets" = "S1-5 Workforce targets", "S1-14_health_safety_metrics" = "S1-14 Health and safety metrics",
  "G1-1_business_conduct_policies" = "G1-1 Business conduct policies", "G1-2_supplier_relationships" = "G1-2 Supplier relationships",
  "G1-3_anti_corruption_controls" = "G1-3 Anti-corruption controls", "G1-4_corruption_bribery_incidents" = "G1-4 Corruption and bribery incidents")
topic_name <- c(E = "Climate change (E1)", S = "Own workforce (S1)", G = "Business conduct (G1)")
seg_order <- c("factual_boundary_distortion", "evidence_conflation", "non_disclosure_statement",
               "inferential_inflation", "unsupported_novelty", "contradiction")
d3 <- read_csv(file.path(D, "ed3_diagnosis_by_task.csv"), show_col_types = FALSE) |>
  mutate(task = factor(short[task_id], levels = rev(short)),
         topic = factor(topic_name[substr(task_id, 1, 1)], levels = topic_name[c("E", "S", "G")]),
         label = factor(label, levels = seg_order))
tot <- d3 |> group_by(task, topic) |> summarise(n = sum(dcs), .groups = "drop")
tops <- d3 |> filter(top_in_task) |> mutate(tlab = ifelse(label == "factual_boundary_distortion", "", "◆"))
p3 <- ggplot(d3, aes(y = task, x = share_pct, fill = label)) +
  geom_col(width = 0.7, position = position_stack(reverse = TRUE), colour = "white", linewidth = 0.2) +
  geom_text(data = d3 |> filter(label %in% c("factual_boundary_distortion", "evidence_conflation")) |>
              group_by(task) |> arrange(label, .by_group = TRUE) |>
              mutate(x = cumsum(share_pct) - share_pct / 2) |> ungroup(),
            aes(x = x, y = task, label = sprintf("%.0f", share_pct)), inherit.aes = FALSE,
            family = FONT, size = 5.2 / .pt, colour = "white", fontface = "bold") +
  geom_text(data = tot, aes(x = 101, y = task, label = comma(n)), inherit.aes = FALSE, family = FONT,
            size = 5.2 / .pt, colour = INK2, hjust = 0) +
  geom_text(data = tot |> filter(topic == levels(topic)[1]) |> slice(1), aes(x = 101, y = Inf, label = "n"),
            inherit.aes = FALSE, family = FONT, size = 5.2 / .pt, colour = INK2, fontface = "bold", hjust = 0, vjust = -0.4) +
  facet_grid(topic ~ ., scales = "free_y", space = "free_y", switch = "y") +
  scale_fill_manual(values = DCOL, labels = DNAME, breaks = seg_order, name = NULL) +
  scale_x_continuous(breaks = seq(0, 100, 20), expand = c(0, 0)) +
  coord_cartesian(xlim = c(0, 100), clip = "off") +
  labs(x = "Share of unsupported disclosure claims in the task (%)", y = NULL) +
  guides(fill = guide_legend(nrow = 1)) +
  theme_bace() + no_ygrid +
  theme(legend.position = "top", legend.justification = "left", legend.margin = margin(b = 6),
        axis.text.y = element_text(size = 5.8, colour = INK),
        strip.placement = "outside", strip.text.y.left = element_text(angle = 90, face = "bold", hjust = 0.5, size = 5.8),
        panel.spacing.y = unit(4, "pt"), plot.margin = margin(3, 34, 3, 3))
save_fig(p3, "ed_fig3", 85)
