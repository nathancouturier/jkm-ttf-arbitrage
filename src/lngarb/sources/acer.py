"""ACER's LNG price assessments and benchmark, EUR/MWh, from what ACER publishes on its main site.

ACER assesses a daily spot price for LNG delivered ex ship (DES) into three
areas, North-West Europe (NWE), South Europe (SE) and the EU as a whole, and
publishes a daily benchmark: the EU DES assessment minus the settlement of the
ICE Endex TTF front-month futures contract. The benchmark is EU minus TTF, not
NWE minus TTF. Each assessment is for delivery in the second half-month ahead:
H1 is days 1 to 15 of a month, H2 day 16 to its end, and the dates on which the
period rolls are a published table, not a formula.

The daily reports live on ACER's TERMINAL platform, which this pipeline does not
fetch; saving them is a manual step. TERMINAL also offers the history of the
three assessments and the benchmark as one CSV file, which the owner downloads
by hand into data/private/acer/ (parse_terminal_history); the latest such file
is read. What code fetches here is on ACER's main site, whose robots.txt
allows it:

    the correction notice of 20 December 2024, whose table gives the published
    and the corrected values of all four series for 26 weekdays, 4 November to
    9 December 2024, the only daily ACER values on the main site
    the assessment and benchmark methodology, version 1.1, whose annex 1 lists
    the dates on which the assessed half-month rolls, from 31 March 2023 to 24
    December 2024

The corrected values are the series; the values first published are kept in
the revised_from column as printed, and on those 26 days TERMINAL's download
must give the corrected values. ACER's figures are published; a TTF level is
never backed out of them, because the TTF leg is ICE's. The one figure this
study computes from them is the spread of the North-West Europe assessment to
the TTF front month, the EU benchmark plus the NWE assessment less the EU one:
a spread, never a TTF level.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber

from ..config import BOUNDS_DES_EUR_MWH, BOUNDS_DES_SPREAD_EUR_MWH
from . import base
from .base import Adapter, SourceError, http_get

__all__ = [
    "PAGE_URL",
    "NOTICE_URL",
    "METHODOLOGY_URL",
    "parse_roll_dates",
    "period_for",
    "parse_correction_notice",
    "parse_terminal_history",
    "latest_terminal_file",
    "AcerLngDaily",
]

PAGE_URL = "https://www.acer.europa.eu/gas/lng-price-assessment"
_DOCS = "https://www.acer.europa.eu/sites/default/files/documents/en/Gas/LNG_Price_Assessment/"
NOTICE_URL = _DOCS + "LNGPA_Correction_Notice_20241220.pdf"
METHODOLOGY_URL = _DOCS + "ACER_LNG_price_assessment_and_benchmark_methodology_1.1.pdf"

_ROLL = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(H[12] [A-Z]{3} \d{2})")
_NOTICE_ROW = re.compile(
    r"^(?:[A-Z]{3} )?(\d{2}/\d{2}/\d{4}) (?:Monday|Tuesday|Wednesday|Thursday|Friday)"
    r"((?: -?\d+\.\d{3}){12})$"
)


def _pdf_text(payload: bytes) -> str:
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def parse_roll_dates(methodology_pdf: bytes) -> list[tuple[pd.Timestamp, str]]:
    """The dates from which each half-month is assessed, from annex 1, in order."""
    text = _pdf_text(methodology_pdf)
    rows = [(pd.to_datetime(d, format="%d/%m/%Y"), label) for d, label in _ROLL.findall(text)]
    if len(rows) < 10:
        raise SourceError("annex 1 of the methodology gives %d roll dates; expected dozens" % len(rows))
    dates = [d for d, _ in rows]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise SourceError("the roll dates in annex 1 are not in order or repeat")
    return rows


def period_for(day: pd.Timestamp, rolls: list[tuple[pd.Timestamp, str]]) -> str | None:
    """The half-month assessed on a day, or None outside the published table.

    After the table's last roll the period is known only until the next roll
    could have come: within the shortest gap between two rolls in the table.
    """
    shortest = min(b[0] - a[0] for a, b in zip(rolls, rolls[1:]))
    if day < rolls[0][0] or day >= rolls[-1][0] + shortest:
        return None
    current = None
    for start, label in rolls:
        if start <= day:
            current = label
    return current


def parse_correction_notice(notice_pdf: bytes) -> pd.DataFrame:
    """The 26 rows of the correction notice's table: published, correct, difference."""
    text = _pdf_text(notice_pdf)
    if "Corrected LNG price assessment and benchmark values" not in text:
        raise SourceError("the correction notice does not carry its table")
    rows = []
    for line in text.splitlines():
        match = _NOTICE_ROW.match(line.strip())
        if not match:
            continue
        numbers = [float(x) for x in match.group(2).split()]
        (eu_p, eu_c, eu_d, nwe_p, nwe_c, nwe_d, se_p, se_c, se_d, b_p, b_c, b_d) = numbers
        rows.append(
            {
                "date": pd.to_datetime(match.group(1), format="%d/%m/%Y"),
                "eu": (eu_p, eu_c, eu_d),
                "nwe": (nwe_p, nwe_c, nwe_d),
                "se": (se_p, se_c, se_d),
                "benchmark": (b_p, b_c, b_d),
            }
        )
    if len(rows) != 26:
        raise SourceError("the correction notice's table gives %d rows; it has 26" % len(rows))
    return pd.DataFrame(rows)


