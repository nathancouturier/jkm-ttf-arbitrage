# Open questions

Everything this study has not settled, numbered in the order it was raised,
with what would settle it. A question is closed by a decision written here,
never by deleting it.

---

## Data layer

### 1. The weekly JKM and TTF archive is closed to code

Raised 30 September 2026. **Decided 7 October 2026.**

EIA's Natural Gas Weekly Update carried the only public weekly JKM and TTF
averages this study found, credited to Bloomberg Finance L.P. eia.gov's
`robots.txt` disallows the archive that holds every past issue
(`/naturalgas/weekly/archivenew_ngwu`), and the Weekly Update ended with the
issue of 22 January 2026. Code reads only that final issue. The archive index
lists 292 issues from January 2020 and 389 from January 2018; which one first
carried the international prices item cannot be established without reading
them.

Options: save the issues by hand into `data/private/ngwu/YYYY/MM_DD.html` (the
parser reads them and the manifest records the step); ask EIA for permission to
fetch the archive with code, or for the series; or build the weekly analysis
without it. Until this is settled, the six weekly anchors from 2021 to 2024 are
unverified and no public JKM series covers April 2021 onward.

Decision: the archived issues are read from the Internet Archive's earliest
capture of each, never from eia.gov, under the Archive's terms
(`docs/sources.md` 2.16). All 488 issues the index lists from 2016 are held
privately; 207 carry the item, from the issue of 16 September 2021 to the
final one, and every weekly anchor reproduces exactly. The parsed figures and
the text they were read from are committed, the pages are not, except eleven
kept as test fixtures.

### 2. Figures EIA prints under a third party's credit

Raised 30 September 2026. **Decided 7 October 2026.**

EIA's publications are in the public domain, but its reuse page also says
material "contributed or licensed by private individuals, companies, or
organizations" "may be protected". The weekly JKM and TTF prices are credited
to Bloomberg Finance L.P. in the text of every issue read; the Henry Hub spot
price is credited on EIA's definitions page to "Refinitiv, an LSEG business".
The page does not say whether such figures fall under the protected materials
sentence. The caches are committed with the credit carried wherever the values
are used. EIA's contact route on the same page is the one way to settle it.

Decision: the caches are committed, with the credit EIA prints carried beside
every value they hold and on every page that shows them. EIA's reuse statement
covers its information products; the figures are EIA's publication of them.
Should EIA or a rights holder object, the two series move to `data/private/`
and the site shows only what is derived from them.

### 3. The Henry Hub bound

Raised 30 September 2026. **Decided 7 October 2026.**

The declared range for Henry Hub was 0.5 to 25 USD/MMBtu. EIA's daily spot
series prints 30.72 on 23 January 2026 and 25.01 on 26 January 2026, so the
adapter refused the whole workbook and no Henry Hub cache existed.

Decision: the range is 0.5 to 50 USD/MMBtu. The bounds exist to catch a unit
or parse error, not to judge a price, and the two prints are EIA's own. A
price read in cents would still fail.

### 4. A revision that breaks EIA's own addition

Raised 30 September 2026. **Decided 8 October 2026.**

In the release of 30 September 2026, United Kingdom exports for February 2024
move from 34,117 to 34,724 MMcf while the by vessel total does not move, so the
destinations of that month sum to 607 MMcf more than the total. The study keeps
both figures as EIA publishes them. Shares are computed against a stated
denominator (question 5), so the gap is visible rather than absorbed.

Decision: the two figures are kept as EIA publishes them. Shares use the by
vessel total of question 5, so the 607 MMcf by which February 2024's
destinations exceed it is visible in the revisions log rather than absorbed,
and no share for that month is recomputed from the sum.

### 5. The denominator of the Asian share

Raised 30 September 2026. **Decided 7 October 2026.**

EIA's LNG total, `N9133US2`, includes re-exports of previously imported cargoes
and exports by truck; the by vessel total does not. They are equal in January
and June 2026 and differ by 16 MMcf in May 2026. The share of exports going to
Asia needs one of them, stated.

Decision: shares of exports by destination are computed against the by vessel
total, the block the destination columns belong to. The LNG total including
re-exports is shown beside it where the two differ.

### 6. "From Canada" in the exports by vessel block

Raised 30 September 2026. **Decided 8 October 2026.**

The series EIA's page lists as Canada in the LNG exports by vessel block is
named "U.S. Liquefied Natural Gas Exports by Vessel from Canada" in the
workbook, with one value, 3,477 MMcf in January 2026. It is counted with the
Americas. What the label means has not been established.

Decision: the series is counted with the Americas under the name the workbook
gives it. Its one value, 3,477 MMcf in January 2026, is under one percent of
that month's total, so either reading leaves every share the study shows
unchanged at the precision printed.

### 7. Earlier releases of the exports table

Raised 30 September 2026. **Decided 7 October 2026.**

EIA keeps no old release online. The Internet Archive holds 41 captures of the
exports workbook from 2011 to May 2026. One, the release of 30 April 2026, is a
test fixture here and shows EIA revising back at least fourteen months,
including China. Importing the others as earlier vintages would extend the
revisions record; they are not imported yet.

Decision: not imported. The latest release carries every month, and earlier
captures would only extend the record of revisions, which each new release now
adds to by itself.

### 8. The DOE transaction file as a source

Raised 30 September 2026. **Decided 7 October 2026.**

