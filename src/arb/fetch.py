"""The weekly refresh: python -m arb.fetch [source ...]

Each source is fetched on its own. One that fails keeps the data it had: the
failure is written to data/status.json with the date of the last value held,
the site shows that date, and the run goes on. Nothing is ever filled in.

Fetched here (fixed addresses that each site's robots rules allow):
    eia_weekly     JKM and TTF, EIA's WNGSR Supplement, the current issue only
    henry_hub      EIA's daily Henry Hub spot price
    usd_per_eur    Federal Reserve H.10
    sofr           New York Fed
    usd_per_sdr    IMF rate, through the Bundesbank
    doe_cargoes    DOE's cargo by cargo record of US LNG exports
    charter_rate   Spark's Atlantic rate, when an LNG Prime headline states it

Updated by hand, as committed files: ACER's DES assessments (a download from
its TERMINAL platform), the EU allowance price, the canal statistics, and any
charter rate a headline does not give.

Traps met in these sources
    EIA  The Supplement shows one issue. A week not read while it is current
         can only be read by hand from EIA's archive pages, which its robots
         rules close to code. eia.gov answers 503 to HEAD requests.
    EIA  The Henry Hub workbook is a legacy .xls; holidays are omitted.
    Fed  A day with no rate carries OBS_VALUE -9999 with OBS_STATUS ND.
    DOE  The workbook's address changes every month and its page every year,
         so both are read from the listing. A row is a cargo or a part of one.
    NY Fed  Rows come newest first; a day with no publication has no row.
"""

from __future__ import annotations

import csv
import html
import io
import json
import re
import sys
import zipfile
from datetime import date, datetime, timezone

import pandas as pd
import requests

from . import params

DATA = params.DATA
AGENT = {"User-Agent": "Mozilla/5.0 (compatible; jkm-ttf-arbitrage study; +https://github.com/nathancouturier/jkm-ttf-arbitrage)"}
EIA = "https://www.eia.gov/naturalgas/weekly/supplement/content/"
MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October November December".split(), 1)}


def get(url: str, **params_) -> requests.Response:
    response = requests.get(url, headers=AGENT, timeout=90, **params_)
    response.raise_for_status()
    return response


def _between(value: float, low: float, high: float, what: str) -> float:
    if not low <= value <= high:
        raise ValueError("%s of %s is outside %s to %s" % (what, value, low, high))
    return value


# ---------------------------------------------------------------------------
# EIA: weekly JKM and TTF
# ---------------------------------------------------------------------------

def parse_supplement(bullets_html: str, release: dict) -> dict:
    """The week's JKM and TTF averages from the Supplement's LNG bullets."""
    items = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", li)).strip()
             for li in re.findall(r"<li>(.*?)</li>", bullets_html, flags=re.S)]
    week = datetime.strptime(release["data-week-ending"], "%B %d, %Y").date()
    heading = next(i for i in items if i.startswith("For the week ending"))
    month, day = re.search(r"For the week ending (\w+) (\d+)", heading).groups()
    if (MONTHS[month], int(day)) != (week.month, week.day):
        raise ValueError("the bullets are for %s %s but the release file says %s" % (month, day, week))

    def averaged(names: str, other: str) -> float:
        found = [i for i in items if re.search(names, i) and "averaged $" in i and not re.search(other, i)]
        if len(found) != 1:
            raise ValueError("%d sentences give an average for %s" % (len(found), names))
        return float(re.search(r"averaged \$(\d+\.\d+)/MMBtu", found[0]).group(1))

    jkm = _between(averaged(r"Japan-Korea Marker|JKM", r"Title Transfer Facility|TTF"), 0.5, 150, "JKM")
    ttf = _between(averaged(r"Title Transfer Facility|TTF", r"Japan-Korea Marker|JKM"), 0.5, 150, "TTF")
    released = datetime.strptime(release["release-date"], "%B %d, %Y").date()
    return {"week_ending": str(week), "jkm_usd_mmbtu": jkm, "ttf_usd_mmbtu": ttf, "basis": "front-month futures",
            "source": "EIA WNGSR Supplement", "released": str(released)}


def eia_weekly() -> tuple[str, str]:
    release = get(EIA + "release_dates.json").json()
    row = parse_supplement(get(EIA + "bullets_lng_2.html").text, release)
    path = DATA / "prices_weekly.csv"
    frame = pd.read_csv(path, dtype=str)
    listed = {p["data-week-ending"] for p in release.get("past-publications", [])} | {row["week_ending"]}
    missing = sorted(w for w in listed if w > "2026-01-28" and w not in set(frame["week_ending"]) | {row["week_ending"]})
    note = "" if not missing else "; not held and only readable by hand: " + ", ".join(missing)
    if row["week_ending"] in set(frame["week_ending"]):
        return frame["week_ending"].max(), "no new week" + note
    frame = pd.concat([frame, pd.DataFrame([{k: str(v) for k, v in row.items()}])]).sort_values("week_ending")
    frame.to_csv(path, index=False)
    return row["week_ending"], "added the week to %s: JKM %s, TTF %s%s" % (row["week_ending"], row["jkm_usd_mmbtu"], row["ttf_usd_mmbtu"], note)


