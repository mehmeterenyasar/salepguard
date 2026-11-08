"""Shared helpers for the final SalepGuard species distribution models (modelling lead).

Everything here is plain numpy / scikit-learn / elapid so the method is fully visible:
spatial blocks, ENMeval-style tuning metrics, continuous Boyce index, MESS.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common import (  # noqa: E402  (read-only use of the shared helpers)
    COVARIATE_NAMES,
    COVARIATES,
    PROCESSED,
    config,
    read_raster,
    training_grid,
    turkey_mask,
    write_raster,
)

MODELING = ROOT / "modeling"
CACHE = MODELING / "cache"
OUT = ROOT / "outputs" / "models"
FIG = OUT / "figures"
SEED = int(config()["project"]["random_seed"])  # 42
NODATA = -9999.0
GRID = training_grid()
SSPS = list(config()["future"]["scenarios"])
PERIOD = config()["future"]["period"]

FC_GRID = {"L": ["linear"], "LQ": ["linear", "quadratic"], "LQH": ["linear", "quadratic", "hinge"]}
RM_GRID = [0.5, 1.0, 2.0, 4.0]


# ----------------------------------------------------------------------------- data
def load_stack(folder: Path, names: list[str] | None = None) -> np.ndarray:
    names = names or COVARIATE_NAMES
    return np.stack([read_raster(folder / f"{v}.tif") for v in names])


def future_folder(ssp: str) -> Path:
    return PROCESSED / "covariates_future" / f"{ssp}_{PERIOD}"


def cells_of(df: pd.DataFrame, valid_flat: np.ndarray) -> np.ndarray:
    """Unique 2.5' grid cells (flat index) of points; drops cells with NA covariates."""
    r, c, inside = GRID.cell_index(df["decimalLongitude"], df["decimalLatitude"])
    cells = np.unique((r * GRID.width + c)[inside])
    return cells[valid_flat[cells]]


