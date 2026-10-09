# Methodology

How this study turns published figures into the numbers it shows: the data
layer, the engine, the analysis and the site.

---

## 1. Rules the data layer keeps

1. **Nothing is invented.** A source that fails, or a date a source did not
   publish, is missing. In a CSV cache a missing value is an empty cell; in a
   JSON file it is `null`; on the site it is a word that says which figure is
   missing ("no figure" in a cell, "missing for this date" under a field, "no
   crossing" for a breakeven hire that does not exist), with the reason beside
   it or in the sentence under the table, never a bare "n/a" (open question
   49). Zero never means missing.
2. **Nothing is filled.** No interpolation, no carrying a value forward, no
   substitution from a neighbouring source without a label saying so.
3. **A failed fetch keeps the previous cache.** The source is marked `failed`
   in `data/manifest.json` with the error, and the refresh exits non zero.
4. **Every cache is validated before it is written**: dates in order and
   unique, the declared bounds, a row count that did not shrink, and a minimum
   number of real observations in every value column. A series that failed
   or holds nothing stops the build, so no page with an empty chart is ever
   deployed: the site already live stays as it was until the series is mended.
5. **Every release is a vintage.** Where a publisher revises figures and keeps
   no old release online (EIA's exports table, the World Bank's Pink Sheet),
   the latest release is cached in full and every value a later release
   changes is logged beside the value it replaced.
6. **Provisional is labelled provisional.** A series whose latest months are
   estimates carries `provisional_from` in the manifest.
7. **A figure printed with a typo is kept as printed** in a `_printed` column,
   next to the value read from it, with the correction described in the
   `anomaly` column. It is never corrected silently.
8. **Sources are read the way their publishers allow.** Every request checks
   the host's `robots.txt` first, with the matching rules of RFC 9309, and a
   disallowed URL is never requested. What can only be read by hand is a manual
   step recorded in the manifest, with what it is, why it is needed and what
   skipping it costs.

---

## 2. Units

TTF is quoted in euros per megawatt hour; JKM and Henry Hub in US dollars per
million British thermal units; all on a gross calorific value basis. The one
conversion path is `lngarb.units.eur_mwh_to_usd_mmbtu`:

```
usd_mmbtu = eur_mwh * usd_per_eur / 3.412142
```

One megawatt hour is 3.6e9 joules and one British thermal unit (International
Table) is 1,055.05585262 joules exactly: NIST Special Publication 811,
appendix B.9, footnote 9, gives "1.055 055 852 62 kJ" (the table's 1.055 056
E+03 is rounded). So one MWh is 3.41214163 MMBtu. The study rounds this to
3.412142; the rounding moves a price by about one part in ten million. The
exchange rate is quoted as US dollars per euro, the direction the Federal
Reserve Board's H.10 release quotes it, and the argument is named for its
direction.

---

## 3. Validation bounds

Each value column is checked against a range before a cache is written. The
ranges catch a parse or a unit error, a price read in cents or a rate read in
basis points; they are not forecasts of where prices can go.

| Quantity | Range | Why this range |
|---|---|---|
| JKM, TTF and Japanese spot LNG, USD/MMBtu | 1 to 120 | the highest monthly value in the World Bank's Europe gas series is 70.04, August 2022 |
| Henry Hub, USD/MMBtu | 0.5 to 50 | EIA's daily spot price printed 30.72 on 23 January 2026 and 25.01 on 26 January 2026; the bound catches a price read in cents, not a high price (open question 3) |
| US dollars per euro | 0.8 to 1.7 | the euro's range on H.10 since 1999 is 0.8270 (25 October 2000) to 1.6010 (22 April 2008) |
| Reported charter hire, USD per day | minus 10,000 to 500,000 | a spot charter rate can be assessed below zero; the reported figures are in the freight anchors |
| DES LNG spreads to the TTF front month, EUR/MWh | minus 40 to 20 | widened when ACER's history was read: its EU benchmark ran from minus 23.938 on 3 March 2026, when TTF jumped and the assessed half-month did not, to 7.687 in June 2026 |
| US dollars per SDR | 1 to 2 | a rate read the other way up, SDR per dollar, would be below 1 |
| SOFR, and EFFR before it, percent per year | minus 1 to 15 | a rate read in basis points would be a hundred times too large |
| US gas exports in one month, MMcf | 0 to 2,000,000 | the largest monthly LNG total in EIA's release of 31 August 2026 is 573,089, March 2026 |
| Price of US LNG exports in one month, USD per thousand cubic feet | 0.1 to 100 | a price read per MMcf or in cents would be a thousand or a hundred times too large; from 2016 the release of 30 September 2026 runs from 1.86 to 40.44 |
| A DES LNG price level, EUR/MWh | 1 to 400 | a guard against a unit or a parse error in ACER's assessments, not a range the market implies |
| An EU allowance price, EUR per tonne of CO2 | 1 to 200 | a guard against a unit or a parse error, not a range the market implies |

The ranges are declared once in `src/lngarb/config.py` and repeated, on
purpose, in `tools/validate-data.mjs`, which measures the committed files
independently of the Python that wrote them.

---

## 4. Dates

| Series | Date column means |
|---|---|
| EIA weekly JKM and TTF | the last day of the report week, a Wednesday |
| EIA NGWU issue index | the release date of the issue, a Thursday except once |
| METI and JOGMEC spot LNG | the month, dated on the 1st |
| ACER DES assessments | the publication day; the half-month assessed is stored beside it where ACER's roll table gives it (31 March 2023 to early January 2025) |
| EU allowance price | the month of the auctions, dated on the 1st |
| EIA exports by destination | the month, dated on the 15th as EIA dates it |
| EIA Henry Hub, H.10, SOFR | the trading or value day |
| World Bank Pink Sheet | the month, dated on the 1st |

Gaps in the manifest are computed at each series' frequency: for a daily series
every weekday with no value, holidays included, because no holiday calendar is
applied; for weekly, monthly and annual series every period with no value,
reported at the start of the period (the Monday, the 1st of the month, the 1st
of January).

---

## 5. Structural breaks found in the data so far

| Where | When | What changes |
|---|---|---|
| EIA weekly JKM and TTF | between the weeks ending 21 and 28 January 2026 | the Natural Gas Weekly Update ends and the WNGSR Supplement begins, with new wording for both prices. Kept as two series. |
| EIA weekly JKM and TTF, wording only | the week ending 25 February 2026 | the one Supplement issue that names the product, "near-month futures", for both prices. Every change printed into and out of that week equals the difference of the levels, so it is read as the same series, not a break. |
| EIA weekly East Asia price | between the weeks ending 6 and 13 July 2022 | from a swap (for a named month, the prompt month, the balance of the month or a month not named, each with its weeks) to a futures price, called front-month from the week ending 14 December 2022 |
| EIA weekly TTF price | between the weeks ending 6 and 13 July 2022 | from a day-ahead price to a futures price |
| EIA weekly year-earlier figures | issues from January 2023 | the weeks of 2022 priced as swaps and day-ahead are reprinted on the futures basis, so none of them matches what the 2022 issue printed |
| World Bank Europe gas | April 2015 | TTF from here; an average import border price with a spot component, including the UK, from April 2010 to March 2015 |
| World Bank Japan LNG | every release | the last two months are estimates and are revised |
| EIA exports by destination | every release | revisions at least fourteen months back, logged vintage against vintage |
| Japanese spot LNG | between March and April 2021 | METI's survey ends and JOGMEC's continues it; the two are kept as two series |
| JOGMEC arrival-based price | April 2023 | from cargoes contracted and delivered in the month to cargoes delivered in the month whenever contracted |
| ACER DES assessments | January to March 2023 | NWE priced from 19 January 2023, SE from 20 January, the EU from 8 March, the EU benchmark to TTF from 31 March |
| EU allowance price | after June 2025 | the Commission's latest auction report ends there; DEHSt's average of the German auctions stands in, a proxy 0.10 EUR/t above the Commission's on average over the 18 months both cover |

### 5.1 The weekly series checked against itself

Every issue prints the same week a year earlier, so each week can be read
twice: as its own issue printed it and as the issue a year later reprinted it.
Weeks are matched on the calendar, the week ending 364 days earlier
(`lngarb.sources.eia_ngwu.year_earlier_check`). Of the 140 weeks read twice:

* all 26 weeks of 2022 that the 2022 issues priced as a swap and a day-ahead
  price differ, both prices, from what the 2023 issues reprint. EIA reprinted
  them on the futures basis, which is the break in the table above seen from
  the other side;
* the East Asia weeks of the second half of 2022 called "futures" without a
  month agree with the "front-month futures" the 2023 issues reprint, but for
  the week ending 3 August 2022 (44.57 printed, 43.97 a year later); the TTF
  futures weeks of the same half year all agree;
* among the weeks of the futures basis from December 2022, one differs: the
  week ending
  10 July 2024, East Asia 12.49 then 12.40 and TTF 10.51 then 10.12. Its report
  week is a single week, so it is not an average over the skipped holiday week.
  These two are listed, not explained.

Two weeks have no value: the issues of 14 September 2023 and 7 March 2024
repeat the previous week's item word for word (`docs/sources.md` 3.1). The
cross-check lists the figures EIA printed for them a year later, with no
difference, since there is nothing to compare them with. The
weekly figures are never stitched across a break: each carries its definition
and its basis, and a chart that crosses a break marks it.

---

## 6. The Suez route: toll, rebate and availability

What the Suez Canal Authority's own texts and the public record give the canal
line, dated, so that a transit on any day is priced under the instruments then
in force. The traps are in `docs/sources.md`, sections 3.12 and 3.13; what is
still open is in `docs/open-questions.md`, questions 25 to 30.

### 6.1 The toll

```
normal_dues = sum over bands of rate(band, laden or ballast) * SCNT in band   # SDR
surcharge   = s(transit date) * normal_dues                                   # LNG carriers only
rebate      = r(transit date, destination) * normal_dues                      # US Gulf to Asia, conditions apply
toll_sdr    = normal_dues + surcharge - rebate                                # one reading, see open question 26
toll_usd    = toll_sdr * usd_per_sdr(transit date)
```

Each transit is dated from the loading day: the laden transit after the load
day and the sea distance from Sabine Pass to the canal, measured along the
route's line; the ballast transit after the whole laden leg and the distance
back from Futtsu to the canal. At 17 knots a cargo through Suez transits about
17 days after loading, laden, and 57 days after in ballast; through Panama,
about 5 and 44 days after.

Normal dues for LNG carriers ("Rate (5)"), in SDR per ton of Suez Canal Net
Tonnage, laden and ballast, from the schedules the Authority attaches to its
circulars:

| SCNT band | 1 May 2015 to 31 Dec 2022 | 1 Jan 2023 to 14 Jan 2024 | from 15 Jan 2024 |
|---|---|---|---|
| first 5,000 | 7.88 / 6.70 | 9.06 / 7.71 | 10.42 / 8.87 |
| next 5,000 | 6.13 / 5.21 | 7.05 / 5.99 | 8.11 / 6.89 |
| next 10,000 | 5.30 / 4.51 | 6.10 / 5.19 | 7.02 / 5.97 |
| next 20,000 | 4.10 / 3.49 | 4.72 / 4.01 | 5.43 / 4.61 |
| next 30,000 | 3.80 / 3.23 | 4.37 / 3.71 | 5.03 / 4.27 |
| next 50,000 | 3.63 / 3.09 | 4.17 / 3.55 | 4.80 / 4.08 |
| the rest | 3.53 / 3.00 | 4.06 / 3.45 | 4.67 / 3.97 |

The first column is the schedule applicable from 1 May 2015, whose circular
(2/2015) keeps the dues "unchanged the same as in 2014"; the schedules of 1
April 2020 (circular 2/2020) and 1 February 2022 (circular 5/2021, whose 6
percent increase excludes "LNG Carriers") print the same row. The second is
circular 14/2022 of 18 September 2022, which raised normal dues 15 percent from
1 January 2023; the third is circular 7/2023. No circular found changes the LNG
row between those dates. The schedules say the rates "shall be applied
according to the vessel's actual condition upon transit".

The other instruments that move an LNG carrier's toll:

| From | What changes | Instrument |
|---|---|---|
| 1 May 2015 | general reduction for LNG carriers cut from 35 to 25 percent | circular 2/2015 |
| 1 Oct 2017 | rebate for US Gulf cargoes to Asia begins, see 6.2 | circular 7/2017 |
| 1 Apr 2020 | general reduction raised to 30 percent, to 30 June 2020 | periodical of 31 March 2020 |
| 1 Jul 2020 | general reduction back to 25 percent | periodical of 21 June 2020 |
| 1 Nov 2021 | general reduction cut from 25 to 15 percent | periodical of 26 October 2021 |
| 1 Feb 2022 | new schedule | circular 5/2021 |
| 1 Mar 2022 | surcharge of 7 percent on normal dues, laden and ballast | circular 5/2022 |
| 15 Mar 2022 | general reduction cancelled | periodical of 14 March 2022 |
| 1 Jan 2023 | normal dues raised 15 percent | circular 14/2022 of 18 September 2022 |
| 15 Jan 2024 | normal dues raised 15 percent | circular 7/2023 of 16 October 2023 |
| 15 Jul 2026 | surcharge raised from 7 to 19 percent | periodical 20/2026 of 7 June 2026 |

The rebate in 6.2 cannot be combined with any other LNG rebate: circular
7/2017 says the carrier "has no right to benefit from other rebates granted by
SCA to LNG tankers, beside that rebate subject of this circular". The study
takes the larger of the two, which is always the route rebate.

### 6.2 The rebate for a cargo from the US Gulf to Japan

The rate for the band that contains Japan, from the circular and periodicals
the Authority publishes, each read from its own record:

| Transits | Rate | Band named | Instrument |
|---|---|---|---|
| 1 Oct 2017 to 30 Sep 2018 | 50 percent | Singapore and its eastern ports | circular 7/2017, an experimental year |
| 1 Oct 2018 to 30 Sep 2019 | 65 percent | Singapore and its eastern ports | periodical of 25 September 2018 |
| 1 Oct 2019 to 31 Dec 2021 | 75 percent | Singapore ports and its eastern ports | periodicals of 12 September 2019 and 31 March 2020, renewed to 31 December 2021 |
| 1 Jan 2022 to 31 Dec 2022 | 70 percent | Singapore ports and its eastern ports | periodical of 21 December 2021, renewed 12 June 2022 |
| 1 Jan 2023 to 30 Jun 2023 | 70 percent | Port Klang and its eastern ports | periodical of 18 December 2022 |
| 1 Jul 2023 to 31 Dec 2026 | 75 percent | Port Klang and its eastern ports | periodical of 21 June 2023, renewed six monthly to periodical 8/2026 |

From 1 January 2025 the renewals cover only LNG carriers "directly operating"
between the US Gulf and Asia. The texts cover laden and ballast carriers
(open question 27). Nothing published yet covers transits after 31 December
2026. Before 1 October 2017 only the general reduction of 6.1 applies.

### 6.3 When the Red Sea was open to a US cargo

A US Gulf cargo to Japan through Suez must cross Bab el Mandeb. The bands below
are those the public record supports; a period no source covers is a gap, not
an assumption.

| From | To | What the record shows | Source |
|---|---|---|---|
| 2021 | end of 2023 | routine use: 434 laden LNG transits of Suez in 2023, 130 of them US cargoes southbound | Oxford Institute for Energy Studies, NG 188 |
| 1 Jan 2024 | 12 Jan 2024 | most carriers already diverting; eight laden transits, Qatari and Russian, none from the US | The National, 15 January 2024; NG 188 |
| 13 Jan 2024 | 16 Jan 2024 | Qatari laden carriers turn south; the last ballast LNG carrier passes Suez on 16 January | The National, 15 and 16 January 2024; NG 188 |
| 17 Jan 2024 | June 2024 | no LNG carrier crosses the Red Sea; canal transits only for Aqaba and Ain Sukhna | NG 188; IEA, Gas Market Report Q3 2025 |
| June 2024 | September 2024 | crossings by two Russia linked ships, and a few ballast ships bound for Russia | gCaptain, 8 February 2025; IEA, Global Gas Security Review 2024 |
| October 2024 | 7 Feb 2025 | no LNG carrier crosses | gCaptain, 8 February 2025 |
| 8 Feb 2025 | June 2025 | three crossings in the half year; the two named are Salalah LNG, from Oman, and Trader III | IEA, Gas Market Reports Q2 and Q3 2025; Kpler, 8 May 2025 |
| July 2025 | February 2026 | "only a handful" of crossings in 2025; "limited" in the winter | IEA, Gas Market Reports Q1 and Q2 2026 |
| March 2026 | July 2026 | no LNG vessel at Bab el Mandeb, then one in ballast | Discovery Alert, 22 July 2026, citing S&P Global data (secondary) |
| August 2026 | September 2026 | unknown: no source this study uses reports on LNG carriers in the Red Sea | (open question 38) |

No source read shows a US Gulf cargo going to Asia through Suez after 12
January 2024. That is an absence of reports, not a count of zero. When the
route is closed to a US cargo in the model, and on what evidence it reopens, is
open question 28.

---

## 7. Port costs: what the published record gives

The engine needs a port cost at Sabine Pass, at Gate and at a Tokyo Bay
discharge port. No public source prices one port alone for an LNG carrier.
What exists is two all-in figures for a pair of ports, and the published
components of each port's charges.

### 7.1 Spark's two-port figures

Spark's note on negative freight rates, undated on its pages, dates from 11 to
14 February 2022: its worked examples use the assessment of 8 February 2022,
its screenshots show releases of 8 and 11 February 2022, and the copy the
Internet Archive captured on 16 February 2022 carries the same words page for
page as the copy read in 2026. It gives:

| Ports | Ship | Figure | How it is given |
|---|---|---|---|
| Sabine Pass and Gate | 160,000 m3 TFDE | 308,947 $ | in text, "Port costs provided by GAC on an indicative basis" |
| Sabine Pass and Futtsu, via Panama | 160,000 m3 TFDE | 273,184 $ (0.08 $/MMBtu) | in a screenshot of Spark's Routes page, release of 8 February 2022, beside a canal cost of 923,400 $ and a total of 6,378,210 $ |

The second figure is read from an image with no text layer; its four cost
lines add up to the total it shows. Neither figure is split between the two
ports, and neither says what it includes. Spark's methodology 3.2 (November
2022) names the source of its port costs: "based on latest costs provided by
GAC (as seen on the Spark platform)". Taken at face value the two figures put
Sabine Pass and Futtsu 35,763 $ below Sabine Pass and Gate. The engine uses
both as they stand, one per destination, for every route, every year and both
ships, each an assumption in the parameter table (open questions 31 and 32).

