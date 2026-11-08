## Inspiration

Every cup of salep, the hot winter drink and the stretchy *dondurma*, starts with an orchid tuber dug out of the ground. In Turkey about 90 orchid species in 24 genera are reported in salep (Sezik 2002). None are farmed commercially, so supply comes from wild collection, and harvesting a tuber kills the plant. The same pattern is reported in Greece (Kreziou et al. 2016) and Iran (Ghorbani et al. 2014). Conservation agencies cannot survey a whole country. We wanted an open tool that says **where to look first**, and is honest about how sure it is.

## What it does

SalepGuard is an interactive, uncertainty-aware conservation-prioritisation tool for Turkey's salep orchids. It combines:

- **species distribution models** for 20 salep orchid species,
- a **harvest-pressure proxy** (population and travel time to cities),
- **protected-area coverage** (WDPA + OpenStreetMap),

into the **SalepGuard Priority Index** = Σ species suitability × pressure × (1 − protected). The dashboard (https://salepguard.streamlit.app) has a species explorer (suitability, bootstrap uncertainty, 2041–2060 projections and change), a risk page with live pressure-weight scenarios and robust hotspots, an 81-province ranking, a per-species protection-gap chart, and full methods and limitations.

**Responsible display:** raw orchid locations are never shown, and maps are aggregated to ~9 km so the tool cannot be used as a collecting guide.

## How we built it

1. **Data (all open):** 62,435 GBIF orchid records for the Eastern Mediterranean (download DOI [10.15468/dl.mfzrky](https://doi.org/10.15468/dl.mfzrky)); WorldClim 2.1 and CMIP6 projections (3 GCMs × SSP2-4.5/SSP5-8.5); WorldPop 2020; Weiss et al. (2018) travel time; WDPA + OpenStreetMap protected areas; geoBoundaries provinces.
2. **Cleaning:** CoordinateCleaner-style filters re-implemented in Python → 24,557 records; 20 species with enough data.
3. **Models:** MaxEnt with a **target-group background** (all orchid records) to cancel recorder bias; 6 non-redundant climate variables; complexity tuned per species; **spatial block cross-validation** (200 km blocks); 20 bootstrap refits; MESS extrapolation checks; bias-aware null models.
4. **Index and uncertainty:** bootstrap SD propagated into the index; a *robust hotspot* stays in the top 5 % even at the lower 95 % bound. Jaccard sensitivity across pressure weights and thresholding.
5. **Reproducible:** one command (`python run_all.py`) rebuilds everything; Streamlit Community Cloud hosts the dashboard.

## Results

- Spatial-block AUC **0.72** on average (0.58–0.87), TSS 0.32, Boyce 0.58. Random CV would have claimed 0.76: that gap is the optimism we removed.
- All 20 species beat a bias-aware null model; *Anacamptis morio* and *A. pyramidalis* (AUC < 0.6) are **excluded** from the index rather than over-trusted.
- Only **4.5 %** of the area suitable for salep orchids is protected, no more than the 4.5 % of Turkey as a whole. Median species: 7.2 %.
- Hotspots cluster on the Aegean, Marmara and eastern Mediterranean coasts; top provinces **Hatay, İzmir, Aydın, İstanbul, Gaziantep**. 1,983 of 2,339 hotspot cells are robust to model uncertainty.
- Hotspots are stable across pressure weights (Jaccard 0.87–0.88) and more sensitive to thresholding (0.60–0.64).
- 2041–2060 without dispersal: the median species loses 9–14 % of its Turkish range; *Himantoglossum robertianum*, *Orchis anatolica* and *Ophrys lutea* lose a third to almost 90 %.

## Challenges we ran into

- **About 65 % of Turkish records are deliberately blurred** (~28 km) by iNaturalist to protect orchids. We respected that and dropped them, which leaves eastern Anatolia and *Dactylorhiza* nearly empty. The east is *unknown, not empty*.
- Records are dominated by Greece and Cyprus, so we had to model sampling bias explicitly.
- The public WDPA release lists only 17 Turkish sites, so we merged it with OpenStreetMap.
- Random cross-validation looked flattering; spatial validation was humbling but honest.

## Accomplishments that we're proud of

An end-to-end, open and reproducible pipeline with honest validation, propagated uncertainty, and a display policy designed not to help collectors.

## What we learned

How strongly sampling bias and spatial autocorrelation inflate model scores, and why uncertainty belongs on the map, not in a footnote.

## What's next for SalepGuard

Digitised herbarium data for eastern Turkey, trade- and interview-based pressure calibration, the national protected-area registry, field validation of robust hotspots with local partners, and a cultivation-suitability module for certified salep supply, together with the collectors whose livelihoods depend on it.

## Team and AI use

Mehmet Eren Yaşar (data pipeline, risk index, dashboard) and Sena Aydın (statistical modelling, validation, uncertainty). We used Claude Code substantially for code, documentation and the pitch video (synthetic text-to-speech narration of our script); details in `docs/ai_usage.md`.

Code: https://github.com/mehmeterenyasar/salepguard (MIT).
