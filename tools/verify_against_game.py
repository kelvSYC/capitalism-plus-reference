#!/usr/bin/env python3
"""
verify_against_game.py — check the committed data against the game's own files.

This is a VERIFIER, not an extractor. It never writes to data/; it reads the
game's files, derives what the dataset ought to contain, and reports any
disagreement. Capitalism Plus is a 1996 DOS title whose content will not change,
so a disagreement means our data is wrong, not that the game moved.

    python3 tools/verify_against_game.py --game-dir "/path/to/Capitalism Plus"
    CAPITALISM_GAME_DIR="/path/to/game" python3 tools/verify_against_game.py

The game directory is the one containing GAMESET/ and CapPlus.gog. Nothing from
the game is copied anywhere; the files are read and discarded.

What is checked
---------------
Product dataset (data/index_cards.json), against GAMESET/*.SET:
    name, raw_class, category, sale_index, sellable, output_quantity,
    output_unit, inputs, livestock_yields, growing_conditions

Scenario goals (the SCENARIOS array in data/site_template.html), against the
.SCN files on CapPlus.gog:
    years, bonus, excludedClasses, dominateClasses, dominateIndustries

Requires Python 3.8+, standard library only.
"""
import argparse
import json
import os
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "data" / "index_cards.json"
TEMPLATE = ROOT / "data" / "site_template.html"

# Which .SET file backs which gameset. The numeric prefixes are the game's own
# ordering of the three gamesets.
SET_FOR_GAMESET = {
    "Standard": "1STD.SET",
    "Alternative": "2ALTER.SET",
    "Food & Beverage": "3FOOD.SET",
}

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def slug(text):
    """The icon_file naming rule: non-alphanumerics collapse to a single '_'."""
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9]", "_", text))

# FARMCROP.RAIN is a plain enum.
RAINFALL = {1: "Little", 2: "Moderate", 3: "Plentiful"}

# FARMCROP.TEMP is NOT a bitmask under any assignment we have found: the four
# values observed across all three gamesets map as below, with 9 behaving as a
# "tolerant" special case rather than a combination of the others. Recorded
# empirically; if a value outside this table ever appears the verifier says so
# rather than guessing.
CLIMATE = {2: "Cool", 3: "Warm", 4: "Hot", 9: "Warm, Cool, or Cold"}

# .SCN goal-header offsets. See docs/DECODING.md for how each was established.
SCN_YEARS = 179
SCN_BONUS = 183
SCN_DOMINATE_INDUSTRIES = 305        # 4 bytes
SCN_EXCLUDED_CLASSES = 315           # one byte per ITEMCLAS row, 0 = excluded
SCN_DOMINATE_CLASSES = 415           # same layout, 1 = must dominate

# Byte order at 305 is reversed relative to the display convention used
# everywhere else on the site.
INDUSTRY_AT_305 = ["Retailing", "Manufacturing", "Farming", "Raw Material Production"]

# RAW.FIRM_CODE names the site type that works a raw material. The site used to
# infer this from the product's name, which happened to be right but would not
# survive a gameset that named things differently.
SITE_FOR_FIRM = {
    "MINE": {"site": "Mine", "unit": "Mining Unit"},
    "FORE": {"site": "Lumber Mill", "unit": "Logging Unit"},
    "OIL": {"site": "Oil Well", "unit": "Oil-Extracting Unit"},
}


# --------------------------------------------------------------- .SET reader ---
# The container is a self-describing table format: a descriptor block naming each
# table, then per table a 32-byte header, one 32-byte header per column, and
# fixed-length rows. Column headers carry their own offset within the row, so
# nothing here hard-codes a field position.

