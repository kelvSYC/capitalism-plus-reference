#!/usr/bin/env python3
"""
Run the verifier against a real copy of the game, if one is available.

Skips when it is not. The game is not a build dependency and cannot be one --
it is a commercial product nobody can assume is present, and the site builds and
serves without it. But when a copy IS to hand, this is the only test in the suite
that checks the data against its actual source rather than against itself.

    CAPITALISM_GAME_DIR="/path/to/game" python3 -m unittest discover -s tests

The directory is the one containing GAMESET/ and CapPlus.gog.
"""
import json
import os
import re
import struct
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "tools" / "verify_against_game.py"


def game_dir():
    configured = os.environ.get("CAPITALISM_GAME_DIR")
    if configured and (Path(configured) / "GAMESET").is_dir():
        return configured
    return None


class TestAgainstGameFiles(unittest.TestCase):
    def test_committed_data_matches_the_game(self):
        """Product dataset and scenario goals both agree with the game's files.

        A failure here means the committed data is wrong: Capitalism Plus is a
        1996 DOS title, so its content does not change under us.
        """
        directory = game_dir()
        if directory is None:
            self.skipTest("set CAPITALISM_GAME_DIR to a game directory to run this")
        result = subprocess.run(
            [sys.executable, str(VERIFIER), "--game-dir", directory],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode,
                         f"verifier reported problems:\n{result.stdout}\n{result.stderr}")
        # Guard against a verifier that silently checks nothing: exit 0 with an
        # empty run would otherwise look like a pass. Matched by pattern, not by
        # line position -- the summary is followed by the divergence explanation.
        totals = re.findall(r"^(\d+) checks passed", result.stdout, re.M)
        self.assertTrue(totals, f"no summary line found:\n{result.stdout}")
        self.assertGreater(int(totals[-1]), 1000,
                           f"suspiciously few checks ran:\n{result.stdout}")


class TestDatasetIsComplete(unittest.TestCase):
    def test_augmenting_from_the_game_changes_nothing(self):
        """The committed dataset already holds everything augment_from_game.py
        would write, so a fresh run against a retail copy is a no-op.

        This is what separates the tool from a build step. index_cards.json is
        complete as committed -- the site builds, and the verifier passes, with
        no game present -- and the tool exists so the five fields it wrote stay
        reproducible rather than becoming folklore. If this ever reports work to
        do, the dataset shipped short of what the game says, which is the claim
        the tool's existence would otherwise quietly undermine.
        """
        directory = game_dir()
        if directory is None:
            self.skipTest("set CAPITALISM_GAME_DIR to a game directory to run this")
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "augment_from_game.py"),
             "--game-dir", directory, "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("0 fields added, 0 updated, 0 removed", result.stdout)


class TestPaletteFormat(unittest.TestCase):
    """`.RES` is an extension, not a format: 30 files share it and only the two
    palettes parse as one. That is why the Palette grammar sets no
    fileextension -- auto-associating it would point it at MUSIC.RES."""

    PALETTES = {"PAL_STD.RES", "IFCOLOR.RES"}
    TAG = 0xB123

    def _resources(self):
        directory = game_dir()
        if directory is None:
            self.skipTest("set CAPITALISM_GAME_DIR to a game directory to run this")
        return sorted((Path(directory) / "RESOURCE").glob("*.RES"))

    def test_exactly_two_res_files_are_palettes(self):
        # Both halves of the 8-byte header identify the format: the file states
        # its own length, then carries a constant tag. Neither holds for the
        # other 28, so the pair is decidable from the bytes rather than by name.
        matched = set()
        for path in self._resources():
            head = path.read_bytes()[:8]
            size, tag = struct.unpack("<II", head)
            if size == path.stat().st_size and tag == self.TAG:
                matched.add(path.name)
        self.assertEqual(self.PALETTES, matched)

    def test_a_palette_is_eight_bytes_then_256_rgb_triples(self):
        for path in self._resources():
            if path.name in self.PALETTES:
                self.assertEqual(8 + 256 * 3, path.stat().st_size, path.name)


