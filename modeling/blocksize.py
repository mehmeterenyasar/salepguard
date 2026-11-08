"""Spatial block size from covariate spatial autocorrelation (idea of blockCV::cv_spatial_autocor).

For each selected covariate: empirical semivariogram on 3,000 random land cells, exponential model
fitted by least squares; effective range = distance where 95 % of the sill is reached. The block
size is the median range, capped to [100, 200] km (see docs/methods.md for the reason).

    python modeling/blocksize.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sdm import COVARIATE_NAMES, COVARIATES, GRID, MODELING, OUT, SEED, load_stack


def haversine_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.deg2rad, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def expo(h, nugget, psill, a):
    return nugget + psill * (1 - np.exp(-3 * h / a))  # a = effective (practical) range


def main() -> None:
    vars_ = (MODELING / "variables.txt").read_text().split()
    stack = load_stack(COVARIATES)
    valid = np.all(~np.isnan(stack), axis=0).ravel()
    rng = np.random.default_rng(SEED)
    cells = rng.choice(np.where(valid)[0], 3000, replace=False)
    r, c = np.divmod(cells, GRID.width)
    lon = GRID.lon_min + (c + 0.5) * GRID.res
    lat = GRID.lat_max - (r + 0.5) * GRID.res
    iu = np.triu_indices(len(cells), 1)
    d = haversine_km(lon[iu[0]], lat[iu[0]], lon[iu[1]], lat[iu[1]])
    bins = np.arange(0, 1525, 25)
    which = np.digitize(d, bins) - 1
    ok = (which >= 0) & (which < len(bins) - 1)
    mids = (bins[:-1] + bins[1:]) / 2
    rows = []
    for v in vars_:
        z = stack[COVARIATE_NAMES.index(v)].ravel()[cells]
        z = (z - z.mean()) / z.std()
        g = 0.5 * (z[iu[0]] - z[iu[1]]) ** 2
        gam = np.bincount(which[ok], weights=g[ok], minlength=len(mids))[: len(mids)]
        n = np.bincount(which[ok], minlength=len(mids))[: len(mids)]
        gam = gam / np.maximum(n, 1)
        try:
            p, _ = curve_fit(expo, mids, gam, p0=[0.05, 1.0, 300], bounds=([0, 0, 5], [2, 5, 5000]), maxfev=20000)
            rng_km = float(p[2])
        except RuntimeError:
            rng_km = np.nan
        rows.append(dict(variable=v, range_km=rng_km))
    tab = pd.DataFrame(rows)
    med = float(np.nanmedian(tab["range_km"]))
    chosen = float(np.clip(med, 100, 200)) if np.isfinite(med) else 150.0
    tab.loc[len(tab)] = dict(variable="median", range_km=med)
    tab.loc[len(tab)] = dict(variable="chosen_block_km", range_km=chosen)
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT / "tables" / "block_size_variogram.csv", index=False)
    (MODELING / "block_size_km.txt").write_text(f"{chosen:.0f}\n")
    print(tab.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
