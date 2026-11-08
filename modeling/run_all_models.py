"""One command for the whole final-model workflow (run from the repo root):

    python modeling/run_all_models.py            # prepare -> block size -> models -> null -> outputs -> figures -> summary
    python modeling/run_all_models.py --skip-fit # rebuild outputs/figures/summary from modeling/cache/

Covariates must exist first: python run_all.py --only worldclim
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NULL_SPECIES = ["orchis_anatolica", "anacamptis_pyramidalis", "ophrys_vicina"]


def run(*args: str) -> None:
    print("\n>>>", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], cwd=HERE, check=True)


def main() -> None:
    skip = "--skip-fit" in sys.argv
    if not skip:
        run("prepare.py")
        run("blocksize.py")
        run("run_models.py", "--force")
        import pandas as pd

        sp = pd.read_csv(HERE.parent / "data" / "processed" / "species_list.csv")
        run("null_model.py", "--n-null", "49", *sp.loc[sp["selected"], "species_slug"])
    run("assemble.py")
    run("figures.py")
    run("results_summary.py")


if __name__ == "__main__":
    main()
