"""Turkey country/province boundaries (geoBoundaries) and the Turkey raster mask.

Also fetches Natural Earth reference layers used by the coordinate-cleaning tests
(country centroids, capitals).
"""

from __future__ import annotations

import zipfile

import geopandas as gpd
import numpy as np
import requests
from rasterio.features import rasterize

from src.common import PROCESSED, RAW, download, get_logger, training_grid, write_raster, write_vector

log = get_logger("boundaries")

GB_API = "https://www.geoboundaries.org/api/current/gbOpen/TUR/{level}/"
NE_URLS = {
    "ne_10m_admin_0_countries": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip",
    "ne_10m_populated_places_simple": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_populated_places_simple.zip",
}


def fetch_geoboundaries(level: str) -> gpd.GeoDataFrame:
    dest = RAW / "geoboundaries" / f"geoBoundaries-TUR-{level}.geojson"
    if not dest.exists():
        r = requests.get(GB_API.format(level=level), timeout=60)
        r.raise_for_status()
        meta = r.json()
        (RAW / "geoboundaries").mkdir(parents=True, exist_ok=True)
        (RAW / "geoboundaries" / f"meta_{level}.json").write_text(r.text, encoding="utf-8")
        download(meta["gjDownloadURL"], dest, log)
    return gpd.read_file(dest).to_crs("EPSG:4326")


def fetch_natural_earth() -> None:
    for name, url in NE_URLS.items():
        z = download(url, RAW / "naturalearth" / f"{name}.zip", log)
        out = RAW / "naturalearth" / name
        if not out.exists():
            with zipfile.ZipFile(z) as zf:
                zf.extractall(out)


def main() -> None:
    grid = training_grid()
    adm0 = fetch_geoboundaries("ADM0")
    adm1 = fetch_geoboundaries("ADM1")
    adm1 = adm1.rename(columns={"shapeName": "province"})[["province", "shapeISO", "shapeID", "geometry"]]
    write_vector(adm1, PROCESSED / "admin1_turkey.gpkg")
    write_vector(adm0[["shapeName", "shapeISO", "geometry"]], PROCESSED / "admin0_turkey.gpkg")

    mask = rasterize(
        ((g, 1) for g in adm0.geometry), out_shape=grid.shape, transform=grid.transform, fill=0, dtype="uint8"
    )
    write_raster(PROCESSED / "turkey_mask.tif", mask, grid, nodata=255, dtype="uint8")

    # Province id raster (1..81) for zonal statistics; 0 = outside Turkey
    prov = rasterize(
        ((g, i + 1) for i, g in enumerate(adm1.geometry)),
        out_shape=grid.shape,
        transform=grid.transform,
        fill=0,
        dtype="uint8",
    )
    write_raster(PROCESSED / "province_id.tif", prov, grid, nodata=255, dtype="uint8")

    fetch_natural_earth()
    log.info(
        "provinces=%d, Turkey cells=%d, province cells=%d",
        len(adm1),
        int(mask.sum()),
        int(np.count_nonzero(prov)),
    )


if __name__ == "__main__":
    main()
