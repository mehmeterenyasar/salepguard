# Pitch video script (target 8:30, hard limit 10:00)

Numbers come from the **final** model (`outputs/risk/summary.json`, `docs/results_summary.md`).

| # | Time | Visual | Speaker |
|---|---|---|---|
| 1 | 0:00–0:40 | Slide 1, then a photo of a salep drink (own or CC-licensed photo, credited) | M |
| 2 | 0:40–1:40 | Slide 2 (Problem) | M |
| 3 | 1:40–2:40 | Slide 3 (Data) | M |
| 4 | 2:40–4:00 | Slide 4 (Method) | Teammate |
| 5 | 4:00–6:30 | **Dashboard live demo** (screen recording, see below) | M |
| 6 | 6:30–7:30 | Slides 6–7 (Results) | Teammate |
| 7 | 7:30–8:10 | Slide 9 (Limitations) | Teammate |
| 8 | 8:10–8:40 | Slides 8 + 10 (Impact, next steps) | M |

## Narration

**1. Hook (0:00–0:40)**
"Every cup of salep starts with an orchid being dug out of the ground. In Turkey, around ninety orchid
species are collected for salep. They are not farmed, and harvesting the tuber kills the plant. We built
SalepGuard to answer one question: where are these orchids most exposed to harvest, outside protected
areas, and how sure are we?"

**2. Problem (0:40–1:40)**
"Salep is part of Turkish culture: the hot winter drink, the stretchy dondurma, folk remedies. Trade
studies since the 1990s describe large volumes collected from the wild, and similar collection is reported
in Greece and Iran. Conservation agencies cannot survey the whole country. They need to know where to look
first. No open tool combines where the species can live, where people can reach them, and where
protection is missing, while being honest about uncertainty."

**3. Data (1:40–2:40)**
"We used only open data. From GBIF we took sixty-two thousand orchid records from the whole Eastern
Mediterranean, because a wider region describes each species' climate niche better. After cleaning we
kept about twenty-four and a half thousand records of salep genera. One finding surprised us. About
two-thirds of Turkish records have their coordinates deliberately blurred by around 28 kilometres to
protect the orchids from collectors. We respected that and removed them, and it shaped how we display
our own results. Climate comes from WorldClim, including three climate models for 2041 to 2060.
Population is from WorldPop, travel time from the Malaria Atlas Project, and protected areas from
OpenStreetMap."

**4. Method (2:40–4:00)** (teammate)
"Open orchid records are not a map of orchids; they are a map of where people looked. So we model each of
twenty species against all orchid records, not against the whole landscape. This target-group background
asks: where does this species occur, compared with where orchid recorders went? We use MaxEnt with six
non-redundant climate variables, tune its complexity for each species, and validate with spatial blocks of
two hundred kilometres, so the model is always tested in regions it has never seen. Every model is refitted
twenty times on resampled data, which gives each map cell an uncertainty, and we flag where future climate
is outside the training range. The SalepGuard Priority Index then multiplies suitability by harvest
pressure and by one minus protection, and sums over species. A robust hotspot stays in the top five percent
even at the pessimistic end of the propagated uncertainty."
(Full version and figure cues: `slides/modeling_script.md`.)

**5. Demo (4:00–6:30)**: see the click script below. Narrate each step in one sentence.

**6. Results (6:30–7:30)** (teammate)
"Under spatial validation the average AUC is 0.72; random cross-validation would have claimed 0.76, and
that gap is the optimism we removed. Every species beats a bias-aware null model, but two, *Anacamptis
morio* and *A. pyramidalis*, stay below 0.6 and are left out of the index. Hotspots cluster on the Aegean,
Marmara and eastern Mediterranean coasts, and the protection gap is the headline: Hatay, İzmir,
Aydın, İstanbul and Gaziantep lead the ranking, 1,983 of 2,339 hotspot cells are robust to model
uncertainty, and only 4.5 percent of the suitable area is protected, no more than Turkey's 4.5 percent
overall; for the median species it is 7.2 percent. Under climate change the median species loses nine to fourteen percent of its Turkish range if it
cannot disperse, and *Himantoglossum robertianum*, *Orchis anatolica* and *Ophrys lutea* lose a third to
almost ninety percent."

**7. Limitations (7:30–8:10)** (teammate)
"We want to be clear about what this is not. It is not a map of harvest or of orchids, and every hotspot
needs field checks. Suitability is relative and background records are not true absences. Eastern
Anatolia and the important genus *Dactylorhiza* are almost missing from open data, so the east is
unknown, not empty. Future maps ignore fungi, pollinators and dispersal and rest on three climate models.
Our pressure layer is a proxy and over-rates big cities, and the OpenStreetMap protected areas are
incomplete."

**8. Impact and close (8:10–8:40)**
"SalepGuard can help ministries and NGOs decide where to survey, where to extend protection, and where to
pilot orchid cultivation and certified salep, together with the communities who depend on it. Everything
is open and reproducible with one command. Thank you."

## Dashboard demo click script (record at 1920×1080, browser zoom 90 %)

1. **Overview** (15 s): point to the four numbers and pan the priority map.
2. **Species explorer** (40 s): choose *Orchis anatolica* → layer *Suitability* → *Uncertainty
   (bootstrap SD)* → *Future 2041–60 SSP5-8.5* → *Change*. Point at the AUC/TSS card and the salep-use
   reference.
3. **Harvest risk & priority** (45 s): *Priority index* → *Robust hotspots* (turn on protected-area
   outlines) → switch the pressure scenario to *population_heavy*, then *access_heavy*, and show the map
   hardly changes → scroll to the Jaccard table.
4. **Province ranking** (30 s): colour by *n_robust_hotspot_cells* → choose *İzmir* in the details box →
   read the main species.
5. **Protection gap** (20 s): point to the dashed "Turkey average" line.
6. **Methods & limitations** (10 s): scroll briefly and show the AI-usage tab.

Before recording, open every page once to warm the cache.