### 7.2 The components, port by port

These are tariffs, read from the publishers' own documents. They are recorded
so that the order of magnitude of each part is known; none of them is an
all-in port cost.

| Port | Charge | Rate | Basis | Document |
|---|---|---|---|---|
| Any Japanese open port | tonnage tax | 16 yen per entry, or 48 yen a year | per ton of net tonnage | Tonnage Tax Act, article 3 |
| Any Japanese open port | special tonnage tax | 20 yen per entry, or 60 yen a year | per ton of net tonnage | Special Tonnage Tax Act, article 3 |
| Kisarazu port, which contains JERA's Futtsu power station | entry dues, foreign-going ships | 2.50 yen | per gross ton | Chiba prefecture's port charges schedule |
| Tokyo Bay | pilotage, ships of 10,000 GT and over, bay entrance to the Kisarazu port limit | cap of 65,953 yen plus 1,122 yen a step | steps of gross tonnage and draft | Minister's approved caps, as of 1 January 2024 |
| Rotterdam | seaport dues, LNG tankers, 2024 | 0.346 euro per GT plus 0.564 euro per tonne of LNG | cargo part capped at GT times 133.7 percent times 0.564 | Port of Rotterdam general terms and port tariffs 2024 |
| Rotterdam | seaport dues, LNG tankers, 2025 | 0.309 euro per GT, 0.597 euro per tonne, 0.065 euro per GT sustainability component | no LNG tanker row in the efficiency discount table, so no stated cap on the cargo part | the same, 2025 |
| Rotterdam | seaport dues, LNG tankers, 2026 | 0.320 euro per GT, 0.618 euro per tonne, 0.067 euro per GT sustainability component | as in 2025 | the same, 2026 |
| Rotterdam | towage | listed rates plus 150 percent for LNG carriers | per tug, by length | Port of Rotterdam, tariffs of third parties 2026 |
| Sabine Pass | pilotage, Sabine Neches waterway, Zone 1 (this study's reading: the tariff does not name the terminal; Zone 1 runs from the Sabine Bar pilot station to below Beacon No. 40, Port Arthur Canal) | 41.41 $ per draft foot plus 0.0339 $ per gross ton unit | the unit is length times breadth times depth times a coefficient, over 100, not the registered tonnage | Sabine Pilots, rates effective 1 January 2023 |
| Sabine Pass | Sabine Neches Navigation District user fee | 0.20 $ per short ton of hydrocarbon cargo from 1 May 2021, adjustable to 0.35 | per short ton of cargo | the District's fact sheet |

Gate charges no fee per ship call that could be found: its berthing rights are
part of the capacity its customers buy ("throughput capacity (including
berthing rights, storage and regasification)"), so this study counts them in
the Northwest Europe discount, not in the ship's port costs. Gate's page says
nothing about charges to ships.

The District's user fee is a charge on the cargo at the load port. A court
record of 2023 lists what it cost one LNG offtaker's loadings from May to
August 2021: 15,462.21 $ to 16,357.03 $ a voyage. The cost line in the engine
has no place for it yet (open question 33).

What a Futtsu figure assembled from these would still lack: the net tonnage of
a named ship under the Japanese measurement law, its arrival draft, the number
of tugs and hours, line handling, agency and berth charges at JERA's jetty,
whether an LNG carrier counts as an LNG fuelled ship for Chiba's exemption from
entry dues (open question 34), and a dated yen to dollar rate.

---

## 8. The Panama route: toll, other charges and availability

What the Panama Canal Authority's own tariff documents and advisories give the
canal line for an LNG carrier, period by period. The traps are in
`docs/sources.md`, section 3.16; what is open is in `docs/open-questions.md`,
questions 39 to 42.

### 8.1 The toll

Rates in US dollars per cubic metre of cargo capacity "as determined by the
admeasurement performed by the Panama Canal". Until 2022 the rate falls by
band: the first 60,000 m3, the next 30,000, the next 30,000, and the rest.
From 2023 a fixed charge per transit is added and one rate applies to the whole
capacity, by size category; LNG carriers of the study's sizes are neopanamax
vessels.

| From | To | Laden, per m3 | Ballast | Documents |
|---|---|---|---|---|
| 1 Apr 2016 | 30 Sep 2017 | 2.50, 2.15, 2.07, 1.96 by band | its own bands: 2.23, 1.88, 1.80, 1.71 | 2016 approved tolls tables, from the Internet Archive's copies; the Authority's history of tolls |
| 1 Oct 2017 | 31 Mar 2020 | 2.88, 2.47, 2.38, 2.25 | 2.56, 2.16, 2.07, 1.97 | tolls approved 1 August 2017 |
| 1 Apr 2020 | 31 Dec 2022 | 3.12, 2.68, 2.58, 2.44 | 2.79, 2.35, 2.26, 2.15 | the Authority's history of tolls, September 2020 and May 2023 |
| 1 Jan 2023 | 31 Dec 2023 | 300,000 per transit plus 1.35 per m3 | 85 percent of laden | items 1010.FN02, 1010.NN01, 1010.BA01; tolls approved 12 July 2022 |
| 1 Jan 2024 | 31 Dec 2024 | 300,000 plus 1.70 | 85 percent | the same items, 2024 tariff |
| 1 Jan 2025 | to date | 300,000 plus 2.05 | 85 percent | the same items, 2025 tariff; still listed in February 2026 |

From 2016 to 2022 a third, lower table applied to a ship returning through the
canal in ballast within 60 days ("roundtrip ballast"): 2.00, 1.75, 1.60, 1.50
from 2016, 2.30, 2.01, 1.84, 1.73 from October 2017, 2.48, 2.17, 1.99, 1.87
from April 2020. From 2023 the ballast toll is 85 percent of the laden toll, on
the fixed and capacity components, for an LNG carrier carrying at most 10
percent of its cargo capacity.

What these give, this study's arithmetic on the rates above, in US dollars per
transit:

| From | 174,000 m3 laden | 174,000 m3 ballast | 160,000 m3 laden | 160,000 m3 ballast |
|---|---|---|---|---|
| 1 Apr 2016 | 382,440 | 336,540 | 355,000 | 312,600 |
| 1 Oct 2017 | 439,800 | 386,880 | 408,300 | 359,300 |
| 1 Apr 2020 | 476,760 | 421,800 | 442,600 | 391,700 |
| 1 Jan 2023 | 534,900 | 454,665 | 516,000 | 438,600 |
| 1 Jan 2024 | 595,800 | 506,430 | 572,000 | 486,200 |
| 1 Jan 2025 | 656,700 | 558,195 | 628,000 | 533,800 |

The 2016 bands reproduce, to the cent, the worked example the Authority
published with them (382,440 $ laden and 336,540 $ in ballast for 174,000 m3).
No advisory read to 5 October 2026 announces a toll change after 2025.

### 8.2 The other Panama charges

* **Fresh water surcharge**, mandatory on every transit since 15 February
  2020: 10,000 $ per transit for a ship over 300 feet, plus a percentage of the
  tolls set daily from the level of Gatun Lake. From 15 February 2020 the
  percentage is 0.10 / (1 + e^(0.6 (x - 82))), x the lake level in feet, with a
  floor of 1 percent; from 1 January 2023 it ranges from 0 to 10 percent; from
  1 October 2023 the curve is centred on 79 feet and applies to the total
  tolls. At the 2025 toll it adds 10,000 $ to 75,670 $ to a laden transit of a
  174,000 m3 carrier (this study's arithmetic). The lake levels of past days
  were not collected.
* **Booking fees for a neopanamax vessel**, paid only by a ship that books a
  slot: 35,000 $ when neopanamax bookings opened in 2016; 70,000 $ or 85,000 $
  by beam (under or over 42.67 m) for booking dates from 1 June 2021; 80,000 $
  in the list of January 2024; 100,000 $ from 1 January 2025 (item 1050.IBN1).
  The amount in force in 2023 was not found.
* **Slot auctions and long-term allocations** are paid at the winning bid,
  above a base of 93,500 $ in 2021 and 100,000 $ from 2024, and 200,000 $ per
  slot for long-term allocations from 2025. The Authority publishes no auction
  results.
* **Waiting days** are not published by segment. The IEA gives two to three
  days for LNG carriers in normal conditions and an average of 15 days for
  unreserved slots in mid December 2023; Spark reported 12 days for unbooked
  vessels in late July 2023 (LNG Prime, 28 July 2023).

Two published estimates set against the tariff of their date, this study's
arithmetic: the IEA's 0.6 to 0.7 million $ for a 170,000 m3 carrier "for
bookings made in advance" (Gas Market Report Q1 2024) is consistent with the
laden toll plus a booking fee of 80,000 $, the fee of the January 2024 list;
Spark's canal cost of 923,400 $ for Sabine Pass to Futtsu via Panama on 8
February 2022 is 89,100 $ above that date's laden and ballast tolls for a
160,000 m3 carrier, a gap of the size of the fresh water surcharge or a booking
fee, which Spark's figure does not break down.

### 8.3 When Panama was available to an LNG carrier

No band below closes the canal to LNG carriers; they describe how hard a slot
was to get.

| From | To | What the record shows | Source |
|---|---|---|---|
| 26 Jun 2016 | 30 Sep 2018 | the expanded locks open (first LNG carrier 25 July 2016, from Sabine Pass); daylight and encounter restrictions on LNG carriers | the Authority's press releases of 2016 and 2018 |
| 1 Oct 2018 | 2 Jan 2023 | restrictions lifted; up to two booked LNG slots a day; auctions from January 2021; 58 LNG transits in January 2021, a record | advisory A-29-2018; press release of 3 February 2021 |
| 3 Jan 2023 | 29 Jul 2023 | water saving measures; neopanamax draught cut in steps to 44 feet by 19 June 2023; 12 days of delay for unbooked vessels in late July | advisories of 2023; LNG Prime, 28 July 2023 |
| 30 Jul 2023 | 31 Oct 2023 | daily transits cut to an average of 32, 10 of them neopanamax; queues of up to 163 ships and 21 days in August, all ship types | advisory A-35-2023; IEA, Global Gas Security Review 2024 |
| 1 Nov 2023 | 15 Jan 2024 | 31 transits, 9 neopanamax, then 8, 7 and 6 neopanamax booking slots in December; unreserved LNG waits of 15 days in mid December | advisories A-48-2023 and A-53-2023; IEA, Gas Market Report Q1 2024 |
| 16 Jan 2024 | 31 May 2024 | 24 booking slots, 7 neopanamax, full container ships ahead of LNG in the first booking period; LNG transits "almost completely dried up" by early 2024 | advisories A-54-2023 and A-08-2024; IEA |
| 1 Jun 2024 | 14 Aug 2024 | neopanamax booking slots back to 8, 9, then 10 | advisories of 2024 |
| 15 Aug 2024 | 31 Aug 2024 | the Authority states its commitment to return to normal operating conditions (50 feet; 36 booking slots, 10 neopanamax, from 1 September 2024) | advisory A-28-2024 |
| 1 Sep 2024 | about November 2025 | normal operating conditions; LNG use stays low | advisory A-28-2024; IEA, Gas Market Reports 2025 and Q1 2026 |
| December 2025 | 2 Jul 2026 | water conservation measures in place, which the Authority says leave the daily transits as they were; their advisories of December 2025 to May 2026 were not read; an LNG first rule for one booking slot from 4 January 2026 | the Authority's press release of 5 August 2026; advisory A-28-2025 |
| 3 Jul 2026 | 3 Sep 2026 | neopanamax draught cut in steps, to 49.5 feet on 3 July and 48 feet by 2 September 2026; booking slots unchanged | advisories A-18, A-22, A-25, A-29 and A-33-2026 |
| 4 Sep 2026 | to date | El Nino measures: 9 neopanamax slots a day; 10 slots and at least four LNG slots a week announced from 15 October 2026 | advisories A-29-2026 and A-36-2026 |

---

## 9. The engine

`src/lngarb/engine.py` holds the formulas, `src/lngarb/cases.py` applies them
to every route of one loading date, and `src/lngarb/worked.py` reads the inputs
of a date from the committed data and the parameter table. Every parameter that
is not market data is a named entry in `lngarb.config.PARAMETERS`, with its
value, unit, status, source and the date it was read (section 11).

### 9.1 Volumes and days

A cargo of capacity V m3, loaded to the share `fill` and converted at K MMBtu
per m3, loads `Q_load = V x fill x K`. The ship boils off or burns
`b = Q_load x BOR` MMBtu a day, on laden and ballast days alike, the basis
Spark states for its boil-off rate. Each leg takes its sea distance over 24
times the speed, plus canal and waiting days; the laden leg adds a day to load,
a day to discharge and any flex days, which are zero except to reproduce Spark
and count, for the EU ETS, as days of the laden voyage. Days at sea can be
typed for either leg instead of computed from the distance.
The gas used over the round trip is `G = b x T_total`, and the cargo delivered
is `Q_del = Q_load - G`: the heel for the ballast leg stays on board. Laden and
ballast routes are set separately; a worked date sends both legs the same way.
The pilot fuel a dual fuel engine burns with the gas is left out, of the
voyage's cost and of its emissions: a limitation the Method view lists.

The ship is the benchmark freight rates' own: the 160,000 m3 TFDE, at 0.1
percent a day, before 2 January 2024, and the 174,000 m3 two-stroke, at 0.085
percent a day, from that date, when Spark's methodology changed its vessel.

### 9.2 The cost stack

For a destination d and a route r, in US dollars:

    C(d, r) = hire x T_total + port(d) + canal(r, laden) + canal(r, ballast)
              + slot premium(r) + ets(d, r) + financing(r)

* **Hire** runs for the whole round trip, until the ship is back at the load
  port. Spark defines its rate as the charterer's payment less the ballast fuel,
  over the round trip's days, so a Spark rate used as round trip hire, with the
  ballast heel inside G, counts nothing twice.
* **Port costs** are one figure per destination, each a pair of ports: Spark's
  308,947 $ for Sabine Pass and Gate and 273,184 $ for Sabine Pass and Futtsu,
  held for every year and both ships (section 7.1).
* **Canals.** Each transit is priced on its own day (section 6.1). Panama from
  the dated tolls of section 8.1, with the roundtrip ballast table before 2023
  when both legs pass the canal, and the fresh water surcharge from 15
  February 2020: 10,000 $ a transit and 5 percent of tolls. Suez from section
  6. A canal route is offered only if its laden transit falls while the canal
  is open to a US cargo, and the ballast leg is taken to return the same way.
  Suez is offered only where its toll can be priced; without the SDR rate it
  is shown and not offered, never priced at zero. Slot premiums and waiting
  days are zero by default.
* **EU ETS**, on the voyage to Northwest Europe only:
  `eua_usd x phase(year) x tCO2e per t(year) x (b x days / MMBtu per t)`, where
  the laden voyage and the ballast leg count at the voyage share and the
  discharge day at Gate at the berth share. The load day at Sabine Pass is
  outside the scheme. Each day's emissions take the phase and the gases of
  their own calendar year, since a year's surrender covers that year's
  emissions: a cargo loaded in late December reaches Gate in the next year. The
  phase is zero before 2024; methane and nitrous oxide count from 2026. The EU
  allowance price is that of the loading month. Before 2024 no price is read:
  the price is left empty, never zero, and the cost is zero because nothing is
  surrendered. A surrender at a price not read leaves the cost unknown.
* **Financing**: the part of the cargo's purchase cost paid only when it is
  lifted, `1.15 x HH x Q_load`, at the overnight rate plus a spread, for the
  laden days, on an actual over 365 basis. The fixed fee, and its carrying
  cost, are owed whether or not the cargo is lifted, so they are left out, as
  the lift test requires. The overnight rate is SOFR from 2 April 2018 and the
  effective federal funds rate before it.

`C0` is the same stack without hire.

### 9.3 Netbacks and the arb

    P_des(NWE) = TTF + delta_nwe        delta_nwe, the DES discount, usually negative
    P_des(NEA) = JKM                    JKM is already a DES price
    NB(d, r)   = (P_des(d) x Q_del(r) - C(d, r)) / Q_load
    arb(r)     = NB(NEA, r) - NB(NWE, direct)

The gas used on the way is simply not sold, so it is valued at the delivered
price without a separate fuel line. A route that is closed on the date is
computed and shown, and never chosen.

### 9.4 The breakeven spread

The JKM - TTF spread at which a cargo pays the same east and west:

    S*(r)    = (TTF + delta_nwe) x Q_del(NWE) / Q_del(r) + (C(NEA, r) - C(NWE)) / Q_del(r) - TTF
    boil-off = TTF x (Q_del(NWE) / Q_del(r) - 1)
    regas    = delta_nwe x Q_del(NWE) / Q_del(r)
    voyage   = (C(NEA, r) - C(NWE)) / Q_del(r)

The three parts add up to S*. The arb and the breakeven are tied exactly:
`arb(r) = (JKM - TTF - S*(r)) x Q_del(r) / Q_load`.

### 9.5 The breakeven hire

    H*(r) = [JKM x Q_del(r) - (TTF + delta_nwe) x Q_del(NWE) - (C0(NEA, r) - C0(NWE))]
            / (T_total(r) - T_total(NWE))

the hire at which east and west net back the same. A negative H* means the
route east does not pay even with a free ship. "Was the arb open?" becomes "was
the reported hire below H*?", which a reader can check against each reported
figure.

### 9.6 The lift test

    best_netback = max over destinations and open routes of NB(d, r)
    lift_margin  = best_netback - 1.15 x HH(loading month)
    full_margin  = lift_margin - liquefaction fee       shown, never used to decide
    cancel       = lift_margin < 0

The fee is owed whether or not the cargo is lifted, so it never decides. HH is
EIA's daily Henry Hub spot averaged over the loading month, standing in for the
NYMEX final settlement the contracts name, which EIA stopped publishing after 5
April 2024.

### 9.7 Exact and conventional freight

The market quotes freight per delivered MMBtu with the fuel valued at a
reference price: `F_conv = (C + P_ref x G) / Q_del` and
`NB_conv = P_des - F_conv`. With `P_ref = P_des`, as Platts does, the two
netbacks differ by exactly `G x (P_des x G + C) / (Q_load x Q_del)`, a second
order term that grows with the voyage and the price. The study uses the exact
form everywhere and shows both for the latest date.

### 9.8 The inputs of a date

`lngarb.worked` reads, for a loading date: JKM and TTF from the Weekly Update or
the Supplement for the week ending that day, or, before the weekly prices
begin, METI's contract-based monthly price as a labelled proxy for JKM and the
World Bank's TTF; Henry Hub as the loading month's average of EIA's daily spot;
the euro rate of H.10 on or before the day; SOFR, or the effective federal funds
rate before 2 April 2018; the Northwest Europe DES discount as ACER's NWE
spread to the TTF front month (the EU benchmark plus the NWE assessment less
the EU one, computed from ACER's figures), averaged over the days the price
spans, the week to the day for a weekly price and the calendar month for a
monthly one, where ACER published it on at least half of the span's weekdays,
and otherwise (before 31 March 2023, in March 2023, after the last download
held) the labelled assumption of section 11; the EU allowance price of the month from the
Commission's auction reports, after June 2025 the average of the German
auctions DEHSt reports, a labelled proxy, and after August 2026 that month
held, the labelled assumption of section 11; the reported charter rate nearest
the date, within 14 days, from the freight anchors, dated by the day it refers
to or else by its article, or, where none is that close, the low, central and
high hire they give; the benchmark ship of the day; and the routes offered for
the laden transits that loading implies (Panama from 26 June 2016, Suez to a
laden transit on 12 January 2024). The Henry Hub average of a month the data
do not yet finish says so. An input the data do not hold is reported missing,
never filled. `scripts/worked_table.py` prints every input with its source,
every line of the result and the sensitivities of section 11 for the worked
dates.

### 9.9 Delivery months

`lngarb.delivery` gives the delivery month each front-month price names on a
day. JKM futures for month M stop trading on the 15th of M-1, or the business
day before, and settle on Platts' JKM from the 16th of M-2 to the 15th of M-1
(ICE Futures Europe and the Japan Exchange Group; "The Platts JKM rolls on the
16th of each calendar month", Platts' press release of 16 June 2015). Dutch TTF
futures stop trading "two UK Business Days prior to the first calendar day of
the delivery month" (ICE Endex). Business days are UK business days: weekdays
that are not bank holidays in England and Wales (`lngarb.calendars`), whose
rule reproduces every day gov.uk lists for 2019 to 2028 and, with the TTF rule,
every one of the 134 last trading days ICE Endex lists for November 2026 to
December 2037. The two front months name the same month from the 1st to the
15th and after the TTF expiry at the end of the month, and different months
from the 16th to the expiry. A week is aligned when every trading day of it
names the same month, misaligned when none does, and mixed otherwise.

### 9.10 The calculator

The Model view runs the same engine in the browser (`src/engine.js`, held to
the Python to 1e-9 by `tools/validate-engine.mjs` on 240 random cases, 14
edge cases, the six presets and the named edits) over a preset's inputs with
the visitor's figures laid over them.

* **Presets.** Each is a loading date worked as section 9.8 works it: the
  latest week, April 2020, 12 October 2022, 27 March 2024, 25 March 2026 and
  Spark's worked example, assessed on 8 February 2022, loading on 9 February.
* **Missing is shown as missing.** An input the data do not hold for a
  preset's date is left empty, with the reason under its field and in the
  preset's lead, and every output that needs it has no figure until one is
  typed; nothing is filled in its place. The parameters of section 11 are not
  data and are not missing: Europe's DES spread where ACER published too
  little, and the allowance price after the last auction published, are the
  labelled assumptions of that section, as the analysis takes them, and the
  page says so under their fields. April 2020 has no charter rate
  reported within 14 days, so its hire is empty, and the page offers the low,
  central and high levels of the reported rates, the three the analysis runs,
  for the visitor to choose. A date whose inputs cannot be read at all is not
  offered, and the page says why.
* **Assumptions are named.** The liquefaction fee, the port costs, the
  funding spread and the canal tolls' reading of the tariffs (an unbooked
  ship at its nominal capacity, Panama's fresh water surcharge at 5 percent
  of tolls, Suez's net tonnage from capacity) are always this study's
  assumptions (section 11), and the fields, the route table and the preset's
  lead say so; so do they for Europe's DES spread where
  ACER published too little, and for an allowance price held. Every one can be
  typed over, as can the ship's speed, boil-off, fill and days in port, the
  contract's share of Henry Hub, the two energy conversions and the EU ETS
  shares of a voyage and a berth stay, each with its source. Methane slip is a
  box to tick, off as in the study, with each ship's default share from the
  EU's monitoring rules, which can be typed over. The canal tariffs
  behind the tolls (Suez's net tonnage per cubic metre, Panama's fresh water
  surcharge and its reading of capacity) and the factors of the gases counted
  under the EU ETS (tonnes of CO2 and N2O per tonne of LNG, their warming
  potentials, the year methane enters) are fixed there: they are rules or
  readings of a rule, not inputs a cargo chooses, and the tolls and carbon
  cost they give can be typed over, per route or through the shares.
* **Spark's example** types Spark's 17.5 laden and 12.5 ballast days, read
  through Spark30's composition of 30 days (25 sailing, 1 load, 1 discharge, 3
  flex): 12.5 laden days at sea, the day to load and the day to discharge, and
  3 flex days; 12.5 ballast days at sea. The split is this study's reading.
* **Tolls follow the ship.** Panama and Suez price on capacity, so the
  preset carries both ships' tolls for its date; choosing the other ship
  takes its tolls, unless a toll is typed.
* **A ballast leg back by another route** takes that route's distance, canal
  days and waiting days as they stand, and the toll of a ballast transit
  alone: at Panama before 2023 the ballast table, not the lower roundtrip
  table, which applies only to a ship that passed the canal laden too, priced
  on the day of that route's own ballast transit; at Suez its ballast toll. A
  typed ballast toll wins. Back by a route closed to a US cargo, the route is
  closed too.
* **Limits, not clamps.** Dollars per euro from 0.5 to 2, which brackets
  every H.10 rate since 1999; speed from 5 to 25 knots; boil-off from 0 to 1
  percent a day; fill from 50 to 100 percent; days to load or discharge up to
  10; days at sea up to 120 a leg; flex and canal days up to 30; waiting days
  up to 60; every EU ETS share from 0 to 1; from 15 to 30 MMBtu per m3 and 40
  to 60 per tonne; the contract's share of Henry Hub up to 200 percent; an
  allowance from 0 to 1,000 euros a tonne. A
  figure outside them, or too large to be finite, is refused with its limits
  and treated as missing; nothing is clamped. Inputs under which the ship burns as much gas
  as it loads give no netback, and the page says so.
* **Missing is missing.** An empty or unreadable field leaves every output
  that depends on it without a figure, and the page names the input, route
  cells included. An empty days at sea field takes the days from the distance.

---

## 10. The tests that pin the engine

| # | Test | Where |
|---|---|---|
| 1 | Units: 30 EUR/MWh at 1.10 $/EUR is 9.671344 $/MMBtu | `tests/test_units.py` |
| 2 | Volumes: 174,000 m3 at 98.5 percent loads 3,941,970 MMBtu and boils off 3,350.6745 a day | `tests/test_engine.py` |
| 3 | Spark's worked example, every line within a dollar, both rates and the unit freight | `tests/test_engine.py` |
| 4 | Null: no costs, netbacks are the prices and S* is zero | `tests/test_engine.py`, `tests/test_cases.py` |
| 5 | Symmetry: equal voyages break even at the regas discount | `tests/test_engine.py` |
| 6 | Linearity in hire | `tests/test_engine.py` |
| 7 | Round trip: JKM = TTF + S*, and hire = H*, close the arb | `tests/test_engine.py`, `tests/test_cases.py` |
| 8 | The three parts add up to S* | `tests/test_engine.py`, `tests/test_cases.py` |
| 9 | Exact against conventional netback | `tests/test_engine.py` |
| 10 | Monotonicity of S* | `tests/test_engine.py` |
| 11 | Panama tolls: 656,700 $ laden and 558,195 $ in ballast for 174,000 m3 from 1 January 2025 | `tests/test_canals.py` |
| 12 | EU ETS: phase by year, Asian voyages free, berth in full | `tests/test_worked.py`, `tests/test_cases.py` |
| 13 | Delivery months: 18 September 2026 gives November against October | `tests/test_delivery.py` |
| 14 | Distances against searoute and published durations | `tests/test_sea_routes.py` |
| 15 | Anchors of every parser | `tests/test_sources_*.py` |
| 16 | Every exported destination has a region | `tests/test_sources_eia.py`, `tests/test_sources_doe.py` |

---

## 11. Parameters

Every number the engine uses that is neither market data nor a canal tariff
(the tariffs are in sections 6 and 8) is a named entry in
`lngarb.config.PARAMETERS`, with its value, unit, status (published: read in
the named document; derived: computed from published figures; assumption:
chosen by this study and labelled), the document, its address and the date it
was read. The site's Method view prints that table. The assumptions, and the
published values used as scenarios, each with the alternatives the study
names for it. `scripts/worked_table.py` runs those of the liquefaction fee,
the regas discount, the Suez tonnage and rebate, and the hire on the worked
dates; the others are named, not run:

| Parameter | Value | Alternatives | Why |
|---|---|---|---|
| liquefaction fee | 3.00 $/MMBtu | 2.25 and 3.50, both published | the fee most Sabine Pass contracts carry |
| regas discount in Northwest Europe, before 31 March 2023 | -2 EUR/MWh | -3, 0, and -35 for a loading from 25 July to 15 October 2022 | ACER's printed average and range (open question 18); ACER's own NWE spread averages -2.33 from April to August 2023 |
| port costs | Spark's two pairs | none | the only source pricing both destinations on one basis; held for every year and both ships |
| Suez net tonnage | 85,000 SCNT per 145,000 m3, scaled to the capacity | 85,000 and 112,148 | a canal agency's approximation; the Authority's net tonnage per LNG transit in 2023 (open question 25) |
| Suez rebate on the surcharge | not applied | applied | the rebate is written on normal tolls (open question 26) |
| Panama capacity charged | the nominal capacity | none | the canal's admeasurement rules were not read (open question 39) |
| Panama booking fee | none, an unbooked ship | none | the booked case is a scenario (open question 40) |
| hire where no rate was reported within 14 days | 45,500 $/day | -750 and 374,000 | the median, lowest and highest of the freight anchors |
| EU allowance price after the last published month | the last month published, held (on 8 October 2026 August 2026, 82.31 EUR/t, German auctions) | 61 and 86 | the last published month held, and the Commission's range for 2025 |
| funding spread | 150 bp | none | the convention of the study's copper sibling |
| Panama variable fresh water surcharge | 5 percent of tolls | 0 and 10 | the middle of the Authority's range |
| Suez closed to a US cargo | from 13 January 2024 | none | the day after the last laden LNG transit |
| methane slip | off | 1.7 percent (174,000 m3), 3.1 percent (160,000 m3) | the regulation's defaults for the likely engine classes |
| monthly loading day | the 15th | none | a monthly observation loads in the middle of its month |
| weeks a monthly mean needs | 3 | none | fewer leave the month without an observation |
| first month of the monthly history | January 2016 | none | the first overnight rate held; Sabine Pass's first cargo followed in February 2016 |
| years the flows test is also run without | 2020, 2022, 2026 | none | the cancellations, the European gas crisis, the Strait of Hormuz |
| Panama waiting days reported, published | 12 per transit in July 2023, 15 in December 2023 | in those months only, against no wait | Spark in late July 2023, the IEA in mid December 2023 |

---

## 12. The analysis

`lngarb.analysis` works every price observation the study holds through the
engine as a cargo loading on its day; `scripts/analysis_report.py` prints the
result. Nothing is fitted: no parameter is searched and nothing is forecast.

### 12.1 The observations

* **Weekly**: the Weekly Update's East Asia and TTF averages from the week
  ending 15 September 2021, then the Supplement's JKM and TTF from the week
  ending 28 January 2026, each loading on the week's last day, the Wednesday,
  and tagged aligned, mixed or misaligned by its delivery months (9.9).
* **Monthly**, loading on the 15th: METI's contract-based price, a proxy for
  JKM, with the World Bank's TTF, January 2016 to March 2021; then the mean of
  each month's weekly averages, for a month holding three weeks or more. April
  to August 2021 have no public JKM: METI's survey ended and JOGMEC's
  continuation stays private (open question 14). The monthly JKM is therefore
  a Japanese spot price to March 2021 and a JKM-type price after it, a
  definition break the history marks. On 8 October 2026 the other months with
  no monthly observation are March, June and August 2016, June 2017 and
  November 2019, when METI published no contract-based price, and November
  2021, which holds two weekly averages (`analysis.months_without_observation`).
* **Hire**: each observation at the low, central and high hire of the freight
  anchors (the lowest, median and highest reported figure), and at the figure
  reported nearest its date where one lies within 14 days.
* **Breaks**: every week whose stored basis changes, the change of series, the
  ship of 2 January 2024, the routes (Panama from 26 June 2016, Suez closed to
  a US cargo from 13 January 2024), the EU ETS phase-in and the allowance price
  sources (`analysis.breaks`). The regas discount becomes observed from 31
  March 2023 (ACER), an input change rather than a break in a price series. A
  change where the product is named on one side
  only is kept as a naming change, not a definition break: the Weekly Update's
  TTF before 29 September 2021 and the Supplement's week of near-month futures
  (section 5).

Every other input of a date is what 9.8 describes; a date the data cannot
price is listed with the input it lacks, never filled.

### 12.2 Did the cargoes follow

The share of US LNG exports by vessel going to the JKM markets (Japan, South
Korea, China, Taiwan) and to Asia as a whole, month by month, from EIA's
exports by destination: the block of exports by vessel, its own total row and
its countries summed by region (trucks to Canada and Mexico and re-exports of
foreign LNG are left out). The signal is the arb at loading at the best open
route east, at each hire level. The test is a least squares regression of the
share on the arb, with Newey-West standard errors (Bartlett kernel, L =
floor(4 (n/100)^(2/9)) lags, no small sample correction; a pair of residuals
enters the lag l term only when its months are l apart, so a gap in the sample
is never taken for adjacency), and a table of months by the sign of the arb
against the share above or below its median. Both are run on every month that
has an observation and an export figure, and again without 2020, 2022 and 2026.

What the test cannot separate: long-term contracts with Asian buyers, whose
cargoes move whatever the spot economics; Panama's slot constraints; China's
tariff on US LNG from February 2025; the gap between spot hire and the cost of
a ship already on term charter; and the month, which is coarser than the
decisions. A month's cargo is also decided weeks before it loads, on the
prices of then.

### 12.3 2020

Each loading month of 2020 is worked twice: with its own monthly prices, and
with those published by the cancellation notice date, the 20th of the month
two months before (Sabine Pass's agreement with Centrica, section 5.7). By
then METI and the World Bank had published month M-3 (METI released a month
around the 12th of the next, the World Bank early in it), so the notice date
test takes METI's contract-based price and the World Bank's TTF of M-3, and
Henry Hub's spot averaged over M-2 to the notice day in place of the futures
for the loading month, which this study does not hold. On the notice date JKM
futures name the loading month itself, since they stop trading in M-1; METI's
price, a monthly average of Japanese spot contracts, stands in for them and
lags a falling market. METI's figure is the one its latest release before the
notice day printed, usually the preliminary figure for M-3, from the releases
saved by hand (`meti_spot_lng_releases`); it can differ from the figure METI
finalised later (for July 2020, 5.2 against 4.2). Where that release printed
no figure for its survey month, the latest month it did print is taken (for
February 2020, October 2019), with the World Bank's TTF of the same month. A
loading month whose notice day has no price published in the data held is
listed with the reason. The margins are set beside the cancellations EIA
reported for June to September 2020 and the monthly exports by vessel
(2.24 of `docs/sources.md`).

### 12.4 The route

The best open route east each month, and two breakevens against the Cape:
the slot premium for the round trip at which Panama nets what the Cape does,
Panama's lead times the cargo loaded, and the waiting days per Panama transit,
laden and ballast alike, at which they net the same, found by bisection on the
engine. The waits reported in 2023 are applied only in the months they were
reported: 12 days per transit in July 2023 and 15 in December 2023. The
result is set beside the route use Platts reported: a record 27 US cargoes to
Asia via the Cape in March 2024, against one via Panama in that month to 27
March, and 31 of 34 round the Cape in data running to 28 April 2026, over a
period not stated, when auctioned slots had made Panama impractical for spot
cargoes according to Platts' sources (2.24 of `docs/sources.md`).

### 12.5 The history on the site

The History view draws section 12.1's observations as they are worked, with
nothing smoothed or fitted (`lngarb.spreadhistory`):

* **The spread against the cheapest route.** For each week, and for each month
  from January 2016, JKM's premium over TTF, over the breakeven spread S* of
  the cheapest open route east at the low and the high hire, a shaded band,
  and at the central hire, a dashed line. A week whose spread lies above that
  line is a week the arb east was open: a cargo netted more at Futtsu than at
  Gate. The cheapest route is the open route with the lowest S* at each level
  of hire; on 9 October 2026 it was Panama in every week since September
  2021.
* **The breakeven hire against the charter rates reported.** H*, the hire at
  which the cheapest route nets what Gate does, each week, with every reported
  rate as a point. A rate below the line is a week the arb was open at the
  market's own freight. H* runs from minus millions of dollars a day in 2022,
  when TTF stood far above JKM, to about a million, so the scale is drawn over
  the middle nine tenths of a range's values and every rate reported; each
  week beyond it is a short tick at the edge, counted under the chart.
* **Marks.** Rings mark the weeks in which, by the futures calendars of 9.9,
  the JKM and TTF front months name different delivery months every day, and
  solid dots the mixed weeks, in which they differ on some days; before the
  futures of July 2022 the TTF price drawn was a spot or day-ahead price,
  which names no delivery month, so there a mark shows the calendar, not the
  prices. Numbered rules mark the breaks of 12.1 that change a
  price's definition, a route, the ship or the EU ETS, listed with their
  sources under the charts; a change of name alone is not drawn. Lettered
  marks at the foot of the spread charts are the dated events of
  `lngarb.events`, each from one document, listed with what was left out.
* **Ranges.** Every week, 2021 to 2023, 2024 on, and the last 52 weeks; each
  range's counts and sentences are computed for it.
