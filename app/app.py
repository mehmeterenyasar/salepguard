"""SalepGuard dashboard.  Run locally:  streamlit run app/app.py

Reads only pre-rendered, committed files (app/layers, outputs/, data/processed/*.csv),
so it starts fast and never touches raw data or rasters at runtime.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import folium
import matplotlib
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "app" / "layers"
RISK = ROOT / "outputs" / "risk"
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

st.set_page_config(page_title="SalepGuard", page_icon="🌸", layout="wide")

DISCLAIMER = ("**Risk prioritisation, not observed harvest.** Maps show modelled habitat suitability "
              "combined with proxy harvest pressure at a deliberately coarse resolution for responsible "
              "display. They do not show where orchids or harvesting actually occur and require field "
              "validation.")


# ---------------------------------------------------------------- data
@st.cache_data
def load_index() -> dict:
    return json.loads((LAYERS / "index.json").read_text(encoding="utf-8"))


@st.cache_data
def png_uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((LAYERS / f"{name}.png").read_bytes()).decode()


@st.cache_data
def geojson(name: str) -> dict:
    return json.loads((LAYERS / f"{name}.geojson").read_text(encoding="utf-8"))


@st.cache_data
def csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@st.cache_data
def summary() -> dict:
    return json.loads((RISK / "summary.json").read_text(encoding="utf-8"))


INDEX = load_index()
SOURCE = INDEX["model_source"]
MODEL_DIR = ROOT / "outputs" / ("models" if SOURCE == "final" else "baseline")
SPECIES = csv(PROCESSED / "species_list.csv")
SELECTED = SPECIES[SPECIES["selected"]].copy() if not SPECIES.empty else SPECIES
METRICS = csv(MODEL_DIR / "metrics.csv")


# ---------------------------------------------------------------- map helpers
def legend(name: str) -> None:
    meta = INDEX["layers"][name]
    if meta.get("categorical"):
        labels = {"protected_areas": {"1": "Protected area"},
                  "hotspot_class": {"1": "Hotspot (top 5%)", "2": "Robust hotspot (top 5%, low uncertainty)"}}
        lab = labels.get(name, {"1": meta["label"]})
        chips = " ".join(f"<span style='display:inline-block;width:12px;height:12px;background:{c};"
                         f"margin:0 4px 0 12px;border-radius:2px'></span>{lab.get(k, k)}"
                         for k, c in meta["categorical"].items())
        st.markdown(f"<div style='font-size:0.85rem'>{chips}</div>", unsafe_allow_html=True)
        return
    cmap = matplotlib.colormaps[meta["cmap"]]
    stops = ", ".join(matplotlib.colors.to_hex(cmap(i / 10)) for i in range(11))
    st.markdown(
        f"<div style='font-size:0.8rem'>{meta['label']}"
        f"<div style='height:12px;max-width:360px;background:linear-gradient(to right,{stops});"
        f"border-radius:3px'></div><div style='display:flex;justify-content:space-between;max-width:360px'>"
        f"<span>{meta['vmin']:.2f}</span><span>{meta['vmax']:.2f}</span></div></div>",
        unsafe_allow_html=True)


def make_map(layers: list[str], opacity: float = 0.8, provinces: bool = True, protected: bool = False,
             height: int = 520, key: str = "map"):
    m = folium.Map(location=[39.0, 35.3], zoom_start=6, min_zoom=5, max_zoom=9, tiles="CartoDB positron",
                   control_scale=True)
    for name in layers:
        meta = INDEX["layers"][name]
        folium.raster_layers.ImageOverlay(png_uri(name), bounds=meta["bounds"], opacity=opacity,
                                          name=meta["label"], interactive=False).add_to(m)
    if protected:
        folium.GeoJson(geojson("protected_areas"), name="Protected areas",
                       style_function=lambda f: {"color": "#1b7837", "weight": 1, "fillOpacity": 0.05}).add_to(m)
    if provinces:
        folium.GeoJson(geojson("provinces"), name="Provinces",
                       style_function=lambda f: {"color": "#555", "weight": 0.6, "fillOpacity": 0},
                       tooltip=folium.GeoJsonTooltip(["province"], labels=False)).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    st_folium(m, height=height, use_container_width=True, returned_objects=[], key=key)


def banner() -> None:
    label = "final model (teammate, bias-corrected MaxEnt)" if SOURCE == "final" else \
        "baseline model (fallback, Python MaxEnt)"
    st.caption(f"🧭 **Showing: {label}** · display aggregated to {INDEX['aggregation_arcmin']:g} arc-min (~9 km)")
    st.warning(DISCLAIMER, icon="⚠️")


# ---------------------------------------------------------------- pages
def page_overview():
    s = summary()
    st.title("SalepGuard")
    st.subheader("Where are Turkey's salep orchids most exposed to tuber harvest, outside protected areas?")
    st.markdown(
        "Salep — the traditional hot drink, salep ice cream (*dondurma*) and folk remedy — is made from the "
        "dried tubers of wild terrestrial orchids. In Turkey, tubers of roughly 90 orchid species from 24 "
        "genera have been reported in salep (Sezik 2002), essentially all collected from wild populations, "
        "and harvesting a tuber kills the plant. SalepGuard combines species distribution models, "
        "harvest-pressure proxies and protected-area coverage into a transparent, uncertainty-aware "
        "**conservation prioritisation tool**.")
    c = st.columns(4)
    c[0].metric("Species modelled", s["n_species"])
    c[1].metric("Cleaned occurrence records", f"{s['n_clean_records']:,}")
    c[2].metric("Suitable area protected", f"{s['suitable_area_protected_pct']:.1f}%",
                help="Share of area suitable for ≥1 modelled species that lies inside a protected area.")
    c[3].metric("Top priority province", s["top_province"])
    st.markdown(f"Top-5 provinces by mean priority: **{', '.join(s['top5_provinces'])}**. "
                f"Robust hotspots (top 5% priority with low model uncertainty): "
                f"**{s['n_robust_hotspot_cells']:,} cells** of {s['n_hotspot_cells']:,} hotspot cells.")
    banner()
    make_map(["priority_index"], key="ov")
    legend("priority_index")
    st.markdown("""
