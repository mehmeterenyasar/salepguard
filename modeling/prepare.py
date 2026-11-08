"""Step 1-3: contract check, sampling-bias analysis, thinning table, variable selection (|r|, VIF).

    python modeling/prepare.py
Writes outputs/models/tables/*.csv, outputs/models/figures/{sampling_bias,correlation_heatmap}.png
and modeling/variables.txt (the common variable set used by run_models.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sdm import (
    COVARIATE_NAMES,
    COVARIATES,
    FIG,
    GRID,
    MODELING,
    OUT,
    PROCESSED,
    SEED,
    cells_of,
    load_stack,
    turkey_mask,
)

TAB = OUT / "tables"
# biologically motivated priority: temperature seasonality, cold limit, water balance, terrain
PRIORITY = [
    "bio04",  # temperature seasonality
    "bio06",  # min temperature of coldest month
    "bio12",  # annual precipitation
    "bio18",  # precipitation of warmest quarter
    "bio17",  # precipitation of driest quarter
    "elevation",
    "bio15",  # precipitation seasonality
    "bio02",  # mean diurnal range
    "bio01",
    "bio05",
    "bio10",
    "bio11",
    "bio09",
    "bio08",
    "bio19",
    "bio03",
    "bio07",
    "bio13",
    "bio14",
    "bio16",
]


def vif(df: pd.DataFrame) -> pd.Series:
    """VIF_j = diag(R^-1) of the correlation matrix (same as usdm::vif)."""
    inv = np.linalg.inv(np.corrcoef(df.values, rowvar=False))
    return pd.Series(np.diag(inv), index=df.columns)


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    import rasterio

    # ---------------- 1. contract checks
    checks = []
    for name in COVARIATE_NAMES:
        with rasterio.open(COVARIATES / f"{name}.tif") as src:
            checks.append(
                dict(
                    layer=name,
                    shape=f"{src.height}x{src.width}",
                    crs=src.crs.to_string(),
                    transform_ok=np.allclose(tuple(src.transform)[:6], tuple(GRID.transform)[:6]),
                )
            )
    stack = load_stack(COVARIATES)
    valid = np.all(~np.isnan(stack), axis=0)
    tr = turkey_mask()
    chk = pd.DataFrame(checks)
    chk["na_share_extent"] = [float(np.isnan(stack[i]).mean()) for i in range(len(COVARIATE_NAMES))]
    chk["na_share_turkey"] = [float(np.isnan(stack[i][tr]).mean()) for i in range(len(COVARIATE_NAMES))]
    chk.to_csv(TAB / "contract_check.csv", index=False)
    print(chk[["layer", "shape", "crs", "transform_ok", "na_share_extent", "na_share_turkey"]].to_string(index=False))

    # ---------------- 2. species table + thinning (1 record per 2.5' cell)
    occ = pd.read_csv(PROCESSED / "occurrences_clean.csv")
    bg = pd.read_csv(PROCESSED / "background_targetgroup.csv")
    sp = pd.read_csv(PROCESSED / "species_list.csv")
    sp = sp[sp["selected"]]
    vflat = valid.ravel()
    rows = []
    for s in sp["species_slug"]:
        o = occ[occ["species_slug"] == s]
        cells = cells_of(o, vflat)
        rows.append(
            dict(
                species_slug=s,
                n_records_raw=len(o),
                n_cells_thinned=len(cells),
                n_turkey=int((o["countryCode"] == "TR").sum()),
                n_greece=int((o["countryCode"] == "GR").sum()),
                n_cyprus=int((o["countryCode"] == "CY").sum()),
                n_other=int((~o["countryCode"].isin(["TR", "GR", "CY"])).sum()),
                year_median=float(o["year"].median()),
                share_pre2000=float((o["year"] < 2000).mean()),
            )
        )
    st = pd.DataFrame(rows)
    st.to_csv(TAB / "species_records.csv", index=False)
    bg_cells = cells_of(bg, vflat)
    print(f"\nbackground: {len(bg)} records -> {len(bg_cells)} unique valid cells")
    print(st.to_string(index=False))

    # ---------------- 3. sampling-bias figure
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    agg = 6  # 0.25 deg bins for display
    r, c, inside = GRID.cell_index(bg["decimalLongitude"], bg["decimalLatitude"])
    dens = np.zeros((GRID.height // agg, GRID.width // agg))
    np.add.at(dens, (r[inside] // agg, c[inside] // agg), 1)
    land = valid.reshape(GRID.height // agg, agg, GRID.width // agg, agg).any(axis=(1, 3))
    dens_plot = np.where(land, np.log10(dens + 1), np.nan)
    cc = bg["countryCode"].fillna("NA").value_counts()
    top = cc.head(6)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [3, 1]})
    im = ax[0].imshow(dens_plot, extent=GRID.bounds[0:1] + GRID.bounds[2:3] + GRID.bounds[1:2] + GRID.bounds[3:4],
                      cmap="viridis", origin="upper")
    ax[0].contour(np.flipud(tr[::agg, ::agg].astype(float)), levels=[0.5], colors="white", linewidths=0.6,
                  extent=(GRID.lon_min, GRID.lon_max, GRID.lat_min, GRID.lat_max))
    ax[0].set_title("Target-group background: Orchidaceae records per 0.25° cell (log10)")
    ax[0].set_xlabel("Longitude")
    ax[0].set_ylabel("Latitude")
    fig.colorbar(im, ax=ax[0], shrink=0.8, label="log10(records + 1)")
    ax[1].barh(top.index[::-1], top.values[::-1], color="#3b528b")
    ax[1].set_title("Records by country")
    ax[1].set_xlabel("Cleaned Orchidaceae records")
    fig.tight_layout()
    fig.savefig(FIG / "sampling_bias.png", dpi=300)
    plt.close(fig)
    cc.rename("n_records").to_csv(TAB / "background_by_country.csv")

    # ---------------- 4. variable selection on cells sampled across the training extent
    rng = np.random.default_rng(SEED)
    land_cells = np.where(vflat)[0]
    samp = rng.choice(land_cells, min(10_000, len(land_cells)), replace=False)
    X = pd.DataFrame(stack.reshape(len(COVARIATE_NAMES), -1).T[samp], columns=COVARIATE_NAMES)
    corr = X.corr()
    corr.to_csv(TAB / "correlation_matrix.csv")
    keep: list[str] = []
    for v in PRIORITY:
        if all(abs(corr.loc[v, k]) <= 0.7 for k in keep):
            keep.append(v)
    while True:
        vv = vif(X[keep])
        if vv.max() <= 10:
            break
        keep.remove(vv.idxmax())
    vv = vif(X[keep])
    pd.DataFrame({"variable": keep, "vif": vv.values}).to_csv(TAB / "selected_variables_vif.csv", index=False)
    (MODELING / "variables.txt").write_text("\n".join(keep) + "\n", encoding="utf-8")
    print("\nselected variables:", keep)
    print(vv.round(2).to_string())
    base = ["bio01", "bio12", "bio04", "bio19", "bio02", "bio08"]
    print("max |r| among selected:", round(float(corr.loc[keep, keep].abs().where(~np.eye(len(keep), dtype=bool)).max().max()), 3))
    print("baseline set VIF:", vif(X[base]).round(2).to_dict())

    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    im = ax.imshow(corr.values, cmap="cividis", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=90)
    ax.set_yticks(range(len(corr)), corr.columns)
    for i, v in enumerate(corr.columns):
        if v in keep:
            ax.get_xticklabels()[i].set_fontweight("bold")
            ax.get_yticklabels()[i].set_fontweight("bold")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson r")
    ax.set_title("Covariate correlation (10,000 random cells); bold = selected")
    fig.tight_layout()
    fig.savefig(FIG / "correlation_heatmap.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
