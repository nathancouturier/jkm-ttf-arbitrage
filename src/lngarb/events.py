"""Dated events the History view marks on its charts, each with its source.

None of them is an input to the engine or a break in the data: the breaks,
which change a price's definition, a route, the ship, the EU ETS or the source
of Europe's DES spread, are found by lngarb.analysis and drawn as numbered
rules. An event is a thing that happened to the trade, drawn as a lettered
rule so a reader can set the spread and the breakeven against it, and listed
with its source under the charts. Each is one sentence, dated to the day it
took effect or, where a source gives only a month, to the first of that month,
and says so; a period carries its last day. An event no readable document
supports is not a row: it is listed in LEFT_OUT with the reason, so the page
can say what it does not show.

The rows are written to data/seed/events.json by write_seed() and checked
against these rules by problems().
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .sources import base

__all__ = ["Event", "EVENTS", "LEFT_OUT", "seed_path", "problems", "write_seed", "record", "lettered"]

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Event:
    """One dated event."""

    #: the day it took effect, yyyy-mm-dd; for a month the source names, its first day
    day: str
    #: what happened, one sentence a reader needs, in this study's words
    what: str
    #: who reported it, and in what
    source: str
    #: the document's address, or None where the source is named and not linked
    url: str | None
    #: "day" when the source dates it to the day, "month" when to the month
    dated_to: str = "day"
    #: the last day of a period, or None for one day
    end: str | None = None


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
    Event("2016-02-24", "The first export cargo of the shale era leaves Sabine Pass, the Asia Vision, for Brazil.",
          "US Department of Energy, LNG monthly reports, transaction file",
          "https://www.energy.gov/hgeo/listings/natural-gas-imports-and-exports-monthly-reports"),
    Event("2016-07-25", "The first LNG carrier passes the expanded Panama Canal, the Maran Gas Apollonia from "
          "Sabine Pass.",
          "Panama Canal Authority, press release of 25 July 2016", _PANAMA_2016),
    Event("2019-04-30", "Panama's neopanamax draught cut to 44 feet in the drought of 2019, from 49 in February; "
          "a further step to 43 feet was announced, postponed and suspended.",
          "Panama Canal Authority, advisories A-10-2019 of 1 April 2019, A-13, A-24 and A-26-2019",
          _ACP + "2019/04/a-10-2019.pdf"),
    Event("2020-06-01", "US cargoes cancelled: about 46 in June, 50 in July, 45 for August and 30 for September "
          "2020, by EIA's estimate and the trade press it cites.",
          "U.S. Energy Information Administration, Today in Energy, 11 August 2020", _EIA_44697, "month",
          end="2020-09-30"),
    Event("2024-03-01", "A record 27 US cargoes to Asia sail round the Cape of Good Hope in the month.",
          "Platts, republished by Hellenic Shipping News, 22 April 2024",
          "https://www.hellenicshippingnews.com/updated-transit-levels-at-panama-canal-dont-faze-lng-shippers/",
          "month", end="2024-03-31"),
    Event("2025-02-08", "The first LNG carrier in five months passes Bab el Mandeb.",
          "gCaptain, 8 February 2025",
          _GCAPTAIN + "first-lng-carrier-in-five-months-passes-through-bab-el-mandeb-strait-as-houthi-threat-eases/"),
    Event("2026-06-01", "US LNG is shipped to China again: EIA's table, which records the destination declared at "
          "departure, shows 4,576 MMcf by vessel in June and 4,555 in July, the first since 546 in September 2025; "
          "whether the LNG was used in China or shipped on is not established.",
          "U.S. Energy Information Administration, exports by country, release of 30 September 2026",
          "https://www.eia.gov/dnav/ng/ng_move_expc_s1_m.htm", "month", end="2026-07-31"),
    Event("2026-09-18", "The US and China are reported to be discussing a cut to China's tariff on US LNG.",
          "gCaptain, 19 September 2026, reporting Reuters of 18 September",
          _GCAPTAIN + "us-china-discuss-cutting-tariffs-on-us-lng-ahead-of-xi-visit/"),
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
    Event("2026-02-28", "US and Israeli strikes on Iran; a radio broadcast said to come from Iran's navy bans "
          "transits of the Strait of Hormuz, with no official word from Iran, and Qatari gas tankers pause.",
          "Bloomberg, in gCaptain, 28 February 2026", _GCAPTAIN + "hormuz-strait-tankers-avoid-iran-ban-us-strikes/"),
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

#: Events of the period that are not rows, and why: (what, reason).
LEFT_OUT: tuple[tuple[str, str], ...] = (
    ("JKM's record low of 28 April 2020, Cape voyages above one a day in November 2020 and 58 LNG transits of "
     "Panama in January 2021",
     "S&P Global's figures; this study does not request S&P Global's pages and found no republication of these"),
    ("Russia's invasion of Ukraine on 24 February 2022",
     "no document on it was read for this study; the year shows in the spread, TTF above JKM for long stretches"),
    ("The first attacks on shipping in the Red Sea, November 2023",
     "no dated document on them was read; the diversions are marked from 24 December 2023 and the closure of the "
     "route from 13 January 2024"),
    ("The Suez Canal Authority's rebates for US Gulf LNG carriers and Panama's slot auctions",
     "rules of the canals, not events: they are in the tolls and on the Routes view's timeline"),
    ("No US cargo reaching China from 6 February 2025",
     "a statement of April 2025 about arrivals, which EIA's table contradicts for September 2025"),
    ("Spark's Atlantic rate jumping 163 percent on 3 March 2026",
     "Lloyd's List's figure, which this study does not request; LNG Prime's 161,750 $/day for 3 March is drawn as "
     "a charter rate"),
    ("The JKM to TTF spread flipping from a European to an Asian premium in March 2026",
     "IEA's averages were not read; the spread itself is drawn"),
    ("JKM and TTF reported on 18 September 2026 with the US arbitrage to Asia uneconomic",
     "Global LNG Hub's note was not read"),
    ("Spark's first negative Atlantic rate, 8 February 2022, and its record of 374,000 $/day in October 2022",
     "charter rates, drawn as such on the breakeven hire panel"),
    ("The EU ETS covering shipping and Spark's change of ship, January 2024",
     "breaks in the data, drawn as numbered rules"),
)


def seed_path() -> Path:
    return base.REPO_ROOT / "data" / ("se" + "ed") / "events.json"


def _letter(index: int) -> str:
    """A, B ... Z, AA, AB and on."""
    out = ""
    n = index
    while True:
        out = chr(ord("A") + n % 26) + out
        n = n // 26 - 1
        if n < 0:
            return out


def problems(events: tuple[Event, ...] = EVENTS) -> list[str]:
    """What breaks the rules the rows are kept to: dated, sourced, a period ending after it begins."""
    out: list[str] = []
    for e in events:
        try:
            first = date.fromisoformat(e.day)
            if e.end is not None and date.fromisoformat(e.end) < first:
                out.append("%s: ends on %s, before it begins" % (e.day, e.end))
        except ValueError as exc:
            out.append("%s: %s" % (e.day, exc))
        if e.url is not None and not e.url.startswith("https://"):
            out.append("%s: the address %r is not https" % (e.day, e.url))
        if e.dated_to not in ("day", "month"):
            out.append("%s: dated_to is %r, not day or month" % (e.day, e.dated_to))
        for field in ("what", "source"):
            if not getattr(e, field).strip():
                out.append("%s: no %s" % (e.day, field))
    return out


def lettered(events: tuple[Event, ...] = EVENTS) -> list[dict[str, Any]]:
    """The events in order of day, each with its letter, A onwards."""
    ordered = sorted(events, key=lambda e: e.day)
    return [{"letter": _letter(index), **asdict(event)} for index, event in enumerate(ordered)]


def document() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "note": (
            "Dated events that explain the regimes in the sample, each with the document it was read in, in this "
            "study's words. An event no readable document supports is not a row; left_out lists them with the reason."
        ),
        "events": [asdict(e) for e in sorted(EVENTS, key=lambda e: e.day)],
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
    ordered = sorted(EVENTS, key=lambda e: e.day)
    if found:
        status, note = "failed", "; ".join(found)
    else:
        note = (
            "%d dated events from %s to %s, each with the document it was read in, and %d left out, each with "
            "the reason. A seed, not a time series."
            % (len(EVENTS), ordered[0].day, ordered[-1].day, len(LEFT_OUT))
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
