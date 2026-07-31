# Binary grammars

[Synalyze It! / Hexinator](https://www.synalysis.net/) grammars for the file
formats behind this project — the closest thing to a specification the game has,
and the basis for the tools in [`../../tools/`](../../tools/) that read it. See the
reproducibility note in [`../DECODING.md`](../DECODING.md) for what is automated
and what is not.

Open a `.grammar` file in Synalyze It! Pro or Hexinator, then open the
corresponding game file.

| Grammar | Describes | State |
|---|---|---|
| `Capitalism Plus SET Grammar` | `GAMESET/*.SET` — the table container behind the whole product dataset | Verified: parses all three gamesets |
| `Capitalism Database File` | `GAMESET/*.II2` — named image archive, 120×120 icons | Verified against `1STD.II2` |
| `Capitalism Raster File` | one `GAMESET/*.II` record — 60×60 icon | Verified, with two corrections below |
| `Capitalism Palette File` | `RESOURCE/PAL_STD.RES` and `IFCOLOR.RES` — the two 256-colour palettes | Verified: both are 776 bytes = 8 + 256×3 |
| `Capitalism Plus SCN Goal Header` | the goal fields of `SCENARIO/*.SCN` on the disc image | **New**, and untested in the tool — see below |

## How these were checked

Not by opening them in the tool. `../../tools/verify_against_game.py` implements
the `.SET` container from the SET grammar's specification and reads a retail copy
of the game with it — 2,020 checks against the committed data, 0 failures. That
exercises the format description far harder than eyeballing a hex dump does, and
it is what "verified" means in the table above.

The two image grammars and the palette grammar were checked the same way, by
reading the real files in Python and confirming the sizes and headers come out as
the grammars say. `1STD.II` is 303,072 bytes = 84 × 3608, one record per `ITEM`
row, with each record `4 + (4 + 60×60)`. `1STD.II2` holds 84 entries 14,404 bytes
apart = `4 + 120×120`.

The palette's 8-byte header is fully accounted for: four bytes of the file's own
length, then the constant `0x0000B123`. Of the 30 `.RES` files in `RESOURCE/`,
exactly two satisfy both conditions — `PAL_STD.RES` and `IFCOLOR.RES` — so a
palette is identifiable from its bytes rather than by name. The tag is byte-identical
across two files with entirely different colour tables, which is what a format
marker looks like and what a checksum does not.
`tests/test_against_game.py` asserts both, given a copy of the game.

## File association

Three grammars declare a `fileextension`, so the tool offers them automatically:
`Capitalism Plus SET Grammar` (`.SET`), `Capitalism Plus SCN Goal Header`
(`.SCN`) and `Capitalism Database File` (`.II2`). Two deliberately do not, and
adding one would make them worse:

- **`Capitalism Palette File`** — `.RES` is an extension, not a format. Only two
  of the thirty are palettes; the others are music, sound, text and fonts, and an
  association would offer this grammar for all of them.
- **`Capitalism Raster File`** — it describes **one** 60×60 record, while a `.II`
  file holds 84 of them end to end. Pointed at the whole file it parses the first
  icon and stops, which reads as a truncated file rather than a partial grammar.

## Corrections made to the Raster grammar

Both are in the committed copy. Neither has been re-opened in Synalyze It!, so
verify them there before relying on them.

1. **The leading four bytes are a length, not an unknown.** They hold
   `4 + Width × Height` — 3604 for a 60×60 icon. Renamed from `<new binary>` to
   `Length`.
2. **`Width` and `Height` were swapped in the row-mapping script.** It read
   `rowCount = Width` and strode by `Height`. For a square icon that is
   indistinguishable from correct, which is presumably why it survived; for the
   464×63 `GAMESET/*.PIC` it would map the rows wrongly. Now `rowCount = Height`,
   stride `Width`.

## The SCN grammar is new and unverified in-tool

Hand-written from offsets established in `../DECODING.md`, following the XML
idiom of the other four. Its offsets are checked automatically — `test_data.py`
walks the element lengths and asserts each documented field lands where it should
— but **nobody has opened it in Synalyze It!**, so treat structural details as
unproven even though the offsets are right.

It covers only the goal header. Scenarios are specially-built save games, so
everything after it — map, terrain, company state — is undecoded.

## What is still unexplained

- Roughly 36 of the 64 header bytes per `.SET` table (`<type?>`, `<unused>`).
  Harmless: the tables parse without them.
- `Row Data` in the SET grammar is an empty placeholder. The `Data` script marks
  row boundaries but never applies the column definitions to the bytes inside, so
  the tool shows rows as opaque blobs. The column metadata needed to decode them
  is all present and correct — `verify_against_game.py` uses exactly that — so
  this is unfinished wiring rather than missing knowledge.
- `GAMESET/*.PLA`, `*.PLP`, `*.PLO` are **not** palettes despite the names. They
  open with a ten-entry table of four-character tags (`RETA`, `FACT`). No grammar
  covers them.

## Licensing

These grammars are the project author's own work, under the terms in
[`../../LICENSE`](../../LICENSE). They describe file layouts; they contain no game
data. Documenting a format is not the same as having the right to redistribute
what that format holds — the outstanding question about the icons is in
[`../../ATTRIBUTION.md`](../../ATTRIBUTION.md) and is unaffected by anything here.
