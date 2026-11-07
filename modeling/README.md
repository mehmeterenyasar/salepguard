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
