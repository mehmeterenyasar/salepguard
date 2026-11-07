PY ?= python

.PHONY: all data model risk web app test lint
all:            ## full pipeline
	$(PY) run_all.py
data:
	$(PY) run_all.py --from boundaries --only manifest || true
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
