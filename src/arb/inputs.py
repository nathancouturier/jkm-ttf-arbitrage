"""Market data and parameters for one loading day, as the model's inputs.

Every input always has a value. Where a series holds nothing for the day, a
documented default takes its place and the input is marked: 'held' (the last
published value), 'derived' (computed from two published series) or 'assumed'
(a stated assumption from data/params.json).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import engine, params

DATA = params.DATA


def _read(name: str, dates: list[str]) -> pd.DataFrame:
    return pd.read_csv(DATA / name, parse_dates=dates)


def _last_on_or_before(frame: pd.DataFrame, day: pd.Timestamp, column: str):
    """(value, its date) of the last row on or before the day, or of the first row."""
    rows = frame[frame["date"] <= day]
    row = rows.iloc[-1] if len(rows) else frame.iloc[0]
    return float(row[column]), row["date"].date()


class Market:
    """The committed data files, loaded once."""

    def __init__(self):
        self.weekly = _read("prices_weekly.csv", ["week_ending", "released"]).rename(
            columns={"week_ending": "date", "jkm_usd_mmbtu": "jkm", "ttf_usd_mmbtu": "ttf"})
        self.hh = _read("henry_hub_daily.csv", ["date"])
        self.fx = _read("usd_per_eur_daily.csv", ["date"])
        self.sofr = _read("sofr_daily.csv", ["date"])
        self.sdr = _read("usd_per_sdr_daily.csv", ["date"])
        self.acer = _read("des_nwe_acer_daily.csv", ["date"])
        self.rates = _read("charter_rates.csv", ["date"])
        self.eua = pd.read_csv(DATA / "eua_monthly.csv")
        self.meti = pd.read_csv(DATA / "japan_spot_lng_meti.csv")
        self.wb = pd.read_csv(DATA / "ttf_monthly_worldbank.csv")
        self.p = params.load()

    # -- observations ---------------------------------------------------------

    def weekly_observations(self) -> list[dict]:
        return [{"date": r.date.date(), "jkm": float(r.jkm), "ttf": float(r.ttf), "basis": r.basis, "period": "week"}
                for r in self.weekly.itertuples()]

    def monthly_observations(self) -> list[dict]:
        """One cargo a month from January 2016, loading on the 15th.

        To September 2020 JKM is METI's contract-based price for spot cargoes
        to Japan, a proxy, and TTF the World Bank's monthly average. From
        October 2020 both are the mean of the month's weekly averages, where
        the month holds at least two.
        """
        weekly = self.weekly.assign(month=self.weekly["date"].dt.strftime("%Y-%m"))
        means = weekly.groupby("month").agg(jkm=("jkm", "mean"), ttf=("ttf", "mean"), weeks=("jkm", "size"))
        meti = self.meti.set_index("month")["contract_based_usd_mmbtu"].dropna()
        wb = self.wb.set_index("month")["ttf_usd_mmbtu"].dropna()
        out = []
        for month in pd.period_range("2016-01", weekly["month"].max(), freq="M").strftime("%Y-%m"):
            day = date.fromisoformat(month + "-15")
            if month >= "2020-10" and month in means.index and means.loc[month, "weeks"] >= 2:
                out.append({"date": day, "jkm": float(means.loc[month, "jkm"]), "ttf": float(means.loc[month, "ttf"]),
                            "basis": "mean of %d weekly averages" % means.loc[month, "weeks"], "period": "month"})
            elif month in meti.index and month in wb.index:
                out.append({"date": day, "jkm": float(meti[month]), "ttf": float(wb[month]),
                            "basis": "METI spot price for Japan and World Bank TTF", "period": "month"})
        return out

    # -- one input at a time ----------------------------------------------------

    def hire_scenarios(self, ship_id: str) -> dict:
        """Low, central and high: quartiles of the monthly medians of the rates reported for the ship."""
        name = next(s["name"] for s in self.p["ships"] if s["id"] == ship_id)
        rates = self.rates[self.rates["ship"] == name]
        monthly = rates.groupby(rates["date"].dt.strftime("%Y-%m"))["usd_per_day"].median()
        q = self.p["hire"]["scenario_quantiles"]
        return {k: float(round(monthly.quantile(v) / 250.0) * 250.0) for k, v in q.items()}

    def hire(self, day: pd.Timestamp, ship: dict) -> dict:
        """The last reported rate, held for 26 weeks at most; otherwise the stated assumption."""
        h = self.p["hire"]
        rows = self.rates[(self.rates["date"] <= day) & (self.rates["date"] >= day - pd.Timedelta(days=h["max_hold_days"]["value"]))]
        if not len(rows):
            return {"value": self.hire_scenarios(ship["id"])[h["unreported"]["value"]], "date": None, "status": "assumed",
                    "note": "no rate reported in the 26 weeks before: the low scenario for the ship"}
        row = rows.iloc[-1]
        age = (day - row["date"]).days
        return {"value": float(row["usd_per_day"]), "date": row["date"].date(), "status": "reported" if age <= 14 else "held",
                "note": "%s, %s" % (row["assessment"], row["publisher"]), "url": row["url"] if isinstance(row["url"], str) else None}

    def des_discount_eur_mwh(self, day: pd.Timestamp, period: str, ttf_usd: float, usd_per_eur: float) -> dict:
        d = self.p["des_discount"]
        spread = self.acer.dropna(subset=["nwe_spread_to_ttf_eur_mwh"])
        column = "nwe_spread_to_ttf_eur_mwh"
        if period == "month":
            month = spread[spread["date"].dt.strftime("%Y-%m") == day.strftime("%Y-%m")]
            if len(month) >= 10:
                return {"value": float(month[column].mean()), "date": month["date"].iloc[-1].date(), "status": "observed",
                        "note": "ACER, mean of the month's %d daily values" % len(month)}
        window = spread[(spread["date"] <= day) & (spread["date"] > day - pd.Timedelta(days=45))].tail(int(d["window_days"]["value"]))
        if len(window) >= 5 and (day - window["date"].iloc[-1]).days <= 10:
            return {"value": float(window[column].mean()), "date": window["date"].iloc[-1].date(), "status": "observed",
                    "note": "ACER, mean of the last %d daily values" % len(window)}
        if day > spread["date"].iloc[-1]:
            last = spread.tail(int(d["window_days"]["value"]))
            return {"value": float(last[column].mean()), "date": last["date"].iloc[-1].date(), "status": "held",
                    "note": "ACER, mean of the last %d daily values published" % len(last)}
        level = self.acer.dropna(subset=["nwe_des_eur_mwh"])
        week = level[(level["date"] <= day) & (level["date"] > day - pd.Timedelta(days=7))]
        if len(week) >= 3:
            ttf_eur = engine.usd_mmbtu_to_eur_mwh(ttf_usd, usd_per_eur)
            return {"value": float(week["nwe_des_eur_mwh"].mean()) - ttf_eur, "date": week["date"].iloc[-1].date(),
                    "status": "derived", "note": "ACER's Northwest Europe DES price for the week less the week's TTF"}
        squeeze = d["squeeze_2022"]
        if pd.Timestamp(squeeze["from"]) <= day <= pd.Timestamp(squeeze["to"]):
            return {"value": squeeze["eur_mwh"], "date": None, "status": "assumed",
                    "note": "ACER reports a discount above 35 EUR/MWh on most days from late July to mid October 2022"}
        return {"value": d["before_acer_eur_mwh"]["value"], "date": None, "status": "assumed",
                "note": "before ACER's assessments begin: its average for 2023, 2 EUR/MWh"}

    def henry_hub(self, day: pd.Timestamp) -> dict:
        """The contract's Henry Hub: the NYMEX final settlement for the loading month.

        The contract for a month expires three business days before the month
        begins. EIA no longer publishes futures, so the spot price of that
        expiry day stands in for the settlement: spot and the expiring future
        converge, and a month's average spot would carry spikes the contract
        price never saw (February 2021, January 2026).
        """
        first = day.replace(day=1)
        before = self.hh[(self.hh["date"] < first) & (self.hh["date"] >= first - pd.offsets.MonthBegin(1))]
        if len(before) >= 15 and self.hh["date"].iloc[-1] >= first - pd.Timedelta(days=4):
            row = before.iloc[-3]
            return {"value": float(row["usd_mmbtu"]), "date": row["date"].date(), "status": "observed",
                    "note": "spot price on the day the loading month's NYMEX contract expired"}
        last = self.hh.iloc[-1]
        return {"value": float(last["usd_mmbtu"]), "date": last["date"].date(), "status": "held",
                "note": "the last daily spot price published"}

    def eua_eur_t(self, day: pd.Timestamp) -> dict:
        month = day.strftime("%Y-%m")
        rows = self.eua[self.eua["month"] <= month]
        if not len(rows):
            return {"value": 0.0, "date": None, "status": "observed", "note": "shipping is outside the EU ETS before 2024"}
        row = rows.iloc[-1]
        return {"value": float(row["eua_eur_t"]), "date": row["month"], "status": "observed" if row["month"] == month else "held",
                "note": row["source"]}

    def _stamp(self, frame: pd.DataFrame, day: pd.Timestamp, column: str, note: str) -> dict:
        value, on = _last_on_or_before(frame, day, column)
        return {"value": value, "date": on, "status": "observed" if (day.date() - on).days <= 10 else "held", "note": note}

    # -- one cargo ----------------------------------------------------------------

    def cargo(self, when, jkm: float, ttf: float, period: str = "week") -> tuple[dict, dict]:
        """The model's inputs for a cargo loading on a day, and where each one comes from."""
        day = pd.Timestamp(when)
        ship = params.ship_on(day.date())
        fx = self._stamp(self.fx, day, "usd_per_eur", "Federal Reserve H.10, noon buying rate")
        des = self.des_discount_eur_mwh(day, period, ttf, fx["value"])
        hire = self.hire(day, ship)
        hh = self.henry_hub(day)
        sofr = self._stamp(self.sofr, day, "sofr_percent", "New York Fed, SOFR")
        sdr = self._stamp(self.sdr, day, "usd_per_sdr", "IMF rate, through the Bundesbank")
        eua = self.eua_eur_t(day)
        ets = params.ets_on(day.date(), ship["id"])
        panama = params.panama_charges(day.date(), ship["capacity_m3"])
        suez = params.suez_charges(day.date(), ship["capacity_m3"], sdr["value"])
        canal_days = self.p["voyage"]["canal_days_per_transit"]["value"]
        tolls = {"europe": (0.0, 0.0, 0.0), "cape": (0.0, 0.0, 0.0),
                 "panama": (panama["laden"], panama["ballast"], canal_days),
                 "suez": (suez["laden"], suez["ballast"], canal_days)}
        routes, status = {}, {}
        for rid in params.ROUTE_ORDER:
            status[rid] = params.route_status(rid, day.date())
            laden, ballast, days = tolls[rid]
            routes[rid] = {
                "market": params.MARKET[rid],
                "distance_nm": params.routes()[rid]["distance_nm"],
                "canal_days": days, "wait_days": 0.0,
                "toll_laden": laden, "toll_ballast": ballast,
                "port_cost": float(self.p["ports"]["europe_usd" if rid == "europe" else "asia_usd"]["value"]),
                "open": status[rid]["status"] == "open",
            }
        inputs = {
            "ship": {k: ship[k] for k in ("capacity_m3", "fill", "mmbtu_per_m3", "boil_off", "speed_kn")},
            "port_days": {"load": self.p["voyage"]["load_days"]["value"], "discharge": self.p["voyage"]["discharge_days"]["value"]},
            "jkm": float(jkm), "ttf": float(ttf),
            "des_discount": engine.eur_mwh_to_usd_mmbtu(des["value"], fx["value"]),
            "henry_hub": hh["value"], "hire": hire["value"],
            "carbon": dict(ets, eua_usd_t=eua["value"] * fx["value"]),
            "finance": {"rate": sofr["value"] / 100.0, "spread": self.p["finance"]["spread"]["value"],
                        "day_count": float(self.p["finance"]["day_count"]["value"])},
            "contract": {"hh_multiple": self.p["contract"]["henry_hub_multiple"]["value"],
                         "fee": self.p["contract"]["liquefaction_fee_usd_mmbtu"]["value"]},
            "routes": routes,
        }
        meta = {"date": day.date(), "period": period, "ship": {"id": ship["id"], "name": ship["name"]},
                "usd_per_eur": fx, "des_discount_eur_mwh": des, "hire": hire, "henry_hub": hh, "sofr": sofr,
                "usd_per_sdr": sdr, "eua_eur_t": eua, "route_status": status,
                "panama": panama, "suez": suez, "ets": ets}
        return inputs, meta