# ---------------------------------------------------------------------------
# EIA: Henry Hub
# ---------------------------------------------------------------------------

def henry_hub() -> tuple[str, str]:
    import xlrd

    book = xlrd.open_workbook(file_contents=get("https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls").content)
    sheet = book.sheet_by_name("Data 1")
    rows = []
    for r in range(3, sheet.nrows):
        if sheet.cell_type(r, 0) == xlrd.XL_CELL_DATE and sheet.cell_type(r, 1) == xlrd.XL_CELL_NUMBER:
            day = xlrd.xldate_as_datetime(sheet.cell_value(r, 0), book.datemode).date()
            if day >= date(2015, 1, 1):
                rows.append((str(day), _between(float(sheet.cell_value(r, 1)), 0.3, 60, "Henry Hub")))
    return _replace("henry_hub_daily.csv", ["date", "usd_mmbtu"], rows)


# ---------------------------------------------------------------------------
# Federal Reserve: dollars per euro
# ---------------------------------------------------------------------------

def usd_per_eur() -> tuple[str, str]:
    archive = zipfile.ZipFile(io.BytesIO(get("https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip").content))
    xml = archive.read("H10_data.xml").decode("utf-8", "ignore")
    start = xml.index('SERIES_NAME="RXI$US_N.B.EU"')
    block = xml[start:xml.index("</kf:Series>", start)]
    if "USD per EUR" not in block:
        raise ValueError("the euro series is no longer described as USD per EUR")
    rows = []
    for status, value, day in re.findall(r'OBS_STATUS="(\w+)" OBS_VALUE="([-\d.]+)" TIME_PERIOD="(\d{4}-\d\d-\d\d)"', block):
        if status == "A" and day >= "2015-01-01":
            rows.append((day, _between(float(value), 0.8, 1.7, "USD per EUR")))
    return _replace("usd_per_eur_daily.csv", ["date", "usd_per_eur"], rows)


# ---------------------------------------------------------------------------
# New York Fed: SOFR
# ---------------------------------------------------------------------------

def sofr() -> tuple[str, str]:
    path = DATA / "sofr_daily.csv"
    frame = pd.read_csv(path, dtype=str)
    last = frame["date"].max()
    url = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"
    rates = get(url, params={"startDate": last, "endDate": str(date.today())}).json()["refRates"]
    new = [{"date": r["effectiveDate"], "sofr_percent": str(_between(float(r["percentRate"]), -1, 15, "SOFR")), "kind": "published"}
           for r in rates if r["effectiveDate"] > last]
    if not new:
        return last, "no new day"
    frame = pd.concat([frame, pd.DataFrame(new)]).sort_values("date")
    frame.to_csv(path, index=False)
    return frame["date"].max(), "added %d days" % len(new)


# ---------------------------------------------------------------------------
# IMF through the Bundesbank: dollars per SDR
# ---------------------------------------------------------------------------

def usd_per_sdr() -> tuple[str, str]:
    text = get("https://api.statistiken.bundesbank.de/rest/download/BBEX3/D.USD.XDR.DA.AC.000", params={"format": "csv", "lang": "en"}).text
    rows = []
    for line in csv.reader(io.StringIO(text)):
        if len(line) >= 2 and re.fullmatch(r"\d{4}-\d\d-\d\d", line[0]) and line[0] >= "2015-01-01":
            try:
                rows.append((line[0], _between(float(line[1]), 0.9, 2.0, "USD per SDR")))
            except ValueError:
                continue                      # a day with no rate is printed as a full stop
    return _replace("usd_per_sdr_daily.csv", ["date", "usd_per_sdr"], rows)


# ---------------------------------------------------------------------------
# DOE: cargo by cargo exports
# ---------------------------------------------------------------------------

def doe_cargoes() -> tuple[str, str]:
    import openpyxl

    site = "https://www.energy.gov"
    listing = get(site + "/hgeo/listings/natural-gas-imports-and-exports-monthly-reports").text
    years = sorted(set(re.findall(r'href="(/hgeo/articles/natural-gas-imports-and-exports-monthly-(\d{4}))"', listing)), key=lambda x: x[1])
    page = get(site + years[-1][0]).text
    links = re.findall(r'href="([^"]+LNG%20Exports%20and%20Re-Exports%20Details[^"]+\.xlsx)"', page)
    if len(set(links)) != 1:
        raise ValueError("%d links to the LNG exports workbook on %s" % (len(set(links)), years[-1][0]))
    book = openpyxl.load_workbook(io.BytesIO(get(site + links[0] if links[0].startswith("/") else links[0]).content), read_only=True, data_only=True)
    rows = book["By Vessel and ISO Container"].iter_rows(values_only=True)
    header = [str(h).strip() for h in next(rows)]
    col = {name: header.index(name) for name in
           ("Arrival/Departure Date", "Activity", "Mode of Transport", "Tanker", "Point of Entry or Exit", "Country", "Volume (MMCF)")}
    out = []
    for r in rows:
        day, volume = r[col["Arrival/Departure Date"]], r[col["Volume (MMCF)"]]
        if r[col["Activity"]] != "Exports" or r[col["Mode of Transport"]] != "Vessel" or not isinstance(day, datetime):
            continue
        out.append((str(day.date()), r[col["Tanker"]] or "", r[col["Point of Entry or Exit"]] or "",
                    str(r[col["Country"]]).strip(), _between(float(volume), 0, 10000, "a cargo in MMcf")))
    out.sort()
    known = set(params.load()["flows"]["jkm_markets"]) | {c for group in params.load()["flows"]["regions"].values() for c in group}
    unknown = sorted({r[3] for r in out} - known)
    last, message = _replace("us_lng_cargoes_doe.csv", ["date", "tanker", "port", "country", "mmcf"], out, shrink_ok=False)
    if unknown:
        message += "; counted under Other until data/params.json names their region: " + ", ".join(unknown)
    return last, message


