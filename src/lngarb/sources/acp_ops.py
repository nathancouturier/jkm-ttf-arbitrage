"""The Panama Canal Authority's Monthly Canal Operations Summary, one advisory a month, read from July 2006.

Each month the Authority issues an Advisory to Shipping that summarises the
month's operations: the daily average, high and low of arrivals, of oceangoing
transits, of Canal Waters Time (the hours from a ship's arrival at the canal to
its departure, waiting included) and of In-Transit Time (the hours in the
canal itself), the transits of the month by beam, with the neopanamax locks'
share from their opening in June 2016, and the booking slots offered and used.
The figures are for every ship; the Authority does not split them by market
segment or by booked and unbooked ships, so they bound what an LNG carrier
waited rather than measure it.

The advisories are listed on the Authority's page of advisories to shipping,
one PDF each, named irregularly, from the summary for December 2001; the
adapter reads the page, keeps the links whose label names an operations
summary, and fetches only the months newer than the committed cache, ten
seconds apart, the crawl delay the Authority's robots.txt asks of every
client. The covered month is read from the PDF's own subject line, the label
on the page standing in when the PDF carries none. The summaries from
December 2001 to June 2006 are scanned images without a text layer, which
the parser cannot read; the series starts with July 2006, the first summary
with one, and those months are not counted as gaps.

The Authority's terms of use forbid copying, distribution and publication of
the site's documents "for commercial or lucrative purposes"; this study is
neither, and the figures are kept unchanged and credited, with the
Authority's own disclaimer (docs/sources.md, section 2.17).
"""

from __future__ import annotations

import html
import io
import re
import sys

import pandas as pd
import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

from ..config import (
    BOUNDS_CANAL_HOURS, BOUNDS_DAILY_TRANSITS, BOUNDS_MONTHLY_SLOTS, BOUNDS_MONTHLY_TRANSITS,
)
from .base import Adapter, SourceError, http_get, read_cache

__all__ = ["LIST_URL", "CRAWL_DELAY_S", "FIRST_MONTH", "summary_links", "parse_summary", "AcpCanalOperationsMonthly"]

LIST_URL = "https://pancanal.com/en/maritime-services/advisory-to-shipping/"
#: pancanal.com's robots.txt: "Crawl-delay: 10"
CRAWL_DELAY_S = 10.0
#: the first month the page lists a summary for (advisory A-01-2002)
FIRST_MONTH = "2001-12-01"
#: the first summary with a text layer; the earlier ones are scanned images
TEXT_LAYER_FROM = "2006-07-01"

_ITEM = re.compile(
    r'<a href="(https://pancanal\.com/wp-content/uploads/[^"]+\.pdf)"[^>]*>.*?'
    r'<h3>([^<]*)</h3>\s*<div class="d_des">([^<]*)</div>', re.S)
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"])}
# The Authority's own misspellings of a month, as its labels and subjects carry them.
_MONTHS.update({"juny": 6, "feburary": 2, "febraury": 2, "sept": 9})
_MONTH_YEAR = re.compile(r"summary\s*[^A-Za-z0-9]*\s*([A-Za-z]+)\.?\s*,?\s*(\d{4})", re.I)
_NUM = r"(-?\d[\d,]*\.?\d*)"
_ADVISORY = re.compile(r"Advisory\s+To\s+Shipping\s+No\.?\s*(A-\d+-\d{4})", re.I)
_SUBJECT = re.compile(r"SUBJECT\s*:\s*([^\n]*Summary[^\n]*)", re.I)
_TRIPLE = {
    "arrivals_daily_avg": re.compile(r"Arrivals\s+" + _NUM + r"\s+" + _NUM + r"\s+" + _NUM, re.I),
    "transits_daily_avg": re.compile(r"Oceangoing\s+Transits\s+" + _NUM + r"\s+" + _NUM + r"\s+" + _NUM, re.I),
    "cwt_hours_avg": re.compile(r"Canal\s+Waters\s+Time\s*\(hours\)\s+" + _NUM + r"\s+" + _NUM + r"\s+" + _NUM, re.I),
    "in_transit_hours_avg": re.compile(r"In-?\s?Transit\s+Time\s*\(hours\)\s+" + _NUM + r"\s+" + _NUM + r"\s+" + _NUM, re.I),
}
_TOTAL = re.compile(r"Total:?\s+" + _NUM + r"\s+" + _NUM + r"\s+100(?:\.0+)?\b")
_NEOPANAMAX = re.compile(r"Neopanamax\s+Vessels[^\n]*?\)\s+" + _NUM + r"\s+" + _NUM + r"\s+" + _NUM, re.I)
_SLOTS = re.compile(r"Neopanamax\s*\(vessels[^\n]*?\)\s+" + _NUM + r"\*?\s+" + _NUM, re.I)


