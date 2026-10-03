# Methodology

How this study turns published figures into the numbers it shows. This document
grows with the study; this version covers the data layer. The engine, the
analysis and the site are added as they are built.

---

## 1. Rules the data layer keeps

1. **Nothing is invented.** A source that fails, or a date a source did not
   publish, is missing. In a CSV cache a missing value is an empty cell; in a
   JSON file it is `null`; on the site it is "n/a" with the reason one click
   away. Zero never means missing.
2. **Nothing is filled.** No interpolation, no carrying a value forward, no
   substitution from a neighbouring source without a label saying so.
3. **A failed fetch keeps the previous cache.** The source is marked `failed`
   in `data/manifest.json` with the error, and the refresh exits non zero.
4. **Every cache is validated before it is written**: dates in order and
   unique, the declared bounds, a row count that did not shrink, and a minimum
   number of real observations in every value column.
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
Table) is 1,055.05585262 joules (NIST Special Publication 811, appendix B.9), so
one MWh is 3.41214163 MMBtu. The study rounds this to 3.412142; the rounding
moves a price by about one part in ten million. The exchange rate is quoted as
US dollars per euro, the direction the Federal Reserve Board's H.10 release
quotes it, and the argument is named for its direction.

---

## 3. Validation bounds

Each value column is checked against a range before a cache is written. The
ranges catch a parse or a unit error, a price read in cents or a rate read in
basis points; they are not forecasts of where prices can go.

| Quantity | Range | Why this range |
|---|---|---|
| JKM, TTF and Japanese spot LNG, USD/MMBtu | 1 to 120 | the highest monthly value in the World Bank's Europe gas series is 70.04, August 2022 |
| Henry Hub, USD/MMBtu | 0.5 to 25 | see open question 3: two daily prints of January 2026 exceed 25 |
| US dollars per euro | 0.8 to 1.7 | the euro's range on H.10 since 1999 is 0.8270 (25 October 2000) to 1.6010 (22 April 2008) |
| Reported charter hire, USD per day | minus 10,000 to 500,000 | a spot charter rate can be assessed below zero; the reported figures are in the freight anchors |
| DES LNG spreads to the TTF front month, EUR/MWh | minus 20 to 5 | set before any ACER report was parsed; ACER's own figures will test it |
| SOFR, percent per year | minus 1 to 15 | a rate read in basis points would be a hundred times too large |
| US gas exports in one month, MMcf | 0 to 2,000,000 | the largest monthly LNG total in EIA's release of 31 August 2026 is 539,203 |

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
| ACER DES assessments | the publication day; the half-month assessed is stored beside it |
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
| World Bank Europe gas | April 2015 | TTF from here; an average import border price with a spot component, including the UK, from April 2010 to March 2015 |
| World Bank Japan LNG | every release | the last two months are estimates and are revised |
| EIA exports by destination | every release | revisions at least fourteen months back, logged vintage against vintage |
| Japanese spot LNG | between March and April 2021 | METI's survey ends and JOGMEC's continues it; the two are kept as two series |
| JOGMEC arrival-based price | April 2023 | from cargoes contracted and delivered in the month to cargoes delivered in the month whenever contracted |
| ACER DES assessments | January to March 2023 | NWE priced from 19 January 2023, SE from 20 January, the EU from 8 March, the EU benchmark to TTF from 31 March |
| EU allowance price | after June 2025 | the Commission's latest auction report ends there; later months are missing |

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

Normal dues for LNG carriers ("Rate (5)"), in SDR per ton of Suez Canal Net
Tonnage, from the schedules attached to circular 5/2021 (applicable from 1
February 2022) and circular 7/2023 (applicable from 15 January 2024):

| SCNT band | Laden, from 1 Feb 2022 | Ballast, from 1 Feb 2022 | Laden, from 15 Jan 2024 | Ballast, from 15 Jan 2024 |
|---|---|---|---|---|
| first 5,000 | 7.88 | 6.70 | 10.42 | 8.87 |
| next 5,000 | 6.13 | 5.21 | 8.11 | 6.89 |
| next 10,000 | 5.30 | 4.51 | 7.02 | 5.97 |
| next 20,000 | 4.10 | 3.49 | 5.43 | 4.61 |
| next 30,000 | 3.80 | 3.23 | 5.03 | 4.27 |
| next 50,000 | 3.63 | 3.09 | 4.80 | 4.08 |
| the rest | 3.53 | 3.00 | 4.67 | 3.97 |

Both schedules say the rates "shall be applied according to the vessel's
actual condition upon transit". The schedules in force before February 2022
have not been read, and neither has the step in 2023 (`docs/sources.md`, 3.12).

The other instruments that move an LNG carrier's toll:

| From | What changes | Instrument |
|---|---|---|
| 1 May 2015 | general reduction for LNG carriers cut from 35 to 25 percent | circular 2/2015 |
| 1 Oct 2017 | rebate for US Gulf cargoes to Asia begins, see 6.2 | circular 7/2017 |
| 1 Nov 2021 | general reduction cut from 25 to 15 percent | periodical of 26 October 2021 |
| 1 Feb 2022 | new schedule | circular 5/2021 |
| 1 Mar 2022 | surcharge of 7 percent on normal dues, laden and ballast | circular 5/2022 |
| 15 Mar 2022 | general reduction cancelled | periodical of 14 March 2022 |
| 15 Jan 2024 | normal dues raised 15 percent | circular 7/2023 of 16 October 2023 |
| 15 Jul 2026 | surcharge raised from 7 to 19 percent | periodical 20/2026 of 7 June 2026 |

The rebate in 6.2 cannot be combined with any other LNG rebate, so before 15
March 2022 a US Gulf cargo to Japan takes the larger of the two, not both.

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
| August 2026 | September 2026 | Suez traffic recovering, LNG carriers named among the drivers, no count of Red Sea crossings | Lloyd's List Intelligence, Red Sea briefs |

No source read shows a US Gulf cargo going to Asia through Suez after 12
January 2024. That is an absence of reports, not a count of zero. When the
route is closed to a US cargo in the model, and on what evidence it reopens, is
open question 28.
