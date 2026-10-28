"""The owner's own CSV series: declared once, saved by hand, validated, never committed."""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from lngarb import config
from lngarb.sources import user_csv
from lngarb.sources.base import SourceError

#: The example of a declaration: a subscription's weekly charter rate export the
#: owner may hold and not redistribute.
EXAMPLE = config.UserCsvDeclaration(
    series="owner_charter_rates_weekly",
    label="A weekly charter rate export the owner holds under a subscription, USD per day",
    publisher="the assessment's publisher, named by the owner",
    page_url="https://example.org/freight",
    frequency="weekly",
    unit="USD per day",
    columns={"hire_usd_day": config.BOUNDS_HIRE_USD_DAY},
    observation_column="hire_usd_day",
    licence="the publisher's subscription terms",
    licence_note="The export may be used by the subscriber and not redistributed; it stays under data/private/.",
    how="Exported from the publisher's platform by the owner, one row a week.",
)


def _write(root, text):
    root.mkdir(parents=True, exist_ok=True)
    (root / "owner_charter_rates_weekly.csv").write_text(text, encoding="utf-8")


def test_a_declaration_registers_as_a_private_published_source():
    source = EXAMPLE.source()
    assert source.committable is False and source.method == "published" and source.linkable
    assert source.url_note.startswith("Saved by hand as data/private/user/owner_charter_rates_weekly.csv")
    unlinked = dataclasses.replace(EXAMPLE, linkable=False, page_url="").source()
    assert unlinked.page_url == "" and not unlinked.linkable


def test_the_file_is_read_sorted_and_the_note_says_when_it_was_saved(tmp_path):
    _write(tmp_path, "date,hire_usd_day\n2026-01-09,30000\n2026-01-02,28500\n2026-01-16,\n")
    adapter = user_csv.UserCsv(EXAMPLE, root=tmp_path)
    frame = adapter.fetch()
    assert frame["date"].tolist() == [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-09"), pd.Timestamp("2026-01-16")]
    assert frame["hire_usd_day"].tolist()[:2] == [28500.0, 30000.0] and pd.isna(frame["hire_usd_day"].iloc[2])
    assert adapter.directory() == "private" and not adapter.machine_fetched
    assert adapter.note.startswith("Exported from the publisher's platform by the owner")
    assert "never committed" in adapter.note and adapter.vintage.startswith("the owner's file, saved 20")


@pytest.mark.parametrize("text, why", [
    ("day,hire_usd_day\n2026-01-02,1\n", "no date column"),
    ("date,rate\n2026-01-02,1\n", "lacks the declared column"),
    ("date,hire_usd_day,extra\n2026-01-02,1,2\n", "the declaration does not"),
    ("date,hire_usd_day\n2 Jan 2026,1\n", "does not read as yyyy-mm-dd"),
])
def test_a_file_that_does_not_match_its_declaration_is_refused(tmp_path, text, why):
    _write(tmp_path, text)
    with pytest.raises(SourceError, match=why):
        user_csv.UserCsv(EXAMPLE, root=tmp_path).fetch()


def test_a_missing_file_is_named_not_invented(tmp_path):
    with pytest.raises(SourceError, match="is not there"):
        user_csv.UserCsv(EXAMPLE, root=tmp_path).fetch()


def test_the_bounds_and_frequency_apply_as_to_a_fetched_series(tmp_path):
    from lngarb.sources.base import validate_frame
    _write(tmp_path, "date,hire_usd_day\n2026-01-02,30000\n2026-01-09,900000\n")
    adapter = user_csv.UserCsv(EXAMPLE, root=tmp_path)
    frame = adapter.fetch()
    problems = validate_frame(frame, date_col="date", required_cols=adapter.required_cols, bounds=adapter.bounds,
                              min_rows=1, min_observations=adapter.min_observations, previous=None, unique_dates=True)
    assert any("hire_usd_day" in p for p in problems)


def test_nothing_is_declared_in_the_repository_as_committed():
    assert config.USER_CSV_SERIES == ()
    assert user_csv.adapters() == []