def _month_of(words: str) -> str | None:
    found = _MONTH_YEAR.search(words or "")
    if not found or found.group(1).lower() not in _MONTHS:
        return None
    return "%s-%02d-01" % (found.group(2), _MONTHS[found.group(1).lower()])


def summary_links(page: bytes | str) -> list[dict]:
    """The operations summaries the advisory page links: url, advisory, label and the month the label names."""
    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    out = []
    for url, advisory, label in _ITEM.findall(text):
        label = html.unescape(label).strip()
        if "operations summary" not in label.lower():
            continue
        out.append({"url": url, "advisory": html.unescape(advisory).strip(), "label": label,
                    "month": _month_of(label)})
    if not out:
        raise SourceError("the advisory page lists no operations summary")
    return out


def _sibling(url: str) -> str | None:
    """The upload beside a "-1" copy, or None when the name carries no such suffix."""
    return url[:-len("-1.pdf")] + ".pdf" if url.endswith("-1.pdf") else None


def _number(text: str | None) -> float:
    return float("nan") if text is None else float(text.replace(",", ""))


def _grab(pattern: re.Pattern, flat: str, n: int) -> list[float]:
    found = pattern.search(flat)
    return [float("nan")] * n if not found else [_number(found.group(i + 1)) for i in range(n)]


def parse_summary(pdf: bytes, *, label_month: str | None = None, advisory: str | None = None) -> dict:
    """One month's figures from a summary's PDF.

    The covered month comes from the PDF's subject line, or from the page's
    label when the PDF names none. Figures a summary does not print are NaN:
    the neopanamax rows before the locks opened in June 2016, the slot rows
    where the table has no such line.
    """
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        text = "\n".join((page.extract_text() or "") for page in document.pages)
    flat = re.sub(r"[ \t]+", " ", text)
    subject = _SUBJECT.search(flat)
    month = _month_of(subject.group(1)) if subject else None
    if month is None:
        month = label_month
    if month is None:
        raise SourceError("the summary %s names no month in its subject, and the page's label names none" % advisory)
    found = _ADVISORY.search(flat)
    row = {"date": pd.Timestamp(month), "advisory": found.group(1) if found else (advisory or "")}
    for key, pattern in _TRIPLE.items():
        avg, high, low = _grab(pattern, flat, 3)
        row[key] = avg
        if key == "cwt_hours_avg":
            row["cwt_hours_high"], row["cwt_hours_low"] = high, low
    row["transits_total"] = _grab(_TOTAL, flat, 2)[0]
    row["neopanamax_transits"] = _grab(_NEOPANAMAX, flat, 3)[0]
    row["neopanamax_slots_available"], row["neopanamax_slots_used"] = _grab(_SLOTS, flat, 2)
    if pd.isna(row["cwt_hours_avg"]):
        raise SourceError("the summary %s for %s prints no Canal Waters Time the parser reads" % (row["advisory"], month))
    return row