def read_set(path):
    b = path.read_bytes()
    count = struct.unpack_from("<H", b, 0)[0]
    pos, descriptors = 2, []
    for _ in range(count):
        name = b[pos:pos + 9].split(b"\0")[0].decode("latin-1").strip()
        descriptors.append((name, struct.unpack_from("<I", b, pos + 9)[0]))
        pos += 13

    tables = {}
    for name, off in descriptors:
        row_count = struct.unpack_from("<I", b, off + 4)[0]
        data_off = struct.unpack_from("<H", b, off + 8)[0]
        row_len = struct.unpack_from("<I", b, off + 10)[0]
        col_count = (data_off - 32) // 32

        cols = []
        for i in range(col_count):
            cb = off + 32 + i * 32
            ctype = chr(b[cb + 11])
            cols.append({
                "name": b[cb:cb + 11].split(b"\0")[0].decode("latin-1").strip(),
                "type": ctype,
                "off": struct.unpack_from("<I", b, cb + 12)[0],
                # A numeric column stores length and decimal places in two
                # bytes; everything else uses a 16-bit length.
                "len": b[cb + 16] if ctype == "N" else struct.unpack_from("<H", b, cb + 16)[0],
                "dec": b[cb + 17] if ctype == "N" else 0,
            })

        rows = []
        for r in range(row_count):
            rb = off + data_off + r * row_len
            rec = {}
            for c in cols:
                raw = b[rb + c["off"]: rb + c["off"] + c["len"]]
                if c["type"] == "C":
                    rec[c["name"]] = raw.split(b"\0")[0].decode("latin-1").strip()
                elif c["type"] == "L":
                    # dBASE-style logical: ASCII 'T'/'F', not a zero/non-zero
                    # byte. Testing for non-zero decodes every value as true.
                    rec[c["name"]] = raw[:1].upper() == b"T"
                else:
                    text = raw.decode("latin-1").strip()
                    try:
                        rec[c["name"]] = float(text) if c["dec"] else int(text or 0)
                    except ValueError:
                        rec[c["name"]] = text
            rows.append(rec)
        tables[name] = {"cols": cols, "rows": rows}
    return tables


# ------------------------------------------------------------- ISO9660 reader ---
# The scenarios ship on the CD image rather than in the installed directory, so
# they are read straight out of it. Mounting is deliberately avoided: this only
# needs the directory tree and a byte range.

