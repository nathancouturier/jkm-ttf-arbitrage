"""Everything the study declares: its sources, its checks, and later its parameters.

This module holds three kinds of declaration.

    the source registry     one Source per series or seed file, with its
                            publisher, pages, frequency, method, licence and
                            whether its cache may be published
    the validation bounds   the ranges a value must sit in before it is allowed
                            into a cache
    the region map          every destination country in EIA's export table,
                            mapped to the region the flow analysis uses

The engine's parameters, each with a value, a unit, a status, a source URL and
the date it was read, are added to this module with the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

# ---------------------------------------------------------------------------
# Validation bounds, checked on every write. See docs/methodology.md.
# ---------------------------------------------------------------------------

#: JKM, TTF and Japanese spot LNG, USD/MMBtu
BOUNDS_LNG_USD_MMBTU = (1.0, 120.0)
#: Henry Hub, USD/MMBtu
BOUNDS_HENRY_HUB_USD_MMBTU = (0.5, 25.0)
#: US dollars per euro
BOUNDS_USD_PER_EUR = (0.8, 1.7)
#: reported LNG carrier hire, USD per day. Negative is possible: Spark's
#: Atlantic rate was assessed negative on 8 February 2022.
BOUNDS_HIRE_USD_DAY = (-10000.0, 500000.0)
#: ACER DES LNG spreads to the TTF front month, EUR/MWh
BOUNDS_DES_SPREAD_EUR_MWH = (-20.0, 5.0)

# ---------------------------------------------------------------------------
# The source registry
# ---------------------------------------------------------------------------

#: The frequencies this project handles. Gap detection needs to know which one a
#: series is, because a missing weekday in a weekly series is not a gap.
FREQUENCIES = ("daily", "weekly", "monthly", "annual")

#: How a series came to exist.
#:
#:     published      the source published exactly this series, machine readable
#:     parsed         extracted from a document the source published, a PDF
#:                    table or the text of a web page
#:     reconstructed  recovered from a published chart, with a measured error
#:     derived        computed by this project from other series or tools
#:     seed           committed by hand from a cited document, never fetched
METHODS = ("published", "parsed", "reconstructed", "derived", "seed")


@dataclass(frozen=True)
class Source:
    """One series this project builds, and everything provenance needs about it.

    machine_url is None when the URL cannot be hardcoded and has to be
    discovered; url_note then says what to look for, and the adapter must fail
    loudly when it cannot find it rather than guess.
    """

    #: cache file stem and the series name in the manifest
    series: str
    #: one sentence a human reads on the provenance panel
    label: str
    #: who published it
    publisher: str
    #: the human readable page, always present, always linkable
    page_url: str
    #: the machine readable file, or None when it has to be discovered
    machine_url: str | None
    #: what to do when machine_url is None, or what is odd about it
    url_note: str
    #: one of FREQUENCIES
    frequency: str
    #: the unit of the value columns
    unit: str
    #: one of METHODS
    method: str
    #: the licence, named
    licence: str
    #: what the licence permits and what it does not, in plain words
    licence_note: str
    #: whether the cache may be committed to a public repository. False sends
    #: the cache to data/private/ and keeps it out of the deploy.
    committable: bool

    def __post_init__(self) -> None:
        if self.frequency not in FREQUENCIES:
            raise ValueError(
                "source %r declares frequency %r, not one of %s"
                % (self.series, self.frequency, ", ".join(FREQUENCIES))
            )
        if self.method not in METHODS:
            raise ValueError(
                "source %r declares method %r, not one of %s"
                % (self.series, self.method, ", ".join(METHODS))
            )
        if not self.licence_note:
            raise ValueError(
                "source %r carries no licence_note. Every source states what its "
                "terms permit" % (self.series,)
            )
        if not self.committable and "not" not in self.licence_note.lower():
            raise ValueError(
                "source %r is not committable but its licence_note does not say "
                "what is forbidden" % (self.series,)
            )


def _registry(*sources: Source) -> Mapping[str, Source]:
    seen: dict[str, Source] = {}
    for item in sources:
        if item.series in seen:
            raise ValueError("two sources both claim the series name %r" % item.series)
        seen[item.series] = item
    return MappingProxyType(seen)


# Licence notes paraphrase what docs/sources.md quotes verbatim, with the URL
# each quotation was read from and the date.

_EIA_NOTE = (
    "US government publications are in the public domain. EIA's reuse page says "
    "'You may use and/or distribute any of our data, files, databases, reports, "
    "graphs, charts, and other information products', with an acknowledgment "
    "that includes the publication date."
)

_EIA_BLOOMBERG_NOTE = (
    _EIA_NOTE + " One doubt, recorded rather than resolved: these weekly prices "
    "are credited in the text to Bloomberg Finance L.P., and the same page says "
    "material 'contributed or licensed by private individuals, companies, or "
    "organizations' 'may be protected'. Whether figures EIA prints under a "
    "third party's credit fall under that sentence is not settled by the page. "
    "The parsed weekly values are committed with the credit shown wherever they "
    "are used, and the question is open with the owner and EIA."
)

_EIA_ROBOTS_NOTE = (
    "eia.gov's robots.txt disallows /naturalgas/weekly/archivenew_ngwu for every "
    "user agent, so no archived issue is fetched by code. Code reads the landing "
    "page, which still serves the final issue; every other issue is read from a "
    "copy saved by hand into data/private/ngwu/YYYY/MM_DD.html."
)


SOURCES: Mapping[str, Source] = _registry(
    # -- EIA, the weekly JKM and TTF averages -----------------------------
    Source(
        series="eia_ngwu_issue_index",
        label="Every Natural Gas Weekly Update issue EIA lists from 2016, the checklist for collection",
        publisher="U.S. Energy Information Administration",
        page_url="https://www.eia.gov/naturalgas/weekly/",
        machine_url="https://www.eia.gov/naturalgas/weekly/includes/archive.php",
        url_note=(
            "The index is one allowed page. Its links point into the disallowed "
            "archive and are recorded, never followed. Dates come from the folder "
            "in each link, never from the month and day cells, which are missing "
            "or wrong on several rows. Rows inside HTML comments are not read."
        ),
        frequency="weekly",
        unit="none, a list of issues",
        method="parsed",
        licence="US public domain",
        licence_note=_EIA_NOTE,
        committable=True,
    ),
    Source(
        series="eia_ngwu_international_weekly",
        label="Weekly averages of an East Asia LNG price and of TTF, USD/MMBtu, Natural Gas Weekly Update, to January 2026",
        publisher="U.S. Energy Information Administration, figures credited to Bloomberg Finance L.P.",
        page_url="https://www.eia.gov/naturalgas/weekly/",
        machine_url="https://www.eia.gov/naturalgas/weekly/",
        url_note=_EIA_ROBOTS_NOTE + (
            " The NGWU ended with the issue released on 22 January 2026, week "
            "ending 21 January 2026."
        ),
        frequency="weekly",
        unit="USD per MMBtu",
        method="parsed",
        licence="US public domain, with the third party credit doubt",
        licence_note=_EIA_BLOOMBERG_NOTE,
        committable=True,
    ),
    Source(
        series="eia_wngsr_international_weekly",
        label="Weekly averages of JKM and TTF, USD/MMBtu, WNGSR Supplement, from January 2026",
        publisher="U.S. Energy Information Administration, figures credited to Bloomberg Finance L.P.",
        page_url="https://www.eia.gov/naturalgas/weekly/supplement/",
        machine_url="https://www.eia.gov/naturalgas/weekly/supplement/content/bullets_lng_2.html",
        url_note=(
            "The page is an application shell; the current issue is assembled "
            "from content/bullets_lng_2.html, content/source_lng_2.html and "
            "content/release_dates.json, whose names come from the page's script "
            "and can change with any redeploy. Only the current issue is on an "
            "allowed path: robots.txt disallows /*archive/, which covers every "
            "past issue, so a week not collected while it is current can only "
            "be recovered by hand."
        ),
        frequency="weekly",
        unit="USD per MMBtu",
        method="parsed",
        licence="US public domain, with the third party credit doubt",
        licence_note=_EIA_BLOOMBERG_NOTE,
        committable=True,
    ),
)


def source(series: str) -> Source:
    """The registered Source for a series name, or KeyError naming it."""
    try:
        return SOURCES[series]
    except KeyError:
        raise KeyError("no source registered for series %r" % (series,)) from None
