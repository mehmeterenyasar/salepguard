"""Write data/processed/DATA_MANIFEST.md: source, date, licence, processing and DOI per file."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from src.common import PROCESSED, RAW, config, get_logger

log = get_logger("manifest")

SOURCES = {
    "gbif": ("GBIF.org occurrence data (Orchidaceae, training extent)",
             "Licence varies per record (CC0 / CC BY / CC BY-NC); the download DOI lists all datasets. "
             "Cite the download DOI.",
             "https://www.gbif.org"),
    "worldclim": ("WorldClim 2.1 bioclimatic variables + elevation, 2.5 arc-min, 1970-2000 "
                  "(Fick & Hijmans 2017, Int. J. Climatol. 37:4302-4315, doi:10.1002/joc.5086)",
                  "WorldClim terms: free for academic and other non-commercial use; redistribution or "
                  "commercial use not allowed without prior permission. NOT committed to this repository.",
                  "https://www.worldclim.org/data/worldclim21.html"),
    "cmip6": ("WorldClim 2.1 downscaled CMIP6 bioclim, 2.5 arc-min, 2041-2060",
              "Same WorldClim terms as above. NOT committed to this repository.",
              "https://www.worldclim.org/data/cmip6/cmip6climate.html"),
    "worldpop": ("WorldPop 2020 population density, 1 km, UN-adjusted, Turkey "
                 "(WorldPop & CIESIN 2018, doi:10.5258/SOTON/WP00674)",
                 "CC BY 4.0", "https://hub.worldpop.org/"),
    "map": ("Travel time to cities 2015 (Weiss et al. 2018, Nature 553:333-336, doi:10.1038/nature25181), "
            "Malaria Atlas Project WCS",
            "Malaria Atlas Project open-access policy: CC BY 3.0 Unported (TODO: verify dataset-specific licence)",
            "https://malariaatlas.org/"),
    "osm": ("OpenStreetMap protected areas (boundary=protected_area|national_park, leisure=nature_reserve) "
            "via Overpass API", "ODbL 1.0 - (c) OpenStreetMap contributors", "https://www.openstreetmap.org/copyright"),
    "wdpa": ("World Database on Protected Areas (UNEP-WCMC & IUCN, Protected Planet)",
             "WDPA Terms of Use (non-commercial; attribution required)", "https://www.protectedplanet.net"),
    "geoboundaries": ("geoBoundaries gbOpen TUR ADM0/ADM1 (Runfola et al. 2020, PLoS ONE 15(4):e0231866, "
                      "doi:10.1371/journal.pone.0231866); source: OpenStreetMap",
                      "CC BY-SA 2.0 (as reported by the geoBoundaries API)", "https://www.geoboundaries.org"),
    "naturalearth": ("Natural Earth 1:10m admin-0 countries and populated places (cleaning tests only)",
                     "Public domain", "https://www.naturalearthdata.com"),
}

FILES = [
    ("occurrences_raw_salep.csv", "gbif", "Salep-genus records with species-level names in the training extent, before cleaning."),
    ("occurrences_clean.csv", "gbif", "After cleaning (see cleaning_report.csv); duplicates (species + coordinates) removed."),
    ("background_targetgroup.csv", "gbif", "All cleaned Orchidaceae records (target-group background), duplicates by coordinate+year removed."),
    ("species_list.csv", "gbif", "Per-species record/cell counts and the selection rule (config.species_selection)."),
    ("cleaning_report.csv", "gbif", "Records removed by each cleaning filter."),
    ("covariates/bio01..bio19.tif, elevation.tif", "worldclim", "Exact window of the global 2.5' grid (no resampling), float32, LZW."),
    ("covariates_future/<ssp>_2041-2060/*.tif", "cmip6", "Ensemble mean of the GCMs in config.future.gcms; *_gcm_sd.tif = inter-GCM SD."),
    ("pressure_population.tif", "worldpop", "Mean density per 2.5' cell -> log1p -> min-max 0-1 within Turkey."),
    ("pressure_accessibility.tif", "map", "Mean travel time per cell -> log1p -> min-max -> 1 - x (high = accessible)."),
    ("pressure_index.tif", "worldpop", "w_pop * population + w_acc * accessibility, re-scaled 0-1 (weights in config). Also MAP."),
    ("pressure_scenarios/*.tif", "worldpop", "Sensitivity scenarios with alternative weights (config.pressure.sensitivity_scenarios)."),
    ("protected_areas.tif / .gpkg", "PA_SOURCE", "Polygons; raster = 1 where the cell centre is inside a protected area."),
    ("turkey_mask.tif, admin0_turkey.gpkg", "geoboundaries", "ADM0 rasterised by cell centre."),
    ("admin1_turkey.gpkg, province_id.tif", "geoboundaries", "81 provinces; province_id = row order of admin1_turkey.gpkg + 1."),
]


def main() -> None:
    g = config()["grid"]
    gbif_state = {}
    sp = RAW / "gbif" / "download_state.json"
    if sp.exists():
        gbif_state = json.loads(sp.read_text())
    pa_source = "wdpa" if any((RAW / "wdpa").glob("*")) else "osm"
    doi = gbif_state.get("doi")
    lines = [
        "# DATA_MANIFEST", "",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `src/data/manifest.py`.", "",
        "## Shared grid", "",
        f"- CRS: {g['crs']}; resolution: 2.5 arc-min (1/24 deg, ~4.6 km)",
        f"- Training extent: lon {g['training_extent']['lon_min']}-{g['training_extent']['lon_max']}, "
        f"lat {g['training_extent']['lat_min']}-{g['training_extent']['lat_max']} (624 x 216 cells)",
        "- Reporting extent: Turkey (`turkey_mask.tif`)", "",
        "## GBIF occurrence download", "",
        f"- Method: {gbif_state.get('method', 'GBIF Download API (SIMPLE_CSV)')}",
        f"- DOI: {('https://doi.org/' + doi) if doi else 'none (search API fallback) - TODO: replace with Download API DOI'}",
        f"- Retrieved: {gbif_state.get('created') or gbif_state.get('retrieved_utc') or gbif_state.get('requested_utc')}",
        f"- Records: {gbif_state.get('totalRecords')}",
        "- Query: familyKey=7689 (Orchidaceae), hasCoordinate=true, hasGeospatialIssue=false, "
        "occurrenceStatus=PRESENT, within training-extent polygon", "",
        "## Files", "", "| File | Source | Processing |", "|---|---|---|",
    ]
    for f, src, proc in FILES:
        key = pa_source if src == "PA_SOURCE" else src
        lines.append(f"| `{f}` | {SOURCES[key][0]} | {proc} |")
    lines += ["", "## Sources, licences and links", "", "| Key | Source | Licence | Link |", "|---|---|---|---|"]
    for k, (name, lic, url) in SOURCES.items():
        lines.append(f"| {k} | {name} | {lic} | {url} |")
    cr = PROCESSED / "cleaning_report.csv"
    if cr.exists():
        lines += ["", "## Cleaning report", "", pd.read_csv(cr).to_markdown(index=False)]
    (PROCESSED / "DATA_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("DATA_MANIFEST.md written (protected-area source: %s)", pa_source)


if __name__ == "__main__":
    main()
