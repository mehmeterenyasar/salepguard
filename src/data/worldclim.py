"""WorldClim 2.1 (2.5 arc-min) bioclim + elevation, and CMIP6 future bioclim,
cropped to the training extent on the shared grid (exact window, no resampling)."""

from __future__ import annotations

import zipfile

import numpy as np
import rasterio
from rasterio.windows import from_bounds

from src.common import (
    BIO_VARS,
    COVARIATES,
    PROCESSED,
    RAW,
    config,
    download,
    get_logger,
    training_grid,
    write_raster,
)

log = get_logger("worldclim")
BASE = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base"
CMIP6 = "https://geodata.ucdavis.edu/cmip6/2.5m/{gcm}/{ssp}/wc2.1_2.5m_bioc_{gcm}_{ssp}_{period}.tif"


def crop(src_path: str, band: int = 1) -> np.ndarray:
    grid = training_grid()
    with rasterio.open(src_path) as src:
        win = from_bounds(*grid.bounds, transform=src.transform).round_offsets().round_lengths()
        arr = src.read(band, window=win).astype("float32")
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
    arr[arr < -1e30] = np.nan
    assert arr.shape == grid.shape, arr.shape
    return arr


def current() -> None:
    wc = RAW / "worldclim"
    bio_zip = download(f"{BASE}/wc2.1_2.5m_bio.zip", wc / "wc2.1_2.5m_bio.zip", log)
    elev_zip = download(f"{BASE}/wc2.1_2.5m_elev.zip", wc / "wc2.1_2.5m_elev.zip", log)
    names = zipfile.ZipFile(bio_zip).namelist()
    for i, var in enumerate(BIO_VARS, start=1):
        member = next(n for n in names if n.endswith(f"_bio_{i}.tif"))
        out = COVARIATES / f"{var}.tif"
        if not out.exists():
            write_raster(out, crop(f"/vsizip/{bio_zip.as_posix()}/{member}"))
    member = next(n for n in zipfile.ZipFile(elev_zip).namelist() if n.endswith(".tif"))
    write_raster(COVARIATES / "elevation.tif", crop(f"/vsizip/{elev_zip.as_posix()}/{member}"))
    log.info("current covariates written to %s", COVARIATES.relative_to(PROCESSED.parent.parent))


def future() -> None:
    fc = config()["future"]
    elev = COVARIATES / "elevation.tif"
    for ssp in fc["scenarios"]:
        out_dir = PROCESSED / "covariates_future" / f"{ssp}_{fc['period']}"
        stacks = []
        for gcm in fc["gcms"]:
            url = CMIP6.format(gcm=gcm, ssp=ssp, period=fc["period"])
            path = download(url, RAW / "cmip6" / url.rsplit("/", 1)[1], log)
            stacks.append(np.stack([crop(str(path), b) for b in range(1, 20)]))
            log.info("%s %s cropped", gcm, ssp)
        ens = np.mean(stacks, axis=0)
        for i, var in enumerate(BIO_VARS):
            write_raster(out_dir / f"{var}.tif", ens[i])
            if len(stacks) > 1:
                write_raster(out_dir / f"{var}_gcm_sd.tif", np.std(stacks, axis=0)[i])
        # elevation is static: copy so the folder is a complete covariate set
        write_raster(out_dir / "elevation.tif", rasterio.open(elev).read(1))
        log.info("future covariates (%s, %d GCM) -> %s", ssp, len(stacks), out_dir.name)


def main() -> None:
    current()
    future()
    b1 = crop(str(COVARIATES / "bio01.tif"))
    log.info(
        "bio01 range %.1f..%.1f, NaN share %.2f", np.nanmin(b1), np.nanmax(b1), float(np.isnan(b1).mean())
    )


if __name__ == "__main__":
    main()
