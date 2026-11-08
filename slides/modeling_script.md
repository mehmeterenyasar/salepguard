# Modelling narration (~3 min, Sena)

Numbers from `docs/results_summary.md` (generated from `outputs/models/metrics.csv`). Risk/hotspot
numbers belong to Mehmet's `outputs/risk/summary.json` and are updated by him after `run_all.py --from risk`.

## Method (2:40–4:00, ~80 s)

"Open orchid records are not a map of orchids; they are a map of where people looked. Most of our
records come from Greece and Cyprus, and many Turkish records were blurred to protect the plants. So we
model each species against all orchid records, not against the whole landscape. This target-group
background asks: where does this species occur, compared with where orchid recorders went?

We use MaxEnt with six climate variables that are not redundant: temperature seasonality, winter cold,
annual and summer rain, wet-season temperature and isothermality. For each species we tune model
complexity, twelve settings, and we validate with spatial blocks of two hundred kilometres: the model
is trained in some regions and tested in regions it has never seen. Every model is refitted twenty times
on resampled data, which gives each map cell an uncertainty, and we flag cells where the future climate
is outside anything the model was trained on.

The SalepGuard Priority Index then multiplies suitability by harvest pressure and by one minus protection
and sums over species. The bootstrap uncertainty is carried into the index, and a robust hotspot stays in
the top five percent even at the pessimistic end of that uncertainty."

## Results (6:30–7:30, ~60 s)

"First, how good are the models? Under spatial validation the average AUC is 0.72, from 0.58 to 0.87.
Ordinary random cross-validation would have told us 0.76. That gap is exactly the optimism we wanted to
remove. Every species beats a null model built from random orchid records with the same bias. But two
species, *Anacamptis morio* and *Anacamptis pyramidalis*, stay below 0.6, so we left them out of the
priority index rather than pretend.

Predicted richness peaks on the Aegean and Mediterranean coasts, which is also where harvest pressure and
the hotspots are. Hatay, İzmir, Aydın, İstanbul and Gaziantep lead the province ranking, and 1,983 of the
2,339 hotspot cells stay hotspots even at the pessimistic end of the uncertainty. Yet only 4.5 percent of
the area suitable for salep orchids is protected, no more than the 4.5 percent of Turkey as a whole.

For 2041 to 2060 the picture depends on dispersal. If orchids could move freely, the median species would
gain area. But tuberous orchids spread slowly. Without dispersal the median species loses nine to fourteen
percent of its Turkish range, and the Mediterranean *Himantoglossum robertianum*, *Orchis anatolica* and
*Ophrys lutea* lose between a third and almost ninety percent."

## Limitations (7:30–8:10, ~40 s)

"What this is not: it is not a map of harvest and not a census of orchids. Suitability is relative, and
background records are not true absences. Eastern Anatolia and *Dactylorhiza*, one of the most harvested
genera, are almost missing from open data, so the east is unknown, not empty. The climate baseline is
1970 to 2000, while most records are recent. Future maps ignore fungi, pollinators and dispersal, and
come from three climate models only. Every hotspot needs a field check."
