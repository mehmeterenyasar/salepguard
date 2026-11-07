PY ?= python

.PHONY: all data model risk web app test lint
all:            ## full pipeline
	$(PY) run_all.py
data:
	for s in boundaries worldclim pressure protected gbif clean manifest; do $(PY) run_all.py --only $$s || exit 1; done
model:
	$(PY) run_all.py --only baseline
risk:
	$(PY) run_all.py --from validate
web:
	$(PY) run_all.py --only web
app:
	streamlit run app/app.py
test:
	$(PY) -m pytest -q
lint:
	ruff check src app scripts tests && black --check src app scripts tests
