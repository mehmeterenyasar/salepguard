# Modelling slides (content for Mehmet to merge into `salepguard_slides.md`)

Numbers come from `outputs/models/metrics.csv`, `range_change.csv` and `docs/results_summary.md`.

---

## Data: biased records, handled explicitly

- 24,557 cleaned records, 20 salep orchid species; 1 record per 2.5′ cell (thinning)
- Records are mostly from Greece and Cyprus; Turkey has < 15 % for most species
- ~65 % of Turkish records lost to iNaturalist coordinate obscuring; east Anatolia and *Dactylorhiza* missing
- **Target-group background**: 5,446 cells with any orchid record, so the model learns "species vs where orchid recorders went"

Figure: `outputs/models/figures/sampling_bias.png`

---

## Method: tuned, bias-corrected MaxEnt with honest validation

- 6 climate variables, |r| ≤ 0.65, VIF ≤ 3.1: temperature seasonality, cold-month minimum, annual and summer rain, wet-quarter temperature, isothermality
- **Spatial block CV**: 200 km blocks, 5 folds; train in some regions, test in others
- Tuning per species: 3 feature sets × 4 regularisation levels, chosen by lowest omission, then AUC
- 20 bootstrap refits per species give a per-cell uncertainty, MESS flags extrapolation, and a bias-aware null model tests significance

Figure: `outputs/models/figures/correlation_heatmap.png` (small) + method diagram

---

## Results / validation: honest numbers

- Spatial AUC 0.72 on average (0.58–0.87), Boyce 0.58; random CV would claim 0.76
- All 20 species beat a bias-aware null model (p = 0.02)
- 2 species (*Anacamptis morio*, *A. pyramidalis*) have spatial AUC < 0.6 and are **excluded from the risk index**
- 2041–2060: the median species gains area with dispersal but **loses without dispersal** (−9 % SSP2-4.5, −14 % SSP5-8.5); *Himantoglossum robertianum*, *Orchis anatolica* and *Ophrys lutea* lose 35–89 %

Figures: `spatial_vs_random_cv.png`, `richness_map.png`, `range_change.png` (or `future_change_map.png`)
