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
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Validation bounds, checked on every write. See docs/methodology.md.
# ---------------------------------------------------------------------------

#: JKM, TTF and Japanese spot LNG, USD/MMBtu
BOUNDS_LNG_USD_MMBTU = (1.0, 120.0)
#: Henry Hub, USD/MMBtu
BOUNDS_HENRY_HUB_USD_MMBTU = (0.5, 50.0)
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
#: SOFR, and EFFR before it, percent per year. Not a range the market implies,
#: a guard against a unit error: a rate read in basis points would be a hundred
#: times too large.
BOUNDS_SOFR_PERCENT = (-1.0, 15.0)
#: US dollars per SDR. Not a range the rate implies, a guard against a rate read
#: the other way up, SDR per dollar, which would be below 1.
BOUNDS_USD_PER_SDR = (1.0, 2.0)
#: US natural gas exports in one month, MMcf, any block or total. Not a range
#: the market implies, a guard against a unit or a parse error: the largest
#: monthly LNG total in the 31 August 2026 release is 573,089 MMcf, March 2026.
BOUNDS_EXPORTS_MMCF = (0.0, 2000000.0)
#: The price of US LNG exports in one month, USD per thousand cubic feet. Not a
#: range the market implies, a guard against a unit error: a price read per
#: MMcf or in cents would be a thousand or a hundred times too large. From 2016
#: the release of 30 September 2026 runs from 1.86 to 40.44.
BOUNDS_EXPORT_PRICE_USD_MCF = (0.1, 100.0)
#: One LNG cargo, or part of one, in MMcf. Not a range the market implies, a
#: guard against a unit error: the largest row of DOE's file to July 2026 is
#: 5,277.14 MMcf, and a volume read in Mcf would be a thousand times larger.
BOUNDS_CARGO_MMCF = (0.0, 10000.0)

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
    "user agent, so no archived issue is fetched from eia.gov. Code reads the "
    "landing page, which still serves the final issue; every other issue is read "
    "from the Internet Archive's earliest capture of it, saved privately into "
    "data/private/ngwu/YYYY/MM_DD.html, and each row carries the capture it was "
    "read from."
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

