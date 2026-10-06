"""JOGMEC's monthly spot LNG prices. Private: JOGMEC's pages are not committed.

JOGMEC's terms do not permit republishing its pages, so they cannot be test
fixtures in a public repository. The parser is tested on pages built inside this
file, which copy JOGMEC's layout and carry placeholder numbers that are not
data. The anchors are tested against the pages saved in data/private/ when they
exist on the machine running the tests, and skipped otherwise.
"""

from __future__ import annotations

import json
import math

import pandas as pd
import pytest

from lngarb.sources import base, jogmec

BAR = chr(0x2015)


def page(columns, contract, arrival, unit_as="paragraph"):
    header = "".join("<th>%s</th>" % c for c in columns)
    unit = "（USD/MBtu）"
    caption = "<caption>%s</caption>" % unit if unit_as == "caption" else ""
    before = "<p>%s</p>" % unit if unit_as == "paragraph" else ""
    return (
        "<html><body>%s<table>%s<tr><th>Contracted Month</th>%s</tr>"
        "<tr><th>Contract-based%sprice</th>%s</tr>"
        "<tr><th>Arrival-based price</th>%s</tr></table></body></html>"
        % (
            before,
            caption,
            header,
            chr(0x00A0),
            "".join("<td>%s</td>" % v for v in contract),
            "".join("<td>%s</td>" % v for v in arrival),
        )
    )


def test_a_two_column_page_gives_both_vintages():
    records = jogmec.parse_page(
        page(["March 2031 (Confirmed)", "April 2031 (Preliminary)"], ["1.1", BAR], [BAR, "2.2"]),
        where="constructed",
    )
    assert [(r["date"], r["vintage"]) for r in records] == [
        (pd.Timestamp("2031-03-01"), "confirmed"),
        (pd.Timestamp("2031-04-01"), "preliminary"),
    ]
    assert records[0]["contract"] == 1.1 and math.isnan(records[0]["arrival"])
    assert math.isnan(records[1]["contract"]) and records[1]["arrival"] == 2.2


def test_a_header_broken_over_two_lines_and_a_caption_unit_are_read():
    records = jogmec.parse_page(
        page(["June<br>2031 (Confirmed)", "July 2031 (Preliminary)"], ["3.3", "4.4"], ["5.5", "6.6"], unit_as="caption"),
        where="constructed",
    )
    assert records[0]["date"] == pd.Timestamp("2031-06-01")


def test_a_page_without_the_unit_or_with_an_unknown_cell_is_refused():
    with pytest.raises(base.SourceError):
        jogmec.parse_page(page(["May 2031 (Preliminary)"], ["1.0"], ["2.0"], unit_as="none"), where="no unit")
    with pytest.raises(base.SourceError):
        jogmec.parse_page(page(["May 2031 (Preliminary)"], ["n/a"], ["2.0"]), where="odd cell")


def test_assembly_prefers_the_confirmed_figure_and_keeps_both():
    records = (
        jogmec.parse_page(page(["May 2031 (Preliminary)"], ["1.0"], [BAR]), where="a")
        + jogmec.parse_page(page(["May 2031 (Confirmed)", "June 2031 (Preliminary)"], ["1.5", "2.0"], ["3.0", "4.0"]), where="b")
    )
    frame = jogmec.assemble(records).set_index("date")
    may = frame.loc[pd.Timestamp("2031-05-01")]
    assert may["contract_preliminary_usd_mmbtu"] == 1.0
    assert may["contract_confirmed_usd_mmbtu"] == 1.5
    assert may["contract_usd_mmbtu"] == 1.5
    assert may["arrival_usd_mmbtu"] == 3.0  # disclosed only when confirmed
    june = frame.loc[pd.Timestamp("2031-06-01")]
    assert june["vintage"] == "preliminary"
    assert math.isnan(june["contract_confirmed_usd_mmbtu"])


def test_the_arrival_definition_changes_in_april_2023():
    records = jogmec.parse_page(page(["March 2023 (Confirmed)", "April 2023 (Preliminary)"], ["1.0", "1.0"], ["1.0", "1.0"]), where="c")
    records += jogmec.parse_page(page(["February 2023 (Confirmed)", "March 2023 (Preliminary)"], ["1.0", "1.0"], ["1.0", "1.0"]), where="d")
    records += jogmec.parse_page(page(["January 2023 (Confirmed)", "February 2023 (Preliminary)"], ["1.0", "1.0"], ["1.0", "1.0"]), where="e")
    records += jogmec.parse_page(page(["January 2023 (Preliminary)"], ["1.0"], ["1.0"]), where="f")
    frame = jogmec.assemble(records).set_index("date")
    assert frame.loc[pd.Timestamp("2023-03-01"), "arrival_definition"] == "contracted and delivered in the month"
    assert frame.loc[pd.Timestamp("2023-04-01"), "arrival_definition"] == "delivered in the month, whenever contracted"


def test_the_series_is_never_committable():
    assert jogmec.JogmecSpotLngMonthly.committable is False
    assert jogmec.JogmecSpotLngMonthly().cache_file() == "data/private/jogmec_spot_lng_monthly.csv"


def test_reading_the_saved_pages_offline_keeps_the_last_fetch_time(sandbox):
    previous = {"schema_version": 1, "series": [{"series": "jogmec_spot_lng_monthly", "fetched_at": "2026-09-30T20:44:48Z"}]}
    base.MANIFEST.write_text(json.dumps(previous), encoding="utf-8")
    entry = jogmec.JogmecSpotLngMonthly(offline=True)._entry(status="ok", frame=None, note="")
    assert entry["fetched_at"] == "2026-09-30T20:44:48Z"
    online = jogmec.JogmecSpotLngMonthly()._entry(status="ok", frame=None, note="")
    assert online["fetched_at"] != "2026-09-30T20:44:48Z"


SAVED = base.PRIVATE / "jogmec" / "pages"


@pytest.mark.skipif(not SAVED.exists(), reason="JOGMEC's pages are private and not on this machine")
def test_the_anchors_on_the_saved_pages():
    records = []
    for path in sorted(SAVED.glob("*.html")):
        records.extend(jogmec.parse_page(path.read_bytes(), where=path.name))
    frame = jogmec.assemble(records).set_index("date")
    assert frame.loc[pd.Timestamp("2026-01-01"), "contract_preliminary_usd_mmbtu"] == 11.3
    assert frame.loc[pd.Timestamp("2026-02-01"), "contract_preliminary_usd_mmbtu"] == 11.0
    assert frame.loc[pd.Timestamp("2026-01-01"), "contract_confirmed_usd_mmbtu"] == 11.3
    assert frame.index[0] == pd.Timestamp("2021-04-01")
