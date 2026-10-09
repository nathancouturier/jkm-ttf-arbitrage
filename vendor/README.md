# Vendored typefaces

Three variable fonts and their licences, pinned as bytes in this repository.
The site makes no request to any third party, so nothing is loaded from a font
service. There is no chart library here: the charts are SVG drawn by
`src/charts.js`.

The stylesheet loads each file with a path relative to itself,
`../vendor/...` from `styles/tokens.css`, and `index.html` preloads two of them
with `vendor/...`. The site is served from
`https://nathancouturier.github.io/jkm-ttf-arbitrage/`, a subpath, so a leading
slash in any of those URLs would break it; `tools/check-paths.mjs` fails on one.

## Where the bytes came from

Copied byte for byte on 2026-10-09 from the sibling repository
`crack-spread-study`, which copied them from `lme-comex-arbitrage-model`, whose
`vendor/README.md` records the original fetch of Google Fonts' own `latin`
cuts with the upstream URLs. Nothing was subset, converted or renamed. The same
bytes in the three repositories means the sites draw the same letters.

| Path | Bytes | sha256 |
|---|---|---|
| `fraunces/fraunces.v1.000.latin.woff2` | 67,304 | `7234ed860a9cc83045413c4faee63c960a8f2d1917adcf728119307d56e0d783` |
| `fraunces/LICENSE` | 4,391 | `bdf4c22802eaf804f998195871c6b8938aac2ac14b2d78a8bd66a6f1eced833b` |
| `jetbrains-mono/jetbrains-mono.v2.211.latin.woff2` | 40,404 | `18be452724bfdc236c074ca94a249a7f41a86752c7d04ab258ce9ed5651f6a7e` |
| `jetbrains-mono/LICENSE` | 4,399 | `b2fe5e8987594e9ffd1d2ca52a2f5d73eb8335243893c5d6254b5ad69269591d` |
| `figtree/figtree.v2.002.latin.woff2` | 20,156 | `4ba7d3d096695818fe0686be4f1e82c6b05134e18a22260336130335027462dd` |
| `figtree/LICENSE` | 4,388 | `140d37233e7f3ce7313798befa9600893bcceaf41a55fa0fa5ad52f7f657a268` |

To check again: `sha256sum vendor/*/*`.

| Face | Version | Licence | Upstream |
|---|---|---|---|
| Fraunces | 1.000 | SIL Open Font License 1.1, copyright 2018 The Fraunces Project Authors | `https://github.com/undercasetype/Fraunces` |
| JetBrains Mono | 2.211 | SIL Open Font License 1.1, copyright 2020 The JetBrains Mono Project Authors | `https://github.com/JetBrains/JetBrainsMono` |
| Figtree | 2.002 | SIL Open Font License 1.1, copyright 2022 The Figtree Project Authors | `https://github.com/erikdkennedy/figtree` |

The OFL allows bundling and redistribution with software provided the licence
travels with the font, which is why each `LICENSE` sits beside its file.

## Roles

| Face | Used for | Weights set in CSS |
|---|---|---|
| Fraunces | the verdict and view titles | 400 verdict, 500 view titles |
| Figtree | every word, and figures inside a sentence | 400, 500, 600 |
| JetBrains Mono | figures in table cells and tick values on axes, nothing else | 400, 600 for totals |

## Traps in the files themselves

1. Fraunces' default instance is Black 900 at optical size 9, so every rule
   that names it sets `font-weight`, and `font-variation-settings` is never
   written (it would override the weight).
2. Fraunces has no `tnum` and lacks the up and down arrows.
3. Figtree's default instance is Light 300 with proportional digits: the body
   sets weight 400, and every element that can hold a figure sets
   `font-variant-numeric: tabular-nums lining-nums`.
4. None of the three carries the sun or moon of the theme toggle, or U+FE0E;
   the toggle uses the system face and follows each glyph with U+FE0E so no
   platform draws it as a colour emoji.
5. The cuts are `latin` only: place names are written without macrons
   (Futtsu, not with a long u).

## Figtree stands in for Satoshi

The portfolio sets body text in Satoshi, distributed under the ITF Free Font
License, which forbids making the font available through a repository or a
publicly accessible server; the portfolio loads it from Fontshare, and this site
loads nothing from a third party. Figtree is the openly licensed face the LME
sibling measured as closest to Satoshi at weight 400 (its `vendor/README.md`
holds the measurements). In CSS, `--ff-body` is redefined once, directly after
the portfolio's token block in `styles/tokens.css`.
