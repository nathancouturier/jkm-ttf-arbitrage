"""Everything the study declares: its sources, its checks, and later its parameters.

This module holds three kinds of declaration.

    the source registry     one Source per series or seed file, with its
                            publisher, pages, frequency, method, licence and
                            whether its cache may be published
    the validation bounds   the ranges a value must sit in before it is allowed
                            into a cache
    the region map          every destination country in EIA's export table,
                            mapped to the region the flow analysis uses

The engine's parameters, each with a value, a unit, a status, a source URL and
the date it was read, are added to this module with the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

# ---------------------------------------------------------------------------
# Validation bounds, checked on every write. See docs/methodology.md.
# ---------------------------------------------------------------------------

#: JKM, TTF and Japanese spot LNG, USD/MMBtu
BOUNDS_LNG_USD_MMBTU = (1.0, 120.0)
#: Henry Hub, USD/MMBtu
BOUNDS_HENRY_HUB_USD_MMBTU = (0.5, 25.0)
#: US dollars per euro
BOUNDS_USD_PER_EUR = (0.8, 1.7)
#: reported LNG carrier hire, USD per day. Negative is possible: Spark's
#: Atlantic rate was assessed negative on 8 February 2022.
BOUNDS_HIRE_USD_DAY = (-10000.0, 500000.0)
#: ACER DES LNG spreads to the TTF front month, EUR/MWh
BOUNDS_DES_SPREAD_EUR_MWH = (-20.0, 5.0)
#: A DES LNG price level, EUR/MWh, as ACER assesses it. A guard against a unit
#: or a parse error, not a range the market implies.
BOUNDS_DES_EUR_MWH = (1.0, 400.0)
#: An EU allowance price, EUR per tonne of CO2. A guard against a unit or a
#: parse error, not a range the market implies.
BOUNDS_EUA_EUR_T = (1.0, 200.0)
#: SOFR, percent per year. Not a range the market implies, a guard against a
#: unit error: a rate read in basis points would be a hundred times too large.
BOUNDS_SOFR_PERCENT = (-1.0, 15.0)
#: US natural gas exports in one month, MMcf, any block or total. Not a range
#: the market implies, a guard against a unit or a parse error: the largest
#: monthly LNG total in the 31 August 2026 release is 539,203 MMcf.
BOUNDS_EXPORTS_MMCF = (0.0, 2000000.0)

# ---------------------------------------------------------------------------
# Destination regions for the flow analysis
# ---------------------------------------------------------------------------

#: The regions US LNG exports are grouped into. JKM markets are the four
#: countries JKM assesses delivery to.
REGIONS: Mapping[str, str] = MappingProxyType(
    {
        "jkm_markets": "JKM markets (Japan, South Korea, China, Taiwan)",
        "other_asia": "Other Asia",
        "europe": "Europe (the EU, the UK, Norway and Turkiye)",
        "middle_east_africa": "Middle East and Africa",
        "americas": "The Americas",
    }
)


@dataclass(frozen=True)
class Destination:
    """One destination country of EIA's export table and the region it counts in."""

    #: the country as EIA's series names spell it
    country: str
    #: a key of REGIONS
    region: str
    #: why a borderline country sits where it does, empty when it is not borderline
    note: str = ""

    def __post_init__(self) -> None:
        if self.region not in REGIONS:
            raise ValueError("%s is mapped to unknown region %r" % (self.country, self.region))