#: ACER prints every figure to three decimals after computing the differences
#: from unrounded values, so printed figures can disagree by up to about one
#: thousandth through rounding alone. A disagreement larger than this is real.
ROUNDING_TOLERANCE = 0.0021


def _row(record: dict[str, Any], rolls) -> dict[str, Any]:
    notes = []
    for leg in ("eu", "nwe", "se", "benchmark"):
        published, correct, difference = record[leg]
        if abs((correct - published) - difference) > ROUNDING_TOLERANCE:
            notes.append("%s difference printed as %s, correct minus published is %.3f" % (leg, difference, correct - published))
    # With the TTF settlement unchanged, the benchmark moves by exactly the EU
    # correction. Where it does not, ACER's row is inconsistent and says so.
    if abs(record["benchmark"][2] - record["eu"][2]) > ROUNDING_TOLERANCE:
        notes.append(
            "the benchmark moved by %.3f and the EU assessment by %.3f; with the TTF "
            "settlement unchanged they would move together"
            % (record["benchmark"][2], record["eu"][2])
        )
    return {
        "date": record["date"],
        "delivery_period": period_for(record["date"], rolls),
        "eu_des_eur_mwh": record["eu"][1],
        "nwe_des_eur_mwh": record["nwe"][1],
        "se_des_eur_mwh": record["se"][1],
        "eu_benchmark_spread_eur_mwh": record["benchmark"][1],
        "source_document": "ACER correction notice of 20 December 2024, table 1",
        "revised_from": "first published EU %.3f, NWE %.3f, SE %.3f, benchmark %.3f"
        % (record["eu"][0], record["nwe"][0], record["se"][0], record["benchmark"][0]),
        "anomaly": "; ".join(notes) if notes else None,
    }


#: The header of TERMINAL's historical download, as served on 8 October 2026.
TERMINAL_HEADER = [
    "DATE", "NORTH-WEST EUROPE PRICE (EUR/MWh)", "SOUTH EUROPE PRICE (EUR/MWh)",
    "EU PRICE (EUR/MWh)", "LNG BENCHMARK (EUR/MWh)",
]
_TERMINAL_FILE = re.compile(r"^TERMINAL - PA historical - (\d{4}-\d{2}-\d{2})\.csv$")


def latest_terminal_file(directory: Path | None = None) -> tuple[Path, str] | None:
    """The latest TERMINAL download saved by hand, and the day in its name, or None."""
    directory = base.PRIVATE / "acer" if directory is None else directory
    if not directory.exists():
        return None
    found = sorted((m.group(1), path) for path in directory.iterdir()
                   if (m := _TERMINAL_FILE.match(path.name)))
    if not found:
        return None
    day, path = found[-1]
    return path, day


