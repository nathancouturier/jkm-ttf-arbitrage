"""Writes everything the site reads, from the committed data. Offline and repeatable.

    python -m arb.build

site/data/study.json    the latest cargo, the presets, the history, the flows and the parameter table
site/data/map.json      the land outline and the four route lines
tests/fixtures/engine_cases.json   cases the JavaScript engine must reproduce
"""

from __future__ import annotations

import json
import random
from datetime import date

import pandas as pd

from . import analysis, engine, params
from .inputs import Market

SITE = params.ROOT / "site" / "data"
FIXTURE = params.ROOT / "tests" / "fixtures" / "engine_cases.json"

PRESETS = [
    ("latest", "Latest week", None, "week"),
    ("2020-04", "April 2020", "2020-04-15", "month"),
    ("2022-10", "October 2022", "2022-10-12", "week"),
    ("2024-03", "March 2024", "2024-03-27", "week"),
    ("2026-03", "March 2026", "2026-03-25", "week"),
]
PRESET_NOTES = {
    "latest": "The latest week EIA has published.",
    "2020-04": "Demand collapses in the pandemic. Neither market covers the cost of the gas and US cargoes are cancelled.",
    "2022-10": "Europe is short of gas, TTF is far above JKM and freight is at a record.",
    "2024-03": "Panama is short of water and the Red Sea is shut: the only way east is round the Cape.",
    "2026-03": "The Strait of Hormuz is closed: Asia bids for spot cargoes and freight soars.",
}


# (series, file, date column, credit, address, how it is kept up to date, refresh source)
CREDITS = [
    ("JKM and TTF, weekly averages", "prices_weekly.csv", "week_ending",
     "U.S. Energy Information Administration, Natural Gas Weekly Update and WNGSR Supplement; EIA credits the prices to Bloomberg Finance L.P.",
     "https://www.eia.gov/naturalgas/weekly/supplement/", "weekly refresh", "eia_weekly"),
    ("Henry Hub spot, daily", "henry_hub_daily.csv", "date",
     "U.S. Energy Information Administration; EIA credits the price to Refinitiv, an LSEG business",
     "https://www.eia.gov/dnav/ng/hist/rngwhhdd.htm", "weekly refresh", "henry_hub"),
    ("DES LNG assessments, Northwest Europe", "des_nwe_acer_daily.csv", "date",
     "European Union Agency for the Cooperation of Energy Regulators (ACER)",
     "https://www.acer.europa.eu/gas/lng-price-assessment", "by hand, from ACER's download", None),
    ("Charter rates, Spark30S Atlantic", "charter_rates.csv", "date",
     "Spark Commodities, and Clarksons for one date in 2021, as reported by LNG Prime and by Reuters in gCaptain; each figure links to its article",
     "https://lngprime.com/tag/spark/", "weekly refresh when a headline states the rate, else by hand", "charter_rate"),
    ("US LNG exports, cargo by cargo", "us_lng_cargoes_doe.csv", "date",
     "U.S. Department of Energy, Office of Fossil Energy and Carbon Management",
     "https://www.energy.gov/hgeo/listings/natural-gas-imports-and-exports-monthly-reports", "weekly refresh", "doe_cargoes"),
    ("US dollars per euro, daily", "usd_per_eur_daily.csv", "date",
     "Board of Governors of the Federal Reserve System, H.10", "https://www.federalreserve.gov/releases/h10/", "weekly refresh", "usd_per_eur"),
    ("SOFR, daily", "sofr_daily.csv", "date",
     "Federal Reserve Bank of New York; subject to its Terms of Use, see the NOTICE file", "https://www.newyorkfed.org/markets/reference-rates/sofr", "weekly refresh", "sofr"),
    ("US dollars per SDR, daily", "usd_per_sdr_daily.csv", "date",
     "International Monetary Fund, through the Deutsche Bundesbank", "https://www.imf.org/external/np/fin/data/param_rms_mth.aspx", "weekly refresh", "usd_per_sdr"),
    ("EU allowance price, monthly", "eua_monthly.csv", "month",
     "European Commission auction reports, CC BY 4.0, to June 2025; then Source: EEX, DEHSt, CC BY-NC-ND 4.0, the monthly averages reproduced unchanged",
     "https://www.dehst.de/EN/Topics/EU-ETS-1/EU-ETS-1-Information/Analyses-and-Reports/analysis-and-reports_node.html", "by hand, monthly", None),
    ("Japan spot LNG price, monthly, to March 2021", "japan_spot_lng_meti.csv", "month",
     "Created by processing the information in the Spot LNG Price Statistics (Ministry of Economy, Trade and Industry of Japan)",
     "https://www.meti.go.jp/english/statistics/sho/slng/index.html", "closed series", None),
    ("TTF, monthly", "ttf_monthly_worldbank.csv", "month",
     "The World Bank: Commodity Price Data (The Pink Sheet): Bloomberg Finance L.P.; World Gas Intelligence; Thomson Reuters Datastream; The Wall Street Journal; Official Statistics of Japan; World Bank, CC BY 4.0. The World Bank does not endorse this study",
     "https://www.worldbank.org/en/research/commodity-markets", "release of 2 October 2026, used to September 2020", None),
    ("Panama Canal, monthly operations and LNG transits", "panama_canal_monthly.csv", "month",
     "Panama Canal Authority, advisories to shipping and annual reports", "https://pancanal.com/en/maritime-services/advisory-to-shipping/", "by hand", None),
]


