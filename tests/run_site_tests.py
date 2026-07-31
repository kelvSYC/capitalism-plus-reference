#!/usr/bin/env python3
"""
Run tests/site_behaviour.js against the BUILT site.

The site is one self-contained HTML file with no module boundary, so there is
nothing to import and no way to unit-test its functions in isolation. This
splices the real inline <script> out of site/index.html into the marker in
site_behaviour.js and runs the result under whatever JS engine is available.
Testing the shipped artifact rather than a copy means a build-step regression
(bad substitution, mangled encoding) fails here too.

    python3 tests/run_site_tests.py

Engines, in preference order: node, bun, deno, then macOS's built-in
JavaScriptCore (jsc) so this works on a stock Mac with no toolchain installed.
Exits 1 if no engine is found -- silently skipping would make CI green for the
wrong reason.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILT = ROOT / "site" / "index.html"
HARNESS = Path(__file__).resolve().parent / "site_behaviour.js"
MARKER = "//__SITE_SCRIPT__"

JSC_PATHS = [
    "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc",
    "/System/Library/Frameworks/JavaScriptCore.framework/Resources/jsc",
]


def find_engine():
    for name in ("node", "bun", "deno"):
        path = shutil.which(name)
        if path:
            return [path, "run"] if name == "deno" else [path]
    for candidate in JSC_PATHS:
        if Path(candidate).exists():
            return [candidate]
    return None


def extract_inline_script(html: str) -> str:
    """The site's single inline <script> block -- it vendors nothing, so there is only one."""
    # Splicing takes the FIRST block. If a second one ever appears, the tests
    # would keep passing while silently exercising only part of the site, so
    # make that a failure rather than a quiet gap in coverage.
    found = html.count("<script")
    if found != 1:
        sys.exit(f"error: expected exactly one <script> in site/index.html, found {found}")
    try:
        after = html.split("\n<script>\n", 1)[1]
    except IndexError:
        sys.exit("error: no inline <script> block found in site/index.html")
    return after.split("\n</script>", 1)[0]


def main() -> int:
    engine = find_engine()
    if engine is None:
        print(
            "error: no JavaScript engine found (looked for node, bun, deno, jsc).\n"
            "       Install Node.js to run the behavioural tests.",
            file=sys.stderr,
        )
        return 1

    if not BUILT.exists():
        sys.exit(f"error: {BUILT.relative_to(ROOT)} missing -- run: python3 tools/build_site.py")

    harness = HARNESS.read_text(encoding="utf-8")
    if harness.count(MARKER) != 1:
        sys.exit(f"error: expected exactly one {MARKER} in {HARNESS.name}")

    spliced = harness.replace(MARKER, extract_inline_script(BUILT.read_text(encoding="utf-8")))

    # Write next to the harness so a stack trace's line numbers line up with a
    # file the developer can actually open.
    tmp = HARNESS.with_name("_site_behaviour.generated.js")
    tmp.write_text(spliced, encoding="utf-8")
    try:
        print(f"running {HARNESS.name} under {Path(engine[0]).name}")
        return subprocess.run(engine + [str(tmp)]).returncode
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
