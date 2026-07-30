# capitalism-plus-reference

A modernized, searchable web reference for **Capitalism Plus** (1996) — the
DOS-era business simulation from Enlight Software — covering all three
gamesets' products, dependency chains, farming data, and scenario goals.
Meant to be kept open in a browser tab alongside the game itself.

Every gameplay fact on the site (sale restrictions, scenario domination
goals, production chains) is decoded directly from the game's own `.SET` /
`.SCN` save-file formats, not guessed from memory or secondary sources — see
the commentary in `data/site_template.html` for the byte-level methodology
and verification evidence behind each mechanic.

## Layout

```
site/
  index.html      the actual reference site — open this in a browser
  d3.min.js       D3.js v7 (BSD-licensed), used for the dependency graph
  images/         product icons — NOT committed, see ATTRIBUTION.md
data/
  site_template.html    site source: all HTML/CSS/JS, with one placeholder
                        (__PRODUCTS_JSON__) for the product data
  index_cards.json      canonical product dataset, rebuilt from the game's
                        own .SET files (ITEM/ITEMCLAS/METHOD/FARMCROP/etc.)
  index_cards.csv        same data, flat/spreadsheet form
  classification_legend.json   raw ITEMCLAS code -> display name mapping
  scenarios.json / .py         scenario goal data (years, bonus, sale
                        restrictions, domination targets) and the decode
                        script used to derive it from .SCN files
tools/
  build_site.py   regenerates site/index.html from the template + dataset
```

## Build

```sh
python3 tools/build_site.py
```

This is the only build step — `site/index.html` is otherwise hand-authored
in `data/site_template.html`. Open `site/index.html` directly in a browser
to use the site (no server required).

Product icons are not included in this repository (see below) — the site
will run and remain fully functional without them, just without artwork.

## Product icons

The 245 product icons are extracted from the game's own compiled raster
assets and are **not committed here**, pending resolution of the fair-use /
attribution question described in `ATTRIBUTION.md`. If you have a legitimate
copy of Capitalism Plus, drop the corresponding PNGs into `site/images/`
(named `<Gameset>_<ProductName>.png`, matching `icon_file` in
`index_cards.json`) to populate them locally.

## Status

Feature-complete for personal use: Grid/List/Cards views, a Farmer's Almanac,
an interactive dependency graph, and scenario-goal filtering (including
domination targets, byte-decoded from real save files) across all three
gamesets. Not yet published — see `ATTRIBUTION.md` for the open question
blocking public hosting.
