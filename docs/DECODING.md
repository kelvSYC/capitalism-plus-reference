# Decoding the game's data files

Where the gameplay facts on this site come from, and how each was verified.

This lives here rather than in `data/site_template.html` for two reasons. It is
documentation of *research*, not of *code* — the template's job is to explain the
code a maintainer is reading. And the template is inlined verbatim into
`site/index.html`: anything written there is downloaded by every visitor to the
site.

Everything below was derived from the game's own files using our own parsers. No
game code, artwork, or narrative text is reproduced. See `ATTRIBUTION.md`.

## Sources

| File type | Provides |
|---|---|
| `.SET` (gameset) | `ITEM`, `ITEMCLAS`, `METHOD`, `FARMCROP` tables — the product catalogue, classifications, recipes and crop data behind `data/index_cards.json` |
| `.SCN` (scenario/save) | Scenario goals: duration, bonus, sale restrictions, domination targets |
| `.SCT` | The scenario's human-readable goal prose, used only as an independent check against the decoded bytes |

> **How reproducible this is, precisely.** Every field in
> `data/index_cards.json` is either **read from the game by a committed tool** or
> **derived by a documented rule that a test asserts** — see the table below.
> `tools/verify_against_game.py` implements the `.SET` container and checks the
> data against a retail copy: **2,020 checks, 0 failures, no tolerated
> divergences.** `tools/augment_from_game.py` writes five of the fields outright,
> and `tools/extract_icons.py` reproduces the artwork.
>
> What does not exist is a single command that regenerates the whole file from
> nothing. That is a mechanical gap rather than a research one: the reader, the
> field mapping and every derivation rule are committed and exercised. Nothing
> about the format remains to be discovered.
>
> Run the verifier with
> `python3 tools/verify_against_game.py --game-dir /path/to/game`, or set
> `CAPITALISM_GAME_DIR` and the test suite picks it up, skipping cleanly without
> it.

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
| `output_unit` | `ITEM.UNIT` | blank in the file becomes `"unit"` |
| `inputs` | `METHOD.INPUT1–5`, `IQTY`, `IQUA` | `IQUA` is `quality_pct` |
| `livestock_yields` | `FARMLIVE.PRODUCT1–3` | three slots, hence never more than three |
| `derived_from_livestock` | inverse of the above | |
| `growing_conditions` | `FARMCROP.TEMP`, `RAIN`, `SOW`, `HARVEST` | enums below |
| `used_in` | inverse of `inputs` | |
| `production_technology_pct` | `100 − Σ inputs[].quality_pct` | see [Derived fields](#derived-fields) |
| `classification`, `industry` | our own grouping of `raw_class` | see below |

**`METHOD` has exactly five input slots.** That is why no recipe in the game has
more than five ingredients — a structural limit, not a coincidence of the data.

### Read from the game, or derived?

Every field falls into one of two groups, and nothing falls outside them.

| Read from the game (checked by the verifier) | Derived by rule (asserted by `tests/test_data.py`) |
|---|---|
| `name`, `raw_class`, `category` | `id` — gameset initial + name |
| `sale_index`, `sellable` | `icon_file` — slugified gameset + name |
| `output_unit`, `output_quantity` | `used_in` — the inverse of `inputs` |
| `inputs` | `derived_from_livestock` — the inverse of `livestock_yields` |
| `livestock_yields`, `growing_conditions` | `production_technology_pct` — `100 − Σ input quality_pct` |
| `extraction`, `livestock_production`, `livestock_stats`, `plant` | `classification`, `industry` — our grouping of the 32 class codes |

`classification` and `industry` deserve the caveat: they are **our** taxonomy, not
fields in the file. They are reproducible only while each stays an unambiguous
function of `raw_class`, which a test checks.

No record carries a field describing where it came from. Data asserting its own
provenance is a claim, not evidence: the claim belongs here, where it can be
wrong in one place, and the evidence is the verifier. `build_site.py` rejects
`classification_source`, `icon_image_id` and `graphic_count` by name — they
match nothing in the game's files and are read by no code, so their presence
only invites someone to trust them.

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

### Units and quantities

Each commodity has exactly one unit, and `ITEM.UNIT` agrees with the unit that
commodity carries in every recipe consuming it — verified across all three
gamesets, 0 disagreements. Gold is `oz` whether it comes out of a mine or goes
into Jewelry. `output_unit` is therefore populated for every product.

`output_quantity` is a different matter and stays absent for the 73 products with
no `METHOD` recipe, because a mine or a farm produces at a *rate*, not in batches.
The site's Output section is gated on `output_quantity`, so a raw material never
claims a per-run yield. The verifier asserts both halves: the unit is present and
correct, and the quantity is absent wherever there is no recipe.

> This was the project's one declared divergence, with `output_unit` left null for
> those 73 products on the reasoning that the field meant "unit of a production
> run". Conflating the unit with the quantity was the error — only the quantity was
> ever undefined. There are now no tolerated divergences.

Where the rate lives instead, none of it a per-batch yield:

| Kind | Table | Fields |
|---|---|---|
| Mining / extraction | `RAW` | `SPEED`, `RES_VALUE`, `MAX_SITE`, and `FIRM_CODE` naming the unit (`MINE`, `FORE`, `OIL`) |
| Livestock products | `FARMPROD` | `MONTH_QTY` with a `SMONTH`–`EMONTH` window |
| Crops | `FARMCROP` | the sow/harvest window only |

`FARMPROD` is worth calling out: Milk is 555 quart/month year-round, Wool 9 lb/month
but **only in months 6–10**, Eggs 1.7 dozen/month. The slaughter products carry
`MONTH_QTY` of 0 with `KILLFLAG` set.

### Still unresolved

`icon_image_id` and `graphic_count` **have been removed from the dataset.** They
matched nothing in the game's files and no code read either, so they amounted to an
invitation to trust a number whose origin nobody could state.
`tools/build_site.py` now fails if they reappear. Evidence under
[Graphics](#graphics) below.

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
  3608-byte stride (Car = 18040 = record 5). The `icon_image_id` the dataset used
  to carry was 10 for Car, while Car is entry 6 in `.II2` — so it matched neither,
  which is why the field is gone.

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

**Naming.** Every scenario has two: the stem of its file on the disc image
(`SPAIN.SCN`) and the title the game displays (*The Reign in Spain*). Neither is
derivable from the other — `UK.SCN` is *Rule Britannia*, `ROUGH.SCN` is *The Rough
Road Ahead* — so this document uses the **backticked stem** where the subject is
the file or its bytes, and the **displayed title** where the subject is gameplay.
Tables below give both; the site lists all 20.

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
| Techno-Sweep (`TECHNO`) | Automobile, Chemical Products, Computers, Electronic Products, Toys, Watches | lists exactly those six |
| Market Fortification (`FORTIFY`) | Beverage | "leading the beverage market" |
| Domination Down Under (`UNDER`) | Food, Canned Food, Snacks | — |
| Staying in Vogue (`VOGUE`) | Apparel, Cosmetics, Jewelry, Optical Products | — |
| The Emerging Dragon (`DRAGON`) | Chemical Products, Electronic Products | — |
| Global Domination (`GLOBAL`) | every sellable Standard category | "market dominance in every market" |

Scenarios whose goal is phrased at the *industry* level instead ("dominate
manufacturing and retail") decode to an **empty** array here. That is consistent
rather than a gap: industry-level domination is not a per-category concept and
lives in its own array.

### `dominateIndustries` (offsets 305–308)

Found by comparing two DOSBox saves: one from The Reign in Spain (`SPAIN`), and
one from a custom game built by hand with the same Manufacturing + Farming goal
enabled. Both showed identical bytes `[0,1,1,0]` at 305–308, while a save with no
industry goal (Techno-Sweep) and the custom game before its goal was set both
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
| The Asian Gold Rush (`ASIAN`), Italy — Looking South (`ITALY`) | Manufacturing, Retailing | "manufacturing and retail sectors" |
| The Reign in Spain (`SPAIN`) | Manufacturing, Farming | "manufacturing… retaining leadership in farming" |
| Rule Britannia (`UK`) | Manufacturing, Raw Material Production | "mining and manufacturing sectors" (mining = Raw Material Production) |
| Vertical Integration (`VERTICAL`) | Farming, Manufacturing, Retailing | "farming, manufacturing, and retail industries" |
| Global Domination (`GLOBAL`) | all four | "dominance in every single market" |

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

`production_technology_pct` is computed as `100 - sum(input quality_pct)`, not
read from a field: the game stores no such column, and its own Manufacturer's
Guide screen agrees with the arithmetic — Black Pepper's single 25% input leaves
75% technology. Every product's contributions therefore sum to 100% at the
source, which is why the site's scale factor is a defensive no-op rather than a
real correction. `TestDerivedFields` asserts the identity across all 245.