EIA's exports table is built from DOE's "Natural Gas Imports and Exports". DOE
also publishes a cargo by cargo file of US LNG exports, which reproduces EIA's
country figures to the MMcf and explains, for example, that the 4,576 MMcf
EIA shows to China in June 2026 is one whole cargo and part of another. Its
terms have not been read. Adding it would be a new source.

Decision: added, as `doe_lng_export_cargoes`, from January 2016. DOE's web
policies put its information in the public domain with an acknowledgement
requested (`docs/sources.md`, 2.1.1). It gives the flow analysis each cargo's
terminal and day, so Sabine Pass cargoes can be followed on their own.

### 9. The weekly series changed product in January 2026

Raised 30 September 2026. **Decided 7 October 2026.**

The Weekly Update's "front-month futures prices for liquefied natural gas (LNG)
cargoes in East Asia" and the Supplement's "Japan-Korea Marker (JKM) price" may
or may not be the same Bloomberg series. The two are kept apart, and any chart
that joins them marks the change between the weeks ending 21 and 28 January 2026
as a break.

Decision: kept as two series, with the break marked wherever they are shown
together.

### 10. Test fixtures are kept as the source served them

Raised 30 September 2026. **Decided 30 September 2026.**

The house rule is that no file carries an em or an en dash. Two of EIA's pages
kept as test fixtures carry both, in EIA's own text. The fixtures are kept byte
for byte, like the vendored libraries, and the dash check skips
`tests/fixtures/` as it skips `vendor/`. Every text this study writes itself,
including the item text stored in its caches, writes a dash as its code point.

### 11. The euro rate's route

Raised 30 September 2026. **Decided 7 October 2026.**

The Federal Reserve Board is retiring its Data Download Program: the "Build Your
Package" option goes the week of 9 November 2026 and the rest of the program
later, and long date ranges already come back as an empty body. The Board says
historical data will remain as XML on the release pages, so the study reads the
H.10 release page package. From 2015 it agrees with the history page on every
weekday. The Board now points users of the Data Download Program to FRED
instead; this study keeps to the Board's own publication.

Decision: confirmed. The study reads the H.10 release page package, the route
the Board says will remain.

### 12. SOFR is licensed, and there is none before April 2018

Raised 30 September 2026. **Decided 7 October 2026.**

The New York Fed publishes SOFR under its Terms of Use, which allow copying and
distribution with a required notice, redistribution on the same terms, and
modified content labelled as such. The committed cache is published on those
terms, not under the repository's MIT licence, and the site must show the
notice wherever SOFR or the financing line appears. SOFR's first value date is
2 April 2018, while the study's cargoes start in February 2016. The financing
line before then is either left missing and said so, or built on a stated
predecessor rate, or held at a labelled assumption.

Decision: SOFR is published under the New York Fed's terms, with the notice
wherever it or the financing line appears. Before 2 April 2018 the financing
line runs on the effective federal funds rate, read from the same API under the
same terms, 4 January 2016 to 30 April 2018, and labelled as a different rate,
unsecured where SOFR is secured. The Board's H.15 carries the same figures in
the public domain and agrees on every day, should the New York Fed's terms ever
stand in the way.

### 13. Third party sources behind the World Bank's gas rows

Raised 30 September 2026. **Decided 8 October 2026.**

The Pink Sheet is published under CC BY 4.0, and its terms add that third
party datasets may carry extra conditions in their metadata. The gas rows name
Bloomberg Finance L.P., World Gas Intelligence, Thomson Reuters Datastream, The
Wall Street Journal and Official Statistics of Japan among their sources. The
catalogue entry names no extra condition.

Decision: the Pink Sheet is used under the CC BY 4.0 licence its catalogue
entry declares, which names no extra condition, and the World Bank is credited
with the sources it names beside each gas row.

### 14. JOGMEC's permission

Raised 30 September 2026. **Decided 7 October 2026.**

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

Decision: JOGMEC's series stays private and nothing derived from it is
published. The letter in this question is ready for the owner to send; until
JOGMEC answers, the series is used only as a private check on the public ones.

### 15. METI's preliminary figures

Raised 30 September 2026. **Decided 7 October 2026.**

METI's historical workbook gives every month's latest figure and is the source
of `meti_spot_lng_monthly`. Only the monthly PDFs carry the preliminary figures,
and METI's site challenges automated requests after a handful of files: nine
PDFs are held, 77 are not. They can be saved by hand from a browser, which is
the manual step recorded in the manifest, or the study can do without METI's
preliminary vintages before August 2020.

Decision: not collected. The workbook carries every month's latest figure; the
preliminary figures would only show METI's own revisions.

Revised 8 October 2026: the owner saved 19 of the monthly PDFs by hand, the
releases for October 2019 to March 2021 and the detailed release for March
2021. They are parsed into `meti_spot_lng_releases`, every figure
each release printed with the day of the release, and the 2020 notice test on
the Flows view uses METI's figure as first released by each notice day. The
other releases are not held.

### 16. Do METI's and JOGMEC's arrival-based series join?

Raised 30 September 2026. **Decided 7 October 2026.**

