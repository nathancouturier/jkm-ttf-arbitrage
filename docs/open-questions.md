# Open questions

Everything this study has not settled, numbered in the order it was raised,
with what would settle it. A question is closed by a decision written here,
never by deleting it.

---

## Data layer

### 1. The weekly JKM and TTF archive is closed to code

Raised 30 September 2026. **Open, the owner's decision.**

EIA's Natural Gas Weekly Update carried the only public weekly JKM and TTF
averages this study found, credited to Bloomberg Finance L.P. eia.gov's
`robots.txt` disallows the archive that holds every past issue
(`/naturalgas/weekly/archivenew_ngwu`), and the Weekly Update ended with the
issue of 22 January 2026. Code reads only that final issue. The archive index
lists 290 issues from January 2020 and 377 from January 2018; which one first
carried the international prices item cannot be established without reading
them.

Options: save the issues by hand into `data/private/ngwu/YYYY/MM_DD.html` (the
parser reads them and the manifest records the step); ask EIA for permission to
fetch the archive with code, or for the series; or build the weekly analysis
without it. Until this is settled, the six weekly anchors from 2021 to 2024 are
unverified and no public JKM series covers April 2021 onward.

### 2. Figures EIA prints under a third party's credit

Raised 30 September 2026. **Open, the owner's decision.**

EIA's publications are in the public domain, but its reuse page also says
material "contributed or licensed by private individuals, companies, or
organizations" "may be protected". The weekly JKM and TTF prices are credited
to Bloomberg Finance L.P. in the text of every issue read; the Henry Hub spot
price is credited on EIA's definitions page to "Refinitiv, an LSEG business".
The page does not say whether such figures fall under the protected materials
sentence. The caches are committed with the credit carried wherever the values
are used. EIA's contact route on the same page is the one way to settle it.

### 3. The Henry Hub bound

Raised 30 September 2026. **Open, the owner's decision.**

The declared range for Henry Hub is 0.5 to 25 USD/MMBtu. EIA's daily spot
series prints 30.72 on 23 January 2026 and 25.01 on 26 January 2026, so the
adapter refuses the whole workbook and no Henry Hub cache exists. The bound is
not widened without a decision: either widen it, or list the two values as
known exceptions with EIA's page as the source.

### 4. A revision that breaks EIA's own addition

Raised 30 September 2026. Open, recorded.

In the release of 30 September 2026, United Kingdom exports for February 2024
move from 34,117 to 34,724 MMcf while the by vessel total does not move, so the
destinations of that month sum to 607 MMcf more than the total. The study keeps
both figures as EIA publishes them. Shares are computed against a stated
denominator (question 5), so the gap is visible rather than absorbed.

### 5. The denominator of the Asian share

Raised 30 September 2026. Open, to be decided with the flow analysis.

EIA's LNG total, `N9133US2`, includes re-exports of previously imported cargoes
and exports by truck; the by vessel total does not. They are equal in January
and June 2026 and differ by 16 MMcf in May 2026. The share of exports going to
Asia needs one of them, stated.

### 6. "From Canada" in the exports by vessel block

Raised 30 September 2026. Open.

The series EIA's page lists as Canada in the LNG exports by vessel block is
named "U.S. Liquefied Natural Gas Exports by Vessel from Canada" in the
workbook, with one value, 3,477 MMcf in January 2026. It is counted with the
Americas. What the label means has not been established.

### 7. Earlier releases of the exports table

Raised 30 September 2026. **Open, the owner's decision.**

EIA keeps no old release online. The Internet Archive holds 41 captures of the
exports workbook from 2011 to May 2026. One, the release of 30 April 2026, is a
test fixture here and shows EIA revising back at least fourteen months,
including China. Importing the others as earlier vintages would extend the
revisions record; they are not imported yet.

### 8. The DOE transaction file as a source

Raised 30 September 2026. **Open, the owner's decision.**

EIA's exports table is built from DOE's "Natural Gas Imports and Exports". DOE
also publishes a cargo by cargo file of US LNG exports, which reproduces EIA's
country figures to the MMcf and explains, for example, that the 4,576 MMcf
EIA shows to China in June 2026 is one whole cargo and part of another. Its
terms have not been read. Adding it would be a new source.

### 9. The weekly series changed product in January 2026

Raised 30 September 2026. Open.