**How to read it.** `priority = Σ_species suitability × harvest pressure × (1 − protected)`.
High values mean: many salep species could live here, people can easily reach the area, and it is not
protected. Use the pages on the left to explore species, risk scenarios, provinces and protection gaps.
""")
    st.info("**Responsible data display.** Raw GBIF occurrence points are never shown. Even though GBIF data "
            "are public, a compiled 'where to find salep orchids' map could guide collectors. All layers are "
            "modelled, aggregated surfaces.", icon="🔒")


def page_species():
    st.title("Species explorer")
    banner()
    if SELECTED.empty:
        st.error("No species outputs available.")
        return
    opts = SELECTED.sort_values("species")
    sp = st.selectbox("Species", opts["species"], index=0)
    row = opts[opts["species"] == sp].iloc[0]
    slug = row["species_slug"]
    layer_opts = {"Suitability (mean)": f"{slug}__suitability", "Uncertainty (bootstrap SD)": f"{slug}__sd",
                  "Suitable area (binary)": f"{slug}__binary"}
    for ssp in ("ssp245", "ssp585"):
        if f"{slug}__future_{ssp}" in INDEX["layers"]:
            layer_opts[f"Future 2041–60 {ssp.upper()}"] = f"{slug}__future_{ssp}"
            layer_opts[f"Change {ssp.upper()} (future − now)"] = f"{slug}__change_{ssp}"
    left, right = st.columns([3, 1])
    with right:
        choice = st.radio("Layer", list(layer_opts), index=0)
        prot = st.checkbox("Protected-area outlines", value=False)
        st.markdown(f"#### *{sp}*")
        st.markdown(f"Genus: *{row['genus']}*")
        st.markdown(f"Records (clean, training extent): **{int(row['n_records_total'])}**  \n"
                    f"Unique cells: **{int(row['n_cells_unique'])}** (Turkey: **{int(row['n_cells_turkey'])}**)")
        if not METRICS.empty and slug in set(METRICS["species_slug"]):
            m = METRICS.set_index("species_slug").loc[slug]
            st.markdown(f"AUC: **{m['auc_mean']:.3f} ± {m['auc_sd']:.3f}**  \n"
                        f"TSS: **{m['tss_mean']:.3f} ± {m['tss_sd']:.3f}**  \nBoyce: **{m['cbi_mean']:.2f}**  \n"
                        f"CV: {m['cv_method']}")
        st.caption(f"Salep use: {row['salep_use_reference']}")
        gap = csv(RISK / "protection_gap.csv")
        if not gap.empty and slug in set(gap["species_slug"]):
            g = gap.set_index("species_slug").loc[slug]
            st.metric("Suitable area protected", f"{g['protected_pct']:.1f}%")
    with left:
        make_map([layer_opts[choice]], protected=prot, key=f"sp_{slug}_{choice}")
        legend(layer_opts[choice])
    cc = csv(RISK / "climate_change_species.csv")
    if not cc.empty:
        st.dataframe(cc[cc["species_slug"] == slug].drop(columns=["species_slug"]), hide_index=True)


def page_risk():
    st.title("Harvest risk & priority")
    banner()
    left, right = st.columns([3, 1])
    with right:
        layer = st.radio("Layer", ["Priority index", "Robust hotspots", "Priority uncertainty (SD)",
                                   "Harvest pressure", "Population component", "Accessibility component",
                                   "Species richness", "Future priority", "Priority change (future − now)"])
        scen = st.selectbox("Pressure weighting scenario (sensitivity)",
                            ["balanced (0.5 / 0.5)", "population_heavy (0.7 / 0.3)", "access_heavy (0.3 / 0.7)"])
        ssp = st.selectbox("Climate scenario", ["ssp245", "ssp585"])
        prot = st.checkbox("Protected-area outlines", value=True)
    scen_key = scen.split()[0]
    mapping = {"Priority index": f"priority_{scen_key}", "Robust hotspots": "hotspot_class",
               "Priority uncertainty (SD)": "priority_sd", "Harvest pressure": "pressure_index",
               "Population component": "pressure_population", "Accessibility component": "pressure_accessibility",
               "Species richness": "richness", "Future priority": f"priority_future_{ssp}",
               "Priority change (future − now)": f"priority_change_{ssp}"}
    name = mapping[layer]
    if name not in INDEX["layers"]:
        name = "priority_index"
    with left:
        make_map([name], protected=prot, key=f"risk_{name}")
        legend(name)
    sens = csv(RISK / "sensitivity_jaccard.csv")
    if not sens.empty:
        st.markdown("#### How stable are the hotspots? (Jaccard similarity to the reference top-k% set)")
        st.caption("Reference = balanced weights, continuous suitability. 1 = identical hotspot set.")
        pv = sens.pivot_table(index=["pressure_scenario", "suitability_input"], columns="top_fraction",
                              values="jaccard_vs_reference").reset_index()
        pv.columns = [f"top {c:.1%}" if isinstance(c, float) else c for c in pv.columns]
        st.dataframe(pv, hide_index=True)


def page_provinces():
    st.title("Province ranking")
    banner()
    prov = csv(RISK / "province_ranking.csv")
    if prov.empty:
        st.error("province_ranking.csv not found")
        return
    metric = st.selectbox("Colour provinces by", ["mean_priority", "n_robust_hotspot_cells", "hotspot_km2",
                                                  "suitable_area_protected_pct", "mean_pressure", "mean_richness"])
    left, right = st.columns([3, 2])
    with left:
        m = folium.Map(location=[39.0, 35.3], zoom_start=6, tiles="CartoDB positron")
        folium.Choropleth(geo_data=geojson("provinces"), data=prov, columns=["province", metric],
                          key_on="feature.properties.province", fill_color="YlGnBu", fill_opacity=0.8,
                          line_weight=0.5, legend_name=metric, nan_fill_color="#eeeeee").add_to(m)
        folium.GeoJson(geojson("provinces"), style_function=lambda f: {"weight": 0, "fillOpacity": 0},
                       tooltip=folium.GeoJsonTooltip(["province"], labels=False)).add_to(m)
        st_folium(m, height=520, use_container_width=True, returned_objects=[], key=f"prov_{metric}")
    with right:
        sel = st.selectbox("Province details", prov["province"])
        r = prov[prov["province"] == sel].iloc[0]
        st.markdown(f"### #{int(r['rank'])} {sel}")
        a, b = st.columns(2)
        a.metric("Mean priority", f"{r['mean_priority']:.3f}")
        b.metric("Robust hotspot cells", int(r["n_robust_hotspot_cells"]))
        a.metric("Hotspot area", f"{int(r['hotspot_km2']):,} km²")
        b.metric("Suitable area protected", f"{r['suitable_area_protected_pct']:.1f}%")
        st.markdown(f"**Main species (unprotected risk):** {r['top_species']}")
    st.dataframe(prov, hide_index=True, height=360)
    st.caption("Known salep-collection regions in the literature (e.g. Muğla, Kahramanmaraş, Muş, Antalya) "
               "can be used as a qualitative sanity check only — they are not a validation dataset.")


def page_gap():
    st.title("Protection gap")
    banner()
    gap = csv(RISK / "protection_gap.csv")
    if gap.empty:
        st.error("protection_gap.csv not found")
        return
    s = summary()
    st.markdown(f"Protected areas cover **{s['turkey_protected_pct']:.1f}%** of Turkey's land cells in our "
                f"protected-area layer. For a typical (median) salep species only "
                f"**{s['median_species_protected_pct']:.1f}%** of its suitable area in Turkey is protected.")
    fig = px.bar(gap.sort_values("protected_pct"), x="protected_pct", y="species", color="genus",
                 orientation="h", labels={"protected_pct": "% of suitable area inside protected areas",
                                          "species": ""}, height=max(400, 22 * len(gap)),
                 color_discrete_sequence=px.colors.qualitative.Safe)
    fig.add_vline(x=s["turkey_protected_pct"], line_dash="dash", annotation_text="Turkey average")
    fig.update_layout(yaxis={"tickfont": {"style": "italic"}}, legend_title_text="Genus")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(gap, hide_index=True)


def page_methods():
    st.title("Methods & limitations")
    tabs = st.tabs(["Methods", "Limitations", "Data sources & licences", "AI usage"])
    for tab, fname in zip(tabs, ["methods.md", "limitations.md", "data_sources.md", "ai_usage.md"]):
        with tab:
            p = DOCS / fname
            st.markdown(p.read_text(encoding="utf-8") if p.exists() else f"`docs/{fname}` not found")
    cr = csv(PROCESSED / "cleaning_report.csv")
    if not cr.empty:
        st.markdown("#### Occurrence cleaning report")
        st.dataframe(cr, hide_index=True)
    if not METRICS.empty:
        st.markdown(f"#### Model metrics ({SOURCE})")
        st.dataframe(METRICS, hide_index=True)


PAGES = {"Overview": page_overview, "Species explorer": page_species, "Harvest risk & priority": page_risk,
         "Province ranking": page_provinces, "Protection gap": page_gap, "Methods & limitations": page_methods}
with st.sidebar:
    st.markdown("## 🌸 SalepGuard")
    page = st.radio("Page", list(PAGES), label_visibility="collapsed")
    st.markdown("---")
    st.caption("EthnoHack 2026 · Track 3: Biodiversity & Sustainability")
    st.caption("[GitHub repository](https://github.com/mehmeterenyasar/salepguard)")
PAGES[page]()
