# Data sources and licences

All external data are cited below and used under their licences. Exact files, dates,
processing steps and the GBIF download DOI are recorded automatically in
[`data/processed/DATA_MANIFEST.md`](../data/processed/DATA_MANIFEST.md).

| Data | Provider | Version / date | Licence | Citation | Used for |
|---|---|---|---|---|---|
| Orchidaceae occurrences | GBIF.org | retrieved 2026-11-07 (see manifest) | per-record CC0 / CC BY / CC BY-NC | GBIF.org (2026) GBIF Occurrence Download, DOI in manifest | presences (salep genera) and target-group background (all orchids) |
| Bioclimatic variables + elevation | WorldClim 2.1, 2.5 arc-min | 1970–2000 normals | free for academic / non-commercial use; **redistribution not allowed without permission** | Fick, S.E. & Hijmans, R.J. (2017) WorldClim 2: new 1-km spatial resolution climate surfaces for global land areas. *Int. J. Climatol.* 37: 4302–4315. doi:10.1002/joc.5086 | model covariates |
| Future bioclim (CMIP6) | WorldClim 2.1 downscaled CMIP6, 2.5 arc-min | 2041–2060, SSP2-4.5 & SSP5-8.5; GCMs MPI-ESM1-2-HR, IPSL-CM6A-LR, MIROC6 | as WorldClim | as WorldClim + CMIP6 modelling groups (Eyring et al. 2016, *Geosci. Model Dev.* 9: 1937–1958, doi:10.5194/gmd-9-1937-2016) | climate-change projections |
| Population density | WorldPop | 2020, 1 km, UN-adjusted, Turkey | CC BY 4.0 | WorldPop & CIESIN (2018) Global High Resolution Population Denominators Project. doi:10.5258/SOTON/WP00674 | harvest-pressure proxy |
| Travel time to cities | Malaria Atlas Project | 2015 | MAP open-access policy: CC BY 3.0 Unported (TODO: verify dataset-specific licence) | Weiss, D.J. et al. (2018) A global map of travel time to cities to assess inequalities in accessibility in 2015. *Nature* 553: 333–336. doi:10.1038/nature25181 | harvest-pressure proxy |
| Protected areas (fallback in use) | OpenStreetMap via Overpass API | queried 2026-11-07 | ODbL 1.0, © OpenStreetMap contributors | — | protection layer |
| Protected areas (preferred) | WDPA, UNEP-WCMC & IUCN (Protected Planet) | TODO: month/year of release if downloaded | WDPA Terms of Use | UNEP-WCMC and IUCN (2026), Protected Planet: The World Database on Protected Areas (WDPA), [On-line, TODO month/year], Cambridge, UK: UNEP-WCMC and IUCN. www.protectedplanet.net | protection layer |
| Province / country boundaries | geoBoundaries (gbOpen, TUR ADM0/ADM1; source: OpenStreetMap) | build 2023-12-12 | CC BY-SA 2.0 (as reported by geoBoundaries API) | Runfola, D. et al. (2020) geoBoundaries: A global database of political administrative boundaries. *PLoS ONE* 15(4): e0231866. doi:10.1371/journal.pone.0231866 | Turkey mask, province ranking |
| Country centroids, capitals | Natural Earth 1:10m | v5.x | public domain | Natural Earth | coordinate-cleaning tests only |

## Literature (salep use, harvest context)

Used for the problem statement and the `salep_use_reference` column. Salep use is recorded at
**genus level**; species-level attributions are marked `TODO: verify`.

- Sezik, E. (2002) Turkish orchids and salep. *Acta Pharmaceutica Turcica* 44: 151–157.
- Kasparek, M. & Grimm, U. (1999) European trade in Turkish salep with special reference to Germany. *Economic Botany* 53(4): 396–406.
- Molnár, V.A. et al. (2017) Turkish graveyards as refuges for orchids against tuber harvest. *Ecology and Evolution* 7(24): 11257–11264. (TODO: verify pages/DOI)
- Kreziou, A., de Boer, H. & Gravendeel, B. (2016) Harvesting of salep orchids in north-western Greece continues to threaten natural populations. *Oryx* 50(3): 393–396.
- Ghorbani, A., Gravendeel, B., Naghibi, F. & de Boer, H. (2014) Wild orchid tuber collection in Iran: a wake-up call for conservation. *Biodiversity and Conservation* 23: 2749–2760.

> Bibliographic details above were written from memory by the team/AI assistant and must be
> checked against the publishers' pages before final submission (see checklist).

## Software

Python 3.14 with numpy, pandas, rasterio/GDAL, geopandas, shapely, pyproj, scikit-learn,
elapid (MaxEnt implementation; Anderson 2023, *JOSS* — TODO: verify citation), matplotlib, plotly, folium, streamlit, streamlit-folium.
All are open-source (BSD/MIT/Apache-type licences). The teammate's model code in `modeling/`
lists its own dependencies.

## Redistribution notes

- **WorldClim / CMIP6 rasters are not committed** (WorldClim terms forbid redistribution
  without permission). `python run_all.py --only worldclim` rebuilds them in ~5 minutes.
- Raw GBIF exports are not committed; processed CSVs are, with the download DOI.
- Derived maps (suitability, risk) are published at coarse resolution only (see
  [limitations](limitations.md) and "Responsible use" in the README).
