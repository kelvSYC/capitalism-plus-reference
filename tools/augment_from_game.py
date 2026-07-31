#!/usr/bin/env python3
"""
augment_from_game.py — add production-rate fields to data/index_cards.json.

Unlike tools/verify_against_game.py, this one WRITES. It is a one-shot data tool,
re-runnable and idempotent: it reads the game's FARMPROD, RAW and FARMLIVE tables
and fills in fields the dataset never carried, leaving everything else alone.

    python3 tools/augment_from_game.py --game-dir "/path/to/game" [--dry-run]

Why these fields are worth having: none of this appears in the game's own
Farmer's Guide or its manuals. A player has to establish it by experiment. That
is precisely the sort of thing a reference should carry.

Fields added
------------
extraction            on raw materials, from RAW
                      which site type works it, relative speed, resource value,
                      and how many sites a map may hold
livestock_production  on livestock-derived goods, from FARMPROD
                      either a continuous monthly yield with a season, or a
                      slaughter percentage -- never both
livestock_stats       on the animals themselves, from FARMLIVE
                      weight, growth and reproduction rates. Weight is the base
                      the slaughter percentages apply to.
plant                 on the six crops that have one, from FARMCROP.PLANT_CODE
                      the growing plant as distinct from the harvested crop. The
                      game's own Farmer's Guide shows both images side by side;
                      its Manufacturer's Guide shows only the product.
output_unit           filled in from ITEM.UNIT wherever it was null -- see below

Fields removed
--------------
icon_image_id, graphic_count
                      Neither corresponds to anything in the game's files, and no
                      code reads either. ICONPTR indexes .II with a 3608-byte
                      stride; the recorded icon_image_id matches neither that nor
                      .II2's ordering, so both came out of a since-lost extraction
                      tool. Carrying unverifiable data nobody uses invites someone
                      to trust it later.

Why output_unit is filled rather than left null
-----------------------------------------------
It was null for the 73 products with no METHOD recipe, because the dataset treated
it as the unit of a production RUN and a mine has no runs. But the unit itself was
never in doubt: each commodity has exactly one, and ITEM.UNIT agrees with the unit
that commodity carries in every recipe consuming it -- verified, 0 disagreements.
Gold is 'oz' whether mined or bought.

output_quantity stays null for those products, which is the field that genuinely
does not apply. The site's Output section is gated on output_quantity, so filling
the unit alone cannot produce a phantom "yield N per production run".

Requires Python 3.8+, standard library only.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from verify_against_game import (  # noqa: E402  (path set above)
    MONTHS, SET_FOR_GAMESET, SITE_FOR_FIRM, find_game_dir, read_set, slug,
)

CARDS = ROOT / "data" / "index_cards.json"


def livestock_production(row, unit):
    """FARMPROD row -> one of two shapes, never both.

    KILLFLAG, P_PERCENT > 0 and MONTH_QTY == 0 agree on every row in every
    gameset, so the mode is unambiguous: an animal either yields something month
    after month (Milk, Wool, Eggs) or gives it up when slaughtered (meat,
    Leather, Tallow).
    """
    common = {"rate_percent": row["SPEED"]}
    if row["KILLFLAG"]:
        return {**common, "mode": "slaughter",
                "slaughter_percent": float(row["P_PERCENT"])}
    return {**common, "mode": "continuous",
            "monthly_quantity": float(row["MONTH_QTY"]),
            "unit": unit or None,
            "from_month": MONTHS[row["SMONTH"] - 1],
            "to_month": MONTHS[row["EMONTH"] - 1],
            "all_year": row["SMONTH"] == 1 and row["EMONTH"] == 12}


# Fields the dataset should not carry, with the reason:
#
#   icon_image_id, graphic_count  Matched nothing in the game's files and read by
#                                 no code -- numbers from a since-lost tool.
#   classification_source         The same sentence on all 245 records, asserting
#                                 the data's own provenance. Provenance belongs in
#                                 docs/DECODING.md, where it can be wrong in one
#                                 place, and in the verifier, which demonstrates it
#                                 rather than claiming it.
UNVERIFIABLE_FIELDS = ("icon_image_id", "graphic_count", "classification_source")


def build_additions(game_dir):
    """(gameset, product name) -> dict of new fields."""
    additions = {}
    for gameset, filename in SET_FOR_GAMESET.items():
        path = game_dir / "GAMESET" / filename
        if not path.exists():
            raise SystemExit(f"error: {path} not found")
        tables = read_set(path)
        name_of = {r["CODE"]: r["NAME"] for r in tables["ITEM"]["rows"]}
        unit_of = {r["CODE"]: r["UNIT"] for r in tables["ITEM"]["rows"]}

        # One unit per commodity, from ITEM.UNIT. Blank in the file for most
        # manufactured goods, where the dataset's convention is "unit".
        for row in tables["ITEM"]["rows"]:
            if row["CLASS"] == "PLANT":          # plants are not products
                continue
            additions.setdefault((gameset, row["NAME"]), {})["output_unit"] = \
                row["UNIT"] or "unit"

        for row in tables.get("RAW", {}).get("rows", []):
            product = name_of.get(row["ITEM_CODE"])
            if product is None:
                continue
            site = SITE_FOR_FIRM.get(row["FIRM_CODE"], {"site": row["FIRM_CODE"], "unit": None})
            additions.setdefault((gameset, product), {})["extraction"] = {
                "site": site["site"],
                "unit": site["unit"],
                "speed": row["SPEED"],
                "resource_value": row["RES_VALUE"],
                "max_sites": row["MAX_SITE"],
            }

        for row in tables.get("FARMPROD", {}).get("rows", []):
            product = name_of.get(row["ITEM_CODE"])
            if product is None:
                continue
            additions.setdefault((gameset, product), {})["livestock_production"] = \
                livestock_production(row, unit_of.get(row["ITEM_CODE"]))

        # FARMCROP links a crop to the plant it grows on. Six of them have a
        # distinct PLANT row with its own artwork -- Rubber/Rubber Plant,
        # Coconut/Palm and so on. PLANT rows are not products and stay out of the
        # dataset, so the plant rides along on the crop instead.
        for row in tables.get("FARMCROP", {}).get("rows", []):
            crop = name_of.get(row["ITEM_CODE"])
            plant = name_of.get(row["PLANT_CODE"])
            if crop is None or plant is None or plant == crop:
                continue
            plant_row = next((r for r in tables["ITEM"]["rows"]
                              if r["CODE"] == row["PLANT_CODE"]), None)
            if plant_row is None or plant_row["CLASS"] != "PLANT":
                continue
            additions.setdefault((gameset, crop), {})["plant"] = {
                "name": plant,
                "icon_file": f"{slug(gameset)}_{slug(plant)}.png",
            }

        for row in tables.get("FARMLIVE", {}).get("rows", []):
            animal = name_of.get(row["LSTOCK"])
            if animal is None:
                continue
            additions.setdefault((gameset, animal), {})["livestock_stats"] = {
                "weight": float(row["WEIGHT"]),
                "unit": unit_of.get(row["LSTOCK"]) or "lb",
                "grow_rate": row["GROW"],
                "reproduce_rate": row["REPRODUCE"],
            }
    return additions


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", help="directory containing GAMESET/")
    ap.add_argument("--dry-run", action="store_true", help="report changes, write nothing")
    args = ap.parse_args()

    game = find_game_dir(args.game_dir)
    if game is None:
        print("No game directory given. Pass --game-dir or set CAPITALISM_GAME_DIR.")
        return 2

    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    additions = build_additions(game)

    added = changed = removed = 0
    unmatched = set(additions)
    for card in cards:
        for dead in UNVERIFIABLE_FIELDS:
            if dead in card:
                del card[dead]
                removed += 1
        key = (card["gameset"], card["name"])
        new = additions.get(key)
        if not new:
            continue
        unmatched.discard(key)
        for field, value in new.items():
            if field not in card:
                added += 1
            elif card[field] != value:
                changed += 1
            card[field] = value

    if unmatched:
        print(f"warning: {len(unmatched)} game rows matched no product: "
              f"{sorted(unmatched)[:5]}")

    print(f"{added} fields added, {changed} updated, {removed} removed, "
          f"across {len(cards)} products")
    if args.dry_run:
        print("--dry-run: nothing written")
        return 0

    # Match the committed file's shape exactly -- 2-space indent, no trailing
    # newline -- so the diff shows only the new fields and not a reformat of all
    # 245 records.
    CARDS.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {CARDS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
