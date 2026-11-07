"""Shared helpers: configuration, paths, the common grid, logging and cached downloads."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
COVARIATES = PROCESSED / "covariates"

BIO_VARS = [f"bio{i:02d}" for i in range(1, 20)]
COVARIATE_NAMES = BIO_VARS + ["elevation"]


@lru_cache(maxsize=1)
def config() -> dict:
    with open(ROOT / "config" / "config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader (KEY=VALUE lines); never overrides real env vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        (ROOT / "logs").mkdir(exist_ok=True)
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%H:%M:%S")
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        fh = logging.FileHandler(ROOT / "logs" / "pipeline.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(sh)
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
    return logger


@dataclass(frozen=True)
class Grid:
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    res: float

    @property
    def width(self) -> int:
        return int(round((self.lon_max - self.lon_min) / self.res))

    @property
    def height(self) -> int:
        return int(round((self.lat_max - self.lat_min) / self.res))

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def transform(self):
        from rasterio.transform import from_origin

        return from_origin(self.lon_min, self.lat_max, self.res, self.res)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (self.lon_min, self.lat_min, self.lon_max, self.lat_max)

    def cell_index(self, lon, lat) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Row/col of points and a mask of points falling inside the grid."""
        lon = np.asarray(lon, dtype=float)
        lat = np.asarray(lat, dtype=float)
        col = np.floor((lon - self.lon_min) / self.res).astype(int)
        row = np.floor((self.lat_max - lat) / self.res).astype(int)
        inside = (col >= 0) & (col < self.width) & (row >= 0) & (row < self.height)
        return row, col, inside

    def cell_centers(self) -> tuple[np.ndarray, np.ndarray]:
        lons = self.lon_min + (np.arange(self.width) + 0.5) * self.res
        lats = self.lat_max - (np.arange(self.height) + 0.5) * self.res
        return np.meshgrid(lons, lats)


def training_grid() -> Grid:
    g = config()["grid"]
    e = g["training_extent"]
    return Grid(e["lon_min"], e["lon_max"], e["lat_min"], e["lat_max"], g["resolution_deg"])


def write_raster(
    path: Path, array: np.ndarray, grid: Grid | None = None, nodata=np.nan, dtype: str = "float32"
) -> Path:
    import rasterio

    grid = grid or training_grid()
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(array)
    if arr.ndim == 2:
        arr = arr[np.newaxis]
    assert arr.shape[1:] == grid.shape, f"{path.name}: shape {arr.shape} != grid {grid.shape}"
    profile = dict(
        driver="GTiff",
        height=grid.height,
        width=grid.width,
        count=arr.shape[0],
        dtype=dtype,
        crs=config()["grid"]["crs"],
        transform=grid.transform,
        compress="lzw",
        nodata=nodata,
    )
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype(dtype))
    return path


def read_raster(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        if src.nodata is not None and not np.isnan(src.nodata):
            arr[arr == src.nodata] = np.nan
    return arr


def download(url: str, dest: Path, logger: logging.Logger | None = None, timeout: int = 600) -> Path:
    """Download once; re-use the cached file on later runs."""
    import requests

    if dest.exists() and dest.stat().st_size > 0:
        if logger:
            logger.info("cached: %s", dest.relative_to(ROOT))
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if logger:
        logger.info("downloading %s", url)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(
        url, stream=True, timeout=timeout, headers={"User-Agent": "SalepGuard/0.1 (research hackathon)"}
    ) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    tmp.replace(dest)
    return dest


def _ascii_safe(path: Path) -> bool:
    try:
        str(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def write_vector(gdf, path: Path) -> Path:
    """GeoPackage writer. GDAL's SQLite cannot open non-ASCII Windows paths, so we
    write to an ASCII temp path and move the file into place."""
    import shutil
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    if _ascii_safe(path):
        gdf.to_file(path, driver="GPKG")
        return path
    tmp = Path(tempfile.mkdtemp()) / path.name
    gdf.to_file(tmp, driver="GPKG")
    if path.exists():
        path.unlink()
    shutil.move(str(tmp), path)
    return path


def read_vector(path: Path):
    import shutil
    import tempfile

    import geopandas as gpd

    if _ascii_safe(path):
        return gpd.read_file(path)
    tmp = Path(tempfile.mkdtemp()) / path.name
    shutil.copy(path, tmp)
    return gpd.read_file(tmp)


def turkey_mask() -> np.ndarray:
    return read_raster(PROCESSED / "turkey_mask.tif") == 1


def minmax(arr: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    vals = arr[mask] if mask is not None else arr
    lo, hi = np.nanmin(vals), np.nanmax(vals)
    out = (arr - lo) / (hi - lo) if hi > lo else np.zeros_like(arr)
    return np.clip(out, 0, 1)
