"""Validate model outputs against the shared contract.

    python scripts/validate_outputs.py                 # checks outputs/models (falls back to baseline)
    python scripts/validate_outputs.py outputs/baseline

Checks: grid (CRS, transform, shape), value ranges, missing species/files, NaN share
inside Turkey, metrics.csv columns. Exit code 1 if any ERROR.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common import OUTPUTS, PROCESSED, config, training_grid  # noqa: E402

METRIC_COLS = [
    "species_slug",
    "n_train_cells",
    "auc_mean",
    "auc_sd",
    "tss_mean",
    "tss_sd",
    "cbi_mean",
    "threshold",
    "threshold_method",
    "top_variables",
    "cv_method",
]
PER_SPECIES = {"suitability_mean": (0, 1), "suitability_sd": (0, 1), "binary": (0, 1)}


def model_dir() -> Path:
    final = OUTPUTS / "models"
    if (final / "metrics.csv").exists():
        return final
    return OUTPUTS / "baseline"


def main(folder: Path) -> int:
    grid = training_grid()
    with rasterio.open(PROCESSED / "turkey_mask.tif") as m:
        tr = m.read(1) == 1
    errors, warns = [], []
    species = pd.read_csv(PROCESSED / "species_list.csv")
    slugs = species.loc[species["selected"], "species_slug"].tolist()
    print(f"Validating {folder.relative_to(ROOT)} for {len(slugs)} selected species")

    def check(path: Path, lo=None, hi=None, required=True):
        if not path.exists():
            (errors if required else warns).append(f"missing: {path.name}")
            return
        with rasterio.open(path) as src:
            if src.crs is None or src.crs.to_epsg() != 4326:
                errors.append(f"{path.name}: CRS {src.crs} != EPSG:4326")
            if (src.height, src.width) != grid.shape:
                errors.append(f"{path.name}: shape {(src.height, src.width)} != {grid.shape}")
                return
            if not np.allclose(tuple(src.transform)[:6], tuple(grid.transform)[:6], atol=1e-6):
                errors.append(f"{path.name}: transform differs from shared grid")
            a = src.read(1).astype(float)
            if src.nodata is not None and not np.isnan(src.nodata):
                a[a == src.nodata] = np.nan
        nan_tr = float(np.isnan(a[tr]).mean())
        if nan_tr > 0.02:
            warns.append(f"{path.name}: {nan_tr:.1%} NaN inside Turkey")
        if lo is not None and np.nanmin(a) < lo - 1e-6:
            errors.append(f"{path.name}: min {np.nanmin(a):.3f} < {lo}")
        if hi is not None and np.nanmax(a) > hi + 1e-6:
            errors.append(f"{path.name}: max {np.nanmax(a):.3f} > {hi}")

    for s in slugs:
        for suffix, (lo, hi) in PER_SPECIES.items():
            check(folder / f"{s}_{suffix}.tif", lo, hi)
        for ssp in config()["future"]["scenarios"]:
            check(folder / f"{s}_future_{ssp}_mean.tif", 0, 1, required=(ssp == "ssp245"))
    check(folder / "richness_mean.tif", 0, len(slugs))
    check(folder / "richness_sd.tif", 0, None)

    mpath = folder / "metrics.csv"
    if not mpath.exists():
        errors.append("missing: metrics.csv")
    else:
        mt = pd.read_csv(mpath)
        missing_cols = [c for c in METRIC_COLS if c not in mt.columns]
        if missing_cols:
            errors.append(f"metrics.csv missing columns: {missing_cols}")
        missing_sp = sorted(set(slugs) - set(mt.get("species_slug", [])))
        if missing_sp:
            errors.append(f"metrics.csv missing species: {missing_sp}")
        if "auc_mean" in mt and ((mt["auc_mean"] < 0) | (mt["auc_mean"] > 1)).any():
            errors.append("metrics.csv: auc_mean outside [0,1]")

    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else model_dir()))
