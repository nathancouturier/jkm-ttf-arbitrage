"""Price every observation again with the fresh water surcharge at Gatun Lake's level of each transit, privately.

Usage, from the repository root, once the owner's levels are saved and read
(python scripts/refresh.py --only user):

    PYTHONPATH=src python scripts/gatun_check.py

Reads the private series acp_gatun_level_daily, runs every observation
through the engine at the central hire twice, at the 5 percent share the site
uses and at the Authority's curve at each transit's level (5 percent where
the level is missing), and writes the difference by date to
data/private/gatun_check.csv with a summary on the terminal. Nothing it
computes is published until open question 54 is settled.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from lngarb import analysis, canals  # noqa: E402
from lngarb.sources import base  # noqa: E402

SERIES = "acp_gatun_level_daily"
OUT = base.PRIVATE / "gatun_check.csv"
COLUMNS = ("panama_netback", "panama_s_star", "panama_arb", "best_route_east", "s_star_best", "arb")


def levels() -> dict:
    frame = base.read_cache(SERIES, directory="private")
    if frame is None or frame.empty:
        raise SystemExit("no private cache %s: save the levels and run python scripts/refresh.py --only user" % SERIES)
    frame = frame.dropna(subset=["level_ft"])
    return {day.date(): float(level) for day, level in zip(frame["date"], frame["level_ft"])}


def central(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows[rows["hire_level"] == "central"]
    return rows[["day", "frequency", *COLUMNS]].set_index(["day", "frequency"])


def main() -> int:
    held = levels()
    with analysis.reading_once():
        obs = analysis.observations()
        assumed, _ = analysis.work(obs)
        with canals.gatun_levels(held):
            at_level, _ = analysis.work(obs)
    a, b = central(assumed), central(at_level)
    out = a.join(b, lsuffix="_at_5_percent", rsuffix="_at_level")
    out["panama_s_star_change"] = out["panama_s_star_at_level"] - out["panama_s_star_at_5_percent"]
    out.reset_index().to_csv(OUT, index=False, float_format="%.6f", lineterminator="\n")
    moved = out["panama_s_star_change"].dropna()
    moved = moved[moved != 0.0]
    print("levels held: %d days, %s to %s" % (len(held), min(held), max(held)))
    print("observations priced: %d; Panama S* moved on %d" % (len(out), len(moved)))
    if len(moved):
        print("change in Panama S*, USD/MMBtu: mean %+.4f, smallest %+.4f, largest %+.4f"
              % (moved.mean(), moved.min(), moved.max()))
    routes = out[out["best_route_east_at_5_percent"] != out["best_route_east_at_level"]]
    print("cheapest route east differs on %d observations" % len(routes))
    for column in ("panama_arb", "arb"):
        before, after = out[column + "_at_5_percent"], out[column + "_at_level"]
        flips = out[(before > 0) != (after > 0)]
        print("%s changes sign on %d observations" % (column, len(flips)))
    print("written: %s (private, never committed)" % OUT.relative_to(base.REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
