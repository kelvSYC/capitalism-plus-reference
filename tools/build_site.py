#!/usr/bin/env python3
"""
build_site.py — regenerate site/index.html from the template + product data.

The template (data/site_template.html) contains a single placeholder,
__PRODUCTS_JSON__, which gets replaced with the full contents of
data/index_cards.json. This is the ONLY build step: everything else in
site/index.html is authored directly in the template.

Usage:
    python3 tools/build_site.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "data" / "site_template.html"
CARDS = ROOT / "data" / "index_cards.json"
OUT = ROOT / "site" / "index.html"

def main():
    tpl = TEMPLATE.read_text()
    cards = json.loads(CARDS.read_text())
    out = tpl.replace("__PRODUCTS_JSON__", json.dumps(cards))
    OUT.write_text(out)
    print(f"built {OUT} ({len(out)} bytes)")

if __name__ == "__main__":
    main()