The Weekly Update's "front-month futures prices for liquefied natural gas (LNG)
cargoes in East Asia" and the Supplement's "Japan-Korea Marker (JKM) price" may
or may not be the same Bloomberg series. The two are kept apart, and any chart
that joins them marks the change between the weeks ending 21 and 28 January 2026
as a break.

### 10. Test fixtures are kept as the source served them

Raised 30 September 2026. Recorded.

The house rule is that no file carries an em or an en dash. Two of EIA's pages
kept as test fixtures carry both, in EIA's own text. The fixtures are kept byte
for byte, like the vendored libraries, and the dash check skips
`tests/fixtures/` as it skips `vendor/`. Every text this study writes itself,
including the item text stored in its caches, writes a dash as its code point.

### 11. The euro rate's route

Raised 30 September 2026. Decided provisionally, for the owner to confirm.

The Federal Reserve Board is retiring its Data Download Program: the "Build Your
Package" option goes the week of 9 November 2026 and the rest of the program
later, and long date ranges already come back as an empty body. The Board says
historical data will remain as XML on the release pages, so the study reads the
H.10 release page package. From 2015 it agrees with the history page on every
weekday. The Board now points users of the Data Download Program to FRED
instead; this study keeps to the Board's own publication.

### 12. SOFR is licensed, and there is none before April 2018

Raised 30 September 2026. **Open, the owner's decision.**

The New York Fed publishes SOFR under its Terms of Use, which allow copying and
distribution with a required notice, redistribution on the same terms, and
modified content labelled as such. The committed cache is published on those
terms, not under the repository's MIT licence, and the site must show the
notice wherever SOFR or the financing line appears. SOFR's first value date is
2 April 2018, while the study's cargoes start in February 2016. The financing
line before then is either left missing and said so, or built on a stated
predecessor rate, or held at a labelled assumption.

### 13. Third party sources behind the World Bank's gas rows

Raised 30 September 2026. Open, recorded.

The Pink Sheet is published under CC BY 4.0, and its terms add that third
party datasets may carry extra conditions in their metadata. The gas rows name
Bloomberg Finance L.P., World Gas Intelligence, Thomson Reuters Datastream, The
Wall Street Journal and Official Statistics of Japan among their sources. The
catalogue entry names no extra condition.

### 14. JOGMEC's permission

Raised 30 September 2026. **Open, the owner's decision: whether and how to send.**

JOGMEC's survey is the only public continuation of METI's after March 2021, and
its terms require permission for use beyond private use, education and
quotation, and written permission for a link to its website. Until JOGMEC
answers, the series is kept in `data/private/`. JOGMEC's contact route is a web
form, in English at `https://www.jogmec.go.jp/form/?f=inquiry_en.html` or in
Japanese on the journal site; both require a company name and limit the
message to 2,000 characters. The closest subject in the English form is
"Gathering/Providing Information (Oil and Natural Gas)". Draft:

> Subject: Permission to reuse the monthly spot LNG prices for delivery to Japan
>
> Dear Sir or Madam,
>
> My name is Nathan Couturier. I am an individual building a public,
> non-commercial study of the US LNG export arbitrage between Europe and
> Northeast Asia. The code and results will be published in a public GitHub
> repository (planned address: github.com/nathancouturier/jkm-ttf-arbitrage)
> and on its GitHub Pages website.
>
> I would like to ask JOGMEC's permission to use the series "Monthly spot LNG
> prices for delivery to Japan" from April 2021 onwards: the contract-based and
> arrival-based prices, both preliminary and confirmed values, as published on
> journal.jogmec.go.jp. The values would be stored as a data file in the
> repository and shown in charts and tables on the website.
>
> Every chart, table and data file would carry the credit "Source: JOGMEC,
> Monthly spot LNG prices for delivery to Japan", with a link to your page if you
> allow linking. The website would state clearly that the values were edited by
> this study (arranged into a monthly time series and compared with other
> prices), and that JOGMEC is not responsible for the results. Months that JOGMEC
> did not disclose would be shown as gaps.
>
> Nothing will be published before I receive your permission, and I will follow
> any conditions you set.
>
> Thank you for your time.
>
> Yours faithfully,
> Nathan Couturier
> [email address]

### 15. METI's preliminary figures

Raised 30 September 2026. **Open, the owner's decision.**

