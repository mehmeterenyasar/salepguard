"""Figures for report and slides (300 dpi, viridis/cividis, English labels).

    python modeling/figures.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from sdm import CACHE, FIG, GRID, MODELING, OUT, read_raster, turkey_mask  # noqa: E402

EXT = (GRID.lon_min, GRID.lon_max, GRID.lat_min, GRID.lat_max)
TR = turkey_mask()
# Turkey bounding box for zoomed maps
TR_EXT = (25.5, 45.0, 35.7, 42.3)


def rd(name):
    return read_raster(OUT / name)


def turkey_map(ax, arr, title, cmap="viridis", vmin=None, vmax=None, label=""):
    a = np.where(TR, arr, np.nan)
    im = ax.imshow(a, extent=EXT, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_xlim(TR_EXT[0], TR_EXT[1])
    ax.set_ylim(TR_EXT[2], TR_EXT[3])
    ax.set_title(title, fontsize=11)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.colorbar(im, ax=ax, shrink=0.75, label=label)
    return im


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    mt = pd.read_csv(OUT / "metrics.csv")
    vars_ = (MODELING / "variables.txt").read_text().split()

    # ---- spatial vs random CV
    d = mt.sort_values("auc_mean")
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    y = np.arange(len(d))
    ax.hlines(y, d["auc_mean"], d["auc_random_cv"], color="0.7")
    ax.scatter(d["auc_random_cv"], y, color="#fde725", edgecolor="k", zorder=3, label="Random 5-fold CV")
    ax.scatter(d["auc_mean"], y, color="#21918c", edgecolor="k", zorder=3, label="Spatial block 5-fold CV")
    ax.set_yticks(y, [s.replace("_", " ").capitalize() for s in d["species_slug"]], fontsize=8)
    ax.axvline(0.6, ls="--", color="0.5", lw=0.8)
    ax.set_xlabel("Validation AUC (presence vs target-group background)")
    gap = (d["auc_random_cv"] - d["auc_mean"]).mean()
    ax.set_title(f"Random CV is optimistic: mean AUC gap {gap:+.3f}")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "spatial_vs_random_cv.png", dpi=300)
    plt.close(fig)

    # ---- variable importance (heatmap species x variable)
    imp = pd.DataFrame(
        [dict(item.split(":") for item in s.split(";")) for s in mt["importance"]], index=mt["species_slug"]
    ).astype(float)[vars_]
    fig, ax = plt.subplots(figsize=(7, 7))
    im = ax.imshow(imp.values, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(vars_)), vars_, rotation=45)
    ax.set_yticks(range(len(imp)), [s.replace("_", " ").capitalize() for s in imp.index], fontsize=8)
    plt.colorbar(im, ax=ax, label="Permutation importance (% of total AUC drop)")
    ax.set_title("Variable importance (full model per species)")
    fig.tight_layout()
    fig.savefig(FIG / "variable_importance.png", dpi=300)
    plt.close(fig)

    # ---- response curves (all species, one panel per variable)
    n = len(vars_)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(3.2 * cols, 2.6 * rows), squeeze=False)
    cmap = plt.get_cmap("viridis")
    for k, v in enumerate(vars_):
        ax = axs[k // cols][k % cols]
        for i, s in enumerate(mt["species_slug"]):
            z = np.load(CACHE / f"{s}.npz")
            ax.plot(z[f"curve_x_{v}"], z[f"curve_y_{v}"], color=cmap(i / len(mt)), lw=0.8, alpha=0.8)
        ax.set_title(v, fontsize=10)
        ax.set_ylim(0, 1)
    for k in range(n, rows * cols):
        axs[k // cols][k % cols].axis("off")
    fig.suptitle("Marginal response curves (other variables at median), one line per species", fontsize=11)
    fig.supylabel("Relative suitability (cloglog)")
    fig.tight_layout()
    fig.savefig(FIG / "response_curves.png", dpi=300)
    plt.close(fig)

    # ---- richness, uncertainty, MESS, future change
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    turkey_map(ax[0], rd("richness_mean.tif"), "Predicted species richness (binary, maxSSS)", label="Species (of 20)")
    turkey_map(ax[1], rd("richness_sd.tif"), "Uncertainty: bootstrap SD of richness", cmap="cividis", label="SD (species)")
    fig.tight_layout()
    fig.savefig(FIG / "richness_map.png", dpi=300)
    plt.close(fig)

    sds = np.nanmean([rd(f"{s}_suitability_sd.tif") for s in mt["species_slug"]], axis=0)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    turkey_map(ax[0], rd("richness_prob_mean.tif"), "Summed suitability (20 species)", label="Sum of suitability")
    turkey_map(ax[1], sds, "Mean bootstrap SD of suitability", cmap="cividis", label="SD")
    fig.tight_layout()
    fig.savefig(FIG / "uncertainty_map.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(1, 3, figsize=(17, 4.2))
    for a, (lab, suf) in zip(ax, [("Current", ""), ("SSP2-4.5 2041-2060", "_ssp245"), ("SSP5-8.5 2041-2060", "_ssp585")]):
        neg = np.mean([rd(f"{s}_mess{suf}.tif") < 0 for s in mt["species_slug"]], axis=0)
        turkey_map(a, neg * 100, f"Non-analog climate (MESS < 0): {lab}", cmap="cividis", vmin=0, vmax=100,
                   label="% of species models")
    fig.tight_layout()
    fig.savefig(FIG / "mess_map.png", dpi=300)
    plt.close(fig)

    cur = rd("richness_mean.tif")
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    for a, ssp, lab in zip(ax, ["ssp245", "ssp585"], ["SSP2-4.5", "SSP5-8.5"]):
        diff = rd(f"richness_future_{ssp}.tif") - cur
        lim = np.nanmax(np.abs(np.where(TR, diff, np.nan)))
        turkey_map(a, diff, f"Change in richness, {lab} 2041-2060 (full dispersal)", cmap="PuOr", vmin=-lim, vmax=lim,
                   label="Species gained (+) / lost (-)")
        neg = np.mean([rd(f"{s}_mess_{ssp}.tif") < 0 for s in mt["species_slug"]], axis=0) > 0.5
        a.contourf(np.where(TR & neg, 1.0, np.nan), levels=[0.5, 1.5], colors="none", hatches=["////"],
                   extent=EXT, origin="upper")
    fig.text(0.5, 0.01, "Hatched: non-analog climate (MESS < 0) for most species; change there is extrapolation.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "future_change_map.png", dpi=300)
    plt.close(fig)

    # ---- range change by species
    rc = pd.read_csv(OUT / "range_change.csv")
    full = rc[rc["dispersal"] == "full"].pivot(index="species_slug", columns="scenario", values="change_pct")
    ana = rc[rc["dispersal"] == "full"].pivot(index="species_slug", columns="scenario", values="change_pct_analog_only")
    order = full["ssp585"].sort_values().index
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    yy = np.arange(len(order))
    ax.barh(yy - 0.2, full.loc[order, "ssp585"], height=0.4, color="#440154", label="SSP5-8.5, all cells")
    ax.barh(yy + 0.2, ana.loc[order, "ssp585"], height=0.4, color="#35b779", label="SSP5-8.5, analog cells only")
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(yy, [s.replace("_", " ").capitalize() for s in order], fontsize=8)
    ax.set_xlabel("Change in suitable area in Turkey (%), full dispersal")
    ax.set_title("Projected range change 2041-2060")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "range_change.png", dpi=300)
    plt.close(fig)

    # ---- one example species map (best spatial AUC among included)
    ex = mt[mt["include_in_index"]].sort_values("auc_mean").iloc[-1]["species_slug"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    turkey_map(ax[0], rd(f"{ex}_suitability_mean.tif"), f"{ex.replace('_', ' ').capitalize()}: suitability (mean)",
               vmin=0, vmax=1, label="Relative suitability")
    turkey_map(ax[1], rd(f"{ex}_suitability_sd.tif"), "Bootstrap SD", cmap="cividis", label="SD")
    fig.tight_layout()
    fig.savefig(FIG / "example_species.png", dpi=300)
    plt.close(fig)
    print("figures written to", FIG)
    _ = json  # noqa


if __name__ == "__main__":
    main()