def credits(status: dict) -> list[dict]:
    out = []
    for series, name, column, credit, url, kept, source in CREDITS:
        frame = pd.read_csv(params.DATA / name, dtype=str)
        entry = status.get(source, {}) if source else {}
        out.append({"series": series, "credit": credit, "url": url, "from": frame[column].min(), "to": frame[column].max(),
                    "kept": kept, "checked": entry.get("checked"), "ok": entry.get("ok"), "message": entry.get("message")})
    return out


def timing_split(weekly: list[dict]) -> dict:
    """Weeks whose two front months name the same delivery month, against the others.

    JKM's front month rolls on the 16th and TTF's two business days before the
    month ends, so a week that lies wholly within the 1st to the 15th compares
    the same delivery month. Counted from the weeks EIA prints as futures.
    """
    rows = [r for r in weekly if r["basis"] == "front-month futures"]
    same = [r for r in rows if 7 <= r["date"].day <= 15]
    other = [r for r in rows if not 7 <= r["date"].day <= 15]

    def stat(group):
        return {"weeks": len(group), "open": sum(1 for r in group if r["open"]),
                "mean_spread": sum(r["spread"] for r in group) / len(group),
                "mean_abs_spread": sum(abs(r["spread"]) for r in group) / len(group)}
    return {"same_month": stat(same), "different_months": stat(other)}


def rounded(value, digits: int = 5):
    if isinstance(value, float):
        return None if value != value else round(value, digits)   # a missing cell becomes null
    if isinstance(value, dict):
        return {k: rounded(v, digits) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(v, digits) for v in value]
    return value


def by_ship(market: Market, day: date, sdr: float) -> dict:
    """What changes when the calculator's ship changes: the ship, its tolls, its carbon factor, its hire scenarios."""
    out = {}
    for row in market.p["ships"]:
        ship = params.ship_by_id(row["id"])
        panama = params.panama_charges(day, ship["capacity_m3"])
        suez = params.suez_charges(day, ship["capacity_m3"], sdr)
        out[row["id"]] = {
            "name": row["name"],
            "ship": {k: ship[k] for k in ("capacity_m3", "fill", "mmbtu_per_m3", "boil_off", "speed_kn")},
            "tolls": {"panama": [panama["laden"], panama["ballast"]], "suez": [suez["laden"], suez["ballast"]]},
            "tco2e_per_t_lng": params.ets_on(day, row["id"])["tco2e_per_t_lng"],
            "scenarios": market.hire_scenarios(row["id"]),
        }
    return out


