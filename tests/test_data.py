#!/usr/bin/env python3
"""
Data invariants the site silently depends on.

These are not "does the data look plausible" checks -- each one guards a
specific way the site breaks if the invariant is violated. The dependency graph,
the relation lists and the transitive diagram all resolve product references by
(gameset, name) at render time with no error handling, so a dangling reference
is a blank section or a thrown exception, not a degraded page.

    python3 -m unittest discover -s tests

Standard library only.
"""
import csv
import json
import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "data" / "index_cards.json"
CSV_FILE = ROOT / "data" / "index_cards.csv"
TEMPLATE = ROOT / "data" / "site_template.html"
BUILT = ROOT / "site" / "index.html"

CARDS_DATA = json.loads(CARDS.read_text(encoding="utf-8"))
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")

GAMESETS = {"Standard", "Alternative", "Food & Beverage"}
MONTHS_FULL = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


def slug(text):
    """The icon_file naming rule: non-alphanumerics collapse to single '_'."""
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9]", "_", text))


class TestProductKeys(unittest.TestCase):
    def test_ids_are_unique(self):
        dupes = [i for i, n in Counter(c["id"] for c in CARDS_DATA).items() if n > 1]
        self.assertEqual([], dupes)

    def test_gameset_name_pairs_are_unique(self):
        # byGameset()/name lookups in the site assume this; a collision would
        # silently resolve to whichever record happens to come first.
        pairs = Counter((c["gameset"], c["name"]) for c in CARDS_DATA)
        self.assertEqual([], [p for p, n in pairs.items() if n > 1])

    def test_gamesets_are_the_expected_three(self):
        self.assertEqual(GAMESETS, {c["gameset"] for c in CARDS_DATA})


class TestReferentialIntegrity(unittest.TestCase):
    """The invariants that keep the dependency graph from drawing holes."""

    def setUp(self):
        self.by_name = {(c["gameset"], c["name"]): c for c in CARDS_DATA}
        self.by_id = {c["id"]: c for c in CARDS_DATA}

    def test_every_input_material_resolves_within_its_gameset(self):
        dangling = [
            (c["id"], i["material"])
            for c in CARDS_DATA
            for i in c["inputs"]
            if (c["gameset"], i["material"]) not in self.by_name
        ]
        self.assertEqual([], dangling)

    def test_every_used_in_id_resolves(self):
        dangling = [
            (c["id"], u["id"])
            for c in CARDS_DATA
            for u in c["used_in"]
            if u["id"] not in self.by_id
        ]
        self.assertEqual([], dangling)

    def test_used_in_is_the_exact_inverse_of_inputs(self):
        # Both directions are stored denormalized, so they can drift apart. The
        # detail page reads used_in while the graph builds edges from inputs --
        # if they disagree, the two disagree on screen.
        forward = Counter(
            (c["gameset"], i["material"], c["name"]) for c in CARDS_DATA for i in c["inputs"]
        )
        backward = Counter(
            (c["gameset"], c["name"], u["product"]) for c in CARDS_DATA for u in c["used_in"]
        )
        self.assertEqual(forward, backward)

    def test_optional_livestock_references_resolve(self):
        for c in CARDS_DATA:
            for y in c.get("livestock_yields", []):
                self.assertIn((c["gameset"], y), self.by_name, f"{c['id']} yields {y!r}")
            for a in c.get("derived_from_livestock", []):
                self.assertIn((c["gameset"], a), self.by_name, f"{c['id']} from {a!r}")

    def test_production_graph_is_acyclic(self):
        # calcTier() walks this graph recursively; a cycle is a hang or a
        # wrong tier assignment, not a caught error.
        edges = {}
        for c in CARDS_DATA:
            edges[(c["gameset"], c["name"])] = [(c["gameset"], i["material"]) for i in c["inputs"]]
        WHITE, GREY, BLACK = 0, 1, 2
        colour = {k: WHITE for k in edges}

        def visit(node, path):
            colour[node] = GREY
            for nxt in edges.get(node, []):
                if colour.get(nxt) == GREY:
                    self.fail(f"cycle: {' -> '.join(n[1] for n in path + [node, nxt])}")
                if colour.get(nxt) == WHITE:
                    visit(nxt, path + [node])
            colour[node] = BLACK

        for node in edges:
            if colour[node] == WHITE:
                visit(node, [])


