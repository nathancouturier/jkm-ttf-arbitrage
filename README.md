# JKM-TTF arbitrage study

When does a US Gulf LNG cargo pay to go to Asia instead of Europe? This study prices one cargo loaded at Sabine Pass, sold at Gate against TTF or at Futtsu against JKM by Panama, Suez or the Cape of Good Hope, net of freight, boil-off, canal tolls, carbon and financing, and finds the JKM minus TTF spread at which each route east pays as much as Europe.

**Site:** https://nathancouturier.github.io/jkm-ttf-arbitrage/ · **Two-page note:** [JKM-TTF-Arbitrage-Research-Note.pdf](JKM-TTF-Arbitrage-Research-Note.pdf)

## The finding

<!-- finding:start -->
**Week to 4 November 2026.** JKM is 0.68 USD/MMBtu above TTF. At 31,500 USD a day, the last charter rate reported, a cargo pays to go east above -0.54 via Panama and 0.16 via the Cape, so the arb is open on both routes. A cargo delivered to Northwest Europe sells 1.67 under TTF, which lowers every level by as much.

| Reroute level, USD/MMBtu | Ship paid for | Low, 26,500 | Central, 43,250 | High, 64,750 | Arb closes above |
|---|---|---|---|---|---|
| via Panama | -0.73 | -0.57 | -0.47 | -0.34 | 229,904 USD a day |
| via Suez (closed) | -0.24 | 0.12 | 0.34 | 0.63 | 68,492 USD a day |
| via the Cape | -0.30 | 0.09 | 0.33 | 0.64 | 67,551 USD a day |

Since September 2020 the spread has cleared the level of the cheapest open route in 149 of 288 weeks at the reported charter rate, and in 204 with the ship already paid for. After a month with the arb open, 30 percent of US LNG left for Japan, South Korea, China and Taiwan; after a closed month, 17 percent; since 2022 the gap is 1 point.
<!-- finding:end -->

![Reroute level by route against the charter rate](assets/reroute-levels.png)

## Method in five lines

```
loaded    = capacity x fill x MMBtu per m3                      174,000 m3 x 98.5 percent x 23
delivered = loaded - boil-off a day x round trip days           the boil-off is the ship's fuel
netback   = (DES price x delivered - hire x days - ports - tolls - carbon - financing) / loaded
S*(route) = the JKM minus TTF spread at which netback(Asia, route) = netback(Europe)
H*(route) = the charter rate at which the two netbacks are equal at today's prices
```

Europe's DES price is TTF less the discount ACER assesses for Northwest Europe. Hire runs for the round trip, as in the Spark30S assessment, whose worked example the model reproduces to the dollar. The lift test sets the best netback against 115 percent of Henry Hub. The whole model is [`src/arb/engine.py`](src/arb/engine.py); the browser runs a line-for-line copy, [`site/js/engine.js`](site/js/engine.js), held to it by a fixture test. Every parameter and its source is in [`data/params.json`](data/params.json) and on the site's Method view.

## Run it

```
pip install -r requirements.txt
make            # builds the site's data, runs the tests, writes the note
make serve      # http://localhost:8000/jkm-ttf-arbitrage/
```

Python 3.11 or later, and Node for the one test that runs the browser's engine. `make refresh` fetches the public series; a scheduled workflow does the same every week, each source on its own, and a push to `main` tests, builds and publishes the `site` folder.

## Data and credits

| Series | Source and credit | Kept up to date |
|---|---|---|
| JKM and TTF, weekly averages from September 2020 | U.S. Energy Information Administration, which credits the prices to Bloomberg Finance L.P. | weekly refresh |
| Henry Hub spot, daily | U.S. Energy Information Administration, which credits the price to Refinitiv, an LSEG business | weekly refresh |
| DES LNG assessments, Northwest Europe, from 2023 | European Union Agency for the Cooperation of Energy Regulators (ACER) | by hand |
| Charter rates, Spark30S Atlantic, 135 figures | Spark Commodities, as reported by LNG Prime and by Reuters in gCaptain | weekly when a headline states it |
| US LNG exports, cargo by cargo from 2016 | U.S. Department of Energy | weekly refresh |
| Japan spot LNG price, monthly to March 2021 | Created by processing the information in the Spot LNG Price Statistics (Ministry of Economy, Trade and Industry of Japan) | closed |
| TTF, monthly | The World Bank: Commodity Price Data (The Pink Sheet): Bloomberg Finance L.P.; World Gas Intelligence; Thomson Reuters Datastream; The Wall Street Journal; Official Statistics of Japan; World Bank, CC BY 4.0. The World Bank does not endorse this study | static |
| EU allowance price, monthly | European Commission auction reports, CC BY 4.0; Source: EEX, DEHSt, CC BY-NC-ND 4.0, the monthly averages reproduced unchanged | by hand |
| Dollars per euro; SOFR; dollars per SDR | Board of Governors of the Federal Reserve System, H.10; Federal Reserve Bank of New York; International Monetary Fund, through the Deutsche Bundesbank | weekly refresh |
| Canal tariffs, traffic and advisories | Panama Canal Authority; Suez Canal Authority | by hand |
| Routes and map | searoute (Apache License 2.0) over Eurostat's SeaRoute network (EUPL 1.2); Natural Earth, public domain, through world-atlas (ISC) | fixed |

Platts' counts and assessments are quoted from the publications that republished them. Typefaces: Fraunces, Figtree, JetBrains Mono and Liberation Serif, under the SIL Open Font License. Charts: D3 (ISC). Code under the MIT licence; other publishers' data keep their terms, set out in [`NOTICE`](NOTICE).

## Limits

- The charter rate is one published assessment, held between reports; a real fixture differs, and the zero case stands for a ship already on term charter.
- Europe's DES discount is ACER's assessment averaged over 20 days; before 2023 it is an assumption.
- Panama is priced at the tariff with a booked slot. Auctioned slots cost more and their price is not published.
- Prices are weekly averages of front months. Before October 2020 the JKM series is METI's price of spot cargoes for Japan, a proxy.
- Flows show association, not cause, and nothing here is a forecast or a trading signal.
