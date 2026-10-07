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
| DES LNG spreads to the TTF front month, EUR/MWh | minus 20 to 5 | set before any ACER report was parsed; ACER's own figures will test it |
| SOFR, percent per year | minus 1 to 15 | a rate read in basis points would be a hundred times too large |
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
March 2022 a US Gulf cargo to Japan cannot take both. This study assumes it
takes the larger, which the circular does not say.

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
Sabine Pass and Futtsu 35,763 $ below Sabine Pass and Gate. Which of them the
engine uses, and how a two-port figure enters a cost line written per port, are
open questions 31 and 32.

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
| 15 Aug 2024 | about November 2025 | the Authority states its commitment to return to normal operating conditions (50 feet; 36 booking slots, 10 neopanamax, from 1 September 2024); LNG use stays low | advisory A-28-2024; IEA, Gas Market Reports 2025 and Q1 2026 |
| December 2025 | 3 Sep 2026 | water conservation; neopanamax draught cut to 48 feet by 2 September 2026; an LNG first rule for one booking slot from 4 January 2026 | the Authority's press release of 5 August 2026; advisories of 2025 and 2026 |
| 4 Sep 2026 | to date | El Nino measures: 9 neopanamax slots a day; 10 slots and at least four LNG slots a week announced from 15 October 2026 | advisories A-29-2026 and A-36-2026 |
