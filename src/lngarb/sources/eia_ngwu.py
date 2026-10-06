"""EIA's weekly JKM and TTF averages: the Natural Gas Weekly Update and its successor.

What the series is
------------------
Each issue of EIA's Natural Gas Weekly Update (NGWU) carried an item headed
"International futures prices" giving, from Bloomberg Finance L.P., the weekly
average of an East Asia LNG price and of TTF, both in USD/MMBtu, with the same
week a year earlier. The NGWU ended with the issue released on 22 January 2026
(week ending 21 January 2026), whose page says "This week is the final
publication of the Natural Gas Weekly Update". From 29 January 2026 EIA prints
the same two prices, from the same credited source but in new words, in the
Weekly Natural Gas Storage Report (WNGSR) Supplement. The two are kept as two
series, because nothing EIA publishes says the underlying Bloomberg series are
the same, and the change of product is a structural break either way.

What code may and may not fetch
-------------------------------
eia.gov's robots.txt disallows /naturalgas/weekly/archivenew_ngwu, where every
archived NGWU issue lives, and /*archive/, which covers the Supplement's
archive. Code therefore reads only:

    the NGWU landing page, which still serves the final issue
    the NGWU archive index, a single allowed page listing every issue
    the Supplement's current issue, three small files it is assembled from

Every other issue is read from a copy saved by hand into data/private/ngwu/ or
data/private/wngsr/, a manual step recorded in the manifest. base.http_get
enforces robots.txt, so a mistake here fails rather than fetches.

How the item is read
--------------------
By sentence and by the words in it, never by position. Each price sentence is
recognised by what it names (East Asia, TTF, the same week last year) and the
wording that defines each price is stored for every week, so a change of
definition is visible in the data rather than hidden in a line. A sentence of a
form this module does not recognise stops the parse with an error naming the
issue: extending the parser is a code change with a test, never a guess.

A figure printed with a typo is stored as printed in a *_printed column, next
to the value read from it, with the correction described in the anomaly column.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from bs4 import BeautifulSoup

from ..config import BOUNDS_LNG_USD_MMBTU
from . import base
from .base import Adapter, SourceError, http_get, read_cache

__all__ = [
    "LANDING_URL",
    "INDEX_URL",
    "SUPPLEMENT_URL",
    "ParseError",
    "normalise_text",
    "split_sentences",
    "parse_ngwu_page",
    "parse_ngwu_item",
    "parse_index",
    "parse_supplement",
    "NgwuIssueIndex",
    "NgwuInternationalWeekly",
    "WngsrInternationalWeekly",
]

LANDING_URL = "https://www.eia.gov/naturalgas/weekly/"
INDEX_URL = "https://www.eia.gov/naturalgas/weekly/includes/archive.php"
ARCHIVE_URL = "https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/{folder}/"
SUPPLEMENT_URL = "https://www.eia.gov/naturalgas/weekly/supplement/"
SUPPLEMENT_PRICES_URL = SUPPLEMENT_URL + "content/bullets_lng_2.html"
SUPPLEMENT_SOURCE_URL = SUPPLEMENT_URL + "content/source_lng_2.html"
SUPPLEMENT_DATES_URL = SUPPLEMENT_URL + "content/release_dates.json"

#: The first year of the index kept. Shale era exports from Sabine Pass start in
#: February 2016, so nothing earlier can be part of this study.
INDEX_FIRST_YEAR = 2016

#: The heading of the item, as the final issue prints it.
ITEM_HEADING = "International futures prices"

#: The credit every issue read so far carries.
CREDIT = "Bloomberg Finance, L.P."


class ParseError(SourceError):
    """An issue does not carry the item in a form this module recognises."""


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------

#: Dash characters are written as their code points in stored text. The
#: repository carries no em or en dash in any tracked file, and a verbatim quote
#: is no exception; the token keeps the quote exact and reversible.
_DASHES = {
    chr(0x2012): "[U+2012]",
    chr(0x2013): "[U+2013]",
    chr(0x2014): "[U+2014]",
    chr(0x2015): "[U+2015]",
}

#: Abbreviations whose full stop does not end a sentence.
_ABBREVIATIONS = ("L.P.", "U.S.", "Inc.", "Co.", "No.", "vs.", "e.g.", "i.e.")
_DOT = "\u0000"


def normalise_text(text: str) -> str:
    """Collapse whitespace, turn non-breaking spaces into spaces, tokenise dashes."""
    text = text.replace(chr(0x00A0), " ")
    for dash, token in _DASHES.items():
        text = text.replace(dash, token)
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    """Split on a full stop followed by a space and a capital, minding abbreviations."""
    protected = text
    for abbreviation in _ABBREVIATIONS:
        protected = protected.replace(abbreviation, abbreviation.replace(".", _DOT))
    pieces = re.split(r"(?<=[.])\s+(?=[A-Z])", protected)
    return [piece.replace(_DOT, ".").strip() for piece in pieces if piece.strip()]


_MONTH_DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"


def _parse_long_date(text: str) -> date:
    return datetime.strptime(text.strip(), "%B %d, %Y").date()


@dataclass(frozen=True)
class Price:
    """One price as printed and as read."""

    printed: str
    value: float
    note: str


_PRICE_TOKEN = re.compile(r"^\$(\d+(?:\.\d+)?)(.*)$")


def read_price(token: str) -> Price:
    """Read a printed price token such as "$10.73/MMBtu" or "$34.420MBtu".

    The value is the number printed. When the unit is not printed as "/MMBtu"
    the note says so; the digits are never changed.
    """
    printed = token.strip().rstrip(".,;")
    match = _PRICE_TOKEN.match(printed)
    if not match:
        raise ParseError("price token %r does not start with a dollar amount" % (token,))
    value = float(match.group(1))
    unit = match.group(2)
    note = ""
    if unit != "/MMBtu":
        note = "printed as %r, read as %s USD/MMBtu from the digits printed" % (
            printed,
            match.group(1),
        )
    return Price(printed=printed, value=value, note=note)


# --------------------------------------------------------------------------
# The NGWU item
# --------------------------------------------------------------------------

_LEG_SENTENCE = re.compile(
    r"^(?:According to Bloomberg Finance, L\.P\., )?"
    r"(?P<definition>.+?) "
    r"(?P<change>(?:increased|decreased|rose|fell|climbed|declined|dropped|gained|lost)"
    r" .+?|was unchanged|were unchanged|remained unchanged|remained flat)"
    r" (?:to|at) a weekly average of (?P<price>\$\S+?)\.?$"
)

_PRIOR_SENTENCE = re.compile(
    r"^In the same week last year \(week ending " + _MONTH_DATE + r"\), "
    r"the prices were (?P<asia>\$\S+) in East Asia and (?P<ttf>\$\S+) at TTF\.?$"
)

_INTRO_SENTENCE = re.compile(
    r"^International natural gas futures prices [a-z ]+ this report week\.$"
)


def _leg(sentence: str) -> str | None:
    if "same week last year" in sentence:
        return None
    if "East Asia" in sentence and "weekly average of" in sentence:
        return "east_asia"
    if ("Title Transfer Facility" in sentence or "(TTF)" in sentence) and (
        "weekly average of" in sentence
    ):
        return "ttf"
    return None


def parse_ngwu_item(item_text: str, *, where: str) -> dict[str, Any]:
    """The values, wordings and anomalies of one NGWU international prices item.

    where names the issue in error messages. Raises ParseError when the item
    lacks a price sentence, carries one twice, or words one in a form not
    recognised here.
    """
    body = item_text
    if body.startswith(ITEM_HEADING):
        body = body[len(ITEM_HEADING):].lstrip(" :")
    sentences = split_sentences(body)

    legs: dict[str, dict[str, Any]] = {}
    prior: dict[str, Any] | None = None
    extra: list[str] = []
    notes: list[str] = []

    for sentence in sentences:
        leg = _leg(sentence)
        if leg is not None:
            match = _LEG_SENTENCE.match(sentence)
            if not match:
                raise ParseError(
                    "%s: the %s sentence is in a form this parser does not "
                    "recognise: %r" % (where, leg, sentence)
                )
            if leg in legs:
                raise ParseError("%s: two %s sentences" % (where, leg))
            price = read_price(match.group("price"))
            if price.note:
                notes.append("%s %s" % (leg, price.note))
            legs[leg] = {
                "definition": match.group("definition"),
                "change": match.group("change"),
                "price": price,
            }
        elif "same week last year" in sentence:
            match = _PRIOR_SENTENCE.match(sentence)
            if not match:
                raise ParseError(
                    "%s: the same week last year sentence is in a form this "
                    "parser does not recognise: %r" % (where, sentence)
                )
            if prior is not None:
                raise ParseError("%s: two same week last year sentences" % (where,))
            asia = read_price(match.group("asia"))
            ttf = read_price(match.group("ttf"))
            for leg_name, price in (("prior year east_asia", asia), ("prior year ttf", ttf)):
                if price.note:
                    notes.append("%s %s" % (leg_name, price.note))
            prior = {"week_ending": _parse_long_date(match.group(1)), "asia": asia, "ttf": ttf}
        elif _INTRO_SENTENCE.match(sentence):
            continue
        else:
            extra.append(sentence)

    for required in ("east_asia", "ttf"):
        if required not in legs:
            raise ParseError("%s: no %s price sentence in the item" % (where, required))

    if extra:
        notes.append("%d further sentence(s) not about the two prices" % len(extra))
    credited = CREDIT in item_text
    if not credited:
        notes.append("no credit to %s in the item" % CREDIT)

    return {
        "east_asia_usd_mmbtu": legs["east_asia"]["price"].value,
        "ttf_usd_mmbtu": legs["ttf"]["price"].value,
        "east_asia_printed": legs["east_asia"]["price"].printed,
        "ttf_printed": legs["ttf"]["price"].printed,
        "east_asia_change_printed": legs["east_asia"]["change"],
        "ttf_change_printed": legs["ttf"]["change"],
        "east_asia_definition": legs["east_asia"]["definition"],
        "ttf_definition": legs["ttf"]["definition"],
        "prior_year_week_ending": prior["week_ending"].isoformat() if prior else None,
        "prior_year_east_asia_usd_mmbtu": prior["asia"].value if prior else None,
        "prior_year_ttf_usd_mmbtu": prior["ttf"].value if prior else None,
        "prior_year_east_asia_printed": prior["asia"].printed if prior else None,
        "prior_year_ttf_printed": prior["ttf"].printed if prior else None,
        "credit": CREDIT if credited else None,
        "anomaly": "; ".join(notes) if notes else None,
    }


def parse_ngwu_page(html: str | bytes, *, where: str) -> dict[str, Any]:
    """The dates and the international prices item of one NGWU issue page.

    Returns the week ending and release date printed in the report header and
    the item's text, normalised. Raises ParseError when either is missing or
    ambiguous.
    """
    soup = BeautifulSoup(html, "lxml")
    header = soup.find("div", class_="report_header")
    header_text = normalise_text(header.get_text(" ")) if header else ""
    week = re.search(r"for week ending " + _MONTH_DATE, header_text)
    release = re.search(r"Release date: " + _MONTH_DATE, header_text)
    if not week or not release:
        raise ParseError(
            "%s: the report header does not carry a week ending and a release "
            "date in the expected words: %r" % (where, header_text[:200])
        )

    items = []
    for strong in soup.find_all("strong"):
        if normalise_text(strong.get_text()).startswith(ITEM_HEADING):
            container = strong.find_parent("li") or strong.find_parent("p")
            if container is not None:
                items.append(container)
    if not items:
        raise ParseError("%s: no %r item on the page" % (where, ITEM_HEADING))
    if len(items) > 1:
        raise ParseError("%s: %d %r items on the page" % (where, len(items), ITEM_HEADING))

    return {
        "week_ending": _parse_long_date(week.group(1)),
        "release_date": _parse_long_date(release.group(1)),
        "item_text": normalise_text(items[0].get_text(" ")),
    }


# --------------------------------------------------------------------------
# The archive index
# --------------------------------------------------------------------------

_FOLDER = re.compile(r"/naturalgas/weekly/archivenew_ngwu/(\d{4})/(\d{2})_(\d{2})")


def listed_folders(html: str | bytes) -> set[str]:
    """The folder of every issue link in the page's markup, outside HTML comments.

    A plain scan of the text, independent of how a parser builds the table. It
    is the count parse_index must reach.
    """
    text = html.decode("utf-8", "replace") if isinstance(html, bytes) else html
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    folders = {"%s/%s_%s" % match for match in _FOLDER.findall(text)}
    return {folder for folder in folders if int(folder[:4]) >= INDEX_FIRST_YEAR}


def parse_index(html: str | bytes) -> pd.DataFrame:
    """Every issue the archive index lists from INDEX_FIRST_YEAR, one row each.

    The date of an issue is its release date, read from the folder in its link,
    never from the month and day cells, which are missing or wrong on several
    rows. A row that says "No report released" has no link; its date is the week
    after the next older issue, and must agree with the day printed in its row.
    Rows inside HTML comments are not part of the page and are not read.

    The table's markup is broken: 35 rows from 2016 to 2025 have no opening
    <tr>, so their cells sit in no row at all once the page is parsed. Rows are
    therefore found from their last cell, the one holding the link or "No report
    released", and the two cells before it in document order give the printed
    release and week ending days. The folders read must equal a plain scan of
    the markup (listed_folders), or the parse fails.
    """
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict[str, Any]] = []
    for tab in soup.find_all("div", id=re.compile(r"^tabs-past-\d{4}$")):
        year = int(tab["id"][-4:])
        if year < INDEX_FIRST_YEAR:
            continue
        pending: list[dict[str, Any]] = []
        for cell in tab.find_all("td"):
            link = cell.find("a")
            text = normalise_text(cell.get_text())
            if link is None and text != "No report released":
                continue
            before = cell.find_all_previous("td", limit=2)
            if len(before) != 2:
                raise ParseError("an index row has fewer than two cells before %r" % (text,))
            week_printed = normalise_text(before[0].get_text())
            day_printed = normalise_text(before[1].get_text())
            if link is not None:
                href = re.sub(r"\s+", "", link.get("href", ""))
                match = _FOLDER.search(href)
                if not match:
                    raise ParseError("index row links %r, not an issue folder" % (href,))
                released = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                rows.append(
                    {
                        "date": released,
                        "folder": "%s/%s_%s" % match.groups(),
                        "status": "published",
                        "release_day_printed": day_printed,
                        "week_ending_day_printed": week_printed,
                        "link_text": text,
                    }
                )
                for waiting in pending:
                    waiting["older"] = released
                pending = []
            elif text == "No report released":
                row = {
                    "date": None,
                    "folder": None,
                    "status": "no report released",
                    "release_day_printed": day_printed,
                    "week_ending_day_printed": week_printed,
                    "link_text": text,
                    "older": None,
                }
                rows.append(row)
                pending.append(row)
    for row in rows:
        if row["status"] != "no report released":
            continue
        older = row.pop("older", None)
        if older is None:
            raise ParseError("a 'No report released' row has no older issue to date it from")
        expected = older + timedelta(days=7)
        if str(expected.day) != row["release_day_printed"].lstrip("0"):
            raise ParseError(
                "a 'No report released' row prints day %s, but the week after "
                "the next older issue is %s" % (row["release_day_printed"], expected)
            )
        row["date"] = expected

    read = [row["folder"] for row in rows if row["folder"] is not None]
    listed = listed_folders(html)
    if len(read) != len(set(read)) or set(read) != listed:
        missing = sorted(listed - set(read))
        unexpected = sorted(set(read) - listed)
        raise ParseError(
            "the markup links %d issues from %d outside comments but %d rows were read "
            "(not read: %s; not in the markup: %s)"
            % (len(listed), INDEX_FIRST_YEAR, len(read), missing[:5], unexpected[:5])
        )

    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    return frame[
        ["date", "folder", "status", "release_day_printed", "week_ending_day_printed", "link_text"]
    ]


# --------------------------------------------------------------------------
# The Supplement
# --------------------------------------------------------------------------

_SUPPLEMENT_SENTENCE = re.compile(
    r"^(?P<definition>The .+?) averaged (?P<price>\$\S+?), (?P<change>.+? than the previous week)\.?$"
)


def parse_supplement(
    prices_html: str | bytes, source_html: str | bytes, dates_json: str | bytes
) -> dict[str, Any]:
    """The JKM and TTF weekly averages of one WNGSR Supplement issue.

    The week is read from release_dates.json and must agree with the month and
    day the prices fragment prints ("For the week ending September 23:").
    """
    dates = json.loads(dates_json)
    week_ending = _parse_long_date(dates["data-week-ending"])
    release = _parse_long_date(dates["release-date"])

    soup = BeautifulSoup(prices_html, "lxml")
    bullets = [normalise_text(li.get_text(" ")) for li in soup.find_all("li")]
    header = [b for b in bullets if b.startswith("For the week ending")]
    if len(header) != 1:
        raise ParseError("the Supplement prices fragment does not name one week: %r" % header)
    printed_week = re.match(r"For the week ending ([A-Z][a-z]+ \d{1,2}):", header[0])
    if not printed_week:
        raise ParseError("the Supplement week line is in an unrecognised form: %r" % header[0])
    if printed_week.group(1) != "%s %d" % (week_ending.strftime("%B"), week_ending.day):
        raise ParseError(
            "the Supplement prices fragment prints %r but release_dates.json says "
            "the week ended %s" % (printed_week.group(1), week_ending)
        )

    legs: dict[str, dict[str, Any]] = {}
    extra = 0
    for bullet in bullets:
        if bullet is header[0]:
            continue
        if "Japan-Korea Marker" in bullet or "(JKM)" in bullet:
            leg = "jkm"
        elif "Title Transfer Facility" in bullet or "(TTF)" in bullet:
            leg = "ttf"
        else:
            extra += 1
            continue
        match = _SUPPLEMENT_SENTENCE.match(bullet)
        if not match:
            raise ParseError("the Supplement %s bullet is in an unrecognised form: %r" % (leg, bullet))
        if leg in legs:
            raise ParseError("the Supplement carries two %s bullets" % leg)
        legs[leg] = {
            "definition": match.group("definition"),
            "change": match.group("change"),
            "price": read_price(match.group("price")),
            "text": bullet,
        }
    for required in ("jkm", "ttf"):
        if required not in legs:
            raise ParseError("the Supplement carries no %s bullet" % required)

    credit_text = normalise_text(BeautifulSoup(source_html, "lxml").get_text(" "))
    notes = [
        "%s %s" % (leg, legs[leg]["price"].note) for leg in ("jkm", "ttf") if legs[leg]["price"].note
    ]
    if extra:
        notes.append("%d further bullet(s) not about the two prices" % extra)
    if CREDIT not in credit_text:
        notes.append("the source fragment does not credit %s: %r" % (CREDIT, credit_text))

    return {
        "date": week_ending,
        "release_date": release,
        "item_text": " ".join([header[0], legs["ttf"]["text"], legs["jkm"]["text"]]),
        "jkm_usd_mmbtu": legs["jkm"]["price"].value,
        "ttf_usd_mmbtu": legs["ttf"]["price"].value,
        "jkm_printed": legs["jkm"]["price"].printed,
        "ttf_printed": legs["ttf"]["price"].printed,
        "jkm_change_printed": legs["jkm"]["change"],
        "ttf_change_printed": legs["ttf"]["change"],
        "jkm_definition": legs["jkm"]["definition"],
        "ttf_definition": legs["ttf"]["definition"],
        "credit": CREDIT if CREDIT in credit_text else None,
        "anomaly": "; ".join(notes) if notes else None,
    }


# --------------------------------------------------------------------------
# Adapters
# --------------------------------------------------------------------------

def manual_dir() -> Path:
    """Where NGWU issues saved by hand are read from, as YYYY/MM_DD.html."""
    return base.PRIVATE / "ngwu"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _merge_weekly(
    existing: pd.DataFrame | None, new_rows: Iterable[dict[str, Any]], *, key_text: str
) -> pd.DataFrame:
    """Add new weeks to what is committed, refusing a week whose text changed.

    A week already in the cache is kept as it is. If a new reading of the same
    week carries different item text, that is either a revision by EIA or a
    parser change, and either way a person has to look at it, so it raises.
    """
    frames = []
    have: dict[str, str] = {}
    if existing is not None and len(existing):
        old = existing.copy()
        old["date"] = pd.to_datetime(old["date"])
        frames.append(old)
        have = {
            d.strftime("%Y-%m-%d"): t for d, t in zip(old["date"], old[key_text].astype(str))
        }
    fresh = []
    for row in new_rows:
        day = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
        if day in have:
            if have[day] != str(row[key_text]):
                raise SourceError(
                    "the item for the week ending %s differs from the committed "
                    "one; look at both before replacing it" % day
                )
            continue
        have[day] = str(row[key_text])
        fresh.append(row)
    if fresh:
        new = pd.DataFrame(fresh)
        new["date"] = pd.to_datetime(new["date"])
        frames.append(new)
    if not frames:
        raise SourceError("no issue could be read and nothing is committed yet")
    merged = pd.concat(frames, ignore_index=True)
    return merged.sort_values("date").reset_index(drop=True)


class NgwuIssueIndex(Adapter):
    """Every NGWU issue EIA lists, from 2016, as the checklist for collection."""

    name = "eia_ngwu_issue_index"
    source = "U.S. Energy Information Administration, Natural Gas Weekly Update archive index"
    url = INDEX_URL
    page_url = LANDING_URL
    unit = "none, a list of issues"
    frequency = "weekly"
    method = "parsed"
    required_cols = ("date", "folder", "status")
    observation_column = "folder"
    min_rows = 400

    def fetch(self) -> pd.DataFrame:
        response = http_get(INDEX_URL)
        frame = parse_index(response.content)
        published = int((frame["status"] == "published").sum())
        silent = frame.loc[frame["status"] != "published", "date"].dt.strftime("%Y-%m-%d")
        self.note = (
            "%d issues listed from %s, dated by the folder in each link. Weeks EIA marks "
            "'No report released': %s. The links point into the archive robots.txt "
            "disallows and are recorded, never followed."
            % (published, INDEX_FIRST_YEAR, ", ".join(silent) or "none")
        )
        return frame


class NgwuInternationalWeekly(Adapter):
    """The NGWU international prices item, one row per issue read."""

    name = "eia_ngwu_international_weekly"
    source = "U.S. Energy Information Administration, Natural Gas Weekly Update, figures credited to Bloomberg Finance L.P."
    url = LANDING_URL
    page_url = LANDING_URL
    unit = "USD per MMBtu"
    frequency = "weekly"
    method = "parsed"
    required_cols = ("date", "east_asia_usd_mmbtu", "ttf_usd_mmbtu", "item_text")
    bounds = {
        "east_asia_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "ttf_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "prior_year_east_asia_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "prior_year_ttf_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
    }
    min_observations = {
        "east_asia_usd_mmbtu": 1,
        "ttf_usd_mmbtu": 1,
        "prior_year_east_asia_usd_mmbtu": 1,
        "prior_year_ttf_usd_mmbtu": 1,
    }
    observation_column = "east_asia_usd_mmbtu"

    COLUMNS = (
        "date", "release_date", "folder", "how_read", "page_url", "page_sha256",
        "east_asia_usd_mmbtu", "ttf_usd_mmbtu",
        "prior_year_week_ending", "prior_year_east_asia_usd_mmbtu", "prior_year_ttf_usd_mmbtu",
        "east_asia_printed", "ttf_printed", "prior_year_east_asia_printed", "prior_year_ttf_printed",
        "east_asia_change_printed", "ttf_change_printed",
        "east_asia_definition", "ttf_definition", "credit", "anomaly", "item_text",
    )

    def _row(self, payload: bytes, *, folder: str | None, how: str, url: str) -> dict[str, Any]:
        where = folder or url
        page = parse_ngwu_page(payload, where=where)
        values = parse_ngwu_item(page["item_text"], where=where)
        release = page["release_date"]
        derived_folder = "%04d/%02d_%02d" % (release.year, release.month, release.day)
        if folder is not None and folder != derived_folder:
            raise ParseError(
                "%s: the file is named for folder %s but the page prints release "
                "date %s" % (where, folder, release)
            )
        return {
            "date": page["week_ending"],
            "release_date": release.isoformat(),
            "folder": derived_folder,
            "how_read": how,
            "page_url": url,
            "page_sha256": _sha256(payload),
            "item_text": page["item_text"],
            **values,
        }

    def read_saved_issues(self) -> list[dict[str, Any]]:
        """Every issue the owner saved by hand, parsed. Raises on the first bad one."""
        rows = []
        directory = manual_dir()
        if not directory.exists():
            return rows
        for path in sorted(directory.glob("*/*.html")):
            folder = "%s/%s" % (path.parent.name, path.stem)
            if not re.fullmatch(r"\d{4}/\d{2}_\d{2}", folder):
                raise ParseError("%s is not named YYYY/MM_DD.html" % path)
            rows.append(
                self._row(
                    path.read_bytes(),
                    folder=folder,
                    how="saved by hand",
                    url=ARCHIVE_URL.format(folder=folder),
                )
            )
        return rows

    def fetch(self) -> pd.DataFrame:
        rows = self.read_saved_issues()
        response = http_get(LANDING_URL)
        rows.append(self._row(response.content, folder=None, how="landing page", url=LANDING_URL))
        existing = read_cache(self.name, directory=self.directory())
        merged = _merge_weekly(existing, rows, key_text="item_text")
        by_hand = int((merged["how_read"] == "saved by hand").sum())
        self.note = (
            "%d issue(s) read: %d saved by hand, %d from the landing page, which still "
            "serves the final issue. Every other issue is in the archive robots.txt "
            "disallows to code; see the manual step."
            % (len(merged), by_hand, len(merged) - by_hand)
        )
        return merged[list(self.COLUMNS)]


class WngsrInternationalWeekly(Adapter):
    """The WNGSR Supplement's JKM and TTF weekly averages, from 29 January 2026."""

    name = "eia_wngsr_international_weekly"
    source = "U.S. Energy Information Administration, Weekly Natural Gas Storage Report Supplement, figures credited to Bloomberg Finance L.P."
    url = SUPPLEMENT_PRICES_URL
    page_url = SUPPLEMENT_URL
    unit = "USD per MMBtu"
    frequency = "weekly"
    method = "parsed"
    required_cols = ("date", "jkm_usd_mmbtu", "ttf_usd_mmbtu", "item_text")
    bounds = {"jkm_usd_mmbtu": BOUNDS_LNG_USD_MMBTU, "ttf_usd_mmbtu": BOUNDS_LNG_USD_MMBTU}
    min_observations = {"jkm_usd_mmbtu": 1, "ttf_usd_mmbtu": 1}
    observation_column = "jkm_usd_mmbtu"

    COLUMNS = (
        "date", "release_date", "how_read", "page_url", "page_sha256",
        "jkm_usd_mmbtu", "ttf_usd_mmbtu", "jkm_printed", "ttf_printed",
        "jkm_change_printed", "ttf_change_printed", "jkm_definition", "ttf_definition",
        "credit", "anomaly", "item_text",
    )

    def fetch(self) -> pd.DataFrame:
        prices = http_get(SUPPLEMENT_PRICES_URL).content
        source = http_get(SUPPLEMENT_SOURCE_URL).content
        dates = http_get(SUPPLEMENT_DATES_URL).content
        row = parse_supplement(prices, source, dates)
        row["release_date"] = row["release_date"].isoformat()
        row["how_read"] = "current issue"
        row["page_url"] = SUPPLEMENT_URL
        row["page_sha256"] = _sha256(prices + source + dates)
        existing = read_cache(self.name, directory=self.directory())
        merged = _merge_weekly(existing, [row], key_text="item_text")
        self.note = (
            "%d week(s) collected, each while it was the current issue; the latest "
            "is the release of %s. Earlier issues sit in the archive robots.txt "
            "disallows to code; see the manual step." % (len(merged), row["release_date"])
        )
        return merged[list(self.COLUMNS)]


def main(argv: list[str] | None = None) -> int:
    """Run the three adapters and print what each recorded."""
    failed = 0
    for adapter in (NgwuIssueIndex(), NgwuInternationalWeekly(), WngsrInternationalWeekly()):
        try:
            entry = adapter.run()
        except Exception as exc:  # the manifest already carries the failure
            failed += 1
            print("FAILED %s: %s" % (adapter.name, exc))
        else:
            print(
                "ok     %s: %d observations, %s to %s"
                % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"])
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
