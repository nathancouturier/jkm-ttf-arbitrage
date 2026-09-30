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
            "The archived issues of EIA's Natural Gas Weekly Update, from the first issue "
            "carrying the international futures prices item to January 2026, have to be "
            "saved from a browser. At most 290 issues from January 2020; the index of "
            "every issue is in data/cache/eia_ngwu_issue_index.csv."
        ),
        "why": (
            "eia.gov's robots.txt disallows /naturalgas/weekly/archivenew_ngwu for every "
            "automated client, so this pipeline does not fetch the archive. Only the final "
            "issue, still served at the landing page, is read by code."
        ),
        "cost_if_skipped": (
            "The weekly JKM and TTF series has one observation, the week ending 21 January "
            "2026. Every weekly chart and test before 2026 has no EIA data, and after March "
            "2021 no public monthly JKM exists in this study either."
        ),
        "how": (
            "Open https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/YYYY/MM_DD/ for each "
            "folder in the index, save the page as HTML only to data/private/ngwu/YYYY/MM_DD.html, "
            "then run python -m lngarb.sources.eia_ngwu. The saved pages stay private; the "
            "parsed item text and values are committed."
        ),
        "cadence": "once, the series has ended",
        "status": "outstanding",
    },
    {
        "id": "eia_wngsr_weekly_collection",
        "series": ["eia_wngsr_international_weekly"],
        "what": (
            "The WNGSR Supplement's current issue has to be collected every week, after its "
            "Thursday release. Issues released before collection started, from 29 January "
            "2026, have to be saved by hand."
        ),
        "why": (
            "Only the current issue is on a path robots.txt allows. Every past issue sits "
            "under /naturalgas/weekly/supplement/archive/, which /*archive/ disallows."
        ),
        "cost_if_skipped": (
            "A week not collected while current becomes a gap that only a hand saved copy "
            "can fill, in the only weekly JKM and TTF series EIA still publishes."
        ),
        "how": (
            "python -m lngarb.sources.eia_ngwu each week after the Thursday release; the "
            "scheduled refresh does it. Past issues: open the archived issue in a browser "
            "and save it under data/private/wngsr/, a reader for which is added once the "
            "first saved copy shows what the archived page holds."
        ),
        "cadence": (
            "weekly, after the Thursday release, which EIA's schedule gives as "
            "'Thursday by 5:00 p.m.' with no time zone"
        ),
        "status": "standing",
    },
    {
        "id": "meti_monthly_pdfs_by_hand",
        "series": ["meti_spot_lng_monthly"],
        "what": (
            "METI's monthly spot LNG releases, one PDF per month from March 2014 to "
            "March 2021, have to be saved from a browser to recover the preliminary "
            "figures. Nine are held (August 2020 to March 2021); 77 are not."
        ),
        "why": (
            "METI's site answers automated requests with a bot challenge after a few "
            "files, and this pipeline does not get around a challenge. The historical "
            "workbook, read once, carries every month's latest figure but drops the "
            "preliminary ones."
        ),
        "cost_if_skipped": (
            "None to the series itself, which is complete from the workbook. Without "
            "the PDFs the study cannot show how METI's preliminary figures were "
            "revised before August 2020."
        ),
        "how": (
            "Open https://www.meti.go.jp/english/statistics/sho/slng/index.html in a "
            "browser and save each monthly PDF into data/private/meti/pdf/ under the "
            "name the page links it by. The PDFs stay private; a reader for them is "
            "added once they are collected."
        ),
        "cadence": "once, the survey has ended",
        "status": "outstanding",
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
