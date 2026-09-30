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

### 2.2 The routes, this study's computation

The distances and lines in `data/seed/routes.json` and `data/seed/routes.geojson`
were computed by this study with searoute 1.6.0
(`https://github.com/genthalili/searoute-py`), released under the Apache License
2.0, over the Eurostat SeaRoute maritime network the library bundles. The
library is a development tool; it is not shipped with the site.

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

### 3.4 The routes

* **searoute draws the Pacific crossing past -180 degrees** as one continuous
  line, down to -220.36 degrees of longitude, rather than jumping to +180. A
  distance test that wraps each vertex on its own invents a segment spanning
  the globe. `lngarb.sea_routes` wraps each segment once.
* **Florida Strait and Dover Strait are not in searoute's passage list**, so
  they are tested from the geometry against reference points, with the
  distances recorded in the seed.

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

---

## 5. How to check

* `python scripts/refresh.py --offline` remeasures every committed cache with
  no network and rewrites the manifest only if something other than the clock
  changed.
* `node tools/validate-data.mjs` measures the same files again in JavaScript,
  independently, and checks the house rules over every tracked file.
* `python -m pytest tests` runs every parser against committed fixtures, with
  no network.
