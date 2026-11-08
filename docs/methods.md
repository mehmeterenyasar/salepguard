# Methods

> Sections marked **[pipeline]** were written by the data/software lead (Mehmet). Sections marked
> **[modelling]** belong to the statistics/modelling lead and are filled in from `modeling/`.

## 1. Study design and shared grid [pipeline]

- CRS EPSG:4326, WorldClim 2.1 native 2.5 arc-minute grid (1/24°, ≈4.6 km). All layers use an exact
  window of the global WorldClim grid, so no climate resampling is needed.
- **Training extent** (Eastern Mediterranean): lon 19–45°E, lat 34–43°N (624 × 216 cells), covering
  Greece, Cyprus, Turkey, the southern Balkans and part of the Caucasus. Using a larger extent than
  Turkey gives more records and samples more of each species' climatic niche, reducing truncation.
- **Reporting extent**: Turkey (geoBoundaries ADM0, rasterised by cell centre).
- Display layers are aggregated ×2 (5 arc-min, ≈9 km) for responsible display.

## 2. Occurrence data [pipeline]

One GBIF query for **all Orchidaceae** (familyKey 7689) in the training extent
(`hasCoordinate=true`, `hasGeospatialIssue=false`, `occurrenceStatus=PRESENT`). Salep genera
(`config.yaml: taxa.salep_genera`) provide presences; all orchids provide the **target-group
background**, which has a similar observer/sampling bias to the presences (Phillips et al. 2009).

Cleaning (Python re-implementation of CoordinateCleaner tests; Zizka et al. 2019), applied identically
to presences and background; counts per step are in `data/processed/cleaning_report.csv`:

1. drop missing coordinates; `basisOfRecord` FOSSIL_SPECIMEN / LIVING_SPECIMEN
2. drop missing year (counted) and `year < 1970` (aligns with the WorldClim 1970–2000 baseline)
3. drop `coordinateUncertaintyInMeters > 5000` (missing values kept and counted)
4. zero coordinates, equal latitude/longitude
5. within 1 km of country centroids (Natural Earth) or Turkish province centroids (geoBoundaries);
   within 10 km of national capitals; GBIF headquarters
6. points in cells without WorldClim data (sea)
7. presences only: duplicate species + coordinates

Names come from the GBIF backbone `species` field, so subspecies/varieties are merged at species
level. Institution (herbarium/museum) coordinates are **not** tested (no open gazetteer was wired in;
listed in limitations).

**Species selection:** ≥ 50 unique 2.5′ cells in the training extent **and** ≥ 15 unique cells in
Turkey after cleaning (`config.yaml: species_selection`).

## 3. Harvest-pressure proxy [pipeline]

Salep collection is concentrated in accessible areas near villages. We use two open proxies:

- **Population**: WorldPop 2020 1 km UN-adjusted density, averaged per 2.5′ cell, `log1p`, min–max to 0–1
  within Turkey.
- **Accessibility**: travel time to the nearest city in 2015 (Weiss et al. 2018), averaged per cell,
  `log1p`, min–max, inverted (short travel time → high pressure).
- `pressure_index = 0.5 · population + 0.5 · accessibility`, re-scaled 0–1. The weights are an
  **assumption**; we test 0.7/0.3 and 0.3/0.7 (section 6). The two components are correlated
  (Pearson r ≈ 0.69 across Turkish cells).

This is a proxy for *potential* harvest pressure, not observed harvest.

## 4. Protected areas [pipeline]

WDPA (Protected Planet, November 2026 public release) and OpenStreetMap are combined (union). The
public WDPA release for Turkey contains only 17 sites (most national designations are not publicly
shared), so OpenStreetMap supplies most polygons (`boundary=protected_area|national_park`,
`leisure=nature_reserve`; `protect_class` > 6 dropped). A cell is protected if its centre falls
inside a polygon. The source actually used is recorded in `DATA_MANIFEST.md`.

## 5. Species distribution models

### 5a. Final model [modelling]

Code: `modeling/`; one command reruns everything: `python modeling/run_all_models.py`.
Python 3.12, `elapid` 1.0.4, `scikit-learn` 1.9.1, `numpy` 2.5.4, `scipy` 1.18.1, `rasterio` 1.5.2,
`pandas` 3.1.1, `matplotlib` 3.11.2 (full list: `modeling/sessionInfo.txt`). Seed 42 everywhere.
The plan was written for R (`maxnet`, `ENMeval`, `blockCV`, `ecospat`). None of those packages were
installed on the modelling machine on the night, so the same procedures were written out in Python;
every step below says which R function it mirrors. The code is short and readable in `modeling/sdm.py`.

