"""The inputs of a loading date, read from the committed data and the parameter table.

lngarb.cases does the arithmetic; this module says where each number comes
from on a given day: which price series and which week or month, which ship,
which routes are open, which tolls apply, which carbon price and phase, which
overnight rate, which reported hire. Every input carries a label naming its
source, and an input the data do not hold is reported missing rather than
filled.
"""

from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from . import canals, config, units
from .cases import EAST, WEST, Inputs, RouteInput
from .engine import Vessel
from .freight_anchors import ANCHORS, hire_levels
from .sea_routes import canal_distances, routes_json
from .sources.base import read_cache

__all__ = ["MissingInput", "vessel_on", "distances", "transit_days", "routes_on", "henry_hub_month",
           "usd_per_eur_on", "overnight_rate_on", "eua_eur_t_in", "ets_phase", "ets_tco2e_per_t", "nearest_hire",
           "wide_regas_discount_on", "WorkedDate", "WORKED_DATES", "inputs_for"]


class MissingInput(LookupError):
    """An input the committed data do not hold for the date asked."""


def _p(name: str) -> Any:
    return config.PARAMETERS[name].value


def _day(when: date | str) -> date:
    return when if isinstance(when, date) else date.fromisoformat(str(when)[:10])


# --------------------------------------------------------------------------
# The ship and the routes
# --------------------------------------------------------------------------

def vessel_on(when: date | str) -> Vessel:
    """The benchmark ship of the day: the 160,000 m3 TFDE, then from 2 January 2024 the 174,000 m3 two-stroke."""
    if _day(when) >= date.fromisoformat(_p("vessel_174k_from")):
        return Vessel("174,000 m3 two-stroke", _p("vessel_174k_capacity_m3"), _p("fill"),
                      _p("vessel_174k_boil_off_per_day"), _p("vessel_174k_speed_kn"),
                      _p("load_days"), _p("discharge_days"))
    return Vessel("160,000 m3 TFDE", _p("vessel_160k_capacity_m3"), _p("fill"),
                  _p("vessel_160k_boil_off_per_day"), _p("vessel_160k_speed_kn"),
                  _p("load_days"), _p("discharge_days"))


def distances() -> dict[str, float]:
    """Route id to its distance in nautical miles, from the committed routes seed."""
    document = json.loads(routes_json().read_text(encoding="utf-8"))
    return {route["id"]: float(route["distance_nm"]) for route in document["routes"]}


def transit_days(route_id: str, vessel: Vessel) -> tuple[float, float]:
    """Days from loading to the laden and to the ballast canal transit of a route through a canal.

    The laden transit comes after the load day and the sea distance to the
    canal; the ballast transit after the whole laden leg and the sea distance
    back from Futtsu to the canal. Both at the ship's speed, with no canal or
    waiting days.
    """
    to_canal = canal_distances()[route_id]
    total = distances()[route_id]
    per_day = vessel.speed_kn * 24.0
    laden = vessel.load_days + to_canal / per_day
    t_laden = vessel.load_days + total / per_day + vessel.discharge_days
    return laden, t_laden + (total - to_canal) / per_day


def _on(day: date, after_days: float) -> date:
    return day + timedelta(days=int(after_days))


def _panama(laden_day: date, ballast_day: date, capacity_m3: float) -> tuple[float, float, str]:
    """Laden and ballast Panama charges, each on its own transit day, through the canal both ways."""
    laden = canals.panama_toll(laden_day, capacity_m3, laden=True)
    ballast = canals.panama_toll(ballast_day, capacity_m3, laden=False, roundtrip_ballast=True)
    if laden is None or ballast is None:
        raise MissingInput("no Panama toll table covers %s or %s" % (laden_day, ballast_day))
    laden_all = laden + canals.panama_fresh_water_surcharge(laden_day, laden)
    ballast_all = ballast + canals.panama_fresh_water_surcharge(ballast_day, ballast)
    note = ("Panama toll, laden transit %s under %s, %s; ballast transit %s under %s, %s; each with "
            "the fresh water surcharge from 15 February 2020" % (
                laden_day, canals.panama_period(laden_day).source, format(laden, ",.0f"),
                ballast_day, canals.panama_period(ballast_day).source, format(ballast, ",.0f")))
    return laden_all, ballast_all, note


