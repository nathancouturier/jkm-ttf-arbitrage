"""The optional private layer: settlements and freight the owner exports himself.

Daily JKM, TTF and Henry Hub settlements by contract month, and a licensed
freight series, are not redistributable. The owner saves them as CSV files in
data/private/user/, one or several, each with exactly the columns

    date, series, contract_month, value, unit, source

and this module reads and checks them. It never fetches, and nothing it reads
is committed or deployed: data/private/ is ignored by git and left out of the
site. The site is complete without the layer, and nothing the study publishes
changes when it is present, so the committed artifacts stay the same on every
machine; what the layer allows is private work, such as comparing the weekly
averages with the settlements of the same delivery month (aligned_spread).

A file that breaks a rule is refused whole, with every problem named.
"""

from __future__ import annotations

import math
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ..config import BOUNDS_HENRY_HUB_USD_MMBTU, BOUNDS_HIRE_USD_DAY, BOUNDS_LNG_USD_MMBTU
from . import base
from .base import SourceError

__all__ = ["COLUMNS", "SERIES", "DIRECTORY", "problems", "read", "summary", "aligned_spread"]

COLUMNS = ("date", "series", "contract_month", "value", "unit", "source")

#: The series the layer takes, each with its unit and the bounds a value must
#: lie in. Gas settlements are by contract month; a freight rate is not.
SERIES: Mapping[str, dict[str, Any]] = {
    "jkm_settlement": {"unit": "USD/MMBtu", "bounds": BOUNDS_LNG_USD_MMBTU, "contract_month": True},
    "ttf_settlement": {"unit": "USD/MMBtu", "bounds": BOUNDS_LNG_USD_MMBTU, "contract_month": True},
    "henry_hub_settlement": {"unit": "USD/MMBtu", "bounds": BOUNDS_HENRY_HUB_USD_MMBTU, "contract_month": True},
    "freight_rate": {"unit": "USD/day", "bounds": BOUNDS_HIRE_USD_DAY, "contract_month": False},
}

DIRECTORY: Path = base.PRIVATE / "user"

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def problems(frame: pd.DataFrame, name: str = "the file") -> list[str]:
    """Everything that breaks the layer's rules in one file, in words."""
    out: list[str] = []
    if tuple(frame.columns) != COLUMNS:
        return ["%s has the columns %s, not %s" % (name, ", ".join(map(str, frame.columns)), ", ".join(COLUMNS))]
    for index, row in frame.iterrows():
        where = "%s, row %d" % (name, index + 2)
        day = None
        try:
            if not _DAY.match(str(row["date"])):
                raise ValueError
            day = date.fromisoformat(str(row["date"]))
        except ValueError:
            out.append("%s: the date %r is not yyyy-mm-dd" % (where, row["date"]))
        if day is not None and day > date.today():
            out.append("%s: the date %s lies in the future" % (where, day))
        spec = SERIES.get(str(row["series"]))
        if spec is None:
            out.append("%s: the series %r is not one of %s" % (where, row["series"], ", ".join(SERIES)))
            continue
        month = row["contract_month"]
        has_month = isinstance(month, str) and month.strip() != ""
        if spec["contract_month"] and not (has_month and _MONTH.match(month)):
            out.append("%s: a settlement needs its contract month as yyyy-mm, not %r" % (where, month))
        elif spec["contract_month"] and day is not None and month < day.isoformat()[:7]:
            out.append("%s: the contract month %s had expired by %s" % (where, month, day))
        if not spec["contract_month"] and has_month:
            out.append("%s: a freight rate has no contract month" % where)
        try:
            value = float(row["value"])
        except (TypeError, ValueError):
            value = math.nan
        lo, hi = spec["bounds"]
        if not math.isfinite(value):
            out.append("%s: the value %r is not a number; leave the row out rather than write a zero" % (where, row["value"]))
        elif not lo <= value <= hi:
            out.append("%s: %s lies outside %s to %s" % (where, value, lo, hi))
        if str(row["unit"]) != spec["unit"]:
            out.append("%s: the unit of %s is %s, not %r" % (where, row["series"], spec["unit"], row["unit"]))
        if not str(row["source"]).strip() or str(row["source"]) == "nan":
            out.append("%s: no source" % where)
    keys = frame[["date", "series", "contract_month"]].astype(str)
    if keys.duplicated().any():
        out.append("%s repeats a date, series and contract month" % name)
    return out


def read(directory: Path | None = None) -> pd.DataFrame | None:
    """Every CSV in the private directory, checked, as one frame; None when there is none.

    Raises SourceError naming every problem when a file breaks the rules."""
    directory = DIRECTORY if directory is None else directory
    files = sorted(directory.glob("*.csv")) if directory.exists() else []
    if not files:
        return None
    frames, found = [], []
    for path in files:
        frame = pd.read_csv(path, dtype={"contract_month": str, "date": str}, keep_default_na=False,
                            na_values={"value": [""]})
        found += problems(frame, path.name)
        frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    if not found and out[["date", "series", "contract_month"]].astype(str).duplicated().any():
        found.append("two files give the same date, series and contract month")
    if found:
        raise SourceError("the private layer refuses its files: " + "; ".join(found[:20]))
    out["date"] = pd.to_datetime(out["date"])
    out["value"] = out["value"].astype(float)
    return out.sort_values(["series", "date", "contract_month"]).reset_index(drop=True)


def summary(frame: pd.DataFrame | None) -> dict[str, Any]:
    """What the layer holds, in counts and dates only: no value leaves it."""
    if frame is None or frame.empty:
        return {"present": False}
    return {
        "present": True,
        "series": sorted(frame["series"].unique()),
        "rows": int(len(frame)),
        "first": frame["date"].min().date().isoformat(),
        "last": frame["date"].max().date().isoformat(),
    }


def aligned_spread(frame: pd.DataFrame) -> pd.DataFrame:
    """JKM over TTF day by day for the same contract month, where both settled: the
    comparison the weekly averages cannot make, kept private like its inputs."""
    jkm = frame[frame["series"] == "jkm_settlement"][["date", "contract_month", "value"]]
    ttf = frame[frame["series"] == "ttf_settlement"][["date", "contract_month", "value"]]
    both = jkm.merge(ttf, on=["date", "contract_month"], suffixes=("_jkm", "_ttf"))
    both["spread"] = both["value_jkm"] - both["value_ttf"]
    return both[["date", "contract_month", "spread"]].sort_values(["date", "contract_month"]).reset_index(drop=True)
