"""The Federal Reserve Board's release packages: one XML file per release, every series in it.

The Board publishes each statistical release (H.10 for exchange rates, H.15
for interest rates) as a zip holding one SDMX-ML file with every series of the
release and its whole history. The route the Board says will remain once its
Data Download Program is retired is this package on the release page. One
series is read from it at a time, by its SERIES_NAME, never by position.

Every observation carries OBS_STATUS: A is a value, and NA, ND and NC say why
there is none; the value printed with them, -9999, is a sentinel that must
never become a number. The structure files of both releases define the same
four codes.
"""

from __future__ import annotations

import io
import math
import zipfile
from xml.etree import ElementTree

import pandas as pd

from .base import SourceError

__all__ = ["NOT_A_VALUE", "parse_release_series"]

#: OBS_STATUS codes the release structure files define: A normal, NA not
#: available, ND no data, NC not calculable. Only A carries a value.
NOT_A_VALUE = frozenset({"NA", "ND", "NC"})


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_release_series(
    payload: bytes,
    *,
    member: str,
    series_name: str,
    description: str,
    first_day: pd.Timestamp | None,
    value_column: str,
) -> tuple[pd.DataFrame, str]:
    """One series of a release package, from first_day, and the time the package was prepared.

    Returns a frame with the columns date, value_column and obs_status. Raises
    SourceError when the package is not a zip holding the member, the series is
    missing or appears twice, its UNIT_MULT is not 1, its description is not
    the one expected (so the unit or the direction of a quote cannot be
    assumed), an observation carries an unknown status, or the package carries
    no Prepared time.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
        handle = archive.open(member)
    except (zipfile.BadZipFile, KeyError) as exc:
        raise SourceError("the download is not the release package holding %s: %s" % (member, exc)) from exc

    prepared = None
    found = 0
    in_series = False
    described = False
    rows: list[dict] = []
    with handle:
        for event, element in ElementTree.iterparse(handle, events=("start", "end")):
            name = _local(element.tag)
            if event == "end" and name == "Prepared" and prepared is None:
                prepared = (element.text or "").strip()
            if name == "Series":
                if event == "start":
                    in_series = element.attrib.get("SERIES_NAME") == series_name
                    if in_series:
                        found += 1
                        if element.attrib.get("UNIT_MULT") != "1":
                            raise SourceError(
                                "%s has UNIT_MULT %r" % (series_name, element.attrib.get("UNIT_MULT"))
                            )
                else:
                    in_series = False
                    element.clear()
                continue
            if not in_series or event != "end":
                continue
            if name == "AnnotationText" and (element.text or "").strip() == description:
                described = True
            elif name == "Obs":
                status = element.attrib.get("OBS_STATUS")
                day = pd.Timestamp(element.attrib["TIME_PERIOD"])
                if first_day is None or day >= first_day:
                    if status == "A":
                        value = float(element.attrib["OBS_VALUE"])
                    elif status in NOT_A_VALUE:
                        value = math.nan
                    else:
                        raise SourceError(
                            "%s on %s has unknown OBS_STATUS %r" % (series_name, day.date(), status)
                        )
                    rows.append({"date": day, value_column: value, "obs_status": status})
                element.clear()

    if found != 1:
        raise SourceError("%s appears %d times in %s" % (series_name, found, member))
    if not described:
        raise SourceError(
            "%s is not described as %r in its annotations; what it quotes cannot be assumed"
            % (series_name, description)
        )
    if not prepared:
        raise SourceError("the XML carries no Prepared time")
    if not rows:
        raise SourceError("%s carries no observation from %s" % (series_name, first_day))
    frame = pd.DataFrame(rows).sort_values("date", kind="mergesort").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise SourceError("%s repeats a day" % series_name)
    return frame, prepared
