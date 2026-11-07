"""Harvest-pressure proxy layers on the shared grid (Turkey only).

* population: WorldPop 2020 1 km UN-adjusted density -> mean per 2.5' cell -> log1p -> 0-1
* accessibility: Weiss et al. (2018) travel time to cities (2015) -> mean per cell ->
  inverted (short travel time = high pressure) after log1p -> 0-1
* pressure_index = w_pop * population + w_acc * accessibility  (weights in config)

Sensitivity scenarios (config.pressure.sensitivity_scenarios) are written to
data/processed/pressure_scenarios/.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

from src.common import PROCESSED, RAW, config, download, get_logger, minmax, training_grid, \
    turkey_mask, write_raster

log = get_logger("pressure")
WORLDPOP_URL = ("https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/"
                "2020/TUR/tur_pd_2020_1km_UNadj.tif")
MAP_WCS = ("https://data.malariaatlas.org/geoserver/Accessibility/wcs?service=WCS&version=2.0.1"
           "&request=GetCoverage&coverageId=Accessibility__201501_Global_Travel_Time_to_Cities"
           "&subset=Long(25,45.5)&subset=Lat(35,42.5)&format=image/geotiff")


def to_grid(path, resampling=Resampling.average) -> np.ndarray:
    grid = training_grid()
    dst = np.full(grid.shape, np.nan, dtype="float32")
    with rasterio.open(path) as src:
        srcarr = src.read(1).astype("float32")
        nd = src.nodata
        if nd is not None:
            srcarr[srcarr == nd] = np.nan
        srcarr[srcarr < 0] = np.nan
        reproject(srcarr, dst, src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
                  dst_transform=grid.transform, dst_crs=config()["grid"]["crs"], dst_nodata=np.nan,
                  resampling=resampling)
    return dst


def compose(pop: np.ndarray, acc: np.ndarray, w_pop: float, w_acc: float) -> np.ndarray:
    total = w_pop + w_acc
    return (w_pop * pop + w_acc * acc) / total


def main() -> None:
    mask = turkey_mask()
    pop_path = download(WORLDPOP_URL, RAW / "worldpop" / "tur_pd_2020_1km_UNadj.tif", log)
    acc_path = download(MAP_WCS, RAW / "accessibility" / "travel_time_cities_2015_tur.tif", log)

    pop = to_grid(pop_path)
    pop = np.where(mask, np.nan_to_num(pop, nan=0.0), np.nan)  # WorldPop NaN inside TR = 0 people
    pop_n = np.where(mask, minmax(np.log1p(pop), mask), np.nan)

    tt = to_grid(acc_path)  # minutes
    fill = np.nanmax(tt[mask])
    tt = np.where(mask, np.where(np.isnan(tt), fill, tt), np.nan)
    acc_n = np.where(mask, 1.0 - minmax(np.log1p(tt), mask), np.nan)

    w = config()["pressure"]["weights"]
    idx = compose(pop_n, acc_n, w["population"], w["accessibility"])
    idx = np.where(mask, minmax(idx, mask), np.nan)

    write_raster(PROCESSED / "pressure_population.tif", pop_n)
    write_raster(PROCESSED / "pressure_accessibility.tif", acc_n)
    write_raster(PROCESSED / "pressure_index.tif", idx)
    for name, sw in config()["pressure"]["sensitivity_scenarios"].items():
        s = compose(pop_n, acc_n, sw["population"], sw["accessibility"])
        write_raster(PROCESSED / "pressure_scenarios" / f"pressure_index_{name}.tif",
                     np.where(mask, minmax(s, mask), np.nan))

    r = np.corrcoef(pop_n[mask], acc_n[mask])[0, 1]
    log.info("pressure: mean=%.3f, median travel time=%.0f min, r(pop,acc)=%.2f",
             float(np.nanmean(idx)), float(np.nanmedian(tt[mask])), r)


if __name__ == "__main__":
    main()