class TestIcons(unittest.TestCase):
    """Icons are populated by hand from the user's own copy of the game (see
    ATTRIBUTION.md), so the filenames are a contract with a human, not with a
    generator -- which makes them easy to get wrong and worth pinning."""

    def test_icon_filenames_are_unique(self):
        names = Counter(c["icon_file"] for c in CARDS_DATA)
        self.assertEqual([], [n for n, k in names.items() if k > 1])

    def test_icon_filenames_are_filesystem_and_url_safe(self):
        # No spaces, '&', apostrophes or non-ASCII: these are interpolated
        # straight into src="images/..." with no encoding.
        bad = [c["icon_file"] for c in CARDS_DATA if not re.fullmatch(r"[A-Za-z0-9_]+\.png", c["icon_file"])]
        self.assertEqual([], bad)

    def test_icon_filenames_are_prefixed_with_their_gameset(self):
        wrong = [
            (c["id"], c["icon_file"])
            for c in CARDS_DATA
            if not c["icon_file"].startswith(slug(c["gameset"]) + "_")
        ]
        self.assertEqual([], wrong)

    def test_no_case_insensitive_collisions(self):
        # macOS and Windows are case-insensitive; a collision means one icon
        # silently overwrites another when populated.
        lowered = Counter(c["icon_file"].lower() for c in CARDS_DATA)
        self.assertEqual([], [n for n, k in lowered.items() if k > 1])


class TestTaxonomy(unittest.TestCase):
    def test_every_classification_has_a_colour(self):
        """CLASS_SOLID in the template is the only classification->colour map.
        A classification with no entry renders a badge with no background."""
        block = re.search(r"const CLASS_SOLID = \{(.*?)\n\};", TEMPLATE_TEXT, re.S)
        assert block is not None, "CLASS_SOLID not found in template"
        mapped = set(re.findall(r'"([^"]+)":', block.group(1)))
        self.assertEqual(set(), {c["classification"] for c in CARDS_DATA} - mapped)

    def test_sellable_and_sale_index_never_disagree(self):
        for c in CARDS_DATA:
            self.assertEqual(
                bool(c["sellable"]), (c["sale_index"] or 0) > 0, f"{c['id']}: {c['sale_index']}"
            )

    def test_crops_carry_complete_growing_conditions(self):
        for c in CARDS_DATA:
            gc = c.get("growing_conditions")
            if gc is not None:
                self.assertEqual(
                    {"climate", "rainfall", "sowing_month", "harvesting_month"},
                    set(gc),
                    c["id"],
                )


class TestProductionRates(unittest.TestCase):
    """Fields added from RAW / FARMPROD / FARMLIVE. None of this appears in the
    game's own Farmer's Guide, so nothing outside this project would catch it
    going wrong."""

    def test_extraction_only_on_raw_materials(self):
        for c in CARDS_DATA:
            if "extraction" in c:
                self.assertEqual("Raw Material", c["classification"], c["id"])

    def test_extraction_is_complete(self):
        # measured_in is gone: output_unit now carries the commodity's unit for
        # every product, so extraction no longer needs its own copy.
        want = {"site", "unit", "speed", "resource_value", "max_sites"}
        for c in CARDS_DATA:
            if "extraction" in c:
                self.assertEqual(want, set(c["extraction"]), c["id"])
                self.assertIn(c["extraction"]["site"], {"Mine", "Lumber Mill", "Oil Well"})

    def test_livestock_production_modes_are_exclusive(self):
        """A product is harvested from a living animal or taken from a dead one,
        never both -- the shape of the record enforces which fields exist."""
        for c in CARDS_DATA:
            lp = c.get("livestock_production")
            if not lp:
                continue
            self.assertIn(lp["mode"], {"continuous", "slaughter"}, c["id"])
            if lp["mode"] == "slaughter":
                self.assertIn("slaughter_percent", lp, c["id"])
                self.assertNotIn("monthly_quantity", lp, c["id"])
            else:
                self.assertIn("monthly_quantity", lp, c["id"])
                self.assertNotIn("slaughter_percent", lp, c["id"])
                self.assertGreater(lp["monthly_quantity"], 0, c["id"])
                self.assertIn(lp["from_month"], MONTHS_FULL, c["id"])
                self.assertIn(lp["to_month"], MONTHS_FULL, c["id"])

    def test_livestock_production_only_on_derived_goods(self):
        for c in CARDS_DATA:
            if "livestock_production" in c:
                self.assertIn(c["raw_class"], {"LPRODUCT", "LSEMI"}, c["id"])

    def test_livestock_stats_only_on_animals(self):
        for c in CARDS_DATA:
            if "livestock_stats" in c:
                self.assertEqual("LSTOCK", c["raw_class"], c["id"])
                self.assertGreater(c["livestock_stats"]["weight"], 0, c["id"])

    def test_every_slaughter_product_can_be_quantified(self):
        """A percentage is meaningless without the weight it applies to, so every
        slaughter product must have at least one source animal carrying one."""
        by_key = {(c["gameset"], c["name"]): c for c in CARDS_DATA}
        for c in CARDS_DATA:
            lp = c.get("livestock_production")
            if not lp or lp["mode"] != "slaughter":
                continue
            sources = c.get("derived_from_livestock") or []
            self.assertTrue(sources, c["id"])
            weights = [by_key[(c["gameset"], a)].get("livestock_stats") for a in sources]
            self.assertTrue(all(weights), f"{c['id']}: a source animal has no weight")


