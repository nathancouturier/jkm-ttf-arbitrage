"""Gatun Lake's daily level, with no network: the files are the Authority's, so none is committed
or kept as a fixture; the parsers and the curve check run on text built here."""

from __future__ import annotations

import pandas as pd
import pytest

from lngarb.sources import acp_gatun
from lngarb.sources.base import SourceError


def _history(days):
    return "DATE_LOG,GATUN_LAKE_LEVEL(FEET)\n" + "\n".join("%s,%.2f" % (d, v) for d, v in days) + "\n"


def test_the_history_file_reads_as_one_level_a_day_in_order():
    frame = acp_gatun.parse_history(_history([("2026-10-25", 86.45), ("2026-10-26", 86.52), ("2026-10-27", 86.56)]))
    assert list(frame.columns) == ["date", "level_ft"]
    assert frame["date"].tolist() == [pd.Timestamp("2026-10-25"), pd.Timestamp("2026-10-26"), pd.Timestamp("2026-10-27")]
    assert frame["level_ft"].tolist() == [86.45, 86.52, 86.56]


def test_a_history_file_with_another_header_a_repeated_day_or_a_word_is_refused():
    with pytest.raises(SourceError):
        acp_gatun.parse_history("date,level\n2026-10-25,86.45\n")
    with pytest.raises(SourceError):
        acp_gatun.parse_history(_history([("2026-10-25", 86.45), ("2026-10-25", 86.46)]))
    with pytest.raises(SourceError):
        acp_gatun.parse_history("DATE_LOG,GATUN_LAKE_LEVEL(FEET)\n2026-10-25,high\n")
    with pytest.raises(SourceError):
        acp_gatun.parse_history(_history([("2026-10-26", 86.52), ("2026-10-25", 86.45)]))


PROJECTION = (
    "The estimated maximum drafts shown in the Gatun Water Level Projection graph are only estimates.\n"
    "The official maximum Panama Canal transit drafts are communicated via Advisories to Shipping.\n"
    "projected_date,projected_gatun_water_level,surcharge_pcent,max_neopanamax_draft_ft,max_panamax_draft_ft\n"
    "12/06/2026, 87.2, 0.07, 50.0, 39.5\n"
    "12/07/2026, 85.0, 0.27, 50.0, 39.5\n"
    "12/08/2026, 79.0, 5.00, 44.0, 39.5\n"
)


def test_the_projection_file_reads_its_rows_and_the_engine_s_curve_reproduces_the_authority_s_surcharge():
    frame = acp_gatun.parse_projection(PROJECTION)
    assert len(frame) == 3 and frame["date"].iloc[0] == pd.Timestamp("2026-12-06")
    assert frame["surcharge_percent"].tolist() == [0.07, 0.27, 5.0]
    # the curve with its centre at 79 feet from October 2023, to the two decimals the Authority prints
    assert acp_gatun.curve_check(frame) < 0.01
    with pytest.raises(SourceError):
        acp_gatun.parse_projection("no rows here\n")


def test_the_adapter_builds_its_frame_and_note_from_texts_without_the_network():
    days = [(str(d.date()), 85.0 + (i % 7) / 10.0) for i, d in enumerate(pd.date_range("2025-01-01", periods=400))]
    adapter = acp_gatun.AcpGatunLakeLevelDaily(history=_history(days), projection=PROJECTION)
    frame = adapter.fetch()
    assert len(frame) == 400 and adapter.committable is False and adapter.directory() == "private"
    assert "kept privately" in adapter.note and "reproduces it to the two decimals" in adapter.note
    assert adapter.bounds["level_ft"][0] < frame["level_ft"].min() and frame["level_ft"].max() < adapter.bounds["level_ft"][1]
