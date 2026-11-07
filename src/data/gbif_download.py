"""Download all Orchidaceae occurrences in the training extent from GBIF.

Primary route: GBIF Download API (produces a citable DOI). Credentials come from
GBIF_USER / GBIF_PWD / GBIF_EMAIL (environment or a local, git-ignored .env).
Fallback: paged occurrence/search requests (no DOI; query + date are logged).

Usage:
    python -m src.data.gbif_download request   # submit, store key, return immediately
    python -m src.data.gbif_download wait      # poll until ready, then download + extract
    python -m src.data.gbif_download search    # fallback without credentials
"""

from __future__ import annotations

import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone

import pandas as pd
import requests

from src.common import RAW, config, download, get_logger, load_dotenv

log = get_logger("gbif")
API = "https://api.gbif.org/v1"
GBIF_DIR = RAW / "gbif"
STATE = GBIF_DIR / "download_state.json"
RAW_CSV = GBIF_DIR / "orchidaceae_extent.csv"

KEEP_COLS = [
    "gbifID",
    "datasetKey",
    "occurrenceStatus",
    "basisOfRecord",
    "family",
    "genus",
    "species",
    "infraspecificEpithet",
    "taxonRank",
    "scientificName",
    "verbatimScientificName",
    "taxonKey",
    "speciesKey",
    "countryCode",
    "stateProvince",
    "locality",
    "decimalLatitude",
    "decimalLongitude",
    "coordinateUncertaintyInMeters",
    "coordinatePrecision",
    "year",
    "month",
    "day",
    "eventDate",
    "institutionCode",
    "issue",
]


def _extent_wkt() -> str:
    e = config()["grid"]["training_extent"]
    x0, x1, y0, y1 = e["lon_min"], e["lon_max"], e["lat_min"], e["lat_max"]
    # counter-clockwise ring, as required by GBIF
    return f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"


def predicate() -> dict:
    return {
        "type": "and",
        "predicates": [
            {"type": "equals", "key": "FAMILY_KEY", "value": str(config()["taxa"]["gbif_family_key"])},
            {"type": "equals", "key": "HAS_COORDINATE", "value": "true"},
            {"type": "equals", "key": "HAS_GEOSPATIAL_ISSUE", "value": "false"},
            {"type": "equals", "key": "OCCURRENCE_STATUS", "value": "PRESENT"},
            {"type": "within", "geometry": _extent_wkt()},
        ],
    }


def _creds() -> tuple[str, str, str]:
    load_dotenv()
    user, pwd, email = (os.environ.get(k) for k in ("GBIF_USER", "GBIF_PWD", "GBIF_EMAIL"))
    if not (user and pwd and email):
        sys.exit(
            "GBIF_USER / GBIF_PWD / GBIF_EMAIL not set (env or .env). "
            "Create a free account at https://www.gbif.org/user/profile or run `search`."
        )
    return user, pwd, email


def request_download() -> str:
    if STATE.exists() and json.loads(STATE.read_text()).get("key"):
        key = json.loads(STATE.read_text())["key"]
        log.info("download already requested: %s", key)
        return key
    user, pwd, email = _creds()
    body = {
        "creator": user,
        "notificationAddresses": [email],
        "sendNotification": True,
        "format": config()["gbif"]["format"],
        "predicate": predicate(),
    }
    r = requests.post(f"{API}/occurrence/download/request", json=body, auth=(user, pwd), timeout=60)
    if r.status_code >= 400:
        sys.exit(f"GBIF request failed ({r.status_code}): {r.text}")
    key = r.text.strip()
    GBIF_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {"key": key, "requested_utc": datetime.now(timezone.utc).isoformat(), "predicate": predicate()},
            indent=2,
        )
    )
    log.info("GBIF download requested: %s", key)
    return key