**Sampling bias and background.** Cleaned Orchidaceae records are heavily concentrated in Greece and
Cyprus and along the Aegean/Mediterranean coasts (`outputs/models/figures/sampling_bias.png`,
`outputs/models/tables/background_by_country.csv`). For that reason we use a **target-group background**
(Phillips et al. 2009): all 5,446 unique valid 2.5′ cells with a cleaned Orchidaceae record, including the
focal species' own cells (standard target-group design). Target-group background makes the model contrast
the species with *where orchid recorders went*, not with the whole landscape, so the recording bias
largely cancels out. It reduces bias but cannot remove gaps where nobody recorded any orchid (eastern
Anatolia), see limitations.

**Thinning.** One presence per 2.5′ (~4.6 km) cell; background also de-duplicated by cell. Counts before
and after thinning per species: `outputs/models/tables/species_records.csv`. (A 10 km thinning
sensitivity run was planned as optional and was not done.)

**Variables.** Pearson correlation and VIF of bio01–bio19 + elevation on 10,000 random land cells of the
training extent (`tables/correlation_matrix.csv`, `figures/correlation_heatmap.png`). Greedy selection
along a biologically ordered list (temperature seasonality, cold limit, annual and summer water supply,
terrain, then the rest), keeping a variable only if |r| ≤ 0.7 with all kept ones, then dropping the
largest VIF until all VIF ≤ 10 (VIF = diag(R⁻¹), as in `usdm::vif`). Result, common to all species:
**bio04** (temperature seasonality), **bio06** (min. temperature of coldest month), **bio12** (annual
precipitation), **bio18** (precipitation of warmest quarter), **bio08** (mean temperature of wettest
quarter), **bio03** (isothermality); max |r| = 0.65, max VIF = 3.1 (`tables/selected_variables_vif.csv`).
Elevation was dropped because it is strongly correlated with bio06 (|r| > 0.7); bio06 is the more
direct physiological limit for winter-green tuberous orchids. Compared with the baseline set (bio01,
bio12, bio04, bio19, bio02, bio08) we replace mean annual temperature by the cold limit (bio06), winter
precipitation by summer precipitation (bio18, summer drought during tuber dormancy) and diurnal range
by isothermality. Both sets have low VIF; ours was chosen for interpretability, not performance.

**Model.** MaxEnt (`elapid.MaxentModel`, cloglog output, clamping on; equivalent in intent to `maxnet`,
Phillips et al. 2017). Presence = thinned species cells, background = target-group cells.

**Spatial block cross-validation** (mirrors `blockCV::cv_spatial` + `cv_spatial_autocor`; Valavi et al.
2019). Block size from covariate autocorrelation: an exponential semivariogram was fitted to each
selected covariate on 3,000 random cells (`modeling/blocksize.py`,
`tables/block_size_variogram.csv`). The median effective range was ~854 km (bio08 463 km – bio04 at the
5,000 km bound), i.e. larger than a third of the 26° × 9° extent; blocks that large would leave whole
countries in a single fold. Following the plan we capped the block size at **200 km**. Square blocks are
assigned at random to 5 folds; of 200 random assignments the one with the most even number of presences
per fold is kept (the "iteration" idea of `cv_spatial`). Presence and background points in the same block
are always in the same fold.

**Tuning** (mirrors `ENMeval` 2.x, Muscarella et al. 2014; Kass et al. 2021). Feature classes L, LQ, LQH ×
regularisation multiplier rm 0.5, 1, 2, 4 (12 settings), each evaluated on the 5 spatial folds.
Selection rule (sequential): lowest mean 10 % training-presence omission rate (OR10), ties broken by
highest mean validation AUC. Chosen `fc`/`rm` per species are in `metrics.csv`; all 12 settings × species
in `tables/tuning_all.csv`.

**Metrics** (per fold on the held-out block fold, then mean ± SD over folds):
- AUC, presence vs background (`roc_auc_score`); with background instead of absences this measures
  discrimination from the recording effort, not from true absences.
- TSS at the maxSSS threshold. The threshold is computed on the *training* folds and applied to the test
  fold (more honest than optimising it on the test fold, as the baseline did).
- Continuous Boyce index (Hirzel et al. 2006), moving window of 10 % of the prediction range, 101 windows,
  Spearman correlation, repeated P/E values removed (as in `ecospat.boyce`).