JOGMEC changed its arrival-based definition in April 2023. METI's own definition
of arrival-based is in its overview document, which could not be read, so
whether METI's arrival-based series continues into JOGMEC's old definition, its
new one, or neither is not established. Until it is, the two are not drawn as
one arrival-based line. Both surveys' notes describe the same kind of cargo:
spot cargoes, cargo by cargo, on a DES basis, as simple averages. JOGMEC defines
its contract-based price in the text of each month's page; METI's monthly
notes use the term without defining it.

Decision: kept as two arrival-based lines, never joined, and the contract-based
series are joined only with the change of survey marked.

### 17. April 2026 in JOGMEC's publications

Raised 30 September 2026. **Decided 8 October 2026.**

JOGMEC's May 2026 page, in English and in Japanese, gives the confirmed
contract-based price for April 2026 as 19.2 and says in words that it was
revised from the preliminary 19.1. Both of JOGMEC's historical workbooks,
modified after that page, still give 19.1. The study follows the page.

Decision: the page is followed, 19.2, since it says in words that the
preliminary figure was revised; the workbook's 19.1 is kept beside it. The
series is private either way (question 14).

### 18. ACER's reports, and which discount is observed

Raised 30 September 2026. **Decided 7 October 2026.**

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

Decision: no report is collected by hand for now; the manual step stays in the
manifest for whenever one is. The observed discount is ACER's EU benchmark on
the 26 corrected days, labelled as the EU's. Everywhere else the Northwest
Europe discount is a labelled assumption whose range is set from what ACER's
monitoring reports print, about 2 EUR/MWh on average from January to August
2023 and 2 to 3 EUR/MWh in the months before April 2024, and the verdict's
sensitivity to it is shown.

Revised 8 October 2026: the owner saved TERMINAL's historical download, every
day ACER published from 19 January 2023. The Northwest Europe discount is now observed
from 31 March 2023, as the EU benchmark plus the NWE assessment less the EU
one, computed from ACER's figures and averaged over the days each price spans;
the assumption of -2 EUR/MWh stays for earlier dates. Over April to August 2023
the observed NWE spread averages -2.33 EUR/MWh, close to the assumption.

### 19. What ACER's legal notice permits

Raised 30 September 2026. **Decided 7 October 2026.**

The first paragraph of ACER's copyright notice prohibits reuse of "this
Licensed Material" without defining it; the second permits reproduction with
acknowledgement. The study reads the first as applying to material ACER marks
as licensed. ACER can confirm it.

Decision: the study proceeds on the reading that the first paragraph covers
only material ACER marks as licensed, and acknowledges ACER as the source of
every value.

Revised 8 October 2026: most of the committed values now come from TERMINAL's
historical download. TERMINAL's home page carries no legal notice or terms of
its own, offers the CSV download as a feature and points to ACER's website,
while ACER's methodology mentions a TERMINAL legal notice the page does not
show. The same reading of ACER's legal notice is applied to the download, with
ACER acknowledged as the source; should a TERMINAL notice turn up that forbids
it, the series moves to `data/private/` and only what is derived from it is
shown.

### 20. The EU allowance price after June 2025

Raised 30 September 2026. **Decided 8 October 2026.**

The Commission's latest auction report covers April to June 2025. For later
months: ask EEX in writing to republish monthly averages of its auction
results; use the German Emissions Trading Authority's monthly reports, whose
terms could not be read because its robots.txt disallows the pages that hold
them; or hold a labelled assumption.

Decision: the Commission's auction reports stay the series to June 2025. After
it, the engine takes the monthly average of Germany's auctions as DEHSt reports
it, a labelled proxy, committed as `dehst_eua_german_auction_monthly`: DEHSt's
terms, read in a browser on 8 October 2026, put its texts under CC BY-NC-ND
4.0, which lets the contents of a database be shared for non-commercial
purposes, unchanged (`docs/sources.md` 2.23). Over the 18 months both cover,
the German average is 0.10 EUR/t above the Commission's on average and 1.40 at
most. After DEHSt's last month, August 2026, 82.31 EUR/t, that month is held,
labelled an assumption, and the result is shown at 61 and 86 EUR/t, the range
of 2025 the Commission's electricity market report for the fourth quarter of
2025 prints for a secondary market price. Should DEHSt or EEX object, the
series moves to `data/private/`. Written requests to EEX and to the Commission
on reports after June 2025 remain a step for the owner.

### 21. The licence of the route lines

Raised 1 October 2026. **Decided 7 October 2026.**

The lines in `data/seed/routes.geojson` are vertices of the network searoute
bundles. searoute is Apache 2.0; it credits Eurostat's SeaRoute, which is EUPL
1.2, whose copyleft clause does not list the Apache License as compatible; and
Eurostat's network rests on a 2000 Oak Ridge dataset with no stated licence.
Options: keep the lines with attribution to all three; publish only the
distances and draw the map from a coarser set of waypoints this study sets
itself; or ask the library's author how the network was derived.

Decision: the distances stay this study's and MIT. The lines in
`data/seed/routes.geojson` are published under the European Union Public
Licence 1.2, as a work derived from the network Eurostat's Searoute carries,
with attribution to searoute (Apache License 2.0), to Eurostat and to the Oak
Ridge National Laboratory dataset Eurostat names; `NOTICE` says so.

### 22. The Suez route over the Bahamas

Raised 1 October 2026. **Decided 7 October 2026.**

The computed Suez route crosses what reads as the shallow Great Bahama Bank,
which no LNG carrier could use. Forced through deep water it is 44 to 53 nm
longer, 0.3 to 0.4 percent, about a tenth of a day at 17 knots. The committed
distance is the library's; the difference is small against every other
uncertainty in the voyage, and is stated rather than corrected.

