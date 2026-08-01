// Shared navigation for the a11y specs.
//
// The site is one page with three tabs (Grid, Graph, Almanac); Grid/List/Cards
// are LAYOUTS inside the Grid tab, and the graph has its own diagram/table
// toggle. Encoding that here once keeps the specs from each re-deriving it and
// disagreeing about what "a view" is.
const VIEWS = {
  grid: { tab: "#viewGrid", panel: "#grid-view", label: "Grid" },
  graph: { tab: "#viewGraph", panel: "#graph-view", label: "Graph" },
  almanac: { tab: "#viewAlmanac", panel: "#almanac-view", label: "Almanac" },
};

// Every view is reached by clicking its tab, so a spec that wants one asks for
// it by name rather than knowing the id. Waits on the panel becoming visible
// rather than on a timeout: setView() swaps display, and asserting against a
// hidden panel yields an empty accessibility tree that looks like a pass.
async function showView(page, name) {
  const view = VIEWS[name];
  if (!view) throw new Error(`unknown view: ${name}`);
  await page.click(view.tab);
  await page.waitForSelector(`${view.panel}:visible`);
  return view;
}

// Products are rendered as role="button" with tabindex="0" (see ACTIVATABLE in
// the template), which is also how a reader perceives them -- so specs address
// them by role rather than by the .card class, and keep working if a layout
// renders something other than a card.
const PRODUCT = '#grid-view [role="button"]';

// The detail page is a region rather than a tabpanel, and is reached by
// activating a product, not a tab. Takes the first one so the spec does not
// depend on a particular product surviving in the dataset.
async function showFirstProductDetail(page) {
  await showView(page, "grid");
  await page.locator(PRODUCT).first().click();
  await page.waitForSelector("#detail-view:visible");
}

module.exports = { VIEWS, PRODUCT, showView, showFirstProductDetail };
