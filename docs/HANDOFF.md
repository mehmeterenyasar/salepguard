# SalepGuard — status and handoff (2026-11-07, evening)

Written for **Sena** (modelling lead) and her Claude Code session. Read this first, then
[`modeling/README.md`](../modeling/README.md) for the exact input/output contract.

**Deadline:** 8 Nov 2026, 11:00 EET (12:00 TRT). Team target: **11:00 TRT**.

## 1. What exists now

| Area | Status | Where |
|---|---|---|
| Public repo (MIT) | done | https://github.com/mehmeterenyasar/salepguard |
| Live dashboard | done (baseline model) | https://salepguard.streamlit.app |
| Data contract (`data/processed/`) | done, frozen | see section 2 |
| GBIF download with DOI | done | https://doi.org/10.15468/dl.mfzrky (62,435 Orchidaceae records) |
| Baseline SDM (Python `elapid` MaxEnt) | done, 20 species | `outputs/baseline/` |
| Risk / priority index, uncertainty, sensitivity, climate, provinces, protection gap | done | `outputs/risk/` |
| Figures for README/slides | done | `outputs/figures/` |
| README, data sources, AI usage, pipeline parts of methods/limitations | done | `README.md`, `docs/` |
| Slide skeleton (Marp), video script, Devpost text, checklist | drafted | `slides/`, `docs/devpost_submission.md`, `docs/submission_checklist.md` |
| **Final model (bias-corrected MaxEnt, spatial block CV, bootstrap)** | **TODO: Sena** | `modeling/` → `outputs/models/` |
| Modelling sections of methods/limitations/AI usage | **TODO: Sena** | marked `[modelling]` in `docs/` |
| Video, slide PDF, Devpost submission | TODO (both) | |

## 2. Data contract (inputs for the final model)

- Grid: EPSG:4326, WorldClim 2.5′ (1/24°). Training extent lon 19–45, lat 34–43 → **624 × 216** cells.
  Reporting: Turkey (`turkey_mask.tif`).
- `occurrences_clean.csv`: 24,557 salep-genus records, 108 species, already cleaned (fossil/living,
  year ≥ 1970, uncertainty ≤ 5 km, centroids, capitals, sea, duplicates). **Thinning and bias analysis are
  your job.**
- `background_targetgroup.csv`: 21,908 cleaned records of all Orchidaceae (target-group background).
- `species_list.csv`: **20 species selected** (≥ 50 cells in extent and ≥ 15 cells in Turkey):
  *Anacamptis* (coriophora, laxiflora, morio, papilionacea, pyramidalis, sancta), *Ophrys* (fusca, lutea,
  reinholdii, scolopax, speculum, sphegodes, tenthredinifera, vicina), *Orchis* (anatolica, italica,
  purpurea), *Neotinea tridentata*, *Himantoglossum robertianum*, *Serapias vomeracea*.
- `covariates/` (bio01–bio19, elevation) and `covariates_future/{ssp245,ssp585}_2041-2060/` (3-GCM mean of
  MPI-ESM1-2-HR, IPSL-CM6A-LR and MIROC6, plus `*_gcm_sd.tif`). **These are not in git** because the
  WorldClim licence forbids redistribution. Build them locally:
  ```bash
  pip install -r requirements-dev.txt
  python run_all.py --only worldclim     # ~3.5 GB download, ~5 min
  ```
- Pressure, protected areas, mask and province layers are in `data/processed/` and described in
  `DATA_MANIFEST.md`.

## 3. Outputs the dashboard expects from you (`outputs/models/`)

Use the same grid and file names as `outputs/baseline/` (that folder is a working example):

- `{slug}_suitability_mean.tif`, `{slug}_suitability_sd.tif` (0–1), `{slug}_binary.tif` (0/1)
- `{slug}_future_ssp245_mean.tif` and `{slug}_future_ssp585_mean.tif`
- `richness_mean.tif`, `richness_sd.tif`
- `metrics.csv` with the columns `species_slug, n_train_cells, auc_mean, auc_sd, tss_mean, tss_sd, cbi_mean,
  threshold, threshold_method, top_variables, cv_method`