METI's historical workbook gives every month's latest figure and is the source
of `meti_spot_lng_monthly`. Only the monthly PDFs carry the preliminary figures,
and METI's site challenges automated requests after a handful of files: nine
PDFs are held, 77 are not. They can be saved by hand from a browser, which is
the manual step recorded in the manifest, or the study can do without METI's
preliminary vintages before August 2020.

### 16. Do METI's and JOGMEC's arrival-based series join?

Raised 30 September 2026. Open.

JOGMEC changed its arrival-based definition in April 2023. METI's own definition
of arrival-based is in its overview document, which could not be read, so
whether METI's arrival-based series continues into JOGMEC's old definition, its
new one, or neither is not established. Until it is, the two are not drawn as
one arrival-based line. The contract-based series are defined the same way in
both surveys' notes.

### 17. April 2026 in JOGMEC's publications

Raised 30 September 2026. Open, recorded.

JOGMEC's May 2026 page, in English and in Japanese, gives the confirmed
contract-based price for April 2026 as 19.2 and says in words that it was
revised from the preliminary 19.1. Both of JOGMEC's historical workbooks,
modified after that page, still give 19.1. The study follows the page.

### 18. ACER's reports, and which discount is observed

Raised 30 September 2026. **Open, the owner's decision.**

ACER's daily reports are on TERMINAL, which this study does not access by code.
They have to be saved by hand; the manual step in the manifest says how, and
starts with the reports of 18 and 23 February 2026, whose figures the study
expects to reproduce. Until reports are saved, the observed discount rests on
the 26 corrected days of ACER's notice of December 2024.

ACER's benchmark is the EU DES assessment minus TTF, while the model's
Northwest Europe discount is for a cargo into Gate. Either the EU benchmark is
used as the observed discount, labelled as the EU's, or an NWE spread is derived
as the benchmark plus the NWE minus EU assessments, using ACER's figures only
but computed by this study. ACER's market monitoring reports show the NWE
spread only as charts built on another publisher's prices; they print an
average of 2 EUR/MWh for January to August 2023 and a range of 2 to 3 EUR/MWh
in the months before April 2024, which can bound an assumption.

### 19. What ACER's legal notice permits

Raised 30 September 2026. Open, recorded.

The first paragraph of ACER's copyright notice prohibits reuse of "this
Licensed Material" without defining it; the second permits reproduction with
acknowledgement. The study reads the first as applying to material ACER marks
as licensed. ACER can confirm it.

### 20. The EU allowance price after June 2025

Raised 30 September 2026. **Open, the owner's decision.**

The Commission's latest auction report covers April to June 2025. For later
months: ask EEX in writing to republish monthly averages of its auction
results; use the German Emissions Trading Authority's monthly reports, whose
terms could not be read because its robots.txt disallows the pages that hold
them; or hold a labelled assumption.

### 21. The licence of the route lines

Raised 1 October 2026. **Open, the owner's decision.**

The lines in `data/seed/routes.geojson` are vertices of the network searoute
bundles. searoute is Apache 2.0; it credits Eurostat's SeaRoute, which is EUPL
1.2, whose copyleft clause does not list the Apache License as compatible; and
Eurostat's network rests on a 2000 Oak Ridge dataset with no stated licence.
Options: keep the lines with attribution to all three; publish only the
distances and draw the map from a coarser set of waypoints this study sets
itself; or ask the library's author how the network was derived.

### 22. The Suez route over the Bahamas

Raised 1 October 2026. Open.

The computed Suez route crosses what reads as the shallow Great Bahama Bank,
which no LNG carrier could use. Forced through deep water it is 44 to 53 nm
longer, 0.3 to 0.4 percent, about a tenth of a day at 17 knots. The committed
distance is the library's; the difference is small against every other
uncertainty in the voyage, and is stated rather than corrected.

### 23. Spark's worked example and its discharge volume

Raised 1 October 2026. Recorded for the engine.

Spark's note on negative freight rates prints a discharge volume of 3,501,428
MMBtu, 14,628 MMBtu below the loaded volume less thirty days of boil-off.
Spark's methodology of November 2022 defines the discharge volume as 98.5
percent of capacity less the laden boil-off less a heel of 3,000 m3. With
fifteen days of laden boil-off that definition gives 3,501,428 exactly. Why the
note uses fifteen laden days for the volume while it uses 17.5 for hire and
fuel is not stated in it. The engine reproduces the note's other lines on their
own terms and does not tune anything to this one.

### 24. Platts' voyage duration via Panama