class TestUnitsAndQuantities(unittest.TestCase):
    """output_unit was the project's one declared divergence, null for the 73
    products with no METHOD recipe. Conflating the unit with the quantity was the
    error: only the quantity was ever undefined."""

    def test_every_product_carries_a_unit(self):
        missing = [c["id"] for c in CARDS_DATA if not c.get("output_unit")]
        self.assertEqual([], missing)

    def test_output_quantity_is_absent_without_a_recipe(self):
        """A mine or farm produces at a rate, not in batches, so a per-run yield
        must not appear for anything with no inputs and no recipe."""
        for c in CARDS_DATA:
            if c["output_quantity"] is None:
                continue
            # Anything claiming a per-run quantity must have a recipe behind it.
            self.assertTrue(c["inputs"] or c.get("livestock_production"),
                            f"{c['id']} claims a yield with no recipe")

    def test_the_removed_fields_stay_removed(self):
        for c in CARDS_DATA:
            self.assertNotIn("icon_image_id", c, c["id"])
            self.assertNotIn("graphic_count", c, c["id"])

    def test_build_forbids_the_removed_fields(self):
        """The build is what stops them coming back, so the list has to be there."""
        build = (ROOT / "tools" / "build_site.py").read_text(encoding="utf-8")
        self.assertIn("FORBIDDEN_KEYS", build)
        self.assertIn("icon_image_id", build)
        self.assertIn("graphic_count", build)


class TestDerivedFields(unittest.TestCase):
    """Fields the dataset computes rather than reads from the game. Each was
    documented as following a rule but nothing checked that it did, which is the
    condition under which a documented rule quietly stops being true."""

    def test_production_technology_is_the_remainder_of_input_quality(self):
        """100 - sum(input quality_pct). Absent where there are no inputs, since
        there is no recipe to take a remainder of."""
        for c in CARDS_DATA:
            if not c["inputs"]:
                self.assertIsNone(c["production_technology_pct"], c["id"])
                continue
            want = 100 - sum(i["quality_pct"] or 0 for i in c["inputs"])
            self.assertAlmostEqual(want, c["production_technology_pct"] or 0,
                                   places=6, msg=c["id"])

    def test_derived_from_livestock_is_the_inverse_of_livestock_yields(self):
        forward = Counter((c["gameset"], c["name"], y)
                          for c in CARDS_DATA for y in (c.get("livestock_yields") or []))
        backward = Counter((c["gameset"], a, c["name"])
                           for c in CARDS_DATA for a in (c.get("derived_from_livestock") or []))
        self.assertEqual(forward, backward)

    def test_livestock_production_unit_restates_the_products_own_unit(self):
        """Both come from ITEM.UNIT, so the copy inside livestock_production is
        the product's output_unit under another name. The verifier checks
        output_unit against the game; this is what ties the copy to it."""
        for c in CARDS_DATA:
            lp = c.get("livestock_production") or {}
            if "unit" in lp:
                self.assertEqual(c["output_unit"], lp["unit"], c["id"])

    def test_all_year_is_the_season_spanning_january_to_december(self):
        """A restatement of from_month/to_month, which the verifier does check.
        The site branches on it, so a stale value would caption a seasonal yield
        as year-round."""
        for c in CARDS_DATA:
            lp = c.get("livestock_production") or {}
            if "all_year" in lp:
                want = lp["from_month"] == "January" and lp["to_month"] == "December"
                self.assertEqual(want, lp["all_year"], c["id"])

    def test_id_follows_its_convention(self):
        initial = {"Standard": "S", "Alternative": "A", "Food & Beverage": "F"}
        for c in CARDS_DATA:
            self.assertEqual(f"{initial[c['gameset']]} - {c['name']}", c["id"])

    def test_classification_and_industry_are_functions_of_raw_class(self):
        """Both are our grouping of the game's 32 class codes, not fields in the
        file. They are reproducible only while the mapping stays unambiguous."""
        for field in ("classification", "industry"):
            seen = {}
            for c in CARDS_DATA:
                seen.setdefault(c["raw_class"], set()).add(c[field])
            ambiguous = {k: v for k, v in seen.items() if len(v) > 1}
            self.assertEqual({}, ambiguous, f"{field} is not a function of raw_class")

    def test_the_dataset_makes_no_claim_about_its_own_provenance(self):
        """classification_source was the same sentence on every record. Provenance
        lives in docs/DECODING.md and is demonstrated by the verifier."""
        for c in CARDS_DATA:
            self.assertNotIn("classification_source", c, c["id"])


