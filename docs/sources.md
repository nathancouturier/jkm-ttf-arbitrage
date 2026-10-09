# Sources

Every source this study reads: what it is, where it is read from, what its
terms permit in the source's own words, whether its cache may be committed, and
the traps somebody rebuilding this will otherwise fall into.

Terms are quoted rather than summarised, because a paraphrase of a licence is a
claim about a licence and the reader should be able to check it in one click.
Every quotation below was read from the URL printed next to it, on the date
given. Where the terms leave a question open, the question is in section 4 and
in `docs/open-questions.md`, not resolved silently.

Nothing here is legal advice. It is a record of what was read, when, and what
was decided on the strength of it.

---

## 1. The table

| Series | What it is | Machine URL | Cadence | Cache committed | Licence |
|---|---|---|---|---|---|
| `eia_ngwu_international_weekly` | Weekly averages of an East Asia LNG price and of TTF, USD/MMBtu, from the Natural Gas Weekly Update, figures credited to Bloomberg Finance L.P. | [landing page](https://www.eia.gov/naturalgas/weekly/) for the final issue; every other issue from the Internet Archive's earliest capture of it (2.16), because eia.gov's archive is closed to code | weekly, from the week ending 15 September 2021 to the week ending 21 January 2026, ended | **yes**, with the doubt in 2.1 | US public domain |
| `eia_ngwu_issue_index` | Every issue EIA lists from 2016, the checklist for collection | [archive.php](https://www.eia.gov/naturalgas/weekly/includes/archive.php) | fixed, the series has ended | **yes** | US public domain |
| `eia_wngsr_international_weekly` | Weekly averages of JKM and TTF, USD/MMBtu, from the WNGSR Supplement, figures credited to Bloomberg Finance L.P. | [bullets_lng_2.html](https://www.eia.gov/naturalgas/weekly/supplement/content/bullets_lng_2.html) and two sibling files; past issues from EIA's archive pages read in a browser, and five from the Internet Archive's captures of the same files (2.16, 3.1) | weekly, Thursday, only the current issue | **yes**, with the doubt in 2.1 | US public domain |
| `eia_lng_exports_monthly` | US LNG exports and re-exports by destination country, MMcf, and their prices, USD per thousand cubic feet, the latest release | [NG_MOVE_EXPC_S1_M.xls](https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls) | monthly, end of month | **yes** | US public domain |
| `eia_lng_exports_revisions` | Every volume or price a release of the table above changed, both releases side by side | derived by this study | with each release | **yes** | US public domain |
| `doe_lng_export_cargoes` | US LNG exports and re-exports cargo by cargo from January 2016: departure date, exporter, docket, supplier, ship, port of exit, destination, MMcf | read from the year's page on the [report list](https://www.energy.gov/hgeo/listings/natural-gas-imports-and-exports-monthly-reports); the file's path changes | monthly, with DOE's report | **yes** | US public domain |
| `eia_henry_hub_daily` | Henry Hub spot price, daily, USD/MMBtu, credited by EIA to Refinitiv | [RNGWHHDd.xls](https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls) | weekly release, daily values | **yes**, with the doubt in 2.1 | US public domain |
| `acer_lng_daily` | ACER's DES LNG assessments for NWE, SE and the EU, its EU benchmark to TTF, and the NWE spread to TTF this study computes from them, daily, EUR/MWh, from 19 January 2023 | TERMINAL's historical download, saved by hand, with the [correction notice](https://www.acer.europa.eu/sites/default/files/documents/en/Gas/LNG_Price_Assessment/LNGPA_Correction_Notice_20241220.pdf) | each weekday; extended when the download is saved again | **yes** | ACER legal notice, with the doubt in 2.7 |
| `ec_eua_auction_monthly` | EU allowance price, monthly volume weighted average auction clearing price, EUR/t, January 2023 to June 2025 | quarterly reports linked from the [Commission's auctioning page](https://climate.ec.europa.eu/areas-action/carbon-markets/eu-emissions-trading-system-eu-ets/auctioning-allowances_en) | quarterly, lagging | **yes** | CC BY 4.0, with the doubt in 2.8 |
| `dehst_eua_german_auction_monthly` | EU allowance price in Germany's auctions on EEX, monthly average, EUR/t, January 2024 to August 2026, the proxy after June 2025 | the latest report of each year linked from [DEHSt's reports page](https://www.dehst.de/EN/Topics/EU-ETS-1/EU-ETS-1-Information/Analyses-and-Reports/analysis-and-reports_node.html) | monthly, about a month after | **yes**, for non-commercial use, with the doubt in 2.23 | CC BY-NC-ND 4.0, figures credited to EEX and DEHSt |
| `meti_spot_lng_monthly` | Japan spot LNG price, DES, contract-based and arrival-based, monthly, March 2014 to March 2021 | [historical-data-e.xlsx](https://www.meti.go.jp/english/statistics/sho/slng/historical-data-e.xlsx), read once | ended | **yes** | METI terms, compatible with CC BY 4.0 |
| `meti_spot_lng_releases` | Every figure METI's monthly releases printed, preliminary, detailed and fixed, with the day of each release, for the releases of October 2019 to March 2021 | the release PDFs, saved by hand from [METI's page](https://www.meti.go.jp/english/statistics/sho/slng/index.html) | fixed, the survey has ended | **yes** | METI terms of use, compatible with CC BY 4.0 |
| `jogmec_spot_lng_monthly` | Japan spot LNG price, DES, contract-based and arrival-based, monthly, from April 2021 | one page per month from JOGMEC's English spot price list page | monthly, 9th to 15th | **NO**, `data/private/` until JOGMEC permits | JOGMEC terms, permission not yet requested |
| `worldbank_gas_monthly` | Europe gas (TTF from April 2015), US gas at Henry Hub, and Japan LNG import price, monthly, USD/MMBtu, from 2015 | read from the [commodity markets page](https://www.worldbank.org/en/research/commodity-markets); the file's path changes | monthly, early in the month | **yes** | CC BY 4.0 |
| `worldbank_gas_revisions` | Every value a Pink Sheet release changed, both releases side by side | derived by this study | with each release that changes a value | **yes** | CC BY 4.0 |
| `h10_usd_per_eur_daily` | US dollars per euro, noon buying rate in New York, daily, from 2015 | [FRB_h10_xml.zip](https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip) | weekly, Mondays | **yes** | US public domain |
| `nyfed_sofr_daily` | Secured Overnight Financing Rate, daily, percent, from 2 April 2018 | [markets API](https://markets.newyorkfed.org/api/rates/secured/sofr/search.json) | daily, next business day | **yes**, under the New York Fed's terms | New York Fed Terms of Use |
| `nyfed_effr_daily` | Effective federal funds rate, daily, percent, 4 January 2016 to 30 April 2018, the overnight rate before SOFR | [markets API](https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json) | closed | **yes**, under the New York Fed's terms | New York Fed Terms of Use |
| `imf_usd_per_sdr_daily` | US dollars per special drawing right, daily, from 2016, the IMF's rate as the Bundesbank republishes it, for the Suez toll | [Bundesbank API](https://api.statistiken.bundesbank.de/rest/download/BBEX3/D.USD.XDR.DA.AC.000?format=csv&lang=en) | daily | **yes**, with the IMF credited (2.20) | IMF terms for its data |
| `freight_anchors` | Reported LNG carrier charter rates, USD per day, ten figures from February 2022 to October 2026, one per month at most, each from a dated article | written from rows kept in `lngarb.freight_anchors`; nothing fetched | as figures are verified | **yes**, figures only (2.13, 2.14) | individual figures quoted with attribution |
| `routes` | The four sea routes from Sabine Pass, distances and lines | computed once by `scripts/routes.py` | fixed | **yes** | distances: this study, MIT; lines: EUPL 1.2; searoute Apache 2.0 |

---

## 2. Reuse terms, in each source's own words

### 2.1 EIA, US public domain, with a question about third party figures

Read at `https://www.eia.gov/about/copyrights_reuse.php` on 30 September 2026.
Under "Public domain and use of EIA content":

> "U.S. government publications are in the public domain and are not subject to
> copyright protection. You may use and/or distribute any of our data, files,
> databases, reports, graphs, charts, and other information products that are
> on our website or that you receive through our email distribution service.
> However, if you use or reproduce any of our information products, you should
> use an acknowledgment, which includes the publication date, such as: "Source:
> U.S. Energy Information Administration (Oct 2008).""

Under "Quoting EIA content and translations":

> "When quoting EIA text, the acknowledgment should clearly indicate which text
> is EIA content and which is not."

Under "Protected materials":

> "You may see on our website documents, illustrations, photographs, or other
> information resources contributed or licensed by private individuals,
> companies, or organizations that may be protected by U.S. and foreign
> copyright laws. Transmission or reproduction of protected items beyond that
> allowed by fair use as defined in the copyright laws requires the written
> permission of the copyright owners."

**Redistributable: yes for EIA's own data.** Two of the series this study reads
from EIA are figures EIA prints under a third party's credit:

* the weekly JKM and TTF averages, whose items begin "According to Bloomberg
  Finance, L.P.," (Natural Gas Weekly Update) or end with "Data source:
  Bloomberg Finance, L.P." (WNGSR Supplement);
* the Henry Hub spot price, which EIA's table definitions page, read at
  `https://www.eia.gov/dnav/ng/TblDefs/ng_pri_fut_tbldef2.asp`, credits:
  "Spot Price: Refinitiv, an LSEG business."

EIA's page does not say whether figures it publishes under such a credit are
"information resources ... licensed by" that party. The committed caches carry
the credit wherever the values are used, and the question is open with the
owner (section 4).

The exports table's own definitions page, read at
`https://www.eia.gov/dnav/ng/TblDefs/ng_move_expc_tbldef2.asp`, names its source
from 1999 as "Office of Fossil Energy, U.S. Department of Energy, Natural Gas
Imports and Exports", a US government publication.

**Attribution this project uses:** "Source: U.S. Energy Information
Administration", with the release date of the file read, and the third party
credit EIA prints for the weekly prices and for Henry Hub.

### 2.1.1 US Department of Energy, cargo by cargo exports, US public domain

Read at `https://www.energy.gov/web-policies` on 7 October 2026, under
"Copyright, Restrictions and Permissions Notice":

> "Government information at DOE websites is in the public domain. Public
> domain information may be freely distributed and copied, but it is requested
> that in any subsequent use the Department of Energy be given appropriate
> acknowledgement."

**Redistributable: yes**, acknowledging the U.S. Department of Energy, Office
of Fossil Energy and Carbon Management. The file names exporters, suppliers and
ships, all published by DOE.

### 2.2 World Bank Pink Sheet, CC BY 4.0

Read at `https://www.worldbank.org/ext/en/legal/terms-conditions/datasets` on 30
September 2026, "Last Updated: Mar 23, 2018":

> "Unless specifically labeled otherwise, these Datasets are provided to you
> under a Creative Commons Attribution 4.0 International License (CC BY 4.0),
> with the additional terms below."

> "Where these Dataset Terms conflict with the general Terms and Conditions,
> these Dataset Terms shall prevail."

> "You may not publicly represent or imply that The World Bank is participating
> in, or has sponsored, approved or endorsed the manner or purpose of your use
> or reproduction of the Datasets."

The dataset's catalogue entry, "Commodity Prices - History and Projections",
read at `https://datacatalog.worldbank.org/search/dataset/0038238`, says:
"This dataset is licensed under Creative Commons Attribution 4.0".

The general site terms, which the landing page's "Terms of use for Datasets"
link now redirects to, carry a narrower non commercial, no derivatives clause
for "the remainder of the Materials"; the dataset terms say they prevail over
the general terms for datasets, and those are the terms applied here.

**Redistributable: yes**, with attribution and without implying endorsement.
One residual is recorded rather than resolved: the summary terms of use at
`https://data.worldbank.org/summary-terms-of-use` say "Some datasets and
indicators are provided by third parties, and may not be redistributed or
reused without the consent of the original data provider, or may be subject to
additional terms and conditions. Where applicable, these conditions are
included in the dataset or indicator metadata." The workbook's Description
sheet names the sources of the gas rows (Bloomberg Finance L.P., World Gas
Intelligence, Thomson Reuters Datastream, The Wall Street Journal, Official
Statistics of Japan); the catalogue entry names no extra condition.

**Attribution this project uses:** "The World Bank, Commodity Price Data (The
Pink Sheet)", with the release's "Updated on" date.

### 2.3 Federal Reserve Board, H.10, US public domain

Read at `https://www.federalreserve.gov/disclaimer.htm` on 30 September 2026,
"Last Update: August 02, 2024":

> "Unless otherwise indicated, information on Board's website is in the public
> domain and may be copied and distributed without permission. Please cite to
> the Board as the source of the information."

What the rate is, from `https://www.federalreserve.gov/releases/h10/about.htm`:

> "The data are noon buying rates in New York for cable transfers payable in the
> listed currencies. The rates have been certified by the Federal Reserve Bank of
> New York for customs purposes as required by section 522 of the amended Tariff
> Act of 1930."

**Redistributable: yes**, citing the Board.

### 2.4 Federal Reserve Bank of New York, SOFR and EFFR, licensed

Read at `https://www.newyorkfed.org/privacy/termsofuse` on 30 September 2026,
"Last Updated: 6/9/2023". The API's own description says use of the reference
rates and all data accessible through it is subject to these terms.

> "The New York Fed grants you a non-exclusive license, subject to the Terms, to
> use, copy, and distribute Content for your personal or business purposes."

> "If you distribute the Content, you must make the Content available with the
> same permissions, conditions, and restrictions set forth in these Terms. You
> may not impose more restrictive terms or conditions on the Content."

> "If you use or distribute reference rate data or related information posted to
> the website, you must include the following notice and disclaimer with your
> presentation of that data or information: “The [NAME OF DATA or CONTENT]* is
> subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not
> responsible for publication of the [DATA NAME] by [NAME OF PUBLISHER], does not
> [sanction] or [endorse] any particular republication, and has no liability for
> your use.”"

> "The Secured Overnight Financing Rate (SOFR) Data and Broad General Collateral
> Rate (BGCR) Data are calculated using data provided under a license granted to
> the New York Fed by DTCC Solutions LLC (“Solutions”), an affiliate of The
> Depository Trust & Clearing Corporation."

The same page also requires its attribution line where no other is given, and
that modified content be labelled so that it is not attributed to the New York
Fed.

The same terms were read again on 7 October 2026: the text from "Last Updated:
6/9/2023" to the end is unchanged, character for character. The API's
description names the effective federal funds rate (EFFR) among the reference
rates its notice covers; the third party licence sentence names only SOFR and
BGCR.

**Redistributable: yes, under the New York Fed's terms, not this repository's.**
The committed SOFR and EFFR caches travel under those terms, not under the MIT
licence.
The financing line the study computes from SOFR is this study's derivative and
is labelled as such. The site shows the completed notice wherever SOFR or the
financing line appears.

### 2.5 METI, Spot LNG Price Statistics, compatible with CC BY 4.0

Read at `https://www.meti.go.jp/english/other/terms_of_use.html` on 30 September
2026, "Last updated:2025-03-10":

> "Unless otherwise specified, the copyrights to the Content belong to METI, but
> you may use the Content under the terms of use if you comply with the Public
> Data License (Version 1.0; PDL 1.0)."

> "If you edit or process the Content for use, you should include a statement
> expressing that the Content has been edited or processed in addition to the
> abovementioned source citation. You are not allowed to make public or use
> edited or processed information in a way that makes it appear as if the
> Government of Japan (or its ministries and/or agencies) created it."

> "The Terms of Use are compatible with the Creative Commons Attribution License
> 4.0 (hereinafter referred to as the CC License). This means that Content based
> on the Terms of Use may be used under the CC License in lieu of the Terms of
> Use."

**Redistributable: yes**, citing the source and saying the data were edited.
The appendix of content under other terms and the "Agreement for use" page could
not be read past METI's bot challenge (section 3.7); nothing in the survey's
files names a third party.

**Attribution this project uses:** "Created by processing the information in
the Spot LNG Price Statistics (Ministry of Economy, Trade and Industry of
Japan) (https://www.meti.go.jp/english/statistics/sho/slng/index.html)",
following the pattern METI's terms give.

The monthly release PDFs carry what the workbook drops: each month's
preliminary figure as first published, and the day of each release. The
owner saved the releases for October 2019 to March 2021 from a browser on 8
October 2026 (the manual step); every figure they print is committed as
`meti_spot_lng_releases`, with METI's own label, and the PDFs stay private
except two kept as test fixtures. Every detailed and fixed figure they print
equals the workbook's.

### 2.6 JOGMEC, spot LNG prices for delivery to Japan, not redistributable yet

From the "Global Disclaimer" on JOGMEC's English natural gas page,
`https://journal.jogmec.go.jp/oilgas/nglng-en/index.html`, read on 30 September
2026:

> "Use of this material beyond the scope permitted under the Copyright Act of
> Japan, such as private use, educational use, or quotation, requires prior
> permission from JOGMEC or the relevant copyright holders."

From JOGMEC's English terms of use, `https://www.jogmec.go.jp/english/terms.html`:

> "Any transfer or reproduction of this Website in whole or in part, in either
> its existing form or modified form, is expressly prohibited except for
> personal use or citation for nonprofit purposes permitted under copyright law
> and other laws."

> "You may not link to this website without prior written permission from
> JOGMEC."

**Redistributable: no, not without JOGMEC's permission**, which has not been
requested yet (the draft and the decision are in `docs/open-questions.md`,
question 14). The series is kept in
`data/private/`; no value, chart or derived figure from it is published, and
the public pages carry no link to JOGMEC until JOGMEC allows it. The
registry marks the source `linkable=False`: its manifest entry carries no URL,
the provenance table names JOGMEC in plain text, and the data validator and a
test fail if its domain reaches the page or any data file the page reads. Its
addresses appear only as plain text, never as links, in this document, in the
open questions and in the code that reads the series privately.

### 2.7 ACER, LNG price assessment and benchmark

Read at `https://www.acer.europa.eu/legal-notice` on 30 September 2026, under
"Copyright notice", its first paragraph:

> "Unless otherwise stated, the Agency is the owner of copyright and database
> rights of this website and its contents. Downloading of this Licensed Material
> other than for personal use is prohibited. The republication, retransmission,
> reproduction or other use of this Licensed Material is prohibited."

and its second:

> "Information and documents made available on the Agency's webpages are public
> and may be reproduced and/or distributed, totally or in part, irrespective of
> the means and/or the formats used, for non-commercial and commercial purposes,
> provided that the Agency is always acknowledged as the source of the material.
> Such acknowledgement must be included in each copy of the material."

ACER's methodology documents (versions 1.0, 1.1 and Beta 2.0) and its complaint
procedure print: "Reproduction is authorised provided the source is
acknowledged." The correction notice carries no such line.

Most of the committed values come from TERMINAL's historical download, saved
by hand. TERMINAL's home page, as the owner read it on 8 October 2026, carries
no legal notice or terms of its own: it describes the application as
publishing the LNG price assessment and benchmark under REMIT, lists among its
features the "Possibility to download historical data in the CSV format", and
points to ACER's website. ACER's methodology refers to a legal notice of
TERMINAL's own, which the page does not show. The study applies ACER's legal
notice above to the downloaded values, with the same acknowledgement, and
records the doubt in question 19.

**Redistributable: yes, with acknowledgement, on the reading that the first
paragraph applies only to material ACER marks as licensed.** The notice does not
say what "Licensed Material" is, and read literally its first paragraph forbids
what its second permits; the question is open (section 4). The benchmark's TTF
leg is ICE data: ACER's DES prices and spreads are published as ACER prints
them, and a TTF level backed out of them is never computed.

What ACER publishes, from `https://www.acer.europa.eu/gas/lng-price-assessment`:
"From 13 January 2023, ACER publishes its LNG price assessment every weekday
before 18.00 CET. From 31 March 2023 onwards, ACER publishes its LNG benchmark
every weekday typically at 21.00 CET." The methodology defines the benchmark as
"the spread between the daily LNG price assessment for DES LNG Spot EU and the
settlement price for the TTF Gas Futures front-month contract established by
ICE Endex Markets B.V."

### 2.8 European Commission, auction reports, CC BY 4.0

Read at `https://commission.europa.eu/legal-notice_en` on 30 September 2026:

> "Unless otherwise indicated (e.g. in individual copyright notices), content
> owned by the EU on this website is licensed under the Creative Commons
> Attribution 4.0 International (CC BY 4.0) licence . This means that reuse is
> allowed, provided appropriate credit is given and changes are indicated."

> "To use or reproduce content that is not owned by the EU, you may need to seek
> permission directly from the rightholders."

The auction reports carry no individual copyright notice. **Redistributable:
yes**, crediting the European Commission and saying that the months are
combined from several reports by this study. One doubt, recorded: each report
says it assembles "the information provided by the common auction platform",
and whether its tables are content owned by the EU is not stated.

EEX, which runs the auctions and publishes every result, was read and not used:
its website terms say its contents may not be "copied, reprinted, published,
transmitted, transferred, disseminated or distributed in any manner without the
prior written approval of EEX AG". Its figures reproduce the Commission's
monthly averages to the cent and are kept privately as a check.

### 2.9 The routes, this study's computation, and the network under them

The distances and lines in `data/seed/routes.json` and `data/seed/routes.geojson`
were computed by this study with searoute 1.6.0
(`https://github.com/genthalili/searoute-py`). Its licence file, read from the
package and from the repository on 1 October 2026, is the Apache License 2.0
with the line "Copyright 2024 - Gent Halili". Its README warns: "Not for
routing purposes! This library was developed to generate realistic-looking sea
routes for visualizations of maritime routes, not for mariners to route their
ships." The library is a development tool; it is not shipped with the site.

The lines are vertices of the maritime network the library bundles, which
carries no licence or source of its own. The README credits "Eurostat's
Searoute Java library" (`https://github.com/eurostat/searoute`), released under
the European Union Public Licence 1.2, whose copyleft clause requires
derivatives to be distributed under it or a licence on its compatibility list;
the Apache License is not on that list. Eurostat's README says its network "is
based on the Oak Ridge National Labs CTA Transportation Network Group, Global
Shipping Lane Network, World, 2000", whose copy on GeoCommons carries no
licence field. **The distances are this study's computation and are published
under the MIT licence. The committed lines are published under the European
Union Public Licence 1.2**, as a work derived from that network, with
attribution to searoute, to Eurostat and to the Oak Ridge dataset
(`NOTICE`; question 21).

### 2.9.1 The land on the map: Natural Earth, through world-atlas

The land drawn on the Routes view's map is Natural Earth's 1:110m land, as the
world-atlas package 2.0.2 packs it in TopoJSON (`vendor/world-atlas/`). Natural
Earth's terms of use (`https://www.naturalearthdata.com/about/terms-of-use/`),
read on 9 October 2026, place every version of its raster and vector map data
in the public domain, and say: "No permission is needed to use Natural Earth."
Credit is not required; the study gives it. The package's licence, beside its
file, is the ISC licence, copyright 2013 to 2019 Michael Bostock, which allows
copying and distribution provided the notice travels with it.
**Redistributable: yes.**

### 2.10 Suez Canal Authority, circulars and annual reports

Read at `https://www.suezcanal.gov.eg/` on 1 October 2026. No terms of use page
could be found. Every page's footer reads:

> "Copyright 2017 | All Right Reserved Suez Canal Authority"

The study quotes rates, percentages and dates from the Authority's circulars
and periodicals, and yearly transit counts from its annual navigation reports,
each with the instrument or report named beside it. It copies no document and
commits no file of the Authority's. **Redistributable: quotation only**, until
the owner decides otherwise (section 4).

Where things are. Each circular has a page under
`https://www.suezcanal.gov.eg/English/Navigation/NavigationCirculars/Pages/`,
but its articles are not in that page: the page's own script fetches them from
`/SCAAPI/api/values/GetUpdatedCircularsAndArticles`, which also records which
later instrument amended, renewed or cancelled each one. The toll schedules are
PDFs attached to their circulars, the English schedule of circular 7/2023 under
an `/Arabic/` path. The annual reports are PDFs under
`/English/Downloads/DownloadsDocLibrary/Navigation Reports/`. The toll
calculator, the tolls table and the statistics reports are interactive pages,
and none is read by code.

### 2.11 The Red Sea record, and on what terms each part is quoted

The record of LNG carriers in the Red Sea since January 2024 is assembled from
short quotations, each attributed, from these:

* Oxford Institute for Energy Studies, "LNG Shipping Chokepoints", NG 188,
  February 2024,
  `https://www.oxfordenergy.org/wpcms/wp-content/uploads/2024/02/NG-188-LNG-Shipping-Chokepoints.pdf`,
  read on 1 October 2026. Page i:

  > "This publication may be reproduced in part for educational or non-profit
  > purposes without special permission from the copyright holder, provided
  > acknowledgment of the source is made."

* International Energy Agency, Gas Market Reports from Q1 2024 to Q3 2026 and
  the Global Gas Security Review 2024, read on 1 October 2026. The last page of
  each report reads:

  > "Subject to the IEA’s Notice for CC-licenced Content, this work is licenced
  > under a Creative Commons Attribution 4.0 International Licence."

* EIA, Today in Energy, US public domain (2.1).
* Kpler, gCaptain, The National, Discovery Alert and Leth Agencies: ordinary
  copyright, quoted briefly with attribution. Their terms pages were not read.
* Lloyd's List Intelligence: its Red Sea briefs were read on 1 October 2026 and
  its terms on 3 October 2026, after the briefs. The terms forbid, "unless
  expressly permitted by us in writing", any "bulk/batch downloading or
  automated scraping of Content". The briefs are therefore not a source of
  this study (question 38).

### 2.12 Port tariffs, and the documents they are read from

Each rate in `docs/methodology.md`, section 7.2, is quoted from its publisher's
own document, read on 3 October 2026, with the document named beside it. No
file from these publishers is committed. Their terms pages were not read, so
nothing beyond the quoted rates is reproduced.

| Publisher | Document | Where |
|---|---|---|
| Government of Japan | Tonnage Tax Act and Special Tonnage Tax Act, article 3 of each; Pilotage Act, article 46 | `https://laws.e-gov.go.jp/` |
| Chiba prefecture | the Kisarazu port page; the port charges schedule under the prefecture's port management ordinance; the page on entry dues for LNG fuelled ships | `https://www.pref.chiba.lg.jp/kouwan/` |
| City of Yokohama | the Minister's approved pilotage caps for Tokyo Bay, as of 1 January 2024 | `https://www.city.yokohama.lg.jp/` |
| Port of Rotterdam Authority | General terms and conditions including port tariffs, 2024, 2025 and 2026; tariffs of third parties 2026 | `https://www.portofrotterdam.com/en/sea-shipping/seaport-dues` |
| Gate terminal | commercial tariff page | `https://www.gateterminal.com/en/commercial/tariff/` |
| Sabine Pilots | rates effective 1 January 2023, Sabine Neches waterway and Sabine Bank | `https://dispatch.sabinepilots.com/portals/0/2023ratesstatebank.pdf` |
| Sabine Neches Navigation District | user fee fact sheet | `https://navigationdistrict.org/fact_sheets/sabine-neches-waterway-user-fee/` |
| Supreme Court of the United States | docket 22-805, the petition and its appendix, a public record | `https://www.supremecourt.gov/docket/docketfiles/html/public/22-805.html` |

### 2.13 Spark Commodities, its methodology and its note on negative rates

The study quotes figures from two documents Spark publishes on its site, read
on 1 October 2026: its LNG freight methodology (versions 3.2 and 3.8) and its
note on negative freight rates. Every page of the note reads "All data and
images are copyright • Spark Commodities". Spark's terms, read on 3 October
2026 from the documents its site's terms pages redirect to:

From "Spark Content Usage", last updated February 2023:

> "Without a Spark Licence, you may not copy, store (hardcopy and/or electronic
> format), adapt, alter, translate, transmit, disseminate, distribute, perform,
> broadcast, publish, reproduce, publicly display, hyperlink, sell, licence,
> rent, lease and/or otherwise transfer any of the Spark Content, ..."

From the "Spark Terms of Use", version 2.1, February 2024:

> "You must not use and/or replicate Spark Content, other than as permitted by
> laws relating to fair use, without our prior written consent and/or without
> authorised licence with Spark, which consent we may withhold in our absolute
> discretion."

> "Unless otherwise stated, you may not link (including, but not limited to,
> hyperlink, in-line link or deep-link) ..."

**Redistributable: no document; individual figures only as quotation**, as fair
use for a non-commercial study (question 36). No Spark document is committed,
and Spark's documents are named, not linked.

### 2.14 The trade press, for reported charter rates

Spark's spot charter rates reach the public through the press. The terms of the
publishers read so far:

* LNG Prime, terms effective 22 July 2024, read on 3 October 2026: "Any
  republication, redistribution or re-editing or other use of this material in
  any form, including translation, is strictly prohibited without the prior
  consent of LNG Prime." Every article of 2026 read was behind a subscription
  after its first sentence.
* Lloyd's List links its terms to Lloyd's List Intelligence's (2.11).
* Hellenic Shipping News, whose republication of a Platts report is the only
  readable copy of it, prohibits republication without the editor's written
  authorisation. S&P Global, which publishes Platts, refuses automated requests
  even for its robots.txt.

The ten figures verified in readable articles are committed in
`data/seed/freight_anchors.json` (question 37): for each, the figure, the day
it refers to or the article's date, the assessment and the vessel basis,
marked inferred where the article does not state them, the publisher and the
article's address. No article's sentence and no article is committed. The
figure of 3 March 2026, 161,750 $/day, is taken from LNG Prime's article of that
day, never from Lloyd's List (question 38). Where a month has more than one
reported figure, the first reported is kept, as for October 2022.

### 2.15 Panama Canal Authority, tariffs and advisories

Read at `https://pancanal.com/en/terms-of-use/` on 6 October 2026, linked from
the footer of every page of the Authority's site:

> "The information, documents, reports, maps and photographs appearing on this
> site are the property of the Panama Canal Authority; therefore, their
> modification or alteration, as well as their copying, distribution,
> transmission, reproduction or publication for commercial or lucrative
> purposes is prohibited."

> "Their use for commercial or lucrative purposes requires prior express
> authorization from the Panama Canal Authority."

The tariff documents and advisories carry no notice of their own. The study
quotes rates, item codes and dates from them, each with its document, for a
non-commercial study, and commits none of them. The terms grant no licence, do
not address quotation, and may be read as forbidding any "modification or
alteration" whatever the purpose. **Redistributable: quotation only**, and
whether that is enough is open (question 41).

Where things are. The tariff for each year from 2023 is a PDF deck under
`https://pancanal.com/wp-content/uploads/`, item 1010 for tolls, and a
consolidated list of maritime tariffs is published beside it. The documents of
2016 and 2017 were published under an older address the current site does not
link; they are read from the Internet Archive's copies, and the Authority's own
histories of tolls of September 2020 and May 2023 reproduce the tables of 2016,
2017 and 2020. Advisories to shipping are listed on the Authority's advisories
page, one PDF each.

### 2.16 The Internet Archive, for pages a publisher no longer serves to code

Read at `https://archive.org/about/terms` on 7 October 2026, the terms of use
dated 31 December 2014:

> "Access to the Archive's Collections is provided at no cost to you and is
> granted for scholarship and research purposes only."

> "In particular, you certify that your use of any part of the Archive's
> Collections will be limited to noninfringing or fair use under copyright
> law."

> "You agree not to interfere with the work of other users or Archive
> personnel, servers, or resources."

> "In addition, we request that, according to standard academic practice, if
> you use the Archive's Collections for any research that results in an
> article, a book, or other publication, you list the Archive as a resource in
> your bibliography."

`https://archive.org/robots.txt`, read the same day, disallows only `/control/`
and `/report/` for every user agent; `https://web.archive.org/robots.txt`
answers HTTP 404, so nothing there is disallowed. The terms page is a script
application that serves no text to a plain request, so it was read in a
browser.

The terms govern access to the Archive's copies, not the works copied. Every
page this study reads there is a US government publication or a document whose
own terms are quoted above, and the study is research, so it reads the copies
under these terms: one request at a time with a pause of four seconds, the
earliest capture of each Natural Gas Weekly Update issue and of each distinct
Supplement prices file, and for a file the
publisher replaces with each release, the capture holding the release named,
each with its timestamp, address and checksum logged beside it. The saved pages stay in `data/private/`; what is committed is what
the publisher's own terms allow, here the parsed figures and the text they were
read from, plus the issues kept byte for byte as test fixtures. The Archive is
named as the place each such row was read from, in the row itself and on every
page that shows it.

**Used for:** every archived issue of the Natural Gas Weekly Update and five
past issues of the WNGSR Supplement (3.1), the release of EIA's exports table
of 30 April 2026 and the World Bank workbook of
2 July 2026 kept as fixtures, and the Panama Canal Authority's tariff documents
of 2016 and 2017 (2.15).

### 2.17 EUR-Lex and the Commission, for the EU ETS rules on shipping

The shares of a voyage's emissions, the phase-in by year, the emission factor
of LNG and the global warming potentials are read from the legal texts on
EUR-Lex: Directive 2003/87/EC as amended by Directive (EU) 2023/959, Regulation
(EU) 2015/757 as amended by Delegated Regulation (EU) 2023/2776, and Delegated
Regulation (EU) 2020/1044, all read on 7 October 2026. EUR-Lex's legal notice,
read the same day:

> "Unless otherwise specified, you can re-use the legal documents published in
> EUR-Lex for commercial or non-commercial purposes."

The Commission's FAQ on maritime transport in the EU ETS, updated 24 November
2025, is read under the Commission's legal notice (2.8). **Redistributable:
yes.** The study quotes articles and figures, each with its text.

### 2.18 The IEA and Eurostat's Energy Statistics Manual, for MMBtu per tonne

One conversion factor, 51,560 Btu per kilogramme of LNG on a gross calorific
basis, is read from Annex 3, Table A3.9, of the Energy Statistics Manual the IEA
and Eurostat published in 2004, on Eurostat's site, read on 7 October 2026.
Eurostat's copyright notice:

> "Reuse of statistical data, metadata, publications, and other dissemination
> tools published on this website for commercial or non-commercial purposes is
> authorised provided the source is acknowledged."

> "The permission granted above does not extend to any material whose copyright
> is identified as belonging to a third-party"

The manual carries an OECD/IEA copyright of 2004 and asks for permission to
reproduce all or part of it. **Redistributable: the one factor, cited; the
manual is not committed.**

### 2.19 The JKM and TTF contract rules: ICE, Platts and the Japan Exchange Group

The delivery month a front-month price names follows from when its futures stop
trading. ICE's product pages, read in a browser on 8 October 2026, give both
rules. Dutch TTF Natural Gas Futures, ICE Endex:

> "Trading will cease at 18:00 CET two UK Business Days prior to the first
> calendar day of the delivery month, quarter, season, or calendar."

JKM LNG (Platts) Future, ICE Futures Europe:

> "Trading will cease on the 15th calendar day of the calendar month prior to
> the contract month. If the 15th calendar day is not a business day then
> trading will cease on the next preceding business day."

The TTF page's expiry details list the last trading day of 134 live contracts,
November 2026 to December 2037; the study's rule with the UK calendar of 2.22
gives every one of them. ICE's terms of use say their licence "does not include
use of any data mining, robots or similar data gathering or extraction
methods"; nothing was read from ICE by code. The rule that Platts rolls JKM on
the 16th is also in Platts' press release of 16 June 2015 as Mondo Visione
republished it ("The Platts JKM rolls on the 16th of each calendar month"), and
the Japan Exchange Group's specification of its LNG (Platts JKM) futures,
updated 4 November 2024, gives the same settlement window; its terms say:

> "The collection of data or secondary use of information from this website
> for commercial purposes is strictly prohibited, unless JPX has granted prior
> permission or authorized such use under a paid contract."

**Redistributable: the rules as quotation, for a non-commercial study.** No
price from these sources is used.

### 2.20 The IMF's SDR rate, through the Deutsche Bundesbank

The IMF's daily US dollars per SDR, which the Suez toll needs, is read from the
Bundesbank's statistics API, series BBEX3.D.USD.XDR.DA.AC.000, whose file names
the "International Monetary Fund (IMF), Washington" as its source; the IMF's own
hosts refuse automated requests. The IMF's terms, "Copyright and Usage",
effective 11 October 2024, read in a browser at
`https://www.imf.org/en/about/copyright-and-terms` on 8 October 2026, govern
its "Exchange Rate Data" under "The Use of IMF Data":

> "You may download, extract, copy, create derivative works, publish,
> distribute, and use Data obtained from IMF Sites, subject to the following
> conditions:"

> "Whether obtained directly from the IMF or another party, when Data is
> distributed or reproduced in any manner, it must appear accurately with
> attribution to the IMF as the source, e.g. "Source: International Monetary
> Fund, Database Name, <<link to the dataset>>.""

The Bundesbank's terms leave third party data to its originator's permission,
which these terms give. On the 41 days of October 2022 and September 2026
compared with the IMF's own monthly tables, every Bundesbank rate is the IMF's
to the sixth decimal, and the IMF's closing days are missing from both.
**Redistributable: yes, with the IMF credited.**

### 2.21 Cheniere's filings, for the contract terms

The price formula of a US Gulf contract, the fixed fee and its range, the
inflation indexation and the right to suspend cargoes are read from Cheniere
Energy Partners' and Cheniere Energy's filings with the Securities and Exchange
Commission, as their investor sites republish them, read on 7 October 2026:
the sale and purchase agreements with Centrica (2013) and Woodside (2014), filed
as exhibits, the Form 10-K for 2015, 2017 and 2025, and a presentation of
August 2012. SEC.gov answered the study's first request with HTTP 403, so
EDGAR itself was not read; the accession numbers let anyone find the same
documents there. The investor sites' "Terms" link leads to Cheniere's website
disclaimer, read first, which says nothing on reuse or automated access:

> "The information and materials on this website are provided for
> informational purposes only."

**Redistributable: quotation of public filings.** Contract figures are quoted
with their document and section; no filing is committed.

### 2.22 gov.uk, the UK bank holidays

The exchanges count UK business days. The bank holidays of England and Wales
for 2019 to 2028 are read from `https://www.gov.uk/bank-holidays.json` on 8
October 2026, under the Open Government Licence v3.0: the footer of gov.uk's
bank holidays page reads "All content is available under the Open Government
Licence v3.0, except where otherwise stated". The study builds earlier
years from the same rule, which reproduces every day gov.uk lists. The file is
kept as a test fixture. **Redistributable: yes, with attribution.**

---

### 2.23 DEHSt, the German auctions, CC BY-NC-ND 4.0

The German Emissions Trading Authority (DEHSt) at the German Environment Agency
reports the results of Germany's own allowance auctions, held weekly on EEX,
month by month. Its editorial information,
`https://www.dehst.de/EN/Service/Editorial-information/editorial-information_node.html`,
sits on a path its robots.txt closes to code and was read in a browser on 8
October 2026:

> "Unless otherwise indicated, objects, graphics, sound documents, video
> sequences and texts created by DEHSt on this website are under a Creative
> Commons Attribution, non-commercial, no derivatives 4.0 international
> license."

(the three parts of the licence's name are joined by dashes in the original).
The licence's section on database rights, read on creativecommons.org the same
day, grants "the right to extract, reuse, reproduce, and Share all or a
substantial portion of the contents of the database for NonCommercial purposes
only and provided You do not Share Adapted Material". The reports carry no
licence sentence of their own. The one table the study reads, "Overview of the
entire year", names "Source: EEX, DEHSt"; other tables and figures credit ICE,
Nasdaq OMX, Refinitiv or LSEG and LEBA besides, and each cover credits a photo
library, so no report is committed, not even as a test fixture: the tests
rebuild the year tables as text. The study keeps each month's average
unchanged, credited to EEX and DEHSt, and is non-commercial.
**Redistributable: yes, for non-commercial use, credited to EEX and DEHSt.**
One doubt, recorded: EEX's own terms (2.8) forbid distributing its contents
without its approval, and whether a monthly average DEHSt computes and
publishes from EEX's results carries EEX's rights is not stated. Should DEHSt
or EEX object, the series moves to `data/private/`. robots.txt asks for
"Crawl-delay: 30"; the study waits 31 seconds between requests to dehst.de.

### 2.24 Figures others reported, which the analysis is set against

`lngarb.reported` keeps a few counts and assessments read in dated, readable
documents, none of them an input to the engine: each as a figure with its
publisher, the document's address and the day it was read, never as a
sentence. All were read on 8 October 2026.

* **EIA, Today in Energy of 11 August 2020**, "U.S. liquefied natural gas
  exports remain at low levels this summer"
  (`https://www.eia.gov/todayinenergy/detail.php?id=44697`): about 46 cargoes
  cancelled in June 2020 and about 50 in July, EIA's estimates from the cargoes
  loaded and the capacity in operation, and 45 for August and an estimated 30
  for September, from trade press reports it cites. US public domain (2.1).
* **Platts, republished by Hellenic Shipping News on 22 April 2024** (2.14, the
  same report as the freight anchor of April 2024): a record 27 US LNG cargoes
  to Asia via the Cape of Good Hope in March 2024, in S&P Global's data. The
  page sits behind a bot check that an automated browser did not pass; it was
  read in the owner's own browser, where it loaded with no check to answer.
* **Platts, republished by the World Ports Organization on 29 March 2024**: 14
  US LNG cargoes reached Asia via the Panama Canal in 2024 to 27 March, one of
  them in March, against 40 in the same period of 2023. The World Ports
  Organization's terms, effective 1 January 2021: "You may view and share
  individual articles for personal, non-commercial use, provided attribution
  and a link to the original remain."
* **Platts, republished by Cyprus Shipping News on 5 May 2026**: Platts'
  arbitrage of US to North Asia against US to the Atlantic assessed at +53.3
  cents/MMBtu via the Panama Canal and -67.7 cents via the Cape of Good Hope on
  28 April 2026, and 31 of 34 LNG cargoes from US facilities to Asia-Pacific
  routed round the Cape, the period not stated; Platts' sources said auctioned
  Panama Canal slots had made the route impractical for spot cargoes, most of
  its traffic being tied to long-term contracts. Cyprus Shipping News' terms,
  last updated 1 September 2026, give "a strictly limited, non-exclusive,
  personal, and non-commercial license to view, read, and listen to the
  content", and forbid "Any republication, reproduction, distribution,
  modification, adaptation, translation, commercial exploitation, or creation
  of derivative works from any part of the Website without the prior written
  consent of the rights holder". The figures are quoted individually, as for
  Spark's (question 36).

S&P Global's own pages are never requested (2.14).

## 3. Known traps, per source

### 3.1 EIA Natural Gas Weekly Update and its successor

* **The archive is closed to code on eia.gov.** eia.gov's `robots.txt` carries
  `Disallow: /naturalgas/weekly/archivenew_ngwu` for every user agent, and
  `Disallow: /*archive/`, which also covers the Supplement's archive. Nothing in
  this repository fetches either from eia.gov; `lngarb.sources.base.http_get`
  checks `robots.txt` before every request and refuses a disallowed URL. The
  archived issues are read from the Internet Archive's earliest capture of each
  (2.16): all 488 issues the index lists from 2016, saved privately, each
  capture logged with its timestamp, address and checksum.
* **The prices begin on 16 September 2021.** No earlier issue carries them, and
  no issue's own week ends before 15 September 2021. The year-earlier sentences
  of the 39 issues to 7 July 2022 reach back to the week ending 16 September
  2020, and are the only EIA weekly figures for September 2020 to July 2021.
  The East Asia series reaches further back still: the issues of 28 October and
  4 November 2021 call its record a record "since January 2020", "the first
  year" and "the first month for which comparable data are available".
* **The item had four forms.** The issue of 16 September 2021 prints the
  prices inside the spot prices item; from 23 September 2021 to 10 February 2022
  the item has no heading; from 17 February 2022 it is headed "International
  Spot Prices", then "International spot prices"; from 14 July 2022
  "International futures prices". The adapter finds it by its heading, or before
  it had one as the smallest list item naming East Asia and TTF with a price in
  USD/MMBtu.
* **The product changed with the wording.** East Asia is a swap for a named
  month (to the week ending 27 October 2021), for the prompt month (3 November
  2021), for the balance of the month (17 November 2021 to 23 March 2022) and
  for a month not named (30 March to 6 July 2022), then a futures price from the
  week ending 13 July 2022, "front-month" from 14 December 2022. TTF is a spot
  price with no product named for two weeks, then a day-ahead price to the week
  ending 6 July 2022, then a futures price. The stored definition is the
  sentence's own words; the basis column is this study's reading of it.
* **Two issues repeat the previous issue's item word for word.** The issues of
  14 September 2023 and 7 March 2024 carry the items of 7 September 2023 and
  29 February 2024, year-earlier week included, under a new header. The pages
  were captured a week and four months after their release, so the repeat is EIA's.
  Their values are left empty and their text kept; EIA printed the two missing
  weeks a year later as year-earlier figures, which are not used to fill them.
* **One issue prints the wrong year-earlier week.** The issue of 26 January
  2023 gives "week ending January 25, 2022", a Tuesday; the week a year earlier
  ended on 26 January 2022. Stored as printed, flagged in the anomaly column,
  and the cross-check matches weeks on the calendar.
* **Half a year of issues prints no year-earlier figures,** the 23 issues from
  14 July to 22 December 2022, the first of the futures basis.
* **One issue carries no item.** The issue of 27 March 2025 has no
  international prices; the week is a gap, not a zero.
* **A sentence can name both markets.** The TTF sentence of 24 February 2022
  ends "bringing the TTF price back above the price in East Asia"; a clause
  naming both belongs to the market named before its level.
* **A level can be restated in a sentence that names no market.** On 4 and 18
  November 2021 the East Asia level is in a sentence beginning "The weekly
  average", after the sentence that names the market.
* **Two headers of 2020 print a date without its comma** ("April 16 2020",
  "June 24 2020").
* **Weeks without an issue** are holiday weeks and 20 June 2024, when EIA
  released none. The issue after a skipped week still reports one week ("this
  report week (Wednesday, July 3, to Wednesday, July 10)").
* **Python's `urllib.robotparser` says "allowed" to every path on eia.gov.** The
  file opens with `Allow: /`, and the standard library applies the first
  matching line rather than the longest. The project's own parser implements
  RFC 9309, and a test proves the difference on EIA's file as served.
* **The Natural Gas Weekly Update has ended.** Its final issue, released on 22
  January 2026 for the week ending 21 January 2026, says: "This week is the
  final publication of the Natural Gas Weekly Update." The landing page still
  serves that issue. A job polling it keeps finding the same week and must not
  append it twice.
* **The successor is a different product.** The WNGSR Supplement, from 29
  January 2026, prints "The Japan-Korea Marker (JKM) price" and "The price at
  the Title Transfer Facility (TTF) in Europe" (without the abbreviations until
  the issue of 9 April 2026, and for JKM again on 20 August 2026), where the Weekly Update printed
  "weekly average front-month futures prices for liquefied natural gas (LNG)
  cargoes in East Asia" and "Natural gas futures for delivery at the Title
  Transfer Facility (TTF) in the Netherlands". Nothing EIA publishes says the
  underlying Bloomberg series are the same. The two are kept as two series and
  the change is a structural break.
* **The TTF sentence of the final issue does not say "front-month".** Only the
  East Asia sentence does. The stored definition says what each sentence says.
* **Only the Supplement's current issue is readable by code.** It is assembled
  from `content/bullets_lng_2.html`, `content/source_lng_2.html` and
  `content/release_dates.json` inside an application shell, and it is replaced
  every Thursday. A week not collected while current can be recovered from the
  Internet Archive when it captured the three files while the week was current.
  It did so five times before collection began: the issues of 2 April, 28 May,
  23 and 30 July and 6 August 2026, read from the earliest capture of each
  distinct prices file with the other two captured beside it. For the
  Supplement's own archive the Internet Archive holds the application shell of
  one issue and none of its content files.
* **The other past issues were read in a browser.** EIA keeps every past issue
  at `https://www.eia.gov/naturalgas/weekly/supplement/archive/YYYY/MM/DD/`,
  under the path `robots.txt` closes to code. The 29 issues from 29 January to
  17 September 2026 that no capture holds were opened there in a browser on 8
  October 2026, page by page, as the manual step. The text each page showed,
  its header, the list holding the two prices and the "Data source" line, is
  logged privately, in batches of up to five pages with the time each batch
  was logged, and the row parsed from it names the page, the day it was read
  and a checksum of that text. Each page's release and week must be a pair EIA's own list of
  past publications gives. The issue of 2 April 2026, read both ways, gives the
  same text word for word. All 36 issues from 29 January to 1 October 2026 are
  held, and code never requests the archive path.
* **The Supplement's wording varies.** The issues to 9 April 2026 print "The
  Japan-Korea Marker price" and "The price at the Title Transfer Facility in
  Europe", without the abbreviations of later issues. The issue of 26 February
  2026 alone names the product: "The near-month futures price at the Title
  Transfer Facility in Europe" and "The near-month futures price for the
  Japan-Korea Marker". Other bullets come and go: the force majeure at Ras
  Laffan (5 March), the Strait of Hormuz (12 March), the missile strikes (19
  March), a comparison of both prices with the week ending 25 February 2026 in
  percent (16 April to 13 August), Qatar's restart (25 June), both prices'
  highest since December 2022 for TTF and January 2023 for JKM (27 August)
  and EU storage (3 September to 1 October),
  each naming both markets or neither. On 5 February a second
  JKM bullet gives an intraweek high, and on 20 August the TTF bullet adds the
  2023 average it was the highest since. A level is read only from a sentence
  that names one market and says what it "averaged"; every other bullet and
  sentence is counted in the anomaly column, and a sentence giving an average
  for both markets at once stops the parse. The stored item text keeps the
  week line and the two price bullets.
* **The printed change can miss the printed levels by a cent.** Of the 70
  changes the issues from 5 February to 1 October 2026 print, each equals the
  difference of the two printed averages (`weekly_change_check`), except TTF
  on 1 October 2026: "$0.98/per MMBtu lower", against 24.18 less 25.15, 0.97.
  Probably rounding of unrounded averages; the change is stored as printed and
  never used as a value. A price that did not move is printed "unchanged from
  the previous week" (JKM, 5 February) or "remaining unchanged from the
  previous week" (TTF, 26 February).
* **The archive index needs care.** Take each issue's date from the folder in
  its link, never from the month and day cells, which are missing or wrong on
  several rows. Drop rows inside HTML comments: the 2026 tab carries a commented
  copy of 43 rows of 2025. Expect a row that says "No report released" (release
  20 June 2024) and a Friday release (10 January 2025).
* **The index table's markup is broken.** 35 of its rows from 2016 to 2025 have
  no opening `<tr>`, so a parser that walks table rows silently drops them and
  reports 453 issues where the page links 488. The adapter finds each row from
  its link and checks the folders it read against a plain scan of the markup,
  and fails if the two differ.
* **Items carry extra sentences.** The final issue adds a sentence on EU storage
  after the prices. Parse by sentence content, never by position.
* **Changes are printed in more than one form**, with and without "/MMBtu", in
  dollars or in cents.

### 3.2 EIA exports by destination

* **Prices are on a second sheet.** "Data 2" mirrors "Data 1" series for
  series, in dollars per thousand cubic feet, under the same source key with
  `_DMCF` for `_MMCF` (`N9133US3` for `N9133US2`). The definitions page says:
  "LNG prices are a volume-weighted average of the prices reported by cargo."
* **A price and a volume do not always come together.** In the release of 31
  August 2026, one price stands on a volume printed as 0 (Canada by truck,
  January 2018, 19.21 USD per thousand cubic feet), and eight months of 2019
  carry a volume with no price. Both are kept as printed.
* **Prices are revised more often than volumes.** The release of 30 September
  2026 changed one LNG volume and 40 LNG prices, by 0.01 to 2.77 USD per
  thousand cubic feet.
* **Read series by source key**, never by name or position. Names vary between
  "Liquefied U.S." and "U.S. Liquefied", "Vessel" and "Vessels", "(MMcf)" and
  "(Million Cubic Feet)", with double spaces and a leading space in places.
* **The LNG total `N9133US2` includes re-exports**; the by vessel block does
  not. The first shale era cargo, February 2016, is split across the exports
  and re-exports blocks.
* **The series EIA labels "Canada" in the by vessel block is named "from
  Canada" in the workbook.** It holds one value, 3,477 MMcf in January 2026.
* **Components do not always add to totals.** In the release of 30 September
  2026, the destinations of February 2024 sum to 607 MMcf more than the by
  vessel total, because the United Kingdom was revised and the total was not.
* **EIA revises the table**, at least fourteen months back and including the
  China column (February 2026 read 509 MMcf in the release of 30 April 2026 and
  0 in the release of 31 August 2026). No old release stays online, so every
  release is kept as a vintage.
* **Months are dated on the 15th.** Empty cells mean both "no data" and "not
  applicable"; zeros are real zeros.
* **Never probe eia.gov with HEAD.** It answers HTTP 503 to HEAD and HTTP 200 to
  GET on the same URL.

### 3.2.1 DOE's cargo by cargo exports

* **The workbook's address changes every month, and its page every year.** It
  is read from the year's report page, found on the list of report pages, by
  its link text "U.S. LNG Exports and Re-Exports Details (Jan 2016 - <month>
  <year>)"; the parse fails if either link is missing or there are two.
* **A row is a cargo or part of one.** A cargo split between destinations, or
  between long and short term authorisations, appears as several rows with the
  same ship and day. June 2026's 4,575.58 MMcf to China is the whole cargo of
  the Al Fat'h from Plaquemines and part of the Clean Mistral's from Corpus
  Christi, the rest of which is declared for South Korea.
* **It reproduces EIA's monthly table to the MMcf** by departure month and
  country, for exports (Japan, June 2026: 28,827.06 against EIA's 28,827).
  Re-exports and ISO containers sit in the same sheet and are labelled.
* **One row has no date** (an ISO container of 2.53 MMcf to Antigua and
  Barbuda) and is left out, with the count in the manifest's note.
* **Two ports of exit are in Mexico**, Altamira (27 rows) and Ensenada (one),
  and their "U.S. Contiguous" field reads "Yes" like every other row; what the
  field means for them is not stated. They are kept as printed.

### 3.3 EIA Henry Hub spot

* **EIA's NYMEX futures series stop on 5 April 2024.** The data page's heading
  says "(Futures prices after April 5, 2024, are not available)".
* **Two January 2026 values sit above 25 USD/MMBtu**: 30.72 on 23 January and
  25.01 on 26 January. They are EIA's prints and are kept; the study's bound
  for Henry Hub is 0.5 to 50, a guard against a price read in cents (open
  question 3).
* **Holidays are omitted, except from July 2015 to November 2017**, when rows
  repeat the previous business day. 1997 to 2006 are sparse. 2018-01-05 is a
  dated row with no value. A monthly average must use the days present and
  must not impute.

### 3.4 World Bank Pink Sheet

* **The workbook's path changes.** Its link is read from the landing page every
  time, and the adapter fails when it finds none or more than one.
* **A hidden sheet, "Mismatch Details", comes first.** Open "Monthly Prices" by
  name, never by index, and find each series by its label, checked against the
  unit printed below it.
* **Three spellings of the missing value token:** an ellipsis character in the
  Japan column before 1977, three full stops elsewhere in the file, and two in
  the notes.
* **The Europe series changes definition twice inside one column**: TTF from
  April 2015, an average import border price with a spot component including the
  UK from April 2010 to March 2015, and the same excluding the UK from June 2000.
* **The Japan series is an import price, cif, and its last two months are
  estimates** that the next release revises: June 2026 read 12.83 in the release
  of 2 July 2026 and 11.79 in that of 2 September 2026.
* **The "Terms of use for Datasets" link redirects to the general terms**, which
  are narrower. The dataset terms are one level down.
* **Kept from January 2015.** Earlier values (Europe 0.38 in January 1964, US
  0.14 in January 1960) would fail the study's validation ranges, and the study's
  monthly history starts in 2015.

### 3.5 Federal Reserve H.10

* **The Data Download Program is being retired.** The Board removes its "Build
  Your Package" option the week of 9 November 2026 and plans further removals in
  2026 and 2027. Long date ranges already return HTTP 200 with an empty body. The
  release page XML is the route the Board says will remain.
* **A day with no rate carries `OBS_VALUE="-9999"`** with `OBS_STATUS="ND"`. It is
  read as missing; a parser that reads the value would publish a price of minus
  9,999 dollars per euro.
* **Every weekday has a row**, holidays included as no data.
* **The rate is a New York noon rate, released weekly on Mondays**, so the latest
  value can be about ten days old. The series is corrected after the fact: the
  rate for 3 August 2026 was corrected on 12 August 2026.
* **The direction of the quote is not in the data columns.** The series' short
  description, "EMU Members Euro (USD per EUR)", is checked on every parse.
* **Cross check:** from 2015 the XML agrees with the history page
  `dat00_eu.htm` on all 3,062 weekdays, no data days included.

### 3.6 New York Fed SOFR

* **The sibling repository's SOFR series is read through FRED**, not from the
  New York Fed. This study reads the New York Fed's API directly.
* **SOFR's first value date is 2 April 2018**, published on 3 April 2018. A
  start check copied from a FRED based cache would refuse the first row.
* **Rows come newest first**, and a day with no publication has no row at all.
* **Percentiles can be the string "NA"** (31 May 2019, 5 August 2021) and can be
  negative. Only the rate is read.
* **No SOFR exists before 2 April 2018.** Nothing is filled in. Before then the
  financing line runs on EFFR (open question 12), a different rate: unsecured
  where SOFR is secured.
* **EFFR's source and method change inside its window.** From 1 March 2016 it
  is a volume weighted median of FR 2420 transactions; before, a volume
  weighted mean of brokered trades. The cache's method column says which.
* **EFFR's API rows come in two layouts in one response**: the 39 rows before 1
  March 2016 carry intraday figures, the rest percentiles and volume. The API's
  own description names the rate `percent`, where every row carries
  `percentRate`.
* **The Board's H.15 carries the same EFFR**, public domain: on all 585 days from
  4 January 2016 to 30 April 2018 the two agree. The New York Fed's copy is read
  because it is the rate's publisher and the study already reads its API.

### 3.7 METI spot LNG

* **METI's site answers automated requests with a bot challenge** after a
  handful of files: HTTP 202 with an empty body and the header
  `x-amzn-waf-action: challenge`. A script that treats 202 as success writes
  empty files. The survey ended with March 2021, so the pipeline reads the
  workbook fetched once and never refetches.
* **The workbook drops the preliminary figures.** Each month's PDF revises the
  month before it (December 2020, contract-based: 8.6 preliminary, 7.4
  detailed), and a March issue can fix the year before (February 2019 is the one
  month labelled "Fixed"). Only the PDFs carry the earlier vintages.
* **A month METI did not publish is a multiplication sign** (U+00D7) in the
  workbook, never a zero or a blank.
* **METI's own text is not always consistent.** Its release for August 2020
  quotes July 2020 contract-based at 5.2, labelled "detailed", while its table and
  the workbook give 4.2; its releases for January and February 2021 announce a
  "Change" to figures that are printed unchanged.
* **File names switch** from `YYYYMM-e.pdf` to `YYYYMM_e.pdf` in May 2018.
* **A release prints two months, or three**: the survey month as Preliminary,
  the month before as Detailed and, where METI corrected one again, a month of the year
  before as Fixed, each marked with one, two or three asterisks against a key
  under the table; the release for March 2020 prints a Fixed month, that for
  March 2021 does not. The detailed release of March 2021, the last, has no
  preliminary row. The preliminary figure can move by a dollar or more: July
  2020, 5.2 then 4.2; December 2020, 8.6 then 7.4.

### 3.8 JOGMEC spot LNG

* **The confirmed figure has no page of its own.** It is printed in the first
  column of the next month's page. A month undisclosed at the preliminary stage
  can be disclosed when confirmed (July 2022 arrival-based, May 2025
  contract-based).
* **The arrival-based definition changed with the April 2023 release**, from
  cargoes contracted and delivered in the month to cargoes delivered in the month
  whenever contracted.
* **Undisclosed is a horizontal bar**, U+2015, not a hyphen and not a zero.
  JOGMEC withholds a month when fewer than two companies imported spot LNG:
  26 of 65 contract-based months and 41 of 65 arrival-based months to August
  2026.
* **JOGMEC's publications disagree once.** April 2026 contract-based is 19.2 on
  the May 2026 page, in English and in Japanese, and 19.1 in both historical
  workbooks. The study follows the page, which states the revision in words.
* **Pages are edited in place and have been renamed.** The August 2022 page was
  updated on 12 October 2022; the pages for October and November 2025 were once
  served without the `-preliminary` suffix. A first release can only be kept by
  saving it when it appears.
* **JOGMEC writes the unit as "USD/MBtu".** The same pages quote Henry Hub in
  that unit at a level that only makes sense per million Btu, so it is read as
  USD/MMBtu. That is an inference, not JOGMEC's statement.

### 3.9 ACER

* **ACER's daily reports are on its TERMINAL platform**, at
  `aegis.acer.europa.eu`, which this pipeline never fetches, by the owner's rule
  for this study. That host serves no robots.txt at all (HTTP 404), so the rule
  is not written there; it is kept as a rule of this study. ACER's main site,
  which its robots.txt allows, publishes no report and no data file.
* **TERMINAL offers the whole history as one CSV file**, "PA historical", with
  the three assessments and the benchmark for every day ACER published, newest
  first, and an empty cell for a value not published. ACER publishes on its
  working days only, its holidays set by a decision TERMINAL links; the
  benchmark also needs ICE's settlement. The days with no row (68 weekdays to 8
  October 2026, Christmas and Easter among them) are listed as gaps. The owner saved it by hand on 8 October 2026;
  the benchmark of that day itself was not yet published. On the 26 days of
  the correction notice it gives the corrected values exactly on 25 days; on 4
  December 2024 its EU assessment, 47.322, differs from the notice's 47.323 by a
  thousandth, which is noted.
* **The NWE spread is computed, not published**: the EU benchmark plus the NWE
  assessment less the EU one, the NWE assessment's spread to the TTF front
  month. No TTF level is computed. From April to August 2023 it averages -2.33
  EUR/MWh, against the about 2 EUR/MWh ACER's monitoring report prints for the
  EU spread from January to August 2023.
* **A jump in TTF opens a spread the assessment cannot follow at once**: on 2
  and 3 March 2026 the EU benchmark was -14.095 and -23.938 EUR/MWh, the TTF
  front month having jumped while the assessed half-month had not yet moved.
  The engine takes the spread's mean over the week or month a price spans.
* **The benchmark is EU minus TTF, not NWE minus TTF.** An NWE figure would be
  derived by this study, not published by ACER.
* **The series start on different days**: the first report on 13 January 2023,
  without a price; the first NWE price on 19 January 2023; SE from 20 January
  2023; the EU price from 8 March 2023; the benchmark from 31 March 2023.
* **The assessed half-month rolls on dates ACER publishes as a table**, not by a
  formula. The table in the methodology ends with the period rolling on 24
  December 2024; for later reports the period has to be read from the report.
* **ACER corrects published values in place**, as it did for 26 days in
  November and December 2024. A report saved when it appears is the only record
  of what was first printed.
* **One row of ACER's own correction table is inconsistent**: on 18 November
  2024 the benchmark moves by 0.475 while the EU assessment moves by 0.044, where
  every other row moves them together. It is kept as ACER printed it and flagged.
* **Printed differences disagree with the printed values by up to about one
  thousandth**, because ACER rounds after computing them.

### 3.10 European Commission auction reports

* **Each report's Table 1 covers fifteen months**, so several editions are read
  and each month is taken from the latest that prints it. Months printed by up
  to five editions agree exactly.
* **The reports lag.** On 8 October 2026 the latest covers April to June 2025;
  after June 2025 the study uses DEHSt's averages of the German auctions, a
  labelled proxy (3.10.1).
* **A month with no auction prints dashes** (January 2021), read as missing.
* **Annual rows sit under the monthly ones** and are not read as months.

### 3.10.1 DEHSt's auctioning reports

* **German auctions only, a proxy for the EU price.** Germany auctions its
  share weekly on EEX, apart from the common auction platform. Over the 18
  months both cover, January 2024 to June 2025, the German average is 0.10
  EUR/t above the Commission's on average, 0.64 EUR/t in absolute terms and
  1.40 EUR/t at most (May 2024). Used only after the Commission's last month.
* **The average changes kind.** A month marked "*" is a simple average of its
  auctions, "**" a volume weighted one (August and December of each year read);
  the `average` column keeps the mark.
* **Reports to 2024 add a type column.** Aviation allowances (EUAA) were
  auctioned in some months, in rows of their own; October 2024 prints its name
  on a line between its EUA and EUAA rows. Only EUA rows are read.
* **One report a year is enough.** Each report's year table carries every month
  of the year so far, so the latest report of each year is read, a quarter
  counting to its third month. On 8 October 2026 these are the fourth quarter
  of 2024 and of 2025 and August 2026.
* **Every month's volume times its price gives its revenue** to within half a
  cent per allowance; a month that did not would be noted in `anomaly`.
* **The page's dates are not used.** The January 2026 report is dated
  "07/04/2025" on the page.

### 3.11 The routes

* **searoute measures in nautical miles only with `units="naut"`.** It also
  accepts `units="nm"`, which returns lengths 1.32 times too long.
* **Pass the restrictions on every call.** The network object is cached, and a
  call with `restrictions=None` reuses the previous call's restrictions.
* **searoute draws the Pacific crossing past -180 degrees** as one continuous
  line, down to -220.36 degrees of longitude, rather than jumping to +180. A
  distance test that wraps each vertex on its own invents a segment spanning
  the globe; `lngarb.sea_routes` wraps each segment once, and a map must split
  the line.
* **The line starts and ends at the network nodes nearest the terminals**, 1.4
  to 3.9 nm away. The recorded distances exclude those gaps, as the library
  returns them.
* **The three terminal points are this study's.** Sabine Pass (-93.87, 29.74),
  Gate (4.03, 51.96) and Futtsu (139.82, 35.30), longitude then latitude, were
  set for this study and are not taken from a published list; they are
  recorded in `src/lngarb/sea_routes.py` and in the seed.
* **The Suez route leaves the Straits of Florida eastwards at about 25.3 N**,
  which reads as crossing the shallow Great Bahama Bank. Forcing it through deep
  water adds 44 to 53 nm, 0.3 to 0.4 percent.
* **Florida Strait and Dover Strait are not in searoute's passage list**, so
  they are tested from the geometry against reference points, with the
  distances recorded in the seed.
* **The independent test.** Spark's methodology gives Spark30, Sabine Pass to
  Gate and back, 25 sailing days at 17 knots; the computed round trip is 24.41
  days, 2.4 percent shorter. EIA gives the Suez and Cape routes from the Gulf
  Coast to Chiba as about 17 and 21 days longer than Panama; the computed extra
  distances stand in the ratio 0.816 against EIA's 0.810, and both imply about
  13 knots. EIA's days are rounded, so any ratio from 0.767 to 0.854 agrees
  with them, and its ships are LPG carriers: the test confirms the order of
  the three routes and their rough proportion, not the distances. Platts'
  figure for the Panama route could not be read: its site refuses automated
  requests, even for robots.txt.

### 3.12 Suez Canal Authority

* **The toll is not in dollars.** It is special drawing rights per ton of Suez
  Canal Net Tonnage, in seven bands, laden and ballast, payable in one of ten
  currencies the schedule lists. A dollar toll embeds an SDR rate and a date.
* **The tonnage is not the cargo capacity.** A canal agency's guidance, read
  at `https://kadmar.com/calculator-guidelines/`, says: "For the LNG vessels the
  SCNT depends on the construction, and the SCNT is reflected on the volume of
  the hull, not the cargo carrying capacity." Membrane and spherical tank ships
  of the same capacity differ.
* **A circular's HTML page holds only its heading.** The articles come from the
  Authority's API (2.10). Some instruments are scans with no text layer, and one
  sets its bands in a map image.
* **Dates disagree in small ways.** Periodical 7/2025 is listed "on 27/05/2025"
  and dated 28 May 2025 on its page; periodical 28/2026 is listed "on 7/09/2026"
  and dated 8 September 2026. The page date is used.
* **The annual reports' folder name carries three zero width spaces**
  (`Annual%20Reports%E2%80%8B%E2%80%8B%E2%80%8B`); a URL typed by hand fails.
* **The LNG surcharge is not in the schedules.** LNG carriers, laden and
  ballast, pay a surcharge on top of normal dues: 7 percent from 1 March 2022
  (circular 5/2022), 19 percent from 15 July 2026 (periodical 20/2026 of 7 June
  2026), which says the surcharges "are temporary and can be either amended or
  cancelled".
* **A general LNG reduction existed and is gone.** 35 percent from circular
  8/1994, 25 percent from 1 May 2015 (circular 2/2015), 15 percent from 1
  November 2021, cancelled from 15 March 2022. The February 2022 schedule still
  prints the 15 percent line, and agency pages still repeat older figures.
* **The rebate for US Gulf cargoes to Asia is often misdated.** The IEA's Gas
  Market Report for Q1 2024 says that "In October 2023" the Authority set
  "reductions on canal tolls ranging from 30% for destinations west of Kochi in
  India, to 70% for Singapore and beyond". The Authority's own texts say
  otherwise: the terms in force from 1 July 2023 were set on 21 June 2023 and
  give 75 percent for "Port Klang" and its eastern ports; "70% for Singapore
  and beyond" is the wording in force during 2022; the October 2023 circular,
  7/2023, is the 15 percent toll increase from 15 January 2024. The dated rates
  are in `docs/methodology.md`, section 6.
* **The rebate has conditions.** From 1 January 2025 it covers only carriers
  "directly operating" between the two areas, and since 2017 the ship "must not
  call any port in between port of origin and port of destination for
  commercial purposes". It excludes every other LNG rebate.
* **The rebate is renewed half year by half year**, each periodical a few
  weeks before its half year starts. The latest read runs to 31 December 2026;
  nothing published covers transits after that.
* **One link in the Authority's own records is wrong.** The cancellation of 14
  March 2022 points to circular 5/2015, while its text cancels article two of
  circular 2/2015. The text is followed.
* **The 2023 increase sits in a circular of 2022.** Circular 14/2022, dated 18
  September 2022, raised normal dues 15 percent from 1 January 2023; its LNG
  row is the earlier one times 1.15 to within 0.01. Searching the circulars of
  2023 does not find it.
* **The LNG row did not move from 2014 to 2022.** The schedules of 1 May 2015, 1
  April 2020 and 1 February 2022 print the same figures; circular 5/2021
  raised other dues 6 percent "excluding ... LNG Carriers". The schedule of
  2015 is a sideways scan with no text layer, read by eye.
* **The general reduction moved in 2020.** It was 30 percent from 1 April to
  30 June 2020, then 25 percent again, before the cut to 15 percent in
  November 2021. A US Gulf cargo to Japan took the larger route rebate
  instead, which cannot be combined with it.

### 3.13 The Red Sea record

* **A canal transit is not a Red Sea crossing.** The Authority's yearly counts
  of LNG ships, 819 in 2023, 119 in 2024 and 282 in 2025, include ships that
  enter from the north to deliver at Ain Sukhna or Aqaba and never pass Bab el
  Mandeb. Kpler counted 26 LNG transits of the canal in 2025 to 8 May, of which
  one crossed Bab el Mandeb.
* **Laden and ballast counts differ.** The Oxford Institute counts laden
  carriers (434 in 2023); the Authority counts all (819 in 2023). Several of the
  crossings after January 2024 were ballast repositionings.
* **"QatarEnergy paused" is a report, not a statement.** The National's
  article of 15 January 2024 reports ship tracking and says QatarEnergy did not
  respond; the halt itself is a Reuters report cited by the Oxford Institute.
  EIA's list of companies "pausing Red Sea transits" as of 23 January 2024 is
  the cleanest public statement naming QatarEnergy.
* **One source dates the halt to February 2024** (the Baker Institute, March
  2026). The Oxford Institute's day by day account from port calls, written in
  February 2024, puts the last laden LNG transit on 12 January.
* **Russia linked and sanctioned ships made several of the 2024 crossings.**
  They are not evidence that the route was open to a US cargo.
* **The only source for March to July 2026 is secondary**: an investor
  newsletter citing S&P Global data the study cannot read.
* **A search engine summary of the Authority's 2025 report turned "137.0"
  percent into "137 vessels".** The count is 282.

### 3.16 Panama Canal Authority

* **The toll changed structure in 2023.** Until 2022, rates per m3 fall by
  band of capacity, with a ballast table and a lower roundtrip ballast table;
  from 2023, a fixed charge per transit plus one rate per m3, and ballast at 85
  percent of laden on those two components only.
* **A printed effective date is not always the date of the amount.** The fixed
  charge prints "1-Jan-2024" with the symbol MW, a change of wording; the
  300,000 $ dates from 1 January 2023.
* **The rate is on capacity as the canal measures it**, "as determined by the
  admeasurement performed by the Panama Canal", not on the cargo carried. The
  admeasurement rules were not read; the nominal capacity stands in for the
  admeasured one as an assumption (question 39).
* **Size category is by dimensions.** A neopanamax vessel has a beam over
  32.61 m and/or a length over 294.44 m; the 2025 deck also classes by draught.
  The booking fee depended on beam from 2021.
* **The fresh water surcharge is not in the toll tables.** It is a separate,
  mandatory item since 15 February 2020, set daily from Gatun Lake's level.
* **Advisories date changes by booking date or by transit date**, and some
  were postponed after publication: the booking fees of 70,000 and 85,000 $
  announced for 15 April 2021 took effect for booking dates from 1 June 2021.
* **The tariff decks' item descriptions carry en dashes**, as published; they
  are quoted around them.
* **The IEA and the Authority disagree in places**: three LNG slots a day from
  August 2024 (IEA) against an LNG cap of two through normal booking (the
  Authority's notices); 27 vessels a day in 2025 (IEA) against 36 booking
  slots from 1 September 2024; only 24 transits in early 2024 against 27
  booking slots from March 2024; LNG carriers "prohibited from night transits"
  (IEA) against the lifting of the daylight restriction in 2018. The
  Authority's own texts are followed (question 42).

### 3.14 Spark's note on negative freight rates

* **Never read its figures from the text layer.** The layer interleaves the
  two columns of every page and drops the last character of many lines
  ("24,50" for 24,500). Every figure is read from the rendered page.
* **The note is undated.** The live file's `Last-Modified` header, 10
  September 2026, is the web site's, not the note's. The copy the Internet
  Archive captured on 16 February 2022 carries PDF metadata of 14 February 2022
  and the same words, page for page.
* **The printed total is one dollar more than its printed parts.** 1,186,288 +
  308,947 + 1,692,355 = 3,187,590, printed 3,187,591. The total uses the laden
  fuel rounded to the dollar (exact 1,692,355.686), the laden fuel line prints
  it truncated. Every other line is the exact value rounded to the dollar.
* **The laden fuel line reads "17.5 (Ballast Days)"**, a slip for laden days.
* **The discharge volume is not explained in the note.** Spark's own
  definition of 2022 (98.5 percent of capacity, less laden boil-off, less a
  heel of 3,000 m3) gives 3,501,428 MMBtu exactly with fifteen days of laden
  boil-off; the note does not say which laden days it used (open question 23).
* **The Futtsu figure is an image.** The Routes screenshot on page 3 has no
  text layer; 273,184 $ is read from the picture, and its cost lines add up to
  its total.
* **Every page reads "All data and images are copyright • Spark
  Commodities".** Individual figures are quoted with attribution; nothing else
  is reproduced.

### 3.15 Port charges

* **Net and gross tonnage are taxed differently.** Japan's two tonnage taxes
  are on net tonnage; Kisarazu's entry dues and Tokyo Bay pilotage are on
  gross tonnage; the Suez toll is on a third tonnage of its own.
* **Futtsu is in Kisarazu port, not Chiba port.** Chiba prefecture's Kisarazu
  page places JERA's Futtsu power station in the port's Futtsu district.
* **Japanese pilotage tables are caps.** Each pilot notifies the fee actually
  charged within the cap; no notified table for Tokyo Bay was found online.
* **Rotterdam's dues have a cargo part per tonne**, so they depend on the cargo
  as well as the ship, and from 2025 a sustainability component per GT is added
  while the GT rate falls. In 2024 the cargo part of an LNG tanker is capped at
  133.7 percent of its GT; the 2025 and 2026 efficiency discount tables give
  ratios for other ship types and none for LNG tankers, so whether their cargo
  part is still capped is not stated.
* **The Sabine pilots' "gross ton unit" is computed from dimensions**, not
  read from the ship's certificate.
* **A capacity is not a propulsion.** GasLog's fleet list carries 174,000 m3
  ships with tri-fuel diesel electric (TFDE) propulsion and others with
  two-stroke engines.

---

## 4. Positions taken, and what is left to the owner

Every position this study takes on a source, with the open question that
records it. Those marked **owner** need a step only the owner can take, and
the study runs without it, on the labelled position given.

1. **The weekly JKM and TTF archive** is read from the Internet Archive's
   copies, never from eia.gov by code (question 1); the Supplement's past
   issues no capture holds were read from EIA's archive pages in a browser, as
   the manual step (3.1).
2. **Third party figures in EIA publications** are committed with the credit
   EIA prints, and move to `data/private/` should EIA or a rights holder object
   (question 2).
3. **The Henry Hub bound** is 0.5 to 50 USD/MMBtu (question 3).
4. **The euro rate** is read from the H.10 release page package (question 11).
5. **SOFR** is published under the New York Fed's terms with its notice, and
   the **effective federal funds rate** stands in before 2 April 2018 on the
   same terms (question 12).
6. **JOGMEC's series** stays private; **owner**: send the permission request
   drafted in question 14.
7. **METI's monthly PDFs**: the releases of October 2019 to March 2021 were
   saved by hand and their figures are committed; the 67 earlier ones would add
   older preliminary figures (**owner**, optional).
8. **ACER's history**: TERMINAL's download, saved by hand on 8 October 2026,
   gives the observed Northwest Europe discount from 31 March 2023; before it
   the discount is a labelled assumption (question 18). TERMINAL shows no terms
   of its own, so ACER's legal notice is applied (question 19); **owner**: save
   the download again to extend it, and record TERMINAL's legal notice should
   one appear.
9. **The EU allowance price after June 2025** is the monthly average of
   Germany's auctions DEHSt reports, a labelled proxy, to August 2026, and that
   month held after it, shown at 61 and 86 EUR/t; **owner**: write to EEX and
   the Commission (question 20).
10. **The route lines** are published under the EUPL 1.2 (question 21).
11. **The Suez toll** is computed from the Authority's schedules with the
    tonnage a labelled assumption (question 25), the rebate on normal dues only
    (question 26) and on the ballast leg too (question 27), converted at the
    IMF's SDR rate of each transit day, committed with the IMF credited
    (question 46).
12. **The Red Sea** is closed to a US cargo from 13 January 2024 (question 28).
13. **The Suez Canal Authority and the Panama Canal Authority** are quoted for
    rates, dates and counts, with no document copied (questions 30 and 41).
14. **Port costs** are Spark's two pairs, held for every year and both ships
    (questions 31 to 33).
15. **Spark's figures** are quoted individually as fair use (question 36), and
    **the freight anchors** commit figures, never sentences (question 37).
16. **Lloyd's List and Lloyd's List Intelligence** are dropped (question 38).
17. **The Panama inputs** are the nominal capacity, the roundtrip ballast table
    before 2023, the fresh water surcharge at 5 percent of tolls, and no booking
    fee or waiting days by default (questions 39 and 40).
18. **The contract terms** come from Cheniere's filings as its investor sites
    republish them; **owner**: decide whether EDGAR is to be read with a contact
    address in the user agent (2.21).
19. **The TTF and JKM expiry rules** are ICE's, with the UK calendar
    (question 44).
20. **Methane slip** is off by default (question 45), and **MMBtu per tonne** is
    the IEA and Eurostat's factor; **owner**: GIIGNL's report, saved by hand,
    could replace it (question 47).
21. **Figures others reported** (cancellations, route use, Platts'
    assessments) are quoted individually with their source and never used as
    inputs (2.24).

---

## 5. How to check

* `python scripts/refresh.py --offline` remeasures every committed cache with
  no network and rewrites the manifest only if something other than the clock
  changed.
* `node tools/validate-data.mjs` measures the same files again in JavaScript,
  independently, and checks the house rules over every tracked file.
* `python -m pytest tests` runs every parser against committed fixtures, with
  no network.
