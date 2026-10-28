"""The Panama Canal Authority's monthly operations summaries, with no network.

The fixture is the summary for December 2023, advisory A-02-2024, the month
with a 15 day wait reported for LNG carriers without a slot; the list parser
is tested on a page built here in the advisory page's own markup.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lngarb.sources import acp_ops, base
from lngarb.sources.base import SourceError

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
SUMMARY = (FIXTURES / "acp_ops_summary_2023-12_A-02-2024.pdf").read_bytes()
URL = "https://pancanal.com/wp-content/uploads/2024/01/ADV02-2024-Monthly-Canal-Operations-Summary-December-2023.pdf"


def _page(items):
    rows = []
    for url, advisory, label in items:
        rows.append('<li class="d_boxes col-md-6">\n<a href="%s" target="_blank">\n<img class="d_img" src="x.png"/>\n'
                    '<h3>%s</h3><div class="d_des">%s</div><img class="d_icon" src="y.png"/></a></li>' % (url, advisory, label))
    return "<html><body><ul>%s</ul></body></html>" % "\n".join(rows)


def test_the_december_2023_summary_reads_as_the_authority_printed_it():
    row = acp_ops.parse_summary(SUMMARY, label_month="2023-12-01", advisory="A-02-2024")
    assert row["date"] == pd.Timestamp("2023-12-01") and row["advisory"] == "A-02-2024"
    assert row["cwt_hours_avg"] == pytest.approx(44.10)
    assert row["cwt_hours_high"] == pytest.approx(87.06) and row["cwt_hours_low"] == pytest.approx(17.46)
    assert row["in_transit_hours_avg"] == pytest.approx(9.74)
    assert row["transits_total"] == 748.0 and row["neopanamax_transits"] == 208.0
    # That month's table prints no neopanamax slot line, only the auctioned slots.
    assert math.isnan(row["neopanamax_slots_available"]) and math.isnan(row["neopanamax_slots_used"])


def test_the_pdf_subject_names_the_month_over_the_label():
    row = acp_ops.parse_summary(SUMMARY, label_month="2024-01-01")
    assert row["date"] == pd.Timestamp("2023-12-01")


def test_the_list_keeps_summaries_and_reads_their_months_with_the_authority_s_spellings():
    page = _page([
        ("https://pancanal.com/wp-content/uploads/2026/10/ADV-38-2026.pdf", "A-38-2026", "Monthly Canal Operations Summary September 2026"),
        ("https://pancanal.com/wp-content/uploads/2026/04/ADV-18-2026.pdf", "A-18-2026", "Draft adjustment in the Neopanamax Locks"),
        ("https://pancanal.com/wp-content/uploads/2023/01/ADV33-2023.pdf", "A-33-2023", "Montly Canal Operations Summary &#8211; JUNY 2023"),
        ("https://pancanal.com/wp-content/uploads/2025/03/ADV-05-2025.pdf", "A-05-2025", "Monthly Canal Operations Summary Feburary 2025"),
    ])
    links = acp_ops.summary_links(page)
    assert [l["advisory"] for l in links] == ["A-38-2026", "A-33-2023", "A-05-2025"]
    assert [l["month"] for l in links] == ["2026-09-01", "2023-06-01", "2025-02-01"]


def test_a_page_without_a_summary_is_refused():
    with pytest.raises(SourceError, match="no operations summary"):
        acp_ops.summary_links(_page([("https://pancanal.com/wp-content/uploads/a.pdf", "A-1-2026", "Tolls")]))


def test_a_run_reads_only_the_months_newer_than_the_cache(monkeypatch, tmp_path):
    held = pd.DataFrame([{
        "date": pd.Timestamp("2023-11-01"), "advisory": "A-50-2023", "cwt_hours_avg": 40.0, "cwt_hours_high": 80.0,
        "cwt_hours_low": 20.0, "in_transit_hours_avg": 10.0, "arrivals_daily_avg": 30.0, "transits_daily_avg": 30.0,
        "transits_total": 900.0, "neopanamax_transits": 200.0, "neopanamax_slots_available": float("nan"),
        "neopanamax_slots_used": float("nan")}])
    monkeypatch.setattr(acp_ops, "read_cache", lambda name, directory="cache": held)
    page = _page([
        (URL, "A-02-2024", "Monthly Canal Operations Summary &#8211; December 2023"),
        ("https://pancanal.com/wp-content/uploads/2023/12/ADV50-2023.pdf", "A-50-2023", "Monthly Canal Operations Summary November 2023"),
    ])
    fetched = []

    def fake_get(url, **kwargs):
        fetched.append(url)
        raise AssertionError("nothing should be fetched: the page and the summary are given")

    monkeypatch.setattr(acp_ops, "http_get", fake_get)
    adapter = acp_ops.AcpCanalOperationsMonthly(page=page.encode(), summaries={URL: SUMMARY})
    frame = adapter.fetch()
    assert fetched == []
    assert [d.strftime("%Y-%m") for d in frame["date"]] == ["2023-11", "2023-12"]
    assert frame["cwt_hours_avg"].tolist() == pytest.approx([40.0, 44.10])
    assert math.isnan(frame["neopanamax_slots_available"].iloc[0])
    assert "1 summary(ies) read this run; 2 months held, November 2023 to December 2023" in adapter.note
    assert adapter.vintage == "advisories A-50-2023 to A-02-2024"


def test_the_adapter_is_registered_as_it_declares_itself():
    from lngarb.config import SOURCES
    registered = SOURCES[acp_ops.AcpCanalOperationsMonthly.name]
    assert registered.frequency == "monthly" and registered.method == "parsed" and registered.committable
    assert acp_ops.CRAWL_DELAY_S == 10.0
