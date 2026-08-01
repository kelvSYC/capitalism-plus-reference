// What a screen reader would SAY, via @guidepup/virtual-screen-reader.
//
// The virtual reader is a simulator: it computes announcements from the real
// accessibility tree of a real browser, but it is not VoiceOver or NVDA. It
// catches wrong or missing announcements and wrong reading order. It cannot
// catch real-reader quirks -- notably whether an aria-live region survives being
// replaced by innerHTML, which the site's own comment on #resultStatus worries
// about. That one needs Guidepup driving a real reader, run by hand.
//
// Expectations are SNAPSHOTS, not hand-written strings. Writing the phrasing by
// hand would record what someone assumed a reader says; recording it and
// reviewing the diff records what one actually says. Assertions that do not
// depend on phrasing are written out longhand below.
const { test, expect } = require("@playwright/test");
const { PRODUCT, showView } = require("./views");

// The package ships a browser bundle (exports "./browser.js", also its unpkg
// entry). Chromium will not import a module from file://, so it is served to the
// page through a route rather than inlined -- an inlined ES module cannot expose
// its named exports to the test.
const VSR = require.resolve("@guidepup/virtual-screen-reader/browser.js");

async function installReader(page) {
  await page.route("**/__vsr.js", (route) =>
    route.fulfill({ path: VSR, contentType: "text/javascript" })
  );
  await page.addScriptTag({
    type: "module",
    content: `import { virtual } from "/__vsr.js"; window.__virtual = virtual;`,
  });
  await page.waitForFunction(() => Boolean(window.__virtual));
}

// Drives the reader over `steps` interactions and returns everything it said.
async function speak(page, steps) {
  return page.evaluate(async (n) => {
    const virtual = window.__virtual;
    await virtual.start({ container: document.body });
    for (let i = 0; i < n; i++) await virtual.next();
    const log = await virtual.spokenPhraseLog();
    await virtual.stop();
    return log;
  }, steps);
}

test.beforeEach(async ({ page }) => {
  await page.goto("/index.html");
  await installReader(page);
});

test("the first things a reader reaches", async ({ page }) => {
  // The skip link exists because ~40 sidebar controls precede the content on
  // every view. If it is not among the first announcements, it is not doing its
  // job however correct its markup is.
  const spoken = await speak(page, 6);
  expect(spoken.join("\n")).toMatchSnapshot("entry-announcements.txt");
  expect(spoken.join(" ").toLowerCase()).toContain("skip");
});

test("the view tabs announce their state", async ({ page }) => {
  const spoken = await page.evaluate(async () => {
    const virtual = window.__virtual;
    await virtual.start({ container: document.getElementById("viewGrid").parentElement });
    const log = [];
    for (let i = 0; i < 4; i++) {
      await virtual.next();
      log.push(await virtual.lastSpokenPhrase());
    }
    await virtual.stop();
    return log;
  });
  expect(spoken.join("\n")).toMatchSnapshot("tablist-announcements.txt");
  // Phrasing varies between readers; the semantics must not. A tablist whose
  // active tab is not conveyed leaves a reader unable to tell where they are.
  const joined = spoken.join(" ").toLowerCase();
  expect(joined).toContain("tab");
  expect(joined).toMatch(/selected|current/);
});

test("label and value are read as a pair on the detail page", async ({ page }) => {
  // The <dl>/<dt>/<dd> conversion exists so "Site" and "Mine" arrive joined
  // rather than as two adjacent runs of text. This is the assertion that would
  // have failed before that change.
  await page.locator(PRODUCT).first().click();
  await page.waitForSelector("#detail-view:visible");
  const spoken = await page.evaluate(async () => {
    const virtual = window.__virtual;
    const dl = document.querySelector("#detail-view dl.kv");
    if (!dl) return null;
    await virtual.start({ container: dl });
    const log = [];
    for (let i = 0; i < 8; i++) {
      await virtual.next();
      log.push(await virtual.lastSpokenPhrase());
    }
    await virtual.stop();
    return log;
  });
  test.skip(spoken === null, "this product has no .kv block");
  expect(spoken.join("\n")).toMatchSnapshot("detail-kv-announcements.txt");
});

test("the graph's table equivalent reads as a table", async ({ page }) => {
  await showView(page, "graph");
  await page.click("#graphTable");
  const spoken = await page.evaluate(async () => {
    const virtual = window.__virtual;
    await virtual.start({ container: document.querySelector("#graph-view") });
    const log = [];
    for (let i = 0; i < 12; i++) {
      await virtual.next();
      log.push(await virtual.lastSpokenPhrase());
    }
    await virtual.stop();
    return log;
  });
  expect(spoken.join("\n")).toMatchSnapshot("graph-table-announcements.txt");
  // A caption is how a reader learns what the table is before entering it.
  expect(spoken.join(" ").toLowerCase()).toContain("table");
});

test("a full growing-calendar row, for judging verbosity", async ({ page }) => {
  // Recorded rather than asserted. The calendar is 16 columns wide, so every one
  // of the twelve month cells is announced with its column header -- correct, and
  // possibly unbearable. No tool can decide which; this exists so a person can
  // read one row end to end and form a view.
  //
  // Rubber deliberately: it is a crop WITH a growing plant, so its row header
  // carries two names and is the longest case rather than the friendliest.
  await showView(page, "almanac");
  const spoken = await page.evaluate(async () => {
    const virtual = window.__virtual;
    const rows = Array.from(document.querySelectorAll("#almanac-view tbody tr"));
    const row = rows.find((r) => (r.textContent || "").includes("Rubber"));
    if (!row) return null;
    await virtual.start({ container: row });
    // A fixed number of steps, NOT "stop when a phrase repeats": an unsown month
    // is an empty cell announced as bare "cell", so consecutive empty months
    // repeat legitimately and a repeat-detector truncates the row mid-way. 60 is
    // comfortably past the ~45 a 16-column row produces.
    const log = [];
    for (let i = 0; i < 60; i++) {
      await virtual.next();
      log.push(await virtual.lastSpokenPhrase());
    }
    await virtual.stop();
    // Cut at "end of row": the reader wraps back to the top of the container once
    // it runs out, and a second pass through the same row is noise that would
    // double the snapshot and hide where the row actually ends.
    const end = log.findIndex((phrase) => phrase.startsWith("end of row"));
    return end === -1 ? log : log.slice(0, end + 1);
  });
  test.skip(spoken === null, "no Rubber row in this gameset");
  expect(spoken.join("\n")).toMatchSnapshot("almanac-row-announcements.txt");
});

test("filtering announces the new result count", async ({ page }) => {
  // #resultStatus is a persistent role=status region, deliberately not recreated
  // on each render. Its CONTENT is what a reader hears; assert the content
  // changes and is non-empty rather than guessing the sentence.
  const status = page.locator("#resultStatus");
  await page.fill("#searchBox", "leather");
  await expect(status).not.toBeEmpty();
  const after = (await status.textContent()).trim();
  expect(after).toMatchSnapshot("filter-status.txt");
  expect(after).toMatch(/\d/);
});
