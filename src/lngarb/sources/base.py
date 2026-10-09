"""Shared plumbing for every data source adapter.

This module is the contract the rest of the data layer depends on. It owns five
things and nothing else:

    where files live          REPO_ROOT, DATA, CACHE, SEED, FIXTURES, PRIVATE,
                              MANIFEST
    how we talk to the web    USER_AGENT, user_agent_for, check_robots,
                              http_get, http_head, SourceError
    how a frame is checked    validate_frame, observation_count, find_gaps
    how a result is recorded  read_cache, write_cache, manifest_read,
                              manifest_upsert
    what an adapter is        Adapter

The rules it enforces are the data rules in docs/methodology.md:

  * never invent a value. A failed fetch keeps the previous cache and is written
    into the manifest with status "failed". A missing observation stays NaN in a
    cache and null in JSON, never zero.
  * validate on write. Monotonic dates, no duplicates, the declared bounds, a
    row count that did not shrink against the cache already on disk, and a
    declared minimum number of real observations in every value column, so a
    source that starts printing a dash where it used to print a price fails
    loudly instead of caching a column of nothing.
  * be polite. A delay before every request, exponential backoff on 429, 5xx and
    connection errors, one request per file.
  * respect robots.txt. Every request is checked against the host's robots.txt
    first, with the matching rules of RFC 9309, and a disallowed URL is never
    requested. A source that can only be read by hand is a manual step.

This module is adapted from the same plumbing in the sibling repository
crack-spread-study, which paid for most of the lessons written into it. Two of
them bear repeating because they are about hosts this project also reads:

1. NEVER PROBE WITH HEAD. eia.gov answers HTTP 503 to a HEAD request and HTTP
   200 to a GET of the same URL. A liveness check with HEAD reports the source
   as down when it is up, so http_head refuses that host.

2. THE USER AGENT IS NOT ONE STRING. Some hosts refuse an obvious script user agent
   and at least one public data host resets the connection when sent a browser
   string. The host to user agent map lives here, once, with the measurement
   behind each exception written next to it.

Nothing here fetches anything by itself. The adapters do that.
"""

from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import requests

from .. import manual_steps
from ..config import FREQUENCIES, METHODS, SOURCES

__all__ = [
    "REPO_ROOT",
    "DATA",
    "CACHE",
    "SEED",
    "FIXTURES",
    "PRIVATE",
    "MANIFEST",
    "USER_AGENT",
    "PROJECT_USER_AGENT",
    "USER_AGENT_BY_HOST",
    "HEAD_IS_BROKEN_ON",
    "user_agent_for",
    "SourceError",
    "RobotsDisallowed",
    "parse_robots",
    "robots_allows",
    "check_robots",
    "http_get",
    "http_head",
    "utc_now_iso",
    "read_cache",
    "write_cache",
    "find_gaps",
    "missing_business_days",
    "observation_count",
    "validate_frame",
    "manifest_read",
    "manifest_upsert",
    "manifest_remove",
    "Adapter",
    "MANIFEST_SCHEMA_VERSION",
    "STATUS_VALUES",
    "ENTRY_KEYS",
    "DIRECTORIES",
]


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

# This file is <repo>/src/lngarb/sources/base.py, so the repo root is three
# parents up from its directory: sources -> lngarb -> src -> repo root.
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

DATA: Path = REPO_ROOT / "data"
CACHE: Path = DATA / "cache"
SEED: Path = DATA / "seed"
FIXTURES: Path = DATA / "fixtures"
#: Gitignored, never committed, never deployed. A cache whose terms forbid
#: redistribution lives here, and so do the files the owner collects by hand.
PRIVATE: Path = DATA / "private"
MANIFEST: Path = DATA / "manifest.json"

#: The three places an adapter may write, and the meaning of each. They are kept
#: apart on purpose: data/cache is reserved for what a source actually served, so
#: a hand seeded file does not get to sit there and look like a record of the
#: market, and a file nobody is allowed to republish does not get to sit there
#: and be committed by accident.
DIRECTORIES = ("cache", "seed", "private")


def _verify_repo_root(root: Path) -> None:
    """Fail loudly if the parents walk did not land on the repo root.

    A wrong root would silently write caches into some other directory, so this
    is checked at import time rather than left to be discovered later. The
    markers are files every clean checkout carries.
    """
    markers = ("pyproject.toml", ".gitignore")
    missing = [m for m in markers if not (root / m).exists()]
    if missing:
        raise RuntimeError(
            "REPO_ROOT resolved to %s which does not look like the repository "
            "root, missing %s. base.py must stay at src/lngarb/sources/base.py."
            % (root, ", ".join(missing))
        )


_verify_repo_root(REPO_ROOT)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

# A real, currently shipping desktop browser string. Several sources refuse an
# obvious script user agent. Refresh the version from time to time, a very old
# string is itself a signal.
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

#: A named bot token, the more correct thing to send to a public data API than a
#: browser string pretending to be a person.
PROJECT_USER_AGENT: str = (
    "jkm-ttf-arbitrage/0.1 "
    "(+https://github.com/nathancouturier/jkm-ttf-arbitrage)"
)

