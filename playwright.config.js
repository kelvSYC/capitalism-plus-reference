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

  // A snapshot written by a stray --update-snapshots run is worse than a failure,
  // because it records whatever the tree happened to be. CI never updates.
  forbidOnly: !!process.env.CI,
  updateSnapshots: process.env.CI ? "none" : "missing",

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
