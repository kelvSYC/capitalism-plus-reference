// @ts-check
//
// Accessibility harness config. Separate from tests/site_behaviour.js, which
// splices the inline script against a hand-written DOM stub -- that stub has no
// accessibility tree, so nothing there can answer "what would a screen reader
// say". This config drives a real browser to get a real tree.
//
// Served over HTTP rather than opened as file://, for two reasons: Chromium
// refuses to load ES modules from file:// (which the virtual screen reader needs),
// and HTTP is what a visitor actually gets. The server is python3's stdlib
// http.server -- the repo already requires Python, so this adds no dependency.
const { defineConfig, devices } = require("@playwright/test");

const PORT = 8321;

module.exports = defineConfig({
  testDir: "./tests/a11y",
  fullyParallel: true,

  forbidOnly: !!process.env.CI,

  // A snapshot written by a stray update run is worse than a failure: it records
  // whatever the tree happened to be and calls it correct. So recording is opt-in
  // through an explicit variable rather than inferred, and CI refuses by default.
  //
  // "changed" rather than "missing" when recording, because a deliberate
  // improvement to the markup makes existing snapshots MISMATCH, not disappear --
  // and "missing" leaves those untouched, so a re-record run reports failures and
  // silently rewrites nothing. What keeps "changed" honest is not the mode but the
  // workflow: it uploads what it wrote as an artifact for review instead of
  // committing it, so a diff is still read by a person before it lands.
  updateSnapshots: process.env.A11Y_RECORD_SNAPSHOTS
    ? "changed"
    : process.env.CI
      ? "none"
      : "missing",

  // One canonical set of snapshots, not one per platform. They are recorded and
  // checked on CI's Linux/Chromium, so a platform-suffixed path would let a
  // second set appear from someone's laptop and quietly diverge. A real
  // difference between platforms should surface as a failure to look at.
  snapshotPathTemplate: "{testDir}/__snapshots__/{testFileName}/{arg}{ext}",

  // No retries: an accessibility assertion that passes on the second attempt is
  // reporting a race in the page, which is itself the finding.
  retries: 0,

  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : [["list"]],

  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: {
    // Serves the built artifact -- the same bytes the deploy uploads and
    // build_site.py --check guards. Testing the template instead would test
    // something no visitor ever loads.
    command: `python3 -m http.server ${PORT} --directory site --bind 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    stdout: "ignore",
  },
});