- OR10: share of test presences below the 10th percentile of training-presence predictions.
- `auc_random_cv`: AUC with the same fc/rm under ordinary random 5-fold CV, to show how much random CV
  inflates performance when records are spatially clustered.
- Null model (Raes & ter Steege 2007), bias-aware variant: n random cells drawn from the target-group
  background (same bias, no species signal), modelled and evaluated in the same way; p = (k + 1)/(N + 1)
  with k null AUCs ≥ the observed one, N = 49 null models per species, so the smallest possible p is 0.02
  (`modeling/null_model.py`). Run for all 20 species.
- **Quality flag** `include_in_index = FALSE` if CBI < 0, spatial AUC < 0.6 or null-model p > 0.05; the
  reason is in `exclusion_reason`. The risk index uses this flag.

**Bootstrap uncertainty.** 20 refits per species with presences resampled with replacement (background
fixed), selected fc/rm, predicted to the whole grid for current and both future climates. Mean and SD per
cell are the `_suitability_mean` / `_suitability_sd` outputs. Each replicate is also thresholded at its
own maxSSS, and the per-replicate binary maps give the richness SD.

**Thresholding.** Main threshold maxSSS (maximum sensitivity + specificity, presence vs background) on
the bootstrap-mean surface at the training cells. maxSSS is recommended for presence-only data because
it does not depend on prevalence (Liu et al. 2013). For comparison, the 10 % training-presence
threshold (`threshold_p10`) and the share of Turkey suitable under each threshold are reported in
`metrics.csv`.

**Richness.** `richness_mean` = sum of the 20 binary maps; `richness_prob_mean` = sum of suitabilities;
`richness_sd` = SD over the 20 bootstrap replicates of the summed replicate binaries. All 20 species are
included in richness; `include_in_index` only affects the risk index.

**Extrapolation (MESS, Elith et al. 2010).** For each species, the reference set is its presence +
background cells. MESS is computed for the current climate over the whole extent and for each SSP
(`_mess.tif`, `_mess_ssp245.tif`, `_mess_ssp585.tif`); negative values = at least one variable outside
the reference range. MaxEnt predictions are clamped to the training range of each feature, so negative-MESS
cells get a constant extrapolated response, not a real prediction.

**Climate change.** The bootstrap models are projected onto the 3-GCM ensemble mean (MPI-ESM1-2-HR,
IPSL-CM6A-LR, MIROC6) for SSP2-4.5 and SSP5-8.5, 2041–2060. Future binary = future mean ≥ the current
maxSSS threshold. In Turkey we report current and future suitable area, loss, kept, gain (km², cell area
= (res·111.32 km)²·cos(lat)) and % change under **full dispersal** (all future suitable cells) and **no
dispersal** (future ∩ current), `range_change.csv`. To separate signal from extrapolation the % change is
also recomputed using only analog cells (MESS ≥ 0), and the share of the future suitable area that falls
in non-analog climate is reported. The inter-GCM SD of the covariates (`covariates_future/*/*_gcm_sd.tif`)
is a separate uncertainty source that is not propagated into the suitability SD (only the ensemble mean
was projected).

### 5b. Baseline / fallback model [pipeline]

Python `elapid` MaxEnt (linear + quadratic + hinge features, β = 1.5, cloglog output):

- presences: one per occupied 2.5′ cell; background: up to 10 000 target-group cells
- covariates: greedy selection from an ecologically ordered list of bio01–bio19 + elevation, keeping a
  variable only if |Pearson r| ≤ 0.7 with all already-kept variables (computed on background)
- **random** 5-fold CV → AUC, TSS (max sensitivity + specificity), continuous Boyce index
- threshold: maximum sensitivity + specificity on pooled CV predictions
- 10 bootstrap refits (presences resampled with replacement) → mean and SD suitability
- future: each bootstrap model is projected onto the 3-GCM ensemble mean for SSP2-4.5 and SSP5-8.5,
  2041–2060

Random CV is optimistic under spatial autocorrelation; the baseline is a fallback and a robustness
check, not the main inference.

## 6. SalepGuard Priority Index [pipeline]

For species *s* and Turkish cell *i*:

```
harvest_risk_s,i     = suitability_s,i × pressure_i
unprotected_risk_s,i = harvest_risk_s,i × (1 − protected_i)
priority_i           = Σ_s w_s · unprotected_risk_s,i      (w_s = 1 by default), scaled to 0–1
```

Equal species weights are used because no consistent, citable species-level salep-use or national
threat weighting was available; `config.yaml: risk.species_weights` allows weights.

**Uncertainty.** First-order (delta-method) propagation of the per-species bootstrap SDs, treating
species as independent and pressure/protection as fixed:

