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
| `eia_ngwu_international_weekly` | Weekly averages of an East Asia LNG price and of TTF, USD/MMBtu, from the Natural Gas Weekly Update, figures credited to Bloomberg Finance L.P. | [landing page](https://www.eia.gov/naturalgas/weekly/) only; the archive is closed to code | weekly, ended with the week ending 21 January 2026 | **yes**, with the doubt in 2.1 | US public domain |
| `eia_ngwu_issue_index` | Every issue EIA lists from 2016, the checklist for collection by hand | [archive.php](https://www.eia.gov/naturalgas/weekly/includes/archive.php) | fixed, the series has ended | **yes** | US public domain |
| `eia_wngsr_international_weekly` | Weekly averages of JKM and TTF, USD/MMBtu, from the WNGSR Supplement, figures credited to Bloomberg Finance L.P. | [bullets_lng_2.html](https://www.eia.gov/naturalgas/weekly/supplement/content/bullets_lng_2.html) and two sibling files | weekly, Thursday, only the current issue | **yes**, with the doubt in 2.1 | US public domain |
| `eia_lng_exports_monthly` | US LNG exports and re-exports by destination country, MMcf, the latest release | [NG_MOVE_EXPC_S1_M.xls](https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls) | monthly, end of month | **yes** | US public domain |
| `eia_lng_exports_revisions` | Every value a release of the table above changed, both releases side by side | derived by this study | with each release | **yes** | US public domain |
| `eia_henry_hub_daily` | Henry Hub spot price, daily, USD/MMBtu, credited by EIA to Refinitiv | [RNGWHHDd.xls](https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls) | weekly release, daily values | **yes**, with the doubt in 2.1 | US public domain |
| `acer_lng_daily` | ACER's DES LNG assessments for NWE, SE and the EU, and its EU benchmark to TTF, daily, EUR/MWh; today the 26 corrected days of its notice of 20 December 2024 | [correction notice](https://www.acer.europa.eu/sites/default/files/documents/en/Gas/LNG_Price_Assessment/LNGPA_Correction_Notice_20241220.pdf); daily reports saved by hand | fixed until reports are saved | **yes** | ACER legal notice, with the doubt in 2.7 |
| `ec_eua_auction_monthly` | EU allowance price, monthly volume weighted average auction clearing price, EUR/t, January 2023 to June 2025 | quarterly reports linked from the [Commission's auctioning page](https://climate.ec.europa.eu/areas-action/carbon-markets/eu-emissions-trading-system-eu-ets/auctioning-allowances_en) | quarterly, lagging | **yes** | CC BY 4.0, with the doubt in 2.8 |
| `meti_spot_lng_monthly` | Japan spot LNG price, DES, contract-based and arrival-based, monthly, March 2014 to March 2021 | [historical-data-e.xlsx](https://www.meti.go.jp/english/statistics/sho/slng/historical-data-e.xlsx), read once | ended | **yes** | METI terms, compatible with CC BY 4.0 |
| `jogmec_spot_lng_monthly` | Japan spot LNG price, DES, contract-based and arrival-based, monthly, from April 2021 | one page per month from the [list page](https://journal.jogmec.go.jp/oilgas/nglng-en/spotprice/index.html) | monthly, 9th to 15th | **NO**, `data/private/` until JOGMEC permits | JOGMEC terms, permission requested |
| `worldbank_gas_monthly` | Europe gas (TTF from April 2015), US gas at Henry Hub, and Japan LNG import price, monthly, USD/MMBtu, from 2015 | read from the [commodity markets page](https://www.worldbank.org/en/research/commodity-markets); the file's path changes | monthly, early in the month | **yes** | CC BY 4.0 |
| `worldbank_gas_revisions` | Every value a Pink Sheet release changed, both releases side by side | derived by this study | with each release that changes a value | **yes** | CC BY 4.0 |
| `h10_usd_per_eur_daily` | US dollars per euro, noon buying rate in New York, daily, from 2015 | [FRB_h10_xml.zip](https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip) | weekly, Mondays | **yes** | US public domain |
| `nyfed_sofr_daily` | Secured Overnight Financing Rate, daily, percent, from 2 April 2018 | [markets API](https://markets.newyorkfed.org/api/rates/secured/sofr/search.json) | daily, next business day | **yes**, under the New York Fed's terms | New York Fed Terms of Use |
| `routes` | The four sea routes from Sabine Pass, distances and lines | computed once by `scripts/routes.py` | fixed | **yes** | this study, MIT; searoute Apache 2.0 |

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

### 2.4 Federal Reserve Bank of New York, SOFR, licensed

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

**Redistributable: yes, under the New York Fed's terms, not this repository's.**
The committed SOFR cache travels under those terms, not under the MIT licence.
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

**Redistributable: no, not without JOGMEC's permission**, which has been
requested (`docs/open-questions.md`, question 14). The series is kept in
`data/private/`; no value, chart or derived figure from it is published, and
the public pages carry no link to JOGMEC until JOGMEC allows it.

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

ACER's methodology and notices print: "Reproduction is authorised provided the
source is acknowledged."

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
licence field. **The distances are this study's computation and are published.
Whether the committed lines may be published under this chain is an open
question for the owner** (section 4).

---

## 3. Known traps, per source

### 3.1 EIA Natural Gas Weekly Update and its successor

* **The archive is closed to code.** eia.gov's `robots.txt` carries
  `Disallow: /naturalgas/weekly/archivenew_ngwu` for every user agent, and
  `Disallow: /*archive/`, which also covers the Supplement's archive. Nothing in
  this repository fetches either; `lngarb.sources.base.http_get` checks
  `robots.txt` before every request and refuses a disallowed URL.
* **Python's `urllib.robotparser` says "allowed" to every path on eia.gov.** The
  file opens with `Allow: /`, and the standard library applies the first
  matching line rather than the longest. The project's own parser implements
  RFC 9309, and a test proves the difference on EIA's file as served.
* **The Natural Gas Weekly Update has ended.** Its final issue, released on 22
  January 2026 for the week ending 21 January 2026, says: "This week is the
  final publication of the Natural Gas Weekly Update." The landing page still
  serves that issue. A job polling it keeps finding the same week and must not
  append it twice.
* **The successor is a different product.** From 29 January 2026 the WNGSR
  Supplement prints "The Japan-Korea Marker (JKM) price" and "The price at the
  Title Transfer Facility (TTF) in Europe", where the Weekly Update printed
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
  every Thursday. A week not collected while current can only be recovered by
  saving the archived page by hand.
* **The archive index needs care.** Take each issue's date from the folder in
  its link, never from the month and day cells, which are missing or wrong on
  several rows. Drop rows inside HTML comments: the 2026 tab carries a commented
  copy of 41 rows of 2025. Expect a row that says "No report released" (release
  20 June 2024) and a Friday release (10 January 2025).
* **Items carry extra sentences.** The final issue adds a sentence on EU storage
  after the prices. Parse by sentence content, never by position.
* **Changes are printed in more than one form**, with and without "/MMBtu", in
  dollars or in cents.

### 3.2 EIA exports by destination

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

### 3.3 EIA Henry Hub spot

* **EIA's NYMEX futures series stop on 5 April 2024.** The data page's heading
  says "(Futures prices after April 5, 2024, are not available)".
* **Two January 2026 values sit above 25 USD/MMBtu**: 30.72 on 23 January and
  25.01 on 26 January. The study's declared bound for Henry Hub is 0.5 to 25,
  so the adapter refuses the workbook and keeps nothing until that bound is
  decided (section 4).
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
* **No SOFR exists before 2 April 2018.** Nothing is filled in; how the
  financing line is treated before then is an open question.

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
* **The reports lag.** On 30 September 2026 the latest covers April to June
  2025, and no allowance price after June 2025 is in this study.
* **A month with no auction prints dashes** (January 2021), read as missing.
* **Annual rows sit under the monthly ones** and are not read as months.

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
  13 knots. Platts' figure for the Panama route could not be read: its site
  refuses automated requests, even for robots.txt.

---

## 4. Positions the owner has to take

1. **The weekly JKM and TTF archive.** The Natural Gas Weekly Update archive is
   closed to code. Either the issues are saved by hand into
   `data/private/ngwu/`, or EIA is asked for permission or for the series.
2. **Third party figures in EIA publications.** Whether the weekly prices
   credited to Bloomberg and the spot price credited to Refinitiv may be
   committed under EIA's public domain statement.
3. **The Henry Hub bound.** Whether the declared upper bound of 25 USD/MMBtu is
   widened, or the two January 2026 values are listed as exceptions.
4. **The euro rate's route.** This study reads the Board's release page XML
   rather than its Data Download Program, which the Board is retiring.
5. **SOFR's source and licence.** This study reads the New York Fed's API under
   the New York Fed's terms, which travel with the committed cache.
6. **Financing before 2 April 2018**, when no SOFR exists.
7. **JOGMEC's permission**, requested with the draft in `docs/open-questions.md`,
   question 14.
8. **METI's monthly PDFs**, which only a person can save past METI's bot
   challenge, and which alone carry METI's preliminary figures.
9. **ACER's reports**, which only a person can save from TERMINAL, and whether
   the observed discount is ACER's EU benchmark or an NWE spread this study
   derives from ACER's figures.
10. **The EU allowance price after June 2025**, which the Commission has not yet
    published.
11. **Whether the route lines may be published** under the licence chain in
    2.9, or only the distances.

---

## 5. How to check

* `python scripts/refresh.py --offline` remeasures every committed cache with
  no network and rewrites the manifest only if something other than the clock
  changed.
* `node tools/validate-data.mjs` measures the same files again in JavaScript,
  independently, and checks the house rules over every tracked file.
* `python -m pytest tests` runs every parser against committed fixtures, with
  no network.