class TestCropPlants(unittest.TestCase):
    """Six crops have a distinct growing plant. PLANT rows are not products, so
    the plant rides along on the crop's record."""

    WITH_PLANT = {("Standard", "Rubber"), ("Standard", "Sugar"),
                  ("Alternative", "Coconut"), ("Alternative", "Flax Fiber"),
                  ("Food & Beverage", "Coffee"), ("Food & Beverage", "Tea")}

    def test_exactly_the_expected_crops_have_a_plant(self):
        got = {(c["gameset"], c["name"]) for c in CARDS_DATA if "plant" in c}
        self.assertEqual(self.WITH_PLANT, got)

    def test_plant_is_never_itself_a_product(self):
        """A PLANT row must not have leaked into the dataset as a product."""
        names = {(c["gameset"], c["name"]) for c in CARDS_DATA}
        for c in CARDS_DATA:
            if "plant" in c:
                self.assertNotIn((c["gameset"], c["plant"]["name"]), names, c["id"])

    def test_plant_icon_follows_the_naming_rule(self):
        for c in CARDS_DATA:
            if "plant" not in c:
                continue
            want = f"{slug(c['gameset'])}_{slug(c['plant']['name'])}.png"
            self.assertEqual(want, c["plant"]["icon_file"], c["id"])

    def test_only_crops_have_plants(self):
        for c in CARDS_DATA:
            if "plant" in c:
                self.assertIsNotNone(c.get("growing_conditions"), c["id"])


class TestCsvMirror(unittest.TestCase):
    """index_cards.csv is a hand-maintained flat projection with no generator,
    so nothing but this test stops it drifting from the JSON."""

    @staticmethod
    def _rows():
        with CSV_FILE.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_csv_describes_the_same_products(self):
        rows = self._rows()
        self.assertEqual(len(CARDS_DATA), len(rows))
        self.assertEqual(
            {(c["gameset"], c["name"]) for c in CARDS_DATA},
            {(r["gameset"], r["name"]) for r in rows},
        )

    def test_csv_scalars_match_the_json(self):
        rows = {(r["gameset"], r["name"]): r for r in self._rows()}
        for c in CARDS_DATA:
            row = rows[(c["gameset"], c["name"])]
            for field in ("id", "raw_class", "classification", "industry"):
                self.assertEqual(str(c[field]), row[field], f"{c['id']}.{field}")
            # JSON null renders as an empty CSV cell.
            self.assertEqual("" if c["category"] is None else c["category"], row["category"], c["id"])


