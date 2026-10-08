"""The work this pipeline cannot do for itself, and the code that records it.

Some sources may not be fetched by code, because their terms or their robots
file forbid it, and some publish documents that disappear. That work is done by
hand, and forgetting it silently degrades the data, so it is written into the
manifest rather than into a README nobody opens. Each step says what it is, why
it exists, what skipping it costs, and how to do it.

apply() is pure and idempotent. lngarb.sources.base.manifest_upsert calls it on
every write, so no single adapter run can strip the steps from the manifest.
"""

from __future__ import annotations

from typing import Any

__all__ = ["MANUAL_STEPS", "MANUAL_STEPS_NOTE", "steps_by_series", "apply"]


MANUAL_STEPS: tuple[dict[str, Any], ...] = (
    {
        "id": "eia_ngwu_archive_by_hand",
        "series": ["eia_ngwu_international_weekly"],
        "what": (
            "The archived issues of EIA's Natural Gas Weekly Update, every issue the "
            "index lists from 2016, are read from the Internet Archive's earliest "
            "capture of each and kept privately in data/private/ngwu/. Done on 7 October "
            "2026: 488 issues saved, 207 of them carrying the international prices item, "
            "from 16 September 2021 to 22 January 2026."
        ),
        "why": (
            "eia.gov's robots.txt disallows /naturalgas/weekly/archivenew_ngwu for every "
            "automated client, so this pipeline never requests the archive from eia.gov. "
            "The Internet Archive's copies are read instead, on its terms, which grant "
            "access for scholarship and research. The saved pages are not committed; the "
            "parsed item text and values are."
        ),
        "cost_if_skipped": (
            "None while the committed cache stands: every week is in it, with the item "
            "text it was read from. A rebuild from nothing without the saved pages would "
            "have one week, the final issue the landing page still serves."
        ),
        "how": (
            "python -m lngarb.sources.eia_ngwu --from-internet-archive saves every listed "
            "issue not yet saved, from its earliest capture, with a pause of four seconds "
            "between requests, logs each capture in "
            "data/private/ngwu/internet_archive_captures.jsonl, then parses the issues. "
            "An issue the Internet Archive does not hold can be saved by hand from a "
            "browser as data/private/ngwu/YYYY/MM_DD.html."
        ),
        "cadence": "once, the series has ended",
        "status": "done, 7 October 2026",
    },
    {
        "id": "eia_wngsr_weekly_collection",
        "series": ["eia_wngsr_international_weekly"],
        "what": (
            "The WNGSR Supplement's current issue has to be collected every week, after its "
            "Thursday release. Of the 34 issues released before collection started, from "
            "29 January to 17 September 2026, five are read from the Internet Archive's "
            "copies and the other 29 were read in a browser from EIA's archive pages on 8 "
            "October 2026 (the issue of 2 April both ways, with the same text); none is "
            "missing."
        ),
        "why": (
            "Only the current issue is on a path robots.txt allows. Every past issue sits "
            "under /naturalgas/weekly/supplement/archive/, which /*archive/ disallows."
        ),
        "cost_if_skipped": (
            "A week not collected while current has to be read from its archive page in a "
            "browser, unless the Internet Archive happened to capture the issue's files "
            "that week, in the only weekly JKM and TTF series EIA still publishes."
        ),
        "how": (
            "python scripts/refresh.py --only eia-weekly each week after the Thursday "
            "release. No scheduled job runs it yet, so until one does it is run by hand. "
            "Past issues the Internet Archive captured: python -m lngarb.sources.eia_ngwu "
            "--from-internet-archive saves them under data/private/wngsr/. Others: open "
            "https://www.eia.gov/naturalgas/weekly/supplement/archive/YYYY/MM/DD/ (the "
            "release day) in a browser and append the text it shows, as one JSON line "
            "with url, header (the line from 'For week ending' to the next release "
            "date), bullets (the items of the list holding the two prices), source (the "
            "'Data source' line) and read_at (UTC), to "
            "data/private/wngsr/archive_pages.jsonl; the next run reads it."
        ),
        "cadence": (
            "weekly, after the Thursday release, which EIA's schedule gives as "
            "'Thursday by 5:00 p.m.' with no time zone"
        ),
        "status": "standing",
    },
    {
        "id": "acer_reports_by_hand",
        "series": ["acer_lng_daily"],
        "what": (
            "ACER's daily LNG price assessments are on its TERMINAL platform only. "
            "TERMINAL's historical download, one CSV file with every day ACER published "
            "from 19 January 2023, has to be saved by hand; the download of 8 October "
            "2026 is held."
        ),
        "why": (
            "This pipeline does not access TERMINAL by code. ACER corrects values in "
            "place, so a download kept is also the record of what was published then."
        ),
        "cost_if_skipped": (
            "Without a new download the observed Northwest Europe discount stops at the "
            "last day held, and later dates take the labelled assumption."
        ),
        "how": (
            "Open https://aegis.acer.europa.eu/terminal/price_assessments in a browser, "
            "download the price assessments history ('PA historical') into "
            "data/private/acer/ keeping TERMINAL's file name, then run python "
            "scripts/refresh.py --only acer."
        ),
        "cadence": "whenever the history should be extended, ideally each month",
        "status": "done, 8 October 2026; repeat to extend",
    },
    {
        "id": "meti_monthly_pdfs_by_hand",
        "series": ["meti_spot_lng_monthly", "meti_spot_lng_releases"],
        "what": (
            "METI's monthly spot LNG releases, one PDF per month from March 2014 to "
            "March 2021, have to be saved from a browser to recover the preliminary "
            "figures. Nineteen are held, the releases for October 2019 to March 2021 "
            "and the detailed one for March 2021, which cover the cancellation notices "
            "of every cargo loading in 2020; the 67 earlier ones are not."
        ),
        "why": (
            "METI's site answers automated requests with a bot challenge after a few "
            "files, and this pipeline does not get around a challenge. The historical "
            "workbook, read once, carries every month's latest figure but drops the "
            "preliminary ones."
        ),
        "cost_if_skipped": (
            "None to the monthly series, which is complete from the workbook. The "
            "releases series holds only the releases saved: without the earlier PDFs the "
            "study cannot show how METI's preliminary figures were revised before "
            "October 2019."
        ),
        "how": (
            "Open https://www.meti.go.jp/english/statistics/sho/slng/index.html in a "
            "browser and save each monthly PDF into data/private/meti/pdf/ under the "
            "name the page links it by, then run python scripts/refresh.py --only meti. "
            "The PDFs stay private; the figures they print are committed as "
            "meti_spot_lng_releases."
        ),
        "cadence": "once, the survey has ended",
        "status": "partly done, 8 October 2026: 19 of 86 releases saved",
    },
)

MANUAL_STEPS_NOTE = (
    "Work this pipeline cannot do for itself. Each entry says what it is, why it exists, "
    "what it costs to skip it and how to do it. They are repeated against the series they "
    "affect in the manual_step field of those entries."
)


def steps_by_series() -> dict[str, list[dict]]:
    """series name -> the steps that affect it, each without its series list."""
    out: dict[str, list[dict]] = {}
    for step in MANUAL_STEPS:
        for name in step["series"]:
            out.setdefault(name, []).append(
                {k: v for k, v in step.items() if k != "series"}
            )
    return out


def apply(payload: dict) -> dict:
    """Attach the manual steps to a manifest payload, in place. Idempotent.

    A series named by a step gets that step in manual_step; a series named by
    none has the field removed, so a step that stops applying stops being
    printed instead of lingering on the provenance panel.
    """
    by_series = steps_by_series()
    for entry in payload.get("series", []):
        steps = by_series.get(entry.get("series"))
        if steps:
            entry["manual_step"] = steps
        else:
            entry.pop("manual_step", None)
    payload["manual_steps"] = [dict(step) for step in MANUAL_STEPS]
    payload["manual_steps_note"] = MANUAL_STEPS_NOTE
    return payload
