"""Static figures for README / slides -> outputs/figures/ (aggregated to 5' like the dashboard)."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.common import OUTPUTS, PROCESSED, get_logger, read_raster, read_vector  # noqa: E402
from src.viz.web_layers import Renderer, aggregate  # noqa: E402

log = get_logger("figures")
FIG = OUTPUTS / "figures"
RISK = OUTPUTS / "risk"
NOTE = "Risk prioritisation, not observed harvest. Aggregated to 5 arc-min (~9 km)."


def map_fig(arr, title, cmap, fname, vmin=None, vmax=None, label="", categorical=None):
    r = Renderer()
    a = aggregate(arr[r.win].astype("float32"), r.f, "max" if categorical else "mean")
    a[~r.mask] = np.nan
    h, w = a.shape
    ext = [r.west, r.west + w * r.res, r.north - h * r.res, r.north]
    adm1 = read_vector(PROCESSED / "admin1_turkey.gpkg")
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
    if categorical:
        from matplotlib.colors import ListedColormap

        cm = ListedColormap(["#e9ecef"] + [c for _, c in categorical])
        im = ax.imshow(
            a, extent=ext, cmap=cm, vmin=-0.5, vmax=len(categorical) + 0.5, interpolation="nearest"
        )
        from matplotlib.patches import Patch

        ax.legend(handles=[Patch(color=c, label=n) for n, c in categorical], loc="lower left", fontsize=8)
    else:
        im = ax.imshow(a, extent=ext, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        fig.colorbar(im, ax=ax, shrink=0.7, label=label)
    adm1.boundary.plot(ax=ax, color="#444", linewidth=0.3)
    ax.set_xlim(25.5, 45)
    ax.set_ylim(35.7, 42.3)
    ax.set_title(title, loc="left", fontsize=12)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    fig.text(0.01, 0.01, NOTE, fontsize=7, color="#555")
    fig.tight_layout()
    fig.savefig(FIG / fname)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    s = json.loads((RISK / "summary.json").read_text())
    src = s["model_source"]
    map_fig(
        read_raster(RISK / "priority_index.tif"),
        f"SalepGuard Priority Index ({src} model)",
        "viridis",
        "priority_index.png",
        0,
        1,
        "Priority (0-1)",
    )
    map_fig(
        read_raster(RISK / "hotspot_class.tif"),
        "Priority hotspots (top 5%)",
        None,
        "hotspots.png",
        categorical=[("Hotspot", "#f4a261"), ("Robust hotspot (CV < 0.5)", "#9b2226")],
    )
    map_fig(
        read_raster(RISK / "priority_sd.tif"),
        "Priority uncertainty (propagated bootstrap SD)",
        "magma",
        "priority_sd.png",
        0,
        None,
        "SD",
    )
    map_fig(
        read_raster(PROCESSED / "pressure_index.tif"),
        "Harvest-pressure proxy (population + accessibility)",
        "cividis",
        "pressure_index.png",
        0,
        1,
        "Pressure (0-1)",
    )
    map_fig(
        read_raster(RISK / "richness_binary_turkey.tif"),
        "Modelled salep-orchid richness",
        "viridis",
        "richness.png",
        0,
        None,
        "Number of species (thresholded)",
    )
    if (RISK / "priority_change_ssp245.tif").exists():
        map_fig(
            read_raster(RISK / "priority_change_ssp245.tif"),
            "Priority change 2041-2060, SSP2-4.5",
            "PuOr_r",
            "priority_change_ssp245.png",
            -0.5,
            0.5,
            "Future - current",
        )

    gap = pd.read_csv(RISK / "protection_gap.csv").sort_values("protected_pct")
    fig, ax = plt.subplots(figsize=(8, max(4, 0.26 * len(gap))), dpi=150)
    ax.barh(gap["species"], gap["protected_pct"], color="#21918c")
    ax.axvline(s["turkey_protected_pct"], color="#9b2226", ls="--", lw=1, label="Share of Turkey protected")
    ax.set_xlabel("% of suitable area in Turkey inside protected areas")
    ax.set_yticks(range(len(gap)), gap["species"], fontstyle="italic", fontsize=8)
    ax.legend(fontsize=8)
    ax.set_title("Protection gap per species", loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "protection_gap.png")
    plt.close(fig)

    prov = pd.read_csv(RISK / "province_ranking.csv").head(15)[::-1]
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    ax.barh(prov["province"], prov["mean_priority"], color="#3b528b")
    ax.set_xlabel("Mean priority index")
    ax.set_title("Top 15 provinces", loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "province_top15.png")
    plt.close(fig)

    cr = pd.read_csv(PROCESSED / "cleaning_report.csv")
    cr = cr[(cr["dataset"].str.startswith("salep")) & ~cr["step"].str.startswith("(info)")]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ax.barh(cr["step"][::-1], cr["remaining"][::-1], color="#5ec962")
    ax.set_xlabel("Records remaining (salep genera)")
    ax.set_title("Occurrence cleaning", loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "cleaning_funnel.png")
    plt.close(fig)
    log.info("figures written to %s", FIG)


if __name__ == "__main__":
    main()
