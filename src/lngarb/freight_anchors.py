"""Reported LNG carrier charter rates, one per month at most, each from a dated article.

This study builds no freight series. Spark's assessments are proprietary, and
none is collected, rebuilt or interpolated. What it keeps instead is a short
list of individual figures that were read in a dated, readable article or
document, each with the assessment it names and the vessel it is for, so that
a reader can set each one against the breakeven hire the engine computes from
prices. A row carries the figure, the date it refers to (empty when the article
gives none, with the article's own date beside it), the assessment and the
vessel basis (marked inferred where the article does not state them), the
publisher and the article's address, never the article's sentence.

The rows are written to data/seed/freight_anchors.json by write_seed() and
checked against these rules by problems(). docs/sources.md, sections 2.13 and
2.14, quotes the terms they are read under.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .config import BOUNDS_HIRE_USD_DAY, PARAMETERS
from .sources import base

__all__ = ["Anchor", "ANCHORS", "ASSESSMENT_WORDS", "SHIPS", "seed_path", "problems", "write_seed", "record",
           "ship_on", "anchor_day", "hire_levels", "hire_levels_by_ship"]

#: The two ships the engine prices with, keyed as the Model view keys them, in
#: the order they served: the 160,000 m3 TFDE to 1 January 2024 and the
#: 174,000 m3 two-stroke from 2 January 2024, the day Spark's benchmark changed
#: ship (lngarb.config, vessel_174k_from). A reported rate belongs to the ship
#: of its own day, whatever the article names.
SHIPS: tuple[tuple[str, str], ...] = (("tfde_160k", "160,000 m3 TFDE"), ("two_stroke_174k", "174,000 m3 two-stroke"))

#: What each assessment named in the anchors is, in words a reader needs once:
#: from Spark's LNG Freight Methodology 3.8, named and not linked (docs/sources.md
#: 2.13). Spark30S is the Atlantic basin's spot charter rate for a thirty day
#: round trip, 25 days at sea at 17 knots, a day to load, a day to discharge
#: and three flex days, in dollars a day, assessed daily since April 2022 and
#: twice a week before; the ship is the 174,000 m3 two-stroke from 2 January
#: 2024 and the 160,000 m3 TFDE before.
ASSESSMENT_WORDS: dict[str, str] = {
    "Spark30S Atlantic": (
        "Spark's spot charter rate for a thirty day round trip in the Atlantic basin, 25 days at sea, "
        "a day to load, a day to discharge and three flex days, in dollars a day"
    ),
}

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Anchor:
    """One reported charter rate."""

    #: the month the figure belongs to, yyyy-mm
    month: str
    #: the day the rate refers to, when the article states it
    rate_date: str | None
    #: the day the article was published
    article_date: str | None
    hire_usd_day: float
    assessment: str
    assessment_stated: bool
    vessel: str
    vessel_stated: bool
    publisher: str
    url: str | None
    note: str = ""


ANCHORS: tuple[Anchor, ...] = (
    Anchor(
        "2021-01", "2021-01-08", "2021-01-13", 322_500.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/lng-terminals/spot-lng-prices-charter-rates-continue-to-skyrocket/9923/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2021-03", "2021-03-09", "2021-03-09", 19_750.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/lng-charter-rates-remain-low-after-january-surge/14237/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2021-10", "2021-10-05", "2021-10-06", 67_750.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "gCaptain, a Reuters wire quoting Spark",
        "https://gcaptain.com/lng-ship-rates-climb-due-to-widening-spread-between-europe-and-asia-prices/",
        "The Reuters wire names Tuesday 5 October 2021 and a 160,000 m3 TFDE carrier, and the "
        "Atlantic rate without naming the assessment; it also quotes an Atlantic forward rate "
        "for December of 136,000 $/day, not kept."
    ),
    Anchor(
        "2022-01", "2022-01-11", "2022-01-11", 34_250.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/lng-charter-rates-continue-to-fall/38750/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2022-02", "2022-02-08", None, -750.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "Spark Commodities, note on negative freight rates", None,
        "The note is undated; it is named, not linked. The vessel is the one Spark's "
        "methodology of that time assesses; the note does not name it. Published "
        "rounded to the nearest 250 $/day.",
    ),
    Anchor(
        "2022-03", "2022-03-04", "2022-03-07", 28_250.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/lng-freight-rates-up-spot-prices-surge/44933/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name."
    ),
    Anchor(
        "2022-06", "2022-06-16", "2022-06-16", 77_750.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/lng-freight-rates-drop-on-freeport-shutdown/54678/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name."
    ),
    Anchor(
        "2022-09", "2022-09-12", "2022-09-13", 102_750.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/lng-freight-rates-continue-to-rise/61383/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name."
    ),
    Anchor(
        "2022-10", "2022-10-10", "2022-10-10", 374_000.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/spark-atlantic-lng-freight-rate-hits-374000-per-day/63423/",
        "The article does not name the vessel for this figure; LNG Prime's article of 20 "
        "October 2022 does, and reports 482,250 $/day for 20 October, the highest figure "
        "reported that month in the articles read. The first figure reported is kept.",
    ),
    Anchor(
        "2022-11", None, "2022-11-22", 447_000.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/spark-says-lng-freight-rates-drop-in-both-basins/67048/",
        "Read from the article's text, which names no day: the article's date stands."
    ),
    Anchor(
        "2022-12", "2022-12-09", "2022-12-09", 182_500.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/lng-freight-rates-dip-below-200000-per-day/68461/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2023-01", "2023-01-12", "2023-01-13", 96_750.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/lng-freight-rates-drop-below-100000-per-day/70797/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2023-02", "2023-02-03", "2023-02-06", 55_750.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/atlantic-lng-freight-rates-continue-downward-trend/72774/",
        "Read from the article's text, which names the day. The vessel is the one Spark's "
        "methodology assessed on that date, which the article does not name. LNG Prime "
        "printed the figure as $55.750/day, a misplaced separator, read as 55,750."
    ),
    Anchor(
        "2023-03", None, "2023-03-21", 51_250.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/spark-atlantic-lng-freight-rates-drop-to-51250-per-day/76806/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2023-04", None, "2023-04-14", 42_750.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/spark-pacific-lng-freight-rates-drop-to-lowest-level-this-year/78857/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2023-05", "2023-05-09", "2023-05-10", 41_250.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/spark-pacific-lng-freight-rates-drop-to-46750-per-day/81086/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name."
    ),
    Anchor(
        "2023-06", None, "2023-06-08", 45_000.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/lng-freight-rates-rise-in-both-basins/83370/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2023-07", None, "2023-07-28", 71_250.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/spark-lng-freight-rates-remain-at-about-71000-per-day/87422/",
        "The day is not stated: the week ending 21 or 28 July 2023. The same article "
        "reports 12 days of Panama delay for unbooked vessels.",
    ),
    Anchor(
        "2023-08", None, "2023-08-04", 75_500.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spark-atlantic-lng-freight-rate-for-october-rises-above-200000-per-day/88042/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2023-09", "2023-09-01", "2023-09-01", 137_750.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spark-spot-lng-freight-rates-rise-over-10-percent-in-both-basins/90559/",
        "Read from the article's text, which names the day. The Atlantic rate is read as "
        "Spark's Spark30S assessment, which the article does not name. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2023-10", "2023-10-06", "2023-10-06", 147_000.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spark-spot-lng-shipping-rates-continue-to-decline/93998/",
        "Read from the article's text, which names the day. The vessel is the one Spark's "
        "methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2023-11", None, "2023-11-03", 165_000.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spot-lng-shipping-rates-continue-to-rise/96620/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2023-12", None, "2023-12-01", 155_250.0, "Spark30S Atlantic", False,
        "160,000 m3 TFDE", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spot-lng-shipping-rates-european-prices-drop-this-week/99095/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "Atlantic rate is read as Spark's Spark30S assessment, which the article does not "
        "name. The vessel is the one Spark's methodology assessed on that date, which the "
        "article does not name."
    ),
    Anchor(
        "2024-01", None, "2024-01-05", 108_500.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spot-lng-shipping-rates-continue-to-decline-2/101504/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2024-02", None, "2024-02-02", 52_750.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spot-lng-freight-rates-continue-to-drop-european-prices-rise/103896/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2024-03", None, "2024-03-29", 46_500.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/spot-lng-shipping-rates-drop-below-50000-per-day/108680/",
        "The day is not stated: the week of the article.",
    ),
    Anchor(
        "2024-04", "2024-04-18", "2024-04-22", 44_500.0, "Platts Atlantic day rate", True,
        "two-stroke, size not stated", True,
        "Hellenic Shipping News, reporting Platts",
        "https://www.hellenicshippingnews.com/updated-transit-levels-at-panama-canal-dont-faze-lng-shippers/",
        "A secondary report; Platts' own page could not be read. The same report gives "
        "33,000 $/day for a TFDE.",
    ),
    Anchor(
        "2024-05", None, "2024-05-03", 42_500.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/spot-lng-shipping-rates-steady-european-prices-rise/111296/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2024-06", None, "2024-06-07", 57_000.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/atlantic-lng-shipping-rates-continue-to-climb-european-prices-drop/114236/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2024-07", None, "2024-07-05", 89_500.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/lng-shipping-rates-slightly-up-european-prices-drop/116451/",
        "Read from the article's text, which names no day: the article's date stands. The "
        "vessel is the one Spark's methodology assessed on that date, which the article does "
        "not name."
    ),
    Anchor(
        "2024-08", None, "2024-08-02", 73_750.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/pacific-lng-shipping-rates-up-european-prices-jump/119938/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2024-09", None, "2024-09-06", 59_250.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/atlantic-lng-shipping-rates-drop-below-60000-per-day/124272/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2024-10", None, "2024-10-04", 51_500.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/lng-shipping-rates-continue-to-decline-european-prices-rise/127980/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2024-11", None, "2024-11-01", 18_250.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/atlantic-lng-shipping-rates-dip-to-just-18250-per-day/131153/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2024-12", None, "2024-12-13", 22_750.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/spot-lng-shipping-rates-remain-low-european-prices-dip/135694/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-01", None, "2025-01-03", 24_750.0, "Spark30S Atlantic", True,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/spot-lng-shipping-rates-slightly-up-european-prices-jump/137044/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The vessel is the one "
        "Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-02", "2025-02-04", "2025-02-05", 4_250.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "gCaptain, a Reuters wire quoting Spark",
        "https://gcaptain.com/lng-shipping-rates-plunge-on-increasing-vessel-availability/",
        "The Reuters wire names Tuesday 4 February 2025 and the two-stroke ship, and the "
        "Atlantic rate without naming the assessment."
    ),
    Anchor(
        "2025-03", None, "2025-03-14", 25_750.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/atlantic-lng-shipping-rates-rise-to-four-month-high/145018/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-05", None, "2025-05-23", 32_000.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/europe/atlantic-lng-shipping-rates-down-for-third-week-in-a-row/152313/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-06", None, "2025-06-13", 33_000.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/atlantic-lng-shipping-rates-rise-to-33000-per-day/154198/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-08", None, "2025-08-15", 36_000.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/atlantic-lng-rates-remain-at-36000-per-day-european-prices-down/160186/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-10", None, "2025-10-31", 61_250.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/atlantic-lng-shipping-rates-jump-to-61250-per-day/167599/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-11", None, "2025-11-07", 68_000.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/atlantic-lng-shipping-rates-rise-to-68000-per-day/168271/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2025-12", None, "2025-12-19", 92_000.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/atlantic-lng-shipping-rates-drop-to-92000-per-day/172588/",
        "The figure is in the article's title, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2026-01", None, "2026-01-02", 71_750.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/top-news-of-the-week/atlantic-lng-rates-drop-to-71750-per-day/173283/",
        "The figure is in the article's title, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2026-02", None, "2026-02-13", 22_500.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/atlantic-lng-rates-rise-to-22500-per-day/177606/",
        "The figure is in the article's public summary, the article itself behind LNG Prime's "
        "subscription; no day is named, so the article's date stands. The Atlantic rate is "
        "read as Spark's Spark30S assessment, which the article does not name. The vessel is "
        "the one Spark's methodology assessed on that date, which the article does not name."
    ),
    Anchor(
        "2026-03", "2026-03-03", "2026-03-03", 161_750.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark Commodities",
        "https://lngprime.com/europe/atlantic-lng-rates-surge-to-161750-per-day/179110/",
        "The first figure reported in March 2026, read from the article's opening "
        "paragraph, which gives the Atlantic rate for Tuesday 3 March and credits Spark "
        "Commodities; the assessment and vessel are inferred, as for August 2026. LNG "
        "Prime's article of 4 March gives 278,250 $/day for Wednesday 4 March.",
    ),
    Anchor(
        "2026-04", None, "2026-04-03", 92_000.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark Commodities and Fearnley LNG",
        "https://lngprime.com/asia/atlantic-lng-rates-down-to-92000-per-day/182236/",
        "The first figure reported in April 2026, read from the article's headline; its "
        "opening paragraph credits Spark Commodities and Fearnley LNG for the week's rates "
        "and gives no figure. The assessment, the vessel and the day are inferred.",
    ),
    Anchor(
        "2026-08", None, "2026-08-28", 11_750.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/atlantic-spot-lng-rates-drop-to-11750-per-day/195938/",
        "Read from the article's opening paragraph, which names neither the assessment "
        "nor the vessel nor the day; Spark's Atlantic spot assessment and its current "
        "vessel are inferred.",
    ),
    Anchor(
        "2026-09", None, "2026-09-18", 25_250.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/asia/atlantic-lng-rates-continue-to-increase/197077/",
        "Read from the article's opening paragraph; assessment, vessel and day inferred "
        "as for August 2026.",
    ),
    Anchor(
        "2026-10", None, "2026-10-02", 31_500.0, "Spark30S Atlantic", False,
        "174,000 m3 two-stroke", False,
        "LNG Prime, quoting Spark Commodities",
        "https://lngprime.com/asia/atlantic-lng-rates-rise-to-31500-per-day/197834/",
        "Read from the article's opening paragraph; assessment, vessel and day inferred "
        "as for August 2026.",
    ),
)


def seed_path() -> Path:
    return base.REPO_ROOT / "data" / ("se" + "ed") / "freight_anchors.json"


def problems(anchors: tuple[Anchor, ...] = ANCHORS) -> list[str]:
    """What breaks the rules the rows are kept to: one per month, dated, in range."""
    out: list[str] = []
    months = [a.month for a in anchors]
    if months != sorted(months) or len(set(months)) != len(months):
        out.append("months are not increasing and unique: %s" % months)
    lo, hi = BOUNDS_HIRE_USD_DAY
    for a in anchors:
        if not lo <= a.hire_usd_day <= hi:
            out.append("%s: %s $/day is outside %s to %s" % (a.month, a.hire_usd_day, lo, hi))
        day = a.rate_date or a.article_date
        if day is None:
            out.append("%s: neither the rate's day nor the article's is known" % a.month)
        else:
            if day[:7] != a.month:
                out.append("%s: dated %s, another month" % (a.month, day))
            date.fromisoformat(day)
        if a.url is not None and not a.url.startswith("https://"):
            out.append("%s: the address %r is not https" % (a.month, a.url))
    return out


def document() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "unit": "USD per day",
        "note": (
            "Individual reported charter rates, never a series: no value is interpolated "
            "between them. Each row names its assessment and vessel, and says whether the "
            "article states them or this study infers them."
        ),
        "anchors": [asdict(a) for a in ANCHORS],
    }


def write_seed() -> Path:
    """Write the rows to the seed file, byte for byte the same on every run."""
    path = seed_path()
    text = json.dumps(document(), indent=2, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def anchor_day(anchor: Anchor) -> date:
    """The day a figure refers to, or its article's day when none is stated."""
    return date.fromisoformat(anchor.rate_date or anchor.article_date)