class TestScenarios(unittest.TestCase):
    """The SCENARIOS array is authored inline in the template (it is the live,
    only source of truth for scenario goals). These checks catch a hand-edit
    that names something the data doesn't have."""

    def setUp(self):
        block = re.search(r"const SCENARIOS = \[(.*?)\n\];", TEMPLATE_TEXT, re.S)
        self.assertIsNotNone(block, "SCENARIOS array not found in template")
        self.block = block.group(1)
        self.raw_classes = {c["raw_class"] for c in CARDS_DATA}

    def _codes(self, field):
        return {
            code
            for group in re.findall(rf"{field}: \[([^\]]*)\]", self.block)
            for code in re.findall(r'"([^"]+)"', group)
        }

    def test_every_scenario_names_a_real_gameset(self):
        self.assertEqual(set(), set(re.findall(r'gameset: "([^"]+)"', self.block)) - GAMESETS)

    def test_scenario_keys_are_unique(self):
        keys = re.findall(r'\{ key: "([A-Z]+)"', self.block)
        self.assertEqual(20, len(keys), "expected the 20 decoded scenarios")
        self.assertEqual(len(keys), len(set(keys)))

    def test_excluded_and_dominate_classes_are_real_itemclas_codes(self):
        # These are the game's own raw ITEMCLAS codes, not display names -- a
        # display name here silently matches no product and the restriction
        # quietly stops applying.
        self.assertEqual(set(), self._codes("excludedClasses") - self.raw_classes)
        self.assertEqual(set(), self._codes("dominateClasses") - self.raw_classes)

    def test_dominate_industries_are_real_industries_or_retailing(self):
        allowed = {c["industry"] for c in CARDS_DATA} | {"Retailing"}
        self.assertEqual(set(), self._codes("dominateIndustries") - allowed)

    def test_the_docs_pair_each_scenario_title_with_the_right_filename(self):
        # docs/DECODING.md writes scenarios as "Title (`STEM`)" in its evidence
        # tables. Neither half is derivable from the other -- UK.SCN is Rule
        # Britannia -- so a wrong pairing sends a reader to the wrong file with
        # nothing to catch them. Check both directions against the live array.
        names = dict(re.findall(r'key: "([A-Z]+)", name: "([^"]+)"', self.block))
        doc = (ROOT / "docs" / "DECODING.md").read_text(encoding="utf-8")
        # Anchored on the known strings rather than a "Title (`STEM`)" pattern:
        # the same shape spells out class codes -- Frozen Beef (`LPRODUCT`) --
        # and an unanchored title capture runs back through the sentence.
        seen = 0
        for stem, title in names.items():
            # Right stem, wrong title.
            for m in re.finditer(r"\(`%s`\)" % stem, doc):
                before = doc[: m.start()].rstrip()
                self.assertTrue(before.endswith(title), f"`{stem}` is titled {before[-40:]!r}")
                seen += 1
            # Right title, wrong stem.
            for found in re.findall(re.escape(title) + r" \(`([A-Z_]+)`\)", doc):
                self.assertEqual(stem, found, f"{title} is {stem}.SCN, not {found}.SCN")
        self.assertTrue(seen, "no Title (`STEM`) pairs found -- has the convention changed?")


class TestBuildContract(unittest.TestCase):
    def test_template_has_exactly_one_placeholder(self):
        self.assertEqual(1, TEMPLATE_TEXT.count("__PRODUCTS_JSON__"))

    def test_built_site_has_no_stray_script_terminator(self):
        # The payload is inlined into a <script>, an HTML raw-text element: the
        # parser ends the script at the first "</script" it sees, even inside a
        # JS string. The site has exactly one inline script and loads nothing
        # external, so exactly one terminator may exist.
        self.assertEqual(1, BUILT.read_text(encoding="utf-8").lower().count("</script"))

    def test_built_site_loads_no_external_resources(self):
        """Self-contained by design: no CDN, no vendored bundle, works over
        file://. A src=/href= to a script or stylesheet would reintroduce both a
        network dependency and a third-party license obligation."""
        html = BUILT.read_text(encoding="utf-8")
        self.assertNotIn("<script src", html)
        self.assertNotIn('rel="stylesheet"', html)

    def test_built_site_contains_no_placeholder(self):
        self.assertNotIn("__PRODUCTS_JSON__", BUILT.read_text(encoding="utf-8"))


class TestPalette(unittest.TestCase):
    """Classification colours have to stay tellable apart at a 12px swatch. This
    computes CIELAB distance rather than eyeballing hex values."""

    @staticmethod
    def _lab(hex_):
        def lin(c):
            c /= 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        h = hex_.lstrip("#")
        r, g, b = (lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))
        x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
        y = r * 0.2126 + g * 0.7152 + b * 0.0722
        z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
        f = lambda v: v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116
        fx, fy, fz = f(x), f(y), f(z)
        return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))

    def _palette(self):
        block = re.search(r"const PALETTE = \{(.*?)\n\};", TEMPLATE_TEXT, re.S)
        self.assertIsNotNone(block, "PALETTE not found")
        return dict(re.findall(r"(\w+):\s*'(#[0-9A-Fa-f]{6})'", block.group(1)))

    def test_palette_is_the_single_source_of_colour(self):
        """Every classification colour comes from PALETTE, not a literal. The
        manufactured red used to be written out in four places."""
        block = re.search(r"const CLASS_SOLID = \{(.*?)\n\};", TEMPLATE_TEXT, re.S).group(1)
        self.assertEqual([], re.findall(r"#[0-9A-Fa-f]{6}", block))

    def test_colours_are_mutually_distinguishable(self):
        palette = self._palette()
        self.assertGreaterEqual(len(palette), 7)
        too_close = []
        names = sorted(palette)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                la, lb = self._lab(palette[a]), self._lab(palette[b])
                d = sum((la[k] - lb[k]) ** 2 for k in range(3)) ** 0.5
                if d < 15:
                    too_close.append(f"{a}/{b}={d:.1f}")
        self.assertEqual([], too_close)


