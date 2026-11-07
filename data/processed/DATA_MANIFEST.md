# DATA_MANIFEST

Generated 2026-11-07 18:02 UTC by `src/data/manifest.py`.

## Shared grid

- CRS: EPSG:4326; resolution: 2.5 arc-min (1/24 deg, ~4.6 km)
- Training extent: lon 19.0-45.0, lat 34.0-43.0 (624 x 216 cells)
- Reporting extent: Turkey (`turkey_mask.tif`)

## GBIF occurrence download

- Method: GBIF Download API (SIMPLE_CSV)
- DOI: https://doi.org/10.15468/dl.mfzrky
- Retrieved: 2026-11-07T17:49:30.347+00:00
- Records: 62435
- Query: familyKey=7689 (Orchidaceae), hasCoordinate=true, hasGeospatialIssue=false, occurrenceStatus=PRESENT, within training-extent polygon

## Files

| File | Source | Processing |
|---|---|---|
| `occurrences_raw_salep.csv` | GBIF.org occurrence data (Orchidaceae, training extent) | Salep-genus records with species-level names in the training extent, before cleaning. |
| `occurrences_clean.csv` | GBIF.org occurrence data (Orchidaceae, training extent) | After cleaning (see cleaning_report.csv); duplicates (species + coordinates) removed. |
| `background_targetgroup.csv` | GBIF.org occurrence data (Orchidaceae, training extent) | All cleaned Orchidaceae records (target-group background), duplicates by coordinate+year removed. |
| `species_list.csv` | GBIF.org occurrence data (Orchidaceae, training extent) | Per-species record/cell counts and the selection rule (config.species_selection). |
| `cleaning_report.csv` | GBIF.org occurrence data (Orchidaceae, training extent) | Records removed by each cleaning filter. |
| `covariates/bio01..bio19.tif, elevation.tif` | WorldClim 2.1 bioclimatic variables + elevation, 2.5 arc-min, 1970-2000 (Fick & Hijmans 2017, Int. J. Climatol. 37:4302-4315, doi:10.1002/joc.5086) | Exact window of the global 2.5' grid (no resampling), float32, LZW. |
| `covariates_future/<ssp>_2041-2060/*.tif` | WorldClim 2.1 downscaled CMIP6 bioclim, 2.5 arc-min, 2041-2060 | Ensemble mean of the GCMs in config.future.gcms; *_gcm_sd.tif = inter-GCM SD. |
| `pressure_population.tif` | WorldPop 2020 population density, 1 km, UN-adjusted, Turkey (WorldPop & CIESIN 2018, doi:10.5258/SOTON/WP00674) | Mean density per 2.5' cell -> log1p -> min-max 0-1 within Turkey. |
| `pressure_accessibility.tif` | Travel time to cities 2015 (Weiss et al. 2018, Nature 553:333-336, doi:10.1038/nature25181), Malaria Atlas Project WCS | Mean travel time per cell -> log1p -> min-max -> 1 - x (high = accessible). |
| `pressure_index.tif` | WorldPop 2020 population density, 1 km, UN-adjusted, Turkey (WorldPop & CIESIN 2018, doi:10.5258/SOTON/WP00674) | w_pop * population + w_acc * accessibility, re-scaled 0-1 (weights in config). Also MAP. |
| `pressure_scenarios/*.tif` | WorldPop 2020 population density, 1 km, UN-adjusted, Turkey (WorldPop & CIESIN 2018, doi:10.5258/SOTON/WP00674) | Sensitivity scenarios with alternative weights (config.pressure.sensitivity_scenarios). |
| `protected_areas.tif / .gpkg` | Union of WDPA (Nov 2026 public release, 17 Turkish sites) and OpenStreetMap protected areas | Polygons; raster = 1 where the cell centre is inside a protected area. |
| `turkey_mask.tif, admin0_turkey.gpkg` | geoBoundaries gbOpen TUR ADM0/ADM1 (Runfola et al. 2020, PLoS ONE 15(4):e0231866, doi:10.1371/journal.pone.0231866); source: OpenStreetMap | ADM0 rasterised by cell centre. |
| `admin1_turkey.gpkg, province_id.tif` | geoBoundaries gbOpen TUR ADM0/ADM1 (Runfola et al. 2020, PLoS ONE 15(4):e0231866, doi:10.1371/journal.pone.0231866); source: OpenStreetMap | 81 provinces; province_id = row order of admin1_turkey.gpkg + 1. |

## Sources, licences and links

