"""Dated events the History view marks on its charts, each with its source.

None of them is an input to the engine or a break in the data: the breaks,
which change a price's definition, a route, the ship or the EU ETS, are found
by lngarb.analysis and drawn as numbered rules. An event is a thing that
happened to the trade, drawn as a lettered rule so a reader can set the
spread and the breakeven against it, and listed with its source under the
charts. Each is one sentence, dated to the day it took effect or, where a
source gives only a month, to the first of that month, and says so.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Event", "EVENTS", "lettered"]


@dataclass(frozen=True)
class Event:
    """One dated event."""

    #: the day it took effect, yyyy-mm-dd
    day: str
    #: what happened, one sentence a reader needs
    what: str
    #: who reported it, and in what
    source: str
    #: the document's address, or None where the source is named and not linked
    url: str | None
    #: "day" when the source dates it to the day, "month" when to the month
    dated_to: str = "day"


_EIA_44697 = "https://www.eia.gov/todayinenergy/detail.php?id=44697"
_PANAMA_2016 = "https://pancanal.com/en/inaugural-transit-of-the-expanded-panama-canal-begins/"
_OIES = "https://www.oxfordenergy.org/wpcms/wp-content/uploads/2024/02/NG-188-LNG-Shipping-Chokepoints.pdf"

EVENTS: tuple[Event, ...] = (
    Event("2016-07-25", "The first LNG carrier passes the expanded Panama Canal, from Sabine Pass.",
          "Panama Canal Authority, press release of 25 July 2016", _PANAMA_2016),
    Event("2020-06-01", "US cargoes cancelled: about 46 in June, 50 in July, 45 for August and 30 for September "
          "2020, by EIA's estimate and the trade press it cites.",
          "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "month"),
    Event("2023-07-30", "Panama cuts daily transits to an average of 32, 10 of them neopanamax, in the drought; "
          "queues of up to 21 days in August.",
          "Panama Canal Authority, advisory A-35-2023; IEA, Global Gas Security Review 2024", None),
    Event("2024-01-13", "The last laden LNG carrier passes Suez; Qatari carriers turn south and no LNG carrier "
          "crosses the Red Sea from mid January.",
          "Oxford Institute for Energy Studies, NG-188, February 2024", _OIES),
    Event("2024-01-16", "Panama holds 24 booking slots a day, 7 of them neopanamax, with container ships ahead "
          "of LNG; LNG transits all but stop.",
          "Panama Canal Authority, advisories A-54-2023 and A-08-2024; IEA", None),
    Event("2024-09-01", "Panama back to normal operating conditions, 36 booking slots a day, 10 of them "
          "neopanamax.",
          "Panama Canal Authority, advisory A-28-2024", None),
    Event("2026-07-03", "Panama's neopanamax draught cut in steps, 49.5 feet from 3 July 2026 to 48 feet from "
          "2 September.",
          "Panama Canal Authority, advisories A-18, A-22, A-25, A-29 and A-33-2026", None),
)


def lettered() -> list[dict]:
    """The events in order of day, each with its letter, A onwards."""
    ordered = sorted(EVENTS, key=lambda e: e.day)
    out = []
    for index, event in enumerate(ordered):
        letter = ""
        n = index
        while True:
            letter = chr(ord("A") + n % 26) + letter
            n = n // 26 - 1
            if n < 0:
                break
        out.append({"letter": letter, "day": event.day, "what": event.what, "source": event.source,
                    "url": event.url, "dated_to": event.dated_to})
    return out
