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


_EIA = "https://www.eia.gov/todayinenergy/detail.php?id="
_EIA_44697 = _EIA + "44697"
_PANAMA_2016 = ("https://pancanal.com/en/first-ever-lng-vessel-transits-the-expanded-panama-canal-ushering-in-new-era-"
                "for-the-segment-and-global-lng-trade/")
_GCAPTAIN = "https://gcaptain.com/"
_LNGPRIME = "https://lngprime.com/"
_OIES = "https://www.oxfordenergy.org/wpcms/wp-content/uploads/2024/02/NG-188-LNG-Shipping-Chokepoints.pdf"
_ACP = "https://pancanal.com/wp-content/uploads/"
_GCAPTAIN_DIVERT = "https://gcaptain.com/will-us-lng-exports-reroute-to-avoid-both-the-panama-and-suez-canals/"

EVENTS: tuple[Event, ...] = (
    Event("2016-07-25", "The first LNG carrier passes the expanded Panama Canal, the Maran Gas Apollonia from "
          "Sabine Pass.",
          "Panama Canal Authority, press release of 25 July 2016", _PANAMA_2016),
    Event("2019-04-30", "Panama's neopanamax draught cut to 44 feet in the drought of 2019, from 49 in February; "
          "a further step to 43 feet was announced, postponed and suspended.",
          "Panama Canal Authority, advisories A-10-2019 of 1 April 2019, A-13, A-24 and A-26-2019",
          _ACP + "2019/04/a-10-2019.pdf"),
    Event("2020-06-01", "US cargoes cancelled: about 46 in June, 50 in July, 45 for August and 30 for September "
          "2020, by EIA's estimate and the trade press it cites.",
          "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "month"),
    Event("2021-01-12", "JKM assessed at 32.494 $/MMBtu, the highest since Platts began assessing it in 2009, in "
          "the cold snap of January 2021; a cargo trades at 39.30.",
          "Bloomberg, in gCaptain, 12 January 2021", _GCAPTAIN + "asian-lng-breaks-30-barrier-as-cold-makes-traders-scramble/"),
    Event("2021-12-21", "Dutch front month gas rises more than 16 percent in a day to a record 171.40 EUR/MWh as "
          "flows on the Yamal pipeline reverse eastward.",
          "Reuters, in gCaptain, 21 December 2021", _GCAPTAIN + "european-gas-prices-hit-record-as-russian-pipeline-flows-reverse/"),
    Event("2022-06-08", "Fire at Freeport LNG shuts the plant, 2 billion cubic feet a day and 17 percent of US "
          "export capacity; Henry Hub falls 1.27 $/MMBtu the next day.",
          "U.S. Energy Information Administration, Today in Energy, 23 June 2022", _EIA + "52859"),
    Event("2022-07-11", "Nord Stream 1 stops for ten days of maintenance, 11 to 21 July 2022, with no assurance "
          "of its return.",
          "Reuters, in gCaptain, 11 July 2022", _GCAPTAIN + "post-maintenance-shutdown-nord-stream-gas-flow-to-germany-is-unknown/"),
    Event("2022-08-31", "Gazprom halts Nord Stream 1 for three days from 31 August; the week's TTF average of 83.62 "
          "$/MMBtu is the highest of the weekly series.",
          "Reuters, in gCaptain, 21 August 2022; this study's weekly series",
          _GCAPTAIN + "nord-stream-1-pipeline-to-shut-for-three-days-in-latest-fuel-blow-to-europe/"),
    Event("2023-02-21", "Freeport LNG cleared to restart its remaining trains, eight months after the fire; its "
          "first cargo since loads in February 2023.",
          "LNG Prime, 9 March 2023", _LNGPRIME + "americas/freeport-lng-gets-ok-to-restart-remaining-train/75730/"),
    Event("2023-09-08", "Workers at Chevron's Gorgon and Wheatstone plants, over 5 percent of world supply, start "
          "industrial action; suspended on 22 September.",
          "LNG Prime, 8 and 22 September 2023",
          _LNGPRIME + "australia-and-oceania/chevron-gorgon-and-wheatstone-lng-workers-to-start-strike-after-talks-fail/91224/"),
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
    Event("2024-12-26", "Plaquemines LNG loads its first cargo, the eighth US export terminal; Corpus Christi "
          "Stage 3 follows in February 2025.",
          "U.S. Energy Information Administration, Today in Energy, 13 January 2025", _EIA + "64224"),
    Event("2025-02-10", "China's tariff of 15 percent on US LNG and coal takes effect, in reply to the US "
          "tariffs of 4 February; China's imports of US LNG fall to zero by March.",
          "Reuters, in gCaptain, 4 February 2025; Bloomberg, in gCaptain, 21 April 2025",
          _GCAPTAIN + "china-launches-limited-tariffs-after-trump-imposes-sweeping-new-levies/"),
    Event("2025-04-10", "China's tariff on all US goods raised to 84 percent, then 125 on 11 April, on top of "
          "the 15 on LNG.",
          "Bloomberg and Reuters, in gCaptain, 9 and 11 April 2025",
          _GCAPTAIN + "china-raises-tariffs-on-us-goods-to-84-as-trade-rift-worsens/"),
    Event("2025-05-14", "The Geneva step: China's 125 percent falls to 10 for ninety days; the 15 percent on "
          "US LNG stays, and the trade stays halted.",
          "Bloomberg, in gCaptain, 12 May 2025", _GCAPTAIN + "us-china-to-slash-tariffs-during-90-day-reprieve-for-talks/"),
    Event("2025-11-11", "The Houthis announce a suspension of their maritime operations; container lines test "
          "the Red Sea again from February 2026.",
          "gCaptain, 11 November 2025", _GCAPTAIN + "houthis-declare-suspension-of-red-sea-attacks-but-maritime-threat-remains/"),
    Event("2026-02-28", "US and Israeli strikes on Iran; Iran declares the Strait of Hormuz closed to all ships and "
          "Qatari gas tankers pause.",
          "Reuters and Bloomberg, in gCaptain, 28 February 2026", _GCAPTAIN + "hormuz-strait-tankers-avoid-iran-ban-us-strikes/"),
    Event("2026-03-04", "QatarEnergy declares force majeure on its LNG exports, two days after halting production "
          "at Ras Laffan; gas prices and freight at multi year highs.",
          "Reuters, in gCaptain, 4 March 2026", _GCAPTAIN + "qatar-lng-force-majeure-iran-war-gas-exports/"),
    Event("2026-03-18", "An Iranian missile strike damages Ras Laffan: two of Qatar's fourteen trains, 17 percent "
          "of its capacity, out for three to five years.",
          "Bloomberg and Reuters, in gCaptain, 18 and 19 March 2026",
          _GCAPTAIN + "iran-attack-wipes-out-17-of-qatars-lng-capacity-for-up-to-five-years/"),
    Event("2026-04-22", "Golden Pass LNG loads its first cargo, the ninth US export terminal.",
          "U.S. Energy Information Administration, Today in Energy, 23 April 2026", _EIA + "67564"),
    Event("2026-05-10", "The first Qatari LNG cargo since the war crosses Hormuz by the northern route Iran "
          "allows, sold to Pakistan.",
          "Bloomberg and Reuters, in gCaptain, 10 and 11 May 2026",
          _GCAPTAIN + "first-qatar-lng-shipment-moves-through-hormuz-since-war-started/"),
    Event("2026-06-01", "An interim agreement between the US and Iran ends four months of hostilities and "
          "provides for a return to the maritime traffic of before the war.",
          "Reuters, in gCaptain, 16 June and 5 July 2026", _GCAPTAIN + "iran-and-qatar-resume-maritime-trade/", "month"),
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