| Key | Source | Licence | Link |
|---|---|---|---|
| gbif | GBIF.org occurrence data (Orchidaceae, training extent) | Licence varies per record (CC0 / CC BY / CC BY-NC); the download DOI lists all datasets. Cite the download DOI. | https://www.gbif.org |
| worldclim | WorldClim 2.1 bioclimatic variables + elevation, 2.5 arc-min, 1970-2000 (Fick & Hijmans 2017, Int. J. Climatol. 37:4302-4315, doi:10.1002/joc.5086) | WorldClim terms: free for academic and other non-commercial use; redistribution or commercial use not allowed without prior permission. NOT committed to this repository. | https://www.worldclim.org/data/worldclim21.html |
| cmip6 | WorldClim 2.1 downscaled CMIP6 bioclim, 2.5 arc-min, 2041-2060 | Same WorldClim terms as above. NOT committed to this repository. | https://www.worldclim.org/data/cmip6/cmip6climate.html |
| worldpop | WorldPop 2020 population density, 1 km, UN-adjusted, Turkey (WorldPop & CIESIN 2018, doi:10.5258/SOTON/WP00674) | CC BY 4.0 | https://hub.worldpop.org/ |
| map | Travel time to cities 2015 (Weiss et al. 2018, Nature 553:333-336, doi:10.1038/nature25181), Malaria Atlas Project WCS | Malaria Atlas Project open-access policy: CC BY 3.0 Unported (TODO: verify dataset-specific licence) | https://malariaatlas.org/ |
| osm | OpenStreetMap protected areas (boundary=protected_area|national_park, leisure=nature_reserve) via Overpass API | ODbL 1.0 - (c) OpenStreetMap contributors | https://www.openstreetmap.org/copyright |
| wdpa | World Database on Protected Areas, public release Nov 2026, Turkey (UNEP-WCMC & IUCN, Protected Planet); only 17 sites are public for Turkey | WDPA Terms of Use (non-commercial; attribution required) | https://www.protectedplanet.net |
| wdpa_osm | Union of WDPA (Nov 2026 public release, 17 Turkish sites) and OpenStreetMap protected areas | WDPA Terms of Use + ODbL 1.0 | https://www.protectedplanet.net ; https://www.openstreetmap.org/copyright |
| geoboundaries | geoBoundaries gbOpen TUR ADM0/ADM1 (Runfola et al. 2020, PLoS ONE 15(4):e0231866, doi:10.1371/journal.pone.0231866); source: OpenStreetMap | CC BY-SA 2.0 (as reported by the geoBoundaries API) | https://www.geoboundaries.org |
| naturalearth | Natural Earth 1:10m admin-0 countries and populated places (cleaning tests only) | Public domain | https://www.naturalearthdata.com |

## Cleaning report

| dataset                      | step                                       |   removed |   remaining |
|:-----------------------------|:-------------------------------------------|----------:|------------:|
| background (all Orchidaceae) | raw GBIF records in extent                 |         0 |       62435 |
| background (all Orchidaceae) | missing coordinates                        |         0 |       62435 |
| background (all Orchidaceae) | basisOfRecord fossil/living                |        72 |       62363 |
| background (all Orchidaceae) | missing year                               |       202 |       62161 |
| background (all Orchidaceae) | year < 1970                                |      1591 |       60570 |
| background (all Orchidaceae) | (info) missing coordinate uncertainty kept |         0 |        8195 |
| background (all Orchidaceae) | coordinate uncertainty > 5000 m            |     23967 |       36603 |
| background (all Orchidaceae) | zero coordinates                           |         0 |       36603 |
| background (all Orchidaceae) | equal latitude/longitude                   |         8 |       36595 |
| background (all Orchidaceae) | country/province centroids (<1000 m)       |       357 |       36238 |
| background (all Orchidaceae) | capitals (<10 km)                          |       549 |       35689 |
| background (all Orchidaceae) | GBIF headquarters                          |         0 |       35689 |
| background (all Orchidaceae) | sea / no climate data                      |        96 |       35593 |
| salep genera (species level) | raw GBIF records in extent                 |         0 |       54391 |
| salep genera (species level) | missing coordinates                        |         0 |       54391 |
| salep genera (species level) | basisOfRecord fossil/living                |         1 |       54390 |
| salep genera (species level) | missing year                               |       142 |       54248 |
| salep genera (species level) | year < 1970                                |      1288 |       52960 |
| salep genera (species level) | (info) missing coordinate uncertainty kept |         0 |        6549 |
| salep genera (species level) | coordinate uncertainty > 5000 m            |     21754 |       31206 |
| salep genera (species level) | zero coordinates                           |         0 |       31206 |
| salep genera (species level) | equal latitude/longitude                   |         4 |       31202 |
| salep genera (species level) | country/province centroids (<1000 m)       |       353 |       30849 |
| salep genera (species level) | capitals (<10 km)                          |       471 |       30378 |
| salep genera (species level) | GBIF headquarters                          |         0 |       30378 |
| salep genera (species level) | sea / no climate data                      |        85 |       30293 |
| salep genera (species level) | duplicate species+coordinates              |      5736 |       24557 |
