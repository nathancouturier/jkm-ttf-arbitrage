"""The Panama Canal's LNG transits by fiscal year, a seed typed from the Authority's reports."""

from __future__ import annotations

import json

from lngarb import panama_transits


def test_the_rows_run_every_fiscal_year_from_the_expanded_locks_and_hold_the_drought():
    years = [t.fiscal_year for t in panama_transits.TRANSITS]
    assert years == list(range(2016, 2026))
    by_year = {t.fiscal_year: t.transits for t in panama_transits.TRANSITS}
    assert by_year[2021] == 537 and by_year[2024] == 115 and by_year[2025] == 61
    assert panama_transits.problems() == []
    assert all(t.url.startswith("https://pancanal.com/wp-content/uploads/") for t in panama_transits.TRANSITS)


def test_the_committed_seed_is_the_rows_in_the_code():
    committed = json.loads(panama_transits.seed_path().read_text(encoding="utf-8"))
    assert committed == panama_transits.document()
    assert committed["rows"][0]["note"].startswith("The expanded locks opened on 26 June 2016")