class TestAccessibility(unittest.TestCase):
    """Guards the accessibility properties of the built page. These are cheap
    structural checks, not a substitute for testing with an actual screen
    reader -- but they stop the specific regressions that made the site
    mouse-only in the first place."""

    HTML = BUILT.read_text(encoding="utf-8")
    TEMPLATE = TEMPLATE_TEXT

    # The three checks below duplicate ground the Playwright harness covers far
    # better -- but that harness is not a deploy gate (it downloads a browser), and
    # this suite is. Each guards a defect the harness found in the accessibility
    # tree and nothing else could see, so each needs to fail in the fast suite too.

    def test_activatable_is_never_applied_to_a_list_item(self):
        """role="button" replaces the implicit listitem role, so a <ul> of them
        stops being a list: no "list, 3 items", no positions, and axe reports
        "<ul> must only directly contain <li>". Rows wrap their contents in a
        span that carries it instead."""
        self.assertNotIn("<li ${ACTIVATABLE}", self.TEMPLATE)
        self.assertIn('class="rel-item" ${ACTIVATABLE}', self.TEMPLATE)

    def test_monogram_tiles_are_hidden_from_assistive_tech(self):
        """The initial is drawn by CSS content: attr(data-initial), which Chromium
        exposes to the accessibility tree -- so without aria-hidden every product
        announces as "AC Air Conditioner". alt="" cannot reach generated content."""
        for opener in re.findall(r'<span class="picon[^>]*>', self.TEMPLATE):
            self.assertIn("aria-hidden", opener, opener)

    def test_the_composition_bar_pairs_each_name_with_its_percentage(self):
        """The bar's segments carry percentages and its legend carries names, so
        the association was colour-only -- unusable to a reader and to anyone who
        cannot separate the swatches. The legend must carry both, and the bar is
        then decoration."""
        self.assertIn('class="bar" aria-hidden="true"', self.TEMPLATE)
        self.assertIn("${inp.quality_pct}%</span>", self.TEMPLATE)
        self.assertIn("Production Technology &middot; ${p.production_technology_pct}%"
                      .replace("&middot;", "\u00b7"), self.TEMPLATE)

    def test_has_viewport_meta(self):
        # Without it, mobile browsers scale a 980px layout down to ~38%.
        self.assertIn('name="viewport"', self.HTML)

    def test_label_value_pairs_use_a_description_list(self):
        """A CSS grid of anonymous divs pairs a label with its value visually but
        not programmatically. Every kv block is a <dl>."""
        self.assertNotIn('<div class="k">', self.HTML)
        self.assertIn('<dl class="kv"', self.HTML)
        self.assertEqual(self.HTML.count('<dl class="kv"'), self.HTML.count("</dl>"))

    def test_tables_are_not_display_block(self):
        """Setting display:block on a <table> to make it scroll strips the
        element's implicit ARIA table role, so a screen reader stops announcing
        rows and columns. Wide tables use a .table-scroll wrapper instead."""
        for line in self.HTML.split("\n"):
            if "display: block" in line and ("-table" in line or "table {" in line):
                self.fail(f"table set to display:block: {line.strip()}")
        self.assertIn(".table-scroll { overflow-x: auto;", self.HTML)

    def test_has_responsive_and_print_styles(self):
        self.assertIn("@media (max-width: 760px)", self.HTML)
        self.assertIn("@media print", self.HTML)

    def test_document_language_and_title(self):
        self.assertIn('<html lang="en">', self.HTML)
        self.assertIn("<title>", self.HTML)
        self.assertIn('name="description"', self.HTML)

    def test_view_tabs_are_buttons_in_a_tablist(self):
        self.assertIn('role="tablist"', self.HTML)
        for tab in ("viewGrid", "viewGraph", "viewAlmanac"):
            m = re.search(rf'<button[^>]*id="{tab}"[^>]*>', self.HTML)
            self.assertIsNotNone(m, f"{tab} is not a <button>")
            self.assertIn('role="tab"', m.group(0))
            self.assertIn("aria-controls=", m.group(0))

    def test_panes_are_labelled_tabpanels(self):
        for pane in ("grid-view", "graph-view", "almanac-view"):
            m = re.search(rf'<div id="{pane}"[^>]*>', self.HTML)
            self.assertIsNotNone(m, pane)
            self.assertIn('role="tabpanel"', m.group(0))
            self.assertIn("aria-labelledby=", m.group(0))

    def test_form_controls_have_labels(self):
        # A placeholder is not an accessible name.
        self.assertIn('<label class="sr-only" for="searchBox">', self.HTML)
        self.assertIn('<label for="scenarioSelect">', self.HTML)

    def test_chip_groups_are_named(self):
        for group in ("categoryChips", "classChips", "industryChips", "sellableChips"):
            m = re.search(rf'<div id="{group}"[^>]*>', self.HTML)
            self.assertIsNotNone(m, group)
            self.assertIn('role="group"', m.group(0))
            self.assertIn("aria-labelledby=", m.group(0))

    def test_has_live_region_for_result_count(self):
        self.assertIn('id="resultStatus"', self.HTML)
        self.assertIn('aria-live="polite"', self.HTML)

    def test_has_visible_focus_indicator(self):
        # There was no focus style at all, so even reachable controls gave no
        # indication of keyboard position.
        self.assertIn(":focus-visible", self.HTML)

    def test_has_skip_link_to_content(self):
        """~40 sidebar controls precede the content on every view (WCAG 2.4.1)."""
        self.assertIn('class="skip-link" href="#main-content"', self.HTML)
        self.assertIn('id="main-content"', self.HTML)

    def test_heading_levels_do_not_skip(self):
        """The document went h1 -> h3, with no h2 outside the detail view."""
        levels = sorted({int(m) for m in re.findall(r"<h([1-6])[ >]", self.HTML)})
        self.assertEqual(list(range(1, len(levels) + 1)), levels, f"levels present: {levels}")

    def test_only_one_h1(self):
        self.assertEqual(1, len(re.findall(r"<h1[ >]", self.HTML)))

    def test_honours_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.HTML)

    def test_tablists_use_a_roving_tabindex(self):
        """A tablist that is entirely Tab stops contradicts its own role: Tab
        should reach the strip once, arrows should move within it."""
        self.assertIn("""tab.setAttribute('tabindex', v === view ? '0' : '-1')""", self.HTML)

    def test_detail_view_has_an_accessible_name(self):
        m = re.search(r'<div id="detail-view"[^>]*>', self.HTML)
        self.assertIsNotNone(m)
        self.assertIn('aria-labelledby="detailHeading"', m.group(0))

    def test_has_noscript_fallback(self):
        self.assertIn("<noscript>", self.HTML)

    def test_paired_title_graphic_collapses_without_artwork(self):
        """A crop shown with its plant has two tiles. With no artwork both would
        render as monograms -- "SC" and "S" for Sugar -- which conveys nothing the
        product's alone does not, so the plant tile is dropped."""
        self.assertIn(".title-art .picon-empty.plant-tile { display: none; }", self.HTML)

    def test_the_collapse_is_scoped_to_the_title_graphic(self):
        """In the Almanac the plant is the ONLY tile, so it must keep its
        monogram; an unscoped rule would blank that column without artwork."""
        for line in self.HTML.split("\n"):
            if ".picon-empty.plant-tile" in line and "{" in line:
                self.assertIn(".title-art", line, line.strip())

    def test_no_hardcoded_white_on_coloured_badges(self):
        """Badge foregrounds are computed by onColor(); a literal `color: white`
        on .badge/.badge-lg/.bar-seg is what produced 1.90:1 text."""
        for rule in (".badge {", ".badge-lg {", ".bar-seg {"):
            i = self.HTML.index(rule)
            decl = self.HTML[i:self.HTML.index("}", i)]
            self.assertNotIn("color: white", decl, rule)


