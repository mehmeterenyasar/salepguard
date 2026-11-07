# Pitch video script (target 8:30, hard limit 10:00)

Numbers come from the **baseline** model. Re-check them against `outputs/risk/summary.json` after the
final model is integrated.

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
"For each of twenty species with enough data we fit a MaxEnt species distribution model. As background we
used all orchid records, so the model compares like with like and corrects for where botanists tend to go.
We validate with spatially blocked cross-validation and repeat every model on bootstrap samples, which
gives each map cell an uncertainty. Then the SalepGuard Priority Index multiplies, for every species,
habitat suitability by harvest pressure by one minus protection, and sums over species. We propagate the
bootstrap uncertainty into the index. A robust hotspot is a place that stays in the top five percent even
at the pessimistic end of that uncertainty."

**5. Demo (4:00–6:30)**: see the click script below. Narrate each step in one sentence.

**6. Results (6:30–7:30)** (teammate)
"Hotspots cluster on the Aegean, Marmara and eastern Mediterranean coasts: İzmir, Aydın, Hatay and the
Marmara provinces. Most of them stay hotspots under uncertainty. The headline is the protection gap. Only
about four percent of the area suitable for salep orchids is inside a protected area, no more than
Turkey's average, so the protected-area network is not targeting these species. Changing the pressure
weights keeps almost ninety percent of the hotspot set."

**7. Limitations (7:30–8:10)** (teammate)
"We want to be clear about what this is not. It is not a map of harvest or of orchids, and every hotspot
needs field checks. Eastern Anatolia and the important genus *Dactylorhiza* are under-represented in open
data. Our pressure layer is a proxy and over-rates big cities. The OpenStreetMap protected areas are
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
