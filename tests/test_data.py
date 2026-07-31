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


class TestAccessibility(unittest.TestCase):
    """Guards the accessibility properties of the built page. These are cheap
    structural checks, not a substitute for testing with an actual screen
    reader -- but they stop the specific regressions that made the site
    mouse-only in the first place."""

    HTML = BUILT.read_text(encoding="utf-8")

    def test_has_viewport_meta(self):
        # Without it, mobile browsers scale a 980px layout down to ~38%.
        self.assertIn('name="viewport"', self.HTML)

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

    def test_has_noscript_fallback(self):
        self.assertIn("<noscript>", self.HTML)

    def test_no_hardcoded_white_on_coloured_badges(self):
        """Badge foregrounds are computed by onColor(); a literal `color: white`
        on .badge/.badge-lg/.bar-seg is what produced 1.90:1 text."""
        for rule in (".badge {", ".badge-lg {", ".bar-seg {"):
            i = self.HTML.index(rule)
            decl = self.HTML[i:self.HTML.index("}", i)]
            self.assertNotIn("color: white", decl, rule)


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
        self.assertEqual(
            ["site/images/.gitkeep"],
            tracked,
            "only .gitkeep may be tracked under site/images until the icon "
            "licensing question in ATTRIBUTION.md is resolved",
        )


if __name__ == "__main__":
    unittest.main()
