"""Run the full SalepGuard pipeline end to end (cached steps are skipped quickly).

python run_all.py            # everything
python run_all.py --from risk
"""

import argparse
import subprocess
import sys

STEPS = [
    ("boundaries", ["-m", "src.data.boundaries"]),
    ("worldclim", ["-m", "src.data.worldclim"]),
    ("pressure", ["-m", "src.features.pressure"]),
    ("protected", ["-m", "src.data.protected_areas"]),
    ("gbif", ["-m", "src.data.gbif_download", "wait"]),
    ("clean", ["-m", "src.data.clean_occurrences"]),
    ("manifest", ["-m", "src.data.manifest"]),
    ("baseline", ["-m", "src.models.baseline"]),
    ("validate", ["scripts/validate_outputs.py"]),
    ("risk", ["-m", "src.risk.priority"]),
    ("web", ["-m", "src.viz.web_layers"]),
    ("figures", ["-m", "src.viz.figures"]),
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default=STEPS[0][0], choices=[s for s, _ in STEPS])
    ap.add_argument("--only", default=None, choices=[s for s, _ in STEPS])
    a = ap.parse_args()
    names = [s for s, _ in STEPS]
    todo = STEPS[names.index(a.start) :] if not a.only else [STEPS[names.index(a.only)]]
    for name, args in todo:
        print(f"\n=== {name} ===", flush=True)
        subprocess.run([sys.executable, *args], check=True)