#: Every destination code in EIA's table of US natural gas exports by country,
#: keyed by the three characters that end each series id
#: (NGM_EPG0_EVE_NUS-NJA_MMCF is Japan). The exports adapter refuses a code that
#: is not here, so a new destination fails loudly instead of dropping out of a
#: regional total.
EIA_DESTINATIONS: Mapping[str, Destination] = MappingProxyType(
    {
        # JKM markets
        "NJA": Destination("Japan", "jkm_markets"),
        "NKS": Destination("South Korea", "jkm_markets"),
        "NCH": Destination("China", "jkm_markets"),
        "NTW": Destination("Taiwan", "jkm_markets"),
        # Other Asia
        "NBG": Destination("Bangladesh", "other_asia"),
        "NIN": Destination("India", "other_asia"),
        "NID": Destination("Indonesia", "other_asia"),
        "NMY": Destination("Malaysia", "other_asia"),
        "NPK": Destination("Pakistan", "other_asia"),
        "NRP": Destination("Philippines", "other_asia"),
        "NSN": Destination(
            "Singapore",
            "other_asia",
            "A trading and bunkering hub. Counted with other Asia, not with the JKM "
            "markets, because JKM assesses delivery to Japan, South Korea, China and "
            "Taiwan only.",
        ),
        "NTH": Destination("Thailand", "other_asia"),
        # Europe
        "NBE": Destination("Belgium", "europe"),
        "NHR": Destination("Croatia", "europe"),
        "NFI": Destination("Finland", "europe"),
        "NFR": Destination("France", "europe"),
        "NGM": Destination("Germany", "europe"),
        "NGR": Destination("Greece", "europe"),
        "NIT": Destination("Italy", "europe"),
        "NLH": Destination("Lithuania", "europe"),
        "NM6": Destination("Malta", "europe"),
        "NNL": Destination("Netherlands", "europe"),
        "NPL": Destination("Poland", "europe"),
        "NPO": Destination("Portugal", "europe"),
        "NSP": Destination("Spain", "europe"),
        "NUK": Destination("United Kingdom", "europe"),
        "NTU": Destination(
            "Turkiye",
            "europe",
            "Counted with Europe, as the region is defined for this study. A cargo "
            "from the US Gulf reaches it through the Mediterranean with no canal, "
            "like the European destinations.",
        ),
        "NRS": Destination(
            "Russia",
            "europe",
            "EIA's table records one volume, 1,895 MMcf in October 2007, and nothing "
            "since. Counted with Europe for completeness; it carries no volume in the "
            "study period, so the choice changes no result.",
        ),
        # Middle East and Africa
        "NBA": Destination("Bahrain", "middle_east_africa"),
        "NEG": Destination("Egypt", "middle_east_africa"),
        "NIS": Destination("Israel", "middle_east_africa"),
        "NJO": Destination("Jordan", "middle_east_africa"),
        "NKU": Destination("Kuwait", "middle_east_africa"),
        "NTC": Destination("United Arab Emirates", "middle_east_africa"),
        "NMR": Destination(
            "Mauritania",
            "middle_east_africa",
            "One volume in the table, 517 MMcf in July 2024, the same figure as "
            "Senegal's that month.",
        ),
        "NSG": Destination("Senegal", "middle_east_africa"),
        # The Americas
        "NAC": Destination("Antigua and Barbuda", "americas"),
        "NAT": Destination("Argentina", "americas"),
        "NBF": Destination("Bahamas", "americas"),
        "NBB": Destination("Barbados", "americas"),
        "NBR": Destination("Brazil", "americas"),
        "NCA": Destination(
            "Canada",
            "americas",
            "In the LNG by vessel block EIA names this series 'from Canada', not "
            "'to Canada'; it holds one value, 3,477 MMcf in January 2026. Counted "
            "with the Americas; what the label means is an open question.",
        ),
        "NCI": Destination("Chile", "americas"),
        "NCO": Destination("Colombia", "americas"),
        "NDR": Destination("Dominican Republic", "americas"),
        "NES": Destination("El Salvador", "americas"),
        "NHA": Destination("Haiti", "americas"),
        "NJM": Destination("Jamaica", "americas"),
        "NMX": Destination("Mexico", "americas"),
        "NNU": Destination("Nicaragua", "americas"),
        "NPM": Destination("Panama", "americas"),
    }
)

# ---------------------------------------------------------------------------
# The source registry
# ---------------------------------------------------------------------------

#: The frequencies this project handles. Gap detection needs to know which one a
#: series is, because a missing weekday in a weekly series is not a gap.
FREQUENCIES = ("daily", "weekly", "monthly", "annual")

#: How a series came to exist.
#:
#:     published      the source published exactly this series, machine readable
#:     parsed         extracted from a document the source published, a PDF
#:                    table or the text of a web page
#:     reconstructed  recovered from a published chart, with a measured error
#:     derived        computed by this project from other series or tools
#:     seed           committed by hand from a cited document, never fetched
METHODS = ("published", "parsed", "reconstructed", "derived", "seed")


