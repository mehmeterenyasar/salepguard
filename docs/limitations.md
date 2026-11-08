# Limitations

> **[pipeline]** sections by the data/software lead; **[modelling]** sections by the modelling lead.

SalepGuard is a **risk-prioritisation tool**. It does not show where orchids grow, where harvest
happens, or how many plants are taken. Every hotspot needs field validation before management action.
Nothing here is clinical, legal or definitive information.

## Data [pipeline]

- **Sparse, biased Turkish records.** GBIF holds far fewer orchid records for Turkey than for Greece or
  Cyprus. Many Turkish orchid surveys (herbaria, national flora projects) are not digitised in GBIF. The
  training extent and target-group background reduce, but do not remove, this bias.
- **Obscured coordinates.** About 65 % of raw Turkish salep-genus records (2,135 of 3,301) carry
  ~28 km coordinate uncertainty, mostly because iNaturalist deliberately obscures sensitive orchid
  locations. They are unusable on a 4.6 km grid and were removed (> 5 km rule). As a result eastern
  Anatolia and *Dactylorhiza* (a key salep genus) are badly under-represented and no *Dactylorhiza*
  species passed the selection rule; hotspots are biased towards the west and south coasts.
- **Taxonomy.** Names follow the GBIF backbone; orchid taxonomy (e.g. *Ophrys*, *Dactylorhiza*) is
  contested, and lumping/splitting changes species counts. Subspecies are merged.
- **Salep-use attribution** is at genus level (Sezik 2002; Kasparek & Grimm 1999). Not every species of
  a salep genus is harvested equally; species-level use is marked `TODO: verify`.
- **Cleaning** omits an institution/herbarium-coordinate test; some records with large but unreported
  coordinate uncertainty remain.
- **Protected areas.** The public WDPA release has only 17 Turkish sites, so the layer relies mostly on
  OpenStreetMap, which is incomplete and mixes designations of different strength (≈4.5 % of Turkish
  cells protected). Legal protection ≠ effective protection against collection.
- **Climate data** are 1970–2000 normals at ~4.6 km; microhabitats (meadows, open pine forest,
  graveyards) are not resolved.

## Harvest pressure [pipeline]

- Population density and travel time are **proxies** of potential access, not observations of
  harvesting. Remote mountain meadows used by specialised collectors may be underrated; urban areas with
  no orchid habitat are down-weighted only through suitability.
- Population density rewards **urban cores** (İstanbul, İzmir rank high) where little orchid habitat or
  collection remains; a rural-access proxy would be more realistic (future work).
- The 50/50 weights are an assumption (tested with sensitivity scenarios).
- Market demand, land-use change, grazing and tourism are not included.
- Literature-known collection regions are used only as a qualitative sanity check, not validation.

## Priority index and uncertainty [pipeline]

- Multiplicative combination assumes suitability and pressure contribute equally and independently.
- Uncertainty propagation includes only model (bootstrap) uncertainty, treats species as independent
  (likely underestimating SD), and ignores uncertainty in pressure and protection layers.
- Climate projections hold pressure and protected areas constant and assume unlimited or no dispersal
  implicitly via thresholding; 3 GCMs do not span full CMIP6 spread.

## Models

### Final model [modelling]

- **Sampling bias is reduced, not removed.** Target-group background cancels recording effort only where
  orchid recorders went. Where nobody recorded any orchid (large parts of central and eastern Anatolia)
  the model has no information, and low suitability there may simply mean "not recorded".
- **Obscured coordinates.** About 65 % of Turkish salep-genus records (2,135 of 3,301) were removed
  because iNaturalist obscures sensitive species to ~28 km. The remaining data are dominated by Greece
  and Cyprus (`tables/species_records.csv`): for most species fewer than 15 % of the records are Turkish.
  Turkish predictions are therefore partly a transfer from the Aegean/Balkan part of each range.
- **Eastern Anatolia and *Dactylorhiza*.** No *Dactylorhiza* species met the selection rule, although
  the genus is one of the most important salep sources, and eastern Anatolia is almost unrepresented.
  The richness and risk maps therefore cover mainly western/southern, Mediterranean salep orchids and
  must not be read as "no salep orchids in the east".
- **Few records.** Several species have < 150 thinned cells (e.g. *Ophrys vicina* 75, *O. reinholdii*
  123). Their CV metrics have high fold-to-fold SD and their maps are less reliable.
- **Taxonomy.** *Ophrys* in particular is taxonomically unstable (lumping/splitting of the *O. fusca*,
  *O. sphegodes* and *O. scolopax* groups); GBIF backbone names may merge or split taxa that local floras
  treat differently.
- **Climate baseline vs record years.** WorldClim 2.1 describes 1970–2000, while the median record year
  is ~2019–2023 (`share_pre2000` is ≤ 15 % for every species). Recent warming means species are matched
  to a climate that is slightly cooler than the one they currently experience.
- **Relative suitability, not probability.** MaxEnt cloglog output is a relative suitability index;
  prevalence is not identifiable from presence-background data.
- **No true absences.** AUC, TSS and the thresholds compare presences with background (recording effort),
  not with confirmed absences, so they measure discrimination from the recorded landscape.
- **Spatial block CV is still not fully independent.** The covariate autocorrelation range (~850 km
  median) is much larger than the 200 km blocks we used; with larger blocks whole countries would fall
  into one fold. Our spatial AUCs are more honest than random-CV AUCs but may still be somewhat optimistic.
- **Hand-written equivalents of R packages.** Spatial blocks, ENMeval-style tuning, Boyce index and MESS
  were written in Python following the published methods because the R packages were not available on
  the night. They were checked against the definitions, not against the R implementations numerically.
- **Risk ≠ observed harvest.** Suitability × pressure is a potential-risk index; we have no data on where
  tubers are actually dug.
- **Dispersal and biotic interactions.** Orchids depend on mycorrhizal fungi and (for *Ophrys*) on specific
  pollinators; none of this is in the model. Full and no-dispersal scenarios bracket, but do not model,
  real colonisation.
- **Extrapolation.** Non-analog climate (MESS < 0) covers a minority of Turkey for most species (mainly
  the south-east and the high east, `figures/mess_map.png`), so the large per-species changes are mostly
  *not* an extrapolation artefact (analog-only change is close to the all-cell change, `range_change.csv`).
  They rather reflect how strongly a model with no true absences and a coastal sampling bias reacts to a
  shift in the cold limit (bio06) and summer rain (bio18). Clamping keeps predictions bounded but values in
  non-analog cells are not evidence.
- **GCM uncertainty is reported, not propagated.** Only the 3-GCM ensemble mean was projected; the
  inter-GCM SD of the covariates is available as a separate layer. 3 GCMs do not span the CMIP6 spread.
- **Not done in time:** 10 km thinning sensitivity, GLM comparison.

### Baseline model [pipeline]

- Random k-fold CV overestimates performance under spatial autocorrelation.
- Same covariate subset for all species; no species-specific tuning of regularisation.
- Suitability is relative (cloglog) and not a probability of occurrence.

## Responsible display [pipeline]

- Raw points are never shown and maps are aggregated to ~9 km, but modelled suitability can still hint
  at areas with many species. The dashboard therefore frames everything as conservation priority and
  avoids species-level point-scale outputs.