```
sd(priority_i) = sqrt( Σ_s (w_s · pressure_i · (1 − protected_i))² · sd_s,i² )
```

Independence ignores positive covariance between co-occurring species' errors, so this SD is likely
an **underestimate**. The coefficient of variation `CV = sd / priority` is reported.

**Hotspots.** Top 5 % of Turkish cells by priority. **Robust hotspot** = hotspot whose one-sided 95 % lower bound (`priority − 1.645 · sd`) is still above the top-5 % threshold. (A simple CV < 0.5 rule was tried first but flagged every hotspot as robust, because the propagated SD is small relative to the index.)

**Sensitivity analysis.** Hotspot sets (top 2.5 %, 5 %, 10 %) are recomputed under the three pressure
weightings and with thresholded (binary) instead of continuous suitability; the Jaccard similarity to
the reference set is reported in `outputs/risk/sensitivity_jaccard.csv`.

**Climate change.** The index is recomputed with future suitability, holding pressure and protection
fixed (an explicit simplification). Per-cell counts of species losing or gaining suitable status
and per-species suitable-area change (km²) are reported.

**Province ranking.** For each of the 81 provinces: mean and max priority, number of (robust) hotspot
cells, hotspot area, mean pressure, mean richness, share of suitable area protected, and the three
species contributing most unprotected risk.

**Protection gap.** For each species: share of its suitable area (thresholded) in Turkey inside
protected areas, compared with the share of Turkey that is protected. Cell areas account for latitude.

## 7. Dashboard [pipeline]

All rasters are pre-rendered (aggregated to 5′, clipped to Turkey, reprojected to Web Mercator,
viridis/cividis/magma/PuOr colour maps) into PNG overlays in `app/layers/`, so the Streamlit app only
reads small files. Raw occurrence points are never displayed.

## References (methods)

- Phillips, S.J. et al. (2009) Sample selection bias and presence-only distribution models: implications for background and pseudo-absence data. *Ecological Applications* 19: 181–197.
- Zizka, A. et al. (2019) CoordinateCleaner: standardized cleaning of occurrence records from biological collection databases. *Methods in Ecology and Evolution* 10: 744–751.
- Hirzel, A.H. et al. (2006) Evaluating the ability of habitat suitability models to predict species presences. *Ecological Modelling* 199: 142–152.
- Weiss, D.J. et al. (2018) *Nature* 553: 333–336.
- Fick, S.E. & Hijmans, R.J. (2017) *Int. J. Climatol.* 37: 4302–4315.

Final model [modelling] (checked against Crossref, 8 Nov 2026):

- Elith, J. et al. (2010) The art of modelling range-shifting species. *Methods in Ecology and Evolution* 1(4): 330–342. doi:10.1111/j.2041-210X.2010.00036.x
- Kass, J.M. et al. (2021) ENMeval 2.0: redesigned for customizable and reproducible modeling of species' niches and distributions. *Methods in Ecology and Evolution* 12(9): 1602–1608. doi:10.1111/2041-210X.13628
- Liu, C., White, M. & Newell, G. (2013) Selecting thresholds for the prediction of species occurrence with presence-only data. *Journal of Biogeography* 40(4): 778–789. doi:10.1111/jbi.12058
- Muscarella, R. et al. (2014) ENMeval: an R package for conducting spatially independent evaluations and estimating optimal model complexity for Maxent ecological niche models. *Methods in Ecology and Evolution* 5(11): 1198–1205. doi:10.1111/2041-210X.12261
- Phillips, S.J. et al. (2017) Opening the black box: an open-source release of Maxent. *Ecography* 40(7): 887–893. doi:10.1111/ecog.03049
- Raes, N. & ter Steege, H. (2007) A null-model for significance testing of presence-only species distribution models. *Ecography* 30(5): 727–736. doi:10.1111/j.2007.0906-7590.05041.x
- Radosavljevic, A. & Anderson, R.P. (2014) Making better Maxent models of species distributions: complexity, overfitting and evaluation. *Journal of Biogeography* 41(4): 629–643. doi:10.1111/jbi.12227
- Valavi, R. et al. (2019) blockCV: an R package for generating spatially or environmentally separated folds for k-fold cross-validation of species distribution models. *Methods in Ecology and Evolution* 10(2): 225–232. doi:10.1111/2041-210X.13107
- Anderson, C.B. (2023) elapid: Species distribution modeling tools for Python. *Journal of Open Source Software* 8(84): 4930. doi:10.21105/joss.04930