Raised 1 October 2026. Open.

S&P Global refuses automated requests, even for its robots.txt, so Platts'
subscriber note giving Sabine Pass to Futtsu via Panama at 23 days could not be
read. It can be saved by hand; the routes are tested against Spark's and EIA's
figures without it.

### 25. The Suez toll for a 174,000 m3 carrier

Raised 3 October 2026. **Open, the owner's decision.**

The Suez Canal Authority publishes its toll as special drawing rights (SDR) per
ton of Suez Canal Net Tonnage (SCNT), in seven bands, laden and ballast. The
schedule is citable; the tonnage is not. A canal agency's guidance says the
SCNT of an LNG carrier "depends on the construction" and gives about 85,000
for a 145,000 m3 membrane ship; no source read gives it for a 174,000 m3
two-stroke ship. Options: find the SCNT of a named 174,000 m3 ship in a
published particulars sheet or a written quotation, and compute the toll from
the schedule; publish the formula with SCNT as a labelled assumption and its
range; or price Suez only for the years before 2024, when the route was used,
and say so. Every option needs a daily SDR to dollar rate, from the IMF, whose
terms have not been read yet. The schedule in force before 15 January 2024 is
read for February 2022; the step between them is consistent with a 15 percent
rise in 2023, whose circular was not found.

### 26. Whether the Suez rebate reaches the LNG surcharge

Raised 3 October 2026. Open, recorded.

The Authority's rebate for LNG carriers sailing from the US Gulf to Asia is a
percentage "of Suez Canal normal tolls". Its surcharge on LNG carriers, 7
percent from 1 March 2022 and 19 percent from 15 July 2026, is levied "from
Suez Canal normal transit dues". No text read says whether the rebate also
reduces the surcharge. The two readings differ by the rebate times the
surcharge: at 75 percent and 19 percent, 14.25 percent of the normal toll.
Until a canal agency or the Authority answers, both readings are shown.

### 27. The Suez rebate on the ballast leg

Raised 3 October 2026. **Open, the owner's decision.**

Every rebate text since 2019 names LNG carriers "(laden/ballast)", and the
original circular of 2017 names tankers "loaded or in ballast", so a ballast
transit qualifies on its face. Whether the Authority reads a ballast leg from
Japan to the US Gulf as "operating between" the two areas, and what documents
it then asks for, is not written. From 1 January 2025 the rebate is also
limited to carriers "directly operating" between the two areas, so a cargo
reloaded or calling commercially on the way loses it.

### 28. When the Red Sea was open to a US cargo

Raised 3 October 2026. **Open, the owner's decision.**

The record supports: routine use until the end of 2023; the last laden LNG
carrier through Suez on 12 January 2024 and the last in ballast on 16 January;
no LNG carrier across the Red Sea from mid January to June 2024; a few
crossings by Russia linked ships in 2024, three in the first half of 2025,
"only a handful" in 2025 as a whole and "limited" transits in the winter of
2025 to 2026; and, from one secondary source citing data the study cannot
reach, none at Bab el Mandeb from March to July 2026. No source read shows a
US Gulf cargo going to Asia through Suez after January 2024. Choices: close
the route to a US cargo from 13 January 2024, the day after the last laden
transit, or from 15 January 2024, the day QatarEnergy's pause was reported;
whether August and September 2026 are "closed, no evidence of return" or
"unknown"; and whether the secondary source is accepted for March to July
2026.

### 29. The canal's monthly transit counts

Raised 3 October 2026. **Open, the owner's decision.**

The Authority's annual reports give LNG ship transits by year: 819 in 2023,
119 in 2024 and 282 in 2025, both directions, laden and ballast. Its monthly
counts by ship type appear only in an interactive report on its statistics
page, which the study does not read by code. Reading it by hand would give a
monthly record for 2023 to 2026, with the caveat that a canal transit is not a
Red Sea crossing: ships entering from the north to deliver at Ain Sukhna or
Aqaba are counted and never pass Bab el Mandeb.

### 30. Quoting the Suez Canal Authority

Raised 3 October 2026. **Open, the owner's decision.**

The Authority's site has no terms of use page that could be found, and every
page carries "Copyright 2017 | All Right Reserved Suez Canal Authority". The
study quotes rates, percentages and dates from its circulars and counts from
its annual reports, each with its source, and copies no document. Either that
is accepted as quotation, or the Authority is asked.