def parse_terminal_history(payload: bytes) -> pd.DataFrame:
    """TERMINAL's historical download: one row per day ACER published, the three assessments and the EU benchmark.

    An empty cell is a value not published that day (the series start on
    different days, the benchmark of the download's own day comes later), kept
    missing. The header must be the one this parser knows, the days unique and
    weekdays.
    """
    text = payload.decode("utf-8-sig")
    frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    if list(frame.columns) != TERMINAL_HEADER:
        raise SourceError("TERMINAL's download has the header %r, not the one this parser knows" % list(frame.columns))
    out = pd.DataFrame({"date": pd.to_datetime(frame["DATE"], format="%Y-%m-%d")})
    names = {
        "NORTH-WEST EUROPE PRICE (EUR/MWh)": "nwe_des_eur_mwh",
        "SOUTH EUROPE PRICE (EUR/MWh)": "se_des_eur_mwh",
        "EU PRICE (EUR/MWh)": "eu_des_eur_mwh",
        "LNG BENCHMARK (EUR/MWh)": "eu_benchmark_spread_eur_mwh",
    }
    for column, name in names.items():
        out[name] = pd.to_numeric(frame[column].replace("", None), errors="raise")
    if out["date"].duplicated().any():
        raise SourceError("TERMINAL's download repeats a day")
    if (out["date"].dt.weekday >= 5).any():
        raise SourceError("TERMINAL's download holds a weekend day")
    return out.sort_values("date").reset_index(drop=True)


def nwe_spread(frame: pd.DataFrame) -> pd.Series:
    """The North-West Europe assessment's spread to the TTF front month: the EU benchmark plus NWE less EU.

    Computed by this study from ACER's three figures of the day, rounded to the
    thousandth ACER prints; empty where any of them is.
    """
    return (frame["eu_benchmark_spread_eur_mwh"] + frame["nwe_des_eur_mwh"] - frame["eu_des_eur_mwh"]).round(3)