def wait_and_fetch() -> None:
    key = request_download()
    poll = config()["gbif"]["poll_seconds"]
    while True:
        meta = requests.get(f"{API}/occurrence/download/{key}", timeout=60).json()
        status = meta.get("status")
        log.info("status=%s records=%s", status, meta.get("totalRecords"))
        if status == "SUCCEEDED":
            break
        if status in {"FAILED", "KILLED", "CANCELLED"}:
            sys.exit(f"GBIF download {key} ended with {status}")
        time.sleep(poll)
    state = json.loads(STATE.read_text())
    state.update(
        {
            "doi": meta.get("doi"),
            "totalRecords": meta.get("totalRecords"),
            "created": meta.get("created"),
            "downloadLink": meta.get("downloadLink"),
            "license": meta.get("license"),
        }
    )
    STATE.write_text(json.dumps(state, indent=2))
    z = download(meta["downloadLink"], GBIF_DIR / f"{key}.zip", log)
    with zipfile.ZipFile(z) as zf:
        name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        with zf.open(name) as fh:
            df = pd.read_csv(
                fh, sep="\t", quoting=3, dtype=str, on_bad_lines="warn", usecols=lambda c: c in KEEP_COLS
            )
    df.to_csv(RAW_CSV, index=False)
    log.info("saved %d records -> %s (DOI %s)", len(df), RAW_CSV.name, state["doi"])


def search_fallback() -> None:
    """Paged occurrence/search; each partition is kept below the 100k offset limit."""
    e = config()["grid"]["training_extent"]
    base = {
        "familyKey": config()["taxa"]["gbif_family_key"],
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
        "decimalLatitude": f"{e['lat_min']},{e['lat_max']}",
        "decimalLongitude": f"{e['lon_min']},{e['lon_max']}",
    }

    from concurrent.futures import ThreadPoolExecutor

    session = requests.Session()

    def get(params, timeout=120):
        for attempt in range(4):
            try:
                r = session.get(f"{API}/occurrence/search", params=params, timeout=timeout)
                r.raise_for_status()
                return r.json()
            except requests.RequestException:
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"GBIF search failed for {params}")

    def facet(params, field, limit=500):
        res = get({**params, "limit": 0, "facet": field, "facetLimit": limit})
        return {c["name"]: c["count"] for c in res["facets"][0]["counts"]} if res["facets"] else {}

    # Deep offsets are very slow on the search API, so partition by country x year
    # (x month for busy years) and keep every partition small. Records with no year
    # are fetched per country (they are dropped by cleaning anyway, but counted).
    parts, n_noyear = [], 0
    for cc, n_cc in facet(base, "country", 100).items():
        p = {**base, "country": cc}
        years = facet(p, "year")
        for y, n in years.items():
            if n <= 1500:
                parts.append(({**p, "year": y}, n))
            else:
                for mo, nm in facet({**p, "year": y}, "month", 12).items():
                    parts.append(({**p, "year": y, "month": mo}, nm))
        n_noyear += n_cc - sum(years.values())
    log.info(
        "search fallback: %d partitions; %d records without year/month not fetched", len(parts), n_noyear
    )

    def fetch(part):
        p, n = part
        out, offset = [], 0
        while True:
            res = get({**p, "limit": 300, "offset": offset})
            out.extend({k: r.get(k) for k in KEEP_COLS} for r in res["results"])
            offset += 300
            if res.get("endOfRecords") or not res["results"] or offset > 20_000:
                break
        return out

    rows = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, chunk in enumerate(ex.map(fetch, parts)):
            rows.extend(chunk)
            if i % 100 == 0:
                log.info("partition %d/%d, records so far %d", i, len(parts), len(rows))
    df = pd.DataFrame(rows).drop_duplicates("gbifID")
    GBIF_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_CSV, index=False)
    STATE.write_text(
        json.dumps(
            {
                "method": "occurrence/search fallback",
                "params": base,
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "doi": None,
                "totalRecords": len(df),
                "records_without_year_or_month_not_fetched": n_noyear,
            },
            indent=2,
        )
    )
    log.info("saved %d records (search fallback, no DOI)", len(df))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "wait"
    {"request": request_download, "wait": wait_and_fetch, "search": search_fallback}[cmd]()
