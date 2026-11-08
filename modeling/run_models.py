"""Final SalepGuard SDMs: bias-corrected MaxEnt, spatial block CV tuning, bootstrap uncertainty.

    python modeling/run_models.py                       # all selected species
    python modeling/run_models.py orchis_anatolica      # one species (test)
    python modeling/run_models.py --n-boot 3 --rm 1,2 orchis_anatolica   # quick timing test

Per species (results cached in modeling/cache/<slug>.npz; use --force to refit):
  presences  = unique 2.5' cells with a cleaned record (thinning: 1 record per cell)
  background = all unique target-group (Orchidaceae) cells (Phillips et al. 2009)
  tuning     = fc {L, LQ, LQH} x rm {0.5, 1, 2, 4}, 5-fold spatial block CV
               selection: lowest mean 10 % omission rate, ties -> highest mean validation AUC
  metrics    = per fold AUC, TSS (maxSSS threshold from the training folds), CBI, OR10
  random CV  = same fc/rm, 5-fold random CV AUC (to show the optimism of random CV)
  bootstrap  = n refits on presences resampled with replacement -> mean / SD (current + future)
Run modeling/assemble.py afterwards to write outputs/models/.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from sdm import (
    CACHE,
    COVARIATE_NAMES,
    COVARIATES,
    FC_GRID,
    MODELING,
    PROCESSED,
    RM_GRID,
    SEED,
    SSPS,
    assign_folds,
    auc,
    block_ids,
    boyce,
    cell_lonlat,
    cells_of,
    fit,
    future_folder,
    load_stack,
    maxsss_threshold,
    p10_threshold,
    tss_at,
)


def fold_metrics(m, Xtr_p, Xtr_b, Xte_p, Xte_b) -> dict:
    ptr_p, ptr_b = m.predict(Xtr_p), m.predict(Xtr_b)
    pte_p, pte_b = m.predict(Xte_p), m.predict(Xte_b)
    thr_sss = maxsss_threshold(ptr_p, ptr_b)
    thr10 = p10_threshold(ptr_p)
    y = np.r_[np.ones(len(pte_p)), np.zeros(len(pte_b))]
    return dict(
        auc=auc(y, np.r_[pte_p, pte_b]),
        tss=tss_at(pte_p, pte_b, thr_sss),
        cbi=boyce(pte_p, pte_b),
        or10=float(np.mean(pte_p < thr10)),
    )


def run_cv(fc, rm, Xp, Xb, fp, fb, k) -> list[dict]:
    out = []
    for f in range(k):
        trp, tep, trb, teb = fp != f, fp == f, fb != f, fb == f
        if tep.sum() == 0 or teb.sum() == 0:
            continue
        X = np.vstack([Xp[trp], Xb[trb]])
        y = np.r_[np.ones(trp.sum()), np.zeros(trb.sum())]
        m = fit(fc, rm, X, y)
        out.append(dict(fold=f, **fold_metrics(m, Xp[trp], Xb[trb], Xp[tep], Xb[teb])))
    return out


def permutation_importance(m, Xp, Xb, names, rng, repeats=3) -> dict:
    y = np.r_[np.ones(len(Xp)), np.zeros(len(Xb))]
    X = np.vstack([Xp, Xb])
    base = auc(y, m.predict(X))
    imp = {}
    for j, v in enumerate(names):
        drops = []
        for _ in range(repeats):
            Xs = X.copy()
            Xs[:, j] = rng.permutation(Xs[:, j])
            drops.append(base - auc(y, m.predict(Xs)))
        imp[v] = float(np.mean(drops))
    tot = sum(max(d, 0) for d in imp.values()) or 1.0
    return {v: max(d, 0) / tot * 100 for v, d in imp.items()}


def response_curves(m, Xp, Xb, names, n=100) -> dict:
    X = np.vstack([Xp, Xb])
    med = np.median(X, axis=0)
    curves = {}
    for j, v in enumerate(names):
        xs = np.linspace(np.percentile(X[:, j], 1), np.percentile(X[:, j], 99), n)
        Z = np.tile(med, (n, 1))
        Z[:, j] = xs
        curves[v] = (xs, m.predict(Z))
    return curves


def fit_species(job: dict) -> dict:
    warnings.filterwarnings("ignore")
    t0 = time.time()
    slug, Xp, Xb, k = job["slug"], job["Xp"], job["Xb"], job["k"]
    rng = np.random.default_rng(job["seed"])
    fp, fb = assign_folds(job["blk_p"], job["blk_b"], k, job["seed"])

    # ---- tuning under spatial block CV
    tune = []
    for fc in job["fcs"]:
        for rm in job["rms"]:
            for r in run_cv(fc, rm, Xp, Xb, fp, fb, k):
                tune.append(dict(fc=fc, rm=rm, **r))
    tune = pd.DataFrame(tune)
    summ = tune.groupby(["fc", "rm"]).agg(
        auc_mean=("auc", "mean"), auc_sd=("auc", "std"), tss_mean=("tss", "mean"), tss_sd=("tss", "std"),
        cbi_mean=("cbi", "mean"), cbi_sd=("cbi", "std"), or10_mean=("or10", "mean"), n_folds=("auc", "size"),
    ).reset_index()
    best = summ.sort_values(["or10_mean", "auc_mean"], ascending=[True, False]).iloc[0]
    fc, rm = best["fc"], float(best["rm"])
    t_tune = time.time() - t0

    # ---- random 5-fold CV with the selected settings
    from sklearn.model_selection import KFold

    rp = np.zeros(len(Xp), int)
    rb = np.zeros(len(Xb), int)
    for f, (_, te) in enumerate(KFold(k, shuffle=True, random_state=job["seed"]).split(Xp)):
        rp[te] = f
    for f, (_, te) in enumerate(KFold(k, shuffle=True, random_state=job["seed"]).split(Xb)):
        rb[te] = f
    rcv = pd.DataFrame(run_cv(fc, rm, Xp, Xb, rp, rb, k))

    # ---- full model: thresholds, importance, response curves
    X = np.vstack([Xp, Xb])
    y = np.r_[np.ones(len(Xp)), np.zeros(len(Xb))]
    full = fit(fc, rm, X, y)
    pp, pb = full.predict(Xp), full.predict(Xb)
    imp = permutation_importance(full, Xp, Xb, job["vars"], rng)
    curves = response_curves(full, Xp, Xb, job["vars"])

    # ---- bootstrap
    preds, fut, boot_bin, fut_bin = [], {s: [] for s in job["fut"]}, [], {s: [] for s in job["fut"]}
    for _ in range(job["n_boot"]):
        idx = rng.integers(0, len(Xp), len(Xp))
        Xbt = np.vstack([Xp[idx], Xb])
        ybt = np.r_[np.ones(len(idx)), np.zeros(len(Xb))]
        m = fit(fc, rm, Xbt, ybt)
        thr = maxsss_threshold(m.predict(Xp[idx]), m.predict(Xb))
        p = m.predict(job["grid_X"]).astype("float32")
        preds.append(p)
        boot_bin.append(p >= thr)
        for s, fx in job["fut"].items():
            pf = m.predict(fx).astype("float32")
            fut[s].append(pf)
            fut_bin[s].append(pf >= thr)
    preds = np.array(preds)
    mean = preds.mean(0)
    sd = preds.std(0)
    # threshold on the bootstrap-mean surface at the training cells
    pres_mean = mean[job["pres_pos"]]
    bg_mean = mean[job["bg_pos"]]
    thr_sss = maxsss_threshold(pres_mean, bg_mean)
    thr_p10 = p10_threshold(pres_mean)

    return dict(
        slug=slug, fc=fc, rm=rm, tune=tune, summ=summ, rcv=rcv, imp=imp, curves=curves,
        mean=mean, sd=sd, boot_bin=np.array(boot_bin), fut={s: np.mean(v, 0) for s, v in fut.items()},
        fut_bin_share={s: np.mean(v, 0).astype("float32") for s, v in fut_bin.items()},
        thr_sss=thr_sss, thr_p10=thr_p10, thr_full=maxsss_threshold(pp, pb),
        n_pres=len(Xp), n_bg=len(Xb), fold_counts=np.bincount(fp, minlength=k).tolist(),
        secs=time.time() - t0, secs_tune=t_tune,
    )


def save(res: dict) -> None:
    s = res["slug"]
    res["tune"].to_csv(CACHE / f"{s}_tuning_folds.csv", index=False)
    res["summ"].to_csv(CACHE / f"{s}_tuning.csv", index=False)
    res["rcv"].to_csv(CACHE / f"{s}_random_cv.csv", index=False)
    arrays = dict(mean=res["mean"], sd=res["sd"], boot_bin=res["boot_bin"])
    for ssp, v in res["fut"].items():
        arrays[f"fut_{ssp}"] = v
        arrays[f"futbin_{ssp}"] = res["fut_bin_share"][ssp]
    for v, (xs, ys) in res["curves"].items():
        arrays[f"curve_x_{v}"] = xs
        arrays[f"curve_y_{v}"] = ys
    np.savez_compressed(CACHE / f"{s}.npz", **arrays)
    meta = {k: res[k] for k in ["slug", "fc", "rm", "imp", "thr_sss", "thr_p10", "thr_full", "n_pres", "n_bg",
                                  "fold_counts", "secs", "secs_tune"]}
    (CACHE / f"{s}.json").write_text(json.dumps(meta, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("species", nargs="*")
    ap.add_argument("--n-boot", type=int, default=20)
    ap.add_argument("--rm", default=",".join(str(r) for r in RM_GRID))
    ap.add_argument("--fc", default=",".join(FC_GRID))
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    vars_ = (MODELING / "variables.txt").read_text().split()
    block_km = float((MODELING / "block_size_km.txt").read_text())
    vi = [COVARIATE_NAMES.index(v) for v in vars_]
    stack = load_stack(COVARIATES)
    valid = np.all(~np.isnan(stack), axis=0).ravel()
    flat = stack.reshape(len(COVARIATE_NAMES), -1).T
    grid_cells = np.where(valid)[0]
    pos = np.full(len(valid), -1)
    pos[grid_cells] = np.arange(len(grid_cells))
    grid_X = flat[grid_cells][:, vi]
    fut_X = {}
    for ssp in SSPS:
        if not (future_folder(ssp) / "bio01.tif").exists():
            print(f"WARNING: no future covariates for {ssp}; skipped (test runs only)")
            continue
        fs = load_stack(future_folder(ssp)).reshape(len(COVARIATE_NAMES), -1).T[grid_cells][:, vi]
        fut_X[ssp] = np.where(np.isnan(fs), grid_X, fs)  # rare coastal NA -> current value
    np.save(CACHE / "grid_cells.npy", grid_cells)

    occ = pd.read_csv(PROCESSED / "occurrences_clean.csv")
    bg_cells = cells_of(pd.read_csv(PROCESSED / "background_targetgroup.csv"), valid)
    blon, blat = cell_lonlat(bg_cells)
    sp = pd.read_csv(PROCESSED / "species_list.csv")
    slugs = sp.loc[sp["selected"], "species_slug"].tolist()
    if a.species:
        slugs = [s for s in slugs if s in a.species]
    order = {s: i for i, s in enumerate(sp.loc[sp["selected"], "species_slug"])}
    jobs = []
    for s in slugs:
        if (CACHE / f"{s}.npz").exists() and not a.force:
            print(f"cached, skip: {s}")
            continue
        pc = cells_of(occ[occ["species_slug"] == s], valid)
        plon, plat = cell_lonlat(pc)
        jobs.append(dict(
            slug=s, Xp=flat[pc][:, vi], Xb=flat[bg_cells][:, vi], k=5, vars=vars_,
            blk_p=block_ids(plon, plat, block_km), blk_b=block_ids(blon, blat, block_km),
            fcs=a.fc.split(","), rms=[float(r) for r in a.rm.split(",")], n_boot=a.n_boot,
            grid_X=grid_X, fut=fut_X, pres_pos=pos[pc], bg_pos=pos[bg_cells], seed=SEED + order[s],
        ))
    print(f"{len(jobs)} species, block {block_km:.0f} km, vars {vars_}, n_boot {a.n_boot}, workers {a.workers}")
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=min(a.workers, max(1, len(jobs)))) as ex:
        futs = {ex.submit(fit_species, j): j["slug"] for j in jobs}
        for f in as_completed(futs):
            r = f.result()
            save(r)
            b = r["summ"].query("fc == @r['fc'] and rm == @r['rm']").iloc[0]
            print(f"{time.strftime('%H:%M:%S')} {r['slug']:<30} n={r['n_pres']:4d} fc={r['fc']:<3} rm={r['rm']:<3} "
                  f"AUCsp={b['auc_mean']:.3f} TSS={b['tss_mean']:.3f} CBI={b['cbi_mean']:.2f} OR10={b['or10_mean']:.2f} "
                  f"AUCrand={r['rcv']['auc'].mean():.3f} ({r['secs']:.0f}s, tune {r['secs_tune']:.0f}s)", flush=True)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