@dataclass(frozen=True)
class Source:
    """One series this project builds, and everything provenance needs about it.

    machine_url is None when the URL cannot be hardcoded and has to be
    discovered; url_note then says what to look for, and the adapter must fail
    loudly when it cannot find it rather than guess.
    """

    #: cache file stem and the series name in the manifest
    series: str
    #: one sentence a human reads on the provenance panel
    label: str
    #: who published it
    publisher: str
    #: the human readable page, always present, always linkable
    page_url: str
    #: the machine readable file, or None when it has to be discovered
    machine_url: str | None
    #: what to do when machine_url is None, or what is odd about it
    url_note: str
    #: one of FREQUENCIES
    frequency: str
    #: the unit of the value columns
    unit: str
    #: one of METHODS
    method: str
    #: the licence, named
    licence: str
    #: what the licence permits and what it does not, in plain words
    licence_note: str
    #: whether the cache may be committed to a public repository. False sends
    #: the cache to data/private/ and keeps it out of the deploy.
    committable: bool

    def __post_init__(self) -> None:
        if self.frequency not in FREQUENCIES:
            raise ValueError(
                "source %r declares frequency %r, not one of %s"
                % (self.series, self.frequency, ", ".join(FREQUENCIES))
            )
        if self.method not in METHODS:
            raise ValueError(
                "source %r declares method %r, not one of %s"
                % (self.series, self.method, ", ".join(METHODS))
            )
        if not self.licence_note:
            raise ValueError(
                "source %r carries no licence_note. Every source states what its "
                "terms permit" % (self.series,)
            )
        if not self.committable and "not" not in self.licence_note.lower():
            raise ValueError(
                "source %r is not committable but its licence_note does not say "
                "what is forbidden" % (self.series,)
            )


def _registry(*sources: Source) -> Mapping[str, Source]:
    seen: dict[str, Source] = {}
    for item in sources:
        if item.series in seen:
            raise ValueError("two sources both claim the series name %r" % item.series)
        seen[item.series] = item
    return MappingProxyType(seen)


# Licence notes paraphrase what docs/sources.md quotes verbatim, with the URL
# each quotation was read from and the date.

_EIA_NOTE = (
    "US government publications are in the public domain. EIA's reuse page says "
    "'You may use and/or distribute any of our data, files, databases, reports, "
    "graphs, charts, and other information products', with an acknowledgment "
    "that includes the publication date."
)

_EIA_BLOOMBERG_NOTE = (
    _EIA_NOTE + " One doubt, recorded rather than resolved: these weekly prices "
    "are credited in the text to Bloomberg Finance L.P., and the same page says "
    "material 'contributed or licensed by private individuals, companies, or "
    "organizations' 'may be protected'. Whether figures EIA prints under a "
    "third party's credit fall under that sentence is not settled by the page. "
    "The parsed weekly values are committed with the credit shown wherever they "
    "are used, and the question is open with the owner and EIA."
)

_EIA_ROBOTS_NOTE = (
    "eia.gov's robots.txt disallows /naturalgas/weekly/archivenew_ngwu for every "
    "user agent, so no archived issue is fetched by code. Code reads the landing "
    "page, which still serves the final issue; every other issue is read from a "
    "copy saved by hand into data/private/ngwu/YYYY/MM_DD.html."
)


_EIA_REFINITIV_NOTE = (
    _EIA_NOTE + " One doubt, recorded rather than resolved: EIA's definitions "
    "page for this table credits the spot price to 'Refinitiv, an LSEG "
    "business', and EIA's reuse page says material 'contributed or licensed by "
    "private individuals, companies, or organizations' 'may be protected'. The "
    "daily values are committed with that credit shown wherever they are used, "
    "and the question is open with the owner."
)


