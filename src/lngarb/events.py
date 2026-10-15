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
_ACP = "https://pancanal.com/wp-content/uploads/"
_GCAPTAIN_DIVERT = "https://gcaptain.com/will-us-lng-exports-reroute-to-avoid-both-the-panama-and-suez-canals/"

EVENTS: tuple[Event, ...] = (
    Event("2016-07-25", "The first LNG carrier passes the expanded Panama Canal, from Sabine Pass.",
          "Panama Canal Authority, press release of 25 July 2016", _PANAMA_2016),
    Event("2020-06-01", "US cargoes cancelled: about 46 in June, 50 in July, 45 for August and 30 for September "
          "2020, by EIA's estimate and the trade press it cites.",
          "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "month"),
    Event("2023-07-30", "Panama cuts daily transits to an average of 32, 10 of them neopanamax, in the drought; "
          "queues of up to 21 days in August.",
          "Panama Canal Authority, advisory A-35-2023 of 25 July 2023; IEA, Global Gas Security Review 2024",
          _ACP + "2023/01/ADV35-2023-Additional-Measures-to-Mitigate-the-Extended-Dry-Season-and-Reduction-in-"
          "Precipitation-in-the-Canal-Watershed.pdf"),
    Event("2023-11-03", "Panama cuts booking slots to 25 a day, to fall to 22 in December and 18 in February 2024.",
          "Panama Canal Authority, advisory A-48-2023 of 30 October 2023",
          _ACP + "2023/01/ADV48-2023-Reduction-in-Transits-Due-to-the-Ongoing-Deficit-in-Precipitation-in-the-"
          "Canal-Watershed.pdf"),
    Event("2023-12-24", "US cargoes bound for Asia turn from Suez to the Cape: a Cove Point cargo loaded on 16 "
          "December diverts round Africa for Japan, a Freeport cargo for Korea does the same.",
          "Bloomberg, in gCaptain, 24 December 2023", _GCAPTAIN_DIVERT),
    Event("2024-01-13", "The last laden LNG carrier passes Suez; Qatari carriers turn south and no LNG carrier "
          "crosses the Red Sea from mid January.",
          "Oxford Institute for Energy Studies, NG-188, February 2024", _OIES),
    Event("2024-01-16", "Panama holds 24 booking slots a day, 7 of them neopanamax, with container ships ahead "
          "of LNG; LNG transits all but stop.",
          "Panama Canal Authority, advisory A-54-2023 of 15 December 2023, and A-08-2024; IEA",
          _ACP + "2023/01/ADV54-2023-Increase-in-the-Number-of-Booking-Slots-in-the-Panamax-and-Neopanamax-Locks-"
          "and-Other-Modifications-to-the-Transit-Reservation-System.pdf"),
    Event("2024-09-01", "Panama back to normal operating conditions, 36 booking slots a day, 10 of them "
          "neopanamax.",
          "Panama Canal Authority, advisory A-28-2024 of 15 August 2024",
          _ACP + "2024/08/ADV28-2024-Increase-in-the-Maximum-Allowable-Draft-in-the-Neopanamax-Locks-and-"
          "Modifications-to-the-Transit-Reservation-Booking-System.pdf"),
    Event("2026-07-03", "Panama's neopanamax draught cut in steps, 49.5 feet from 3 July 2026 to 48 feet from "
          "2 September, and neopanamax slots to 9 a day from 4 September.",
          "Panama Canal Authority, advisories A-18, A-22, A-25, A-29 and A-33-2026",
          _ACP + "2026/08/ADV-29-2026-Additional-Measures-to-Address-Reduced-Precipitation-in-the-Canal-Watershed.pdf"),
    Event("2026-09-28", "Panama's neopanamax draught back to 49 feet at once, and 10 neopanamax slots a day for "
          "bookings from 15 October, 4 of them a week for LNG.",
          "Panama Canal Authority, advisory A-36-2026 of 28 September 2026",
          _ACP + "2026/04/ADV-36-2026-Increase-in-the-Number-of-Neopanamax-Booking-Slots-Draft-Adjustment-and-"
          "Transit-Reservation-System.pdf"),
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
