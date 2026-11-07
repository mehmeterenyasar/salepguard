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

_To be completed by the modelling lead: thinning, bias analysis, bias-corrected MaxEnt settings,
spatial block cross-validation, bootstrap, thresholding, metrics, future projections._

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

(TODO: verify all bibliographic details before submission.)
