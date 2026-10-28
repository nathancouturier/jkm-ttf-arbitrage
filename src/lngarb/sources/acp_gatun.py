"""Gatun Lake's daily water level, from the Panama Canal Authority's water level indicators page.

The Authority's Maritime Services site serves, from one page, the lake's level
every day since 1965 as a CSV, a sixty day projection with the fresh water
surcharge share each projected level gives, and a PDF of the indicators. The
page carries a notice stricter than the site's general terms: the content may
be used for information purposes only, and not copied, distributed, published
or made into derivative works without the Authority's prior written consent.
So the series is not committable: it is written to data/private/, the site
shows nothing computed from it, and it serves the owner's private checks of
the fresh water surcharge the engine holds (docs/open-questions.md, 53 and 54).

The projection's surcharge column is the one figure the Authority publishes
of its own curve at work. The adapter reads it to check the engine's curve
(lngarb.canals.panama_fresh_water_share_at_level) and records the largest
difference in the manifest note; no projected value is kept.
"""

from __future__ import annotations

import io
import re
from datetime import date

import pandas as pd

from .. import canals
from ..config import BOUNDS_LAKE_FEET, _ACP_HYDROLOGY_NOTE
from .base import Adapter, SourceError, http_get

__all__ = ["AcpGatunLakeLevelDaily", "parse_history", "parse_projection", "curve_check",
           "HISTORY_URL", "PROJECTION_URL", "PAGE_URL"]

PAGE_URL = "https://evtms-rpts.pancanal.com/eng/h2o/index.html"
HISTORY_URL = "https://evtms-rpts.pancanal.com/eng/h2o/Download_Gatun_Lake_Water_Level_History.csv"
PROJECTION_URL = "https://evtms-rpts.pancanal.com/eng/h2o/Gatun_Water_Level_Projection.csv"
#: the seconds left between requests to the Authority's hosts, as pancanal.com's robots file asks
CRAWL_DELAY_S = 10.0
#: the history file's header, exactly as served
HISTORY_HEADER = "DATE_LOG,GATUN_LAKE_LEVEL(FEET)"
_PROJECTION_ROW = re.compile(r"^(\d{2})/(\d{2})/(\d{4}),\s*([0-9.]+),\s*([0-9.]+)")


def parse_history(text: str) -> pd.DataFrame:
    """The daily levels of the history file: date and level_ft, one row a day, in order."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != HISTORY_HEADER:
        raise SourceError("the history file does not start with %r" % HISTORY_HEADER)
    frame = pd.read_csv(io.StringIO("\n".join(lines)))
    frame = frame.rename(columns={"DATE_LOG": "date", "GATUN_LAKE_LEVEL(FEET)": "level_ft"})
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d")
    frame["level_ft"] = pd.to_numeric(frame["level_ft"], errors="coerce")
    if frame["level_ft"].isna().any():
        bad = frame.loc[frame["level_ft"].isna(), "date"].dt.strftime("%Y-%m-%d").tolist()
        raise SourceError("the history file holds a level that is not a number on %s" % ", ".join(bad[:5]))
    if frame["date"].duplicated().any():
        raise SourceError("the history file repeats a day")
    if not frame["date"].is_monotonic_increasing:
        raise SourceError("the history file's days are not in order")
    return frame[["date", "level_ft"]].reset_index(drop=True)


def parse_projection(text: str) -> pd.DataFrame:
    """The projection file's rows: date, level_ft and the surcharge share in percent the Authority prints."""
    rows = []
    for line in text.splitlines():
        found = _PROJECTION_ROW.match(line.strip())
        if found:
            month, day, year, level, share = found.groups()
            rows.append({"date": pd.Timestamp(int(year), int(month), int(day)), "level_ft": float(level),
                         "surcharge_percent": float(share)})
    if not rows:
        raise SourceError("the projection file holds no row of a projected level and surcharge")
    return pd.DataFrame(rows)


def curve_check(projection: pd.DataFrame) -> float:
    """The largest difference, in points of percent, between the engine's curve and the surcharge the
    Authority prints for each projected level, on the day the projection is for."""
    worst = 0.0
    for row in projection.to_dict("records"):
        ours = canals.panama_fresh_water_share_at_level(float(row["level_ft"]), row["date"].date())
        if ours is None:
            raise SourceError("the engine's curve gives no share on %s" % row["date"].date())
        worst = max(worst, abs(100.0 * ours - float(row["surcharge_percent"])))
    return worst


class AcpGatunLakeLevelDaily(Adapter):
    """Gatun Lake's level every day since 1965, feet, as the Authority's history file serves it. Not committable."""

    name = "acp_gatun_lake_level_daily"
    source = "Panama Canal Authority, Maritime Services, Gatun Lake historical water levels"
    url = HISTORY_URL
    page_url = PAGE_URL
    unit = "feet"
    frequency = "daily"
    method = "published"
    committable = False
    licence_note = _ACP_HYDROLOGY_NOTE
    required_cols = ("date", "level_ft")
    bounds = {"level_ft": BOUNDS_LAKE_FEET}
    min_observations = {"level_ft": 365}
    observation_column = "level_ft"

    def __init__(self, *, history: str | None = None, projection: str | None = None):
        # texts given stand in for the files, for a run with no network
        self.history = history
        self.projection = projection

    def fetch(self) -> pd.DataFrame:
        history = self.history if self.history is not None else http_get(HISTORY_URL, delay=CRAWL_DELAY_S).text
        frame = parse_history(history)
        checked = ""
        projection = self.projection
        if projection is None and self.history is None:
            projection = http_get(PROJECTION_URL, delay=CRAWL_DELAY_S).text
        if projection is not None:
            worst = curve_check(parse_projection(projection))
            checked = (" The Authority's projection file prints the surcharge share of each projected day; the "
                       "engine's curve reproduces it " + ("to the two decimals the Authority prints." if worst < 0.005
                                                          else "to within %.2f points of percent." % worst))
        first, last = frame["date"].iloc[0].date(), frame["date"].iloc[-1].date()
        self.vintage = "history file read on %s" % date.today().isoformat()
        self.note = (
            "%d daily levels from %s to %s, as the Authority's history file serves them, kept privately: the "
            "page's notice permits use for information only and forbids copying, publication and derivative "
            "works without the Authority's written consent, so nothing computed from this series is published."
            % (len(frame), first, last) + checked
        )
        return frame
