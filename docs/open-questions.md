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
