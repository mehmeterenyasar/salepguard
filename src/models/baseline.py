"""Fallback baseline species distribution model (Python, elapid MaxEnt).

This is NOT the main model (that lives in modeling/, by the teammate). It exists so the
dashboard and risk index always have inputs, and as a robustness comparison.

Per selected species:
  * presences  = unique 2.5' cells with a cleaned record (1 record per cell)
  * background = target-group background (unique cells of all cleaned Orchidaceae records)
  * covariates = greedy subset of bio01..bio19 + elevation with |r| <= 0.7 on background
  * MaxEnt (linear + quadratic + hinge), cloglog output
  * 5-fold random CV -> AUC, TSS, continuous Boyce index (CBI)
  * threshold = max(sensitivity + specificity) on pooled CV predictions
  * n bootstrap refits (presences resampled) -> suitability mean / SD
Outputs follow the shared contract, under outputs/baseline/.
"""

from __future__ import annotations

import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.common import COVARIATE_NAMES, COVARIATES, OUTPUTS, PROCESSED, config, get_logger, \
    read_raster, training_grid, write_raster

log = get_logger("baseline")
OUT = OUTPUTS / "baseline"
PRIORITY_ORDER = ["bio01", "bio12", "bio04", "bio15", "bio05", "bio06", "bio10", "bio11", "bio16",
                  "bio17", "bio18", "bio19", "bio02", "bio03", "bio07", "bio08", "bio09", "bio13",
                  "bio14", "elevation"]


def load_stack(folder) -> np.ndarray:
    return np.stack([read_raster(folder / f"{v}.tif") for v in COVARIATE_NAMES])


def select_variables(X_bg: pd.DataFrame, max_r: float) -> list[str]:
    corr = X_bg.corr().abs()
    keep: list[str] = []
    for v in PRIORITY_ORDER:
        if all(corr.loc[v, k] <= max_r for k in keep):
            keep.append(v)
    return keep


def auc(y, p) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(y, p))


def max_tss(y, p) -> tuple[float, float]:
    from sklearn.metrics import roc_curve

    fpr, tpr, thr = roc_curve(y, p)
    j = tpr - fpr
    i = int(np.argmax(j))
    return float(j[i]), float(min(thr[i], 1.0))


def boyce(pres: np.ndarray, bg: np.ndarray, n_win: int = 101, width: float = 0.1) -> float:
    """Continuous Boyce index (Hirzel et al. 2006): Spearman r of P/E ratio over moving windows."""
    from scipy.stats import spearmanr

    lo, hi = float(min(pres.min(), bg.min())), float(max(pres.max(), bg.max()))
    w = width * (hi - lo)
    centres = np.linspace(lo + w / 2, hi - w / 2, n_win)
    ratios = []
    for c in centres:
        p = np.mean((pres >= c - w / 2) & (pres <= c + w / 2))
        e = np.mean((bg >= c - w / 2) & (bg <= c + w / 2))
        ratios.append(p / e if e > 0 else np.nan)
    ratios = np.array(ratios)
    ok = ~np.isnan(ratios)
    if ok.sum() < 3:
        return float("nan")
    return float(spearmanr(centres[ok], ratios[ok]).statistic)


def make_model():
    import elapid as ela

    return ela.MaxentModel(feature_types=["linear", "quadratic", "hinge"], beta_multiplier=1.5,
                           transform="cloglog", n_hinge_features=10, use_lambdas="best")


def fit_species(args) -> dict:
    slug, pres_X, bg_X, grid_X, fut_X, n_boot, n_folds, seed = args
    warnings.filterwarnings("ignore")
    from sklearn.model_selection import StratifiedKFold

    t0 = time.time()
    rng = np.random.default_rng(seed)
    X = np.vstack([pres_X, bg_X])
    y = np.r_[np.ones(len(pres_X)), np.zeros(len(bg_X))]

    # cross-validation
    cv_pred = np.zeros(len(y))
    aucs, tsss, cbis = [], [], []
    for tr, te in StratifiedKFold(n_folds, shuffle=True, random_state=seed).split(X, y):
        m = make_model().fit(X[tr], y[tr])
        p = m.predict(X[te])
        cv_pred[te] = p
        aucs.append(auc(y[te], p))
        tsss.append(max_tss(y[te], p)[0])
        cbis.append(boyce(p[y[te] == 1], p[y[te] == 0]))
    _, thr = max_tss(y, cv_pred)

    # bootstrap refits on resampled presences
    preds, futs, bins = [], {k: [] for k in fut_X}, []
    for _ in range(n_boot):
        idx = rng.integers(0, len(pres_X), len(pres_X))
        Xb = np.vstack([pres_X[idx], bg_X])
        yb = np.r_[np.ones(len(idx)), np.zeros(len(bg_X))]
        m = make_model().fit(Xb, yb)
        p = m.predict(grid_X).astype("float32")
        preds.append(p)
        bins.append(p >= thr)
        for k, fx in fut_X.items():
            futs[k].append(m.predict(fx).astype("float32"))
    preds = np.array(preds)
    return {
        "slug": slug, "mean": preds.mean(0), "sd": preds.std(0), "boot_binary": np.array(bins),
        "future": {k: np.mean(v, axis=0) for k, v in futs.items()}, "threshold": thr,
        "auc_mean": np.mean(aucs), "auc_sd": np.std(aucs), "tss_mean": np.mean(tsss),
        "tss_sd": np.std(tsss), "cbi_mean": np.nanmean(cbis), "n_train_cells": len(pres_X),
        "seconds": time.time() - t0,
    }


