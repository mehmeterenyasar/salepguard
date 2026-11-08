# modeling/ — final species distribution models (modelling lead)

This folder belongs to the modelling lead. The data/software side does not edit it.

## Inputs (shared contract, `data/processed/`)

| File | Notes |
|---|---|
| `occurrences_clean.csv` | `species, species_slug, gbifID, decimalLongitude, decimalLatitude, year, countryCode, basisOfRecord, coordinateUncertaintyInMeters, datasetKey` |
| `background_targetgroup.csv` | all cleaned Orchidaceae records (target-group background) |
| `species_list.csv` | `selected == True` species are the ones to model |
| `covariates/*.tif` | bio01–bio19 + elevation, EPSG:4326, 2.5′, lon 19–45, lat 34–43 (624 × 216) — **not in git** (WorldClim licence); build with `python run_all.py --only worldclim` |
| `covariates_future/ssp245_2041-2060/*.tif`, `ssp585_…` | 3-GCM ensemble mean (+ `*_gcm_sd.tif`) |
| `turkey_mask.tif` | 1 = Turkey |

## Outputs expected in `outputs/models/` (same grid)

- `{species_slug}_suitability_mean.tif`, `{species_slug}_suitability_sd.tif`, `{species_slug}_binary.tif`
- `{species_slug}_future_ssp245_mean.tif` (+ `_ssp585_`)
- `richness_mean.tif`, `richness_sd.tif`
- `metrics.csv`: `species_slug, n_train_cells, auc_mean, auc_sd, tss_mean, tss_sd, cbi_mean, threshold, threshold_method, top_variables, cv_method`
- `figures/*.png`; your sections of `docs/methods.md` and `docs/limitations.md`

Check them with:

```bash
python scripts/validate_outputs.py outputs/models
```

As soon as `outputs/models/metrics.csv` exists, the risk index and dashboard switch from the baseline
to the final model (`python run_all.py --from risk`).

## How to run the final model

```bash
python run_all.py --only worldclim          # covariates (not in git), once
python modeling/run_all_models.py           # everything below, ~25 min on 8 cores
```

| Step | Script | Output |
|---|---|---|
| contract check, bias, thinning, variables (|r| ≤ 0.7, VIF ≤ 10) | `prepare.py` | `variables.txt`, `outputs/models/tables/`, bias + correlation figures |
| block size from covariate variograms (capped 100–200 km) | `blocksize.py` | `block_size_km.txt` |
| tuning (fc L/LQ/LQH × rm 0.5/1/2/4) under spatial block CV, random CV, 20 bootstraps, future projection | `run_models.py` | `cache/` |
| bias-aware null model (3 species) | `null_model.py` | `cache/null_model.csv` |
| contract rasters, richness, MESS, `metrics.csv`, `range_change.csv` | `assemble.py` | `outputs/models/` |
| figures | `figures.py` | `outputs/models/figures/` |
| results summary | `results_summary.py` | `docs/results_summary.md` |

Shared helpers (metrics, blocks, MESS) are in `sdm.py`. Package versions: `sessionInfo.txt`. Seed 42.
Method details: `docs/methods.md` §5a.