def preset(market: Market, key: str, label: str, obs: dict) -> dict:
    inputs, meta = market.cargo(obs["date"], obs["jkm"], obs["ttf"], obs["period"])
    ships = by_ship(market, obs["date"], meta["usd_per_sdr"]["value"])
    weekly_print = obs["period"] == "week" or obs["basis"].startswith("mean of")
    return {
        "id": key, "label": label, "note": PRESET_NOTES[key],
        "date": obs["date"], "period": obs["period"],
        "basis": obs["basis"], "ship_id": meta["ship"]["id"], "inputs": inputs,
        "usd_per_eur": meta["usd_per_eur"]["value"], "eua_eur_t": meta["eua_eur_t"]["value"],
        "ships": ships, "scenarios": ships[meta["ship"]["id"]]["scenarios"],
        "sources": {
            "prices": {"date": obs["date"], "status": "observed", "note": obs["basis"],
                       "publisher": "EIA" if weekly_print else "METI and the World Bank"},
            "hire": meta["hire"], "des_discount": meta["des_discount_eur_mwh"], "henry_hub": meta["henry_hub"],
            "usd_per_eur": meta["usd_per_eur"], "sofr": meta["sofr"], "eua": meta["eua_eur_t"], "usd_per_sdr": meta["usd_per_sdr"],
        },
        "route_status": {rid: {k: s[k] for k in ("status", "note", "source", "url")} for rid, s in meta["route_status"].items()},
        "panama": meta["panama"], "suez": {k: meta["suez"][k] for k in ("scnt", "surcharge", "rebate", "laden", "ballast")},
    }


def history_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({
            "date": r["date"], "jkm": r["jkm"], "ttf": r["ttf"], "spread": r["spread"], "basis": r["basis"],
            "hire": r["hire"], "hire_status": r["hire_status"], "des": r["des_discount"], "des_status": r["des_status"],
            "fx": r["usd_per_eur"], "ship": r["ship"],
            # [level at zero hire, rise per 100,000 USD a day of hire, status]
            "routes": {rid: [x["at_zero_hire"], x["per_usd_day"] * 1e5, x["status"]] for rid, x in r["routes"].items()},
            "route": r["route"], "breakeven": r["breakeven"], "open": r["open"],
            "netback_europe": r["netback_europe"], "lift_margin": r["lift_margin"],
        })
    return out