_WORLDBANK_NOTE = (
    "The World Bank's dataset terms: 'Unless specifically labeled otherwise, these "
    "Datasets are provided to you under a Creative Commons Attribution 4.0 "
    "International License (CC BY 4.0)', and the Pink Sheet's catalogue entry says "
    "the same. Attribute to The World Bank, Commodity Price Data (The Pink Sheet), "
    "and do not imply its endorsement. One residual, recorded: the terms say some "
    "datasets are provided by third parties and may carry extra conditions in their "
    "metadata, and the gas rows credit Bloomberg Finance L.P., World Gas "
    "Intelligence and others; the catalogue entry names no extra condition."
)

_H10_NOTE = (
    "The Federal Reserve Board: 'Unless otherwise indicated, information on Board's "
    "website is in the public domain and may be copied and distributed without "
    "permission. Please cite to the Board as the source of the information.' "
    "Nothing read marks the H.10 euro rate as third party material."
)

_SOFR_NOTE = (
    "Licensed, not public domain. The New York Fed's Terms of Use grant a "
    "non-exclusive licence to use, copy and distribute its content, on conditions: "
    "its attribution line, the reference rate notice and disclaimer wherever the "
    "rate is shown, redistribution 'with the same permissions, conditions, and "
    "restrictions', modified content labelled as not the New York Fed's, and no "
    "implied endorsement. The committed cache is distributed under those terms, not "
    "under this repository's MIT licence. SOFR is calculated from data licensed to "
    "the New York Fed by DTCC Solutions LLC."
)


_METI_NOTE = (
    "METI's terms: 'you may use the Content under the terms of use if you comply "
    "with the Public Data License (Version 1.0; PDL 1.0)', and 'The Terms of Use are "
    "compatible with the Creative Commons Attribution License 4.0'. Cite the source "
    "and, because the series is edited into a monthly table here, say so: 'Created "
    "by processing the information in the Spot LNG Price Statistics (Ministry of "
    "Economy, Trade and Industry of Japan)'. Edited data must not be presented as "
    "made by the Government of Japan."
)


_ACER_NOTE = (
    "ACER's legal notice: 'Information and documents made available on the "
    "Agency's webpages are public and may be reproduced and/or distributed, "
    "totally or in part, ... for non-commercial and commercial purposes, provided "
    "that the Agency is always acknowledged as the source of the material', and "
    "ACER's PDFs say 'Reproduction is authorised provided the source is "
    "acknowledged'. One doubt, recorded: the same notice's first paragraph "
    "prohibits reuse of 'this Licensed Material' without saying what that is. The "
    "benchmark's TTF leg is ICE data; ACER's prices and spreads are published, a "
    "TTF level derived from them never is."
)


_EC_NOTE = (
    "The Commission's legal notice: 'Unless otherwise indicated (e.g. in individual "
    "copyright notices), content owned by the EU on this website is licensed under "
    "the Creative Commons Attribution 4.0 International (CC BY 4.0) licence', which "
    "'means that reuse is allowed, provided appropriate credit is given and changes "
    "are indicated.' The reports carry no individual copyright notice. One doubt, "
    "recorded: the tables compile information the auction platform provides, and "
    "whether they are content owned by the EU is not stated."
)


