#!/usr/bin/env python
"""Refresh every source, or revalidate the committed caches with no network.

    python scripts/refresh.py                 fetch everything, politely
    python scripts/refresh.py --offline       fetch nothing, revalidate what is committed
    python scripts/refresh.py --list          print the jobs and exit
    python scripts/refresh.py --only eia      run one or more jobs by name

This is the script behind `make data`, and the one that finishes
data/manifest.json. Four promises, adapted from the sibling repository
crack-spread-study, which paid for them:

1. NOTHING IS INVENTED. A source that fails leaves its cache on disk exactly as
   it was, gets status "failed" with the error in its note, and makes this script
   exit non zero. One dead source does not stop the others.

2. OFFLINE MEANS OFFLINE. --offline opens no socket. It reads the committed
   caches, measures them with the same code the online path uses, and rewrites
   the manifest from what it measured rather than from what the last fetch
   claimed. That is the run CI makes.

3. OFFLINE IS BYTE IDEMPOTENT. Run twice on an unchanged tree, it leaves
   data/manifest.json byte identical, so `git diff --exit-code data/` after it is
   a real check. When nothing but the clock has moved, the previous bytes are
   written back.

4. THE MANUAL STEPS ARE IN THE MANIFEST. Work this pipeline cannot do for
   itself, because a site's robots.txt forbids it or a document disappears, is
   written into the manifest on every run, against the series it affects.

Private caches, whose terms forbid publication, are never in the repository, so
a clean checkout does not have them. Offline carries their entries through
from the committed manifest unchanged, so the manifest is the same on the
owner's machine and in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from lngarb import config, manual_steps  # noqa: E402
from lngarb.sources import base  # noqa: E402
from lngarb.sources.base import Adapter, read_cache, utc_now_iso, validate_frame  # noqa: E402
from lngarb.sources.eia import HenryHubDaily, LngExportsMonthly, LngExportsRevisions  # noqa: E402
from lngarb.sources.eia_ngwu import (  # noqa: E402
    NgwuInternationalWeekly,
    NgwuIssueIndex,
    WngsrInternationalWeekly,
)

# Windows consoles default to cp1252. Printing must never be what fails a refresh.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Job:
    """One unit of work, named so --only can address it.

    adapters builds the Adapter instances offline revalidates, and online is
    what a real run calls. online records its own failures and raises nothing.
    """

    name: str
    what: str
    series: tuple[str, ...]
    adapters: Callable[[], list[Adapter]]
    online: Callable[[argparse.Namespace], list[dict]]


def _run_adapters(adapters: Sequence[Adapter], failures: list[dict]) -> list[dict]:
    entries: list[dict] = []
    for adapter in adapters:
        try:
            entries.append(adapter.run())
        except Exception as exc:  # noqa: BLE001, one dead source is not all of them
            failures.append(
                {
                    "series": adapter.name,
                    "error": "%s: %s" % (type(exc).__name__, exc),
                    "traceback": traceback.format_exc(),
                }
            )
    return entries


def _simple(factory: Callable[[], list[Adapter]]) -> Callable[[argparse.Namespace], list[dict]]:
    def run(args: argparse.Namespace) -> list[dict]:
        failures: list[dict] = []
        entries = _run_adapters(factory(), failures)
        args.failures.extend(failures)
        return entries

    return run


def _eia_tables_online(args: argparse.Namespace) -> list[dict]:
    """The exports adapter writes the revisions log itself when a release changes values."""
    failures: list[dict] = []
    entries = _run_adapters([LngExportsMonthly(), HenryHubDaily()], failures)
    args.failures.extend(failures)
    revisions = base.manifest_read()
    for entry in revisions["series"]:
        if entry.get("series") == "eia_lng_exports_revisions":
            entries.append(entry)
    return entries


JOBS: tuple[Job, ...] = (
    Job(
        name="eia-weekly",
        what=(
            "EIA's weekly JKM and TTF averages: the NGWU index, its international "
            "item (landing page and issues saved by hand), and the WNGSR Supplement"
        ),
        series=(
            "eia_ngwu_issue_index",
            "eia_ngwu_international_weekly",
            "eia_wngsr_international_weekly",
        ),
        adapters=lambda: [NgwuIssueIndex(), NgwuInternationalWeekly(), WngsrInternationalWeekly()],
        online=_simple(
            lambda: [NgwuIssueIndex(), NgwuInternationalWeekly(), WngsrInternationalWeekly()]
        ),
    ),
    Job(
        name="eia-tables",
        what="EIA US LNG exports by destination with its revisions log, and Henry Hub spot",
        series=("eia_lng_exports_monthly", "eia_lng_exports_revisions", "eia_henry_hub_daily"),
        adapters=lambda: [
            LngExportsMonthly(),
            LngExportsRevisions(pd.DataFrame()),
            HenryHubDaily(),
        ],
        online=_eia_tables_online,
    ),
)

JOBS_BY_NAME: Mapping[str, Job] = {job.name: job for job in JOBS}


def resolve_only(values: Sequence[str]) -> list[Job]:
    """Jobs named on the command line, or every job. Raises on an unknown name."""
    if not values:
        return list(JOBS)
    chosen: list[Job] = []
    for value in values:
        job = JOBS_BY_NAME.get(value)
        if job is None:
            raise SystemExit(
                "no job named %r. Jobs: %s" % (value, ", ".join(sorted(JOBS_BY_NAME)))
            )
        if job not in chosen:
            chosen.append(job)
    return chosen


# --------------------------------------------------------------------------
# The manifest, and its idempotence
# --------------------------------------------------------------------------

#: Fields that move on every run whether or not anything about the data changed.
VOLATILE_TOP = ("generated_at", "run")
VOLATILE_ENTRY = ("checked_at",)


def _without_volatile(payload: Mapping[str, Any]) -> dict:
    stripped = {k: v for k, v in payload.items() if k not in VOLATILE_TOP}
    stripped["series"] = [
        {k: v for k, v in entry.items() if k not in VOLATILE_ENTRY}
        for entry in payload.get("series", [])
    ]
    return stripped


def manifest_is_unchanged(before: bytes | None, payload: Mapping[str, Any]) -> bool:
    """True when the only difference from the committed manifest is the clock."""
    if before is None:
        return False
    try:
        previous = json.loads(before.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False
    return _without_volatile(previous) == _without_volatile(payload)


def _write_manifest_bytes(raw: bytes) -> None:
    manifest = base.MANIFEST
    tmp = manifest.with_name(manifest.name + ".tmp.%d" % os.getpid())
    try:
        with open(tmp, "wb") as handle:
            handle.write(raw)
        os.replace(tmp, manifest)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _serialise(payload: Mapping[str, Any]) -> bytes:
    text = json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=False) + "\n"
    return text.encode("utf-8")


def existing_entries() -> dict[str, dict]:
    """The committed manifest, keyed by series name. Empty when there is none."""
    if not base.MANIFEST.exists():
        return {}
    try:
        payload = json.loads(base.MANIFEST.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return {e.get("series"): e for e in payload.get("series", []) if e.get("series")}


def finalise_manifest(mode: str, before: bytes | None, started: str) -> tuple[dict, bool]:
    """Attach the manual steps and the run block, then write, or restore the old bytes."""
    payload = manual_steps.apply(base.manifest_read())
    payload["generated_at"] = utc_now_iso()
    payload["run"] = {
        "mode": mode,
        "started_at": started,
        "finished_at": utc_now_iso(),
        "script": "scripts/refresh.py",
    }
    if manifest_is_unchanged(before, payload):
        _write_manifest_bytes(before)
        return payload, False
    _write_manifest_bytes(_serialise(payload))
    return payload, True


# --------------------------------------------------------------------------
# Offline revalidation
# --------------------------------------------------------------------------

#: Keys the base entry owns. Anything else in a committed entry was put there by
#: an adapter that fetched, and offline carries it through untouched.
_BASE_KEYS = frozenset(base.ENTRY_KEYS) | {"observation_column", "manual_step"}


def carry_forward(entry: dict, previous: Mapping[str, Any] | None) -> dict:
    """Put back everything offline cannot know, from the committed entry."""
    if not previous:
        return entry
    for key, value in previous.items():
        if key not in _BASE_KEYS:
            entry.setdefault(key, value)
    # A run that fetched nothing must not stamp a fresh fetch time.
    if entry.get("machine_fetched"):
        entry["fetched_at"] = previous.get("fetched_at")
    for key in ("vintage", "provisional_from"):
        if entry.get(key) is None:
            entry[key] = previous.get(key)
    return entry


def revalidate(adapter: Adapter, previous: Mapping[str, Any] | None) -> dict:
    """Measure one committed cache and return its manifest entry. Fetches nothing."""
    frame = read_cache(adapter.name, date_col=adapter.date_col, directory=adapter.directory())
    if frame is None:
        if previous and previous.get("status") == "failed":
            # A source that failed before anything was ever cached stays failed,
            # with the note that says why, rather than a note about the file.
            return dict(previous)
        entry = Adapter._entry(
            adapter,
            status="failed",
            frame=None,
            note="%s is not on disk. Nothing was written and nothing was removed."
            % adapter.cache_file(),
        )
        return carry_forward(entry, previous)

    problems = validate_frame(
        frame,
        date_col=adapter.date_col,
        required_cols=adapter.required_cols,
        bounds=adapter.bounds,
        min_rows=adapter.min_rows,
        min_observations=adapter.min_observations,
        previous=None,
        unique_dates=adapter.unique_dates,
    )
    if problems:
        entry = Adapter._entry(
            adapter,
            status="failed",
            frame=frame,
            note="the committed cache does not validate: %s. The file was not changed."
            % "; ".join(problems),
        )
        return carry_forward(entry, previous)

    # Nothing was learned that the last real run did not already know, so the
    # note it wrote is still the true one.
    note = (previous or {}).get("note") or ""
    if not note or (previous or {}).get("status") != "ok":
        note = "revalidated offline from the committed cache. No fetch, no network."
    entry = Adapter._entry(adapter, status="ok", frame=frame, note=note)
    return carry_forward(entry, previous)


def _private_check(adapter: Adapter) -> tuple[bool, str]:
    """A one line report on a private cache: (valid, report)."""
    frame = read_cache(adapter.name, date_col=adapter.date_col, directory=adapter.directory())
    if frame is None:
        return True, "not on this machine, entry carried through from the committed manifest"
    problems = validate_frame(
        frame,
        date_col=adapter.date_col,
        required_cols=adapter.required_cols,
        bounds=adapter.bounds,
        min_rows=adapter.min_rows,
        min_observations=adapter.min_observations,
        previous=None,
        unique_dates=adapter.unique_dates,
    )
    if problems:
        return False, "present and invalid: %s. Run a real refresh." % "; ".join(problems)
    return True, "present and valid, %d rows, entry carried through unchanged" % len(frame)


# --------------------------------------------------------------------------
# Reporting and the command line
# --------------------------------------------------------------------------

def print_summary(payload: Mapping[str, Any], touched: Sequence[str]) -> list[str]:
    rows = [
        (
            str(entry.get("series", "")),
            str(entry.get("status", "")),
            str(entry.get("method", "")),
            str(entry.get("frequency", "")),
            str(entry.get("rows") if entry.get("rows") is not None else ""),
            str(entry.get("first_date") or ""),
            str(entry.get("last_date") or ""),
            str(len(entry.get("gaps") or [])),
            "yes" if entry.get("committable") else "NO",
            "yes" if entry.get("series") in touched else "",
        )
        for entry in payload.get("series", [])
    ]
    header = ("series", "status", "method", "freq", "rows", "first", "last", "gaps", "commit", "run")
    widths = [max(len(header[i]), max((len(r[i]) for r in rows), default=0)) for i in range(len(header))]

    def line(cells: Sequence[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    return [line(header), line(["-" * w for w in widths])] + [line(r) for r in rows]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh the data layer, or revalidate it offline.")
    parser.add_argument("--offline", action="store_true",
                        help="fetch nothing; revalidate the committed caches and rewrite the manifest")
    parser.add_argument("--only", action="append", default=[], metavar="JOB",
                        help="run one job by name, repeatable. See --list")
    parser.add_argument("--list", action="store_true", help="print the jobs and exit")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="polite pause between jobs on an online run, seconds")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    args.failures = []

    if args.list:
        print("jobs, in run order")
        for job in JOBS:
            print("  %-12s %s" % (job.name, job.what))
            for name in job.series:
                registered = config.SOURCES.get(name)
                flag = "" if registered is None or registered.committable else "  NOT committable"
                print("      %s%s" % (name, flag))
        return 0

    jobs = resolve_only(args.only)
    mode = "offline" if args.offline else "online"
    started = utc_now_iso()
    before = base.MANIFEST.read_bytes() if base.MANIFEST.exists() else None
    previous = existing_entries()

    print("scripts/refresh.py, %s, %d job(s), started %s" % (mode, len(jobs), started))
    print("")

    touched: list[str] = []
    for index, job in enumerate(jobs):
        print("[%d/%d] %s, %s" % (index + 1, len(jobs), job.name, job.what))
        if args.offline:
            for adapter in job.adapters():
                if not adapter.committable:
                    valid, note = _private_check(adapter)
                    print("        %-40s private, %s" % (adapter.name, note))
                    if not valid:
                        args.failures.append({"series": adapter.name, "error": note, "traceback": ""})
                    continue
                entry = revalidate(adapter, previous.get(adapter.name))
                base.manifest_upsert(entry)
                touched.append(adapter.name)
                if entry["status"] != "ok":
                    args.failures.append({"series": adapter.name, "error": entry["note"], "traceback": ""})
                print("        %-40s %s, %s rows" % (adapter.name, entry["status"], entry["rows"]))
            continue

        for entry in job.online(args):
            touched.append(entry["series"])
            print("        %-40s %s, %s rows" % (entry["series"], entry["status"], entry["rows"]))
        if index + 1 < len(jobs) and args.delay > 0:
            time.sleep(args.delay)

    payload, changed = finalise_manifest(mode, before, started)

    print("")
    for line in print_summary(payload, touched):
        print(line)
    print("")
    print("manual steps recorded in the manifest, %d:" % len(manual_steps.MANUAL_STEPS))
    for step in manual_steps.MANUAL_STEPS:
        print("  %-30s %s, %s" % (step["id"], step["status"], step["cadence"]))
    print("")
    print("data/manifest.json %s" % ("rewritten" if changed else "unchanged, byte identical"))

    if args.failures:
        print("")
        print("FAILED, %d series:" % len(args.failures))
        for failure in args.failures:
            print("  %s: %s" % (failure["series"], failure["error"]))
        print("")
        print("Every cache on disk was left exactly as it was.")
        return 1

    ok = sum(1 for e in payload.get("series", []) if e.get("status") == "ok")
    print("%d of %d series ok" % (ok, len(payload.get("series", []))))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