COLUMNS = ["date", "advisory", "cwt_hours_avg", "cwt_hours_high", "cwt_hours_low", "in_transit_hours_avg",
           "arrivals_daily_avg", "transits_daily_avg", "transits_total", "neopanamax_transits",
           "neopanamax_slots_available", "neopanamax_slots_used"]


class AcpCanalOperationsMonthly(Adapter):
    """Canal Waters Time and transits, monthly, every ship, from the Authority's summaries."""

    name = "acp_canal_operations_monthly"
    source = "Panama Canal Authority, Monthly Canal Operations Summary, advisories to shipping"
    url = LIST_URL
    page_url = LIST_URL
    unit = "hours, and counts of ships"
    frequency = "monthly"
    method = "parsed"
    required_cols = tuple(COLUMNS)
    bounds = {
        "cwt_hours_avg": BOUNDS_CANAL_HOURS, "cwt_hours_high": BOUNDS_CANAL_HOURS,
        "cwt_hours_low": BOUNDS_CANAL_HOURS, "in_transit_hours_avg": BOUNDS_CANAL_HOURS,
        "arrivals_daily_avg": BOUNDS_DAILY_TRANSITS, "transits_daily_avg": BOUNDS_DAILY_TRANSITS,
        "transits_total": BOUNDS_MONTHLY_TRANSITS, "neopanamax_transits": BOUNDS_MONTHLY_TRANSITS,
        "neopanamax_slots_available": BOUNDS_MONTHLY_SLOTS, "neopanamax_slots_used": BOUNDS_MONTHLY_SLOTS,
    }
    min_observations = {"cwt_hours_avg": 1, "cwt_hours_high": 1, "cwt_hours_low": 1, "in_transit_hours_avg": 1,
                        "arrivals_daily_avg": 1, "transits_daily_avg": 1, "transits_total": 1,
                        "neopanamax_transits": 1, "neopanamax_slots_available": 1, "neopanamax_slots_used": 1}
    observation_column = "cwt_hours_avg"
    licence_note = (
        "The Authority's terms of use forbid copying, distribution and publication of the site's documents "
        "for commercial or lucrative purposes; this non-commercial study keeps the figures unchanged, credits "
        "the Authority and carries its disclaimer that the information is for general purposes and may vary "
        "with traffic audits."
    )

    def __init__(self, *, page: bytes | None = None, summaries: dict[str, bytes] | None = None):
        # page and summaries (url -> PDF) stand in for the network in a run without one
        self.page = page
        self.summaries = summaries

    def fetch(self) -> pd.DataFrame:
        existing = read_cache(self.name, directory=self.directory())
        prior = None
        latest_held = ""
        if existing is not None and len(existing):
            prior = existing[COLUMNS].copy()
            prior["date"] = pd.to_datetime(prior["date"])
            latest_held = prior["date"].max().strftime("%Y-%m-%d")
        page = self.page if self.page is not None else http_get(LIST_URL, timeout=120, delay=CRAWL_DELAY_S).content
        links = summary_links(page)
        wanted, seen = [], set()
        scanned = 0
        for link in links:
            if link["url"] in seen:
                continue
            seen.add(link["url"])
            if link["month"] is not None and link["month"] < TEXT_LAYER_FROM:
                scanned += 1
                continue
            if link["month"] is not None and link["month"] <= latest_held:
                continue
            wanted.append(link)
        rows = []
        unreadable = []
        mislinked = []
        siblings = []
        for link in wanted:
            if self.summaries is not None:
                if link["url"] not in self.summaries:
                    continue
                pdf = self.summaries[link["url"]]
            else:
                pdf = http_get(link["url"], timeout=120, delay=CRAWL_DELAY_S).content
            try:
                row = parse_summary(pdf, label_month=link["month"], advisory=link["advisory"])
            except PdfminerException:
                # The page links a password protected copy of March 2024, named with a
                # "-1" suffix; the readable upload sits beside it without the suffix.
                sibling = _sibling(link["url"])
                pdf = None
                if sibling is not None:
                    if self.summaries is not None:
                        pdf = self.summaries.get(sibling)
                    else:
                        try:
                            pdf = http_get(sibling, timeout=120, delay=CRAWL_DELAY_S).content
                        except SourceError:
                            pdf = None
                if pdf is None:
                    unreadable.append(link)
                    continue
                try:
                    row = parse_summary(pdf, label_month=link["month"], advisory=link["advisory"])
                except (PdfminerException, SourceError):
                    unreadable.append(link)
                    continue
                siblings.append(link)
            except SourceError as exc:
                # The page's label names a summary but the file is another advisory
                # (September 2017 links a lane outage notice): the month is a gap, said here.
                mislinked.append((link, str(exc)))
                continue
            if row["date"].strftime("%Y-%m-%d") <= latest_held:
                continue
            rows.append(row)
        read_months = {r["date"].strftime("%Y-%m-%d") for r in rows}
        for link in unreadable:
            if link["month"] is None or (link["month"] not in read_months and link["month"] > latest_held):
                raise SourceError("the summary %s at %s cannot be opened, and no other file gives its month"
                                  % (link["advisory"], link["url"]))
        frames = [f for f in (prior, pd.DataFrame(rows, columns=COLUMNS) if rows else None) if f is not None and len(f)]
        if not frames:
            raise SourceError("no summary to read and nothing committed")
        frame = pd.concat(frames, ignore_index=True)
        # A month printed twice keeps its later advisory, the Authority's revision.
        frame = frame.sort_values(["date", "advisory"], kind="mergesort").drop_duplicates("date", keep="last")
        frame = frame.reset_index(drop=True)
        first, last = frame["date"].iloc[0], frame["date"].iloc[-1]
        self.vintage = "advisories %s to %s" % (frame["advisory"].iloc[0], frame["advisory"].iloc[-1])
        self.note = (
            "%d summary(ies) read this run%s%s%s; %d months held, %s to %s, each from the Authority's advisory for "
            "it%s. Canal Waters Time is the hours from a ship's arrival to its departure, waiting included, as "
            "the daily average, high and low of the month over every oceangoing ship; the Authority does not "
            "split it by segment or by booked and unbooked ships. Transits are the month's total and the "
            "neopanamax locks' share from their opening in June 2016; the slots are those the Authority "
            "offered and used for neopanamax ships where the summary prints them. Source: Panama Canal "
            "Authority; the information is for general purposes only and may vary with traffic audits, as "
            "the Authority says; non-commercial use."
            % (len(rows),
               "" if not unreadable else (", and %d file(s) the page links that cannot be opened, password protected, "
                                          "whose month another file gives (%s)"
                                          % (len(unreadable), ", ".join(l["advisory"] for l in unreadable))),
               "" if not siblings else (", %d of them from the upload beside a password protected copy the page "
                                        "links (%s)" % (len(siblings), ", ".join(l["advisory"] for l in siblings))),
               "" if not mislinked else (", and %d link(s) whose label names a summary but whose file is another "
                                         "advisory or prints no traffic table, left as gaps (%s)"
                                         % (len(mislinked), "; ".join("%s for %s" % (l["advisory"], l["month"][:7] if l["month"] else "no month")
                                                                        for l, _ in mislinked))),
               len(frame), first.strftime("%B %Y"), last.strftime("%B %Y"),
               "" if not scanned else ("; the %d summaries the page lists before %s, from December 2001, are "
                                       "scanned images without a text layer and are not read"
                                       % (scanned, pd.Timestamp(TEXT_LAYER_FROM).strftime("%B %Y"))))
        )
        return frame


def main() -> int:
    try:
        entry = AcpCanalOperationsMonthly().run()
    except Exception as exc:
        print("FAILED acp_canal_operations_monthly: %s" % exc)
        return 1
    print("ok     %s: %d months, %s to %s" % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