def routes_on(when: date | str, vessel: Vessel, *, suez_scnt: float | None = None,
              suez_rebate_on_surcharge: bool = False) -> dict[str, RouteInput]:
    """Every route for a cargo loading on the day: open or not and why, its distance and its canal charges.

    A canal is priced on each transit's own day. A route is offered only if
    its laden transit falls while the canal is open to a US cargo; the ballast
    leg is taken to return the same way. Suez is offered only where its toll
    can be priced: without a schedule or an SDR rate it is shown and flagged,
    never offered at a toll of zero.
    """
    day = _day(when)
    nm = distances()
    out = {WEST: RouteInput(nm[WEST])}

    laden_after, ballast_after = transit_days("nea_panama", vessel)
    laden_day, ballast_day = _on(day, laden_after), _on(day, ballast_after)
    if laden_day >= date.fromisoformat(_p("panama_open_to_lng_from")):
        laden, ballast, note = _panama(laden_day, ballast_day, vessel.capacity_m3)
        out["nea_panama"] = RouteInput(nm["nea_panama"], canal_laden_usd=laden, canal_ballast_usd=ballast,
                                       canal_note=note)
    else:
        out["nea_panama"] = RouteInput(nm["nea_panama"], open=False,
                                       why_closed="laden transit before the expanded locks opened to LNG carriers")

    laden_after, ballast_after = transit_days("nea_suez", vessel)
    laden_day, ballast_day = _on(day, laden_after), _on(day, ballast_after)
    closed_from = date.fromisoformat(_p("suez_closed_to_us_cargo_from"))
    why = "" if laden_day < closed_from else "laden transit %s: no US Gulf cargo through the Red Sea after 12 January 2024" % laden_day
    priced = canals.suez_transits(laden_day, ballast_day, vessel.capacity_m3, scnt=suez_scnt,
                                  rebate_on_surcharge=suez_rebate_on_surcharge)
    if priced is None:
        out["nea_suez"] = RouteInput(
            nm["nea_suez"], open=False,
            why_closed=why or "no Suez toll can be priced for the transits of %s and %s (no schedule or no SDR rate held)" % (
                laden_day, ballast_day),
            canal_note="no Suez toll priced: no schedule covers the transits or no SDR rate is held",
        )
    else:
        laden, ballast, note = priced
        out["nea_suez"] = RouteInput(nm["nea_suez"], open=not why, why_closed=why,
                                     canal_laden_usd=laden, canal_ballast_usd=ballast, canal_note=note)
    out["nea_cape"] = RouteInput(nm["nea_cape"])
    return out


# --------------------------------------------------------------------------
# Market data on a day
# --------------------------------------------------------------------------

def henry_hub_month(when: date | str) -> tuple[float, str]:
    """EIA's daily Henry Hub spot averaged over the loading month, the proxy for NYMEX's settlement.

    When the data end before the month's last weekday the average is of the
    days held, and the label says the month is incomplete.
    """
    day = _day(when)
    hh = read_cache("eia_henry_hub_daily")
    month = hh[(hh["date"].dt.year == day.year) & (hh["date"].dt.month == day.month)]["henry_hub_usd_mmbtu"].dropna()
    if month.empty:
        raise MissingInput("no Henry Hub spot price in %s" % day.strftime("%B %Y"))
    label = "EIA Henry Hub spot, average of %d days in %s" % (len(month), day.strftime("%B %Y"))
    last_weekday = max(d for d in range(1, calendar.monthrange(day.year, day.month)[1] + 1)
                       if date(day.year, day.month, d).weekday() < 5)
    last_held = hh.loc[hh["henry_hub_usd_mmbtu"].notna(), "date"].max().date()
    if last_held < date(day.year, day.month, last_weekday):
        label += ", an incomplete month: the data end on %s" % last_held
    return float(month.mean()), label


