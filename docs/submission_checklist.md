# Pre-submission checklist (deadline 8 Nov 2026, 11:00 EET = 12:00 TRT; aim for 11:00 TRT)

## Data and models
- [x] GBIF Download API run → DOI 10.15468/dl.mfzrky in README, manifest, Devpost
- [x] WDPA Nov 2026 (17 public Turkish sites) merged with OSM protected areas
- [x] Final model outputs in `outputs/models/` → `python scripts/validate_outputs.py outputs/models` passes
- [x] `python run_all.py --from risk` (index, comparison, web layers, figures) re-run with the final model
- [x] README / slides / Devpost numbers updated from `outputs/risk/summary.json`
- [x] Teammate's sections of `docs/methods.md`, `docs/limitations.md`, `docs/ai_usage.md` filled in

## Repository
- [ ] Repo is public; LICENSE present; no `.env` or secrets committed (`git log -p | grep -i gbif_pwd` is empty)
- [ ] README complete: dashboard, video and slide links; team names; all `TODO` resolved or explicitly marked
- [x] Every `TODO: verify` reference, DOI and licence checked against the source
- [x] `pytest -q` and `ruff check` pass
- [ ] Fresh clone: `pip install -r requirements-dev.txt && streamlit run app/app.py` works

## Deliverables
- [x] Dashboard live on Streamlit Community Cloud (https://salepguard.streamlit.app); opens in a private window
- [ ] Video ≤ 10 min, public or unlisted, link works while logged out
- [x] Slides ≤ 10, exported to PDF in `slides/`
- [ ] Devpost: all fields filled (`docs/devpost_submission.md`), track selected, both team members added,
      links working, submitted before the deadline
