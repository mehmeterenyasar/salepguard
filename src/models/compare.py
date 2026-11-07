"""Robustness check: final model (outputs/models) vs baseline (outputs/baseline).

Per species (inside Turkey): Spearman r of suitability, Jaccard of binary maps, metrics side by side.
Overall: Jaccard of top-5 % priority hotspots computed from each model.
Writes outputs/risk/model_comparison.csv and model_comparison_summary.json.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.common import OUTPUTS, PROCESSED, config, get_logger, read_raster
from src.risk.priority import jaccard, priority_index, top_mask

log = get_logger("compare")
FINAL, BASE = OUTPUTS / "models", OUTPUTS / "baseline"


def main() -> None:
    if not (FINAL / "metrics.csv").exists():
        log.warning("outputs/models/metrics.csv not found - nothing to compare yet")
        return
    tr = read_raster(PROCESSED / "turkey_mask.tif") == 1
    pressure = np.nan_to_num(read_raster(PROCESSED / "pressure_index.tif"))
    protected = np.nan_to_num(read_raster(PROCESSED / "protected_areas.tif"))
    mf = pd.read_csv(FINAL / "metrics.csv").set_index("species_slug")
    mb = pd.read_csv(BASE / "metrics.csv").set_index("species_slug")
    common = [s for s in mf.index if s in mb.index and (FINAL / f"{s}_suitability_mean.tif").exists()]
    rows, sf, sb = [], [], []
    for s in common:
        a = np.nan_to_num(read_raster(FINAL / f"{s}_suitability_mean.tif"))
        b = np.nan_to_num(read_raster(BASE / f"{s}_suitability_mean.tif"))
        sf.append(a)
        sb.append(b)
        bf = np.nan_to_num(read_raster(FINAL / f"{s}_binary.tif")) == 1
        bb = np.nan_to_num(read_raster(BASE / f"{s}_binary.tif")) == 1
        rows.append(
            {
                "species_slug": s,
                "spearman_suitability_turkey": round(float(spearmanr(a[tr], b[tr]).statistic), 3),
                "jaccard_binary_turkey": round(jaccard(bf & tr, bb & tr), 3),
                "auc_final": mf.loc[s, "auc_mean"],
                "auc_baseline": mb.loc[s, "auc_mean"],
                "tss_final": mf.loc[s, "tss_mean"],
                "tss_baseline": mb.loc[s, "tss_mean"],
                "cv_final": mf.loc[s, "cv_method"],
                "cv_baseline": mb.loc[s, "cv_method"],
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUTS / "risk" / "model_comparison.csv", index=False)
    frac = config()["risk"]["hotspot_top_fraction"]
    pf = np.where(tr, priority_index(np.stack(sf), pressure, protected), np.nan)
    pb = np.where(tr, priority_index(np.stack(sb), pressure, protected), np.nan)
    summ = {
        "n_species_compared": len(common),
        "median_spearman_suitability": float(df["spearman_suitability_turkey"].median()),
        "median_jaccard_binary": float(df["jaccard_binary_turkey"].median()),
        "jaccard_top5_priority_final_vs_baseline": jaccard(top_mask(pf, tr, frac), top_mask(pb, tr, frac)),
    }
    (OUTPUTS / "risk" / "model_comparison_summary.json").write_text(json.dumps(summ, indent=2))
    log.info("comparison: %s", summ)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