def _on_or_before(name: str, column: str, day: date) -> tuple[float, date]:
    frame = read_cache(name)
    rows = frame[(frame["date"] <= pd.Timestamp(day)) & frame[column].notna()]
    if rows.empty:
        raise MissingInput("no %s on or before %s" % (column, day))
    last = rows.iloc[-1]
    return float(last[column]), last["date"].date()


def usd_per_eur_on(when: date | str) -> tuple[float, str]:
    value, seen = _on_or_before("h10_usd_per_eur_daily", "usd_per_eur", _day(when))
    return value, "Federal Reserve Board H.10, noon buying rate of %s" % seen


def overnight_rate_on(when: date | str) -> tuple[float, str]:
    """SOFR from its first value date, the effective federal funds rate before it."""
    day = _day(when)
    if day >= date(2018, 4, 2):
        value, seen = _on_or_before("nyfed_sofr_daily", "sofr_percent", day)
        return value, "SOFR of %s, New York Fed" % seen
    value, seen = _on_or_before("nyfed_effr_daily", "effr_percent", day)
    return value, "effective federal funds rate of %s, New York Fed, before SOFR" % seen


def eua_eur_t_in(when: date | str) -> tuple[float, str]:
    """The month's average auction price of an EU allowance, from the Commission's reports.

    After the last month the reports cover, that month's price held, the
    labelled assumption of the parameter table; a month missing before it is
    missing.
    """
    day = _day(when)
    frame = read_cache("ec_eua_auction_monthly")
    rows = frame[(frame["date"].dt.year == day.year) & (frame["date"].dt.month == day.month)]
    if not rows.empty and not pd.isna(rows.iloc[0]["eua_eur_t"]):
        return float(rows.iloc[0]["eua_eur_t"]), "European Commission auction report, %s average" % day.strftime("%B %Y")
    held = frame[frame["eua_eur_t"].notna()].iloc[-1]
    if pd.Timestamp(day) > held["date"]:
        return float(held["eua_eur_t"]), (
            "assumption: the last published monthly auction price, %s, held; no published price "
            "for %s" % (held["date"].strftime("%B %Y"), day.strftime("%B %Y")))
    raise MissingInput("no EU allowance auction price for %s" % day.strftime("%B %Y"))


def ets_phase(when: date | str) -> float:
    """The share of a year's shipping emissions that must be surrendered."""
    year = _day(when).year
    phases = _p("ets_phase_in_by_year")
    eligible = [int(y) for y in phases if int(y) <= year]
    return float(phases[str(max(eligible))]) if eligible else 0.0


def ets_tco2e_per_t(when: date | str, slip: float | None = None) -> float:
    """Tonnes of CO2e the EU ETS counts per tonne of LNG burnt, in the year of the day.

    CO2 only before the methane and nitrous oxide of 2026. With methane slip on,
    the slipped share is not burnt: it leaves the CO2 and N2O terms and counts
    as methane at its global warming potential from 2026.
    """
    slipped = (slip or 0.0) if _p("methane_slip_on") or slip is not None else 0.0
    burnt = 1.0 - slipped
    factor = _p("tco2_per_t_lng") * burnt
    if _day(when) >= date.fromisoformat(_p("ets_ch4_n2o_from")):
        factor += slipped * _p("gwp_ch4") + burnt * _p("tn2o_per_t_lng") * _p("gwp_n2o")
    return factor


def _anchor_day(anchor) -> date:
    return date.fromisoformat(anchor.rate_date or anchor.article_date)