def parameter_table(p: dict) -> list[dict]:
    """The rows of the Method view's parameter table."""
    rows = []

    def add(group, name, value, source, url=None, status="published"):
        rows.append({"group": group, "name": name, "value": value, "source": source, "url": url, "status": status})

    for s in p["ships"]:
        add("Ship", s["name"], "%s m3, boil-off %.3f percent a day, from %s" % (format(s["capacity_m3"], ","), s["boil_off_per_day"] * 100, s["from"]), s["source"], s["url"])
    v = p["voyage"]
    add("Ship", "Fill", "98.5 percent of capacity", v["fill"]["source"])
    add("Ship", "Energy of the cargo", "23 MMBtu per m3 of LNG", p["units"]["mmbtu_per_m3_lng"]["source"])
    add("Ship", "Speed", "17 knots", v["speed_kn"]["source"])
    add("Ship", "Days in port", "1 to load, 1 to discharge", v["load_days"]["source"])
    add("Ship", "Days per canal transit", "1", v["canal_days_per_transit"]["source"], v["canal_days_per_transit"]["url"], "assumption")
    add("Ports", "Sabine Pass and Gate", "308,947 USD a round trip", p["ports"]["europe_usd"]["source"], None, "assumption")
    add("Ports", "Sabine Pass and Futtsu", "273,184 USD a round trip", p["ports"]["asia_usd"]["source"], None, "assumption")
    last = p["panama"]["tolls"][-1]
    add("Panama", "Toll, from %s" % last["from"], "300,000 USD a transit plus 2.05 USD per m3 of capacity; ballast at 85 percent", last["source"], last["url"])
    w = p["panama"]["fresh_water"]
    add("Panama", "Fresh water surcharge", "10,000 USD a transit plus 5 percent of the toll", w["source"], w["url"], "assumption")
    b = p["panama"]["booking_fee"][-1]
    add("Panama", "Booking fee, from %s" % b["from"], "100,000 USD a transit", b["source"], p["panama"]["booking_fee_url"])
    sz = p["suez"]
    add("Suez", "Dues, from %s" % sz["dues_sdr_per_scnt"][-1]["from"], "10.42 to 4.67 SDR per ton of Suez Canal net tonnage laden, by band; 19 percent LNG surcharge; 75 percent rebate for a US Gulf cargo to Asia",
        sz["dues_sdr_per_scnt"][-1]["source"] + "; " + sz["lng_surcharge"][-1]["source"] + "; " + sz["us_gulf_to_asia_rebate"][-1]["source"], sz["circulars_url"])
    add("Suez", "Net tonnage of the ship", "85,000 tons per 145,000 m3 of capacity", sz["scnt_per_m3"]["source"], sz["scnt_per_m3"]["url"], "assumption")
    e = p["ets"]
    add("EU ETS", "Share of emissions surrendered", "40 percent for 2024, 70 percent for 2025, all from 2026", e["source"], e["url"])
    add("EU ETS", "Emissions counted", "Half of the voyage into and out of the EU, all of the berth", e["source"], e["url"])
    add("EU ETS", "Tonnes of CO2 equivalent per tonne of LNG burnt", "2.75 to 2025; 3.21 from 2026 with methane slip of 1.7 percent and nitrous oxide", e["source"], "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2776")
    add("EU ETS", "Energy of a tonne of LNG", "51.56 MMBtu", p["units"]["mmbtu_per_tonne_lng"]["source"], p["units"]["mmbtu_per_tonne_lng"]["url"])
    c = p["contract"]
    add("Contract", "Price of the gas lifted", "115 percent of Henry Hub", c["henry_hub_multiple"]["source"], c["henry_hub_multiple"]["url"])
    add("Contract", "Henry Hub of the loading month", "The spot price on the day the month's NYMEX contract expired, three business days before the month, standing in for the final settlement the contracts name",
        "U.S. Energy Information Administration, Henry Hub spot price", "https://www.eia.gov/dnav/ng/hist/rngwhhdd.htm", "assumption")
    add("Contract", "Fixed liquefaction fee", "3.00 USD/MMBtu, owed whether or not the cargo is lifted (2.25 to 3.50 in published contracts)", c["liquefaction_fee_usd_mmbtu"]["source"], c["liquefaction_fee_usd_mmbtu"]["url"], "assumption")
    f = p["finance"]
    add("Financing", "Rate", "SOFR plus 150 basis points on 115 percent of Henry Hub, loading to discharge, actual over 360", f["spread"]["source"], None, "assumption")
    d = p["des_discount"]
    add("Europe", "DES discount, from 31 March 2023", "ACER's Northwest Europe DES assessment less TTF weighted as ACER weights the deals behind it (the ten weekdays before, decay 0.6), averaged over the last 20 days. It is what the market charges to regasify a cargo and enter the grid. ACER's own spread to one day's TTF is wider when TTF is rising",
        d["reference"]["source"], d["reference"]["url"], "assumption")
    add("Europe", "DES discount, 19 January to 30 March 2023", "Derived: ACER's Northwest Europe assessment for the week less the week's TTF. ACER published the assessment from January 2023 and its spread to TTF from 31 March",
        "ACER, LNG price assessment; U.S. Energy Information Administration, weekly TTF", "https://www.acer.europa.eu/gas/lng-price-assessment", "assumption")
    add("Europe", "DES discount, before", "1.2 EUR/MWh under TTF", d["before_acer_eur_mwh"]["source"], d["before_acer_eur_mwh"]["url"], "assumption")
    ramp, squeeze, easing, january = d["before_acer_periods"]
    add("Europe", "DES discount, February 2022 to January 2023", "Widening in a straight line from the invasion of Ukraine to 35 EUR/MWh in June 2022, 35 to mid October, then narrowing in a straight line to 6.5 for January 2023",
        squeeze["source"] + ". " + january["source"] + ". " + ramp["source"], squeeze["url"], "assumption")
    h = p["hire"]
    add("Charter rate", "Reported rate", "Spark30S Atlantic as LNG Prime and others report it, held until the next report for 26 weeks at most", h["max_hold_days"]["source"], None, "assumption")
    add("Charter rate", "Scenarios", "Quartiles of the monthly medians of the rates reported for the ship; zero for tonnage already on charter", h["unreported"]["source"], None, "assumption")
    for period in h["before_reports"]:
        add("Charter rate", "Before Spark's assessment, %s%s" % (period["from"][:4], "" if period["from"][:4] == period["to"][:4] else " to " + period["to"][:4]),
            "%s USD a day" % format(period["usd_per_day"], ","), period["source"], period["url"], "assumption")
    add("Units", "TTF in dollars", "EUR/MWh x USD per EUR / 3.412142", p["units"]["mmbtu_per_mwh"]["source"], p["units"]["mmbtu_per_mwh"]["url"])
    return rows


