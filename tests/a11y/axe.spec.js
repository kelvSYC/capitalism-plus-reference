// axe-core rule sweep per view.
//
// Complements the ARIA snapshots rather than duplicating them: snapshots catch
// CHANGE, axe catches KNOWN DEFECTS -- missing names, bad contrast, duplicate
// ids, invalid ARIA. Neither judges whether the result is pleasant to listen to;
// that stays a human question.
//
// Scoped to WCAG 2.1 A/AA, which is the bar the site's own tests already claim
// (4.5:1 contrast, keyboard operability, text equivalents). Running the full
// rule set would mix in best-practice advice we have not committed to.
const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const { VIEWS, showView, showFirstProductDetail } = require("./views");

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

// Reported per rule with the offending selectors, because "3 violations" tells
// you nothing on a CI log you cannot click through.
function summarise(violations) {
  return violations.map(
    (v) => `${v.id} (${v.impact}): ${v.help}\n    ${v.nodes.map((n) => n.target.join(" ")).join("\n    ")}`
  );
}

test.beforeEach(async ({ page }) => {
  await page.goto("/index.html");
});

for (const name of Object.keys(VIEWS)) {
  test(`${name} view has no WCAG A/AA violations`, async ({ page }) => {
    const view = await showView(page, name);
    const { violations } = await new AxeBuilder({ page })
      .withTags(TAGS)
      .include(view.panel)
      .analyze();
    expect(summarise(violations)).toEqual([]);
  });
}

test("product detail has no WCAG A/AA violations", async ({ page }) => {
  await showFirstProductDetail(page);
  const { violations } = await new AxeBuilder({ page })
    .withTags(TAGS)
    .include("#detail-view")
    .analyze();
  expect(summarise(violations)).toEqual([]);
});

test("the whole page, including sidebar and header", async ({ page }) => {
  // Unscoped: catches anything living between the landmarks that a per-panel
  // scan would step over.
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  expect(summarise(violations)).toEqual([]);
});
