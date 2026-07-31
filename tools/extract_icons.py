#!/usr/bin/env python3
"""
extract_icons.py — build site/images/ from your own copy of the game.

The site is designed to work without artwork: a missing icon renders as a
monogram tile, and that is the state this repository ships in. This tool is for
somebody who owns Capitalism Plus and wants their local copy of the reference to
show the game's own icons.

    python3 tools/extract_icons.py --game-dir "/path/to/Capitalism Plus"
    python3 tools/extract_icons.py --game-dir ... --verify    # compare, write nothing

It reads only the path you give it. Nothing is bundled, cached or downloaded, and
the output goes to site/images/, which is git-ignored, asserted clean by
tests/test_data.py, and refused by the pages deploy workflow. Those guards are
what make this tool safe to ship: the repository cannot publish what it produces.
The licensing question about the icons themselves is unchanged and unresolved --
see ATTRIBUTION.md.

Where the pixels come from
--------------------------
GAMESET/<gameset>.II2   a named archive: u16 count, then per entry a 9-byte name
                        and u32 offset, each pointing at u16 width, u16 height,
                        then width*height bytes of palette indices. 120x120.
RESOURCE/PAL_STD.RES    the shared 256-colour palette: u32 file size, 4 unknown
                        bytes, then 256 RGB triples, already 8 bits per channel.

Products are matched to archive entries by ITEM.FILENAME -- the entries are DOS
8.3 names (APPLEJ~1, MILK-6), which is also why their numeric suffixes are not a
frame count. See docs/DECODING.md and docs/formats/.

Four crops will differ from the icons the original site shipped with
--------------------------------------------------------------------
Six crops have a separate PLANT row carrying its own artwork -- the growing plant
as distinct from the harvested commodity -- linked by FARMCROP.PLANT_CODE:

    Rubber / Rubber Plant      Sugar / Sugar Cane      Coconut / Palm
    Coffee / Coffee Plant      Flax Fiber / Flax       Tea / Tea Plant

The original extraction used the PLANT artwork for the first four and the
commodity's own for the last two, so it was not consistent. This tool always uses
ITEM.FILENAME, which is the association the game itself makes for each product.
Expect Rubber, Sugar, Coconut and Coffee to show the harvested commodity where
they previously showed the plant.

Requires Python 3.8+, standard library only. PNG is written directly with zlib.
"""
import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from verify_against_game import SET_FOR_GAMESET, find_game_dir, read_set  # noqa: E402

CARDS = ROOT / "data" / "index_cards.json"
DEFAULT_OUT = ROOT / "site" / "images"
PALETTE_FILE = "RESOURCE/PAL_STD.RES"


def read_palette(game_dir):
    """256 RGB triples after an 8-byte header. Values are already 8-bit."""
    data = (game_dir / PALETTE_FILE).read_bytes()
    if len(data) < 8 + 256 * 3:
        raise SystemExit(f"error: {PALETTE_FILE} is {len(data)} bytes, expected at least 776")
    return [tuple(data[8 + i * 3: 8 + i * 3 + 3]) for i in range(256)]


def read_icon_archive(path):
    """name -> (width, height, palette indices) for every entry in a .II2."""
    b = path.read_bytes()
    count = struct.unpack_from("<H", b, 0)[0]
    entries, pos = {}, 2
    for _ in range(count):
        name = b[pos:pos + 9].split(b"\0")[0].decode("latin-1")
        offset = struct.unpack_from("<I", b, pos + 9)[0]
        pos += 13
        width, height = struct.unpack_from("<HH", b, offset)
        entries[name] = (width, height, b[offset + 4: offset + 4 + width * height])
    return entries