def land_rings() -> list[list[list[float]]]:
    """Natural Earth's land, decoded from the vendored TopoJSON into rings of longitude and latitude."""
    topo = json.loads((params.ROOT / "site" / "vendor" / "world-atlas" / "land-110m.json").read_text())
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            points.append([round(x * sx + tx, 2), round(y * sy + ty, 2)])
        arcs.append(points)
    rings = []
    for geometry in topo["objects"]["land"]["geometries"]:
        polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]
        for polygon in polygons:
            for ring in polygon:
                points = []
                for index in ring:
                    piece = arcs[index] if index >= 0 else arcs[~index][::-1]
                    points.extend(piece if not points else piece[1:])
                # a ring that crosses the antimeridian is made continuous, so it never draws a line across the map
                shift, previous = 0.0, points[0][0]
                for i, (lon, lat) in enumerate(points):
                    if lon + shift - previous > 180:
                        shift -= 360
                    elif lon + shift - previous < -180:
                        shift += 360
                    previous = lon + shift
                    points[i] = [round(previous, 2), lat]
                rings.append(points)
    return rings


def fixture_cases(presets: list[dict], seed: int = 20261113) -> list[dict]:
    """The presets and random variations of them, with the Python engine's answers."""
    rng = random.Random(seed)
    cases = []

    def add(name, inputs):
        cases.append({"name": name, "inputs": inputs, "expected": engine.price_cargo(inputs),
                      "canal_question": engine.canal_question(inputs)})

    for p in presets:
        add(p["id"], p["inputs"])
        for n in range(8):
            x = json.loads(json.dumps(p["inputs"]))
            x["jkm"] *= rng.uniform(0.5, 1.6)
            x["ttf"] *= rng.uniform(0.5, 1.6)
            x["des_discount"] = rng.uniform(-6.0, 1.0)
            x["henry_hub"] *= rng.uniform(0.5, 2.0)
            x["hire"] = rng.uniform(-5000.0, 400000.0)
            x["ship"]["speed_kn"] = rng.uniform(13.0, 19.5)
            x["ship"]["boil_off"] = rng.uniform(0.0005, 0.0015)
            x["carbon"]["phase_in"] = rng.choice([0.0, 0.4, 0.7, 1.0])
            for route in x["routes"].values():
                route["wait_days"] = rng.choice([0.0, 0.0, rng.uniform(0.0, 20.0)])
                route["open"] = rng.random() > 0.2 or route["market"] == "nwe"
            add("%s variation %d" % (p["id"], n + 1), x)
    return cases


