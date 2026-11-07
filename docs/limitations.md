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
  OpenStreetMap, which is incomplete and mixes designations of different strength (≈4.4 % of Turkish
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

_To be completed by the modelling lead._

### Baseline model [pipeline]

- Random k-fold CV overestimates performance under spatial autocorrelation.
- Same covariate subset for all species; no species-specific tuning of regularisation.
- Suitability is relative (cloglog) and not a probability of occurrence.

## Responsible display [pipeline]

- Raw points are never shown and maps are aggregated to ~9 km, but modelled suitability can still hint
  at areas with many species. The dashboard therefore frames everything as conservation priority and
  avoids species-level point-scale outputs.
