# Where each fixture comes from

Every file in this folder is a publisher's own bytes, kept exactly as served so
that the parsers are tested on what the sources really publish, with no
network. None of them is covered by this repository's MIT licence: each stays
under its publisher's terms, quoted in `docs/sources.md`. Times are UTC.

| File | Publisher | Read from | Fetched | Terms |
|---|---|---|---|---|
| `acer_correction_notice_2024-12-20.pdf` | ACER | `https://www.acer.europa.eu/sites/default/files/documents/en/Gas/LNG_Price_Assessment/LNGPA_Correction_Notice_20241220.pdf` | 2026-09-30 20:45:33 | ACER's legal notice, `docs/sources.md` 2.7 |
| `acer_methodology_1.1.pdf` | ACER | `https://www.acer.europa.eu/sites/default/files/documents/en/Gas/LNG_Price_Assessment/ACER_LNG_price_assessment_and_benchmark_methodology_1.1.pdf` | 2026-09-30 20:44:57 | ACER's legal notice, 2.7; the document prints "Reproduction is authorised provided the source is acknowledged." |
| `ec_cap_report_202506.pdf` | European Commission | `https://climate.ec.europa.eu/document/download/761233e2-0bce-4e7e-850b-3f38d84b87db_en?filename=cap_report_202506_en.pdf` | 2026-09-30 21:07:38 | CC BY 4.0, 2.8 |
| `eia_exports_release_2026-04-30_wayback.xls` | U.S. Energy Information Administration, release of 30 April 2026 | the Internet Archive's capture of 5 May 2026, `https://web.archive.org/web/20260505012847id_/https://www.eia.gov/dnav/ng/xls/ng_move_expc_s1_m.xls` | 2026-09-30 12:02:26 | US public domain, 2.1 |
| `eia_exports_release_2026-08-31.xls` | U.S. Energy Information Administration, release of 31 August 2026 | `https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls` | 2026-09-30 11:53:09 | US public domain, 2.1 |
| `eia_henry_hub_release_2026-09-23.xls` | U.S. Energy Information Administration, prices credited to Refinitiv | `https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls` | 2026-09-30 11:59:08 | US public domain, with the doubt on third party figures in 2.1 |
| `eia_ngwu_archive_index_2026-09-30.html` | U.S. Energy Information Administration | `https://www.eia.gov/naturalgas/weekly/includes/archive.php` | 2026-09-30 11:31:54 | US public domain, 2.1 |
| `eia_ngwu_final_issue_2026-01-22.html` | U.S. Energy Information Administration, prices credited to Bloomberg Finance L.P. | `https://www.eia.gov/naturalgas/weekly/` | 2026-09-30 11:30:37 | US public domain, with the doubt on third party figures in 2.1 |
| `eia_robots_2026-09-30.txt` | U.S. Energy Information Administration | `https://www.eia.gov/robots.txt` | 2026-09-30 11:30:26 | US public domain, 2.1 |
| `eia_wngsr_bullets_lng_2_2026-09-24.html` | U.S. Energy Information Administration, prices credited to Bloomberg Finance L.P. | `https://www.eia.gov/naturalgas/weekly/supplement/content/bullets_lng_2.html` | 2026-09-30 11:37:16 | US public domain, with the doubt on third party figures in 2.1 |
| `eia_wngsr_release_dates_2026-09-24.json` | U.S. Energy Information Administration | `https://www.eia.gov/naturalgas/weekly/supplement/content/release_dates.json` | 2026-09-30 11:37:04 | US public domain, 2.1 |
| `eia_wngsr_source_lng_2_2026-09-24.html` | U.S. Energy Information Administration | `https://www.eia.gov/naturalgas/weekly/supplement/content/source_lng_2.html` | 2026-09-30 11:37:26 | US public domain, 2.1 |
| `h10_release_2026-09-28.zip` | Board of Governors of the Federal Reserve System | `https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip` | 2026-09-30 15:54:50 | US public domain, 2.3 |
| `meti_historical_data_e.xlsx` | Ministry of Economy, Trade and Industry of Japan | `https://www.meti.go.jp/english/statistics/sho/slng/historical-data-e.xlsx` | 2026-09-30 16:56:44 | METI's terms of use, compatible with CC BY 4.0, 2.5 |
| `nyfed_sofr_2018-01-01_to_2026-09-30.json` | Federal Reserve Bank of New York | `https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate=2018-01-01&endDate=2026-09-30` | 2026-09-30 15:58:59 | the New York Fed's Terms of Use, 2.4, and the notice in `NOTICE` |
| `worldbank_commodity_markets_2026-09-30.html` | The World Bank | `https://www.worldbank.org/en/research/commodity-markets` | 2026-09-30 12:34:25 | a page of the World Bank's site, under its general terms of use, not its dataset terms, 2.2 |
| `worldbank_monthly_release_2026-07-02_wayback.xlsx` | The World Bank, release of 2 July 2026 | the Internet Archive's capture of 10 July 2026, `https://web.archive.org/web/20260710070435id_/https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx` | 2026-09-30 12:41:25 | CC BY 4.0, 2.2 |
| `worldbank_monthly_release_2026-09-02.xlsx` | The World Bank, release of 2 September 2026 | `https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx` | 2026-09-30 12:35:30 | CC BY 4.0, 2.2 |

The H.10 package was also served, byte for byte the same, by the Board's Data
Download Program at the same date. JOGMEC's pages are not here: its terms do
not permit republishing them, so the JOGMEC parser is tested on pages built
inside its test file.
