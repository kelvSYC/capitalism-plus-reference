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
> `.SET` and `.SCN` files directly, and the dataset was assembled by hand from
> what that revealed. So a third party cannot currently regenerate it — not
> because a tool was lost, but because no tool has ever existed.
>
> That is a smaller gap than it sounds. The formats themselves are specified, in
> a set of Synalyze It! / Hexinator binary grammars written during that work (see
> [Method](#method) below). An extractor is a thing somebody could now write from
> a specification, rather than something that must be rediscovered.

## Method

Nothing here was decoded by running a parser over the files. The work was done by
reading bytes in a hex editor, forming a hypothesis about a field, and then
checking it against something independent — the `.SCT` goal prose, a second save
file, or the game's own behaviour under DOSBox. Where a hypothesis survived every
check it is recorded below; where one failed, the counterexample that killed it
is recorded too (see [Falsified hypotheses](#falsified-hypotheses)).

Four binary grammars were written along the way, in
[Synalyze It! / Hexinator](https://www.synalysis.net/) format. They are the
closest thing to a specification this project has:

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

## Scenario byte offsets (`.SCN`)

All verified against fresh byte reads of all 20 `.SCN` files, not just the
scenarios used during discovery.

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