class TestPngRoundTrip(unittest.TestCase):
    """The PNG writer is hand-rolled -- the standard library has no encoder and
    the extractor deliberately has no dependencies -- so it is the riskiest code
    in the tool. This needs no game files."""

    def test_written_png_reads_back_identically(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from extract_icons import decode_png_rgb, write_png

        width, height = 7, 5      # deliberately not square, and not a round number
        rgb = bytes((x * 37 + y * 11 + c * 83) % 256
                    for y in range(height) for x in range(width) for c in range(3))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "probe.png"
            write_png(target, width, height, rgb)
            got_w, got_h, got_rgb = decode_png_rgb(target)
        self.assertEqual((width, height), (got_w, got_h))
        self.assertEqual(rgb, got_rgb)

    def test_reader_rejects_a_format_it_cannot_handle(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from extract_icons import decode_png_rgb
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.png"
            bad.write_bytes(b"not a png at all")
            with self.assertRaises(ValueError):
                decode_png_rgb(bad)


class TestIconExtraction(unittest.TestCase):
    def test_extractor_finds_an_icon_for_every_product(self):
        """Every product must resolve to an archive entry, plus the growing plant
        for the crops that have one. A missing match would silently leave a
        monogram tile in place of artwork.

        The expected count is derived from the dataset rather than written in, so
        adding a product or a plant cannot make this fail spuriously -- nor pass
        while quietly skipping something.
        """
        directory = game_dir()
        if directory is None:
            self.skipTest("set CAPITALISM_GAME_DIR to a game directory to run this")
        cards = json.loads((ROOT / "data" / "index_cards.json").read_text(encoding="utf-8"))
        expected = len(cards) + sum(1 for c in cards if c.get("plant"))
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "extract_icons.py"),
             "--game-dir", directory, "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{expected} icons would be written", result.stdout)


class TestDocumentedCounts(unittest.TestCase):
    """Numbers quoted in prose go stale silently. Two have already: the README
    described the site as mouse-only long after the accessibility work, and three
    documents disagreed about how many checks the verifier runs."""

    DOCS = ("README.md", "docs/DECODING.md", "docs/formats/README.md")

    def _claims(self):
        found = {}
        for name in self.DOCS:
            text = (ROOT / name).read_text(encoding="utf-8")
            for m in re.finditer(r"([0-9][0-9,]*) checks", text):
                found.setdefault(m.group(1).replace(",", ""), []).append(name)
        return found

    def test_the_docs_agree_with_each_other(self):
        """Every "N checks" in the docs is either the verifier's total or the
        scenario subtotal it states separately."""
        claims = self._claims()
        self.assertTrue(claims, "no counts found; has the wording changed?")
        totals = {c for c in claims if c != "100"}
        self.assertEqual(1, len(totals),
                         f"documents disagree about the total: { {c: claims[c] for c in totals} }")

    def test_the_documented_total_is_what_the_verifier_reports(self):
        directory = game_dir()
        if directory is None:
            self.skipTest("set CAPITALISM_GAME_DIR to a game directory to run this")
        result = subprocess.run(
            [sys.executable, str(VERIFIER), "--game-dir", directory],
            capture_output=True, text=True,
        )
        actual = re.findall(r"^(\d+) checks passed", result.stdout, re.M)[-1]
        totals = {c for c in self._claims() if c != "100"}
        self.assertEqual({actual}, totals,
                         f"docs claim {totals}, verifier reports {actual}")


class TestVerifierWithoutGame(unittest.TestCase):
    """The verifier must be honest when it has nothing to check, rather than
    exiting 0 and looking like a pass."""

    def test_reports_that_it_verified_nothing(self):
        env = {k: v for k, v in os.environ.items() if k != "CAPITALISM_GAME_DIR"}
        result = subprocess.run([sys.executable, str(VERIFIER)],
                                capture_output=True, text=True, env=env)
        self.assertEqual(2, result.returncode)
        self.assertIn("Nothing verified", result.stdout)


if __name__ == "__main__":
    unittest.main()