Decision: the library's distance is kept and the difference stated.

### 23. Spark's worked example and its discharge volume

Raised 1 October 2026. **Decided 8 October 2026.**

Spark's note on negative freight rates prints a discharge volume of 3,501,428
MMBtu, 14,628 MMBtu below the loaded volume less thirty days of boil-off.
Spark's methodology of November 2022 defines the discharge volume as 98.5
percent of capacity less the laden boil-off less a heel of 3,000 m3. With
fifteen days of laden boil-off that definition gives 3,501,428 exactly. Why the
note uses fifteen laden days for the volume while it uses 17.5 for hire and
fuel is not stated in it. The engine reproduces the note's other lines on their
own terms and does not tune anything to this one.

Added 3 October 2026. The same note's screenshot of Spark's Routes page for
Sabine Pass to Futtsu via Panama, 8 February 2022, charges fuel and hire for 54
days, and its rounded figures in $/MMBtu fit the same definition with 27 days
of laden boil-off, half the voyage, as fifteen is half of Spark30's thirty.
That is a pattern in Spark's figures, not a rule Spark states.

Decision: nothing is tuned to the discharge volume. The engine reproduces every
other line of the note within a dollar, and the volume is shown with the
definition and the fifteen laden days that reproduce it.

### 24. Platts' voyage duration via Panama

Raised 1 October 2026. **Decided 7 October 2026.**

S&P Global refuses automated requests, even for its robots.txt, so Platts'
subscriber note giving Sabine Pass to Futtsu via Panama at 23 days could not be
read. It can be saved by hand; the routes are tested against Spark's and EIA's
figures without it.

Decision: not pursued; the routes are tested against Spark's and EIA's figures.

### 25. The Suez toll for a 174,000 m3 carrier

Raised 3 October 2026. **Decided 8 October 2026.**

The Suez Canal Authority publishes its toll as special drawing rights (SDR) per
ton of Suez Canal Net Tonnage (SCNT), in seven bands, laden and ballast. The
schedule is citable; the tonnage is not. A canal agency's guidance says the
SCNT of an LNG carrier "depends on the construction" and gives about 85,000
for a 145,000 m3 membrane ship and about 105,000 for a spherical tank (Moss)
ship of the same size; no source read gives it for a 174,000 m3
two-stroke ship. Options: find the SCNT of a named 174,000 m3 ship in a
published particulars sheet or a written quotation, and compute the toll from
the schedule; publish the formula with SCNT as a labelled assumption and its
range; or price Suez only for the years before 2024, when the route was used,
and say so. Every option needs a daily SDR to dollar rate, from the IMF, whose
terms have not been read yet. The schedule in force before 15 January 2024 is
read for February 2022; the step between them is consistent with a 15 percent
rise in 2023, whose circular was not found.

Decision: the toll is computed from the Authority's schedules, every one now
read from 2015 (`docs/methodology.md`, section 6.1), with the tonnage a
labelled assumption: the agency's ratio of 85,000 SCNT to 145,000 m3 applied
to the capacity, 102,000 SCNT for 174,000 m3 and 93,793 for 160,000 m3, shown
also at 85,000 and at 112,148, the Authority's net tonnage per LNG transit in
2023. The SDR is converted at the IMF's rate of the day as the Bundesbank
republishes it, kept private until the IMF's terms are read (question 46). The
route is priced on every date and offered to a US cargo only while it was open
(question 28).

### 26. Whether the Suez rebate reaches the LNG surcharge

Raised 3 October 2026. **Decided 7 October 2026.**

The Authority's rebate for LNG carriers sailing from the US Gulf to Asia is a
percentage "of Suez Canal normal tolls". Its surcharge on LNG carriers, 7
percent from 1 March 2022 and 19 percent from 15 July 2026, is levied "from
Suez Canal normal transit dues". No text read says whether the rebate also
reduces the surcharge. The two readings differ by the rebate times the
surcharge: at 75 percent and 19 percent, 14.25 percent of the normal toll.
Until a canal agency or the Authority answers, both readings are shown.

Decision: the rebate is applied to normal dues only, as the texts say, and the
surcharge is paid in full; the other reading is shown as a sensitivity.

### 27. The Suez rebate on the ballast leg

Raised 3 October 2026. **Decided 7 October 2026.**

Every rebate text since 2019 names LNG carriers "(laden/ballast)", and the
original circular of 2017 names tankers "loaded or in ballast", so a ballast
transit qualifies on its face. Whether the Authority reads a ballast leg from
Japan to the US Gulf as "operating between" the two areas, and what documents
it then asks for, is not written. From 1 January 2025 the rebate is also
limited to carriers "directly operating" between the two areas, so a cargo
reloaded or calling commercially on the way loses it.

Decision: the rebate applies to the ballast leg of a direct round trip, since
every text since 2019 names laden and ballast carriers.

### 28. When the Red Sea was open to a US cargo

Raised 3 October 2026. **Decided 7 October 2026.**

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

Decision: the route through Suez is closed to a US Gulf cargo from 13 January
2024, the day after the last laden LNG transit, to the latest date of the data,
since no source shows a return. Before that it is open. The secondary source
for March to July 2026 is quoted as corroboration only; nothing rests on it.