def ship_on(when: date | str) -> str:
    """The key of the ship the engine prices a day with."""
    day = date.fromisoformat(when) if isinstance(when, str) else when
    return SHIPS[1][0] if day >= date.fromisoformat(PARAMETERS["vessel_174k_from"].value) else SHIPS[0][0]


def hire_levels(anchors: tuple[Anchor, ...] = ANCHORS, *, when: date | str | None = None) -> dict[str, float]:
    """The low, central and high hire: the lowest, the median and the highest of the figures reported.

    With a day, the figures are those reported for the ship the engine prices
    that day with, so that a date with no reported figure of its own runs at
    three levels its own ship saw, never at one invented rate; without a day,
    every figure counts.
    """
    chosen = list(anchors) if when is None else [a for a in anchors if ship_on(anchor_day(a)) == ship_on(when)]
    if not chosen:
        raise ValueError("no reported charter rate for the ship of %s" % when)
    values = [a.hire_usd_day for a in chosen]
    return {"low": min(values), "central": float(statistics.median(values)), "high": max(values)}


def hire_levels_by_ship(anchors: tuple[Anchor, ...] = ANCHORS) -> dict[str, dict[str, Any]]:
    """The three levels for each ship, with the count of figures and the span they cover, keyed as the Model view keys the ships."""
    out: dict[str, dict[str, Any]] = {}
    for key, words in SHIPS:
        chosen = [a for a in anchors if ship_on(anchor_day(a)) == key]
        if not chosen:
            continue
        days = sorted(anchor_day(a) for a in chosen)
        out[key] = {**hire_levels(tuple(chosen)), "ship": words, "count": len(chosen),
                    "first": days[0].isoformat(), "last": days[-1].isoformat()}
    return out