- `figures/*.png` (response curves, variable importance, example maps)

Then:

```bash
python scripts/validate_outputs.py outputs/models   # must print OK
python run_all.py --from risk                       # risk index, baseline-vs-final comparison, web layers, figures
```

As soon as `outputs/models/metrics.csv` exists, the risk index and dashboard switch to the final model
automatically, and `outputs/risk/model_comparison.csv` is produced for the robustness slide. Keep files
under 50 MB each (current baseline files are about 0.2–0.5 MB).

**Git rules:** you own `modeling/` and `outputs/models/`. Mehmet does not edit them. Please don't edit
`src/`, `app/` or `data/processed/` without telling Mehmet. Pull before you push.

## 4. Baseline results (to beat or confirm)

- Random 5-fold CV, mean of 20 species: **AUC 0.79** (0.64–0.91), **TSS 0.49**, **Boyce 0.85**.
  Weakest: *Anacamptis pyramidalis* (AUC 0.64) and *Neotinea tridentata* (0.66). Strongest:
  *A. sancta* and *O. vicina* (0.91 and 0.90).
- Variables kept (|r| ≤ 0.7): bio01, bio12, bio04, bio19, bio02, bio08.
- Only **4.4 %** of the area suitable for salep orchids is protected, the same as Turkey's protected share
  (4.4 %). For the median species it is 6.6 %.
- Top provinces by mean priority: İstanbul, İzmir, Yalova, Aydın, Hatay. There are 2,339 hotspot cells,
  of which 1,873 are robust (still top 5 % at `priority − 1.645·SD`).
- Hotspot Jaccard: 0.88–0.89 across pressure weights, 0.66–0.70 for binary vs continuous suitability.
- Climate change (baseline) varies a lot between species (−97 % to +200 % suitable area). This is likely
  extrapolation; please check with clamping/MESS in the final model.

## 5. Known issues worth your attention

1. **Sampling bias / missing east.** About 65 % of Turkish records (2,135 of 3,301) are iNaturalist
   coordinates obscured by ~28 km and were removed. Eastern Anatolia and *Dactylorhiza* are
   under-represented, and no *Dactylorhiza* species passed the selection rule. The bias analysis and
   spatial thinning should address and document this.
2. **Random CV is optimistic.** Spatial block CV in the final model is the main validation.
3. **Pressure proxy rewards cities** (İstanbul ranks first). This is a pipeline issue; Mehmet may add a
   rural-access variant.
4. **Protected areas:** the public WDPA release (Nov 2026) has only 17 Turkish sites, so the layer is a
   WDPA ∪ OpenStreetMap union.
5. Literature references and the MAP licence are marked `TODO: verify`.

## 6. How to run things

```bash
git clone https://github.com/mehmeterenyasar/salepguard && cd salepguard
python -m venv .venv && .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python run_all.py --only worldclim                       # covariates (not in git)
streamlit run app/app.py                                 # local dashboard
pytest -q
```

All parameters are in `config/config.yaml` (seed 42). A GBIF account is **not** needed: `run_all.py`
reuses the processed CSVs. Do not commit a `.env` file.

## 7. Remaining plan to the deadline

| # | Task | Owner |
|---|---|---|
| 1 | Final models → `outputs/models/`, validate, push | Sena |
| 2 | `[modelling]` sections in `docs/methods.md`, `docs/limitations.md`, `docs/ai_usage.md` | Sena |
| 3 | Re-run `--from risk`, update README/slides/Devpost numbers from `outputs/risk/summary.json` | Mehmet |
| 4 | Slide PDF (≤ 10 slides) from `slides/salepguard_slides.md` + Sena's figures | both |
| 5 | Record video (≤ 10 min) from `slides/video_script.md`, upload unlisted | both |
| 6 | Resolve `TODO: verify` items, go through `docs/submission_checklist.md`, submit on Devpost | Mehmet |
