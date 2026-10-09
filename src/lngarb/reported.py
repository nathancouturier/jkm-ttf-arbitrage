"""Figures others reported, which the analysis sets its results against.

None of them is an input to the engine. Each is a count or an assessment read
in a dated, readable document, kept with its publisher, the document's address
and the day it was read, and quoted as a figure, never as a sentence: the
publishers' terms are in docs/sources.md, section 2.24.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Reported", "REPORTED", "reported"]


@dataclass(frozen=True)
class Reported:
    """One reported figure."""

    #: what it is about: "cancellations", "asia_use", "cape_use", "panama_use" or "arb_assessment"
    topic: str
    #: the period or day it refers to, yyyy-mm or yyyy-mm-dd; where the source
    #: states no period, the last day of its data, and the what says so
    period: str
    figure: float
    unit: str
    what: str
    publisher: str
    url: str
    read_on: str


_EIA_44697 = "https://www.eia.gov/todayinenergy/detail.php?id=44697"
_WPO_CAPE = "https://www.worldports.org/us-exports-record-number-of-lng-cargoes-to-asia-via-cape-of-good-hope-in-march/"
_HSN_CAPE = "https://www.hellenicshippingnews.com/updated-transit-levels-at-panama-canal-dont-faze-lng-shippers/"
_CSN_ARB = "https://cyprusshippingnews.com/2026/05/05/us-lng-arbitrage-to-asia-open-via-panama-canal-laden-flows-limited/"

REPORTED: tuple[Reported, ...] = (
    Reported("cancellations", "2020-06", 46.0, "cargoes",
             "cargoes cancelled in June 2020, about this many by EIA's estimate from the cargoes loaded and "
             "the capacity in operation",
             "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "2026-10-08"),
    Reported("cancellations", "2020-07", 50.0, "cargoes",
             "cargoes cancelled in July 2020, about this many by EIA's estimate from the cargoes loaded and "
             "the capacity in operation",
             "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "2026-10-08"),
    Reported("cancellations", "2020-08", 45.0, "cargoes",
             "cargoes cancelled for August 2020 shipments, according to trade press reports EIA cites",
             "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "2026-10-08"),
    Reported("cancellations", "2020-09", 30.0, "cargoes",
             "cargoes estimated cancelled for September 2020 shipments, according to trade press reports EIA cites",
             "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "2026-10-08"),
    Reported("cape_use", "2024-03", 27.0, "cargoes",
             "US LNG cargoes to Asia via the Cape of Good Hope in March 2024, a record, in S&P Global's data",
             "Platts, republished by Hellenic Shipping News, 22 April 2024", _HSN_CAPE, "2026-10-08"),
    Reported("panama_use", "2024-03", 14.0, "cargoes",
             "US LNG cargoes that reached Asia via the Panama Canal in 2024 to 27 March, one of them in March, "
             "against 40 in the same period of 2023",
             "Platts, republished by the World Ports Organization, 29 March 2024", _WPO_CAPE, "2026-10-08"),
    Reported("asia_use", "2026-04-28", 34.0, "cargoes",
             "LNG cargoes exported from US facilities to Asia-Pacific destinations; the period is not stated, the "
             "article's data run to 28 April 2026",
             "Platts, republished by Cyprus Shipping News, 5 May 2026", _CSN_ARB, "2026-10-08"),
    Reported("cape_use", "2026-04-28", 31.0, "cargoes",
             "of 34 LNG cargoes exported from US facilities to Asia-Pacific destinations, those routed round the "
             "Cape of Good Hope; the period is not stated, the article's data run to 28 April 2026",
             "Platts, republished by Cyprus Shipping News, 5 May 2026", _CSN_ARB, "2026-10-08"),
    Reported("arb_assessment", "2026-04-28", 0.533, "USD/MMBtu",
             "Platts' arbitrage of US to North Asia via the Panama Canal against US to the Atlantic",
             "Platts, republished by Cyprus Shipping News, 5 May 2026", _CSN_ARB, "2026-10-08"),
    Reported("arb_assessment", "2026-04-28", -0.677, "USD/MMBtu",
             "Platts' arbitrage of US to North Asia via the Cape of Good Hope against US to the Atlantic",
             "Platts, republished by Cyprus Shipping News, 5 May 2026", _CSN_ARB, "2026-10-08"),
)


def reported(topic: str) -> tuple[Reported, ...]:
    """The reported figures on one topic, in the order they are kept."""
    return tuple(r for r in REPORTED if r.topic == topic)
