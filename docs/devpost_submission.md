# Devpost submission text (copy and paste)

> Numbers come from the final model (`outputs/risk/summary.json`, `docs/results_summary.md`). Only the
> video URL is left to fill in after the YouTube upload.

**Project title:** SalepGuard

**Tagline:** Mapping where Turkey's wild salep orchids are most exposed to tuber harvest, outside
protected areas, with honest uncertainty.

**Track:** Track 3 – Biodiversity & Sustainability

## Short description

SalepGuard is an open, interactive conservation-prioritisation tool for the wild orchids dug up to make
salep. It combines species distribution models for 20 salep orchids, a harvest-pressure proxy
(population and accessibility) and protected-area coverage into a Priority Index for Turkey. It adds
propagated uncertainty, sensitivity analysis, climate projections for 2041–2060, a province ranking and a
protection-gap analysis.

## Problem

Salep (the traditional hot drink, salep ice cream and folk remedies) is made from orchid tubers. In
Turkey about 90 orchid species in 24 genera are reported in salep (Sezik 2002). The supply comes from
wild collection, and harvesting a tuber kills the plant. Agencies and NGOs have no open, spatial and
uncertainty-aware tool that shows where to focus monitoring, protection and sustainable-supply efforts.

## Solution / approach

1. **Data:** 62,435 GBIF orchid records across the Eastern Mediterranean; WorldClim 2.1 climate plus
   CMIP6 projections (3 GCMs, SSP2-4.5 and SSP5-8.5); WorldPop population; travel time to cities;
   OpenStreetMap/WDPA protected areas; geoBoundaries provinces.
2. **Cleaning:** CoordinateCleaner-style filters leave 24,557 salep-genus records. 20 species meet the
   data-sufficiency rule. A target-group background corrects for sampling bias.
3. **Models:** bias-corrected MaxEnt (target-group background) tuned per species with spatial block
   cross-validation, 20 bootstrap refits, MESS extrapolation checks and bias-aware null models, plus an
   untuned random-CV baseline for comparison.
4. **SalepGuard Priority Index:** Σ species suitability × harvest pressure × (1 − protected). Bootstrap
   uncertainty is propagated to identify *robust hotspots*.
5. **Analyses:** Jaccard stability under alternative pressure weights and thresholding, climate-change
   difference maps, an 81-province ranking, and per-species protection gaps.
6. **Dashboard:** Streamlit app with a species explorer, risk scenarios, province ranking, protection
   gap, and methods and limitations. Raw points are never shown and maps are aggregated to ~9 km for
   responsible display.

## Built with

python, streamlit, folium, leaflet, plotly, rasterio, gdal, geopandas, shapely, numpy, pandas, scipy,
scikit-learn, elapid, maxent, matplotlib, gbif-api, worldclim, cmip6, worldpop, openstreetmap,
overpass-api, geoboundaries, github, claude-code

## Data sources

GBIF.org occurrence download (https://doi.org/10.15468/dl.mfzrky); WorldClim 2.1 (Fick & Hijmans 2017) and WorldClim CMIP6
downscaled projections; WorldPop 2020 (CC BY 4.0); Weiss et al. 2018 travel time to cities (Malaria Atlas
Project); OpenStreetMap (ODbL) / WDPA (UNEP-WCMC & IUCN); geoBoundaries (CC BY-SA 2.0); Natural Earth
(public domain). Full table with licences: `docs/data_sources.md`.

## Results

- 20 salep orchid species modelled. Final model, spatial block CV: mean AUC 0.72 (0.58–0.87), TSS 0.32,
  Boyce 0.58 (random CV would claim 0.76). All species beat a bias-aware null model; 2 with AUC < 0.6 are
  excluded from the index.
- Only **4.5 %** of the area suitable for salep orchids lies inside protected areas, no more than the
  4.5 % of Turkey protected in our layer. For the median species the figure is 7.2 %.
- Priority hotspots concentrate on the Aegean, Marmara and eastern Mediterranean coasts. Top provinces
  are Hatay, İzmir, Aydın, İstanbul and Gaziantep. 1,983 of 2,339 hotspot cells remain hotspots at the lower
  95 % uncertainty bound.
- Hotspots are stable across pressure-weight scenarios (Jaccard 0.87–0.88) and moderately sensitive to
  thresholding (0.60–0.64).
- Limitations: about 65 % of Turkish GBIF records are coordinate-obscured; eastern Anatolia and
  *Dactylorhiza* are under-represented; pressure is a proxy; OSM protected areas are incomplete.

## Team members

- Mehmet Eren Yaşar: data pipeline, risk index, dashboard, documentation
- Sena Aydın: statistical modelling, validation, uncertainty

## Impact and future development

SalepGuard helps the Ministry of Agriculture and Forestry, provincial directorates, NGOs and researchers
decide where to survey, where to extend protection, and where to pilot orchid cultivation and certified
salep supply, without blaming collectors whose livelihoods depend on it. Next steps: digitised herbarium
data for eastern Turkey, trade and interview-based pressure calibration, WDPA and the national registry,
field validation with local partners, and a cultivation-suitability module.

## Links

- GitHub: https://github.com/mehmeterenyasar/salepguard
- Dashboard: https://salepguard.streamlit.app
- Video: <YouTube URL — paste after upload>
- Slides (PDF): https://github.com/mehmeterenyasar/salepguard/blob/main/slides/salepguard_slides.pdf
