"""Null-model significance test (Raes & ter Steege 2007), bias-aware variant.

For a species with n presence cells, draw n cells at random from the target-group background
(same sampling bias, no species signal), fit MaxEnt with the species' selected fc/rm and evaluate it
with the same spatial block CV. p = (#null AUC >= observed AUC + 1) / (n_null + 1).

    python modeling/null_model.py --n-null 49 sp1 sp2 sp3
Writes modeling/cache/null_model.csv (read by assemble.py).
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from run_models import run_cv
from sdm import (
    CACHE,
    COVARIATE_NAMES,
    COVARIATES,
    MODELING,
    PROCESSED,
    SEED,
    assign_folds,
    block_ids,
    cell_lonlat,
    cells_of,
    load_stack,
)


def one(job):
    warnings.filterwarnings("ignore")
    rng = np.random.default_rng(job["seed"])
    nb = len(job["Xb"])
    idx = rng.choice(nb, job["n"], replace=False)
    Xp, blk_p = job["Xb"][idx], job["blk_b"][idx]
    fp, fb = assign_folds(blk_p, job["blk_b"], 5, job["seed"], iters=50)
    r = run_cv(job["fc"], job["rm"], Xp, job["Xb"], fp, fb, 5)
    return job["slug"], float(np.mean([x["auc"] for x in r]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("species", nargs="+")
    ap.add_argument("--n-null", type=int, default=49)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    a = ap.parse_args()
    vars_ = (MODELING / "variables.txt").read_text().split()
    block_km = float((MODELING / "block_size_km.txt").read_text())
    vi = [COVARIATE_NAMES.index(v) for v in vars_]
    stack = load_stack(COVARIATES)
    valid = np.all(~np.isnan(stack), axis=0).ravel()
    flat = stack.reshape(len(COVARIATE_NAMES), -1).T
    occ = pd.read_csv(PROCESSED / "occurrences_clean.csv")
    bg = cells_of(pd.read_csv(PROCESSED / "background_targetgroup.csv"), valid)
    blon, blat = cell_lonlat(bg)
    blk_b = block_ids(blon, blat, block_km)
    jobs, obs = [], {}
    for s in a.species:
        meta = json.loads((CACHE / f"{s}.json").read_text())
        summ = pd.read_csv(CACHE / f"{s}_tuning.csv")
        obs[s] = float(summ[(summ["fc"] == meta["fc"]) & (summ["rm"] == meta["rm"])]["auc_mean"].iloc[0])
        n = len(cells_of(occ[occ["species_slug"] == s], valid))
        for i in range(a.n_null):
            jobs.append(dict(slug=s, n=n, Xb=flat[bg][:, vi], blk_b=blk_b, fc=meta["fc"], rm=meta["rm"],
                             seed=SEED * 1000 + i))
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    df = pd.DataFrame(res, columns=["species_slug", "null_auc"])
    out = []
    for s, g in df.groupby("species_slug"):
        k = int((g["null_auc"] >= obs[s]).sum())
        out.append(dict(species_slug=s, auc_observed=obs[s], null_auc_mean=g["null_auc"].mean(),
                        null_auc_q95=g["null_auc"].quantile(0.95), n_null=len(g),
                        null_model_p=(k + 1) / (len(g) + 1)))
    path = CACHE / "null_model.csv"
    old = pd.read_csv(path) if path.exists() else pd.DataFrame()
    new = pd.concat([old[~old.get("species_slug", pd.Series(dtype=str)).isin(a.species)] if len(old) else old,
                     pd.DataFrame(out)])
    new.to_csv(path, index=False)
    df.to_csv(CACHE / "null_model_draws.csv", mode="a", index=False, header=not (CACHE / "null_model_draws.csv").exists())
    print(pd.DataFrame(out).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