def record() -> dict:
    """Check the committed seed against the rows here and write its manifest entry."""
    from .config import SOURCES

    registered = SOURCES["freight_anchors"]
    status, note = "ok", ""
    found = problems()
    try:
        committed = json.loads(seed_path().read_text(encoding="utf-8"))
        if committed != document():
            found.append("the committed seed differs from the rows in lngarb.freight_anchors")
    except (OSError, ValueError) as exc:
        found.append("the seed could not be read: %s" % exc)
    if found:
        status, note = "failed", "; ".join(found)
    else:
        by_ship = hire_levels_by_ship()
        note = (
            "%d reported charter rates from %s to %s, one per month at most, the first reported in the "
            "month, each from a dated article, never interpolated. Low, central and high hire for a date "
            "with no figure of its own, the lowest, the median and the highest of the figures reported for "
            "the ship the date is priced with: %s. A seed, not a time series."
            % (
                len(ANCHORS), ANCHORS[0].month, ANCHORS[-1].month,
                "; ".join("%s, %s, %s and %s $/day over %d figures" % (
                    v["ship"], format(v["low"], ",.0f"), format(v["central"], ",.0f"), format(v["high"], ",.0f"),
                    v["count"]) for v in by_ship.values()),
            )
        )
    entry = {
        "series": "freight_anchors",
        "source": registered.publisher,
        "url": None,
        "page_url": registered.page_url,
        "linkable": registered.linkable,
        "machine_fetched": False,
        "fetched_at": None,
        "checked_at": base.utc_now_iso(),
        "rows": len(ANCHORS),
        "observations": len(ANCHORS),
        "file_rows": len(ANCHORS),
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
        "file": "data/seed/freight_anchors.json",
        "unit": "USD per day",
        "observation_column": None,
        "unique_dates": True,
    }
    base.manifest_upsert(entry)
    return entry
