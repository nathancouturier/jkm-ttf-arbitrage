"""The optional private layer: its files are checked, refused whole when wrong, and never published."""

from __future__ import annotations

import subprocess

import pandas as pd
import pytest

from lngarb.sources import base, user_csv
from lngarb.sources.base import SourceError

HEADER = "date,series,contract_month,value,unit,source\n"


def _write(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_no_directory_means_no_layer(tmp_path):
    assert user_csv.read(tmp_path / "absent") is None
    assert user_csv.summary(None) == {"present": False}


def test_a_good_file_is_read_and_the_aligned_spread_computed(tmp_path):
    _write(tmp_path, "a.csv",
           "2026-03-18,jkm_settlement,2026-05,15.10,USD/MMBtu,an exchange's settlement file\n"
           "2026-03-18,ttf_settlement,2026-05,14.20,USD/MMBtu,an exchange's settlement file\n"
           "2026-03-18,ttf_settlement,2026-04,14.60,USD/MMBtu,an exchange's settlement file\n"
           "2026-03-18,freight_rate,,92000,USD/day,a broker's report\n")
    frame = user_csv.read(tmp_path)
    assert len(frame) == 4
    spread = user_csv.aligned_spread(frame)
    assert spread["contract_month"].tolist() == ["2026-05"]
    assert spread["spread"].iloc[0] == pytest.approx(0.9)
    assert user_csv.summary(frame) == {"present": True, "rows": 4, "first": "2026-03-18", "last": "2026-03-18",
                                       "series": ["freight_rate", "jkm_settlement", "ttf_settlement"]}


@pytest.mark.parametrize("row, words", [
    ("2026-03-18,jkm_settlement,,15.1,USD/MMBtu,x\n", "contract month"),
    ("2026-03-18,jkm_settlement,2026-05,,USD/MMBtu,x\n", "not a number"),
    ("2026-03-18,jkm_settlement,2026-05,0,USD/MMBtu,x\n", "outside"),
    ("2026-03-18,jkm_settlement,2026-05,15.1,EUR/MWh,x\n", "unit"),
    ("18/03/2026,jkm_settlement,2026-05,15.1,USD/MMBtu,x\n", "yyyy-mm-dd"),
    ("2026-03-18,brent,2026-05,80,USD/bbl,x\n", "not one of"),
    ("2026-03-18,freight_rate,2026-05,92000,USD/day,x\n", "no contract month"),
    ("2026-03-18,jkm_settlement,2026-05,15.1,USD/MMBtu,\n", "no source"),
    ("2026-03-18,jkm_settlement,2026-13,15.1,USD/MMBtu,x\n", "contract month"),
    ("2026-03-18,jkm_settlement,abcd-ef,15.1,USD/MMBtu,x\n", "contract month"),
    ("2026-03-18,jkm_settlement,2020-01,15.1,USD/MMBtu,x\n", "expired"),
    ("20260318,jkm_settlement,2026-05,15.1,USD/MMBtu,x\n", "yyyy-mm-dd"),
    ("2026-W12-3,jkm_settlement,2026-05,15.1,USD/MMBtu,x\n", "yyyy-mm-dd"),
    ("2999-01-04,jkm_settlement,2999-02,15.1,USD/MMBtu,x\n", "future"),
    ("2026-03-18,jkm_settlement,2026-05,nan,USD/MMBtu,x\n", "not a number"),
])
def test_a_file_that_breaks_a_rule_is_refused_whole(tmp_path, row, words):
    _write(tmp_path, "bad.csv", row)
    with pytest.raises(SourceError) as caught:
        user_csv.read(tmp_path)
    assert words in str(caught.value)


def test_wrong_columns_are_refused(tmp_path):
    (tmp_path / "x.csv").write_text("date,value\n2026-03-18,1\n", encoding="utf-8")
    with pytest.raises(SourceError, match="columns"):
        user_csv.read(tmp_path)


def test_the_layer_lives_where_git_ignores_it():
    assert user_csv.DIRECTORY.relative_to(base.REPO_ROOT).as_posix() == "data/private/user"
    probe = "data/private/user/settlements.csv"
    result = subprocess.run(["git", "check-ignore", "-q", probe], cwd=base.REPO_ROOT)
    assert result.returncode == 0, "data/private/user is not ignored by git"


def test_the_same_settlement_in_two_files_is_refused(tmp_path):
    row = "2026-03-18,jkm_settlement,2026-05,15.10,USD/MMBtu,x\n"
    _write(tmp_path, "a.csv", row)
    _write(tmp_path, "b.csv", row.replace("15.10", "15.20"))
    with pytest.raises(SourceError, match="two files"):
        user_csv.read(tmp_path)
