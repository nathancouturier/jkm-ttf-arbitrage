"""EIA's weekly JKM and TTF averages: the Natural Gas Weekly Update and its successor.

What the series is
------------------
From the issue of 16 September 2021, EIA's Natural Gas Weekly Update (NGWU)
carried the weekly average of an East Asia LNG price and of TTF, both in
USD/MMBtu, credited to Bloomberg Finance L.P., with the same week a year
earlier. The item first sat inside the spot prices item, then stood alone with
no heading, then under "International spot prices" and, from 14 July 2022,
"International futures prices". The product changed with the wording: East
Asia was a swap (for a named month, the prompt month, the balance of the month
or no month named) until July 2022 and a futures price after, front-month from
December 2022; TTF was a spot price with no product named for two weeks, then a
day-ahead price until July 2022, then a futures price.
The NGWU ended with the issue released on 22 January 2026 (week ending 21
January 2026), whose page says "This week is the final publication of the
Natural Gas Weekly Update". From 29 January 2026 EIA prints the same two
prices, from the same credited source but in new words, in the Weekly Natural
Gas Storage Report (WNGSR) Supplement. The two are kept as two series, because
nothing EIA publishes says the underlying Bloomberg series are the same, and
the change of product is a structural break either way.

What code may and may not fetch
-------------------------------
eia.gov's robots.txt disallows /naturalgas/weekly/archivenew_ngwu, where every
archived NGWU issue lives, and /*archive/, which covers the Supplement's
archive. Code therefore reads from eia.gov only:

    the NGWU landing page, which still serves the final issue
    the NGWU archive index, a single allowed page listing every issue
    the Supplement's current issue, three small files it is assembled from

Every other NGWU issue is read from the Internet Archive's earliest capture of
it (collect_from_internet_archive), saved privately into data/private/ngwu/
with its provenance logged; an issue it does not hold can be saved there by
hand. base.http_get enforces robots.txt, so a mistake here fails rather than
fetches.

How the item is read
--------------------
By sentence and by role, never by position. A clause naming one market and
stating a week's level gives that market's price, and the wording that
defines each price is stored for every week, with this study's reading of the
product in a basis column, so a change of definition is visible in the data
rather than hidden in a line. A market with no level or with two, a product
not named, or a year-earlier sentence that cannot be read stops the parse with
an error naming the issue: extending the parser is a code change with a test,
never a guess.

A figure printed with a typo is stored as printed in a *_printed column, next
to the value read from it, with the correction described in the anomaly column.
An issue that repeats an earlier issue's item word for word keeps its text and
has its values left empty (read_items).
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
    "NoItem",
    "ITEM_HEADINGS",
    "normalise_text",
    "split_sentences",
    "parse_ngwu_page",
    "parse_ngwu_item",
    "east_asia_basis",
    "ttf_basis",
    "read_items",
    "year_earlier_check",
    "parse_index",
    "parse_supplement",
    "NgwuIssueIndex",
    "NgwuInternationalWeekly",
    "WngsrInternationalWeekly",
    "internet_archive_captures",
    "capture_url",
    "collect_from_internet_archive",
]

LANDING_URL = "https://www.eia.gov/naturalgas/weekly/"
INDEX_URL = "https://www.eia.gov/naturalgas/weekly/includes/archive.php"
ARCHIVE_URL = "https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/{folder}/"
SUPPLEMENT_URL = "https://www.eia.gov/naturalgas/weekly/supplement/"
#: The Internet Archive's capture index. The archived issues are read from its
#: copies, never from eia.gov's archive path, which robots.txt disallows.
CDX_URL = (
    "https://web.archive.org/cdx/search/cdx?url=eia.gov/naturalgas/weekly/archivenew_ngwu/"
    "&matchType=prefix&output=json&fl=original,timestamp,statuscode,mimetype"
    "&filter=statuscode:200&collapse=urlkey&limit=20000"
)
#: Where the provenance of every issue read from the Internet Archive is logged,
#: one JSON object per line, beside the saved pages.
CAPTURES_LOG = "internet_archive_captures.jsonl"
SUPPLEMENT_PRICES_URL = SUPPLEMENT_URL + "content/bullets_lng_2.html"
SUPPLEMENT_SOURCE_URL = SUPPLEMENT_URL + "content/source_lng_2.html"
SUPPLEMENT_DATES_URL = SUPPLEMENT_URL + "content/release_dates.json"

#: The first year of the index kept. Shale era exports from Sabine Pass start in
#: February 2016, so nothing earlier can be part of this study.
INDEX_FIRST_YEAR = 2016

#: The credit every issue read so far carries, as the final issue prints it.
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


#: Two 2020 issue headers print a date without its comma ("April 16 2020").
_MONTH_DATE = r"([A-Z][a-z]+ \d{1,2},? \d{4})"


def _parse_long_date(text: str) -> date:
    return datetime.strptime(re.sub(r"(\d),? (\d{4})$", r"\1, \2", text.strip()), "%B %d, %Y").date()


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

#: The headings the item has carried, the latest first. EIA used "International
#: Spot Prices" from 17 February 2022, "International spot prices" from 14
#: April 2022 and "International futures prices" from 14 July 2022. From 16
#: September 2021 to 10 February 2022 the item has no heading of its own.
ITEM_HEADINGS = ("International futures prices", "International spot prices", "International Spot Prices")

_CREDIT_PRINTED = re.compile(r"Bloomberg Finance,? L\.P\.")

_PRICE = r"(\$\d[\d,]*(?:\.\d+)?[^\s,;]*)"

#: Ways the item states a week's level, in no particular order; the earliest
#: match in a clause is the level.
_LEVEL_PATTERNS = (
    re.compile(r"(?:to|at) a weekly average of " + _PRICE),
    re.compile(r"\baveraged " + _PRICE),
    re.compile(r"\b(?:flat|unchanged)\b[^$]*?\bat " + _PRICE),
    re.compile(r"^The weekly average \w+ to " + _PRICE),
)

#: Clauses that carry a price for one market but not the week's level.
_NOT_A_LEVEL = ("when it averaged",)

#: The item's opening summary ("International natural gas futures prices
#: decreased this report week."), which names no market and prints no price.
#: Only the first sentence can be the summary; a later one is a further sentence.
_INTRO = re.compile(r"^International natural gas (?:futures |spot )?prices?\b[^$]*$")

_CHANGE = re.compile(
    r"\b(?:increased|decreased|rose|fell|climbed|declined|dropped|gained|lost|remained|was|were|averaged)\b"
)

_PREFIXES = (
    re.compile(r"^According to Bloomberg Finance,? L\.P\.,? "),
    re.compile(r"^Bloomberg Finance,? L\.P\.,? reports(?: that)? "),
)

_MONTHS_SHORT = {"Jan.": "January", "Feb.": "February", "Mar.": "March", "Apr.": "April",
                 "Aug.": "August", "Sep.": "September", "Sept.": "September", "Oct.": "October",
                 "Nov.": "November", "Dec.": "December"}

_MONTHS_LONG = ("January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December")

_PRIOR_DATE = re.compile(r"week ending ((?:[A-Z][a-z]+\.?) \d{1,2}, \d{4})")


def _legs_named(clause: str) -> set[str]:
    named = set()
    if "East Asia" in clause:
        named.add("east_asia")
    if "TTF" in clause or "Title Transfer" in clause:
        named.add("ttf")
    return named


def _level(clause: str) -> tuple[str, int] | None:
    if any(marker in clause for marker in _NOT_A_LEVEL):
        return None
    best = None
    for pattern in _LEVEL_PATTERNS:
        match = pattern.search(clause)
        if match and (best is None or match.start(1) < best[1]):
            best = (match.group(1), match.start(1))
    return best


def _markets(clause: str, level: tuple[str, int] | None) -> set[str]:
    """The markets a clause is about: when it names both and states a level,
    the one named before the level ("..., bringing the TTF price back above
    the price in East Asia" is about TTF alone)."""
    named = _legs_named(clause)
    if len(named) == 2 and level is not None:
        before = _legs_named(clause[: level[1]])
        if len(before) == 1:
            return before
    return named


def _clauses(sentence: str) -> list[str]:
    """A sentence that states both markets' levels, split into one clause each."""
    named = _legs_named(sentence)
    if named == {"east_asia", "ttf"}:
        cut = re.search(r", and (?=[^,]*(?:Title Transfer|TTF))", sentence)
        if cut and _level(sentence[: cut.start()]) and _level(sentence[cut.end():]):
            return [sentence[: cut.start()], sentence[cut.end():]]
    return [sentence]


def _definition(clause: str) -> str:
    text = clause
    for prefix in _PREFIXES:
        text = prefix.sub("", text)
    match = _CHANGE.search(text)
    return (text[: match.start()] if match else text).strip(" ,")


#: The words that lead from a change to the level it reached.
_TO_LEVEL = re.compile(r"\s*(?:(?:to|at) a weekly average of|averaged|at|to)$")


def _change(clause: str, printed: str) -> str | None:
    """The change the clause prints before its level ("decreased 47 cents"), if any."""
    match = _CHANGE.search(clause)
    end = clause.find(printed)
    if not match or match.start() >= end:
        return None
    words = _TO_LEVEL.sub("", clause[match.start(): end].strip(" ,")).strip(" ,")
    return words or None


def east_asia_basis(definition: str) -> str:
    """The product the East Asia sentence names, in this study's words."""
    d = definition.lower()
    if "front-month futures" in d:
        return "front-month futures"
    if "futures" in d:
        return "futures, month not named"
    if "swap" in d:
        if "balance of" in d or "rest of" in d:
            return "swap, balance of the month"
        if "prompt month" in d:
            return "swap, prompt month"
        if any(re.search(r"\b%s\b" % month, definition) for month in _MONTHS_LONG):
            return "swap, delivery month named"
        return "swap, month not named"
    raise ParseError("an East Asia price whose product is not named: %r" % (definition,))


def ttf_basis(definition: str) -> str:
    """The product the TTF sentence names, in this study's words."""
    d = definition.lower()
    if "day-ahead" in d:
        return "day-ahead"
    if "futures" in d:
        return "futures, month not named"
    if "spot market" in d or d.endswith("prices"):
        return "spot, product not named"
    raise ParseError("a TTF price whose product is not named: %r" % (definition,))


def _prior_year(sentence: str, *, where: str) -> dict[str, Any]:
    date_match = _PRIOR_DATE.search(sentence)
    if not date_match:
        raise ParseError("%s: a same week last year sentence with no week ending: %r" % (where, sentence))
    printed_date = date_match.group(1)
    month = printed_date.split(" ")[0]
    long_date = printed_date.replace(month, _MONTHS_SHORT.get(month, month), 1)
    prices = [(m.group(1), m.start()) for m in re.finditer(_PRICE, sentence)]
    if len(prices) != 2:
        raise ParseError("%s: a same week last year sentence with %d prices: %r" % (where, len(prices), sentence))
    asia_at, ttf_at = sentence.find("East Asia"), sentence.find("TTF")
    if asia_at < 0 or ttf_at < 0:
        raise ParseError("%s: a same week last year sentence that does not name both markets: %r" % (where, sentence))
    if "respectively" in sentence:
        first, second = ("asia", "ttf") if asia_at < ttf_at else ("ttf", "asia")
        named = {first: prices[0][0], second: prices[1][0]}
    else:
        # "$X in East Asia and $Y at TTF": each price precedes its market.
        named = {}
        for printed, at in prices:
            nxt = min((p for p in (asia_at, ttf_at) if p > at), default=None)
            if nxt is None:
                raise ParseError("%s: a price in the same week last year sentence names no market: %r" % (where, sentence))
            named["asia" if nxt == asia_at else "ttf"] = printed
        if set(named) != {"asia", "ttf"}:
            raise ParseError("%s: the same week last year prices do not name both markets: %r" % (where, sentence))
    return {
        "week_ending": _parse_long_date(long_date),
        "asia": read_price(named["asia"]),
        "ttf": read_price(named["ttf"]),
    }


def parse_ngwu_item(item_text: str, *, where: str) -> dict[str, Any]:
    """The values, wordings and anomalies of one NGWU international prices item.

    The item has been worded in many ways since it began in September 2021, so
    it is read by role, not by template: each clause naming one market and
    stating a week's level gives that market's price (a clause naming both
    belongs to the one named before its level), a following clause that
    only restates "the weekly average" belongs to the market named before it,
    and the same week last year sentence gives the year-earlier prices in
    whichever order it names the markets. where names the issue in error
    messages. Raises ParseError when a market has no level or two, or when a
    product or a year-earlier sentence cannot be read.
    """
    body = item_text
    for heading in ITEM_HEADINGS:
        if body.startswith(heading):
            body = body[len(heading):].lstrip(" :")
            break

    legs: dict[str, dict[str, Any]] = {}
    headline: dict[str, str] = {}
    prior: dict[str, Any] | None = None
    extra: list[str] = []
    notes: list[str] = []
    last_leg: str | None = None

    for position, sentence in enumerate(split_sentences(body)):
        if "same week last year" in sentence:
            if prior is not None:
                raise ParseError("%s: two same week last year sentences" % (where,))
            prior = _prior_year(sentence, where=where)
            for name, price in (("prior year east_asia", prior["asia"]), ("prior year ttf", prior["ttf"])):
                if price.note:
                    notes.append("%s %s" % (name, price.note))
            continue
        used = False
        for clause in _clauses(sentence):
            level = _level(clause)
            named = _markets(clause, level)
            if len(named) == 1:
                leg = next(iter(named))
                if leg not in headline:
                    headline[leg] = clause
                    used = True
                last_leg = leg
                if level is not None:
                    if leg in legs:
                        raise ParseError("%s: two %s levels: %r" % (where, leg, clause))
                    legs[leg] = {"clause": clause, "price": read_price(level[0]), "headline": headline[leg]}
                    used = True
            elif not named and level is not None and clause.startswith("The weekly average"):
                if last_leg is None or last_leg in legs:
                    raise ParseError("%s: a weekly average that names no market: %r" % (where, clause))
                legs[last_leg] = {"clause": clause, "price": read_price(level[0]), "headline": headline[last_leg]}
                used = True
        if not used and not (position == 0 and _INTRO.match(sentence) and not _legs_named(sentence)):
            extra.append(sentence)

    for required in ("east_asia", "ttf"):
        if required not in legs:
            raise ParseError("%s: no %s level in the item" % (where, required))

    out: dict[str, Any] = {}
    for leg in ("east_asia", "ttf"):
        price = legs[leg]["price"]
        if price.note:
            notes.append("%s %s" % (leg, price.note))
        definition = _definition(legs[leg]["headline"])
        out[leg + "_usd_mmbtu"] = price.value
        out[leg + "_printed"] = price.printed
        out[leg + "_change_printed"] = _change(legs[leg]["clause"], price.printed)
        out[leg + "_definition"] = definition
        out[leg + "_basis"] = east_asia_basis(definition) if leg == "east_asia" else ttf_basis(definition)

    if extra:
        notes.append("%d further sentence(s) not about the two prices" % len(extra))
    credit = _CREDIT_PRINTED.search(item_text)
    if not credit:
        notes.append("no credit to %s in the item" % CREDIT)

    out.update({
        "prior_year_week_ending": prior["week_ending"].isoformat() if prior else None,
        "prior_year_east_asia_usd_mmbtu": prior["asia"].value if prior else None,
        "prior_year_ttf_usd_mmbtu": prior["ttf"].value if prior else None,
        "prior_year_east_asia_printed": prior["asia"].printed if prior else None,
        "prior_year_ttf_printed": prior["ttf"].printed if prior else None,
        "credit": credit.group(0) if credit else None,
        "anomaly": "; ".join(notes) if notes else None,
    })
    return out


class NoItem(ParseError):
    """An issue that carries no international prices item."""


def _find_item(soup: BeautifulSoup) -> Any:
    items = []
    for strong in soup.find_all(["strong", "b"]):
        text = normalise_text(strong.get_text())
        if any(text.startswith(h) for h in ITEM_HEADINGS):
            container = strong.find_parent("li") or strong.find_parent("p")
            if container is not None and container not in items:
                items.append(container)
    if len(items) > 1:
        raise ParseError("%d international prices items on the page" % len(items))
    if items:
        return items[0]
    best = None
    for element in soup.find_all(["li", "p"]):
        text = normalise_text(element.get_text(" "))
        if "East Asia" in text and "MMBtu" in text and ("TTF" in text or "Title Transfer" in text):
            if best is None or len(text) < len(normalise_text(best.get_text(" "))):
                best = element
    return best


def parse_ngwu_page(html: str | bytes, *, where: str) -> dict[str, Any]:
    """The dates and the international prices item of one NGWU issue page.

    Returns the week ending and release date printed in the report header and
    the item's text, normalised. The item is found by its heading or, before
    it had one, as the smallest list item naming East Asia and TTF with a price
    in USD/MMBtu. Raises NoItem when the issue has no such item, and
    ParseError when the dates are missing or the item is ambiguous.
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
    try:
        item = _find_item(soup)
    except ParseError as exc:
        raise ParseError("%s: %s" % (where, exc)) from None
    if item is None:
        raise NoItem("%s: no international prices item on the page" % (where,))
    return {
        "week_ending": _parse_long_date(week.group(1)),
        "release_date": _parse_long_date(release.group(1)),
        "item_text": normalise_text(item.get_text(" ")),
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


# --------------------------------------------------------------------------
# Checks that need more than one issue
# --------------------------------------------------------------------------

#: The four figures an NGWU item gives, emptied when the item is not this week's.
VALUE_COLUMNS = (
    "east_asia_usd_mmbtu", "ttf_usd_mmbtu",
    "prior_year_east_asia_usd_mmbtu", "prior_year_ttf_usd_mmbtu",
)

#: Wednesday to Wednesday: the same week a year earlier ends 364 days before.
YEAR_EARLIER_DAYS = 364


def read_items(frame: pd.DataFrame) -> pd.DataFrame:
    """Every NGWU row read again from its stored item text, then checked against the others.

    The values, wordings, bases and anomalies of each row follow from its
    item_text alone, so they are derived again on every run, which keeps a
    committed row and a fresh one identical. Two checks need the other rows:

    * an item that repeats an earlier issue's item word for word carries that
      issue's figures, not this week's, so its four values are left empty;
    * a year-earlier week that does not end 364 days before this week's end is
      flagged, and kept as printed.
    """
    out = frame.copy().sort_values("date").reset_index(drop=True)
    for column in out.columns:
        if column != "date" and column not in VALUE_COLUMNS:
            out[column] = out[column].astype(object)
    seen: dict[str, str] = {}
    for i, row in out.iterrows():
        values = parse_ngwu_item(row["item_text"], where=str(row["folder"]))
        anomaly = values.pop("anomaly")
        notes = [anomaly] if anomaly else []
        week = pd.Timestamp(row["date"]).date()
        if values["prior_year_week_ending"] is not None:
            printed = date.fromisoformat(values["prior_year_week_ending"])
            days = (week - printed).days
            if days != YEAR_EARLIER_DAYS:
                notes.append(
                    "the same week last year is printed as the week ending %s, %d days "
                    "before this week's end; the week a year earlier ended %s"
                    % (printed, days, week - timedelta(days=YEAR_EARLIER_DAYS))
                )
        text = str(row["item_text"])
        if text in seen:
            notes.append(
                "the item repeats the one of issue %s word for word, so its figures are "
                "that issue's; the four values are left empty" % seen[text]
            )
            for column in VALUE_COLUMNS:
                values[column] = None
        else:
            seen[text] = str(row["folder"])
        for column, value in values.items():
            out.at[i, column] = value
        out.at[i, "east_asia_basis"] = east_asia_basis(values["east_asia_definition"])
        out.at[i, "ttf_basis"] = ttf_basis(values["ttf_definition"])
        out.at[i, "anomaly"] = "; ".join(notes) if notes else None
    for column in VALUE_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def year_earlier_check(frame: pd.DataFrame) -> pd.DataFrame:
    """Each week's figure as its own issue printed it, against the same week a year later.

    Weeks are matched on the calendar (the week ending 364 days before the
    later issue's), never on the date the later issue prints, which is wrong
    once. One row per market and pair of issues where the later issue prints a
    figure; difference is the year-later figure less the original, empty when
    the original week has no value (the two repeated issues). A difference across
    a change of basis is a definition break; one within a basis is a revision
    or an error, and the bases are given so a reader can tell which.
    """
    by_week = {pd.Timestamp(d).date(): row for d, row in zip(frame["date"], frame.to_dict("records"))}
    rows = []
    for later_week, later in sorted(by_week.items()):
        earlier = by_week.get(later_week - timedelta(days=YEAR_EARLIER_DAYS))
        if earlier is None:
            continue
        for leg in ("east_asia", "ttf"):
            then = earlier[leg + "_usd_mmbtu"]
            again = later["prior_year_%s_usd_mmbtu" % leg]
            if pd.isna(again):
                continue
            rows.append({
                "week_ending": pd.Timestamp(earlier["date"]).date().isoformat(),
                "market": leg,
                "issue": earlier["folder"],
                "value": then,
                "basis": earlier[leg + "_basis"],
                "issue_year_later": later["folder"],
                "value_year_later": again,
                "basis_year_later": later[leg + "_basis"],
                "difference": round(again - then, 2) if not pd.isna(then) else None,
            })
    columns = ["week_ending", "market", "issue", "value", "basis", "issue_year_later",
               "value_year_later", "basis_year_later", "difference"]
    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------------------------------
# Archived issues, from the Internet Archive's copies
# --------------------------------------------------------------------------

_CAPTURED_ISSUE = re.compile(
    r"archivenew_ngwu/(\d{4})/(\d{2})_(\d{2})/?(?:index\.(?:php|html?))?$"
)


def internet_archive_captures(cdx_rows: list[list[str]]) -> dict[str, tuple[str, str]]:
    """folder -> (timestamp, original URL) of the earliest HTML capture of each issue.

    cdx_rows is the Internet Archive's CDX answer: a header row, then rows of
    original URL, timestamp, status code and media type. An issue is often
    captured under several addresses (with or without a trailing slash,
    index.php, http or https); the earliest capture of any of them is the
    closest to the page as EIA first published it.
    """
    if not cdx_rows or cdx_rows[0][:4] != ["original", "timestamp", "statuscode", "mimetype"]:
        raise SourceError("the capture index does not start with the expected header")
    best: dict[str, tuple[str, str]] = {}
    for original, timestamp, status, mimetype in (row[:4] for row in cdx_rows[1:]):
        if status != "200" or "html" not in mimetype:
            continue
        match = _CAPTURED_ISSUE.search(original.split("?")[0])
        if not match:
            continue
        folder = "%s/%s_%s" % match.groups()
        if folder not in best or timestamp < best[folder][0]:
            best[folder] = (timestamp, original)
    return best


def capture_url(timestamp: str, original: str) -> str:
    """The address of a capture's original bytes, without the archive's frame."""
    return "https://web.archive.org/web/%sid_/%s" % (timestamp, original)


def _read_captures_log() -> dict[str, dict[str, Any]]:
    path = manual_dir() / CAPTURES_LOG
    if not path.exists():
        return {}
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            records[record["folder"]] = record
    return records


def collect_from_internet_archive(*, delay: float = 4.0, limit: int | None = None) -> dict[str, Any]:
    """Save every listed issue not yet saved, from the Internet Archive's earliest capture.

    The list of issues is the committed index. Each page is saved as
    data/private/ngwu/YYYY/MM_DD.html, where the adapter reads saved issues,
    and its provenance is appended to the captures log. The batch stops at
    the first answer that is not a non empty NGWU page.
    """
    index = read_cache("eia_ngwu_issue_index")
    if index is None:
        raise SourceError("the issue index is not committed; run the index first")
    folders = [f for f in index["folder"].dropna().astype(str) if re.fullmatch(r"\d{4}/\d{2}_\d{2}", f)]
    directory = manual_dir()
    directory.mkdir(parents=True, exist_ok=True)
    wanted = [f for f in folders if not (directory / (f + ".html")).exists()]
    if limit is not None:
        wanted = wanted[:limit]
    summary: dict[str, Any] = {"listed": len(folders), "wanted": len(wanted), "saved": 0, "not_captured": []}
    if not wanted:
        return summary
    captures = internet_archive_captures(http_get(CDX_URL, timeout=120).json())
    for folder in wanted:
        if folder not in captures:
            summary["not_captured"].append(folder)
            continue
        timestamp, original = captures[folder]
        address = capture_url(timestamp, original)
        response = http_get(address, timeout=60, delay=delay)
        payload = response.content
        if response.status_code != 200 or not payload or b"Natural Gas Weekly Update" not in payload:
            raise SourceError(
                "the capture of %s at %s answered HTTP %d with %d bytes that are not an "
                "NGWU page; the batch stopped there after %d saved"
                % (folder, address, response.status_code, len(payload), summary["saved"])
            )
        target = directory / (folder + ".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        record = {
            "folder": folder,
            "capture_timestamp": timestamp,
            "original_url": original,
            "capture_url": address,
            "fetched_at": base.utc_now_iso(),
            "bytes": len(payload),
            "sha256": _sha256(payload),
        }
        with open(directory / CAPTURES_LOG, "a", encoding="utf-8") as log:
            log.write(json.dumps(record) + "\n")
        summary["saved"] += 1
    return summary


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
        "east_asia_definition", "ttf_definition", "east_asia_basis", "ttf_basis",
        "credit", "anomaly", "item_text",
    )

    def __init__(self) -> None:
        super().__init__()
        #: Saved issues that carry no international prices item, by folder.
        self.without_item: list[str] = []

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
        """Every saved issue that carries the item, parsed. Raises on the first bad one.

        An issue with no international prices item (every issue before
        September 2021, and the one of 27 March 2025) gives no row; its folder
        is listed in without_item.
        """
        rows = []
        self.without_item = []
        directory = manual_dir()
        if not directory.exists():
            return rows
        captured = _read_captures_log()
        for path in sorted(directory.glob("*/*.html")):
            folder = "%s/%s" % (path.parent.name, path.stem)
            if not re.fullmatch(r"\d{4}/\d{2}_\d{2}", folder):
                raise ParseError("%s is not named YYYY/MM_DD.html" % path)
            payload = path.read_bytes()
            record = captured.get(folder)
            if record is not None and record["sha256"] == _sha256(payload):
                how = "Internet Archive capture of %s" % record["capture_timestamp"]
                url = record["capture_url"]
            else:
                how, url = "saved by hand", ARCHIVE_URL.format(folder=folder)
            try:
                rows.append(self._row(payload, folder=folder, how=how, url=url))
            except NoItem:
                self.without_item.append(folder)
        return rows

    def fetch(self) -> pd.DataFrame:
        rows = self.read_saved_issues()
        response = http_get(LANDING_URL)
        rows.append(self._row(response.content, folder=None, how="landing page", url=LANDING_URL))
        existing = read_cache(self.name, directory=self.directory())
        merged = read_items(_merge_weekly(existing, rows, key_text="item_text"))
        how = merged["how_read"].astype(str)
        captures = int(how.str.startswith("Internet Archive capture").sum())
        by_hand = int((how == "saved by hand").sum())
        landing = int((how == "landing page").sum())
        self.note = (
            "%d issue(s) carry the item: %d read from the Internet Archive's earliest "
            "capture, %d saved by hand, %d from the landing page, which still serves the "
            "final issue. %s Code never requests the archive on eia.gov, which robots.txt "
            "disallows." % (len(merged), captures, by_hand, landing, self._without_item_note(merged))
        )
        return merged[list(self.COLUMNS)]

    def _without_item_note(self, merged: pd.DataFrame) -> str:
        """Which listed issues carry no item, from the committed index and rows.

        Read from what is committed rather than from the saved pages, so the
        note is the same on a machine that holds none of them.
        """
        index = read_cache("eia_ngwu_issue_index")
        if index is None:
            return "The issue index is not committed, so issues without the item are not counted."
        listed = sorted(index["folder"].dropna().astype(str))
        have = set(merged["folder"].astype(str))
        first = min(have)
        before = [f for f in listed if f < first]
        silent = [f for f in listed if f > first and f not in have]
        return (
            "Of the %d issues the index lists from %d, the %d before %s carry no "
            "international prices item, and %s." % (
                len(listed), INDEX_FIRST_YEAR, len(before), first,
                ("neither does " + ", ".join(silent)) if silent else "every later one does",
            )
        )


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
    """Run the three adapters and print what each recorded.

    With --from-internet-archive, first save every listed issue not yet saved,
    from the Internet Archive's copies.
    """
    if argv and "--from-internet-archive" in argv:
        summary = collect_from_internet_archive()
        print(
            "internet archive: %d listed, %d wanted, %d saved, not captured: %s"
            % (summary["listed"], summary["wanted"], summary["saved"], ", ".join(summary["not_captured"]) or "none")
        )
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
