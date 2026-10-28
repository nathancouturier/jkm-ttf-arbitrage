"""A series the owner saves by hand under data/private/user/, validated like every other and never committed.

Some figures the owner may hold but not publish: an export from a subscription
whose terms forbid redistribution, a table typed from a paid report, a page a
publisher serves to a browser and not to code. Each such series is declared
once in lngarb.config.USER_CSV_SERIES, with its columns, bounds, frequency,
unit and terms, and saved as data/private/user/<series>.csv with a date
column and the declared value columns. This adapter reads that file, refuses
it on the same rules as a fetched frame (dates, bounds, counts, gaps at the
declared frequency), writes it as the series' private cache and records it
in the manifest with committable False, so that the site's Provenance view
names the series and its terms while the bytes never reach a commit.

Nothing is fetched. The file's modification time is recorded as the vintage,
and the manual step is the saving of the file; the pipeline cannot know when
the owner's copy is stale, so the note says the day the file was saved.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..config import USER_CSV_SERIES, UserCsvDeclaration
from .base import Adapter, SourceError, REPO_ROOT

__all__ = ["USER_DIR", "UserCsv", "adapters"]

USER_DIR = REPO_ROOT / "data" / "private" / "user"


class UserCsv(Adapter):
    """One declared series read from the owner's CSV."""

    method = "published"
    committable = False
    machine_fetched = False

    def __init__(self, declaration: UserCsvDeclaration, *, root: Path | None = None):
        self.declaration = declaration
        self.name = declaration.series
        self.source = declaration.publisher
        self.url = declaration.page_url if declaration.linkable else ""
        self.page_url = declaration.page_url if declaration.linkable else ""
        self.linkable = declaration.linkable
        self.unit = declaration.unit
        self.frequency = declaration.frequency
        self.licence_note = declaration.licence_note
        self.bounds = dict(declaration.columns)
        self.required_cols = ("date", *declaration.columns)
        self.min_observations = {column: 1 for column in declaration.columns}
        self.observation_column = declaration.observation_column
        self.root = USER_DIR if root is None else root

    def path(self) -> Path:
        return self.root / ("%s.csv" % self.name)

    def fetch(self) -> pd.DataFrame:
        path = self.path()
        if not path.exists():
            raise SourceError("the owner's file %s is not on this machine" % path.relative_to(REPO_ROOT)
                              if path.is_relative_to(REPO_ROOT) else "the owner's file %s is not there" % path)
        frame = pd.read_csv(path, encoding="utf-8", float_precision="round_trip")
        if "date" not in frame.columns:
            raise SourceError("%s has no date column" % path.name)
        missing = [c for c in self.declaration.columns if c not in frame.columns]
        if missing:
            raise SourceError("%s lacks the declared column(s) %s" % (path.name, ", ".join(missing)))
        extra = [c for c in frame.columns if c not in ("date", *self.declaration.columns)]
        if extra:
            raise SourceError("%s carries column(s) the declaration does not: %s" % (path.name, ", ".join(extra)))
        frame["date"] = pd.to_datetime(frame["date"].astype(str).str.strip(), format="%Y-%m-%d", errors="coerce")
        if frame["date"].isna().any():
            raise SourceError("%s has a date that does not read as yyyy-mm-dd" % path.name)
        for column in self.declaration.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = frame.sort_values("date", kind="mergesort").reset_index(drop=True)
        saved = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        self.vintage = "the owner's file, saved %s" % saved.strftime("%Y-%m-%d")
        self.note = (
            "%s Read from the owner's file data/private/user/%s.csv, saved on %s and never committed; "
            "nothing is fetched, and a newer copy is the owner's to save. %s"
            % (self.declaration.how, self.name, saved.strftime("%d %B %Y").lstrip("0"), self.declaration.licence_note)
        )
        return frame


def adapters() -> list[UserCsv]:
    """One adapter per declared series."""
    return [UserCsv(declaration) for declaration in USER_CSV_SERIES]


def main() -> int:
    if not USER_CSV_SERIES:
        print("no user series declared in lngarb.config.USER_CSV_SERIES")
        return 0
    failed = 0
    for adapter in adapters():
        try:
            entry = adapter.run()
        except Exception as exc:
            print("FAILED %s: %s" % (adapter.name, exc))
            failed = 1
            continue
        print("ok     %s: %d observations, %s to %s, private" % (
            entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return failed


if __name__ == "__main__":
    sys.exit(main())
