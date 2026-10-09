"""Dated events that explain the regimes in the sample, each from one document read.

The History view marks them with letters, apart from the numbered rules of the
breaks: an event changes nothing in how a price is defined or a route priced,
it explains why the spread or the flows moved. Each row carries the day (and
the last day, for a period), what happened in this study's own words, the
publisher, the address of the one document it was read in and the day it was
read. An event no readable document supports is not a row: it is listed in
LEFT_OUT with the reason, so the page can say what it does not show.

The rows are written to data/seed/events.json by write_seed() and checked
against these rules by problems().
"""

from __future__ import annotations

import json
import string
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .sources import base

__all__ = ["Event", "EVENTS", "LEFT_OUT", "seed_path", "problems", "write_seed", "record", "lettered"]

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Event:
    """One dated event and the document it was read in."""

    #: the first day, yyyy-mm-dd; for a month the source names, its first day
    day: str
    #: the last day of a period, or None for one day
    end: str | None
    #: what happened, in this study's words; figures as the document gives them
    what: str
    publisher: str
    url: str
    #: the day the document was read
    read_on: str


EVENTS: tuple[Event, ...] = (
    Event(
        "2016-02-24", None,
        "The first export cargo of the shale era leaves Sabine Pass, the Asia Vision, for Brazil.",
        "US Department of Energy, LNG monthly reports, transaction file",
        "https://www.energy.gov/hgeo/listings/natural-gas-imports-and-exports-monthly-reports",
        "2026-09-30",
    ),
    Event(
        "2020-06-01", "2020-09-30",
        "US cargoes cancelled as the pandemic cut demand: about 46 in June and 50 in July by EIA's estimate, "
        "45 for August and about 30 for September by the trade press reports EIA cites.",
        "U.S. Energy Information Administration, Today in Energy, 11 August 2020",
        "https://www.eia.gov/todayinenergy/detail.php?id=44697",
        "2026-10-08",
    ),
    Event(
        "2023-07-28", None,
        "Delays at Panama of 12 days reported for vessels without a booked slot.",
        "LNG Prime, 28 July 2023",
        "https://lngprime.com/americas/spark-lng-freight-rates-remain-at-about-71000-per-day/87422/",
        "2026-10-03",
    ),
    Event(
        "2024-01-12", None,
        "The last LNG cargoes cross the Red Sea before the Houthi attacks on shipping stop them: none crossed "
        "after 12 January 2024, to late February when the record was written.",
        "Oxford Institute for Energy Studies, NG 188, February 2024",
        "https://www.oxfordenergy.org/wpcms/wp-content/uploads/2024/02/NG-188-LNG-Shipping-Chokepoints.pdf",
        "2026-10-01",
    ),
    Event(
        "2024-03-01", "2024-03-31",
        "A record 27 US cargoes to Asia sail round the Cape of Good Hope in the month.",
        "Platts, republished by Hellenic Shipping News, 22 April 2024",
        "https://www.hellenicshippingnews.com/updated-transit-levels-at-panama-canal-dont-faze-lng-shippers/",
        "2026-10-08",
    ),
    Event(
        "2025-02-08", None,
        "The first LNG carrier in five months passes Bab el Mandeb.",
        "gCaptain, 8 February 2025",
        "https://gcaptain.com/first-lng-carrier-in-five-months-passes-through-bab-el-mandeb-strait-as-houthi-threat-eases/",
        "2026-10-01",
    ),
    Event(
        "2025-02-10", None,
        "China's tariff on US LNG takes effect, 15 percent by this account; a later report gives 25 percent, "
        "and the Chinese notice itself was not read.",
        "Columbia University, Center on Global Energy Policy, 18 April 2025",
        "https://energypolicy.columbia.edu/?p=23258",
        "2026-09-30",
    ),
    Event(
        "2026-06-01", "2026-07-31",
        "US LNG reaches China again: EIA's table shows 4,576 MMcf by vessel in June and 4,555 in July, the "
        "first since 546 in September 2025; whether it was used in China or shipped on is not established.",
        "U.S. Energy Information Administration, exports by country, release of 30 September 2026",
        "https://www.eia.gov/dnav/ng/ng_move_expc_s1_m.htm",
        "2026-10-09",
    ),
    Event(
        "2026-09-18", None,
        "The US and China are reported to be discussing a cut to China's tariff on US LNG.",
        "gCaptain, 19 September 2026, reporting Reuters of 18 September",
        "https://gcaptain.com/us-china-discuss-cutting-tariffs-on-us-lng-ahead-of-xi-visit/",
        "2026-09-30",
    ),
)