def cell_lonlat(cells: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r, c = np.divmod(cells, GRID.width)
    lon = GRID.lon_min + (c + 0.5) * GRID.res
    lat = GRID.lat_max - (r + 0.5) * GRID.res
    return lon, lat


def cell_area_km2() -> np.ndarray:
    """Area of each grid cell: (res * 111.32 km)^2 * cos(lat)."""
    _, lat = GRID.cell_centers()
    return ((GRID.res * 111.32) ** 2 * np.cos(np.deg2rad(lat))).astype("float64")


def to_grid(values: np.ndarray, cells: np.ndarray, fill=np.nan) -> np.ndarray:
    arr = np.full(GRID.height * GRID.width, fill, dtype="float32")
    arr[cells] = values
    return arr.reshape(GRID.shape)


def save_tif(path: Path, arr: np.ndarray) -> None:
    """Contract raster: float32, NoData -9999, LZW, shared grid."""
    a = np.where(np.isnan(arr), NODATA, arr).astype("float32")
    write_raster(path, a, nodata=NODATA, dtype="float32")


# ----------------------------------------------------------------------------- metrics
def auc(y: np.ndarray, p: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(y, p))


def maxsss_threshold(p_pres: np.ndarray, p_bg: np.ndarray) -> float:
    """Threshold that maximises sensitivity + specificity (presence vs background)."""
    from sklearn.metrics import roc_curve

    y = np.r_[np.ones(len(p_pres)), np.zeros(len(p_bg))]
    fpr, tpr, thr = roc_curve(y, np.r_[p_pres, p_bg])
    i = int(np.argmax(tpr - fpr))
    return float(min(thr[i], 1.0))


def tss_at(p_pres: np.ndarray, p_bg: np.ndarray, thr: float) -> float:
    return float(np.mean(p_pres >= thr) + np.mean(p_bg < thr) - 1)


def p10_threshold(p_train_pres: np.ndarray) -> float:
    """10 % training-presence threshold (90 % of training presences above it)."""
    return float(np.quantile(p_train_pres, 0.10))


def boyce(pres: np.ndarray, bg: np.ndarray, n_win: int = 101, width: float = 0.1) -> float:
    """Continuous Boyce index (Hirzel et al. 2006), moving window as in ecospat.boyce:
    Spearman r between window centre and predicted/expected ratio."""
    from scipy.stats import spearmanr

    lo, hi = float(min(pres.min(), bg.min())), float(max(pres.max(), bg.max()))
    w = width * (hi - lo)
    centres = np.linspace(lo + w / 2, hi - w / 2, n_win)
    ratios = []
    for c in centres:
        pf = np.mean((pres >= c - w / 2) & (pres <= c + w / 2))
        ef = np.mean((bg >= c - w / 2) & (bg <= c + w / 2))
        ratios.append(pf / ef if ef > 0 else np.nan)
    ratios = np.array(ratios)
    ok = ~np.isnan(ratios)
    # ecospat removes repeated consecutive P/E values before the correlation
    keep = ok.copy()
    idx = np.where(ok)[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if ratios[a] == ratios[b]:
            keep[b] = False
    if keep.sum() < 3:
        return float("nan")
    return float(spearmanr(centres[keep], ratios[keep]).statistic)


# ----------------------------------------------------------------------------- model
def make_model(fc: str, rm: float):
    import elapid as ela

    return ela.MaxentModel(
        feature_types=FC_GRID[fc],
        beta_multiplier=float(rm),
        transform="cloglog",
        clamp=True,  # predictions outside the training range are clamped
        use_lambdas="best",
        n_cpus=1,  # parallelism is across species
    )


def fit(fc: str, rm: float, X: np.ndarray, y: np.ndarray):
    return make_model(fc, rm).fit(X, y)


# ----------------------------------------------------------------------------- spatial blocks
def block_ids(lon: np.ndarray, lat: np.ndarray, size_km: float) -> np.ndarray:
    """Square blocks of ~size_km on a regular lon/lat lattice (degrees per km at mid-latitude)."""
    mid = np.deg2rad((GRID.lat_min + GRID.lat_max) / 2)
    dlat = size_km / 111.32
    dlon = size_km / (111.32 * np.cos(mid))
    bx = np.floor((lon - GRID.lon_min) / dlon).astype(int)
    by = np.floor((lat - GRID.lat_min) / dlat).astype(int)
    return by * 10_000 + bx


def assign_folds(blocks_pres: np.ndarray, blocks_bg: np.ndarray, k: int, seed: int, iters: int = 200):
    """Randomly assign blocks to k folds; keep the assignment with the most even presence
    count across folds (the 'iteration' idea of blockCV::cv_spatial)."""
    rng = np.random.default_rng(seed)
    ub = np.unique(np.r_[blocks_pres, blocks_bg])
    best, best_sd = None, np.inf
    for _ in range(iters):
        f = rng.integers(0, k, len(ub))
        fmap = dict(zip(ub, f))
        fp = np.array([fmap[b] for b in blocks_pres])
        counts = np.bincount(fp, minlength=k)
        if counts.min() == 0:
            continue
        sd = counts.std()
        if sd < best_sd:
            best, best_sd = fmap, sd
    fp = np.array([best[b] for b in blocks_pres])
    fb = np.array([best[b] for b in blocks_bg])
    return fp, fb


# ----------------------------------------------------------------------------- MESS
def mess(ref: np.ndarray, X: np.ndarray) -> np.ndarray:
    """Multivariate environmental similarity surface (Elith et al. 2010).
    ref: reference points x vars; X: prediction cells x vars. Returns min over variables."""
    out = np.full(len(X), np.inf)
    for j in range(ref.shape[1]):
        r = np.sort(ref[:, j])
        mn, mx = r[0], r[-1]
        rng = mx - mn if mx > mn else 1.0
        p = X[:, j]
        f = np.searchsorted(r, p, side="left") / len(r) * 100  # % of ref < p
        s = np.where(
            f == 0,
            (p - mn) / rng * 100,
            np.where(f <= 50, 2 * f, np.where(f < 100, 2 * (100 - f), (mx - p) / rng * 100)),
        )
        out = np.minimum(out, s)
    return out


__all__ = [
    "COVARIATE_NAMES",
    "COVARIATES",
    "PROCESSED",
    "turkey_mask",
    "read_raster",
]