def nearest_hire(when: date | str, *, max_days: int | None = None) -> tuple[float | None, str]:
    """The reported charter rate nearest the day, within max_days, from the freight anchors.

    Each figure is dated by the day it refers to, or by its article when no day
    is stated. None when no figure lies within max_days.
    """
    day = _day(when)
    max_days = _p("hire_anchor_max_days") if max_days is None else max_days
    near = sorted((abs((_anchor_day(a) - day).days), _anchor_day(a), a) for a in ANCHORS)
    gap, dated, anchor = near[0]
    if gap > max_days:
        return None, "no reported charter rate within %d days of %s (the nearest is %d days away)" % (
            max_days, day, gap)
    when_said = anchor.rate_date or ("article of %s" % anchor.article_date)
    return anchor.hire_usd_day, "%s, %s, %s (%s), %d days from the date" % (
        anchor.assessment + ("" if anchor.assessment_stated else ", inferred"),
        anchor.vessel + ("" if anchor.vessel_stated else ", inferred"), when_said, anchor.publisher, gap)


def wide_regas_discount_on(when: date | str) -> bool:
    """Whether the day falls in the span when ACER saw the discount above 35 EUR/MWh on most days."""
    start, end = _p("delta_nwe_wide_window")
    return date.fromisoformat(start) <= _day(when) <= date.fromisoformat(end)


# --------------------------------------------------------------------------
# The worked dates
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkedDate:
    """A date worked through, with where its two prices come from."""

    label: str
    day: str
    #: "ngwu" (the Weekly Update's week ending day), "wngsr" (the Supplement's), or
    #: "monthly" (METI's contract-based price for JKM and the World Bank's TTF)
    prices: str


WORKED_DATES = (
    WorkedDate("April 2020", "2020-04-15", "monthly"),
    WorkedDate("October 2022", "2022-10-12", "ngwu"),
    WorkedDate("March 2024", "2024-03-27", "ngwu"),
    WorkedDate("the latest week", "2026-09-30", "wngsr"),
)


def _slip(vessel: Vessel) -> float:
    return _p("methane_slip_174k") if vessel.capacity_m3 >= _p("vessel_174k_capacity_m3") else _p("methane_slip_160k")


def _prices(worked: WorkedDate) -> tuple[float, float, dict[str, str]]:
    day = pd.Timestamp(worked.day)
    if worked.prices == "ngwu":
        frame = read_cache("eia_ngwu_international_weekly")
        row = frame[frame["date"] == day]
        if row.empty or pd.isna(row.iloc[0]["east_asia_usd_mmbtu"]):
            raise MissingInput("no Weekly Update item for the week ending %s" % worked.day)
        r = row.iloc[0]
        return float(r["east_asia_usd_mmbtu"]), float(r["ttf_usd_mmbtu"]), {
            "jkm": "EIA Natural Gas Weekly Update, East Asia, %s, week ending %s" % (r["east_asia_basis"], worked.day),
            "ttf": "EIA Natural Gas Weekly Update, TTF, %s, week ending %s" % (r["ttf_basis"], worked.day),
        }
    if worked.prices == "wngsr":
        frame = read_cache("eia_wngsr_international_weekly")
        row = frame[frame["date"] == day]
        if row.empty:
            raise MissingInput("no Supplement issue for the week ending %s" % worked.day)
        r = row.iloc[0]
        return float(r["jkm_usd_mmbtu"]), float(r["ttf_usd_mmbtu"]), {
            "jkm": "EIA WNGSR Supplement, JKM, week ending %s" % worked.day,
            "ttf": "EIA WNGSR Supplement, TTF, week ending %s" % worked.day,
        }
    month = day.replace(day=1)
    meti = read_cache("meti_spot_lng_monthly")
    wb = read_cache("worldbank_gas_monthly")
    jkm = meti.loc[meti["date"] == month, "contract_based_usd_mmbtu"]
    ttf = wb.loc[wb["date"] == month, "europe_gas_usd_mmbtu"]
    if jkm.empty or pd.isna(jkm.iloc[0]) or ttf.empty or pd.isna(ttf.iloc[0]):
        raise MissingInput("no monthly JKM proxy or TTF for %s" % month.strftime("%B %Y"))
    return float(jkm.iloc[0]), float(ttf.iloc[0]), {
        "jkm": "METI spot LNG, contract-based, %s, a proxy for JKM" % month.strftime("%B %Y"),
        "ttf": "World Bank Pink Sheet, Europe gas (TTF), %s" % month.strftime("%B %Y"),
    }


