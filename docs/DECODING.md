# Decoding the game's data files

Where the gameplay facts on this site come from, and how each was verified.

This lives here rather than in `data/site_template.html` for two reasons. It is
documentation of *research*, not of *code* — the template's job is to explain the
code a maintainer is reading. And the template is inlined verbatim into
`site/index.html`, so every paragraph here was previously downloaded by every
visitor to the site.

Everything below was derived from the game's own files using our own parsers. No
game code, artwork, or narrative text is reproduced. See `ATTRIBUTION.md`.

## Sources

| File type | Provides |
|---|---|
| `.SET` (gameset) | `ITEM`, `ITEMCLAS`, `METHOD`, `FARMCROP` tables — the product catalogue, classifications, recipes and crop data behind `data/index_cards.json` |
| `.SCN` (scenario/save) | Scenario goals: duration, bonus, sale restrictions, domination targets |
| `.SCT` | The scenario's human-readable goal prose, used only as an independent check against the decoded bytes |

> **There is no extractor, and there never was one.** `data/index_cards.json` was
> not produced by a script. The formats were reverse-engineered by inspecting
> `.SET` and `.SCN` files directly, and the dataset was assembled by hand.
>
> What exists instead is a **verifier**: `tools/verify_against_game.py` reads a
> real copy of the game and checks the committed data against it, field by field.
> It never writes to `data/`. Capitalism Plus is a 1996 DOS title whose content
> will not change, so a disagreement means our data is wrong rather than that the
> game moved — which is what makes verification the useful direction.
>
> Current result against a retail copy: **1,598 checks pass, 0 fail**, with one
> declared divergence (see below). Run it with
> `python3 tools/verify_against_game.py --game-dir /path/to/game`, or set
> `CAPITALISM_GAME_DIR` and the test suite will pick it up and skip cleanly
> without it.

## Method