def _iso_records(f, lba, length):
    f.seek(lba * 2048)
    data = f.read(length)
    pos = 0
    while pos < len(data):
        rec_len = data[pos]
        if rec_len == 0:                      # padding to the end of the sector
            pos = (pos // 2048 + 1) * 2048
            if pos >= len(data):
                break
            continue
        rec = data[pos:pos + rec_len]
        name_len = rec[32]
        yield (rec[33:33 + name_len].decode("latin-1"),
               struct.unpack_from("<I", rec, 2)[0],
               struct.unpack_from("<I", rec, 10)[0],
               rec[25])
        pos += rec_len


def iso_walk(path):
    """(full name, LBA, size) for every file in an ISO9660 image."""
    out = []
    with open(path, "rb") as f:
        f.seek(0x8000 + 156)                  # root record in the primary descriptor
        root = f.read(34)
        stack = [("", struct.unpack_from("<I", root, 2)[0],
                  struct.unpack_from("<I", root, 10)[0])]
        while stack:
            prefix, lba, length = stack.pop()
            for name, ext, size, flags in _iso_records(f, lba, length):
                if name in ("\x00", "\x01"):  # . and ..
                    continue
                clean = name.split(";")[0]
                if flags & 0x02:
                    stack.append((prefix + clean + "/", ext, size))
                else:
                    out.append((prefix + clean, ext, size))
    return out


def iso_read(path, lba, size):
    with open(path, "rb") as f:
        f.seek(lba * 2048)
        return f.read(size)


# ------------------------------------------------------------- normalisations ---
# Three places where the dataset deliberately departs from the raw file. They
# live here, named, because they are editorial decisions rather than game data
# and were previously invisible.

def normalise_unit(raw_unit):
    """ITEM.UNIT is blank for most manufactured goods; the dataset says "unit"."""
    return raw_unit or "unit"


def normalise_category(itemclas_name):
    """ITEMCLAS.NAME is singular in the file ("Computer"); the dataset pluralises
    for display ("Computers"). Only the handful below actually differ."""
    # Exactly the five renames observed across all three gamesets, derived by
    # diffing every ITEMCLAS.NAME against our category rather than guessed. Every
    # other class name is used verbatim.
    return {
        "Apparel, Footwear & Bag": "Apparel, Footwear & Bags",
        "Cigarette": "Cigarettes",
        "Computer": "Computers",
        "Toy": "Toys",
        "Watch": "Watches",
    }.get(itemclas_name, itemclas_name)


def is_product_row(item_row):
    """CLASS=PLANT rows are the growing plant, not the harvested good (Rubber
    Plant, Sugar Cane). The dataset covers products only, which is why ITEM has
    84 rows where Standard has 82 products."""
    return item_row["CLASS"] != "PLANT"


# -------------------------------------------------------------------- checks ---

# Places where the dataset knowingly differs from the file. Declared, counted and
# reported -- never quietly tolerated -- so a new disagreement cannot hide inside
# an accepted one, and so the count itself is a tripwire if the shape changes.
KNOWN_DIVERGENCES = {}
EXPECTED_DIVERGENCES = 0

_RESOLVED_DIVERGENCES = {
    # Kept as a record of what was here and how it was settled. output_unit was
    # null for the 73 products with no METHOD recipe; since the unit itself was
    # never ambiguous -- ITEM.UNIT agrees with every recipe consuming the
    # commodity -- the dataset now carries it, and output_quantity alone stays
    # absent. Nothing is currently tolerated.
    "output_unit (resolved)": (
        "The dataset leaves output_unit null for the products with no METHOD recipe\n"
        "    (raw materials, crops, livestock), because it treats the field as the unit\n"
        "    of a production RUN. There is no production run for these: a mine or a farm\n"
        "    produces at a rate, not in batches.\n"
        "\n"
        "    But the UNIT itself is not ambiguous. Each commodity has exactly one unit,\n"
        "    and ITEM.UNIT agrees with the unit that commodity carries in every recipe\n"
        "    that consumes it -- verified below, 0 disagreements. Gold is 'oz' whether\n"
        "    mined or bought. So the dataset is missing a unit it could state, while the\n"
        "    genuinely undefined thing is the QUANTITY.\n"
        "\n"
        "    Where the rate actually lives, for reference: RAW.SPEED for mining,\n"
        "    FARMPROD.MONTH_QTY plus SMONTH/EMONTH for livestock products (Milk 555\n"
        "    quart/month, Wool 9 lb/month in months 6-10), FARMCROP's sow/harvest window\n"
        "    for crops. None of it is a per-batch yield. Expected count: 73."
    ),
}


class Report:
    def __init__(self):
        self.passed = 0
        self.failures = []
        self.divergences = []

    def check(self, subject, field, got, want):
        if got == want:
            self.passed += 1
        else:
            self.failures.append(f"{subject}: {field}\n      game: {got!r}\n      ours: {want!r}")

    def divergence(self, subject, field, got, want):
        """A mismatch that matches a declared, understood divergence."""
        self.divergences.append(f"{subject}: {field} game={got!r} ours={want!r}")

    def summary(self, label):
        print(f"  {label}: {self.passed} checks passed, {len(self.failures)} failed, "
              f"{len(self.divergences)} known divergences")
        for f in self.failures[:20]:
            print(f"    FAIL {f}")
        if len(self.failures) > 20:
            print(f"    ... and {len(self.failures) - 20} more")


def verify_products(gameset_dir, cards, report):
    for gameset, filename in SET_FOR_GAMESET.items():
        path = gameset_dir / filename
        if not path.exists():
            report.failures.append(f"{gameset}: {filename} not found in {gameset_dir}")
            continue
        tables = read_set(path)
        ours = {c["name"]: c for c in cards if c["gameset"] == gameset}

        items = [r for r in tables["ITEM"]["rows"] if is_product_row(r)]
        report.check(gameset, "product names",
                     sorted(r["NAME"] for r in items), sorted(ours))

        class_name = {r["CLASS"]: r["NAME"] for r in tables["ITEMCLAS"]["rows"]}
        code_of = {r["NAME"]: r["CODE"] for r in tables["ITEM"]["rows"]}
        name_of = {r["CODE"]: r["NAME"] for r in tables["ITEM"]["rows"]}
        methods = {r["OUTPUT"]: r for r in tables["METHOD"]["rows"]}

        for row in items:
            card = ours.get(row["NAME"])
            if card is None:
                continue
            who = f"{gameset}/{row['NAME']}"
            report.check(who, "raw_class", row["CLASS"], card["raw_class"])
            report.check(who, "sale_index", float(row["SALEINDEX"]), float(card["sale_index"]))
            report.check(who, "sellable", row["SALEINDEX"] > 0, card["sellable"])
            # Every product now carries its unit, including the ones with no
            # production run -- the unit was never the ambiguous part.
            report.check(who, "output_unit", normalise_unit(row["UNIT"]), card["output_unit"])
            # output_quantity is the field that genuinely does not apply without a
            # METHOD recipe, and must stay absent for those.
            if code_of.get(row["NAME"]) not in methods:
                report.check(who, "no output_quantity without a recipe",
                             None, card["output_quantity"])
            expected_category = normalise_category(class_name.get(row["CLASS"], ""))
            if card["category"] is not None:
                report.check(who, "category", expected_category, card["category"])

            method = methods.get(code_of.get(row["NAME"]))
            if method:
                report.check(who, "output_quantity",
                             float(method["OQTY"]), float(card["output_quantity"] or 0))
                # METHOD has exactly five input slots; a blank code ends the list.
                got = [(name_of.get(method[f"INPUT{i}"], method[f"INPUT{i}"]),
                        float(method[f"IQTY{i}"]), float(method[f"IQUA{i}"]))
                       for i in range(1, 6) if method[f"INPUT{i}"]]
                mine = [(i["material"], float(i["amount"]), float(i["quality_pct"]))
                        for i in card["inputs"]]
                report.check(who, "inputs", got, mine)

        # One unit per commodity: ITEM.UNIT must agree with the unit that
        # commodity carries wherever it is consumed. This is what makes the
        # output_unit divergence a missing value rather than an ambiguity.
        consumed = {}
        for card in ours.values():
            for i in card["inputs"]:
                consumed.setdefault(i["material"], set()).add(i["unit"])
        for row in items:
            seen = consumed.get(row["NAME"])
            if seen:
                report.check(f"{gameset}/{row['NAME']}", "unit is consistent when consumed",
                             {normalise_unit(row["UNIT"])}, seen)

        for row in tables["FARMLIVE"]["rows"]:
            animal = name_of.get(row["LSTOCK"], row["LSTOCK"])
            card = ours.get(animal)
            if card is None:
                continue
            yields = [name_of.get(row[f"PRODUCT{k}"], row[f"PRODUCT{k}"])
                      for k in (1, 2, 3) if row[f"PRODUCT{k}"]]
            report.check(f"{gameset}/{animal}", "livestock_yields",
                         yields, card.get("livestock_yields"))

        # Production rates -- the fields augment_from_game.py adds. None of this
        # appears in the game's own Farmer's Guide, so it is exactly the sort of
        # thing that would rot unnoticed if it were not checked.
        for row in tables.get("RAW", {}).get("rows", []):
            card = ours.get(name_of.get(row["ITEM_CODE"], ""))
            if card is None or "extraction" not in card:
                continue
            got = {"site": SITE_FOR_FIRM[row["FIRM_CODE"]]["site"],
                   "unit": SITE_FOR_FIRM[row["FIRM_CODE"]]["unit"],
                   "speed": row["SPEED"], "resource_value": row["RES_VALUE"],
                   "max_sites": row["MAX_SITE"]}
            report.check(f"{gameset}/{card['name']}", "extraction", got, card["extraction"])

        for row in tables.get("FARMPROD", {}).get("rows", []):
            card = ours.get(name_of.get(row["ITEM_CODE"], ""))
            if card is None or "livestock_production" not in card:
                continue
            who = f"{gameset}/{card['name']}"
            lp = card["livestock_production"]
            # The three fields agree on every row, so the mode is unambiguous --
            # asserted here so a future dataset cannot record a product as both.
            report.check(who, "production mode is consistent in the file",
                         row["KILLFLAG"] == (row["P_PERCENT"] > 0) == (row["MONTH_QTY"] == 0),
                         True)
            report.check(who, "production mode",
                         "slaughter" if row["KILLFLAG"] else "continuous", lp["mode"])
            report.check(who, "rate_percent", row["SPEED"], lp["rate_percent"])
            if row["KILLFLAG"]:
                report.check(who, "slaughter_percent",
                             float(row["P_PERCENT"]), lp["slaughter_percent"])
            else:
                report.check(who, "monthly_quantity",
                             float(row["MONTH_QTY"]), lp["monthly_quantity"])
                report.check(who, "season",
                             (MONTHS[row["SMONTH"] - 1], MONTHS[row["EMONTH"] - 1]),
                             (lp["from_month"], lp["to_month"]))

        for row in tables.get("FARMLIVE", {}).get("rows", []):
            card = ours.get(name_of.get(row["LSTOCK"], ""))
            if card is None or "livestock_stats" not in card:
                continue
            got = {"weight": float(row["WEIGHT"]),
                   "unit": card["livestock_stats"]["unit"],   # from ITEM.UNIT, checked above
                   "grow_rate": row["GROW"], "reproduce_rate": row["REPRODUCE"]}
            report.check(f"{gameset}/{card['name']}", "livestock_stats",
                         got, card["livestock_stats"])

        # The plant that a crop grows on, where it has a distinct one.
        for row in tables["FARMCROP"]["rows"]:
            card = ours.get(name_of.get(row["ITEM_CODE"], ""))
            plant_name = name_of.get(row["PLANT_CODE"])
            plant_row = next((r for r in tables["ITEM"]["rows"]
                              if r["CODE"] == row["PLANT_CODE"]), None)
            has_plant = (plant_row is not None and plant_row["CLASS"] == "PLANT"
                         and plant_name != (card or {}).get("name"))
            if card is None:
                continue
            if has_plant:
                report.check(f"{gameset}/{card['name']}", "plant",
                             {"name": plant_name,
                              "icon_file": f"{slug(gameset)}_{slug(plant_name)}.png"},
                             card.get("plant"))
            else:
                report.check(f"{gameset}/{card['name']}", "has no plant",
                             False, "plant" in card)

        for row in tables["FARMCROP"]["rows"]:
            crop = name_of.get(row["ITEM_CODE"], row["ITEM_CODE"])
            card = ours.get(crop)
            if card is None or not card.get("growing_conditions"):
                continue
            gc = card["growing_conditions"]
            who = f"{gameset}/{crop}"
            report.check(who, "climate", CLIMATE.get(row["TEMP"], f"<unknown TEMP {row['TEMP']}>"),
                         gc["climate"])
            report.check(who, "rainfall", RAINFALL.get(row["RAIN"], f"<unknown RAIN {row['RAIN']}>"),
                         gc["rainfall"])
            report.check(who, "sowing_month", MONTHS[row["SOW"] - 1], gc["sowing_month"])
            report.check(who, "harvesting_month", MONTHS[row["HARVEST"] - 1], gc["harvesting_month"])


def parse_scenarios(template_text):
    """The SCENARIOS array is authored inline in the template. Split on the start
    of each record rather than matching a closing brace: a lookahead-based
    pattern silently drops the final entry."""
    block = re.search(r"const SCENARIOS = \[(.*?)\n\];", template_text, re.S)
    if block is None:
        raise SystemExit("error: SCENARIOS array not found in the template")
    out = []
    for chunk in re.split(r"\n(?=  \{ key:)", block.group(1).strip()):
        if "key:" not in chunk:
            continue

        def strings(field):
            m = re.search(field + r":\s*\[([^\]]*)\]", chunk)
            return re.findall(r'"([^"]+)"', m.group(1)) if m else []

        def number(field):
            m = re.search(field + r":\s*(\d+)", chunk)
            return int(m.group(1)) if m else None

        out.append({
            "key": re.search(r'key:\s*"([^"]+)"', chunk).group(1),
            "gameset": re.search(r'gameset:\s*"([^"]+)"', chunk).group(1),
            "years": number("years"),
            "bonus": number("bonus"),
            "excludedClasses": strings("excludedClasses"),
            "dominateClasses": strings("dominateClasses"),
            "dominateIndustries": strings("dominateIndustries"),
        })
    return out


def verify_scenarios(iso_path, gameset_dir, scenarios, report):
    scn = {name.split("/")[-1]: (lba, size)
           for name, lba, size in iso_walk(iso_path)
           if name.upper().endswith(".SCN")}
    # Each scenario's flag arrays are one byte per row of ITS gameset's ITEMCLAS
    # table, so a wrong gameset would decode to the wrong class codes -- which
    # makes the class comparisons an implicit check on the gameset assignment.
    itemclas = {}
    for gameset, filename in SET_FOR_GAMESET.items():
        path = gameset_dir / filename
        if path.exists():
            itemclas[gameset] = [r["CLASS"] for r in read_set(path)["ITEMCLAS"]["rows"]]

    for s in scenarios:
        entry = scn.get(s["key"] + ".SCN")
        if entry is None:
            report.failures.append(f"{s['key']}: no {s['key']}.SCN on the disc image")
            continue
        b = iso_read(iso_path, *entry)
        classes = itemclas.get(s["gameset"])
        if classes is None:
            continue
        report.check(s["key"], "years", b[SCN_YEARS], s["years"])
        report.check(s["key"], "bonus", b[SCN_BONUS], s["bonus"])
        report.check(s["key"], "excludedClasses",
                     sorted(c for i, c in enumerate(classes) if b[SCN_EXCLUDED_CLASSES + i] == 0),
                     sorted(s["excludedClasses"]))
        report.check(s["key"], "dominateClasses",
                     sorted(c for i, c in enumerate(classes) if b[SCN_DOMINATE_CLASSES + i] == 1),
                     sorted(s["dominateClasses"]))
        report.check(s["key"], "dominateIndustries",
                     sorted(INDUSTRY_AT_305[i] for i in range(4)
                            if b[SCN_DOMINATE_INDUSTRIES + i] == 1),
                     sorted(s["dominateIndustries"]))


def find_game_dir(explicit):
    for candidate in (explicit, os.environ.get("CAPITALISM_GAME_DIR")):
        if candidate:
            path = Path(candidate)
            if (path / "GAMESET").is_dir():
                return path
            raise SystemExit(f"error: {path} does not contain a GAMESET directory")
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", help="directory containing GAMESET/ and CapPlus.gog")
    args = ap.parse_args()

    game = find_game_dir(args.game_dir)
    if game is None:
        print("No game directory given. Pass --game-dir or set CAPITALISM_GAME_DIR.")
        print("Nothing verified.")
        return 2

    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    report = Report()

    print(f"Verifying against {game}")
    verify_products(game / "GAMESET", cards, report)
    report.summary("product dataset")

    iso = game / "CapPlus.gog"
    scen_report = Report()
    if iso.exists():
        scenarios = parse_scenarios(TEMPLATE.read_text(encoding="utf-8"))
        print(f"  {len(scenarios)} scenarios parsed from the template")
        verify_scenarios(iso, game / "GAMESET", scenarios, scen_report)
        scen_report.summary("scenario goals")
    else:
        print(f"  skipped scenarios: {iso.name} not present "
              "(the .SCN files ship on the disc image)")

    failures = len(report.failures) + len(scen_report.failures)
    diverged = len(report.divergences) + len(scen_report.divergences)
    print(f"\n{report.passed + scen_report.passed} checks passed, {failures} failed, "
          f"{diverged} known divergences")

    if diverged:
        print("\nKnown divergences (declared in KNOWN_DIVERGENCES):")
        for field, why in KNOWN_DIVERGENCES.items():
            print(f"  {field}: {why}")
        if diverged != EXPECTED_DIVERGENCES:
            print(f"\nerror: expected {EXPECTED_DIVERGENCES} known divergences, found "
                  f"{diverged}. The shape of the divergence has changed -- re-examine it "
                  f"rather than updating the number.")
            return 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