def inputs_for(worked: WorkedDate, *, hire_usd_day: float | None = None,
               delta_nwe_eur_mwh: float | None = None, liquefaction_fee: float | None = None,
               suez_scnt: float | None = None, suez_rebate_on_surcharge: bool = False) -> Inputs:
    """Every input of a worked date. The reported hire nearest the date unless one is given."""
    day = _day(worked.day)
    jkm, ttf, sources = _prices(worked)
    vessel = vessel_on(day)
    usd_per_eur, fx_source = usd_per_eur_on(day)
    hh, hh_source = henry_hub_month(day)
    rate, rate_source = overnight_rate_on(day)
    if hire_usd_day is None:
        hire_usd_day, hire_source = nearest_hire(day)
        if hire_usd_day is None:
            raise MissingInput(hire_source + "; give a hire, such as one of %s" % hire_levels())
    else:
        hire_source = "given"
    delta_eur = _p("delta_nwe_eur_mwh") if delta_nwe_eur_mwh is None else delta_nwe_eur_mwh
    # The voyage can run into the next calendar year: each year's emissions are
    # priced at that year's phase and gases (lngarb.cases).
    slip = _slip(vessel) if _p("methane_slip_on") else None
    ets_by_year = {year: (ets_phase(date(year, 1, 1)), ets_tco2e_per_t(date(year, 1, 1), slip))
                   for year in (day.year, day.year + 1)}
    eua_usd, eua_source = 0.0, "no EU ETS on shipping before 2024"
    if any(phase > 0 for phase, _ in ets_by_year.values()):
        eua_eur, eua_source = eua_eur_t_in(day)
        eua_usd = eua_eur * usd_per_eur
    sources = dict(sources)
    sources.update({
        "fx": fx_source, "henry_hub": hh_source, "rate": rate_source, "hire": hire_source,
        "eua": eua_source, "vessel": vessel.name,
        "delta_nwe": "%s EUR/MWh at %s USD per EUR" % (delta_eur, usd_per_eur),
    })
    return Inputs(
        day=day,
        vessel=vessel,
        mmbtu_per_m3=_p("mmbtu_per_m3_lng"),
        jkm=jkm,
        ttf=ttf,
        delta_nwe=units.eur_mwh_to_usd_mmbtu(delta_eur, usd_per_eur),
        hire_usd_day=hire_usd_day,
        henry_hub=hh,
        hh_multiple=_p("spa_henry_hub_multiple"),
        liquefaction_fee=_p("liquefaction_fee_usd_mmbtu") if liquefaction_fee is None else liquefaction_fee,
        routes=routes_on(day, vessel, suez_scnt=suez_scnt, suez_rebate_on_surcharge=suez_rebate_on_surcharge),
        port_west_usd=_p("port_cost_west_usd"),
        port_east_usd=_p("port_cost_east_usd"),
        rate_percent=rate,
        spread_bp=_p("funding_spread_bp"),
        eua_usd_t=eua_usd,
        ets_phase=ets_by_year[day.year][0],
        tco2_per_t_lng=ets_by_year[day.year][1],
        ets_by_year=ets_by_year,
        mmbtu_per_t_lng=_p("mmbtu_per_t_lng"),
        ets_voyage_share=_p("ets_voyage_share"),
        ets_berth_share=_p("ets_berth_share"),
        sources=sources,
    )
