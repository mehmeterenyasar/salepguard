"""Write the output contract (outputs/models/) from modeling/cache/.

    python modeling/assemble.py
Per species rasters, richness (binary + probability, bootstrap SD), MESS (current + SSPs),
future binaries, metrics.csv, range_change.csv, tables/tuning_all.csv.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from sdm import (
    CACHE,
    COVARIATE_NAMES,
    COVARIATES,
    MODELING,
    OUT,
    PROCESSED,
    SSPS,
    cell_area_km2,
    cells_of,
    future_folder,
    load_stack,
    mess,
    save_tif,
    to_grid,
    turkey_mask,
)

THR_METHOD = "maxSSS (max sensitivity+specificity, presence vs target-group background, bootstrap-mean surface)"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tables").mkdir(exist_ok=True)
    vars_ = (MODELING / "variables.txt").read_text().split()
    block_km = float((MODELING / "block_size_km.txt").read_text())
    vi = [COVARIATE_NAMES.index(v) for v in vars_]
    stack = load_stack(COVARIATES)
    valid = np.all(~np.isnan(stack), axis=0).ravel()
    flat = stack.reshape(len(COVARIATE_NAMES), -1).T
    grid_cells = np.load(CACHE / "grid_cells.npy")
    grid_X = flat[grid_cells][:, vi]
    fut_X = {}
    for ssp in SSPS:
        fs = load_stack(future_folder(ssp)).reshape(len(COVARIATE_NAMES), -1).T[grid_cells][:, vi]
        fut_X[ssp] = np.where(np.isnan(fs), grid_X, fs)
    tr_flat = turkey_mask().ravel()[grid_cells]
    area = cell_area_km2().ravel()[grid_cells]

    occ = pd.read_csv(PROCESSED / "occurrences_clean.csv")
    bg_cells = cells_of(pd.read_csv(PROCESSED / "background_targetgroup.csv"), valid)
    sp = pd.read_csv(PROCESSED / "species_list.csv")
    slugs = sp.loc[sp["selected"], "species_slug"].tolist()
    nullp = {}
    if (CACHE / "null_model.csv").exists():
        nullp = pd.read_csv(CACHE / "null_model.csv").set_index("species_slug")["null_model_p"].to_dict()

    rows, rc_rows, tune_all = [], [], []
    rich = np.zeros(len(grid_cells), "float32")
    rich_prob = np.zeros(len(grid_cells), "float32")
    rich_boot = None
    rich_fut = {s: np.zeros(len(grid_cells), "float32") for s in SSPS}
    done = []
    for s in slugs:
        if not (CACHE / f"{s}.npz").exists():
            print("missing in cache:", s)
            continue
        done.append(s)
        z = np.load(CACHE / f"{s}.npz")
        meta = json.loads((CACHE / f"{s}.json").read_text())
        summ = pd.read_csv(CACHE / f"{s}_tuning.csv")
        rcv = pd.read_csv(CACHE / f"{s}_random_cv.csv")
        summ.insert(0, "species_slug", s)
        tune_all.append(summ)
        b = summ[(summ["fc"] == meta["fc"]) & (summ["rm"] == meta["rm"])].iloc[0]
        thr = meta["thr_sss"]
        mean, sd = z["mean"], z["sd"]
        binary = (mean >= thr).astype("float32")
        save_tif(OUT / f"{s}_suitability_mean.tif", to_grid(np.clip(mean, 0, 1), grid_cells))
        save_tif(OUT / f"{s}_suitability_sd.tif", to_grid(np.clip(sd, 0, 1), grid_cells))
        save_tif(OUT / f"{s}_binary.tif", to_grid(binary, grid_cells))
        rich += binary
        rich_prob += mean
        bb = z["boot_bin"].astype("uint8")
        rich_boot = bb.astype("uint16") if rich_boot is None else rich_boot + bb

        # MESS: reference = this species' training cells (presences + target-group background)
        pc = cells_of(occ[occ["species_slug"] == s], valid)
        ref = np.vstack([flat[pc][:, vi], flat[bg_cells][:, vi]])
        m_cur = mess(ref, grid_X)
        save_tif(OUT / f"{s}_mess.tif", to_grid(m_cur.astype("float32"), grid_cells))
        for ssp in SSPS:
            fm = z[f"fut_{ssp}"]
            fbin = (fm >= thr).astype("float32")
            m_fut = mess(ref, fut_X[ssp])
            save_tif(OUT / f"{s}_future_{ssp}_mean.tif", to_grid(np.clip(fm, 0, 1), grid_cells))
            save_tif(OUT / f"{s}_future_{ssp}_binary.tif", to_grid(fbin, grid_cells))
            save_tif(OUT / f"{s}_mess_{ssp}.tif", to_grid(m_fut.astype("float32"), grid_cells))
            rich_fut[ssp] += fbin
            cur, fut = binary.astype(bool) & tr_flat, fbin.astype(bool) & tr_flat
            analog = m_fut >= 0
            a_cur = float(area[cur].sum())
            for disp in ["full", "none"]:
                f_ = fut if disp == "full" else fut & cur
                a_fut = float(area[f_].sum())
                lost = float(area[cur & ~f_].sum())
                kept = float(area[cur & f_].sum())
                gain = float(area[~cur & f_].sum())
                # same change restricted to analog (MESS >= 0) cells: separates signal from extrapolation
                ca, fa = cur & analog, f_ & analog
                rc_rows.append(dict(
                    species_slug=s, scenario=ssp, dispersal=disp, current_km2=round(a_cur), future_km2=round(a_fut),
                    lost_km2=round(lost), kept_km2=round(kept), gained_km2=round(gain),
                    change_pct=round((a_fut - a_cur) / a_cur * 100, 1) if a_cur > 0 else np.nan,
                    future_in_nonanalog_pct=round(float(area[f_ & ~analog].sum()) / a_fut * 100, 1) if a_fut > 0 else np.nan,
                    turkey_nonanalog_pct=round(float(area[tr_flat & ~analog].sum()) / float(area[tr_flat].sum()) * 100, 1),
                    change_pct_analog_only=round((float(area[fa].sum()) - float(area[ca].sum())) / float(area[ca].sum()) * 100, 1)
                    if area[ca].sum() > 0 else np.nan,
                ))

        imp = meta["imp"]
        top = [v for v, _ in sorted(imp.items(), key=lambda kv: -kv[1])[:3]]
        auc_sp, cbi = float(b["auc_mean"]), float(b["cbi_mean"])
        p_null = nullp.get(s, np.nan)
        reasons = []
        if cbi < 0:
            reasons.append("CBI<0")
        if auc_sp < 0.6:
            reasons.append("spatial AUC<0.6")
        if np.isfinite(p_null) and p_null > 0.05:
            reasons.append("null model p>0.05")
        rows.append(dict(
            species_slug=s, n_train_cells=meta["n_pres"], auc_mean=round(auc_sp, 4), auc_sd=round(float(b["auc_sd"]), 4),
            tss_mean=round(float(b["tss_mean"]), 4), tss_sd=round(float(b["tss_sd"]), 4), cbi_mean=round(cbi, 4),
            threshold=round(thr, 4), threshold_method=THR_METHOD,
            top_variables=";".join(top), cv_method=f"spatial block 5-fold ({block_km:.0f} km blocks)",
            n_records_raw=int((occ["species_slug"] == s).sum()), fc=meta["fc"], rm=meta["rm"],
            cbi_sd=round(float(b["cbi_sd"]), 4), omission10_mean=round(float(b["or10_mean"]), 4),
            auc_random_cv=round(float(rcv["auc"].mean()), 4), null_model_p=p_null, block_size_km=block_km,
            include_in_index=not reasons, exclusion_reason=";".join(reasons),
            threshold_p10=round(meta["thr_p10"], 4),
            suitable_share_turkey_maxsss=round(float(area[(mean >= thr) & tr_flat].sum() / area[tr_flat].sum()), 4),
            suitable_share_turkey_p10=round(float(area[(mean >= meta["thr_p10"]) & tr_flat].sum() / area[tr_flat].sum()), 4),
            importance=";".join(f"{v}:{imp[v]:.0f}" for v in sorted(imp, key=lambda k: -imp[k])),
            n_bootstrap=int(z["boot_bin"].shape[0]),
        ))

    if len(done) == len(slugs):
        save_tif(OUT / "richness_mean.tif", to_grid(rich, grid_cells))
        save_tif(OUT / "richness_sd.tif", to_grid(rich_boot.std(0).astype("float32"), grid_cells))
        save_tif(OUT / "richness_prob_mean.tif", to_grid(rich_prob, grid_cells))
        for ssp in SSPS:
            save_tif(OUT / f"richness_future_{ssp}.tif", to_grid(rich_fut[ssp], grid_cells))
    else:
        print(f"richness skipped: {len(done)}/{len(slugs)} species in cache")
    pd.DataFrame(rows).to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame(rc_rows).to_csv(OUT / "range_change.csv", index=False)
    pd.concat(tune_all).to_csv(OUT / "tables" / "tuning_all.csv", index=False)
    print(pd.DataFrame(rows)[["species_slug", "n_train_cells", "fc", "rm", "auc_mean", "auc_random_cv", "tss_mean",
                              "cbi_mean", "omission10_mean", "include_in_index"]].to_string(index=False))


if __name__ == "__main__":
    main()