# Hosts that need something other than the browser string, matched on the host
# and on any parent domain. Each entry carries the observation behind it in
# docs/sources.md.
USER_AGENT_BY_HOST: Mapping[str, str] = {}

# Hosts that answer HTTP 503 to HEAD and HTTP 200 to GET on the same URL. A
# liveness probe with HEAD against one of these reports the source as down when
# it is up, the most expensive kind of false alarm in a pipeline whose job is to
# tell the truth about whether a source answered. http_head refuses them.
HEAD_IS_BROKEN_ON: frozenset[str] = frozenset({"eia.gov", "www.eia.gov"})

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Connection": "close",
}

# Retried: too many requests, request timeout, and anything the server side
# broke. Everything else in the 4xx range is a permanent answer, retrying a 403
# or a 404 only wastes the remote host's time.
RETRY_STATUS: frozenset[int] = frozenset(
    {408, 425, 429, 500, 502, 503, 504, 509, 520, 522, 524}
)


class SourceError(Exception):
    """A data source could not be read, or gave back something unusable."""


class RobotsDisallowed(SourceError):
    """robots.txt asks automated clients not to fetch this URL, so nothing was sent."""


def _host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


# --------------------------------------------------------------------------
# robots.txt, with the matching rules of RFC 9309
# --------------------------------------------------------------------------
#
# Python's urllib.robotparser applies the first matching line rather than the
# longest, and does not understand "*" inside a path. eia.gov's file opens with
# "Allow: /", so robotparser answers "allowed" for its disallowed weekly archive.
# A pipeline that trusted it would crawl pages the publisher asked it not to
# while believing it had checked. The parser below implements the standard: the
# group for the most specific matching product token, otherwise "*"; within it
# the longest matching path pattern wins; an Allow wins a tie; "*" matches any
# run of characters and a final "$" anchors the end.

#: host -> parsed rules, filled on first use, one robots.txt request per host
_ROBOTS_CACHE: dict[str, list[tuple[bool, str]]] = {}


def parse_robots(text: str, product_token: str) -> list[tuple[bool, str]]:
    """The (allow, pattern) rules that apply to product_token, from robots.txt text.

    The group whose user-agent line names the product token applies if there is
    one; otherwise the "*" group; otherwise nothing is disallowed. Several
    groups naming the same product token are merged, as RFC 9309 section 2.2.1 asks.
    """
    token = product_token.lower()
    groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
    names: list[str] = []
    rules: list[tuple[bool, str]] = []
    in_rules = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                groups.append((names, rules))
                names, rules, in_rules = [], [], False
            names.append(value.lower())
        elif key in ("allow", "disallow"):
            in_rules = True
            if value:
                rules.append((key == "allow", value))
    if names:
        groups.append((names, rules))

    specific = [r for names, r in groups if token in names]
    if specific:
        return [rule for r in specific for rule in r]
    wildcard = [r for names, r in groups if "*" in names]
    return [rule for r in wildcard for rule in r]


def _pattern_matches(pattern: str, path: str) -> bool:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    pieces = body.split("*")
    if len(pieces) == 1:
        return path == body if anchored else path.startswith(body)
    if not path.startswith(pieces[0]):
        return False
    position = len(pieces[0])
    # Every piece between two stars, leftmost first, which is never worse
    # than any other placement for what follows.
    for piece in pieces[1:-1]:
        found = path.find(piece, position)
        if found == -1:
            return False
        position = found + len(piece)
    last = pieces[-1]
    if anchored:
        return path.endswith(last) and len(path) - len(last) >= position
    return path.find(last, position) != -1


def robots_allows(rules: Sequence[tuple[bool, str]], url: str) -> bool:
    """Whether the rules allow the URL's path and query, longest match winning."""
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    best_length = -1
    best_allow = True
    for allow, pattern in rules:
        if _pattern_matches(pattern, path):
            length = len(pattern)
            if length > best_length or (length == best_length and allow):
                best_length = length
                best_allow = allow
    return best_allow


def _product_token(user_agent: str) -> str:
    return user_agent.split("/", 1)[0].strip()


