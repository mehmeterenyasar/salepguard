"""SalepGuard Priority Index, uncertainty, sensitivity, climate change, province ranking and
protection-gap analysis. All computed inside the Turkey mask.

    harvest_risk_s     = suitability_s * pressure
    unprotected_risk_s = harvest_risk_s * (1 - protected)
    priority           = sum_s w_s * unprotected_risk_s           (normalised to 0-1)

Uncertainty (first-order propagation, species treated as independent):
    sd(priority_raw) = sqrt( sum_s (w_s * pressure * (1 - protected))^2 * sd_s^2 )
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.common import (
    OUTPUTS,
    PROCESSED,
    config,
    get_logger,
    read_raster,
    read_vector,
    training_grid,
    write_raster,
)

log = get_logger("risk")
OUT = OUTPUTS / "risk"


def model_source() -> tuple[str, object]:
    final = OUTPUTS / "models"
    if (final / "metrics.csv").exists():
        return "final", final
    return "baseline", OUTPUTS / "baseline"


def cell_area_km2() -> np.ndarray:
    g = training_grid()
    _, lat = g.cell_centers()
    side = g.res * 111.32
    return (side * side * np.cos(np.radians(lat))).astype("float32")


# ---------- pure functions (unit-tested) ----------


def priority_index(
    suit: np.ndarray, pressure: np.ndarray, protected: np.ndarray, weights: np.ndarray | None = None
) -> np.ndarray:
    """suit: (n_species, H, W). Returns raw (un-normalised) priority."""
    w = np.ones(suit.shape[0]) if weights is None else np.asarray(weights, float)
    unprot = suit * (pressure * (1.0 - protected))[None]
    return np.tensordot(w, unprot, axes=1)


def priority_sd(
    sd: np.ndarray, pressure: np.ndarray, protected: np.ndarray, weights: np.ndarray | None = None
) -> np.ndarray:
    w = np.ones(sd.shape[0]) if weights is None else np.asarray(weights, float)
    factor = (pressure * (1.0 - protected)) ** 2
    return np.sqrt(np.tensordot(w**2, sd**2, axes=1) * factor)


def top_mask(values: np.ndarray, mask: np.ndarray, fraction: float) -> np.ndarray:
    v = values[mask]
    thr = np.nanquantile(v, 1 - fraction)
    return mask & (values >= thr)


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 1.0


# ---------- pipeline ----------


def main() -> None:
    cfg = config()
    rcfg = cfg["risk"]
    OUT.mkdir(parents=True, exist_ok=True)
    source, mdir = model_source()
    tr = read_raster(PROCESSED / "turkey_mask.tif") == 1
    pressure = np.nan_to_num(read_raster(PROCESSED / "pressure_index.tif"), nan=0.0)
    protected = np.nan_to_num(read_raster(PROCESSED / "protected_areas.tif"), nan=0.0)
    area = cell_area_km2()

    sp_list = pd.read_csv(PROCESSED / "species_list.csv")
    metrics = pd.read_csv(mdir / "metrics.csv")
    slugs = [
        s
        for s in sp_list.loc[sp_list["selected"], "species_slug"]
        if (mdir / f"{s}_suitability_mean.tif").exists()
    ]
    names = dict(zip(sp_list["species_slug"], sp_list["species"]))
    thr = dict(zip(metrics["species_slug"], metrics["threshold"]))
    log.info("model source=%s, species=%d", source, len(slugs))

    def stack(suffix):
        return np.stack([np.nan_to_num(read_raster(mdir / f"{s}_{suffix}.tif"), nan=0.0) for s in slugs])

    suit, sd, binary = stack("suitability_mean"), stack("suitability_sd"), stack("binary")
    sw = rcfg.get("species_weights") or {}
    weights = np.array([float(sw.get(s, 1.0)) for s in slugs])

    raw = priority_index(suit, pressure, protected, weights)
    raw_sd = priority_sd(sd, pressure, protected, weights)
    scale = float(np.nanmax(raw[tr])) or 1.0
    prio = np.where(tr, raw / scale, np.nan)
    prio_sd = np.where(tr, raw_sd / scale, np.nan)
    cv = np.where(tr & (raw > 0), raw_sd / np.maximum(raw, 1e-9), np.nan)
    hot = top_mask(prio, tr, rcfg["hotspot_top_fraction"])
    hot_thr = float(np.nanquantile(prio[tr], 1 - rcfg["hotspot_top_fraction"]))
    # robust = still above the hotspot threshold at the lower one-sided bound (priority - z * SD)
    robust = hot & ((prio - rcfg["robust_z"] * prio_sd) >= hot_thr)
    hot_class = np.where(tr, 0, np.nan).astype("float32")
    hot_class[hot] = 1
    hot_class[robust] = 2

    write_raster(OUT / "priority_index.tif", prio)
    write_raster(OUT / "priority_sd.tif", prio_sd)
    write_raster(OUT / "priority_cv.tif", cv)
    write_raster(OUT / "hotspot_class.tif", hot_class)  # 0 none, 1 hotspot, 2 robust hotspot
    harvest = np.where(tr, np.tensordot(weights, suit * pressure[None], axes=1), np.nan)
    write_raster(OUT / "harvest_risk_sum.tif", harvest / np.nanmax(harvest))
    richness = np.where(tr, binary.sum(0), np.nan)
    write_raster(OUT / "richness_binary_turkey.tif", richness)

    # ---- sensitivity: pressure-weight scenarios and binary-vs-continuous suitability ----
    rows = []
    frac = rcfg["hotspot_top_fraction"]
    for name in cfg["pressure"]["sensitivity_scenarios"]:
        p = np.nan_to_num(
            read_raster(PROCESSED / "pressure_scenarios" / f"pressure_index_{name}.tif"), nan=0.0
        )
        for variant, s_in in [("continuous suitability", suit), ("binary suitability", binary)]:
            pr = np.where(tr, priority_index(s_in, p, protected, weights), np.nan)
            pr = pr / np.nanmax(pr)
            if variant == "continuous suitability":
                write_raster(OUT / "scenarios" / f"priority_{name}.tif", pr)
            for f in (0.025, frac, 0.10):
                h = top_mask(pr, tr, f)
                r = top_mask(prio, tr, f)
                rows.append(
                    {
                        "pressure_scenario": name,
                        "suitability_input": variant,
                        "top_fraction": f,
                        "jaccard_vs_reference": round(jaccard(h, r), 3),
                        "n_cells": int(h.sum()),
                    }
                )
    sens = pd.DataFrame(rows)
    sens.to_csv(OUT / "sensitivity_jaccard.csv", index=False)

    # ---- climate change (pressure held constant) ----
    clim_rows, fut_summary = [], {}
    for ssp in cfg["future"]["scenarios"]:
        paths = [mdir / f"{s}_future_{ssp}_mean.tif" for s in slugs]
        if not all(p.exists() for p in paths):
            continue
        fut = np.stack([np.nan_to_num(read_raster(p), nan=0.0) for p in paths])
        fprio = np.where(tr, priority_index(fut, pressure, protected, weights) / scale, np.nan)
        write_raster(OUT / f"priority_future_{ssp}.tif", fprio)
        write_raster(OUT / f"priority_change_{ssp}.tif", fprio - prio)
        fbin = fut >= np.array([thr[s] for s in slugs])[:, None, None]
        lost = np.where(tr, ((binary == 1) & ~fbin).sum(0), np.nan)
        gain = np.where(tr, ((binary == 0) & fbin).sum(0), np.nan)
        write_raster(OUT / f"species_lost_{ssp}.tif", lost)
        write_raster(OUT / f"species_gained_{ssp}.tif", gain)
        for i, s in enumerate(slugs):
            now = float(area[tr & (binary[i] == 1)].sum())
            then = float(area[tr & fbin[i]].sum())
            clim_rows.append(
                {
                    "species_slug": s,
                    "species": names[s],
                    "scenario": ssp,
                    "suitable_km2_current": round(now),
                    "suitable_km2_future": round(then),
                    "change_pct": round(100 * (then - now) / now, 1) if now else np.nan,
                    "future_suitable_protected_pct": (
                        round(100 * float(area[tr & fbin[i] & (protected == 1)].sum()) / then, 1)
                        if then
                        else np.nan
                    ),
                }
            )
        fut_summary[ssp] = {
            "median_change_pct": float(
                np.nanmedian([r["change_pct"] for r in clim_rows if r["scenario"] == ssp])
            )
        }
    if clim_rows:
        pd.DataFrame(clim_rows).to_csv(OUT / "climate_change_species.csv", index=False)

    # ---- protection gap ----
    tr_prot_pct = 100 * float(area[tr & (protected == 1)].sum() / area[tr].sum())
    gap = []
    for i, s in enumerate(slugs):
        suit_cells = tr & (binary[i] == 1)
        a_suit = float(area[suit_cells].sum())
        a_prot = float(area[suit_cells & (protected == 1)].sum())
        m = metrics.set_index("species_slug").loc[s]
        gap.append(
            {
                "species_slug": s,
                "species": names[s],
                "genus": names[s].split()[0],
                "suitable_km2_turkey": round(a_suit),
                "protected_suitable_km2": round(a_prot),
                "protected_pct": round(100 * a_prot / a_suit, 2) if a_suit else np.nan,
                "mean_pressure_in_suitable": (
                    round(float(pressure[suit_cells].mean()), 3) if a_suit else np.nan
                ),
                "auc_mean": m["auc_mean"],
                "tss_mean": m["tss_mean"],
            }
        )
    gap = pd.DataFrame(gap).sort_values("protected_pct")
    gap.to_csv(OUT / "protection_gap.csv", index=False)
    any_suit = tr & (richness >= 1)
    overall_gap = 100 * float(area[any_suit & (protected == 1)].sum() / area[any_suit].sum())

    # ---- province ranking ----
    prov_id = read_raster(PROCESSED / "province_id.tif")
    adm1 = read_vector(PROCESSED / "admin1_turkey.gpkg")
    unprot = suit * (pressure * (1 - protected))[None]
    prov_rows = []
    for k, row in adm1.reset_index(drop=True).iterrows():
        cells = tr & (prov_id == k + 1)
        if not cells.any():
            continue
        sp_score = unprot[:, cells].mean(1)
        top = np.argsort(sp_score)[::-1][:3]
        suit_here = cells & (richness >= 1)
        prov_rows.append(
            {
                "province": row["province"],
                "shapeISO": row["shapeISO"],
                "mean_priority": round(float(np.nanmean(prio[cells])), 4),
                "max_priority": round(float(np.nanmax(prio[cells])), 4),
                "n_hotspot_cells": int(hot[cells].sum()),
                "n_robust_hotspot_cells": int(robust[cells].sum()),
                "hotspot_km2": round(float(area[cells & hot].sum())),
                "mean_pressure": round(float(pressure[cells].mean()), 3),
                "mean_richness": round(float(richness[cells].mean()), 2),
                "suitable_area_protected_pct": (
                    round(100 * float(area[suit_here & (protected == 1)].sum() / area[suit_here].sum()), 2)
                    if suit_here.any()
                    else np.nan
                ),
                "top_species": "; ".join(names[slugs[j]] for j in top if sp_score[j] > 0),
            }
        )
    prov = pd.DataFrame(prov_rows).sort_values("mean_priority", ascending=False)
    prov.insert(0, "rank", range(1, len(prov) + 1))
    prov.to_csv(OUT / "province_ranking.csv", index=False)

    summary = {
        "model_source": source,
        "n_species": len(slugs),
        "n_clean_records": int(len(pd.read_csv(PROCESSED / "occurrences_clean.csv"))),
        "turkey_protected_pct": round(tr_prot_pct, 2),
        "suitable_area_protected_pct": round(overall_gap, 2),
        "median_species_protected_pct": round(float(gap["protected_pct"].median()), 2),
        "top_province": prov.iloc[0]["province"],
        "top5_provinces": list(prov["province"].head(5)),
        "n_hotspot_cells": int(hot.sum()),
        "n_robust_hotspot_cells": int(robust.sum()),
        "hotspot_km2": round(float(area[hot].sum())),
        "sensitivity_min_jaccard_top5": float(
            sens[sens["top_fraction"] == frac]["jaccard_vs_reference"].min()
        ),
        "future": fut_summary,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info("summary: %s", json.dumps(summary))
    print(gap.to_string(index=False))
    print(prov.head(10).to_string(index=False))
    print(sens.to_string(index=False))


if __name__ == "__main__":
    main()