def write_png(path, width, height, rgb):
    """Truecolour 8-bit PNG, matching the shape of the original extraction.

    Written by hand because the standard library has no PNG writer and this tool
    deliberately has no dependencies. Filter 0 on every scanline: larger than an
    optimising encoder would produce, identical once decoded.
    """
    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def decode_png_rgb(path):
    """Enough of a PNG reader to compare against a previous extraction."""
    b = path.read_bytes()
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, width, height = 8, b"", None, None
    while pos < len(b):
        length = struct.unpack_from(">I", b, pos)[0]
        tag = b[pos + 4:pos + 8]
        if tag == b"IHDR":
            width, height, depth, colour = struct.unpack_from(">IIBB", b, pos + 8)
            if (depth, colour) != (8, 2):
                raise ValueError(f"expected 8-bit truecolour, got depth={depth} type={colour}")
        elif tag == b"IDAT":
            idat += b[pos + 8:pos + 8 + length]
        pos += 12 + length

    raw = zlib.decompress(idat)
    stride, out, prev, p = width * 3, bytearray(), bytearray(width * 3), 0
    for _ in range(height):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if f == 1:
            for i in range(3, stride):
                line[i] = (line[i] + line[i - 3]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = line[i - 3] if i >= 3 else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - 3] if i >= 3 else 0
                c = prev[i - 3] if i >= 3 else 0
                pa, pb, pc = abs(prev[i] - c), abs(a - c), abs(a + prev[i] - 2 * c)
                pred = a if (pa <= pb and pa <= pc) else (prev[i] if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        elif f != 0:
            raise ValueError(f"unknown PNG filter {f}")
        out += line
        prev = line
    return width, height, bytes(out)


def entry_for(card, archive, filename_of, code_of):
    """Match a product to its archive entry.

    ITEM.FILENAME is the key -- the archive is named by DOS 8.3 filenames. One
    product in the Alternative gameset (Apple) carries FILENAME 'APPLERAW' while
    its entry is 'APPLE', so CODE is tried as a fallback rather than special-casing
    that one row.
    """
    for key in (filename_of.get(card["name"]), code_of.get(card["name"])):
        if key and key in archive:
            return archive[key], key
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", help="directory containing GAMESET/ and RESOURCE/")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    ap.add_argument("--verify", action="store_true",
                    help="compare against existing PNGs pixel by pixel; write nothing")
    ap.add_argument("--dry-run", action="store_true", help="report what would be written")
    args = ap.parse_args()

    game = find_game_dir(args.game_dir)
    if game is None:
        print("No game directory given. Pass --game-dir or set CAPITALISM_GAME_DIR.")
        return 2

    palette = read_palette(game)
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    out_dir = Path(args.out)
    if not (args.verify or args.dry_run):
        out_dir.mkdir(parents=True, exist_ok=True)

    written = matched = identical = 0
    problems = []
    for gameset, set_name in SET_FOR_GAMESET.items():
        archive_path = game / "GAMESET" / (set_name.rsplit(".", 1)[0] + ".II2")
        if not archive_path.exists():
            problems.append(f"{gameset}: {archive_path.name} not found")
            continue
        archive = read_icon_archive(archive_path)
        tables = read_set(game / "GAMESET" / set_name)
        filename_of = {r["NAME"]: r["FILENAME"] for r in tables["ITEM"]["rows"]}
        code_of = {r["NAME"]: r["CODE"] for r in tables["ITEM"]["rows"]}

        for card in (c for c in cards if c["gameset"] == gameset):
            entry, key = entry_for(card, archive, filename_of, code_of)
            if entry is None:
                problems.append(f"{gameset}/{card['name']}: no archive entry")
                continue
            width, height, indices = entry
            if len(indices) != width * height:
                problems.append(f"{gameset}/{card['name']}: truncated image data")
                continue
            matched += 1
            rgb = b"".join(bytes(palette[i]) for i in indices)
            target = out_dir / card["icon_file"]

            if args.verify:
                if not target.exists():
                    problems.append(f"{card['icon_file']}: not present to compare")
                    continue
                try:
                    ow, oh, orgb = decode_png_rgb(target)
                except ValueError as exc:
                    problems.append(f"{card['icon_file']}: {exc}")
                    continue
                if (ow, oh) != (width, height):
                    problems.append(f"{card['icon_file']}: {ow}x{oh} vs {width}x{height}")
                elif orgb != rgb:
                    differing = sum(1 for i in range(0, len(rgb), 3)
                                    if rgb[i:i + 3] != orgb[i:i + 3])
                    problems.append(f"{card['icon_file']}: {differing} pixels differ")
                else:
                    identical += 1
            elif not args.dry_run:
                write_png(target, width, height, rgb)
                written += 1

    if args.verify:
        print(f"{identical} of {matched} icons match the existing PNGs exactly")
    elif args.dry_run:
        print(f"{matched} icons would be written to {out_dir}")
    else:
        print(f"wrote {written} icons to {out_dir}")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems[:20]:
            print(f"  {p}")
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