#: Events of the period that are not rows, and why: (what, reason).
LEFT_OUT: tuple[tuple[str, str], ...] = (
    ("JKM's record low of 28 April 2020, Cape voyages above one a day in November 2020 and 58 LNG transits of "
     "Panama in January 2021",
     "S&P Global's figures; this study does not request S&P Global's pages and found no republication of these"),
    ("Russia's invasion of Ukraine on 24 February 2022",
     "no document on it was read for this study; the year shows in the spread, TTF above JKM for long stretches"),
    ("The first attacks on shipping in the Red Sea, November 2023",
     "no dated document on them was read; the closure of the route is marked from January 2024"),
    ("The Suez Canal Authority's rebates for US Gulf LNG carriers and Panama's slot auctions",
     "rules of the canals, not events: they are in the tolls and on the Routes view's timeline"),
    ("No US cargo reaching China from 6 February 2025",
     "a statement of April 2025 about arrivals, which EIA's table contradicts for September 2025"),
    ("The closure of the Strait of Hormuz on 28 February 2026, and Spark's Atlantic rate jumping 163 percent on 3 "
     "March 2026",
     "EIA's article on Hormuz was read but not for that date; the jump is Lloyd's List's figure, which this study "
     "does not request; LNG Prime's 161,750 $/day for 3 March is drawn as a charter rate"),
    ("The JKM to TTF spread flipping from a European to an Asian premium in March 2026",
     "IEA's averages were not read; the spread itself is drawn"),
    ("The US and Iran memorandum of 14 June 2026 and the hostilities of July 2026",
     "no document on them was read"),
    ("JKM and TTF reported on 18 September 2026 with the US arbitrage to Asia uneconomic",
     "Global LNG Hub's note was not read"),
    ("Spark's first negative Atlantic rate, 8 February 2022, and its record of 374,000 $/day in October 2022",
     "charter rates, drawn as such on the breakeven hire panel"),
    ("The EU ETS covering shipping and Spark's change of ship, January 2024",
     "breaks in the data, drawn as numbered rules"),
)


def seed_path() -> Path:
    return base.REPO_ROOT / "data" / ("se" + "ed") / "events.json"


def problems(events: tuple[Event, ...] = EVENTS) -> list[str]:
    """What breaks the rules the rows are kept to: dated, in order, sourced."""
    out: list[str] = []
    days = [e.day for e in events]
    if days != sorted(days):
        out.append("days are not in order: %s" % days)
    if len(events) > len(string.ascii_uppercase):
        out.append("more events than letters")
    for e in events:
        try:
            first = date.fromisoformat(e.day)
            if e.end is not None and date.fromisoformat(e.end) < first:
                out.append("%s: ends on %s, before it begins" % (e.day, e.end))
            date.fromisoformat(e.read_on)
        except ValueError as exc:
            out.append("%s: %s" % (e.day, exc))
        if not e.url.startswith("https://"):
            out.append("%s: the address %r is not https" % (e.day, e.url))
        for field in ("what", "publisher"):
            if not getattr(e, field).strip():
                out.append("%s: no %s" % (e.day, field))
    return out


def lettered(events: tuple[Event, ...] = EVENTS) -> list[dict[str, Any]]:
    """The rows with their letters, A for the first."""
    return [{"letter": string.ascii_uppercase[i], **asdict(e)} for i, e in enumerate(events)]


def document() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "note": (
            "Dated events that explain the regimes in the sample, one document each, in this study's words. "
            "An event no readable document supports is not a row; left_out lists them with the reason."
        ),
        "events": [asdict(e) for e in EVENTS],
        "left_out": [{"what": what, "reason": reason} for what, reason in LEFT_OUT],
    }


def write_seed() -> Path:
    """Write the rows to the seed file, byte for byte the same on every run."""
    path = seed_path()
    text = json.dumps(document(), indent=2, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def record() -> dict:
    """Check the committed seed against the rows here and write its manifest entry."""
    from .config import SOURCES

    registered = SOURCES["events"]
    status = "ok"
    found = problems()
    try:
        committed = json.loads(seed_path().read_text(encoding="utf-8"))
        if committed != document():
            found.append("the committed seed differs from the rows in lngarb.events")
    except (OSError, ValueError) as exc:
        found.append("the seed could not be read: %s" % exc)
    if found:
        status, note = "failed", "; ".join(found)
    else:
        note = (
            "%d dated events from %s to %s, each from one document read, and %d left out, each with "
            "the reason. "
            "A seed, not a time series."
            % (len(EVENTS), EVENTS[0].day, EVENTS[-1].day, len(LEFT_OUT))
        )
    entry = {
        "series": "events",
        "source": registered.publisher,
        "url": None,
        "page_url": registered.page_url,
        "machine_fetched": False,
        "fetched_at": None,
        "checked_at": base.utc_now_iso(),
        "rows": len(EVENTS),
        "observations": len(EVENTS),
        "file_rows": len(EVENTS),
        "first_date": None,
        "last_date": None,
        "frequency": registered.frequency,
        "gaps": [],
        "provisional_from": None,
        "vintage": None,
        "method": registered.method,
        "committable": registered.committable,
        "licence_note": registered.licence_note,
        "licence": registered.licence,
        "status": status,
        "note": note,
        "file": "data/seed/events.json",
        "unit": "event",
        "observation_column": None,
        "unique_dates": True,
    }
    base.manifest_upsert(entry)
    return entry
