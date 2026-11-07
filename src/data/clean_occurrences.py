"""Basic occurrence cleaning (CoordinateCleaner-style tests re-implemented in Python),
species list and selection.

Outputs (data/processed/):
  occurrences_raw_salep.csv, occurrences_clean.csv, background_targetgroup.csv,
  species_list.csv, cleaning_report.csv
Statistical thinning / sampling-bias analysis is done in modeling/ (teammate).
"""

from __future__ import annotations

import re

import geopandas as gpd
import numpy as np
import pandas as pd

from src.common import COVARIATES, PROCESSED, RAW, config, get_logger, read_raster, read_vector, training_grid

log = get_logger("clean")
RAW_CSV = RAW / "gbif" / "orchidaceae_extent.csv"
NE = RAW / "naturalearth"

GENUS_REFERENCE = (
    "genus-level: Sezik 2002 (Acta Pharm. Turc.); Kasparek & Grimm 1999 "
    "(Econ. Bot.); TODO: verify species-level use"
)
UNVERIFIED_REFERENCE = "TODO: verify salep-use citation for this genus"

CLEAN_COLS = [
    "species",
    "species_slug",
    "gbifID",
    "decimalLongitude",
    "decimalLatitude",
    "year",
    "countryCode",
    "basisOfRecord",
    "coordinateUncertaintyInMeters",
    "datasetKey",
]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _haversine_m(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * np.arcsin(np.sqrt(a))


def _near_any(lon, lat, ref_lon, ref_lat, buffer_m) -> np.ndarray:
    """True where a point lies within buffer_m of any reference point."""
    out = np.zeros(len(lon), dtype=bool)
    for rx, ry in zip(ref_lon, ref_lat):
        # cheap bounding-box prefilter before the exact distance
        cand = (np.abs(lat - ry) < buffer_m / 100_000 + 0.01) & (np.abs(lon - rx) < buffer_m / 70_000 + 0.01)
        if cand.any():
            idx = np.where(cand)[0]
            out[idx] |= _haversine_m(lon[idx], lat[idx], rx, ry) <= buffer_m
    return out


def reference_points():
    e = config()["grid"]["training_extent"]
    box = (e["lon_min"] - 1, e["lat_min"] - 1, e["lon_max"] + 1, e["lat_max"] + 1)
    countries = gpd.read_file(next((NE / "ne_10m_admin_0_countries").rglob("*.shp")))
    countries = countries.cx[box[0] : box[2], box[1] : box[3]]
    cen = countries.geometry.to_crs("EPSG:6933").centroid.to_crs("EPSG:4326")
    cen_lon, cen_lat = list(cen.x), list(cen.y)
    if {"LABEL_X", "LABEL_Y"} <= set(countries.columns):  # NE label points are also used as "centroids"
        cen_lon += list(countries["LABEL_X"])
        cen_lat += list(countries["LABEL_Y"])
    prov = read_vector(PROCESSED / "admin1_turkey.gpkg")
    pc = prov.geometry.to_crs("EPSG:6933").centroid.to_crs("EPSG:4326")
    cen_lon += list(pc.x)
    cen_lat += list(pc.y)
    places = gpd.read_file(next((NE / "ne_10m_populated_places_simple").rglob("*.shp")))
    caps = places[(places["adm0cap"] == 1)].cx[box[0] : box[2], box[1] : box[3]]
    return (np.array(cen_lon), np.array(cen_lat)), (caps.geometry.x.values, caps.geometry.y.values)


def clean(df: pd.DataFrame, report: list, label: str) -> pd.DataFrame:
    c = config()["cleaning"]
    grid = training_grid()

    def step(name, keep):
        nonlocal df
        report.append(
            {"dataset": label, "step": name, "removed": int((~keep).sum()), "remaining": int(keep.sum())}
        )
        df = df[keep].copy()

    report.append(
        {"dataset": label, "step": "raw GBIF records in extent", "removed": 0, "remaining": len(df)}
    )
    for col in ["decimalLongitude", "decimalLatitude", "coordinateUncertaintyInMeters", "year"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    step("missing coordinates", df["decimalLongitude"].notna() & df["decimalLatitude"].notna())
    step("basisOfRecord fossil/living", ~df["basisOfRecord"].isin(c["drop_basis_of_record"]))
    if c["drop_missing_year"]:
        step("missing year", df["year"].notna())
    step(f"year < {c['min_year']}", df["year"].isna() | (df["year"] >= c["min_year"]))
    unc = df["coordinateUncertaintyInMeters"]
    report.append(
        {
            "dataset": label,
            "step": "(info) missing coordinate uncertainty kept",
            "removed": 0,
            "remaining": int(unc.isna().sum()),
        }
    )
    step(
        f"coordinate uncertainty > {c['max_coordinate_uncertainty_m']} m",
        unc.isna() | (unc <= c["max_coordinate_uncertainty_m"]),
    )
    lon, lat = df["decimalLongitude"].values, df["decimalLatitude"].values
    step("zero coordinates", ~((np.abs(lon) < 0.5) & (np.abs(lat) < 0.5)))
    lon, lat = df["decimalLongitude"].values, df["decimalLatitude"].values
    step("equal latitude/longitude", ~np.isclose(lon, lat))
    (cx, cy), (kx, ky) = reference_points()
    lon, lat = df["decimalLongitude"].values, df["decimalLatitude"].values
    step(
        f"country/province centroids (<{c['centroid_buffer_m']} m)",
        ~_near_any(lon, lat, cx, cy, c["centroid_buffer_m"]),
    )
    lon, lat = df["decimalLongitude"].values, df["decimalLatitude"].values
    step(
        f"capitals (<{c['capital_buffer_m'] / 1000:.0f} km)",
        ~_near_any(lon, lat, kx, ky, c["capital_buffer_m"]),
    )
    lon, lat = df["decimalLongitude"].values, df["decimalLatitude"].values
    step("GBIF headquarters", ~_near_any(lon, lat, [12.58], [55.67], c["gbif_hq_buffer_m"]))
    # sea / outside climate data: cell without WorldClim value (land mask)
    land = ~np.isnan(read_raster(COVARIATES / "bio01.tif"))
    row, col, inside = grid.cell_index(df["decimalLongitude"], df["decimalLatitude"])
    ok = inside.copy()
    ok[inside] = land[row[inside], col[inside]]
    step("sea / no climate data", ok)
    return df


def main() -> None:
    taxa = config()["taxa"]
    sel = config()["species_selection"]
    grid = training_grid()
    raw = pd.read_csv(RAW_CSV, dtype=str)
    log.info("raw Orchidaceae records: %d", len(raw))
    report: list = []

    # target-group background: every Orchidaceae record, same cleaning
    bg = clean(raw.copy(), report, "background (all Orchidaceae)")
    bg = bg.sort_values("gbifID", key=lambda s: pd.to_numeric(s, errors="coerce")).drop_duplicates(
        ["decimalLongitude", "decimalLatitude", "year"]
    )
    bg[["decimalLongitude", "decimalLatitude", "year", "countryCode"]].to_csv(
        PROCESSED / "background_targetgroup.csv", index=False
    )

    salep = raw[
        raw["genus"].isin(taxa["salep_genera"])
        & raw["species"].notna()
        & raw["species"].str.strip().str.contains(" ")  # species-level names only
    ].copy()
    salep["species_slug"] = salep["species"].map(slugify)
    salep[[c for c in CLEAN_COLS if c in salep] + ["genus", "taxonRank", "issue"]].to_csv(
        PROCESSED / "occurrences_raw_salep.csv", index=False
    )
    occ = clean(salep, report, "salep genera (species level)")
    n0 = len(occ)
    occ = occ.sort_values("gbifID", key=lambda s: pd.to_numeric(s, errors="coerce")).drop_duplicates(
        ["species", "decimalLongitude", "decimalLatitude"]
    )
    report.append(
        {
            "dataset": "salep genera (species level)",
            "step": "duplicate species+coordinates",
            "removed": n0 - len(occ),
            "remaining": len(occ),
        }
    )
    occ["year"] = occ["year"].astype("Int64")
    occ[CLEAN_COLS].to_csv(PROCESSED / "occurrences_clean.csv", index=False)

    tr = turkey_mask_safe()
    row, col, inside = grid.cell_index(occ["decimalLongitude"], occ["decimalLatitude"])
    occ["cell"] = np.where(inside, row * grid.width + col, -1)
    occ["in_turkey"] = inside & tr[np.clip(row, 0, grid.height - 1), np.clip(col, 0, grid.width - 1)]
    genus = occ.groupby("species")["species"].first().str.split().str[0]
    sp = (
        occ.groupby(["species", "species_slug"])
        .agg(
            n_records_total=("gbifID", "size"),
            n_records_turkey=("in_turkey", "sum"),
            n_cells_unique=("cell", "nunique"),
        )
        .reset_index()
    )
    sp["n_cells_turkey"] = (
        sp["species"].map(occ[occ["in_turkey"]].groupby("species")["cell"].nunique()).fillna(0).astype(int)
    )
    sp["genus"] = sp["species"].map(genus)
    sp["selected"] = (sp["n_cells_unique"] >= sel["min_unique_cells_training"]) & (
        sp["n_cells_turkey"] >= sel["min_unique_cells_turkey"]
    )
    sp["salep_use_reference"] = np.where(
        sp["genus"].isin(taxa["unverified_genera"]), UNVERIFIED_REFERENCE, GENUS_REFERENCE
    )
    sp = sp[
        [
            "species",
            "species_slug",
            "genus",
            "n_records_total",
            "n_records_turkey",
            "n_cells_unique",
            "n_cells_turkey",
            "selected",
            "salep_use_reference",
        ]
    ]
    sp.sort_values(["selected", "n_cells_turkey"], ascending=False).to_csv(
        PROCESSED / "species_list.csv", index=False
    )
    pd.DataFrame(report).to_csv(PROCESSED / "cleaning_report.csv", index=False)

    log.info(
        "background records=%d; salep clean records=%d, species=%d, selected=%d",
        len(bg),
        len(occ),
        len(sp),
        int(sp["selected"].sum()),
    )
    print(pd.DataFrame(report).to_string(index=False))
    print(sp.sort_values("n_cells_turkey", ascending=False).head(60).to_string(index=False))


def turkey_mask_safe() -> np.ndarray:
    return read_raster(PROCESSED / "turkey_mask.tif") == 1


if __name__ == "__main__":
    main()
