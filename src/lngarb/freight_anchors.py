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

from .config import BOUNDS_HIRE_USD_DAY
from .sources import base

__all__ = ["Anchor", "ANCHORS", "seed_path", "problems", "write_seed", "record", "hire_levels"]

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
        "2022-02", "2022-02-08", None, -750.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", False,
        "Spark Commodities, note on negative freight rates", None,
        "The note is undated; it is named, not linked. The vessel is the one Spark's "
        "methodology of that time assesses; the note does not name it. Published "
        "rounded to the nearest 250 $/day.",
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
        "2023-07", None, "2023-07-28", 71_250.0, "Spark30S Atlantic", True,
        "160,000 m3 TFDE", True,
        "LNG Prime, quoting Spark",
        "https://lngprime.com/americas/spark-lng-freight-rates-remain-at-about-71000-per-day/87422/",
        "The day is not stated: the week ending 21 or 28 July 2023. The same article "
        "reports 12 days of Panama delay for unbooked vessels.",
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


def hire_levels(anchors: tuple[Anchor, ...] = ANCHORS) -> dict[str, float]:
    """The low, central and high hire from the reported figures: lowest, median, highest.

    Used where a date has no reported figure of its own, so that the result is
    shown at three levels rather than at one invented rate.
    """
    values = [a.hire_usd_day for a in anchors]
    return {"low": min(values), "central": float(statistics.median(values)), "high": max(values)}


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
        levels = hire_levels()
        note = (
            "%d reported charter rates from %s to %s, one per month at most, each from a "
            "dated article, never interpolated. Low, central and high hire for a date with "
            "no figure of its own: %s, %s and %s $/day, the lowest, the median and the "
            "highest. A seed, not a time series."
            % (
                len(ANCHORS), ANCHORS[0].month, ANCHORS[-1].month,
                format(levels["low"], ",.0f"), format(levels["central"], ",.0f"),
                format(levels["high"], ",.0f"),
            )
        )
    entry = {
        "series": "freight_anchors",
        "source": registered.publisher,
        "url": None,
        "page_url": registered.page_url,
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