class AcerLngDaily(Adapter):
    """ACER's DES LNG assessments and EU benchmark, daily, as far as the main site gives them."""

    name = "acer_lng_daily"
    source = "European Union Agency for the Cooperation of Energy Regulators, LNG price assessment and benchmark"
    url = NOTICE_URL
    page_url = PAGE_URL
    unit = "EUR per MWh"
    frequency = "daily"
    method = "parsed"
    required_cols = ("date", "delivery_period", "eu_des_eur_mwh", "nwe_des_eur_mwh", "se_des_eur_mwh",
                     "eu_benchmark_spread_eur_mwh", "nwe_benchmark_spread_eur_mwh")
    bounds = {
        "eu_des_eur_mwh": BOUNDS_DES_EUR_MWH,
        "nwe_des_eur_mwh": BOUNDS_DES_EUR_MWH,
        "se_des_eur_mwh": BOUNDS_DES_EUR_MWH,
        "eu_benchmark_spread_eur_mwh": BOUNDS_DES_SPREAD_EUR_MWH,
        "nwe_benchmark_spread_eur_mwh": BOUNDS_DES_SPREAD_EUR_MWH,
    }
    min_observations = {name: 20 for name in bounds}
    observation_column = "eu_benchmark_spread_eur_mwh"

    def __init__(self, *, notice_pdf: bytes | None = None, methodology_pdf: bytes | None = None,
                 terminal_csv: tuple[bytes, str] | None = None):
        # terminal_csv stands in for the file saved by hand: its bytes and the
        # day it was downloaded
        self.notice_pdf = notice_pdf
        self.methodology_pdf = methodology_pdf
        self.terminal_csv = terminal_csv

    def fetch(self) -> pd.DataFrame:
        notice = self.notice_pdf if self.notice_pdf is not None else http_get(NOTICE_URL, timeout=60).content
        methodology = (
            self.methodology_pdf if self.methodology_pdf is not None else http_get(METHODOLOGY_URL, timeout=120).content
        )
        rolls = parse_roll_dates(methodology)
        records = parse_correction_notice(notice)
        frame = pd.DataFrame([_row(r, rolls) for r in records.to_dict("records")])
        terminal = self.terminal_csv
        if terminal is None:
            saved = latest_terminal_file()
            if saved is not None:
                terminal = (saved[0].read_bytes(), saved[1])
        downloaded = None
        if terminal is not None:
            payload, downloaded = terminal
            history = parse_terminal_history(payload)
            frame = self._merge(frame, history, rolls, downloaded)
        frame["nwe_benchmark_spread_eur_mwh"] = nwe_spread(frame)
        frame = frame.sort_values("date").reset_index(drop=True)
        flagged = int(frame["anomaly"].notna().sum())
        if downloaded is None:
            self.vintage = "correction notice of 20 December 2024; half-months from methodology 1.1 annex 1"
            self.note = (
                "The only daily ACER values on ACER's main site: the corrected values of the "
                "26 weekdays from 4 November to 9 December 2024, with the values first "
                "published kept as printed. %d row(s) flagged. The daily reports are on "
                "ACER's TERMINAL platform, which this pipeline does not fetch; see the "
                "manual step. Source: ACER." % flagged
            )
        else:
            self.vintage = "TERMINAL's historical download of %s; correction notice of 20 December 2024" % downloaded
            self.note = (
                "ACER's daily assessments and EU benchmark from TERMINAL's historical download, "
                "saved by hand on %s (the manual step), with the 26 days of the correction "
                "notice of 20 December 2024 and the values first published then. The NWE "
                "spread to the TTF front month is computed by this study as the EU benchmark "
                "plus the NWE assessment less the EU one. %d row(s) flagged. Source: ACER."
                % (downloaded, flagged)
            )
        return frame

    @staticmethod
    def _merge(notice: pd.DataFrame, history: pd.DataFrame, rolls, downloaded: str) -> pd.DataFrame:
        """TERMINAL's days, with the notice's 26 days kept as the notice prints them and checked against it.

    Both print three decimals, so a difference of a thousandth is a difference
    and is noted.
    """
        legs = ("eu_des_eur_mwh", "nwe_des_eur_mwh", "se_des_eur_mwh", "eu_benchmark_spread_eur_mwh")
        by_day = notice.set_index("date")
        rows = []
        for r in history.to_dict("records"):
            day = r["date"]
            if day in by_day.index:
                kept = by_day.loc[day].to_dict()
                kept["date"] = day
                differ = ["%s %s against %s" % (leg.split("_")[0], r[leg], kept[leg]) for leg in legs
                          if not (abs(r[leg] - kept[leg]) < 0.0005)]
                if differ:
                    note = "TERMINAL's download of %s differs from the notice's corrected value: %s" % (
                        downloaded, ", ".join(differ))
                    kept["anomaly"] = "; ".join(n for n in (kept.get("anomaly"), note) if n)
                rows.append(kept)
                continue
            rows.append({
                "date": day,
                "delivery_period": period_for(day, rolls),
                **{leg: r[leg] for leg in legs},
                "source_document": "ACER TERMINAL, historical price assessments, downloaded by hand on %s" % downloaded,
                "revised_from": None,
                "anomaly": None,
            })
        missing = sorted(set(by_day.index) - set(history["date"]))
        for day in missing:
            kept = by_day.loc[day].to_dict()
            kept["date"] = day
            kept["anomaly"] = "; ".join(n for n in (kept.get("anomaly"),
                                                      "not in TERMINAL's download of %s" % downloaded) if n)
            rows.append(kept)
        return pd.DataFrame(rows)


def main() -> int:
    try:
        entry = AcerLngDaily().run()
    except Exception as exc:
        print("FAILED acer_lng_daily: %s" % exc)
        return 1
    print("ok     %s: %d days, %s to %s" % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