def check_robots(url: str, user_agent: str) -> None:
    """Raise RobotsDisallowed when the host's robots.txt disallows this URL.

    robots.txt itself is always fetchable. A robots.txt that answers 4xx means
    no rules; one that cannot be read at all, a 5xx or a network failure, is
    treated as a complete disallow, as RFC 9309 section 2.3.1.4 asks, and the
    fetch is refused rather than attempted.
    """
    parts = urlsplit(url)
    if parts.path == "/robots.txt":
        return
    host = (parts.hostname or "").lower()
    key = "%s://%s|%s" % (parts.scheme, host, _product_token(user_agent).lower())
    if key not in _ROBOTS_CACHE:
        robots_url = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
        try:
            response = requests.get(
                robots_url,
                headers={**DEFAULT_HEADERS, "User-Agent": user_agent},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RobotsDisallowed(
                "robots.txt for %s could not be read (%s), so nothing is fetched "
                "from that host" % (host, type(exc).__name__)
            ) from exc
        if response.status_code >= 500:
            raise RobotsDisallowed(
                "robots.txt for %s answered HTTP %d, which counts as a complete "
                "disallow" % (host, response.status_code)
            )
        text = response.text if response.status_code < 400 else ""
        _ROBOTS_CACHE[key] = parse_robots(text, _product_token(user_agent))
    if not robots_allows(_ROBOTS_CACHE[key], url):
        raise RobotsDisallowed(
            "robots.txt on %s disallows %s for automated clients. Nothing was "
            "requested. If this source is needed, it is a manual step."
            % (host, url)
        )


def _host_matches(host: str, registered: str) -> bool:
    """True when host is the registered host or a subdomain of it."""
    return host == registered or host.endswith("." + registered)


def user_agent_for(url: str) -> str:
    """The user agent this project sends to that URL's host.

    The browser string everywhere except the hosts in USER_AGENT_BY_HOST.
    Adapters do not need to call this, http_get applies it, but it is exported
    so a test can assert on it without a network call.
    """
    host = _host_of(url)
    for registered, value in USER_AGENT_BY_HOST.items():
        if _host_matches(host, registered):
            return value
    return USER_AGENT


def http_get(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30,
    retries: int = 4,
    backoff: float = 1.7,
    delay: float = 1.5,
) -> requests.Response:
    """GET a URL politely, with retries, and return the response.

    Args:
        url: the absolute URL to fetch.
        headers: extra headers, merged over the defaults. A User-Agent given
            here wins over the per host choice.
        timeout: per attempt timeout in seconds.
        retries: retries after the first attempt, so retries=4 means up to five
            attempts in total.
        backoff: multiplier for the wait between attempts. Attempt n waits
            delay * backoff ** n seconds, honouring Retry-After when sent.
        delay: the polite pause taken before every attempt, including the first.

    Returns:
        The successful requests.Response, status 200 to 399.

    Raises:
        SourceError: after the final retry, or at once on a status that will not
            change if we ask again. The message carries the URL and the status
            or exception seen.
    """
    merged: dict[str, str] = dict(DEFAULT_HEADERS)
    merged["User-Agent"] = user_agent_for(url)
    if headers:
        merged.update(headers)

    # Before anything is sent. Raises RobotsDisallowed, a SourceError, so an
    # adapter records a disallowed URL as a failure rather than fetching it.
    check_robots(url, merged["User-Agent"])

    attempts = max(1, int(retries) + 1)
    last_problem = "no attempt was made"

    for attempt in range(attempts):
        if delay > 0:
            time.sleep(delay)
        try:
            response = requests.get(url, headers=merged, timeout=timeout)
        except requests.RequestException as exc:
            last_problem = "%s: %s" % (type(exc).__name__, exc)
        else:
            if response.status_code < 400:
                return response
            last_problem = "HTTP %d" % response.status_code
            if response.status_code not in RETRY_STATUS:
                raise SourceError(
                    "GET %s failed with HTTP %d, not retryable"
                    % (url, response.status_code)
                )
            wait_hint = response.headers.get("Retry-After")
            if wait_hint:
                try:
                    time.sleep(min(60.0, float(wait_hint)))
                except (TypeError, ValueError):
                    pass

        if attempt < attempts - 1:
            time.sleep(max(0.0, delay) * (backoff ** (attempt + 1)))

    raise SourceError(
        "GET %s failed after %d attempts, last problem %s"
        % (url, attempts, last_problem)
    )


def http_head(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30,
    delay: float = 1.5,
) -> requests.Response:
    """HEAD a URL, for a size or a last modified date. One attempt, no retries.

    Refuses the hosts in HEAD_IS_BROKEN_ON rather than returning their 503,
    because a 503 from those hosts means nothing at all. Use http_get there and
    read the headers off the real response.

    Raises:
        SourceError: on a refused host, on a status of 400 or more, or on a
            connection failure.
    """
    host = _host_of(url)
    for registered in HEAD_IS_BROKEN_ON:
        if _host_matches(host, registered):
            raise SourceError(
                "refusing to HEAD %s. %s answers HTTP 503 to HEAD and HTTP 200 "
                "to GET on the same URL, so a HEAD probe reports the source as "
                "down when it is up. Use http_get." % (url, registered)
            )

    merged: dict[str, str] = dict(DEFAULT_HEADERS)
    merged["User-Agent"] = user_agent_for(url)
    if headers:
        merged.update(headers)
    check_robots(url, merged["User-Agent"])

    if delay > 0:
        time.sleep(delay)
    try:
        response = requests.head(url, headers=merged, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        raise SourceError(
            "HEAD %s failed, %s: %s" % (url, type(exc).__name__, exc)
        ) from exc
    if response.status_code >= 400:
        raise SourceError("HEAD %s returned HTTP %d" % (url, response.status_code))
    return response


def utc_now_iso() -> str:
    """Current UTC time as 2026-09-30T08:04:11Z, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# Cache read and write
# --------------------------------------------------------------------------

def _cache_path(name: str, *, directory: str = "cache") -> Path:
    """Path of a data file, by series name and directory."""
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("cache name %r is not a plain series name" % (name,))
    if directory not in DIRECTORIES:
        raise ValueError(
            "directory %r is not one of %s" % (directory, ", ".join(DIRECTORIES))
        )
    root = {"cache": CACHE, "seed": SEED, "private": PRIVATE}[directory]
    return root / ("%s.csv" % name)


def read_cache(
    name: str, *, date_col: str = "date", directory: str = "cache"
) -> pd.DataFrame | None:
    """Read data/<directory>/<name>.csv, or return None if it is not there.

    The date column is parsed to datetime64. Everything else is left as pandas
    read it, so a value that was missing stays NaN rather than becoming zero.

    float_precision="round_trip" is not a style choice. pandas' default C parser
    is not round trip exact: it can read back the double adjacent to the one
    write_cache wrote, and a rebuild of a cache from a cache then stops being
    byte identical.
    """
    path = _cache_path(name, directory=directory)
    if not path.exists():
        return None
    frame = pd.read_csv(path, encoding="utf-8", float_precision="round_trip")
    if date_col in frame.columns:
        frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    return frame


def _format_float(value: float) -> str:
    """Decimal text for a float, never scientific notation, round trip exact."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    if isinstance(value, float) and math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return np.format_float_positional(value, unique=True, trim="-")


def write_cache(
    name: str, df: pd.DataFrame, *, date_col: str = "date", directory: str = "cache"
) -> None:
    """Write a frame to data/<directory>/<name>.csv atomically.

    utf-8, LF line endings, no index column, dates as yyyy-mm-dd, floats in plain
    decimal so a diff of the committed cache stays readable and the same frame
    always produces the same bytes. The file is written under a temporary name
    and moved into place with os.replace, so a crash cannot leave half a cache.

    lineterminator is passed explicitly: opening the handle with newline="\\n"
    is not enough on Windows, because pandas defaults its terminator to
    os.linesep and writes it straight through.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("write_cache expects a DataFrame, got %r" % (type(df),))

    path = _cache_path(name, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)

    out = df.copy()
    if date_col in out.columns:
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )
    for col in out.columns:
        if col == date_col:
            continue
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")

    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            out.to_csv(
                handle,
                index=False,
                float_format=_format_float,
                na_rep="",
                lineterminator="\n",
            )
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# --------------------------------------------------------------------------
# Gaps
# --------------------------------------------------------------------------

def _clean_dates(dates: Iterable[Any]) -> pd.DatetimeIndex:
    parsed = pd.to_datetime(pd.Series(list(dates)), errors="coerce").dropna()
    if parsed.empty:
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(parsed.dt.normalize().unique()).sort_values()


def _format_dates(index: pd.DatetimeIndex) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in index]


def missing_business_days(dates: Iterable[Any]) -> list[str]:
    """Weekdays between the first and last observation with no observation.

    No holiday calendar is applied, so a bank or exchange holiday appears here
    exactly like a failed fetch. Read the list as "weekdays with no
    observation", not as "days the source lost".
    """
    index = _clean_dates(dates)
    if len(index) < 2:
        return []
    expected = pd.bdate_range(index.min(), index.max(), freq="B")
    return _format_dates(expected.difference(index))


def find_gaps(dates: Iterable[Any], frequency: str) -> list[str]:
    """Periods between the first and last observation that carry no observation.

    Args:
        dates: the dates that carry an observation. Dates with no observation
            must not be passed in, or a hole becomes invisible: the Adapter
            filters on its observation_column before calling this.
        frequency: one of lngarb.config.FREQUENCIES.

            daily     every business day in the span must appear. Holidays are
                      reported as gaps because no holiday calendar is applied.
            weekly    every ISO week in the span must carry an observation. A
                      gap is reported as the Monday of the missing week. The
                      weekday is not checked, because a release that slips by a
                      day for a holiday is not a missing week.
            monthly   every calendar month must carry an observation. A gap is
                      reported as the first of the month.
            annual    every year must carry an observation. A gap is reported
                      as the first of January.

    Returns:
        ISO yyyy-mm-dd strings, sorted ascending.

    Raises:
        ValueError: on an unknown frequency. Guessing would produce a gap list
            that looks authoritative and means nothing.
    """
    if frequency not in FREQUENCIES:
        raise ValueError(
            "frequency %r is not one of %s" % (frequency, ", ".join(FREQUENCIES))
        )
    if frequency == "daily":
        return missing_business_days(dates)

    index = _clean_dates(dates)
    if len(index) < 2:
        return []

    if frequency == "weekly":
        anchors = pd.DatetimeIndex(
            index - pd.to_timedelta(index.dayofweek, unit="D")
        ).unique()
        expected = pd.date_range(anchors.min(), anchors.max(), freq="W-MON")
    elif frequency == "monthly":
        anchors = pd.DatetimeIndex(index.to_period("M").to_timestamp()).unique()
        expected = pd.date_range(anchors.min(), anchors.max(), freq="MS")
    else:  # annual
        anchors = pd.DatetimeIndex(index.to_period("Y").to_timestamp()).unique()
        expected = pd.date_range(anchors.min(), anchors.max(), freq="YS")

    return _format_dates(expected.difference(anchors))


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def observation_count(values: Any) -> int:
    """How many cells of a column are real observations.

    A cell is an observation when it is not NaN, not None and, for a text column,
    not blank once stripped. A missing observation is written as nothing, so
    anything that reads back as nothing is not counted.
    """
    if values is None:
        return 0
    series = values if isinstance(values, pd.Series) else pd.Series(values)
    filled = series.notna()
    if not pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_datetime64_any_dtype(
        series
    ):
        filled = filled & series.astype(str).str.strip().ne("")
    return int(filled.sum())


def validate_frame(
    df: Any,
    *,
    date_col: str = "date",
    required_cols: Sequence[str] = (),
    bounds: Mapping[str, tuple[float, float]] | None = None,
    min_rows: int = 1,
    min_observations: Mapping[str, int] | None = None,
    previous: Any = None,
    unique_dates: bool = True,
) -> list[str]:
    """Check a frame before it is allowed to become the cache.

    Args:
        df: the candidate frame.
        date_col: name of the date column.
        required_cols: columns that must exist.
        bounds: col -> (lo, hi), inclusive, NaN ignored. A NaN is a declared
            missing observation and never a bounds failure.
        min_rows: the frame must have at least this many rows.
        min_observations: col -> the fewest real observations the column may
            carry. This is what stops an all NaN frame with the right dates from
            replacing a good cache, because a row count cannot see the
            difference. When previous carries the same column, the count must
            also not have shrunk against it.
        previous: the frame currently on disk, or an integer row count. If
            given, the new frame must not have fewer rows.
        unique_dates: True for a series with one row per date. A long frame
            that carries several rows per date, one per country or per
            vintage, passes False and is still required to be sorted.

    Returns:
        A list of human readable problems. Empty means valid. Nothing is raised,
        the caller decides what a problem costs.
    """
    problems: list[str] = []

    if not isinstance(df, pd.DataFrame):
        return ["expected a DataFrame, got %s" % type(df).__name__]

    for col in required_cols:
        if col not in df.columns:
            problems.append("missing required column %r" % col)

    if len(df) < min_rows:
        problems.append("row count %d is below the minimum of %d" % (len(df), min_rows))

    if date_col not in df.columns:
        problems.append("missing date column %r" % date_col)
    else:
        raw = df[date_col]
        parsed = pd.to_datetime(raw, errors="coerce")
        bad = int(parsed.isna().sum()) - int(pd.isna(raw).sum())
        if bad > 0:
            examples = raw[parsed.isna() & raw.notna()].astype(str).tolist()[:3]
            problems.append(
                "%d value(s) in %r do not parse as a date, for example %s"
                % (bad, date_col, ", ".join(examples))
            )
        if parsed.isna().any():
            problems.append(
                "%d empty date(s) in %r" % (int(parsed.isna().sum()), date_col)
            )

        clean = parsed.dropna()
        if unique_dates:
            duplicates = clean[clean.duplicated()].dt.strftime("%Y-%m-%d").unique().tolist()
            if duplicates:
                problems.append(
                    "duplicate date(s): %s%s"
                    % (", ".join(duplicates[:5]), " and more" if len(duplicates) > 5 else "")
                )
        if len(clean) > 1 and not clean.is_monotonic_increasing:
            first_break = next(
                (i for i in range(1, len(clean)) if clean.iloc[i] < clean.iloc[i - 1]),
                None,
            )
            where = (
                " first at row %d, %s follows %s"
                % (
                    first_break,
                    clean.iloc[first_break].strftime("%Y-%m-%d"),
                    clean.iloc[first_break - 1].strftime("%Y-%m-%d"),
                )
                if first_break is not None
                else ""
            )
            problems.append("dates are not increasing,%s" % where)

    for col, pair in (bounds or {}).items():
        if col not in df.columns:
            problems.append("bounds given for missing column %r" % col)
            continue
        lo, hi = pair
        values = pd.to_numeric(df[col], errors="coerce")
        unparsed = int(values.isna().sum()) - int(pd.isna(df[col]).sum())
        if unparsed > 0:
            problems.append("%d non numeric value(s) in %r" % (unparsed, col))
        outside = values.notna() & ((values < lo) | (values > hi))
        count = int(outside.sum())
        if count:
            worst = values[outside]
            problems.append(
                "%d value(s) in %r outside [%g, %g], for example %s"
                % (count, col, lo, hi, _format_float(float(worst.iloc[0])))
            )

    for col, floor in (min_observations or {}).items():
        if col not in df.columns:
            problems.append(
                "a minimum observation count was given for missing column %r" % col
            )
            continue
        count = observation_count(df[col])
        if count < int(floor):
            problems.append(
                "column %r holds %d observation(s), below the declared minimum of "
                "%d. A column with no values in it is not a cheaper version of "
                "the same series, it is a different series" % (col, count, int(floor))
            )
            continue
        if isinstance(previous, pd.DataFrame) and col in previous.columns:
            before = observation_count(previous[col])
            if count < before:
                problems.append(
                    "observation count in %r shrank from %d to %d against the "
                    "cache already on disk" % (col, before, count)
                )

    if previous is not None:
        if isinstance(previous, pd.DataFrame):
            previous_rows = len(previous)
        elif isinstance(previous, (int, np.integer)):
            previous_rows = int(previous)
        else:
            problems.append(
                "previous must be a DataFrame or a row count, got %s"
                % type(previous).__name__
            )
            previous_rows = None
        if previous_rows is not None and len(df) < previous_rows:
            problems.append("row count shrank from %d to %d" % (previous_rows, len(df)))

    return problems


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

MANIFEST_SCHEMA_VERSION = 1

STATUS_VALUES = ("ok", "stale", "failed")

# The manifest schema of the sibling repository crack-spread-study, unchanged.
# Beyond series, source, url, vintage, provisional_from, gaps, status and
# licence_note it carries:
#
#   method        how the series came to exist, from lngarb.config.METHODS
#   committable   whether the cache may be published; False sends it to
#                 data/private/
#   frequency     gap lists mean nothing without it, see find_gaps
#   page_url      the human page, the stable thing to link on the provenance
#                 panel when a machine URL has to be discovered
#   observations  rows counts the lines in the file, observations counts the
#                 ones that carry a value for this series
ENTRY_KEYS = (
    "series",
    "source",
    "url",
    "page_url",
    "machine_fetched",
    "fetched_at",
    "checked_at",
    "rows",
    "observations",
    "file_rows",
    "first_date",
    "last_date",
    "frequency",
    "gaps",
    "provisional_from",
    "vintage",
    "method",
    "committable",
    "licence_note",
    "linkable",
    "status",
    "note",
    "file",
    "unit",
)


def link_terms(entry: dict) -> dict:
    """Apply the registry's linkable flag to one manifest entry, in place.

    A publisher whose terms forbid links to its website gets no URL in the
    manifest, which the site serves: url and page_url are None and the entry
    says linkable false. The registry keeps the address, for the code that
    reads the source privately.
    """
    registered = SOURCES.get(str(entry.get("series")))
    linkable = registered.linkable if registered is not None else True
    entry["linkable"] = linkable
    if not linkable:
        entry["url"] = None
        entry["page_url"] = None
    # The base keys in their order, then whatever an adapter added, as
    # manifest_upsert writes them, so an entry carried through and one
    # rewritten come out byte for byte the same.
    ordered = {key: entry.get(key) for key in ENTRY_KEYS}
    ordered.update({k: v for k, v in entry.items() if k not in ENTRY_KEYS})
    entry.clear()
    entry.update(ordered)
    return entry


def manifest_read() -> dict:
    """Read data/manifest.json, returning an empty manifest if it is absent.

    A manifest that exists but does not parse is an error worth surfacing, not
    something to replace silently, so the JSON error propagates.
    """
    if not MANIFEST.exists():
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "generated_at": utc_now_iso(),
            "series": [],
        }
    with open(MANIFEST, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload.setdefault("schema_version", MANIFEST_SCHEMA_VERSION)
    payload.setdefault("generated_at", utc_now_iso())
    payload.setdefault("series", [])
    if not isinstance(payload["series"], list):
        raise ValueError(
            "manifest 'series' must be a list, found %s"
            % type(payload["series"]).__name__
        )
    return payload


def manifest_remove(series: str) -> bool:
    """Drop one series entry from data/manifest.json. Returns whether it was there."""
    payload = manifest_read()
    kept = [e for e in payload["series"] if e.get("series") != series]
    if len(kept) == len(payload["series"]):
        return False
    payload["series"] = kept
    payload["generated_at"] = utc_now_iso()
    manual_steps.apply(payload)
    tmp = MANIFEST.with_name(MANIFEST.name + ".tmp.%d" % os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True, sort_keys=False)
            handle.write("\n")
        os.replace(tmp, MANIFEST)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return True


def manifest_upsert(entry: Mapping[str, Any]) -> None:
    """Insert or replace one series entry in data/manifest.json.

    The entry is matched on its "series" key, so running an adapter twice updates
    the record rather than appending a second one. The list is kept sorted by
    series name and the file is written atomically as utf-8 with LF endings.

    Five things are refused here rather than left to a convention, and each is a
    way the manifest could otherwise tell a lie:

        a status outside the vocabulary
        a method outside the vocabulary, or absent
        a committable flag that is not a boolean. It decides where bytes land.
        a series that declares machine_fetched false while carrying a fetch
            time. A hand seeded file was never fetched; record checked_at.
        a series marked not committable with nothing in licence_note. The
            boolean is what the code reads, the sentence is what a human reads.
    """
    if "series" not in entry:
        raise ValueError(
            "a manifest entry needs a 'series' key, got keys %s" % sorted(entry)
        )
    status = entry.get("status")
    if status not in STATUS_VALUES:
        raise ValueError("status %r is not one of %s" % (status, ", ".join(STATUS_VALUES)))
    method = entry.get("method")
    if method not in METHODS:
        raise ValueError(
            "series %r declares method %r, which is not one of %s"
            % (entry.get("series"), method, ", ".join(METHODS))
        )
    committable = entry.get("committable")
    if not isinstance(committable, bool):
        raise ValueError(
            "series %r declares committable %r. It must be True or False, it "
            "decides whether the cache may be published"
            % (entry.get("series"), committable)
        )
    if entry.get("machine_fetched") is False and entry.get("fetched_at") is not None:
        raise ValueError(
            "series %r declares machine_fetched false and a fetched_at of %r. A "
            "file nothing fetched has no fetch time, record checked_at instead"
            % (entry.get("series"), entry.get("fetched_at"))
        )
    if committable is False and not entry.get("licence_note"):
        raise ValueError(
            "series %r is not committable and carries no licence_note saying "
            "what is forbidden" % (entry.get("series"),)
        )

    record = {key: entry.get(key) for key in ENTRY_KEYS}
    extra = {k: v for k, v in entry.items() if k not in ENTRY_KEYS}
    record.update(extra)
    link_terms(record)

    payload = manifest_read()
    kept = [e for e in payload["series"] if e.get("series") != record["series"]]
    kept.append(record)
    kept.sort(key=lambda e: str(e.get("series")))
    payload["series"] = kept
    payload["schema_version"] = MANIFEST_SCHEMA_VERSION
    payload["generated_at"] = utc_now_iso()
    # The manual steps are reattached on every write, so no single adapter run
    # can strip them and leave a manifest the data validator rejects.
    manual_steps.apply(payload)

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_name(MANIFEST.name + ".tmp.%d" % os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True, sort_keys=False)
            handle.write("\n")
        os.replace(tmp, MANIFEST)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# --------------------------------------------------------------------------
# Adapter
# --------------------------------------------------------------------------

class Adapter:
    """Base class for a single data source.

    A subclass sets the class attributes and implements fetch(). It gets
    validation, atomic cache writing, gap detection at the right frequency and
    manifest bookkeeping for free, and it cannot overwrite a good cache with a
    bad frame or publish a cache it is not allowed to publish.
    """

    #: cache file stem, and the series name in the manifest. It must be a key
    #: of lngarb.config.SOURCES, and run() checks that the two agree.
    name: str = ""
    #: human readable source
    source: str = ""
    #: the exact URL the data came from
    url: str = ""
    #: the human readable page, for the provenance panel
    page_url: str = ""
    #: unit of the value columns
    unit: str = ""
    #: one of lngarb.config.FREQUENCIES. Gap detection needs it.
    frequency: str = "daily"
    #: one of lngarb.config.METHODS
    method: str = "published"
    #: False when the cache may not be redistributed. It sends the file to
    #: data/private/ instead of data/cache/.
    committable: bool = True
    #: what the terms permit and forbid, in words. Required when committable is
    #: False.
    licence_note: str = ""
    #: col -> (lo, hi), inclusive, checked before the cache is replaced
    bounds: Mapping[str, tuple[float, float]] = {}
    #: columns fetch() must return
    required_cols: Sequence[str] = ("date",)
    #: the date column
    date_col: str = "date"
    #: False for a long frame with several rows per date
    unique_dates: bool = True
    #: refuse a frame smaller than this
    min_rows: int = 1
    #: col -> fewest real observations that column may carry. Every adapter
    #: declares this for every value column it bounds.
    min_observations: Mapping[str, int] = {}
    #: the column whose non blank cells define an observation of this series
    observation_column: str | None = None
    #: whether this is machine fetched. False forbids a fetched_at and sends the
    #: file to data/seed.
    machine_fetched: bool = True
    #: when the adapter reads a copy saved earlier instead of fetching, the time
    #: that copy was fetched. None means the bytes were fetched in this run.
    fetched_at: str | None = None
    #: the first date from which the source calls its own figures provisional
    provisional_from: str | None = None
    #: which edition of the source this came from. Set by fetch() when it can
    #: only be known after the fetch.
    vintage: str | None = None
    #: free text carried into the manifest on success
    note: str = ""
    #: True for a file that exists only once there is something to record in
    #: it, such as a revisions log before the first revision. Until then it has
    #: no manifest entry, rather than a failed one.
    written_when_needed: bool = False

    def fetch(self) -> pd.DataFrame:
        """Return a frame with a date column and the series columns.

        Missing observations must be NaN. Do not interpolate, do not substitute
        a neighbouring source without saying so in the note.
        """
        raise NotImplementedError("%s must implement fetch()" % type(self).__name__)

    # -- internals ---------------------------------------------------------

    def directory(self) -> str:
        """Which data directory this adapter reads and writes.

            private   the terms forbid redistribution, so the bytes never reach
                      a commit
            seed      nothing fetched it
            cache     machine fetched and publishable
        """
        if not self.committable:
            return "private"
        return "cache" if self.machine_fetched else "seed"

    def cache_file(self) -> str:
        """Repo relative path of the file this adapter owns."""
        return "data/%s/%s.csv" % (self.directory(), self.name)

    def _check_declarations(self) -> None:
        """Refuse an adapter whose declarations cannot be trusted, before fetching."""
        if not self.name:
            raise ValueError("%s has no name" % type(self).__name__)
        if self.frequency not in FREQUENCIES:
            raise SourceError(
                "%s declares frequency %r, not one of %s. Gap detection cannot "
                "guess" % (self.name, self.frequency, ", ".join(FREQUENCIES))
            )
        if self.method not in METHODS:
            raise SourceError(
                "%s declares method %r, not one of %s"
                % (self.name, self.method, ", ".join(METHODS))
            )
        if not isinstance(self.committable, bool):
            raise SourceError(
                "%s declares committable %r, which must be True or False"
                % (self.name, self.committable)
            )
        registered = SOURCES.get(self.name)
        note = self.licence_note or (registered.licence_note if registered is not None else "")
        if not self.committable and not note:
            raise SourceError(
                "%s is not committable and carries no licence_note. The flag "
                "keeps the bytes out of the repository, the sentence tells a "
                "reader why" % (self.name,)
            )

        # Fail closed. A column this adapter bounds is a value column, and a
        # value column with no floor can be emptied to all NaN without
        # validate_frame noticing, because NaN is exempt from bounds by design.
        unfloored = sorted(set(self.bounds) - set(self.min_observations))
        if unfloored:
            raise SourceError(
                "%s bounds %s but declares no min_observations floor for %s, so "
                "an all NaN column would be accepted. Declare a floor per value "
                "column."
                % (self.name, ", ".join(sorted(self.bounds)), ", ".join(unfloored))
            )

        # Every series is registered, and the registry and the adapter agree.
        # The registry is what the provenance panel and docs/sources.md are
        # built from, so a class that disagreed with it would publish one story
        # and act on another.
        registered = SOURCES.get(self.name)
        if registered is None:
            raise SourceError(
                "%s is not registered in lngarb.config.SOURCES" % (self.name,)
            )
        for field in ("frequency", "method", "committable"):
            mine = getattr(self, field)
            theirs = getattr(registered, field)
            if mine != theirs:
                raise SourceError(
                    "%s declares %s=%r but lngarb.config.SOURCES declares %r"
                    % (self.name, field, mine, theirs)
                )

    def _entry(self, *, status: str, frame: pd.DataFrame | None, note: str) -> dict:
        # file_rows is how many data lines the file has. observations is how
        # many of them carry a value for this series, the only one of the two
        # that gaps are computed from. rows is kept as the manifest's name for
        # observations.
        observations = 0
        file_rows = 0
        first_date = None
        last_date = None
        gaps: list[str] = []
        if frame is not None and len(frame) and self.date_col in frame.columns:
            file_rows = len(frame)
            dates = pd.to_datetime(frame[self.date_col], errors="coerce")
            present = dates.notna()
            column = self.observation_column
            if column and column in frame.columns:
                values = frame[column]
                filled = values.notna()
                if not pd.api.types.is_numeric_dtype(values):
                    filled = filled & values.astype(str).str.strip().ne("")
                present = present & filled
            have = dates[present]
            observations = int(len(have)) if self.unique_dates else int(have.nunique())
            if observations:
                first_date = have.min().strftime("%Y-%m-%d")
                last_date = have.max().strftime("%Y-%m-%d")
                gaps = find_gaps(have, self.frequency)
        # The licence travels with every entry, publishable or not, so the
        # provenance panel can print it for each series. The adapter's own note
        # wins; otherwise the registry's, which docs/sources.md quotes from.
        registered = SOURCES.get(self.name)
        licence_note = self.licence_note or (registered.licence_note if registered else "")
        licence = registered.licence if registered else None
        return {
            "series": self.name,
            "source": self.source,
            "url": self.url,
            "page_url": self.page_url,
            "machine_fetched": bool(self.machine_fetched),
            "fetched_at": (self.fetched_at or utc_now_iso()) if self.machine_fetched else None,
            "checked_at": None if self.machine_fetched else utc_now_iso(),
            "rows": observations,
            "observations": observations,
            "file_rows": file_rows,
            "first_date": first_date,
            "last_date": last_date,
            "frequency": self.frequency,
            "gaps": gaps,
            "provisional_from": self.provisional_from,
            "vintage": self.vintage,
            "method": self.method,
            "committable": bool(self.committable),
            "licence_note": licence_note,
            "licence": licence,
            "status": status,
            "note": note,
            "file": self.cache_file(),
            "unit": self.unit,
            # Declared, never inferred: tools/validate-data.mjs recounts the
            # observations from the file and needs to know which column
            # defines one, and whether a date may repeat.
            "observation_column": self.observation_column,
            "unique_dates": bool(self.unique_dates),
        }

    def run(self) -> dict:
        """Fetch, validate, write, and record. Returns the manifest entry.

        On success the cache is replaced and an "ok" entry is written. On any
        failure, a raising fetch() or a frame that does not validate, the cache
        already on disk is left exactly as it was, a "failed" entry carrying the
        error text is written, and the exception is re raised so the caller can
        exit non zero.
        """
        self._check_declarations()

        existing = read_cache(
            self.name, date_col=self.date_col, directory=self.directory()
        )

        try:
            frame = self.fetch()
            problems = validate_frame(
                frame,
                date_col=self.date_col,
                required_cols=self.required_cols,
                bounds=self.bounds,
                min_rows=self.min_rows,
                min_observations=self.min_observations,
                previous=existing,
                unique_dates=self.unique_dates,
            )
            if problems:
                raise SourceError(
                    "%s did not validate: %s" % (self.name, "; ".join(problems))
                )
        except Exception as exc:
            entry = self._entry(
                status="failed",
                frame=existing,
                note="fetch failed, previous cache kept unchanged. %s: %s"
                % (type(exc).__name__, exc),
            )
            manifest_upsert(entry)
            raise

        write_cache(self.name, frame, date_col=self.date_col, directory=self.directory())
        entry = self._entry(status="ok", frame=frame, note=self.note)
        manifest_upsert(entry)
        return entry