### 29. The canal's monthly transit counts

Raised 3 October 2026. **Decided 7 October 2026.**

The Authority's annual reports give LNG ship transits by year: 819 in 2023,
119 in 2024 and 282 in 2025, both directions, laden and ballast. Its monthly
counts by ship type appear only in an interactive report on its statistics
page, which the study does not read by code. Reading it by hand would give a
monthly record for 2023 to 2026, with the caveat that a canal transit is not a
Red Sea crossing: ships entering from the north to deliver at Ain Sukhna or
Aqaba are counted and never pass Bab el Mandeb.

Decision: not collected; the yearly counts are enough for the record the study
shows.

### 30. Quoting the Suez Canal Authority

Raised 3 October 2026. **Decided 7 October 2026.**

The Authority's site has no terms of use page that could be found, and every
page carries "Copyright 2017 | All Right Reserved Suez Canal Authority". The
study quotes rates, percentages and dates from its circulars and counts from
its annual reports, each with its source, and copies no document. Either that
is accepted as quotation, or the Authority is asked.

Decision: quotation of rates, percentages, dates and counts, each with its
source, is accepted; no document of the Authority's is copied.

### 31. The Japanese port cost

Raised 3 October 2026. **Decided 7 October 2026.**

No public source gives an all-in port cost for an LNG carrier at a Japanese
terminal. Spark's note on negative freight rates shows, in a screenshot of its
Routes page, 273,184 $ for Sabine Pass and Futtsu via Panama, for a 160,000 m3
TFDE, on 8 February 2022, beside its 308,947 $ for Sabine Pass and Gate on the
same basis. Options: use both Spark figures, labelled as Spark's, from GAC,
indicative, early 2022 and two ports combined; set Futtsu equal to Gate,
labelled an assumption; or assemble Futtsu from the published components in
`docs/methodology.md`, section 7.2, which still lack several items listed
there. Spark's pair is the only source that prices both destinations on one
basis.

Decision: Spark's two-port figures are used: 308,947 $ for Sabine Pass and Gate
and 273,184 $ for Sabine Pass and Futtsu, each labelled as Spark's, from GAC,
indicative, February 2022, for a 160,000 m3 TFDE, two ports combined.

### 32. Two-port figures in a cost line written per port

Raised 3 October 2026. **Decided 7 October 2026.**

The cost line is `port(load) + port(destination)`, while Spark gives each pair
of ports as one sum. Either the line becomes a port cost per route, or each sum
is split under a stated assumption. Both Spark figures are also for a 160,000
m3 TFDE in February 2022: for the 174,000 m3 two-stroke and for other years
they are either held constant or scaled, for instance by gross tonnage, and
either choice is an assumption to state.

Decision: the port cost becomes a cost per route, the pair Spark gives, and is
held at Spark's figures for every year and for both ships. Both choices are
labelled assumptions in the parameter table.

### 33. The Sabine Neches cargo fee

Raised 3 October 2026. **Decided 7 October 2026.**