def main(only: list[str] | None = None) -> None:
    cfg = config()["baseline_model"]
    seed = config()["project"]["random_seed"]
    grid = training_grid()
    OUT.mkdir(parents=True, exist_ok=True)

    stack = load_stack(COVARIATES)
    valid = np.all(~np.isnan(stack), axis=0)
    flat = stack.reshape(len(COVARIATE_NAMES), -1).T  # cells x vars
    cell_ok = valid.ravel()

    def cells_of(df):
        r, c, inside = grid.cell_index(df["decimalLongitude"], df["decimalLatitude"])
        cells = np.unique((r * grid.width + c)[inside])
        return cells[cell_ok[cells]]

    occ = pd.read_csv(PROCESSED / "occurrences_clean.csv")
    bg_cells = cells_of(pd.read_csv(PROCESSED / "background_targetgroup.csv"))
    rng = np.random.default_rng(seed)
    if len(bg_cells) > cfg["n_background"]:
        bg_cells = rng.choice(bg_cells, cfg["n_background"], replace=False)
    bg_df = pd.DataFrame(flat[bg_cells], columns=COVARIATE_NAMES)
    vars_ = select_variables(bg_df, cfg["max_abs_correlation"])
    vi = [COVARIATE_NAMES.index(v) for v in vars_]
    log.info("background cells=%d; selected variables (|r|<=%.1f): %s", len(bg_cells),
             cfg["max_abs_correlation"], ", ".join(vars_))

    pred_cells = np.where(cell_ok)[0]
    grid_X = flat[pred_cells][:, vi]
    fut_X = {}
    fc = config()["future"]
    for ssp in fc["scenarios"]:
        folder = PROCESSED / "covariates_future" / f"{ssp}_{fc['period']}"
        if (folder / "bio01.tif").exists():
            fs = load_stack(folder).reshape(len(COVARIATE_NAMES), -1).T[pred_cells][:, vi]
            fut_X[ssp] = np.nan_to_num(fs, nan=np.nanmean(fs))

    species = pd.read_csv(PROCESSED / "species_list.csv")
    species = species[species["selected"]]
    if only:
        species = species[species["species_slug"].isin(only)]
    jobs = []
    for i, (slug,) in enumerate(species[["species_slug"]].itertuples(index=False)):
        pres = cells_of(occ[occ["species_slug"] == slug])
        jobs.append((slug, flat[pres][:, vi], flat[bg_cells][:, vi], grid_X, fut_X,
                     cfg["n_bootstrap"], cfg["cv_folds"], seed + i))
    log.info("fitting %d species (%d bootstrap each)", len(jobs), cfg["n_bootstrap"])

    def to_grid(v, fill=np.nan, dtype="float32"):
        arr = np.full(grid.height * grid.width, fill, dtype=dtype)
        arr[pred_cells] = v
        return arr.reshape(grid.shape)

    rows, rich_boot, rich_mean = [], None, None
    with ProcessPoolExecutor(max_workers=max(1, min(8, (__import__("os").cpu_count() or 2) - 1))) as ex:
        for res in ex.map(fit_species, jobs):
            s = res["slug"]
            write_raster(OUT / f"{s}_suitability_mean.tif", to_grid(res["mean"]))
            write_raster(OUT / f"{s}_suitability_sd.tif", to_grid(res["sd"]))
            binary = (res["mean"] >= res["threshold"]).astype("float32")
            write_raster(OUT / f"{s}_binary.tif", to_grid(binary))
            for k, v in res["future"].items():
                write_raster(OUT / f"{s}_future_{k}_mean.tif", to_grid(v))
            bb = res["boot_binary"].astype("uint16")
            rich_boot = bb if rich_boot is None else rich_boot + bb
            rich_mean = binary if rich_mean is None else rich_mean + binary
            rows.append({"species_slug": s, "n_train_cells": res["n_train_cells"],
                         "auc_mean": round(res["auc_mean"], 4), "auc_sd": round(res["auc_sd"], 4),
                         "tss_mean": round(res["tss_mean"], 4), "tss_sd": round(res["tss_sd"], 4),
                         "cbi_mean": round(res["cbi_mean"], 4), "threshold": round(res["threshold"], 4),
                         "threshold_method": "max_sens_spec (pooled 5-fold CV)",
                         "top_variables": ";".join(vars_), "cv_method": "random 5-fold"})
            log.info("%-32s cells=%4d AUC=%.3f TSS=%.3f CBI=%.2f (%.0fs)", s, res["n_train_cells"],
                     res["auc_mean"], res["tss_mean"], res["cbi_mean"], res["seconds"])
    if only is None and rows:
        write_raster(OUT / "richness_mean.tif", to_grid(rich_mean))
        write_raster(OUT / "richness_sd.tif", to_grid(rich_boot.std(0).astype("float32")))
        pd.DataFrame(rows).sort_values("species_slug").to_csv(OUT / "metrics.csv", index=False)
    (OUT / "variables.txt").write_text("\n".join(vars_), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