def build(market: Market | None = None, write: bool = True) -> dict:
    """The study as one dictionary; written to the site's data folder unless told not to."""
    market = market or Market()
    p = market.p
    weekly = analysis.history(market, "week")
    monthly = analysis.history(market, "month")
    latest = market.weekly_observations()[-1]

    presets = []
    by_date = {str(o["date"]): o for o in market.weekly_observations()}
    by_month = {str(o["date"]): o for o in market.monthly_observations()}
    for key, label, day, period in PRESETS:
        obs = latest if day is None else (by_date if period == "week" else by_month)[day]
        presets.append(preset(market, key, label, obs))
    now = presets[0]
    result = engine.price_cargo(now["inputs"])

    flows = analysis.monthly_flows(market)
    test = analysis.flows_test(monthly, flows, p["flows"]["lag_months"])
    robustness = [analysis.flows_test(monthly, flows, lag) for lag in (0, 2)]
    since_2022 = analysis.flows_test([r for r in monthly if r["date"].year >= 2022], flows, p["flows"]["lag_months"])
    before_2022 = analysis.flows_test([r for r in monthly if r["date"].year < 2022], flows, p["flows"]["lag_months"])
    cancelled = p["cross_checks"]["cancellations_2020"]["cargoes"]
    lift = analysis.lift_history(monthly, flows, cancelled, market)

    flow_rows = []
    arb = {r["date"].strftime("%Y-%m"): r for r in monthly}
    for month, row in flows.iterrows():
        a = arb.get(month)
        flow_rows.append({"month": month, "share_jkm": row["share_jkm"], "share_europe": row["share_europe"],
                          "share_asia": row["share_asia"], "cargoes": int(row["cargoes"]), "mmcf": row["total"],
                          "margin": None if a is None else a["spread"] - a["breakeven"], "open": None if a is None else a["open"]})

    traffic = json.loads((params.DATA / "canal_lng_traffic.json").read_text())
    canal_ops = pd.read_csv(params.DATA / "panama_canal_monthly.csv")
    events = json.loads((params.DATA / "events.json").read_text())["events"]
    status_file = params.DATA / "status.json"
    status = json.loads(status_file.read_text()) if status_file.exists() else {}
    rates = market.rates.assign(date=market.rates["date"].dt.strftime("%Y-%m-%d"))

    platts_obs = by_date["2026-04-29"]
    platts_inputs, _ = market.cargo(platts_obs["date"], platts_obs["jkm"], platts_obs["ttf"])
    platts_model = engine.price_cargo(platts_inputs)["routes"]
    checks = {"platts": dict(p["cross_checks"]["platts_arbitrage_2026_04_28"], week=platts_obs["date"],
                             model_via_panama=platts_model["panama"]["arb"], model_via_cape=platts_model["cape"]["arb"],
                             hire=platts_inputs["hire"]),
              "spark": p["cross_checks"]["spark_example"]}

    no_discount = engine.price_cargo(engine.with_changes(now["inputs"], des_discount=0.0))["routes"]
    study = {
        "data_date": latest["date"],
        "now": {"preset": now, "result": result,
                "table": analysis.reroute_table(now["inputs"], now["scenarios"]),
                "without_discount": {rid: no_discount[rid]["breakeven_spread"] for rid in analysis.EAST},
                "canal": engine.canal_question(now["inputs"])},
        "presets": presets,
        "history": {"weekly": history_rows(weekly), "monthly": history_rows(monthly),
                    "summary": {"weekly": analysis.history_summary(weekly, market), "monthly": analysis.history_summary(monthly, market)}},
        "events": events,
        "charter_rates": rates[["date", "usd_per_day", "assessment", "ship", "publisher", "url"]].to_dict("records"),
        "flows": {"months": flow_rows, "test": {k: v for k, v in test.items() if k != "pairs"},
                  "robustness": [{k: v for k, v in t.items() if k != "pairs"} for t in robustness],
                  "since_2022": {k: v for k, v in since_2022.items() if k != "pairs"},
                  "before_2022": {k: v for k, v in before_2022.items() if k != "pairs"},
                  "rule": p["flows"]["rule"], "jkm_markets": p["flows"]["jkm_markets"],
                  "lift": lift, "cancellations_source": p["cross_checks"]["cancellations_2020"]},
        "routes": {"distances": {rid: params.routes()[rid]["distance_nm"] for rid in params.ROUTE_ORDER},
                   "traffic": traffic,
                   "panama_monthly": canal_ops[["month", "cwt_hours_avg", "cwt_hours_high", "transits_total", "neopanamax_transits"]].to_dict("records"),
                   "waits_reported": p["panama"]["waits_reported"],
                   "status_history": p["route_status"]},
        "parameters": parameter_table(p),
        "checks": checks,
        "timing": timing_split(weekly),
        "credits": credits(status),
    }
    study = rounded(analysis.iso(study), 6)
    # the presets' inputs keep full precision: the browser prices them with its own engine
    for i, pr in enumerate(presets):
        study["presets"][i]["inputs"] = pr["inputs"]
    study["now"]["preset"]["inputs"] = now["inputs"]

    if not write:
        return study
    route_lines = {rid: r["line"] for rid, r in params.routes().items()}
    ports = json.loads((params.DATA / "routes.json").read_text())["ports"]
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "study.json").write_text(json.dumps(study, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    (SITE / "map.json").write_text(json.dumps({"land": land_rings(), "routes": route_lines, "ports": ports},
                                              separators=(",", ":")) + "\n", encoding="utf-8")
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(analysis.iso(fixture_cases(presets)), separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    return study


if __name__ == "__main__":
    s = build()
    r = s["now"]["result"]
    print("data to %s: JKM minus TTF %.2f; reroute level %.2f via Panama, %.2f via the Cape at %s USD a day"
          % (s["data_date"], r["spread"], r["routes"]["panama"]["breakeven_spread"], r["routes"]["cape"]["breakeven_spread"],
             format(int(s["now"]["preset"]["inputs"]["hire"]), ",")))