class TestGrammars(unittest.TestCase):
    """The binary grammars in docs/formats/ are the project's format
    specification. These are cheap structural checks -- the real verification is
    tools/verify_against_game.py, which implements the .SET grammar and reads a
    retail copy with it."""

    GRAMMARS = sorted((ROOT / "docs" / "formats").glob("*.grammar"))

    def test_grammars_are_present(self):
        self.assertGreaterEqual(len(self.GRAMMARS), 5, "expected the documented grammar set")

    def test_grammars_are_well_formed_xml(self):
        import xml.etree.ElementTree as ET
        for path in self.GRAMMARS:
            with self.subTest(path.name):
                ET.parse(path)      # raises on malformed XML

    # Both docs table the grammars, so both can fall behind the directory: a
    # grammar added without a row reads as a complete list that is quietly one
    # short. Naming them by filename in backticks makes each table checkable
    # against the directory in both directions.
    DOCS = ("docs/formats/README.md", "docs/DECODING.md")

    def test_both_doc_tables_list_every_grammar(self):
        # Deliberately the table rows, not the whole document: a grammar named
        # once in prose satisfies a substring search while its table row is
        # still missing, which is how DECODING.md came to introduce five and
        # then table four.
        stems = {p.stem for p in self.GRAMMARS}
        for rel in self.DOCS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            rows = set(re.findall(r"(?m)^\| `(Capitalism [^`]+)` \|", text))
            self.assertEqual(stems, rows, f"{rel}'s table does not match docs/formats/")

    def test_each_grammar_calls_itself_what_its_file_is_called(self):
        # Synalyze It! lists a grammar by its name attribute, not its filename,
        # so a mismatch means the docs name one thing and the tool shows
        # another with no way to tell they are the same grammar.
        import xml.etree.ElementTree as ET
        for path in self.GRAMMARS:
            declared = ET.parse(path).getroot().find("grammar").get("name")
            self.assertEqual(path.stem, declared, f"{path.name} calls itself {declared!r}")

    def test_neither_doc_names_a_grammar_that_does_not_exist(self):
        stems = {p.stem for p in self.GRAMMARS}
        for rel in self.DOCS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for named in re.findall(r"`(Capitalism [^`]+)`", text):
                self.assertIn(named, stems, f"{rel} names a grammar with no file")

    def test_scn_grammar_offsets_match_the_documented_ones(self):
        """The SCN grammar is hand-written and has not been opened in Synalyze
        It!, so at minimum its cumulative element lengths must put each field at
        the offset docs/DECODING.md and the verifier both rely on."""
        import xml.etree.ElementTree as ET
        path = ROOT / "docs" / "formats" / "Capitalism Plus SCN Goal Header.grammar"
        grammar = ET.parse(path).getroot().find("grammar")
        structs = {s.get("id"): s for s in grammar.findall("structure")}
        expected = {"Years": 179, "Bonus": 183, "Dominate Industries": 305,
                    "Excluded Classes": 315, "Dominate Classes": 415}
        offset, seen = 0, {}
        for child in structs["1"]:
            if child.tag == "description":
                continue
            if child.tag == "structref":
                sub = structs[child.get("structure").split(":")[1]]
                size = sum(int(x.get("length")) for x in sub
                           if x.tag in ("number", "binary"))
            else:
                size = int(child.get("length"))
            seen[child.get("name")] = offset
            offset += size
        for field, want in expected.items():
            self.assertEqual(want, seen.get(field), f"{field} is at the wrong offset")


class TestIconLicensingHold(unittest.TestCase):
    """The icons are withheld from version control pending a licensing
    determination (ATTRIBUTION.md), enforced today only by .gitignore. This
    asserts the TRACKED tree is clean, so the decision stays a decision rather
    than eroding by accident.

    Deliberately checks git, not the filesystem: the README tells you to
    populate site/images/ locally from your own copy of the game, so a working
    copy full of PNGs is correct and must not fail the suite."""

    def test_no_icon_assets_are_tracked_by_git(self):
        import shutil
        import subprocess

        if shutil.which("git") is None or not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "site/images"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        # Inverted when Enlight granted permission: the question is no longer
        # "is anything here?" but "is exactly the granted set here?". The grant
        # covers the game's product icons, so a file that does not correspond to
        # a dataset entry is artwork nobody permitted anything about.
        expected = {"site/images/.gitkeep"}
        for card in CARDS_DATA:
            expected.add("site/images/" + card["icon_file"])
            if card.get("plant"):
                expected.add("site/images/" + card["plant"]["icon_file"])
        self.assertEqual(
            expected,
            set(tracked),
            "tracked artwork must match the dataset exactly -- see ATTRIBUTION.md",
        )


if __name__ == "__main__":
    unittest.main()
