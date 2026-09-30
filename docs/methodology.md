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