_EFFR_NOTE = (
    "Licensed, not public domain, on the same terms as SOFR: the New York Fed's "
    "Terms of Use grant a non-exclusive licence to use, copy and distribute its "
    "content, with its attribution line, the reference rate notice and disclaimer "
    "wherever the rate is shown, redistribution 'with the same permissions, "
    "conditions, and restrictions', and modified content labelled as not the New "
    "York Fed's. The terms name no third party licence for EFFR, which is "
    "calculated from FR 2420 reports. The committed cache is distributed under those "
    "terms, not under this repository's MIT licence."
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
    "ACER's methodology documents say 'Reproduction is authorised provided the "
    "source is acknowledged', a line the correction notice itself does not carry. "
    "One doubt, recorded: the same notice's first paragraph "
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
        licence="JOGMEC terms of use, permission not yet requested",
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
    Source(
        series="nyfed_effr_daily",
        label="Effective federal funds rate, daily, percent, 2016 to April 2018, from the New York Fed",
        publisher="Federal Reserve Bank of New York",
        page_url="https://www.newyorkfed.org/markets/reference-rates/effr",
        machine_url="https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json",
        url_note=(
            "The New York Fed's markets API, one window from 1 January 2016 to 30 "
            "April 2018, the month after SOFR began. Rows come newest first, in two "
            "layouts either side of 1 March 2016, when the rate's source and method "
            "changed; days with no publication have no row. The series is closed."
        ),
        frequency="daily",
        unit="percent per year",
        method="published",
        licence="New York Fed Terms of Use",
        licence_note=_EFFR_NOTE,
        committable=True,
    ),
    Source(
        series="imf_usd_per_sdr_daily",
        label="US dollars per special drawing right, daily, from 2016, the IMF's rate through the Bundesbank, private",
        publisher="International Monetary Fund, as republished by the Deutsche Bundesbank",
        page_url="https://www.bundesbank.de/en/homepage/user-information/terms-of-use-642972",
        machine_url="https://api.statistiken.bundesbank.de/rest/download/BBEX3/D.USD.XDR.DA.AC.000?format=csv&lang=en",
        url_note=(
            "The Bundesbank's statistics API, series BBEX3.D.USD.XDR.DA.AC.000, no key. "
            "The IMF's own hosts refuse automated requests. Days with no rate are rows "
            "with '.', never zero."
        ),
        frequency="daily",
        unit="US dollars per SDR",
        method="published",
        licence="IMF terms, not yet read; private",
        licence_note=(
            "The IMF's terms have not been read: its hosts refuse automated requests. "
            "The Bundesbank's terms do not cover third party data without the "
            "originator's permission. Kept in data/private/ and not published until a "
            "person has read the IMF's terms."
        ),
        committable=False,
    ),
    # -- Seeds ------------------------------------------------------------
    Source(
        series="freight_anchors",
        label="Reported LNG carrier charter rates, one per month at most, each from a dated article",
        publisher="this study, from figures reported by Spark Commodities, LNG Prime and Hellenic Shipping News",
        page_url="https://lngprime.com/",
        machine_url=None,
        url_note=(
            "Written by lngarb.freight_anchors from rows kept in the code, each read by "
            "hand in a dated article; nothing is fetched. Never a series: no value is "
            "interpolated between rows."
        ),
        frequency="annual",
        unit="USD per day",
        method="seed",
        licence="individual figures quoted with attribution",
        licence_note=(
            "Each row is one figure quoted with its date, assessment, vessel, publisher "
            "and address, as fair use for a non-commercial study. No article's sentence "
            "is reproduced and no Spark document is linked or copied. Spark's terms bar "
            "republishing its content without a licence except as fair use allows; LNG "
            "Prime's forbid republishing its material; both are quoted in "
            "docs/sources.md, sections 2.13 and 2.14."
        ),
        committable=True,
    ),
    Source(
        series="routes",
        label="The four sea routes from Sabine Pass, their distances and their lines",
        publisher="this study, computed with searoute 1.6.0 over the network it bundles, which its README credits to Eurostat's Searoute",
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
        licence="distances MIT; lines EUPL 1.2; searoute Apache License 2.0",
        licence_note=(
            "The distances are this study's computation, published under the "
            "repository's MIT licence. The lines are published under the European "
            "Union Public Licence 1.2, as a work derived from the network searoute "
            "bundles, which its README credits to Eurostat's Searoute (EUPL 1.2), "
            "itself based on an Oak Ridge National Laboratory dataset. searoute is "
            "released under the Apache License 2.0. The chain is quoted in "
            "docs/sources.md."
        ),
        committable=True,
    ),
    # -- EIA, the data tables -------------------------------------------
    Source(
        series="eia_lng_exports_monthly",
        label="US LNG exports and re-exports by destination country, monthly, MMcf, and their prices, USD per Mcf, the latest release",
        publisher="U.S. Energy Information Administration",
        page_url="https://www.eia.gov/dnav/ng/ng_move_expc_s1_m.htm",
        machine_url="https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls",
        url_note=(
            "A legacy .xls workbook read with xlrd. Series are identified by "
            "their source key, never by name or position. The LNG exports by "
            "vessel block gives destinations; the re-exports block is kept "
            "apart; N9133US2, the LNG total, includes re-exports. EIA revises "
            "the table and keeps no old release online, so each release is a "
            "vintage and changed values go to eia_lng_exports_revisions. The "
            "sheet Data 2 gives each series' price, under the same key with "
            "_DMCF for _MMCF."
        ),
        frequency="monthly",
        unit="MMcf per month; prices in USD per thousand cubic feet",
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
        unit="MMcf per month; prices in USD per thousand cubic feet",
        method="derived",
        licence="US public domain",
        licence_note=_EIA_NOTE,
        committable=True,
    ),
    Source(
        series="doe_lng_export_cargoes",
        label="US LNG exports and re-exports cargo by cargo, from January 2016, MMcf, with the terminal, ship and destination",
        publisher="U.S. Department of Energy, Office of Fossil Energy and Carbon Management",
        page_url="https://www.energy.gov/hgeo/listings/natural-gas-imports-and-exports-monthly-reports",
        machine_url=None,
        url_note=(
            "The workbook 'U.S. LNG Exports and Re-Exports Details (Jan 2016 - "
            "<month> <year>)' is linked from the year's report page, which is "
            "linked from the list of report pages; both addresses change, so "
            "both are read every time and the parse fails when either is "
            "missing or ambiguous."
        ),
        frequency="monthly",
        unit="MMcf per cargo",
        method="published",
        licence="US public domain",
        licence_note=(
            "DOE's web policies: 'Government information at DOE websites is in the "
            "public domain. Public domain information may be freely distributed and "
            "copied, but it is requested that in any subsequent use the Department "
            "of Energy be given appropriate acknowledgement.' Acknowledge the U.S. "
            "Department of Energy, Office of Fossil Energy and Carbon Management."
        ),
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
            "be recovered by hand, or from the Internet Archive's capture of the "
            "three files if it made one that week, as it did five times from April "
            "to August 2026."
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


# ---------------------------------------------------------------------------
# Engine parameters
# ---------------------------------------------------------------------------
#
# Every number the engine uses that is not market data. Each carries its value,
# its unit, a status (published: read in the named document; derived: computed
# from published figures; assumption: chosen by this study and labelled), the
# document it comes from, its address and the date it was read. The site's
# Method view prints this table, and the Model view lets a reader change each
# value.

PARAMETER_STATUSES = ("published", "derived", "assumption")


@dataclass(frozen=True)
class Parameter:
    """One engine input that is not market data."""

    name: str
    value: Any
    unit: str
    status: str
    source: str
    url: str | None
    read_on: str
    note: str = ""


def _parameters(*parameters: Parameter) -> Mapping[str, Parameter]:
    out: dict[str, Parameter] = {}
    for p in parameters:
        if p.status not in PARAMETER_STATUSES:
            raise ValueError("parameter %s has status %r" % (p.name, p.status))
        if p.name in out:
            raise ValueError("parameter %s is declared twice" % p.name)
        out[p.name] = p
    return MappingProxyType(out)


_SPARK_38 = "https://static.sparkcommodities.com/documents/lng-freight/methodology/Spark-LNG-Freight-Methodology-3.8.pdf"
_SPARK_32 = "Spark LNG Freight Methodology 3.2, 11 November 2022, read from the Internet Archive's capture of 8 December 2022"


@dataclass(frozen=True)
class PanamaTollPeriod:
    """The Panama Canal Authority's toll for an LNG carrier over one period.

    Before 2023 the toll is per m3 of capacity by band, the bands being the
    first 60,000 m3, the next 30,000, the next 30,000 and the rest, with a
    separate ballast table and a roundtrip ballast table for a ship returning
    in ballast within 60 days. From 2023 it is a fixed charge per transit plus
    one rate per m3 for a neopanamax vessel, ballast at a share of laden.
    """

    start: str
    end: str | None
    laden_bands: tuple[float, ...] = ()
    ballast_bands: tuple[float, ...] = ()
    roundtrip_bands: tuple[float, ...] = ()
    fixed_usd: float = 0.0
    rate_usd_m3: float = 0.0
    ballast_share: float = 0.0
    source: str = ""
    url: str = ""


PANAMA_BAND_SIZES_M3 = (60_000.0, 30_000.0, 30_000.0)

PANAMA_TOLLS: tuple[PanamaTollPeriod, ...] = (
    PanamaTollPeriod(
        "2016-04-01", "2017-09-30",
        laden_bands=(2.50, 2.15, 2.07, 1.96), ballast_bands=(2.23, 1.88, 1.80, 1.71),
        roundtrip_bands=(2.00, 1.75, 1.60, 1.50),
        source=("Panama Canal Authority, approved tolls tables, implementation 1 April 2016, "
                "read from the Internet Archive's capture of 4 August 2016"),
        url="http://www.pancanal.com/peajes/ApprovedTollsTables-v2.pdf",
    ),
    PanamaTollPeriod(
        "2017-10-01", "2020-03-31",
        laden_bands=(2.88, 2.47, 2.38, 2.25), ballast_bands=(2.56, 2.16, 2.07, 1.97),
        roundtrip_bands=(2.30, 2.01, 1.84, 1.73),
        source=("Panama Canal Authority, tolls approved 1 August 2017, implementation 1 October "
                "2017, read from the Internet Archive's capture of 21 September 2017"),
        url="http://www.pancanal.com/peajes/pdf/2018/2018-ApprovedTolls.pdf",
    ),
    PanamaTollPeriod(
        "2020-04-01", "2022-12-31",
        laden_bands=(3.12, 2.68, 2.58, 2.44), ballast_bands=(2.79, 2.35, 2.26, 2.15),
        roundtrip_bands=(2.48, 2.17, 1.99, 1.87),
        source="Panama Canal Authority, Tolls, September 2020, page 26",
        url="https://pancanal.com/wp-content/uploads/2022/03/Tolls-202009-Rev.pdf",
    ),
    PanamaTollPeriod(
        "2023-01-01", "2023-12-31", fixed_usd=300_000.0, rate_usd_m3=1.35, ballast_share=0.85,
        source=("Panama Canal Authority, tariff item 1010, 1 January 2023, items 1010.FN02, "
                "1010.NN01 and 1010.BA01"),
        url="https://pancanal.com/wp-content/uploads/2021/08/1010-ingles.pdf",
    ),
    PanamaTollPeriod(
        "2024-01-01", "2024-12-31", fixed_usd=300_000.0, rate_usd_m3=1.70, ballast_share=0.85,
        source="Panama Canal Authority, tariff item 1010, 1 January 2024",
        url="https://pancanal.com/wp-content/uploads/2024/01/Nuevas-tarifas-serie-1010-INGLES_efectivas-1Ene2024-V2.pdf",
    ),
    PanamaTollPeriod(
        "2025-01-01", None, fixed_usd=300_000.0, rate_usd_m3=2.05, ballast_share=0.85,
        source="Panama Canal Authority, tariff item 1010, 1 January 2025; still listed in February 2026",
        url="https://pancanal.com/wp-content/uploads/2024/01/Nuevas-tarifas-serie-1010-INGLES_efectivas-1Ene2025-V2.pdf",
    ),
)

@dataclass(frozen=True)
class SuezSchedule:
    """The Suez Canal Authority's normal transit dues for LNG carriers ("Rate (5)") over one period.

    SDR per ton of Suez Canal Net Tonnage, by band: the first 5,000 tons, the
    next 5,000, the next 10,000, the next 20,000, the next 30,000, the next
    50,000 and the rest.
    """

    start: str
    end: str | None
    laden: tuple[float, ...]
    ballast: tuple[float, ...]
    source: str
    url: str


SUEZ_BAND_SIZES_SCNT = (5_000.0, 5_000.0, 10_000.0, 20_000.0, 30_000.0, 50_000.0)

SUEZ_SCHEDULES: tuple[SuezSchedule, ...] = (
    # The same row in the schedules applicable from 1 May 2015 (circular 2/2015,
    # dues "unchanged the same as in 2014"), from 1 April 2020 (circular 2/2020,
    # LNG unchanged) and from 1 February 2022 (circular 5/2021, which excludes
    # LNG carriers from its increase).
    SuezSchedule(
        "2015-05-01", "2022-12-31",
        laden=(7.88, 6.13, 5.30, 4.10, 3.80, 3.63, 3.53),
        ballast=(6.70, 5.21, 4.51, 3.49, 3.23, 3.09, 3.00),
        source=("Suez Canal Authority, rates of transit dues to be applied from 1 May 2015, unchanged "
                "for LNG carriers in the schedules of 1 April 2020 and 1 February 2022"),
        url="https://www.suezcanal.gov.eg/English/Navigation/NavigationCirculars/Documents/Transit%20dues%202015.pdf",
    ),
    SuezSchedule(
        "2023-01-01", "2024-01-14",
        laden=(9.06, 7.05, 6.10, 4.72, 4.37, 4.17, 4.06),
        ballast=(7.71, 5.99, 5.19, 4.01, 3.71, 3.55, 3.45),
        source="Suez Canal Authority, circular 14/2022 of 18 September 2022, schedules applicable from 1 January 2023",
        url="https://www.suezcanal.gov.eg/English/Navigation/NavigationCirculars/Documents/Cir_14-2022_tables_EN.pdf",
    ),
    SuezSchedule(
        "2024-01-15", None,
        laden=(10.42, 8.11, 7.02, 5.43, 5.03, 4.80, 4.67),
        ballast=(8.87, 6.89, 5.97, 4.61, 4.27, 4.08, 3.97),
        source="Suez Canal Authority, circular 7/2023, transit dues schedules applicable from 15 January 2024",
        url="https://www.suezcanal.gov.eg/Arabic/Navigation/NavigationCirculars/Documents/english72023.pdf",
    ),
)

#: The surcharge on LNG carriers' normal dues, from the date named.
SUEZ_LNG_SURCHARGE: tuple[tuple[str, float, str], ...] = (
    ("2022-03-01", 0.07, "circular 5/2022"),
    ("2026-07-15", 0.19, "periodical 20/2026"),
)

#: The general reduction for LNG carriers, from the date named.
SUEZ_LNG_GENERAL_REDUCTION: tuple[tuple[str, float, str], ...] = (
    ("2015-05-01", 0.25, "circular 2/2015"),
    ("2020-04-01", 0.30, "periodical of 31 March 2020"),
    ("2020-07-01", 0.25, "periodical of 21 June 2020"),
    ("2021-11-01", 0.15, "periodical of 26 October 2021"),
    ("2022-03-15", 0.0, "periodical of 14 March 2022, the reduction cancelled"),
)

#: The rebate for an LNG carrier between the US Gulf and the band holding Japan,
#: on normal dues, from the date named; no text covers transits after the last end.
SUEZ_US_GULF_JAPAN_REBATE: tuple[tuple[str, float, str], ...] = (
    ("2017-10-01", 0.50, "circular 7/2017"),
    ("2018-10-01", 0.65, "periodical of 25 September 2018"),
    ("2019-10-01", 0.75, "periodical of 12 September 2019"),
    ("2022-01-01", 0.70, "periodical of 21 December 2021"),
    ("2023-07-01", 0.75, "periodical of 21 June 2023"),
)
SUEZ_US_GULF_JAPAN_REBATE_END = "2026-12-31"


PARAMETERS: Mapping[str, Parameter] = _parameters(
    Parameter("mmbtu_per_m3_lng", 23.0, "MMBtu per m3 of LNG", "published",
              "Spark LNG Freight Methodology 3.8, page 2, 'LNG Conversion Factor: 23'", _SPARK_38,
              "2026-10-01", "A market convention for a lean cargo; 22 to 24 is shown as a sensitivity."),
    Parameter("vessel_174k_capacity_m3", 174_000.0, "m3", "published",
              "Spark LNG Freight Methodology 3.8, page 2, 'Vessel Type: 174,000 m3 2 Stroke'",
              _SPARK_38, "2026-10-01"),
    Parameter("vessel_174k_boil_off_per_day", 0.00085, "share of the loaded volume per day", "published",
              "Spark LNG Freight Methodology 3.8, page 2, 'Boil Off Rate: 0.085% of cargo tanks at "
              "98.5% capacity'", _SPARK_38, "2026-10-01"),
    Parameter("vessel_174k_speed_kn", 17.0, "knots", "published",
              "Spark LNG Freight Methodology 3.8, page 2, 'Speed: 17 knots'", _SPARK_38, "2026-10-01"),
    Parameter("vessel_160k_capacity_m3", 160_000.0, "m3", "published",
              _SPARK_32 + ", page 2, 'Vessel Type: 160,000 m3 TFDE'", None, "2026-10-01"),
    Parameter("vessel_160k_boil_off_per_day", 0.001, "share of the loaded volume per day", "published",
              _SPARK_32 + ", page 2, 'Boil Off Rate: 0.1% of cargo tanks at 98.5% capacity'", None,
              "2026-10-01"),
    Parameter("vessel_160k_speed_kn", 17.0, "knots", "published",
              _SPARK_32 + ", page 3, 'Speed: 17 knots'", None, "2026-10-01"),
    Parameter("fill", 0.985, "share of capacity loaded", "published",
              "Spark LNG Freight Methodology 3.2, page 3, 'Discharge volume: 98.5% of Vessel Capacity "
              "minus boil-off for laden leg minus a heel of 3,000 m3'", None, "2026-10-01",
              "Spark states 98.5 percent as the basis of its boil-off and of its discharge volume, "
              "not as a fill parameter of its own."),
    Parameter("load_days", 1.0, "days", "published",
              "Spark LNG Freight Methodology 3.8, page 2, '1 day load'", _SPARK_38, "2026-10-01"),
    Parameter("discharge_days", 1.0, "days", "published",
              "Spark LNG Freight Methodology 3.8, page 2, '1 day discharge'", _SPARK_38, "2026-10-01"),
    Parameter("spark30_flex_days", 3.0, "days", "published",
              "Spark LNG Freight Methodology 3.8, page 2, Spark30 '30 days (25 days sailing, 1 day "
              "load, 1 day discharge and 3 Flex Days)'", _SPARK_38, "2026-10-01",
              "Used only to reproduce Spark; the engine's default is no flex days."),
    Parameter("funding_spread_bp", 150.0, "basis points over the overnight rate", "assumption",
              "this study, the convention of its copper sibling", None, "2026-10-07",
              "A trading house's cost of borrowing; a real desk's depends on its credit."),
    Parameter("panama_capacity_is_nominal", True, "flag", "assumption",
              "this study; the canal's admeasurement rules were not read", None, "2026-10-07",
              "The canal charges on capacity as it admeasures it; the nominal capacity stands in."),
    Parameter("panama_fresh_water_fixed_usd", 10_000.0, "USD per transit", "published",
              "Panama Canal Authority, advisory ADV-03-2020 and tariff item 1500.RWA2",
              "https://pancanal.com/wp-content/uploads/2021/08/Maritime-tariffs-80-cancellation-feb26.pdf",
              "2026-10-06", "Mandatory from 15 February 2020 for ships over 300 feet."),
    Parameter("panama_fresh_water_variable_share", 0.05, "share of tolls", "assumption",
              "this study: the middle of the Authority's range of 0 to 10 percent", None, "2026-10-07",
              "Set daily from Gatun Lake's level, which is not collected; 0 and 10 percent are shown. "
              "Before 2023 the range was 1 to 10 percent."),
    Parameter("vessel_174k_from", "2024-01-02", "date", "published",
              "Spark LNG Freight Methodology 3.8, page 7, change log: '3.5 2 January 2024 - Vessel "
              "Type updated to 174,000 m3 2 Stroke'", _SPARK_38, "2026-10-01",
              "The study prices a date before it with the 160,000 m3 TFDE and from it with the "
              "174,000 m3 two-stroke, as the benchmark freight rates do."),
    Parameter("port_cost_west_usd", 308_947.0, "USD per round trip, Sabine Pass and Gate together", "published",
              "Spark, note on negative freight rates, February 2022: 'Port costs provided by GAC on "
              "an indicative basis', for a 160,000 m3 TFDE", None, "2026-10-01",
              "Held for every year and both ships, an assumption (open question 32). Taken to "
              "include the Sabine Neches cargo fee (open question 33)."),
    Parameter("port_cost_east_usd", 273_184.0, "USD per round trip, Sabine Pass and Futtsu together", "published",
              "Spark, note on negative freight rates, February 2022: a screenshot of its Routes page, "
              "release of 8 February 2022, Sabine Pass to Futtsu via Panama, for a 160,000 m3 TFDE",
              None, "2026-10-01",
              "Read from an image; used for every route east, every year and both ships, an "
              "assumption (open questions 31 and 32)."),
    Parameter("delta_nwe_eur_mwh", -2.0, "EUR per MWh, DES Northwest Europe less TTF front month", "assumption",
              "this study, from ACER, Gas market trends and price drivers, October 2023, page 13: 'the "
              "average price difference between TTF front-month products and the EU LNG spot "
              "reference price was 2 EUR/MWh in 2023 (1 January to 31 August 2023)'",
              "https://www.acer.europa.eu/sites/default/files/documents/Publications/ACER_MMR_2023_Gas_market_trends_price_drivers.pdf",
              "2026-09-30",
              "Shown at -3, from ACER's LNG market developments, April 2024, page 38 ('in the range "
              "between 2 EUR/MWh and 3 EUR/MWh'), and at 0. The same report says the spread "
              "'exceeded 35 EUR/MWh during most days from end-July to mid-October 2022', so a date "
              "in that span is also shown at -35. Observed directly only on ACER's 26 corrected days "
              "of November and December 2024."),
    Parameter("panama_open_to_lng_from", "2016-06-26", "date", "published",
              "Panama Canal Authority, press release of 26 June 2016, the expanded locks open; the "
              "first LNG carrier, from Sabine Pass, transited on 25 July 2016", None, "2026-10-06",
              "No later band closes the canal to LNG carriers; docs/methodology.md, section 8.3."),
    Parameter("suez_closed_to_us_cargo_from", "2024-01-13", "date", "assumption",
              "this study, from OIES NG-188: the last laden LNG carrier through Suez on 12 January "
              "2024", "https://www.oxfordenergy.org/wpcms/wp-content/uploads/2024/02/NG-188-LNG-Shipping-Chokepoints.pdf",
              "2026-10-01",
              "Closed to the latest date of the data, since no source shows a US Gulf cargo to Asia "
              "through Suez after January 2024 (open question 28)."),
    # -- The US Gulf contract ---------------------------------------------
    Parameter("spa_henry_hub_multiple", 1.15, "multiple of Henry Hub", "published",
              "Sabine Pass Liquefaction and Centrica, LNG sale and purchase agreement of 22 March 2013, "
              "section 9.1.1: 'CSP = (1.15 x HH) + X y', with HH the NYMEX Henry Hub final settlement "
              "for the month in which the cargo's delivery window is scheduled to begin; Cheniere "
              "Energy Partners, Form 10-K for 2025: 'a variable fee per MMBtu of LNG generally equal to "
              "115% of Henry Hub'",
              "https://cqpir.cheniere.com/sec-filings/all-sec-filings/content/0001383650-13-000038/exhibit101centricaspa.htm",
              "2026-10-07"),
    Parameter("liquefaction_fee_usd_mmbtu", 3.00, "USD per MMBtu", "assumption",
              "this study: the fixed fee most Sabine Pass contracts carry at signing, 3.00 $/MMBtu for "
              "KOGAS, GAIL, Total, Centrica, BG's added volumes and Cheniere Marketing (Cheniere Energy "
              "Partners, Form 10-K for 2015, pages 9 and 88)",
              "https://cqpir.cheniere.com/sec-filings/annual-reports/content/0001383650-16-000087/0001383650-16-000087.pdf",
              "2026-10-07",
              "Sunk once the contract is signed: shown in the full margin, never in the lift "
              "decision. 11.5 to 15 percent of it is indexed to US CPI each year, which the study "
              "does not apply."),
    Parameter("liquefaction_fee_low_usd_mmbtu", 2.25, "USD per MMBtu", "published",
              "Cheniere Energy Partners, Form 10-K for 2015, page 9: BG Gulf Coast LNG, Train 1 volumes, "
              "'a fixed fee of $2.25 per MMBtu'",
              "https://cqpir.cheniere.com/sec-filings/annual-reports/content/0001383650-16-000087/0001383650-16-000087.pdf",
              "2026-10-07", "The low end of the range of published fees."),
    Parameter("liquefaction_fee_high_usd_mmbtu", 3.50, "USD per MMBtu", "published",
              "Corpus Christi Liquefaction and Woodside, LNG sale and purchase agreement of 30 June "
              "2014, section 1.1: X0 'equal to USD three decimal fifty per MMBtu (US$3.50/MMBtu)'",
              "https://lngir.cheniere.com/sec-filings/all-sec-filings/content/0000003570-14-000139/cei2014form8kex101woodside.htm",
              "2026-10-07", "The high end of the range of published fees."),
    Parameter("cancellation_notice_day", 20, "day of the month two months before the loading month",
              "published",
              "Sabine Pass Liquefaction and Centrica, sale and purchase agreement, section 5.7: notice "
              "'on or prior to the twentieth (20th) Day of the Month that is two (2) Months prior to "
              "the Month for which Buyer is suspending deliveries'",
              "https://cqpir.cheniere.com/sec-filings/all-sec-filings/content/0001383650-13-000038/exhibit101centricaspa.htm",
              "2026-10-07"),
    # -- EU ETS on shipping ------------------------------------------------
    Parameter("ets_voyage_share", 0.5, "share of a voyage's emissions, between an EU and a non-EU port",
              "published",
              "Directive 2003/87/EC, Article 3ga(1), inserted by Directive (EU) 2023/959: 'fifty percent "
              "(50 %) of the emissions from ships performing voyages departing from a port of call "
              "outside the jurisdiction of a Member State and arriving at a port of call under the "
              "jurisdiction of a Member State'",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023L0959", "2026-10-07"),
    Parameter("ets_berth_share", 1.0, "share of emissions within an EU port of call", "published",
              "Directive 2003/87/EC, Article 3ga(1): 'one hundred percent (100 %) of emissions from ships "
              "within a port of call under the jurisdiction of a Member State'",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023L0959", "2026-10-07"),
    Parameter("ets_phase_in_by_year", {"2024": 0.40, "2025": 0.70, "2026": 1.00},
              "share of a year's verified emissions surrendered, from the year named", "published",
              "Directive 2003/87/EC, Article 3gb, inserted by Directive (EU) 2023/959: 40 % of verified "
              "emissions reported for 2024, 70 % for 2025, 100 % for 2026 and each year thereafter",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023L0959", "2026-10-07",
              "Nothing before 2024."),
    Parameter("tco2_per_t_lng", 2.750, "tonnes of CO2 per tonne of LNG burnt", "published",
              "Regulation (EU) 2015/757, Annex I, as replaced by Delegated Regulation (EU) 2023/2776, "
              "which applies from 1 January 2024: the emission factor of LNG, 2.750 t CO2 per t of fuel",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2776", "2026-10-07"),
    Parameter("tn2o_per_t_lng", 0.00011, "tonnes of N2O per tonne of LNG burnt", "published",
              "Regulation (EU) 2015/757, Annex I, as replaced by Delegated Regulation (EU) 2023/2776: "
              "N2O 0.00011 g per g of LNG",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2776", "2026-10-07"),
    Parameter("ets_ch4_n2o_from", "2026-01-01", "date", "published",
              "Directive 2003/87/EC, Annex I, maritime row, as amended by Directive (EU) 2023/959: "
              "'Carbon dioxide From 1 January 2026, methane and nitrous oxide'",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023L0959", "2026-10-07"),
    Parameter("gwp_ch4", 28.0, "tonnes of CO2e per tonne of CH4, 100 years", "published",
              "Delegated Regulation (EU) 2020/1044, Annex, by reference from Regulation (EU) 2015/757, Annex I",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32020R1044", "2026-10-07"),
    Parameter("gwp_n2o", 265.0, "tonnes of CO2e per tonne of N2O, 100 years", "published",
              "Delegated Regulation (EU) 2020/1044, Annex",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32020R1044", "2026-10-07"),
    Parameter("methane_slip_174k", 0.017, "share of LNG mass not burnt", "assumption",
              "this study: the default for an LNG Otto dual fuel slow speed engine, 1.7 %, in "
              "Regulation (EU) 2015/757, Annex I, as replaced by Delegated Regulation (EU) 2023/2776",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2776", "2026-10-07",
              "Spark names the ship '2 Stroke' only; a Diesel cycle slow speed engine has 0.2 %. Used "
              "only when methane slip is switched on."),
    Parameter("methane_slip_160k", 0.031, "share of LNG mass not burnt", "assumption",
              "this study: the default for an LNG Otto dual fuel medium speed engine, 3.1 %, the class "
              "of a TFDE ship's engines, in Regulation (EU) 2015/757, Annex I, as replaced by Delegated "
              "Regulation (EU) 2023/2776",
              "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2776", "2026-10-07",
              "Used only when methane slip is switched on; no ETS applies before 2024, when this ship "
              "is the benchmark."),
    Parameter("methane_slip_on", False, "flag", "assumption",
              "this study: off by default, as a toggle", None, "2026-10-07",
              "On, from 2026 the slipped mass counts as methane at its global warming potential and "
              "leaves the CO2 term."),
    Parameter("mmbtu_per_t_lng", 51.56, "MMBtu, gross, per tonne of LNG", "published",
              "IEA and Eurostat, Energy Statistics Manual, 2004, Annex 3, Table A3.9, page 182: LNG, "
              "51,560 Btu per kilogramme, gross calorific value",
              "https://ec.europa.eu/eurostat/documents/3859598/5885369/NRG-2004-EN.PDF.pdf/b3c4b86f-8e88-4ca6-9188-b95320900b3f?t=1414781129000",
              "2026-10-07",
              "GIIGNL's table could not be read by code. Spark's 23 MMBtu per m3 at the manual's 0.45 t "
              "per m3 gives 51.11, 0.9 percent less. Used only to turn the gas burnt into tonnes for "
              "the EU ETS."),
    Parameter("eua_eur_t_after_published", 72.06, "EUR per tonne of CO2", "assumption",
              "this study: the Commission's last published monthly auction price, June 2025, held for "
              "every later month",
              "https://climate.ec.europa.eu/areas-action/carbon-markets/eu-emissions-trading-system-eu-ets/auctioning-allowances_en",
              "2026-10-07",
              "No source with a clear licence gives a monthly price from July 2025 (open question 20). "
              "Shown at 61 and 86, the range of 2025 the Commission's electricity market report for "
              "the fourth quarter of 2025 prints for a secondary market price."),
    Parameter("suez_scnt_per_m3", 85_000.0 / 145_000.0, "tons of Suez Canal Net Tonnage per m3 of capacity",
              "assumption",
              "this study, from a canal agency's approximation, 'ca 85.000 SCNT (145.000m3; 75.000dwt)' "
              "for an LNG carrier of the integrated (membrane) type",
              "https://kadmar.com/calculator-guidelines/", "2026-10-01",
              "No source gives the tonnage of a 174,000 m3 or 160,000 m3 ship; the agency's ratio is "
              "applied to the capacity, 102,000 for 174,000 m3. The agency warns the tonnage 'depends on "
              "the construction'. Shown at 85,000 and at 112,148, the Authority's net tonnage per LNG "
              "transit in 2023 (open question 25)."),
    Parameter("panama_booking_fee_usd", 0.0, "USD per transit", "assumption",
              "this study: an unbooked ship by default", None, "2026-10-07",
              "Booked case: 35,000 $ in 2016, 85,000 $ for booking dates from 1 June 2021, 80,000 $ "
              "in the list of January 2024, 100,000 $ from 1 January 2025."),
)