Nothing here was decoded by running a parser over the files. The work was done by
reading bytes in a hex editor, forming a hypothesis about a field, and then
checking it against something independent — the `.SCT` goal prose, a second save
file, or the game's own behaviour under DOSBox. Where a hypothesis survived every
check it is recorded below; where one failed, the counterexample that killed it
is recorded too (see [Falsified hypotheses](#falsified-hypotheses)).

Five binary grammars now live in [`formats/`](formats/), in
[Synalyze It! / Hexinator](https://www.synalysis.net/) format — four written
during the original work and one added since. They are the closest thing to a
specification this project has; see [`formats/README.md`](formats/README.md) for
what each covers and how far each is verified:

| Grammar | Describes |
|---|---|
| Capitalism Plus SET | The `.SET` table format: file descriptors, table headers, column headers, per-column types (number vs non-number, with decimal places), and row data |
| Capitalism Database | The generic container the games use for bundled data files |
| Capitalism Palette | The colour palette format |
| Capitalism Icon Image | The raster format the product icons are stored in |

The `.SET` grammar is the important one for reproducing `index_cards.json`: it
describes a self-describing table structure, so an extractor reads the column
definitions rather than hard-coding offsets. `ITEM`, `ITEMCLAS`, `METHOD` and
`FARMCROP` are tables in that format.

The `.SCN` offsets in the next section were found separately and by hand; they
are not covered by a grammar.

## The product dataset

Every field in `data/index_cards.json`, and where it comes from. All of this is
checked by `tools/verify_against_game.py`.

The three gamesets are three `.SET` files in `GAMESET/`: `1STD.SET` (Standard),
`2ALTER.SET` (Alternative), `3FOOD.SET` (Food & Beverage). Each holds 16 tables;
six matter here.

| Field | Source | Notes |
|---|---|---|
| `name` | `ITEM.NAME` | |
| `raw_class` | `ITEM.CLASS` | the game's own class code |
| `category` | `ITEMCLAS.NAME` | five renames, below |
| `sale_index` | `ITEM.SALEINDEX` | |
| `sellable` | `ITEM.SALEINDEX > 0` | not a stored flag |
| `output_quantity` | `METHOD.OQTY` | absent where there is no recipe |
| `output_unit` | `ITEM.UNIT` | see the divergence below |
| `inputs` | `METHOD.INPUT1–5`, `IQTY`, `IQUA` | `IQUA` is `quality_pct` |
| `livestock_yields` | `FARMLIVE.PRODUCT1–3` | three slots, hence never more than three |
| `derived_from_livestock` | inverse of the above | |
| `growing_conditions` | `FARMCROP.TEMP`, `RAIN`, `SOW`, `HARVEST` | enums below |
| `used_in` | inverse of `inputs` | |
| `production_technology_pct` | `100 − Σ inputs[].quality_pct` | see [Derived fields](#derived-fields) |
| `classification`, `industry` | our own grouping of `raw_class` | see below |
| `icon_image_id`, `graphic_count` | **unknown** | see below |

**`METHOD` has exactly five input slots.** That is why no recipe in the game has
more than five ingredients — a structural limit, not a coincidence of the data.

### Enumerations

`FARMCROP.RAIN`: `1` = Little, `2` = Moderate, `3` = Plentiful.

`FARMCROP.TEMP`: `2` = Cool, `3` = Warm, `4` = Hot, `9` = "Warm, Cool, or Cold".
Only those four values occur across all three gamesets. **`9` is not a bitmask**
under any assignment we have tried — it behaves as a "tolerant" special case. The
verifier reports an unrecognised value rather than guessing.

`FARMCROP.SOW` / `HARVEST`: month number, 1–12.

### Editorial decisions, not game data

Three places where the dataset deliberately departs from the file. All three were
invisible until the verifier forced them to be named.

1. **Blank `ITEM.UNIT` becomes `"unit"`** — most manufactured goods have no unit
   string in the file.
2. **Five class names are pluralised for display:** `Apparel, Footwear & Bag` →
   `… Bags`, `Cigarette` → `Cigarettes`, `Computer` → `Computers`, `Toy` →
   `Toys`, `Watch` → `Watches`. Every other class name is used verbatim.
3. **`CLASS=PLANT` rows are excluded.** `ITEM` holds 84 rows for Standard where
   the dataset has 82 products: the extras are *Rubber Plant* and *Sugar Cane*,
   the growing plant as distinct from the harvested crop.

`classification` (7 values) and `industry` (3 values) are **our groupings** of the
32 `raw_class` codes, not fields in the file. Both are unambiguous functions of
`raw_class` with no conflicts, so they are reproducible — but they are our
taxonomy, and `classification_source` in the dataset should be read that way.

### Known divergence: units vs quantities

`output_unit` is null in the dataset for the 73 products with no `METHOD` recipe —
raw materials, crops and livestock — because the dataset treats the field as the
unit of a production *run*. There is no run for these: a mine or a farm produces
at a rate, not in batches.

**The unit itself is not ambiguous.** Each commodity has exactly one unit, and
`ITEM.UNIT` agrees with the unit that commodity carries in every recipe that
consumes it — verified across all three gamesets, 0 disagreements. Gold is `oz`
whether it comes out of a mine or goes into Jewelry. So the dataset is missing a
unit it *could* state; the genuinely undefined thing is the quantity.

Where the rate lives instead, none of it a per-batch yield:

| Kind | Table | Fields |
|---|---|---|
| Mining / extraction | `RAW` | `SPEED`, `RES_VALUE`, `MAX_SITE`, and `FIRM_CODE` naming the unit (`MINE`, `FORE`, `OIL`) |
| Livestock products | `FARMPROD` | `MONTH_QTY` with a `SMONTH`–`EMONTH` window |
| Crops | `FARMCROP` | the sow/harvest window only |

`FARMPROD` distinguishes two ways a livestock good arrives, and the site now
surfaces both (see [Production rates](#production-rates)).

> **Correction.** An earlier version of this document said `KILLFLAG` marks the
> slaughter products, having observed it set on every row. That observation was
> an artefact of a bug in our own reader: logical columns store ASCII `'T'`/`'F'`,
> and testing for a non-zero byte decodes `'F'` as true, so *every* boolean in
> every table read as set. With that fixed, `KILLFLAG` does exactly what the name
> suggests, and the conclusion happens to be the one originally stated — but it
> was not supported by the evidence at the time.

The verifier declares and counts this divergence rather than tolerating it, so a
new disagreement cannot hide inside it, and it separately asserts the
one-unit-per-commodity property that makes the above true.

### Production rates

Added to the dataset by `tools/augment_from_game.py` and checked by the verifier.
The game's own Farmer's Guide and manuals publish **none** of this — a player has
to establish it by experiment, which is exactly why a reference should carry it.

`extraction`, from `RAW`, on raw materials: which site type works it
(`FIRM_CODE` → Mine / Lumber Mill / Oil Well), the commodity's unit, relative
speed, resource value, and how many sites a map may hold.

**There is no units-per-month figure for extraction, and no table supplies one.**
This is an asymmetry in the game's data rather than a gap in our reading:
`FARMPROD` carries both `SPEED` and `MONTH_QTY`, so a livestock yield can be
stated absolutely ("9 lb per month"), while `RAW` carries `SPEED` alone. All 16
tables were checked. `RAW.SPEED` is also on a different scale from
`FARMPROD.SPEED` — 1, 2 and 4 rather than percentages around 100 — so it has no
absolute anchor at all, and the site states it against the other materials in the
same gameset rather than against a baseline we would have had to invent.

`MAX_SITE` describes the **gameset**, not the game being played, so the product
page scopes it to "an unrestricted game" when the material is restricted.

Raw materials are never excluded by class — `RAW` appears in no scenario's
`excludedClasses` — but they are restricted *transitively* when every downstream
consumer dies: Gold under Italy loses Jewelry, its only consumer. Mechanically a
restricted raw material behaves like restricted livestock: a site could still be
worked, and the Sales Unit would refuse to connect. In practice the distinction
is moot, since a scenario will not offer an extraction site for a resource
nothing can use. Either way the map contents live in the `.SCN` data, which we
have not decoded, so the page scopes the figure rather than asserting anything
about a particular map.

`livestock_production`, from `FARMPROD`, on livestock-derived goods. Two modes,
never both:

- **continuous** — a monthly quantity within a season. Milk 555 quart/month all
  year, Wool 9 lb/month but only June–October, Eggs 1.7 dozen/month.
- **slaughter** — a percentage of the animal's weight. Meat is 100%, Leather 20%,
  Tallow 100%.

`KILLFLAG`, `P_PERCENT > 0` and `MONTH_QTY == 0` agree on all 25 rows across all
three gamesets, so the mode is unambiguous. The verifier asserts that agreement
as well as the values.

`livestock_stats`, from `FARMLIVE`, on the animals: weight, growth and
reproduction rates. Weight is what makes the slaughter percentages concrete —
Cattle at 675 lb gives 675 lb of Frozen Beef and 135 lb of Leather.

### Still unresolved

The dataset's `icon_image_id` and `graphic_count` match nothing in the files (see
[Graphics](#graphics) below), so both came out of the icon-extraction process
rather than the game data.

Roughly 36 of the 64 header bytes per table remain unexplained (`<type?>`,
`<unused>`), which does not matter for reading the tables.

## Graphics

The artwork is split across several files, which is why there are separate raster
and palette grammars. Verified against `1STD.*`:

| File | Contents |
|---|---|
| `GAMESET/*.II` | 84 records × 3608 bytes: `u32 length` (3604) + `u16 W` + `u16 H` + `W×H` bytes. **60 × 60**, 8-bit palette-indexed, one per `ITEM` row |
| `GAMESET/*.II2` | 84 named entries: a `.SET`-style descriptor block (9-byte name + `u32` offset) then `u16 W` + `u16 H` + `W×H`. **120 × 120** — the size of the extracted PNGs, so this is where they came from, not an upscale of `.II` |
| `GAMESET/*.PIC` | a single bare raster, `u16 W` + `u16 H` + data: 464 × 63 |
| `RESOURCE/PAL_STD.RES` | the 256-colour palette: `u32 file size` (776) + 4 unknown + 256 × RGB |

So the two header shapes differ: `.II` records carry a length prefix, while
`.II2` entries and `.PIC` start straight at `W, H`.

Two corrections to earlier assumptions:

- **`.PLA` / `.PLP` / `.PLO` are not palettes**, despite the names. They begin
  `0a 00` then four-character tags (`RETA`, `FACT`), i.e. a small table of ten
  entries in some other container. The Palette grammar describes
  `RESOURCE/PAL_STD.RES`, which it matches exactly.
- **`ITEM.ICONPTR` indexes `.II`, not `.II2`.** It is a byte offset with the
  3608-byte stride (Car = 18040 = record 5). The dataset's `icon_image_id` for
  Car is 10, and Car is entry 6 in `.II2`, so `icon_image_id` corresponds to
  neither — it is extraction-tool numbering.

`.II2` entry names are **DOS 8.3 filenames**, matching `ITEM.FILENAME` — which is
why the numeric suffixes (`MILK-6`, `CAR-9`, `ALUMIN-1`) correlate with nothing:
they are part of the filename, not a frame count. Matching on `ITEM.FILENAME`
resolves every product in every gameset, with one exception: Alternative's Apple
carries `FILENAME` `APPLERAW` while its entry is `APPLE`, so `ITEM.CODE` serves as
a fallback.

`tools/extract_icons.py` uses exactly this to rebuild `site/images/` from a local
copy of the game, reproducing the original PNGs pixel for pixel.

Six crops have a separate `PLANT` row with its own artwork, linked by
`FARMCROP.PLANT_CODE` —

| Crop | Plant |
|---|---|
| Rubber | Rubber Plant |
| Sugar | Sugar Cane |
| Coconut | Palm |
| Coffee | Coffee Plant |
| Flax Fiber | Flax |
| Tea | Tea Plant |

— and all six pairs are genuinely different images.

**The game shows both.** Its Farmer's Guide displays the plant and the harvested
crop side by side (Flax: the spiky plant, then the golden fibre), and lists crops
under the *plant's* name — "Flax", "Palm" — while its Manufacturer's Guide shows
the product alone. So the extractor writes both, 251 files rather than 245, and the
site follows the same split: both images in the Farmer's Almanac and on the crop's
own page, product alone in the grid and the dependency views.

`PLANT` rows are not products and stay out of the dataset as products; the plant
rides along on its crop as a `plant` field. The original extraction wrote one image
per product and chose the plant for four of the six but the commodity for the other
two, which was an inconsistency rather than a rule.

None of this is needed to build the site, which is designed to work without
artwork entirely — see `ATTRIBUTION.md`. It is recorded for completeness, and
because knowing the format is separate from having the right to redistribute
what it contains.

## Scenario byte offsets (`.SCN`)

All verified against fresh byte reads of all 20 `.SCN` files, not just the
scenarios used during discovery.

The scenarios are specially-built save games, and they ship **on the CD image**
(`CapPlus.gog`) rather than in the installed directory — `SCENARIO/*.SCN` with a
`.SCT` prose file beside each. The verifier reads them straight out of the ISO9660
image without mounting it.

`tools/verify_against_game.py` checks all five fields below for all 20 scenarios:
**100 checks, 0 failures.** Note that the class-code comparisons implicitly verify
each scenario's gameset too: the flag arrays are one byte per row of *that
gameset's* `ITEMCLAS` table, so a wrong gameset would decode to the wrong codes.

| Offset | Field | Layout |
|---|---|---|
| 179 | `years` | Scenario duration |
| 183 | `bonus` | Starting bonus |
| 305–308 | `dominateIndustries` | 4 bytes, one per industry, `1` = must dominate |
| 315 | `excludedClasses` | One byte per `ITEMCLAS` row, in table order; `1` = allowed, `0` = excluded |
| 415 | `dominateClasses` | Same layout as 315, exactly 100 bytes later; `1` = must dominate this market to win |

`years` and `bonus` match the `.SCT` prose exactly. The two flag arrays and the
industry array were each solved rather than assumed; the reasoning follows.

### `excludedClasses` (offset 315)

Cross-checked against all 20 scenarios' `.SCT` text with zero mismatches, then
confirmed live in-game. Building a Cattle farm under Rule Britannia — which
excludes `LPRODUCT` and `FOOD`, but not `LSEMI` — produced:

- **Frozen Beef** (`LPRODUCT`): directly blocked, Sales unit never connects.
- **Milk** (`LSEMI`): not itself excluded, but its only buyers (Cheese, Yogurt)
  are category Food, which *is* excluded — so no legal market anywhere.
- **Tallow** (also `LSEMI`): sold fine, because its buyer Soap is category
  Chemical Products, which is not excluded.

This is the observation behind the two-mechanism model in the next section: a
product can be unsellable either directly, by its own class, or indirectly, by
having every downstream buyer stranded.

### `dominateClasses` (offset 415)

Verified against every scenario whose `.SCT` goal names specific categories, with
zero mismatches:

| Scenario | Decoded array | Goal prose |
|---|---|---|
| `TECHNO` | Automobile, Chemical Products, Computers, Electronic Products, Toys, Watches | lists exactly those six |
| `FORTIFY` | Beverage | "leading the beverage market" |
| `UNDER` | Food, Canned Food, Snacks | — |
| `VOGUE` | Apparel, Cosmetics, Jewelry, Optical Products | — |
| `DRAGON` | Chemical Products, Electronic Products | — |
| `GLOBAL` | every sellable Standard category | "market dominance in every market" |

Scenarios whose goal is phrased at the *industry* level instead ("dominate
manufacturing and retail") decode to an **empty** array here. That is consistent
rather than a gap: industry-level domination is not a per-category concept and
lives in its own array.

### `dominateIndustries` (offsets 305–308)

Found by comparing two DOSBox saves: `SCENARIO_SPAIN`, and a custom `UTGAME1`
game built by hand with the same Manufacturing + Farming goal enabled. Both
showed identical bytes `[0,1,1,0]` at 305–308, while a save with no industry goal
(`TECHNO`) and an earlier state of the custom game before its goal was set both
showed `[0,0,0,0]` — an independently reproduced signal.

**The byte order is reversed relative to the display convention used elsewhere on
this site:**

| Offset | Industry |
|---|---|
| 305 | Retailing |
| 306 | Manufacturing |
| 307 | Farming |
| 308 | Raw Material Production |

That mapping was solved, not assumed, by cross-checking all seven industry-goal
scenarios' prose simultaneously. `BERLIN` has a single flagged byte at index 1,
isolating Manufacturing on its own ("dominate the manufacturing sector"), which
anchors every other scenario with zero contradictions:

| Scenario | Decoded | Goal prose |
|---|---|---|
| `ASIAN`, `ITALY` | Manufacturing, Retailing | "manufacturing and retail sectors" |
| `SPAIN` | Manufacturing, Farming | "manufacturing… retaining leadership in farming" |
| `UK` | Manufacturing, Raw Material Production | "mining and manufacturing sectors" (mining = Raw Material Production) |
| `VERTICAL` | Farming, Manufacturing, Retailing | "farming, manufacturing, and retail industries" |
| `GLOBAL` | all four | "dominance in every single market" |

`GLOBAL` is the only scenario with both arrays populated (15 per-class codes *and*
all four industries), since "everything" is expressible either way. The UI prefers
the industry list there to avoid a redundant 19-item display.

`BRINK`, `DILEMMA`, `ENTREPRE`, `JAPAN`, `LATECOME`, `RACETIME` and `ROUGH` have
no domination goal in their prose, and all three arrays are correctly empty.

## The sale-restriction model

A scenario's `excluded` flag on a class governs whether a product can be produced
**and** sold — but only when that product is **terminal**, i.e. nothing else in
the game is made from it.

1. **A terminal product in an excluded class cannot be produced (by a regular
   Factory) or sold at all.** Under Vertical Integration (excludes Spice,
   Beverage, Pasta), a Manufacturing Unit with Flour and Black Pepper linked only
   ever offered Bread and Hamburger Bun — Instant Noodles (Pasta, terminal) never
   appeared as a buildable option.

2. **Livestock-derived products are the exception to production being blocked.**
   A product with `raw_class` `LPRODUCT` or `LSEMI` comes from a Raising +
   Processing Unit rather than a Factory recipe, and *can* still be produced when
   excluded and terminal — but its Sales Unit refuses to connect, so it still
   cannot be sold. Confirmed with Frozen Beef (`LPRODUCT`, terminal) under Rule
   Britannia.

3. **A non-terminal product is never blocked by its own class.** It loses its
   market only if every downstream product is itself dead, transitively.
   Confirmed two ways: Milk under Rule Britannia has no market because Cheese and
   Yogurt are both Food (terminal, excluded), while Tallow sells fine because Soap
   is Chemical Products; and Black Pepper (Spice, excluded) under Vertical
   Integration manufactures and sells fine at a live Department Store precisely
   because it has downstream consumers (Kebab, TV Dinner, Instant Noodles) on top
   of its own retail listing.

The code implements exactly these three rules as two checks — `cannotProduce`
and the transitive `scenarioHasMarket` — in `data/site_template.html`.

### Falsified hypotheses

Recorded because each is a plausible-looking simplification that the data
disproves. Anyone tempted to collapse the model should read these first.

**"Apply the excluded-class check to every product regardless of downstream
use."** Wrong. It flags Black Pepper — and transitively Pepper — as unsellable,
when both demonstrably sell under Vertical Integration. Rule 3 exists for this.

**"A product whose recipe uses any excluded-class ingredient cannot be
manufactured."** Wrong, and specifically disproved by Leather Shoes (`WEAR`, not
excluded), which uses Rubber (Plant Product, excluded under The Emerging Dragon)
and is plainly manufacturable in-game. This hypothesis was invented to explain
Instant Noodles vanishing from the Mft dialog; the real explanation needs no
second mechanism, because Instant Noodles' own category (Pasta) is excluded *and*
it is terminal, which rule 1 already covers once the terminal block is understood
to prevent production rather than only sale.

## Derived fields

`production_technology_pct` is computed as `100 - sum(input quality_pct)` during
the dataset rebuild, not read from a separate field. An earlier pipeline took it
from a prior-art dataset that had drifted for 5 of 245 products — Black Pepper
was recorded there as 50%, while the game's own Manufacturer's Guide screen shows
75%, i.e. `100 - 25`. Every product's bar therefore sums to 100% at the source,
which is why the site's scale factor is a defensive no-op rather than a real
correction.
