#!/usr/bin/env python3
"""
build_site.py — regenerate site/index.html from the template + product data.

The template (data/site_template.html) contains a single placeholder,
__PRODUCTS_JSON__, which gets replaced with the full contents of
data/index_cards.json. This is the ONLY build step: everything else in
site/index.html is authored directly in the template.

site/index.html is a GENERATED file that is nevertheless committed, so the
site stays usable by cloning and opening it directly -- no server, no build
step -- as the README describes. That only works if the committed artifact
never falls behind its inputs, hence --check.

Usage:
    python3 tools/build_site.py            # regenerate site/index.html
    python3 tools/build_site.py --check    # verify it is current; write nothing

--check exits non-zero if site/index.html differs from what a fresh build
would produce. It is the only thing that can actually prove the committed
artifact matches its source; run it in CI and before committing.

Requires Python 3.6+, standard library only.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "data" / "site_template.html"
CARDS = ROOT / "data" / "index_cards.json"
OUT = ROOT / "site" / "index.html"

PLACEHOLDER = "__PRODUCTS_JSON__"

# Keys the site dereferences without guarding, so a record missing one of them
# is a broken page rather than a degraded one. Deliberately not the full key
# set: growing_conditions / livestock_yields / derived_from_livestock are
# genuinely optional (present only on crops, livestock, and livestock-derived
# products respectively) and every read of them in the template is guarded.
REQUIRED_KEYS = frozenset({
    "id", "gameset", "name", "category", "classification", "raw_class",
    "industry", "sellable", "icon_file", "inputs", "used_in", "output_unit",
})

# Recorded by a tool nobody has, matching nothing in the game's files, read by no
# code. Removed from the dataset; the build fails if they come back, because their
# presence invites someone to trust them.
FORBIDDEN_KEYS = frozenset({"icon_image_id", "graphic_count", "classification_source"})


def render() -> str:
    """Build the site HTML in memory. Exits with a message on bad inputs."""
    # encoding="utf-8" is not optional here. The template contains 57
    # non-ASCII characters (em dashes, U+0336 combining strikethrough, arrows,
    # etc.), and on a machine whose locale default is cp1252 an unqualified
    # read_text() decodes those UTF-8 byte sequences WITHOUT raising -- every
    # byte happens to map to some cp1252 character -- so the build would
    # silently emit a mojibake site ("Capitalism Plus â€" Product Reference")
    # and still report success.
    tpl = TEMPLATE.read_text(encoding="utf-8")

    # A missing placeholder used to be a silent no-op: str.replace found
    # nothing, the build printed a plausible byte count, and the resulting page
    # died at `const PRODUCTS = __PRODUCTS_JSON__;` with a ReferenceError that
    # took the whole inline script -- i.e. the entire app -- down with it,
    # rendering a blank page. Fail loudly instead.
    found = tpl.count(PLACEHOLDER)
    if found != 1:
        sys.exit(
            f"error: expected exactly one {PLACEHOLDER} in {TEMPLATE.name}, found {found}"
        )

    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    if not isinstance(cards, list) or not cards:
        sys.exit(f"error: {CARDS.name} must be a non-empty JSON array")
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            sys.exit(f"error: {CARDS.name}[{i}] is {type(card).__name__}, expected object")
        missing = REQUIRED_KEYS - card.keys()
        if missing:
            sys.exit(
                f"error: {CARDS.name}[{i}] ({card.get('id')!r}) missing "
                f"required key(s): {', '.join(sorted(missing))}"
            )
        forbidden = FORBIDDEN_KEYS & card.keys()
        if forbidden:
            sys.exit(
                f"error: {CARDS.name}[{i}] ({card.get('id')!r}) carries "
                f"unverifiable key(s): {', '.join(sorted(forbidden))}"
            )

    # The payload lands inside an inline <script>, which is an HTML *raw-text*
    # element: the parser ends the script at the first "</script" it sees, even
    # inside a JavaScript string literal. json.dumps does not escape "<", so a
    # single product name or note containing "</script>" would break out of the
    # script element entirely. Escaping "<" to its < form is inert in JS
    # (identical string value) and makes that structurally impossible.
    # ensure_ascii additionally neutralizes U+2028/U+2029, which are literal
    # line terminators in JS but legal raw characters in JSON.
    payload = json.dumps(cards, ensure_ascii=True).replace("<", "\\u003c")
    return tpl.replace(PLACEHOLDER, payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate site/index.html from the template + product data."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify site/index.html is up to date; write nothing, exit 1 on drift",
    )
    args = parser.parse_args()

    want = render().encode("utf-8")
    rel = OUT.relative_to(ROOT)

    if args.check:
        have = OUT.read_bytes() if OUT.exists() else None
        if have != want:
            reason = "missing" if have is None else "stale"
            print(
                f"error: {rel} is {reason} -- run: python3 tools/build_site.py",
                file=sys.stderr,
            )
            return 1
        print(f"ok: {rel} is up to date ({len(want)} bytes)")
        return 0

    # Byte-level write with an implicit LF: Path.write_text() goes through text
    # mode, which rewrites \n to \r\n on Windows and would turn every build on
    # that platform into a whole-file diff against the committed artifact.
    OUT.write_bytes(want)
    print(f"built {rel} ({len(want)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
