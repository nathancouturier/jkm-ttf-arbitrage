"""The Method view: every parameter in words, its value as the table shows it, and the counts in its title."""

from __future__ import annotations

import json

import pytest

from lngarb import config, methodpage
from lngarb.sources import base

DATA = base.REPO_ROOT / "data"


@pytest.fixture(scope="module")
def method():
    return json.loads((DATA / "method.json").read_text(encoding="utf-8"))


def test_every_parameter_is_in_words_and_in_the_table(method):
    assert set(methodpage.PARAMETER_WORDS) == set(config.PARAMETERS)
    assert [p["key"] for p in method["parameters"]] == list(config.PARAMETERS)
    for row in method["parameters"]:
        parameter = config.PARAMETERS[row["key"]]
        assert row["status"] == parameter.status and row["read_on"] == parameter.read_on
        assert row["url"] == parameter.url


def test_the_title_counts_the_formulas_parameters_and_assumptions(method):
    values = {s["field"]: s["value"] for s in method["title_segments"] if "field" in s}
    assert values["formulas"] == len(method["formulas"])
    assert values["parameters"] == len(config.PARAMETERS)
    assert values["assumed"] == sum(p.status == "assumption" for p in config.PARAMETERS.values())


@pytest.mark.parametrize("value, unit, words", [
    (0.985, "share of capacity loaded", "98.5 percent of capacity loaded"),
    (0.00085, "share of the loaded volume per day", "0.085 percent of the loaded volume per day"),
    (308_947.0, "USD per round trip", "308,947 USD per round trip"),
    (1.0, "days", "1 day"),
    (3.0, "days", "3 days"),
    (True, "flag", "yes"),
    ("2024-01-02", "date", "2 January 2024"),
    ("2016-01", "month", "January 2016"),
    (("2022-07-25", "2022-10-15"), "dates, first and last", "25 July 2022 to 15 October 2022"),
    ((2020, 2022, 2026), "calendar years", "2020, 2022 and 2026"),
    ({"2023-07": 12.0, "2023-12": 15.0}, "days of waiting", "12 days in July 2023; 15 days in December 2023"),
    ({"2024": 0.4, "2026": 1.0}, "share of a year's emissions", "40 percent from 2024; 100 percent from 2026"),
    (20, "day of the month two months before the loading month",
     "the 20th of the month two months before the loading month"),
    (15, "day of the month", "the 15th of the month"),
    ("the last published month", "EUR per tonne of CO2", "the price of the last published month, held"),
])
def test_a_value_is_written_from_its_unit(value, unit, words):
    assert methodpage.value_words(value, unit) == words


def test_every_document_linked_is_in_the_repository(method):
    for document in method["documents"]:
        path = document["href"].split("/blob/main/")[-1]
        assert (base.REPO_ROOT / path).exists(), document["href"]


def test_the_count_of_charter_rates_follows_the_list(method):
    # The Method view counts them from the list; the README spells the count
    # out, and must be reworded when a rate is added.
    from lngarb import freight_anchors

    held = len(freight_anchors.ANCHORS)
    counts = [s["value"] for item in method["limits"] for s in item if s.get("field") == "anchors"]
    assert counts == [held]
    spelled = {8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen"}
    readme = (base.REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "The study holds " + spelled[held] + " rates" in readme