The Sabine Neches Navigation District charges 0.20 $ per short ton of
hydrocarbon cargo from 1 May 2021, reviewable each year up to 0.35 $. A court
record lists what it cost one offtaker's LNG loadings from May to August 2021:
15,462 $ to 16,357 $ each, about 0.004 $/MMBtu on a full cargo of 160,000 to
174,000 m3 (this study's arithmetic). The current rate was not found, and
whether Spark's port costs include the fee is not stated. Either it is a line of its own at the load port, or it
is taken as part of the port cost and said so.

Decision: no separate line. The fee is taken to be inside the port costs, and
that is stated beside them.

### 34. Kisarazu's entry dues and LNG fuelled ships

Raised 3 October 2026. **Decided 8 October 2026.**

Chiba prefecture exempts "LNGを燃料とする船舶" (ships using LNG as fuel) from
entry dues at Chiba and Kisarazu ports. An LNG carrier burns its cargo's
boil-off; whether it counts is not stated. Chiba's Kisarazu port office can
answer. Until then the dues of 2.50 yen per gross ton are taken to apply.

Decision: not needed. The port cost line is Spark's all-in figure for each pair
of ports (question 32), so no Japanese port due is computed from a tariff and
the exemption changes no figure the study shows.

### 35. Rotterdam's cap on the cargo part for LNG tankers

Raised 3 October 2026. **Decided 8 October 2026.**

In 2024 Rotterdam caps an LNG tanker's cargo dues at 133.7 percent of its
gross tonnage times the cargo rate. The 2025 and 2026 tariffs give such ratios
for other ship types and none for LNG tankers. Whether the cargo part is
uncapped for them, or the row is missing, is a question for the Port of
Rotterdam Authority. It matters only if Rotterdam's dues are modelled from the
tariff rather than taken inside a published all-in figure.

Decision: not needed, for the same reason as question 34: Rotterdam's dues are
not computed from its tariff.

### 36. Spark's figures in this study

Raised 6 October 2026. **Decided 7 October 2026.**

Spark's terms (`docs/sources.md`, 2.13) bar publishing or reproducing Spark
Content without a licence, except "as permitted by laws relating to fair use".
The study already prints Spark figures: the worked example of its note on
negative rates, which the engine is to reproduce line by line, the two port
figures in `docs/methodology.md`, section 7.1, and the discharge volume in
question 23; the freight anchors would add reported rates. Options: rely on
fair use for individual figures, each attributed and none reproduced as a
table or series; ask Spark for written permission to quote a short, named list
(Spark gives commercial@sparkcommodities.com for licences); or keep Spark's
figures in `data/private/` and test the engine against them privately. Only
written permission removes the doubt.

Decision: individual figures are quoted with their attribution, as fair use for
a non-commercial study: the worked example, which the engine reproduces as a
check of method, the two port figures and the reported charter rates. No Spark
document is reproduced, no Spark series is built, and Spark's documents are
named, not linked.

### 37. The freight anchors

Raised 6 October 2026. **Decided 7 October 2026.**

Nine reported charter rates have been verified in readable, dated articles or
documents, one per month, from February 2022 to October 2026. They are kept in
`data/private/` until four things are decided.

* What may be committed: the figure, its date, the assessment and the
  article's address, or also the article's sentence, which LNG Prime, Lloyd's
  List and Hellenic Shipping News each forbid republishing without consent.
* Rows whose assessment day is not stated (five of the nine), or whose
  assessment or vessel is inferred rather than stated (five of the nine, mostly
  the same rows): kept with the gap shown, or dropped.
* October 2022: the figure first reported, on 10 October, or the month's
  highest, reported on 20 October.
* April 2020, for which no readable figure was found: run that date at the
  low, central and high hire set from the other figures, or look for a source
  by hand.

The two figures of the week to 24 July 2026 could not be verified: they sit
behind LNG Prime's subscription.

Decision: the seed carries, for each of the verified figures, the value, the
date it refers to (empty when the article gives none, with the article's own
date beside it), the assessment and vessel basis (marked inferred where the
article does not state them), the publisher and the article's address, and
never the article's sentence. October 2022 is the figure of 10 October, the
first reported. April 2020 is run at the low, central and high hire set from
the other figures. On 8 October 2026 the figures first reported in March and
April 2026 were added from LNG Prime: 161,750 $/day for 3 March, as the
conflict with Iran intensified, and 92,000 $/day in the article of 3 April.
Under the 14-day window the first stands for the weeks ending 18 February to
11 March 2026, all with the arb east closed, two of them before the conflict,
when LNG Prime put Atlantic rates above 30,000 and 40,000 $/day: those two
weeks' reported hire overstates it. The second stands for the weeks ending 25
March to 15 April, in which the arb east was open.

### 38. Lloyd's List Intelligence's briefs

Raised 6 October 2026. **Decided 7 October 2026.**

Nine of Lloyd's List Intelligence's public Red Sea briefs, from 23 July to 1
October 2026, and one Lloyd's List article were read by script before their
publisher's terms were read. The terms forbid, without written permission,
"bulk/batch downloading or automated scraping of Content". No further request
is sent to either site. The last band of the Red Sea record (`docs/methodology.md`,
section 6.3) and one freight anchor rest on them. Options: drop them, and mark
August and September 2026 as unknown; ask the publisher; or have the owner read
and save the pages by hand, as a manual step.

Decision: Lloyd's List Intelligence and Lloyd's List are dropped as sources.
August and September 2026 are marked unknown in the Red Sea record, and the
freight anchor of 3 March 2026 is dropped unless a readable source allowed by
its publisher is found. The copies read stay private and unused, and no request
is sent to either site.

### 39. The Panama toll's inputs

Raised 7 October 2026. **Decided 7 October 2026.**

The dated tolls in `docs/methodology.md`, section 8.1, leave three inputs to
set. The capacity the canal charges on is its own admeasurement, whose rules
were not read: the nominal capacity stands in for it, labelled an assumption,
or the rules are read first. Before 2023 a ship returning through the canal in
ballast within 60 days paid a roundtrip ballast rate, about 79 percent of the
laden toll, instead of the ordinary ballast table, about 88 percent: the model
takes one of the two, or the cheaper only when its own ballast leg is through
Panama within 60 days. The reference ships' beams are not sourced, and from
June 2021 they set the booking fee band; the Authority's own press releases
give LNG carriers it handled beams of 45 to 49 m, all in the upper band.

Decision: the nominal capacity stands in for the canal's admeasured capacity,
labelled an assumption. Before 2023 the roundtrip ballast rate applies when
both legs pass Panama, since the computed voyage returns well within 60 days;
otherwise the ordinary ballast table. The reference ships are taken to be over
42.67 m in beam, labelled an assumption, as every LNG carrier the Authority
describes is.

### 40. The other Panama charges

Raised 7 October 2026. **Decided 7 October 2026.**

The fresh water surcharge has been mandatory since 15 February 2020 and is not
yet a line of the cost model. Its percentage depends on Gatun
Lake's level each day, which was not collected: it is either a scenario range
(0 to 10 percent of tolls, 1 to 10 percent before 2023) or read from a daily
series the Authority links from its advisories, after its own terms are
checked. The booking fee is either zero by default with a booked case, or
always charged; its amount in 2023 was not found. Auction premiums have no
published results and stay a scenario, if shown at all. Waiting days are a
scenario input with three cited values: two to three days in normal conditions
and 15 days for unreserved slots in mid December 2023 (IEA), 12 days for
unbooked vessels in late July 2023 (Spark, reported by LNG Prime).

Decision: the fresh water surcharge is a line of the cost model from 15
February 2020: the fixed 10,000 $ per transit always, and the variable part as
a labelled assumption at the middle of its range, 5 percent of tolls, with 0
and 10 percent shown. The booking fee and waiting days are zero by default, for
an unbooked ship in normal conditions, with a booked case and the cited waiting
days as scenarios.

### 41. Quoting the Panama Canal Authority

Raised 7 October 2026. **Decided 7 October 2026.**

The Authority's terms forbid copying, distribution, reproduction or
publication of its documents "for commercial or lucrative purposes", and may
forbid any "modification or alteration" whatever the purpose. The study quotes
rates, item codes and dates, each with its document, commits no document of
the Authority's, and does not use its logo or images. Either that is accepted
as quotation for a non-commercial study, or the Authority is asked; its
advisories name canaltolls@pancanal.com for toll questions.

Decision: quotation of rates, item codes and dates, each with its document, is
accepted for a non-commercial study; no document, logo or image of the
Authority's is copied.

### 42. Where the IEA and the Panama Canal Authority disagree

Raised 7 October 2026. **Decided 8 October 2026.**

Four statements in the IEA's gas reports disagree with the Authority's own
texts: LNG carriers given three booking slots a day from August 2024; 27
vessels a day after early 2025; only 24 transits a day in early 2024; LNG
carriers barred from night transits. The Authority's notices, advisories and
press releases are followed wherever the two differ, and each difference is
shown where the IEA is quoted. The IEA may count differently, for instance
transits against booking slots.

Decision: the Authority's own notices, advisories and press releases are
followed wherever the two differ, and each difference is shown where the IEA is
quoted.

### 43. Two weekly issues repeat the week before

Raised 7 October 2026. **Decided 7 October 2026.**

The Natural Gas Weekly Update issues of 14 September 2023 and 7 March 2024
print, under their own header, the international prices item of the issue a
week earlier, word for word, year-earlier week included. A year later EIA
printed figures for the two weeks as year-earlier figures: 13.36 and 10.99
USD/MMBtu for the week ending 13 September 2023, and 8.36 and 8.38 for the
week ending 6 March 2024.

Decision: the two weeks have no value in the weekly series. Their text is kept
and the anomaly column says why. The figures printed a year later are shown in
the year-earlier cross-check, never used to fill the two weeks, because they
come from a later issue on whatever basis EIA used then.

### 44. The TTF expiry rule, from ICE's own documents

Raised 8 October 2026. **Decided 8 October 2026.**

The delivery month a front-month TTF price names depends on when ICE Endex's
Dutch TTF futures stop trading, which the study takes as two business days
before the delivery month, on weekdays. ICE's terms of use forbid "any data
mining, robots or similar data gathering or extraction methods" and CME's
forbid scripts, so neither exchange's contract rules were read, and the CFTC's
robots.txt closes its copies of the rule filings to this study's client. The
JKM side is sourced: Platts' roll on the 16th from its press release of June
2015, and the settlement window from the Japan Exchange Group's contract on
Platts JKM. Settling the TTF side takes a person reading ICE Endex's contract
specification in a browser, with its holiday calendar.

Decision: settled on 8 October 2026 from ICE's own pages, read in a browser:
Dutch TTF futures stop trading "two UK Business Days prior to the first
calendar day of the delivery month", and JKM futures on the 15th of the month
before, or the preceding business day. The study applies both with the bank
holidays of England and Wales, which reproduce every day gov.uk lists and every
last trading day ICE Endex lists for its live contracts.

### 45. Which engines the benchmark ships have, for methane slip

Raised 8 October 2026. **Decided 8 October 2026.**

From 2026 the EU ETS counts methane, and the regulation gives a default slip by
engine class: 3.1 percent of the LNG for a dual fuel medium speed Otto engine,
1.7 percent for a slow speed Otto, 0.2 percent for a slow speed Diesel. Spark
calls its ship "2 Stroke" and its older one "TFDE", which name no class.

Decision: methane slip is off by default, as a toggle. When on, the 174,000 m3
two-stroke is taken as a slow speed Otto engine (1.7 percent) and the 160,000
m3 TFDE as a medium speed Otto engine (3.1 percent), each labelled an
assumption, with the Diesel figure named beside the first.

### 46. The SDR rate, for the Suez toll in dollars

Raised 8 October 2026. **Decided 8 October 2026.**

The Suez Canal Authority's tolls are in special drawing rights. The IMF's daily
rate is read by code only through the Deutsche Bundesbank's copy, which names
the IMF as its source; the Bundesbank's terms exclude third party data from
their permission, and the IMF's own hosts refuse automated requests, even for
robots.txt, so the IMF's terms have not been read. Until a person reads them at
the IMF's copyright and terms page, the rate is kept in `data/private/` and only
the tolls computed from it on the study's dates are shown, each with the rate
used.

Decision: settled on 8 October 2026. The IMF's terms, read in a browser, let
its exchange rate data be copied and published with the IMF credited "whether
obtained directly from the IMF or another party". The series is committed,
read from the Bundesbank, credited to the IMF, and checked against the IMF's
own tables on 41 days.

### 47. MMBtu per tonne of LNG, GIIGNL's table or the IEA's

Raised 7 October 2026. **Decided 7 October 2026.**

The brief asks for GIIGNL's published conversion table. Its annual report could
not be read by code. The study uses 51.56 MMBtu per tonne from the IEA and
Eurostat's Energy Statistics Manual (2004, table A3.9, page 182), within about
one percent of the figure Spark's own conversion factors imply.

Decision: the IEA and Eurostat's figure stands, labelled with its source.
GIIGNL's report, saved by hand into `data/private/`, would let its page be cited
in its place; the owner may do so.

### 48. Which events the History view marks

Raised 9 October 2026. **Decided 9 October 2026.**

The brief lists the events that explain the regimes in the sample and asks
that each have a source before it is shown, and that an event which cannot be
sourced be left out. Several of them rest on S&P Global's or Lloyd's List's
figures, which this study does not request, or on documents not read.

Decision: an event is a row of `lngarb.events` only where one readable document
supports it, with that document's address. The others are listed in the same
module with the reason, and the History view prints that list under the events
table: the 2020 low of JKM and the counts of 2020 and 2021 (S&P Global),
Russia's invasion of Ukraine (no document read), the first Red Sea attacks (no
dated document read), the canals' rebates and auctions (rules, on the Routes
view), China's imports from February 2025 (a statement contradicted by EIA's
table), Hormuz and the jump in charter rates of March 2026 (not read for that
date; Lloyd's List), the IEA's averages, the US and Iran memorandum and the
July hostilities, the June 2026 cargo to China (whether imported or re-exported
is not established), and
Global LNG Hub's note. Each can become a row once its document is read.

### 49. How the site says a figure is missing

Raised 9 October 2026. **Decided 9 October 2026.**

The brief asks for "n/a" with the reason one click away. A bare "n/a" says
neither which figure is missing nor why, and the site's sibling studies print
specific words.

Decision: the site prints words that name the missing figure, "no figure" in a
table cell, "missing for this date" under a calculator field, "no crossing" for
a breakeven hire that does not exist, and gives the reason beside it or in the
sentence under the table. The methodology, section 1, says so.

### 50. Named ranges instead of a range brush

Raised 9 October 2026. **Decided 9 October 2026.**

The brief asks for a range brush on the History view. A brush is hard to work
from a keyboard or a phone, and a range picked by dragging cannot be linked.

Decision: four named ranges, every week, 2021 to 2023, 2024 on and the last 52
weeks, each a button kept in the address (`#/history?range=last_52`), with its
own scales, ticks and sentences computed with the data. The monthly chart shows
every month.

### 51. Tariffs, ships and contract terms in the code, not in seed files

Raised 9 October 2026. **Decided 9 October 2026.**

The brief's layout has seed files for the canal tariffs, the ships and the
contract terms. They live in `src/lngarb/config.py` instead: the Panama and Suez
tariffs as dated tables with the document each comes from, the ships and the
contract terms as parameters with their source, status and the day they were
read, all shown on the Method view. A seed file would hold the same figures
without the types and checks the code gives them; the seeds that are kept are
those written from rows by code (routes, freight anchors, events).

Decision: kept in the code, each figure with its source. The Method view and
the methodology are where a reader finds them.

### 52. No wait at Panama by default

Raised 9 October 2026. **Decided 9 October 2026.**

Panama was open under restrictions from 2023, with waits reported for LNG in
two months (12 days in July 2023, 15 in December 2023) and slots auctioned. No
wait is known for the other months, and a wait is a cargo's choice against
paying for a slot.

Decision: the engine adds no wait and no slot premium unless one is typed; the
Flows view sets the two reported waits against the wait at which Panama stops
netting more than the Cape, and the Model view takes waiting days and a slot
premium per route.

### 53. What the private layer may change

Raised 9 October 2026. **Decided 9 October 2026.**

The brief asks for an importer of settlements and licensed freight the owner
exports himself, never fetched, committed or deployed, and that the site publish
nothing from it but the fact that the comparison was run.

Decision: the importer reads and checks the files and computes, privately, JKM
over TTF for the same contract month day by day. The site publishes nothing from
it, not even the fact that it ran: the committed artifacts are rebuilt on every
machine and checked byte for byte, and a flag present on one machine only would
break that check. The lift test keeps EIA's daily Henry Hub as its proxy for the
settlement on every machine.

### 54. China's tariff on US LNG and the cargoes since

Raised 9 October 2026. **Open.**

Columbia University's Center on Global Energy Policy dates China's tariff on US
LNG from 10 February 2025 at 15 percent, and says no US cargo had reached China
since 6 February 2025, a statement of April 2025 about arrivals. EIA's export
table shows a small volume to China in September 2025 and 4,576 MMcf in June
2026. Reports differ on the rate: one of May 2026 gives 25 percent, those of
July and September 2026 give 15 percent. The Chinese Ministry of
Finance's notice, which would settle the rate, was not read.

What would settle it: the ministry's notice, read by hand, and the owner's
choice of words for the June 2026 cargo, whose end use (imported or re-exported)
is not established. Until then the study uses the date only, as a limit of the
flows test.

### 55. An empty chart

Raised 9 October 2026. **Decided 9 October 2026.**

The brief asks that an empty chart name the missing series and the time of the
failed fetch. A failed fetch keeps the last good cache, marked failed in the
manifest and the Provenance table, and the build refuses to deploy a series
that failed or holds nothing; the weekly refresh commits nothing then and opens
an issue. So no chart of the deployed site can be empty.

Decision: no empty chart state is drawn; the site already live stays as it was,
and Provenance names every series with its status and the time of its last
fetch.

