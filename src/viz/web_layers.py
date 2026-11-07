"""Pre-render rasters as coloured PNG overlays for the dashboard (fast cold start).

Responsible display: every layer is aggregated to 5 arc-min (~9 km; factor in config),
clipped to Turkey and reprojected to Web Mercator so it sits correctly on the basemap.
Writes app/layers/<name>.png and app/layers/index.json (bounds, palette, value range).
"""

from __future__ import annotations

import json

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image
from rasterio.transform import from_origin
from rasterio.warp import Resampling, calculate_default_transform, reproject

from src.common import OUTPUTS, PROCESSED, ROOT, config, get_logger, read_raster, read_vector, training_grid
from src.risk.priority import model_source

log = get_logger("web_layers")
LAYERS = ROOT / "app" / "layers"


def aggregate(arr: np.ndarray, f: int, how: str = "mean") -> np.ndarray:
    h, w = arr.shape
    a = arr[: h - h % f, : w - w % f].reshape(h // f, f, w // f, f)
    with np.errstate(all="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore")
        return np.nanmax(a, axis=(1, 3)) if how == "max" else np.nanmean(a, axis=(1, 3))


class Renderer:
    def __init__(self):
        g = training_grid()
        self.f = config()["grid"]["display_aggregation_factor"]
        tr = read_raster(PROCESSED / "turkey_mask.tif") == 1
        rows, cols = np.where(tr)
        pad = 2 * self.f
        r0, r1 = max(rows.min() - pad, 0) // self.f * self.f, min(rows.max() + pad, g.height)
        c0, c1 = max(cols.min() - pad, 0) // self.f * self.f, min(cols.max() + pad, g.width)
        r1 = r0 + (r1 - r0) // self.f * self.f
        c1 = c0 + (c1 - c0) // self.f * self.f
        self.win = (slice(r0, r1), slice(c0, c1))
        self.res = g.res * self.f
        self.west, self.north = g.lon_min + c0 * g.res, g.lat_max - r0 * g.res
        self.src_tf = from_origin(self.west, self.north, self.res, self.res)
        self.mask = aggregate(tr[self.win].astype(float), self.f) > 0.5
        h, w = self.mask.shape
        self.bounds_ll = [[self.north - h * self.res, self.west], [self.north, self.west + w * self.res]]
        self.dst_tf, self.dw, self.dh = calculate_default_transform(
            "EPSG:4326",
            "EPSG:3857",
            w,
            h,
            self.west,
            self.north - h * self.res,
            self.west + w * self.res,
            self.north,
        )
        self.index: dict = {}

    def render(
        self,
        name: str,
        arr: np.ndarray,
        cmap: str,
        vmin=None,
        vmax=None,
        how="mean",
        label: str = "",
        categorical: dict | None = None,
    ):
        a = aggregate(arr[self.win].astype("float32"), self.f, how)
        a[~self.mask] = np.nan
        vmin = float(np.nanmin(a)) if vmin is None else vmin
        vmax = float(np.nanmax(a)) if vmax is None else vmax
        merc = np.full((self.dh, self.dw), np.nan, dtype="float32")
        reproject(
            a,
            merc,
            src_transform=self.src_tf,
            src_crs="EPSG:4326",
            dst_transform=self.dst_tf,
            dst_crs="EPSG:3857",
            resampling=Resampling.nearest,
            src_nodata=np.nan,
            dst_nodata=np.nan,
        )
        norm = np.clip((merc - vmin) / (vmax - vmin if vmax > vmin else 1), 0, 1)
        if categorical:
            colours = np.zeros((*merc.shape, 4), dtype="uint8")
            for val, hexcol in categorical.items():
                rgba = np.array(matplotlib.colors.to_rgba(hexcol)) * 255
                colours[np.isclose(merc, float(val))] = rgba.astype("uint8")
        else:
            colours = (matplotlib.colormaps[cmap](np.nan_to_num(norm)) * 255).astype("uint8")
        colours[np.isnan(merc), 3] = 0
        LAYERS.mkdir(parents=True, exist_ok=True)
        Image.fromarray(colours, "RGBA").save(LAYERS / f"{name}.png", optimize=True)
        self.index[name] = {
            "bounds": self.bounds_ll,
            "cmap": cmap,
            "vmin": round(vmin, 4),
            "vmax": round(vmax, 4),
            "label": label,
            "categorical": categorical,
        }


def main() -> None:
    source, mdir = model_source()
    r = Renderer()
    risk = OUTPUTS / "risk"
    rd = lambda p: read_raster(p)  # noqa: E731

    r.render(
        "pressure_index",
        rd(PROCESSED / "pressure_index.tif"),
        "cividis",
        0,
        1,
        label="Harvest pressure (0-1)",
    )
    r.render(
        "pressure_population",
        rd(PROCESSED / "pressure_population.tif"),
        "cividis",
        0,
        1,
        label="Population (log, 0-1)",
    )
    r.render(
        "pressure_accessibility",
        rd(PROCESSED / "pressure_accessibility.tif"),
        "cividis",
        0,
        1,
        label="Accessibility (0-1)",
    )
    r.render(
        "protected_areas",
        rd(PROCESSED / "protected_areas.tif"),
        "Greens",
        how="max",
        label="Protected",
        categorical={"1": "#1b7837"},
    )
    r.render(
        "priority_index", rd(risk / "priority_index.tif"), "viridis", 0, None, label="Priority index (0-1)"
    )
    r.render("priority_sd", rd(risk / "priority_sd.tif"), "magma", 0, None, label="Priority uncertainty (SD)")
    r.render(
        "hotspot_class",
        rd(risk / "hotspot_class.tif"),
        "viridis",
        how="max",
        label="Hotspot class",
        categorical={"1": "#f4a261", "2": "#9b2226"},
    )
    r.render(
        "richness",
        rd(risk / "richness_binary_turkey.tif"),
        "viridis",
        0,
        None,
        label="Species richness (n suitable)",
    )
    for name in config()["pressure"]["sensitivity_scenarios"]:
        p = risk / "scenarios" / f"priority_{name}.tif"
        r.render(f"priority_{name}", rd(p), "viridis", 0, None, label=f"Priority ({name})")
    for ssp in config()["future"]["scenarios"]:
        if (risk / f"priority_future_{ssp}.tif").exists():
            r.render(
                f"priority_future_{ssp}",
                rd(risk / f"priority_future_{ssp}.tif"),
                "viridis",
                0,
                None,
                label=f"Priority 2041-60 {ssp.upper()}",
            )
            r.render(
                f"priority_change_{ssp}",
                rd(risk / f"priority_change_{ssp}.tif"),
                "PuOr_r",
                -0.5,
                0.5,
                label="Priority change (future - now)",
            )
            r.render(
                f"species_lost_{ssp}",
                rd(risk / f"species_lost_{ssp}.tif"),
                "magma",
                0,
                None,
                label="Species losing suitability",
            )
            r.render(
                f"species_gained_{ssp}",
                rd(risk / f"species_gained_{ssp}.tif"),
                "viridis",
                0,
                None,
                label="Species gaining suitability",
            )

    sp = pd.read_csv(PROCESSED / "species_list.csv")
    for s in sp.loc[sp["selected"], "species_slug"]:
        if not (mdir / f"{s}_suitability_mean.tif").exists():
            continue
        cur = rd(mdir / f"{s}_suitability_mean.tif")
        r.render(f"{s}__suitability", cur, "viridis", 0, 1, label="Suitability (0-1)")
        r.render(f"{s}__sd", rd(mdir / f"{s}_suitability_sd.tif"), "magma", 0, None, label="Bootstrap SD")
        r.render(
            f"{s}__binary",
            rd(mdir / f"{s}_binary.tif"),
            "viridis",
            how="max",
            label="Suitable (thresholded)",
            categorical={"1": "#21918c"},
        )
        for ssp in config()["future"]["scenarios"]:
            fp = mdir / f"{s}_future_{ssp}_mean.tif"
            if fp.exists():
                fut = rd(fp)
                r.render(
                    f"{s}__future_{ssp}", fut, "viridis", 0, 1, label=f"Suitability 2041-60 {ssp.upper()}"
                )
                r.render(f"{s}__change_{ssp}", fut - cur, "PuOr_r", -0.5, 0.5, label="Change (future - now)")
    # light-weight vectors for the app (no geopandas needed at runtime)
    adm1 = read_vector(PROCESSED / "admin1_turkey.gpkg")
    adm1["geometry"] = adm1.geometry.simplify(0.01, preserve_topology=True)
    (LAYERS / "provinces.geojson").write_text(
        adm1[["province", "shapeISO", "geometry"]].to_json(), encoding="utf-8"
    )
    pa = read_vector(PROCESSED / "protected_areas.gpkg")
    pa["geometry"] = pa.geometry.simplify(0.005, preserve_topology=True)
    pa = pa[~pa.geometry.is_empty]
    (LAYERS / "protected_areas.geojson").write_text(
        pa[[c for c in ["name", "designation", "source", "geometry"] if c in pa]].to_json(), encoding="utf-8"
    )

    meta = {"model_source": source, "aggregation_arcmin": 2.5 * r.f, "layers": r.index}
    (LAYERS / "index.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    size = sum(p.stat().st_size for p in LAYERS.glob("*.png")) / 1e6
    log.info("rendered %d layers (%.1f MB) from %s model", len(r.index), size, source)


if __name__ == "__main__":
    main()