SOURCES: Mapping[str, Source] = _registry(
    # -- European Commission, EUA -----------------------------------------
    Source(
        series="ec_eua_auction_monthly",
        label="EU allowance price, monthly volume weighted average auction clearing price, EUR per tonne of CO2",
        publisher="European Commission, Auctions by the Common Auction Platform",
        page_url="https://climate.ec.europa.eu/areas-action/carbon-markets/eu-emissions-trading-system-eu-ets/auctioning-allowances_en",
        machine_url=None,
        url_note=(
            "Quarterly PDF reports linked from the page, cap_report_YYYYMM_en.pdf, "
            "each with a fifteen month Table 1. Read from the report for the quarter "
            "ending March 2024. The latest on 30 September 2026 ends in June 2025."
        ),
        frequency="monthly",
        unit="EUR per tonne of CO2",
        method="parsed",
        licence="CC BY 4.0",
        licence_note=_EC_NOTE,
        committable=True,
    ),
    # -- ACER -------------------------------------------------------------
    Source(
        series="acer_lng_daily",
        label="ACER DES LNG assessments for NWE, SE and the EU, and the EU benchmark to TTF, daily, EUR/MWh",
        publisher="European Union Agency for the Cooperation of Energy Regulators",
        page_url="https://www.acer.europa.eu/gas/lng-price-assessment",
        machine_url="https://www.acer.europa.eu/sites/default/files/documents/en/Gas/LNG_Price_Assessment/LNGPA_Correction_Notice_20241220.pdf",
        url_note=(
            "The daily reports are on ACER's TERMINAL platform, which this pipeline "
            "does not fetch; they are saved by hand. Code reads only ACER's main "
            "site: the correction notice of 20 December 2024 and the methodology's "
            "annex of half-month roll dates."
        ),
        frequency="daily",
        unit="EUR per MWh",
        method="parsed",
        licence="ACER legal notice, reproduction with acknowledgement",
        licence_note=_ACER_NOTE,
        committable=True,
    ),
    # -- METI -------------------------------------------------------------
    Source(
        series="meti_spot_lng_monthly",
        label="Japan spot LNG price, monthly, DES, USD/MMBtu, contract-based and arrival-based, METI, March 2014 to March 2021",
        publisher="Ministry of Economy, Trade and Industry of Japan, Spot LNG Price Statistics",
        page_url="https://www.meti.go.jp/english/statistics/sho/slng/index.html",
        machine_url="https://www.meti.go.jp/english/statistics/sho/slng/historical-data-e.xlsx",
        url_note=(
            "The historical workbook, fetched once and not refetched: METI's site "
            "answers automated requests with a bot challenge after a handful of "
            "files, and the survey ended with March 2021. The monthly PDFs, which "
            "alone carry the preliminary figures, are a manual step."
        ),
        frequency="monthly",
        unit="USD per MMBtu, DES",
        method="published",
        licence="METI terms of use, compatible with CC BY 4.0",
        licence_note=_METI_NOTE,
        committable=True,
    ),
    Source(
        series="jogmec_spot_lng_monthly",
        label="Japan spot LNG price, monthly, DES, contract-based and arrival-based, JOGMEC, from April 2021, private",
        publisher="Japan Organization for Metals and Energy Security",
        page_url="https://journal.jogmec.go.jp/oilgas/nglng-en/spotprice/index.html",
        machine_url="https://journal.jogmec.go.jp/oilgas/nglng-en/spotprice/index.html",
        url_note=(
            "One page per month, YYYYMM-preliminary.html, linked from the list page; "
            "the confirmed figure of a month is printed on the next month's page. "
            "Pages are edited in place and have been renamed once."
        ),
        frequency="monthly",
        unit="USD per MMBtu, DES (JOGMEC writes USD/MBtu)",
        method="parsed",
        licence="JOGMEC terms of use, permission requested",
        licence_note=(
            "JOGMEC's terms do not permit use beyond private use, education and "
            "quotation without its prior permission. Kept in data/private/ and not "
            "published until permission is granted."
        ),
        committable=False,
    ),
    # -- World Bank, Federal Reserve Board, New York Fed -------------------
    Source(
        series="worldbank_gas_monthly",
        label="World Bank Pink Sheet gas prices, monthly, USD/MMBtu: Europe, US Henry Hub, Japan LNG import price",
        publisher="The World Bank, Commodity Price Data (The Pink Sheet)",
        page_url="https://www.worldbank.org/en/research/commodity-markets",
        machine_url=None,
        url_note=(
            "CMO-Historical-Data-Monthly.xlsx, linked from the page; the document "
            "id in its path changes, so the link is read from the page and the "
            "adapter fails when it finds none or several. Sheet 'Monthly Prices', "
            "series found by label and checked by unit. A hidden sheet comes first "
            "in the workbook."
        ),
        frequency="monthly",
        unit="USD per MMBtu",
        method="published",
        licence="CC BY 4.0",
        licence_note=_WORLDBANK_NOTE,
        committable=True,
    ),
    Source(
        series="worldbank_gas_revisions",
        label="Every value a Pink Sheet release changed, release against release",
        publisher="The World Bank, compared release by release by this study",
        page_url="https://www.worldbank.org/en/research/commodity-markets",
        machine_url=None,
        url_note="Written by the World Bank adapter when a new release differs from the committed one.",
        frequency="monthly",
        unit="USD per MMBtu",
        method="derived",
        licence="CC BY 4.0",
        licence_note=_WORLDBANK_NOTE,
        committable=True,
    ),
    Source(
        series="h10_usd_per_eur_daily",
        label="US dollars per euro, daily noon buying rate in New York, Federal Reserve H.10",
        publisher="Board of Governors of the Federal Reserve System, H.10",
        page_url="https://www.federalreserve.gov/releases/h10/hist/dat00_eu.htm",
        machine_url="https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip",
        url_note=(
            "The release page's XML package, series RXI$US_N.B.EU, the route the "
            "Board says will remain; its Data Download Program is being retired "
            "from the week of 9 November 2026. Every weekday has a row; a day with "
            "no rate carries OBS_STATUS ND and the sentinel OBS_VALUE -9999, which "
            "is read as missing and never as a price. Released weekly, on Mondays."
        ),
        frequency="daily",
        unit="US dollars per euro",
        method="published",
        licence="US public domain",
        licence_note=_H10_NOTE,
        committable=True,
    ),
    Source(
        series="nyfed_sofr_daily",
        label="Secured Overnight Financing Rate, daily, percent, from the New York Fed",
        publisher="Federal Reserve Bank of New York",
        page_url="https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates",
        machine_url="https://markets.newyorkfed.org/api/rates/secured/sofr/search.json",
        url_note=(
            "The New York Fed's markets API, with explicit startDate and endDate. "
            "Rows come newest first; days with no publication have no row; the "
            "first value date is 2 April 2018. The rate for a business day is in "
            "the API the next morning and may be revised the same day."
        ),
        frequency="daily",
        unit="percent per year",
        method="published",
        licence="New York Fed Terms of Use",
        licence_note=_SOFR_NOTE,
        committable=True,
    ),
    # -- Seeds ------------------------------------------------------------
    Source(
        series="routes",
        label="The four sea routes from Sabine Pass, their distances and their lines",
        publisher="this study, computed with searoute over Eurostat's SeaRoute maritime network",
        page_url="https://github.com/genthalili/searoute-py",
        machine_url=None,
        url_note=(
            "Computed once by scripts/routes.py with searoute 1.6.0 and committed; "
            "nothing computes a route at build time. The library is a development "
            "tool only and is not shipped with the site."
        ),
        frequency="annual",
        unit="nautical miles",
        method="derived",
        licence="Apache License 2.0 for searoute; the network's own terms in docs/sources.md",
        licence_note=(
            "The distances and lines are this study's computation, published under "
            "the repository's MIT licence. searoute is released under the Apache "
            "License 2.0 and bundles Eurostat's SeaRoute maritime network, whose "
            "terms are quoted in docs/sources.md."
        ),
        committable=True,
    ),
    # -- EIA, the data tables -------------------------------------------
    Source(
        series="eia_lng_exports_monthly",
        label="US LNG exports and re-exports by destination country, monthly, MMcf, the latest release",
        publisher="U.S. Energy Information Administration",
        page_url="https://www.eia.gov/dnav/ng/ng_move_expc_s1_m.htm",
        machine_url="https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls",
        url_note=(
            "A legacy .xls workbook read with xlrd. Series are identified by "
            "their source key, never by name or position. The LNG exports by "
            "vessel block gives destinations; the re-exports block is kept "
            "apart; N9133US2, the LNG total, includes re-exports. EIA revises "
            "the table and keeps no old release online, so each release is a "
            "vintage and changed values go to eia_lng_exports_revisions."
        ),
        frequency="monthly",
        unit="MMcf per month",
        method="published",
        licence="US public domain",
        licence_note=_EIA_NOTE,
        committable=True,
    ),
    Source(
        series="eia_lng_exports_revisions",
        label="Every value a release of EIA's exports by country table changed, both vintages side by side",
        publisher="U.S. Energy Information Administration, compared release by release by this study",
        page_url="https://www.eia.gov/dnav/ng/ng_move_expc_s1_m.htm",
        machine_url=None,
        url_note="Written by the exports adapter when a new release differs from the committed one.",
        frequency="monthly",
        unit="MMcf per month",
        method="derived",
        licence="US public domain",
        licence_note=_EIA_NOTE,
        committable=True,
    ),
    Source(
        series="eia_henry_hub_daily",
        label="Henry Hub spot price, daily, USD/MMBtu",
        publisher="U.S. Energy Information Administration, credited by EIA to Refinitiv, an LSEG business",
        page_url="https://www.eia.gov/dnav/ng/hist/rngwhhdd.htm",
        machine_url="https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls",
        url_note=(
            "Series RNGWHHD. EIA's NYMEX futures series stop on 5 April 2024. "
            "Holidays are omitted except from July 2015 to November 2017, when "
            "rows repeat the previous business day; 1997 to 2006 are sparse; "
            "2018-01-05 is a dated row with no value."
        ),
        frequency="daily",
        unit="USD per MMBtu",
        method="published",
        licence="US public domain, with the third party credit doubt",
        licence_note=_EIA_REFINITIV_NOTE,
        committable=True,
    ),
    # -- EIA, the weekly JKM and TTF averages -----------------------------
    Source(
        series="eia_ngwu_issue_index",
        label="Every Natural Gas Weekly Update issue EIA lists from 2016, the checklist for collection",
        publisher="U.S. Energy Information Administration",
        page_url="https://www.eia.gov/naturalgas/weekly/",
        machine_url="https://www.eia.gov/naturalgas/weekly/includes/archive.php",
        url_note=(
            "The index is one allowed page. Its links point into the disallowed "
            "archive and are recorded, never followed. Dates come from the folder "
            "in each link, never from the month and day cells, which are missing "
            "or wrong on several rows. Rows inside HTML comments are not read."
        ),
        frequency="weekly",
        unit="none, a list of issues",
        method="parsed",
        licence="US public domain",
        licence_note=_EIA_NOTE,
        committable=True,
    ),
    Source(
        series="eia_ngwu_international_weekly",
        label="Weekly averages of an East Asia LNG price and of TTF, USD/MMBtu, Natural Gas Weekly Update, to January 2026",
        publisher="U.S. Energy Information Administration, figures credited to Bloomberg Finance L.P.",
        page_url="https://www.eia.gov/naturalgas/weekly/",
        machine_url="https://www.eia.gov/naturalgas/weekly/",
        url_note=_EIA_ROBOTS_NOTE + (
            " The NGWU ended with the issue released on 22 January 2026, week "
            "ending 21 January 2026."
        ),
        frequency="weekly",
        unit="USD per MMBtu",
        method="parsed",
        licence="US public domain, with the third party credit doubt",
        licence_note=_EIA_BLOOMBERG_NOTE,
        committable=True,
    ),
    Source(
        series="eia_wngsr_international_weekly",
        label="Weekly averages of JKM and TTF, USD/MMBtu, WNGSR Supplement, from January 2026",
        publisher="U.S. Energy Information Administration, figures credited to Bloomberg Finance L.P.",
        page_url="https://www.eia.gov/naturalgas/weekly/supplement/",
        machine_url="https://www.eia.gov/naturalgas/weekly/supplement/content/bullets_lng_2.html",
        url_note=(
            "The page is an application shell; the current issue is assembled "
            "from content/bullets_lng_2.html, content/source_lng_2.html and "
            "content/release_dates.json, whose names come from the page's script "
            "and can change with any redeploy. Only the current issue is on an "
            "allowed path: robots.txt disallows /*archive/, which covers every "
            "past issue, so a week not collected while it is current can only "
            "be recovered by hand."
        ),
        frequency="weekly",
        unit="USD per MMBtu",
        method="parsed",
        licence="US public domain, with the third party credit doubt",
        licence_note=_EIA_BLOOMBERG_NOTE,
        committable=True,
    ),
)


def source(series: str) -> Source:
    """The registered Source for a series name, or KeyError naming it."""
    try:
        return SOURCES[series]
    except KeyError:
        raise KeyError("no source registered for series %r" % (series,)) from None
