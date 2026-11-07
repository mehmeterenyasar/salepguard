# Generative AI usage disclosure

EthnoHack rules require disclosure of significant generative-AI use. We used it substantially.

## Tool

- **Claude Code** (Anthropic; model Claude Opus 5.5), an AI coding assistant running in the developer's
  terminal/desktop app, with access to the project folder, a shell and the web.
- The modelling lead used a separate Claude Code session for `modeling/` (see their section below).

## What the AI did (data/software side)

- Wrote most of the Python code in `src/`, `app/`, `scripts/`, `tests/` and `run_all.py` from a detailed
  specification written by the team (data contract, grid, cleaning rules, index formula, dashboard pages).
- Looked up data endpoints (GBIF API, WorldClim, WorldPop, Malaria Atlas Project WCS, geoBoundaries API,
  Overpass) and licence pages, and drafted `docs/data_sources.md`, the pipeline sections of
  `docs/methods.md` / `docs/limitations.md`, the README, slide skeleton, video script and Devpost text.
- Ran the pipeline, inspected intermediate outputs and fixed bugs (e.g. non-ASCII Windows path handling
  for GeoPackage, slow deep paging on the GBIF search API).

## What the humans did

- Defined the problem, track fit, data contract, design decisions (extent, resolution, selection rule,
  pressure proxies, index formula, responsible-display policy) and the split of work.
- Reviewed the code and outputs, decided on thresholds, and are responsible for all claims.
- The statistical modelling choices (final SDM, spatial CV, bootstrap) were made by the modelling lead.

## Safeguards

- No metrics, DOIs, licences or references were to be invented; anything the AI could not verify is
  marked `TODO: verify` in the docs and is on the pre-submission checklist.
- Literature details written from memory were flagged for manual verification.
- All numbers in the README, slides and dashboard are read from pipeline outputs, not typed by hand.

## Modelling side [modelling]

_To be completed by the modelling lead._