# ---------------------------------------------------------------------------
# LNG Prime: Spark's Atlantic rate, when a headline states it
# ---------------------------------------------------------------------------

def charter_rate() -> tuple[str, str]:
    page = get("https://lngprime.com/tag/spark/").text
    path = DATA / "charter_rates.csv"
    frame = pd.read_csv(path, dtype=str)
    last, added = frame["date"].max(), []
    for block in re.findall(r'<div class="td_module_\w+ td_module_wrap.*?</time>', page, flags=re.S):
        link = re.search(r'<h3 class="entry-title td-module-title">\s*<a href="([^"]+)"[^>]*title="([^"]*)"', block)
        day = re.search(r'datetime="(\d{4}-\d\d-\d\d)', block)
        if not link or not day or day.group(1) <= last:
            continue
        title = html.unescape(link.group(2))
        figure = re.search(r"^Atlantic (?:spot )?LNG (?:shipping |freight )?rates? [a-z ]*?(?:to|at) (?:just )?\$([\d,]+) per day", title)
        if figure and not re.search(r"above|below|almost|nearly|about", title):
            usd = int(figure.group(1).replace(",", ""))
            if 0 <= usd <= 500000 and usd % 250 == 0:
                added.append({"date": day.group(1), "usd_per_day": str(usd), "assessment": "Spark30S Atlantic",
                              "ship": params.ship_on(day.group(1))["name"], "publisher": "LNG Prime, quoting Spark Commodities",
                              "url": link.group(1), "read_from": "headline"})
    if not added:
        return last, "no headline since %s states the rate" % last
    frame = pd.concat([frame, pd.DataFrame(added)]).sort_values("date")
    frame.to_csv(path, index=False)
    return frame["date"].max(), "added %s" % ", ".join("%s on %s" % (a["usd_per_day"], a["date"]) for a in added)


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def _replace(name: str, columns: list[str], rows: list[tuple], shrink_ok: bool = True) -> tuple[str, str]:
    """Writes a file read whole from its source, unless it lost history."""
    path = DATA / name
    old = pd.read_csv(path, dtype=str)
    if not rows or rows[-1][0] < old["date"].max() or (not shrink_ok and len(rows) < len(old)):
        raise ValueError("the source now ends on %s with %d rows, before the %s and %d rows held"
                         % (rows[-1][0] if rows else "nothing", len(rows), old["date"].max(), len(old)))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)
    return rows[-1][0], "%d new rows" % (len(rows) - len(old)) if len(rows) != len(old) else "no new row"


SOURCES = {"eia_weekly": eia_weekly, "henry_hub": henry_hub, "usd_per_eur": usd_per_eur, "sofr": sofr,
           "usd_per_sdr": usd_per_sdr, "doe_cargoes": doe_cargoes, "charter_rate": charter_rate}
FILES = {"eia_weekly": ("prices_weekly.csv", "week_ending"), "henry_hub": ("henry_hub_daily.csv", "date"),
         "usd_per_eur": ("usd_per_eur_daily.csv", "date"), "sofr": ("sofr_daily.csv", "date"),
         "usd_per_sdr": ("usd_per_sdr_daily.csv", "date"), "doe_cargoes": ("us_lng_cargoes_doe.csv", "date"),
         "charter_rate": ("charter_rates.csv", "date")}


def run(names: list[str] | None = None) -> dict:
    path = DATA / "status.json"
    status = json.loads(path.read_text()) if path.exists() else {}
    for name in names or list(SOURCES):
        entry = status.get(name, {})
        entry["checked"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        try:
            entry["last"], entry["message"] = SOURCES[name]()
            entry["ok"] = True
        except Exception as error:               # one source failing must not stop the others
            name_, column = FILES[name]
            entry["ok"] = False
            entry["last"] = str(pd.read_csv(DATA / name_, dtype=str)[column].max())
            entry["message"] = "kept the data held: %s: %s" % (type(error).__name__, str(error)[:160])
        status[name] = entry
        print("%-13s %s  %s" % (name, "ok    " if entry["ok"] else "FAILED", entry["message"]), flush=True)
    path.write_text(json.dumps(status, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return status


if __name__ == "__main__":
    run(sys.argv[1:] or None)
