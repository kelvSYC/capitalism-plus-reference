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
import os
import re
import subprocess
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
