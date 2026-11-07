"""Protected areas of Turkey -> protected_areas.gpkg + protected_areas.tif (0/1).

Preferred source: WDPA (Protected Planet). Its download requires accepting the
terms of use, so it is fetched manually: put the Turkey WDPA zip/shp/gpkg in
data/raw/wdpa/. If nothing is found there, OpenStreetMap protected areas are
queried from the Overpass API (fallback, ODbL).

Rasterisation rule: a cell is protected (1) if its centre lies inside a polygon.
"""

from __future__ import annotations

import json
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from rasterio.features import rasterize
from shapely.geometry import LineString, Polygon
from shapely.ops import linemerge, polygonize, unary_union

from src.common import PROCESSED, RAW, get_logger, training_grid, turkey_mask, write_raster, write_vector

log = get_logger("protected_areas")
WDPA_DIR = RAW / "wdpa"
OSM_CACHE = RAW / "osm" / "overpass_protected_tr.json"
OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = """
[out:json][timeout:600];
area["ISO3166-1"="TR"][admin_level=2]->.tr;
(
  way["boundary"="protected_area"](area.tr);
  relation["boundary"="protected_area"](area.tr);
  way["boundary"="national_park"](area.tr);
  relation["boundary"="national_park"](area.tr);
  way["leisure"="nature_reserve"](area.tr);
  relation["leisure"="nature_reserve"](area.tr);
);
out geom;
"""


def load_wdpa() -> gpd.GeoDataFrame | None:
    if not WDPA_DIR.exists():
        return None
    for z in WDPA_DIR.glob("*.zip"):  # WDPA ships nested zips of shapefiles
        out = WDPA_DIR / z.stem
        if not out.exists():
            with zipfile.ZipFile(z) as zf:
                zf.extractall(out)
        for inner in out.rglob("*.zip"):
            target = inner.with_suffix("")
            if not target.exists():
                with zipfile.ZipFile(inner) as zf:
                    zf.extractall(target)
    files = [p for p in WDPA_DIR.rglob("*") if p.suffix in {".shp", ".gpkg"}]
    polys = [p for p in files if "point" not in p.name.lower()]
    if not polys:
        return None
    gdf = pd.concat([gpd.read_file(p) for p in polys], ignore_index=True)
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    gdf = gdf[gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    if "STATUS" in gdf:
        gdf = gdf[gdf["STATUS"].isin(["Designated", "Inscribed", "Established"])]
    keep = [c for c in ["WDPAID", "NAME", "DESIG_ENG", "IUCN_CAT", "STATUS", "STATUS_YR"] if c in gdf]
    gdf = gdf[keep + ["geometry"]].rename(columns={"NAME": "name", "DESIG_ENG": "designation"})
    gdf["source"] = "WDPA"
    return gdf


def load_osm() -> gpd.GeoDataFrame:
    if not OSM_CACHE.exists():
        log.info("querying Overpass (can take a few minutes)")
        r = requests.post(OVERPASS, data={"data": QUERY}, timeout=900,
                          headers={"User-Agent": "SalepGuard/0.1 (research hackathon)"})
        r.raise_for_status()
        OSM_CACHE.parent.mkdir(parents=True, exist_ok=True)
        OSM_CACHE.write_text(r.text, encoding="utf-8")
    elements = json.loads(OSM_CACHE.read_text(encoding="utf-8"))["elements"]
    rows = []
    for el in elements:
        tags = el.get("tags", {})
        geom = None
        if el["type"] == "way" and len(el.get("geometry", [])) >= 4:
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if coords[0] == coords[-1]:
                geom = Polygon(coords)
        elif el["type"] == "relation":
            outers = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
                      for m in el.get("members", [])
                      if m.get("type") == "way" and m.get("role", "outer") in ("outer", "")
                      and len(m.get("geometry", [])) >= 2]
            if outers:
                polys = list(polygonize(linemerge(outers)))
                if polys:
                    geom = unary_union(polys)
        if geom is not None and geom.is_valid and not geom.is_empty:
            rows.append({"osm_id": f"{el['type']}/{el['id']}", "name": tags.get("name:en", tags.get("name")),
                         "designation": tags.get("protection_title", tags.get("boundary", tags.get("leisure"))),
                         "protect_class": tags.get("protect_class"), "geometry": geom})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    # protect_class 1-6 = nature protection; drop cultural/resource classes (>= 7, e.g. 21-29)
    pc = pd.to_numeric(gdf["protect_class"], errors="coerce")
    gdf = gdf[pc.isna() | (pc <= 6)]
    gdf["source"] = "OpenStreetMap"
    return gdf


def main() -> None:
    grid = training_grid()
    gdf = load_wdpa()
    if gdf is None:
        log.warning("WDPA not found in data/raw/wdpa/ -> using OpenStreetMap fallback")
        gdf = load_osm()
    gdf = gdf[gdf.is_valid].reset_index(drop=True)
    write_vector(gdf, PROCESSED / "protected_areas.gpkg")
    arr = rasterize(((g, 1) for g in gdf.geometry), out_shape=grid.shape, transform=grid.transform,
                    fill=0, dtype="uint8", all_touched=False)
    write_raster(PROCESSED / "protected_areas.tif", arr, grid, nodata=255, dtype="uint8")
    m = turkey_mask()
    log.info("source=%s polygons=%d, protected share of Turkey cells=%.2f%%", gdf["source"].iloc[0],
             len(gdf), 100 * float(arr[m].mean()))


if __name__ == "__main__":
    main()
