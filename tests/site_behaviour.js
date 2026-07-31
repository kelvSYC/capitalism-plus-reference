// Behavioural tests for the site's inline script.
//
// The site is a single self-contained HTML file with no module boundary, so
// there is nothing to import. tests/run_site_tests.py splices the real script
// out of site/index.html into the marker below and runs the whole thing under
// whichever JS engine is available (node, or macOS's built-in jsc). That means
// these assertions exercise the SHIPPED artifact, not a copy of it.
//
// Everything the script touches is stubbed: enough DOM to render into strings
// and to build an SVG tree. Assertions then read back the HTML the real render
// functions produced.

// jsc provides print(); node provides console.log. Support both.
globalThis.print = globalThis.print || console.log;

// ---------------------------------------------------------------- DOM stub ---
const _els = {};
function mkEl(id) {
  const el = {
    id, style: {}, _classes: new Set(), children: [], value: '', checked: false,
    _html: '',
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = String(v); this.children = []; },
    textContent: '',
    appendChild(c) { this.children.push(c); return c; },
    remove() {},
    setAttribute(k, v) { (this.attrs = this.attrs || {})[k] = String(v); },
    getAttribute(k) { return (this.attrs || {})[k]; },
    replaceChildren() { this.children = []; },
    addEventListener(ev, fn) { (this._ls = this._ls || {})[ev] = fn; },
    // The site registers a capture-phase 'error' listener to swap in monogram
    // tiles for absent icons; nothing here dispatches events, so closest()
    // only needs to exist, not resolve.
    closest() { return null; },
    querySelectorAll() { return []; },
    focus() { document.activeElement = this; },
    blur() { if (document.activeElement === this) document.activeElement = null; },
    classList: {
      _s: null,
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      contains(c) { return this._s.has(c); },
      toggle(c, on) {
        if (on === undefined) on = !this._s.has(c);
        on ? this._s.add(c) : this._s.delete(c);
      },
    },
  };
  el.classList._s = el._classes;
  return el;
}
const document = {
  // Focus restoration reads this; mkEl's focus() keeps it current.
  activeElement: null,
  addEventListener(ev, fn) { (this._ls = this._ls || {})[ev] = fn; },
  // The graph builds real SVG nodes now that d3 is gone; nothing asserts on the
  // resulting tree, so these only need to accept the calls without throwing.
  createElementNS(ns, tag) { const e = mkEl('<' + tag + '>'); e.tag = tag; return e; },
  getElementById(id) { return _els[id] || (_els[id] = mkEl(id)); },
  createElement(tag) { const e = mkEl('<' + tag + '>'); e.tag = tag; return e; },
  createTextNode(t) { const e = mkEl('#text'); e.textContent = t; return e; },
  querySelector(sel) { return _els[sel] || (_els[sel] = mkEl(sel)); },
};
const window = { scrollTo() {} };

//__SITE_SCRIPT__

// -------------------------------------------------------------- assertions ---
let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; print('  PASS  ' + name); }
  else { fail++; print('  FAIL  ' + name + (detail ? '  [' + detail + ']' : '')); }
}
const pane = id => document.getElementById(id);
const disp = id => pane(id).style.display;
const tabOn = id => document.getElementById(id)._classes.has('active');
const countOf = id => {
  const m = pane(id).innerHTML.match(/(\d+) product/);
  return m ? +m[1] : null;
};
function reset() {
  state.gameset = 'Standard'; state.scenario = null; state.category = null;
  state.classification = null; state.industry = null; state.goodsFilter = null;
  state.showRestricted = false; state.dominateFilter = null; state.search = '';
  state.view = 'grid'; state.detailId = null;
  _scenarioMarketMemo = null; _scenarioMarketMemoKey = null;
}

print('--- data reached the page ---');
ok('product payload was substituted', Array.isArray(PRODUCTS) && PRODUCTS.length === 245,
   'PRODUCTS=' + (typeof PRODUCTS === 'undefined' ? 'undefined' : PRODUCTS.length));
ok('all three gamesets present', new Set(PRODUCTS.map(p => p.gameset)).size === 3);
ok('20 scenarios decoded', SCENARIOS.length === 20);

print('--- initial load: the visible view is the highlighted view ---');
ok('Grid tab active after bootstrap', tabOn('viewGrid'));
ok('no other view tab active', !tabOn('viewGraph') && !tabOn('viewAlmanac'));

print('--- returning to the Grid re-renders it ---');
// Regression: setView() used to re-render only its graph/almanac branches, so a
// filter changed from another view left a stale product list AND count behind.
reset();
setView('almanac');
state.category = ['Automobile'];
renderAll();
setView('grid');
const expected = filteredProducts().length;
ok('grid count matches the active filter (' + expected + ')',
   countOf('grid-view') === expected, 'rendered=' + countOf('grid-view'));
ok('grid count is not the unfiltered gameset', countOf('grid-view') !== byGameset('Standard').length);

print('--- exactly one pane is ever visible ---');
// Regression: openDetail() hid grid-view and graph-view but not almanac-view,
// so opening a crop from the Almanac left the whole crop table on screen below
// the product detail page.
reset();
setView('almanac');
ok('almanac visible before opening a crop', disp('almanac-view') === 'block');
const crop = PRODUCTS.find(p => p.gameset === 'Standard' && p.growing_conditions);
openDetail(crop.id);
ok('almanac-view hidden after openDetail', disp('almanac-view') === 'none', 'got ' + disp('almanac-view'));
ok('grid-view hidden', disp('grid-view') === 'none');
ok('graph-view hidden', disp('graph-view') === 'none');
ok('detail-view shown', disp('detail-view') === 'block');
ok('no view tab highlighted in the detail view',
   !tabOn('viewGrid') && !tabOn('viewGraph') && !tabOn('viewAlmanac'));
reset();
for (const v of ['grid', 'graph', 'almanac', 'grid', 'almanac', 'graph']) {
  setView(v);
  const shown = Object.entries(VIEW_PANES).filter(([, id]) => disp(id) === 'block').map(([k]) => k);
  ok('one pane visible after setView(' + v + '): ' + shown.join(','),
     shown.length === 1 && shown[0] === v);
}

print('--- the graph honours every sidebar filter, not just three of them ---');
// Regression: graphScopeProducts() applied Category/Classification/Industry but
// silently ignored Goods Type, the domination filter and the search box.
reset();
const allStd = byGameset('Standard').length;
ok('unfiltered graph scope is the whole gameset', graphScopeProducts().length === allStd);
state.goodsFilter = 'Industrial Goods';
const gScope = graphScopeProducts();
ok('Goods Type narrows the graph scope', gScope.length < allStd, gScope.length + '/' + allStd);
reset();
state.search = 'car';
const sScope = graphScopeProducts();
ok('search narrows the graph scope', sScope.length < allStd, sScope.length + '/' + allStd);
ok('search scope contains the match', sScope.some(p => p.name === 'Car'));
ok('search scope pulls in upstream inputs', sScope.some(p => p.name === 'Engine'));
ok('search scope excludes unrelated products', !sScope.some(p => p.name === 'Beer'));
reset();
const domScen = SCENARIOS.find(s =>
  s.gameset === 'Standard' && (s.dominateClasses.length || s.dominateIndustries.length));
state.scenario = domScen.key; state.dominateFilter = domScen.key; state.showRestricted = true;
ok('domination filter narrows the graph scope (' + domScen.key + ')',
   graphScopeProducts().length < allStd);
ok('graph and grid agree on the domination set',
   filteredProducts().every(p => graphScopeProducts().some(g => g.id === p.id)));
reset();
state.scenario = 'DRAGON';
setView('graph');
ok('scope label reports hidden restricted nodes',
   pane('graph-view').innerHTML.includes('restricted nodes are hidden'));
reset();
state.search = '<img src=x onerror=alert(1)>';
setView('graph');
ok('user-typed search text is HTML-escaped in the scope label',
   !pane('graph-view').innerHTML.includes('<img src=x') &&
   pane('graph-view').innerHTML.includes('&lt;img'));

print('--- a restricted product states the restriction and withholds the chain ---');
// The rule: a restricted product cannot be manufactured or sold under that
// scenario, so there is no chain the player could build. Unlike the game's own
// Manufacturer's Guide, this reference accounts for that.
reset();
state.gameset = 'Alternative'; state.scenario = 'UK';   // Rule Britannia
const milk = PRODUCTS.find(p => p.gameset === 'Alternative' && p.name === 'Milk');
ok('Milk is restricted under Rule Britannia', scenarioRestricted(milk));
openDetail(milk.id);
let h = pane('detail-view').innerHTML;
ok('page states the chain is not shown', h.includes('Production chain not shown'));
ok('page still names the specific restriction',
   h.includes('No Market Here') || h.includes('Not Sellable Here'));
ok('no Dependency Diagram section', !h.includes('Dependency Diagram'));
ok('no Immediate Dependencies section', !h.includes('Immediate Dependencies'));
ok('downstream consumer not listed', !h.includes('Cheese'));

state.showRestricted = true;
openDetail(milk.id);
h = pane('detail-view').innerHTML;
ok('Show Restricted brings the chain back',
   h.includes('Dependency Diagram') && h.includes('Immediate Dependencies'));
ok('downstream consumer listed once restricted are shown', h.includes('Cheese'));
ok('no chain-blocked note when Show Restricted is on', !h.includes('Production chain not shown'));
ok('consumer is in the diagram too', transitiveClosure(milk).some(p => p.name === 'Cheese'));

print('--- intrinsic product facts survive on a restricted page ---');
// A restricted crop can still be sown, and a recipe/yield/climate is a property
// of the item in every scenario. Only the relational sections are withheld.
let crops = 0, yields = 0, noteMissing = [], chainLeaked = [], lostFacts = [];
for (const sc of SCENARIOS) {
  reset();
  state.gameset = sc.gameset; state.scenario = sc.key;
  for (const p of byGameset(sc.gameset)) {
    if (!scenarioRestricted(p) || p.classification === 'Livestock') continue;
    openDetail(p.id);
    const d = pane('detail-view').innerHTML;
    if (!d.includes('Production chain not shown')) noteMissing.push(sc.key + '/' + p.name);
    if (d.includes('Dependency Diagram') || d.includes('Immediate Dependencies')) {
      chainLeaked.push(sc.key + '/' + p.name);
    }
    if (p.growing_conditions) {
      if (d.includes('Growing Conditions') && d.includes(p.growing_conditions.sowing_month)) crops++;
      else lostFacts.push(sc.key + '/' + p.name + ' (growing conditions)');
    }
    if (p.output_quantity) {
      if (d.includes('per production run')) yields++;
      else lostFacts.push(sc.key + '/' + p.name + ' (output)');
    }
  }
}
ok('every restricted page carries the explanation', noteMissing.length === 0, noteMissing.slice(0, 3).join('; '));
ok('no restricted page leaks a chain section', chainLeaked.length === 0, chainLeaked.slice(0, 3).join('; '));
ok('no restricted page loses an intrinsic fact', lostFacts.length === 0, lostFacts.slice(0, 3).join('; '));
ok('restricted crops keep sowing/harvest data (' + crops + ' pages)', crops > 0);
ok('restricted products keep their output yield (' + yields + ' pages)', yields > 0);

print('--- invariant: relation lists never disagree with the diagram ---');
// This is the contradiction the old focal-exemption produced: the lists showed
// restricted neighbours that the diagram directly beneath them had dropped.
// Every scenario x both toggle states x every product.
let checked = 0;
const disagreements = [];
for (const sc of SCENARIOS) {
  for (const showRestricted of [false, true]) {
    reset();
    state.gameset = sc.gameset; state.scenario = sc.key; state.showRestricted = showRestricted;
    for (const p of byGameset(sc.gameset)) {
      if (p.classification === 'Livestock') continue;
      if (scenarioRestricted(p) && !state.showRestricted) continue;  // no lists, no diagram
      const nodes = new Set(transitiveClosure(p).map(x => x.name));
      const shown = [
        ...(p.inputs || []).map(i => PRODUCTS.find(x => x.gameset === p.gameset && x.name === i.material)),
        ...(p.used_in || []).map(u => byId(u.id)),
      ].filter(rp => rp && relVisible(rp));
      for (const rp of shown) {
        if (!nodes.has(rp.name)) disagreements.push(sc.key + '/' + showRestricted + ' ' + p.name + ' -> ' + rp.name);
      }
      checked++;
    }
  }
}
ok('lists agree with the diagram on all ' + checked + ' reachable pages',
   disagreements.length === 0, disagreements.slice(0, 5).join('; '));

print('--- the design works with or without icon artwork ---');
// The icon files are not distributed with this site, so the no-artwork state is
// the DEFAULT rendering, not an edge case. Every icon must carry the monogram
// fallback data and must not announce a filename to a screen reader.
reset();
const wheel = PRODUCTS.find(p => p.name === 'Wheel & Tire');
ok('monogram skips punctuation ("Wheel & Tire" -> "WT")',
   productIcon(wheel).includes('data-initial="WT"'), productIcon(wheel));
ok('single-word product gets one initial',
   productIcon(PRODUCTS.find(p => p.name === 'Car')).includes('data-initial="C"'));
ok('monogram is tinted by classification', productIcon(wheel).includes('--picon-fg:'));
ok('monogram colour is legible on the white tile',
   contrastRatio(readableOnWhite(CLASS_SOLID['Semi-Product']), '#ffffff') >= 4.5);
ok('the lightest palette colour is darkened enough to read on white',
   contrastRatio(readableOnWhite('#FFAB00'), '#ffffff') >= 4.5,
   readableOnWhite('#FFAB00') + ' = ' + contrastRatio(readableOnWhite('#FFAB00'), '#ffffff').toFixed(2));
ok('darkening preserves hue rather than going grey',
   readableOnWhite('#FFAB00').toLowerCase() !== '#000000');
ok('icon marks itself decorative (alt="")', productIcon(wheel).includes('alt=""'));
ok('icon defers loading', productIcon(wheel).includes('loading="lazy"'));
// 0.55, not lower: --text dimmed to 0.4 composites to 3.30:1 against the panel,
// under the 4.5:1 AA floor. Pinned because the exact value is a contrast
// guarantee, not a taste call.
ok('restricted icons are dimmed to the AA-safe floor',
   productIcon(wheel, true).includes('opacity:0.55'));
ok('unrestricted icons are not dimmed', !productIcon(wheel, false).includes('opacity'));
let noAlt = 0, noInitial = 0;
for (const p of PRODUCTS) {
  const markup = productIcon(p);
  if (!markup.includes('alt=""')) noAlt++;
  if (/data-initial="[A-Z0-9]{1,2}"/.test(markup) === false) noInitial++;
}
ok('all ' + PRODUCTS.length + ' icons are decorative', noAlt === 0, 'missing alt: ' + noAlt);
ok('all ' + PRODUCTS.length + ' icons have a monogram', noInitial === 0, 'missing: ' + noInitial);
// No render path may emit a bare <img> that bypasses the fallback wrapper.
reset();
setView('grid');
const gridHtml = pane('grid-view').innerHTML;
ok('grid emits no unwrapped images',
   (gridHtml.match(/<img/g) || []).length === (gridHtml.match(/class="picon"/g) || []).length);

print('--- the palette encodes production lineage ---');
// Semi-Product, Manufacturing and Industrial Goods are one colour on purpose:
// the same thing seen from three angles. Asserted so a future edit to one of
// them cannot silently break the relationship.
ok('Semi-Product, Manufacturing and Industrial Goods share one red',
   CLASS_SOLID['Semi-Product'] === INDUSTRY_COLOR['Manufacturing'] &&
   CLASS_SOLID['Semi-Product'] === INDUSTRIAL_GOODS_COLOR);
ok('Retail Product, Retailing and Consumer Goods share one blue',
   CLASS_SOLID['Retail Product'] === INDUSTRY_COLOR['Retailing'] &&
   CLASS_SOLID['Retail Product'] === CONSUMER_GOODS_COLOR);
ok('Livestock and Farming share one orange',
   CLASS_SOLID['Livestock'] === INDUSTRY_COLOR['Farming']);
ok('Raw Material and Raw Material Production share one pink',
   CLASS_SOLID['Raw Material'] === INDUSTRY_COLOR['Raw Material Production']);
// Nothing outside PALETTE may introduce a classification or industry colour.
ok('every classification and industry colour comes from PALETTE',
   [...Object.values(CLASS_SOLID), ...Object.values(INDUSTRY_COLOR)]
     .every(c => Object.values(PALETTE).includes(c)));

print('--- restriction colour encodes the mechanism, not the label ---');
// Two mechanisms: cannot be produced, or produced fine with no buyer anywhere.
// The four labels under the second differ only in which unit refuses to act.
const kindColour = kind => {
  const probe = PRODUCTS[0];
  return restrictionKindInfo(probe, kind).color;
};
ok('cannot-produce is the production-blocked colour',
   kindColour('mfg') === PRODUCTION_BLOCKED_COLOR);
ok('all four no-buyer kinds share the no-market colour',
   ['retail', 'grow', 'market', 'raise'].every(k => kindColour(k) === NO_MARKET_COLOR),
   ['retail', 'grow', 'market', 'raise'].map(k => k + '=' + kindColour(k)).join(' '));
ok('restriction palette is exactly two colours',
   new Set(['mfg', 'retail', 'grow', 'market', 'raise'].map(kindColour)).size === 2);

// The livestock lineage must stay a warm family: goods derived from an orange
// animal should not look unrelated to it. R > G > B is a crude but sufficient
// machine-checkable proxy for "warm".
const warm = hex => {
  const [r, g, bl] = [0, 1, 2].map(i => parseInt(hex.replace('#', '').slice(i * 2, i * 2 + 2), 16));
  return r > g && g > bl;
};
ok('the whole livestock lineage is warm',
   [PALETTE.livestock, PALETTE.livestockProduct, PALETTE.livestockSemi].every(warm),
   [PALETTE.livestock, PALETTE.livestockProduct, PALETTE.livestockSemi].join(' '));
ok('the livestock lineage is ordered light to dark',
   relLuminance(PALETTE.livestock) > relLuminance(PALETTE.livestockProduct) &&
   relLuminance(PALETTE.livestockProduct) > relLuminance(PALETTE.livestockSemi));

// The specific readability complaint: dark text on a saturated red reads worse
// than white, even though the old red technically scored higher against ink.
ok('the manufactured red takes white text again',
   onColor(PALETTE.manufactured) === '#ffffff',
   PALETTE.manufactured + ' white=' + contrastRatio(PALETTE.manufactured, '#ffffff').toFixed(2));

print('--- colour contrast meets WCAG AA ---');
// Small text needs 4.5:1. Eleven of the badge colours are light enough that the
// hardcoded white this site used to emit failed badly (#FFAB00 was 1.90:1), so
// the foreground is computed per background by onColor(). These assertions use
// the site's OWN contrastRatio(), so a palette change that breaks AA fails here.
const AA = 4.5;
const swatches = [
  ...Object.values(CLASS_SOLID),
  CONSUMER_GOODS_COLOR, INDUSTRIAL_GOODS_COLOR,
  PRODUCTION_BLOCKED_COLOR, NO_MARKET_COLOR,
  '#555b66',
];
for (let i = 0; i < 8; i++) swatches.push(pctColor(i));
const lowContrast = swatches
  .map(bg => ({ bg, r: contrastRatio(bg, onColor(bg)) }))
  .filter(x => x.r < AA);
ok('every badge/bar colour clears AA with its computed foreground (' + swatches.length + ' colours)',
   lowContrast.length === 0,
   lowContrast.map(x => x.bg + '=' + x.r.toFixed(2)).join(', '));

// The specific regression: white on the light end of the palette.
ok('onColor picks dark text on light amber', onColor('#FFAB00') === INK);
ok('onColor picks dark text on light green', onColor('#57D9A3') === INK);
ok('onColor picks white on dark blue', onColor('#0533FF') === '#ffffff');
ok('onColor picks white on dark red', onColor(PRODUCTION_BLOCKED_COLOR) === '#ffffff');
ok('NO_MARKET_COLOR clears AA (was #B36B00: 4.18 white / 4.33 ink, failing both)',
   contrastRatio(NO_MARKET_COLOR, onColor(NO_MARKET_COLOR)) >= AA,
   contrastRatio(NO_MARKET_COLOR, onColor(NO_MARKET_COLOR)).toFixed(2));

// Rendered markup must actually carry the computed colour, not just have the
// helper available.
reset();
setView('grid');
const cards = pane('grid-view').innerHTML;
const badges = cards.match(/class="badge"[^>]*/g) || [];
ok('every rendered badge carries an explicit colour (' + badges.length + ')',
   badges.length > 0 && badges.every(b => b.includes('color:')));

print('--- the dependency graph has a real text equivalent ---');
// The diagram is an SVG with no text alternative and no focusable nodes, so the
// whole view was unreadable by a screen reader and unusable without a mouse.
// The table is a genuine alternative, not a summary: same products, same edges,
// same amounts, same navigation buttons.
reset();
state.gameset = 'Standard';
state.graphLayout = 'table';
setView('graph');
const tableHtml = pane('graph-view').innerHTML;
const scope = graphScopeProducts();

ok('every product in scope has a row (' + scope.length + ')',
   scope.every(p => tableHtml.includes('>' + esc(p.name) + '</button>')),
   scope.filter(p => !tableHtml.includes('>' + esc(p.name) + '</button>')).slice(0, 3).map(p => p.name).join(', '));

// Parity: the table must carry every edge the diagram draws. This is the whole
// claim -- if it silently dropped links it would be a summary pretending to be
// an equivalent.
const edges = buildLinks(scope);
// Split into real rows and match on the row header, not the first occurrence of
// a name anywhere -- a product's name also appears in other rows' "Used in"
// cells. Names go through the site's own esc(), so "Wheel & Tire" is compared as
// the markup actually writes it.
const rows = tableHtml.split('<tr').slice(1);
// Match on the ROW HEADER only. A product's name also appears in other rows'
// "Made from" and "Used in" cells, so any search over the whole table finds the
// wrong row -- which is exactly the mistake this helper exists to prevent.
const rowIndexOf = name => rows.findIndex(r => {
  const head = r.slice(r.indexOf('<th scope="row"'), r.indexOf('</th>'));
  return head.includes('>' + esc(name) + '</button>');
});
const rowFor = name => rows[rowIndexOf(name)];
const missingEdges = edges.filter(l => {
  const row = rowFor(l.target);
  if (!row) return true;
  const madeFrom = row.slice(row.indexOf('</th>'));
  return !madeFrom.includes('>' + esc(l.source));
});
ok('every diagram edge appears in the table (' + edges.length + ' edges)',
   missingEdges.length === 0,
   missingEdges.slice(0, 3).map(l => l.source + '->' + l.target).join(', '));
// Quantities are deliberately absent: an input amount is directional, and
// printing it in the "Used in" direction reads as the neighbour's own yield.
ok('quantities are left to the detail page',
   !/\(\d+(\.\d+)? (lb|unit|quart|barrel|can)\)/.test(tableHtml));
ok('the table is captioned and scoped',
   tableHtml.includes('<caption') && tableHtml.includes('<th scope="col"') &&
   tableHtml.includes('<th scope="row"'));
// The tier number is an artefact of the topological sort with no meaning in the
// game, so it is not shown -- but it still orders the rows.
ok('the stage number is not displayed', !/<td>\d+<\/td>/.test(tableHtml));
ok('rows still run raw materials before the things made from them',
   rowIndexOf('Iron Ore') < rowIndexOf('Steel') && rowIndexOf('Steel') < rowIndexOf('Car'),
   `IronOre=${rowIndexOf('Iron Ore')} Steel=${rowIndexOf('Steel')} Car=${rowIndexOf('Car')}`);

print('--- alternatives are distinguished from requirements ---');
// inputs are AND (a recipe needs all of them); derived_from_livestock is OR
// (any one animal yields the product). Standard Leather is the only product in
// the dataset with a genuine choice, which is why it was easy to miss.
const leather = PRODUCTS.find(p => p.gameset === 'Standard' && p.name === 'Leather');
ok('Leather really does have three possible sources',
   sourcesAreAlternatives(leather) && leather.derived_from_livestock.length === 3);
const leatherRow = rowFor('Leather');
ok('the table marks Leather\'s sources as a choice',
   !!leatherRow && leatherRow.includes('any one of'));
ok('the choice reads as "or", not a comma list',
   !!leatherRow && / or <button/.test(leatherRow), leatherRow && leatherRow.slice(0, 0));

// A single-source product must NOT claim a choice.
const beefRow = rowFor('Frozen Beef');
ok('a single-source product is not described as a choice',
   !!beefRow && !beefRow.includes('any one of'));
// And a recipe with several inputs must not be either -- those are all required.
const steelRow = rowFor('Steel');
ok('a multi-input recipe is not described as a choice',
   !!steelRow && !steelRow.includes('any one of'));

reset();
openDetail(leather.id);
const leatherDetail = pane('detail-view').innerHTML;
ok('the detail page states the choice in words',
   leatherDetail.includes('Any one of these') && leatherDetail.includes('do not need all'));
reset();
openDetail(PRODUCTS.find(p => p.gameset === 'Standard' && p.name === 'Frozen Beef').id);
ok('a single-source detail page does not claim a choice',
   !pane('detail-view').innerHTML.includes('Any one of these'));

reset();
state.gameset = 'Standard'; state.graphLayout = 'table'; setView('graph');
ok('switching to the table announces the change',
   document.getElementById('resultStatus').textContent.includes('production chain'));

state.graphLayout = 'diagram';
setView('graph');
const diagramHtml = pane('graph-view').innerHTML;
ok('the diagram is exposed as a single image, not a pile of shapes',
   diagramHtml.includes('role="img"'));
ok('the image says what it shows and where the readable version is',
   /aria-label="Dependency diagram:[^"]*Table view/.test(diagramHtml));
ok('the scroll container can be reached and scrolled by keyboard',
   diagramHtml.includes('class="graph-scroll" tabindex="0" role="region"'));
ok('the view toggle exposes which view is active',
   diagramHtml.includes('id="graphDiagram"') && diagramHtml.includes('aria-pressed="true"'));

// The detail page's spider diagram gets the same treatment; its text equivalent
// is the Immediate Dependencies list already on the page.
reset();
openDetail(PRODUCTS.find(p => p.gameset === 'Standard' && p.inputs.length && p.used_in.length).id);
const detail = pane('detail-view').innerHTML;
ok('the spider diagram is labelled and points at its text equivalent',
   detail.includes('id="spider-svg" role="img"') &&
   detail.includes('Immediate Dependencies above'));
ok('the spider diagram is keyboard scrollable', detail.includes('class="spider-wrap" tabindex="0"'));

print('--- the growing calendar exists in text, not just in colour ---');
// The calendar was 12 empty <td>s per crop whose entire content was a background
// colour and two border edges -- invisible to a screen reader, in the one view
// that exists to show it.
const MONTH_STATE = /<span class="sr-only">(Sown|Harvested|Growing|Sown and harvested)<\/span>/;
let statelessCells = [], missingRows = [];
for (const gs of ['Standard', 'Alternative', 'Food & Beverage']) {
  reset();
  state.gameset = gs;
  setView('almanac');
  const html = pane('almanac-view').innerHTML;
  // Every cell carrying a visual state class must also carry text.
  const cells = html.match(/<td class="month-cell[^"]*">[^<]*(<span[^>]*>[^<]*<\/span>)?/g) || [];
  for (const cell of cells) {
    const visual = /grow|sow|harvest/.test(cell.slice(0, cell.indexOf('>')));
    const textual = MONTH_STATE.test(cell + '</span>');
    if (visual && !textual) statelessCells.push(gs + ': ' + cell.slice(0, 60));
  }
  for (const p of byGameset(gs).filter(x => x.growing_conditions)) {
    if (!html.includes(esc(p.name))) missingRows.push(gs + '/' + p.name);
  }
}
ok('no month cell conveys its state by colour alone',
   statelessCells.length === 0, statelessCells.slice(0, 3).join(' | '));
ok('every crop appears in its gameset calendar', missingRows.length === 0,
   missingRows.slice(0, 3).join(', '));

reset(); state.gameset = 'Standard'; setView('almanac');
const almanac = pane('almanac-view').innerHTML;
ok('sowing is announced', almanac.includes('>Sown<'));
ok('harvesting is announced', almanac.includes('>Harvested<'));
ok('growing months are announced', almanac.includes('>Growing<'));
ok('month columns carry full names, not just an initial',
   almanac.includes('>January<') && almanac.includes('>December<'));
ok('the calendar table has a caption', almanac.includes('<caption'));
ok('columns are scoped', almanac.includes('<th scope="col"'));
ok('each crop row is a row header', almanac.includes('<th scope="row"'));
ok('the decorative climate bar is hidden from assistive tech',
   almanac.includes('class="climate-bar" aria-hidden="true"'));
ok('the decorative rain bar is hidden from assistive tech',
   almanac.includes('class="rain-bar" aria-hidden="true"'));
// The climate/rainfall words themselves must survive -- they were the only
// non-decorative carrier once the bars went aria-hidden.
ok('climate is still stated in words', /aria-hidden="true">.*?<\/span>Warm/.test(almanac.replace(/\n/g, '')));

reset(); state.gridLayout = 'list'; setView('grid');
const listView = pane('grid-view').innerHTML;
ok('the product list table is captioned and scoped',
   listView.includes('<caption') && listView.includes('<th scope="col"') &&
   listView.includes('<th scope="row"'));
ok('the restriction column has a header name', listView.includes('Scenario restriction'));
state.gridLayout = 'cards';

print('--- keyboard operability ---');
// The site was mouse-only: zero tabindex/role/aria/key handlers anywhere, so a
// keyboard user could reach exactly three controls.
reset();
setView('grid');
const gridMarkup = pane('grid-view').innerHTML;
const cardCount = (gridMarkup.match(/class="card/g) || []).length;
ok('grid cards are focusable and expose a button role (' + cardCount + ')',
   cardCount > 0 &&
   (gridMarkup.match(/tabindex="0" role="button"/g) || []).length >= cardCount);

state.gridLayout = 'list';
renderGrid();
const listMarkup = pane('grid-view').innerHTML;
ok('list rows carry a real activation control',
   listMarkup.includes('class="cell-activate"'));
ok('row buttons stop the click reaching the row handler',
   listMarkup.includes('event.stopPropagation()'));
state.gridLayout = 'cards';

reset();
openDetail(PRODUCTS.find(p => p.used_in.length && p.inputs.length).id);
const detailMarkup = pane('detail-view').innerHTML;
ok('Back is a real button', detailMarkup.includes('<button type="button" class="back"'));
ok('relation-list entries are keyboard activatable',
   detailMarkup.includes('tabindex="0" role="button"'));

print('--- the page says where you are ---');
// document.title never changed, so every view and every product looked
// identical from the tab strip, browser history and a screen reader's
// navigation announcement.
reset();
setView('grid');
ok('the title names the view', /Products · Standard/.test(document.title), document.title);
setView('almanac');
ok('the title follows the view', /Almanac/.test(document.title), document.title);
reset();
const titled = PRODUCTS.find(p => p.gameset === 'Standard' && p.name === 'Car');
openDetail(titled.id);
ok('the title names the open product', /^Car · Standard/.test(document.title), document.title);
ok('the site name is still in the title', /Capitalism Plus/.test(document.title));

print('--- roving tabindex ---');
reset();
setView('graph');
ok('the selected tab is the tablist\'s single Tab stop',
   document.getElementById('viewGraph').getAttribute('tabindex') === '0');
ok('unselected tabs are skipped by Tab',
   document.getElementById('viewGrid').getAttribute('tabindex') === '-1' &&
   document.getElementById('viewAlmanac').getAttribute('tabindex') === '-1');

print('--- product names are escaped wherever they reach markup ---');
// "Wheel & Tire" is the only name in the dataset containing a markup character,
// which is exactly why unescaped interpolation went unnoticed for so long.
reset();
const amp = PRODUCTS.find(p => p.name === 'Wheel & Tire');
ok('the dataset still has the awkward name', !!amp);
openDetail(amp.id);
const ampHtml = pane('detail-view').innerHTML;
ok('the detail heading escapes it', ampHtml.includes('>Wheel &amp; Tire</h2>'));
ok('no raw ampersand leaks into the markup',
   !/Wheel & Tire/.test(ampHtml.replace(/Wheel &amp; Tire/g, '')));
setView('grid');
ok('the card escapes it', pane('grid-view').innerHTML.includes('Wheel &amp; Tire'));

print('--- focus survives a re-render ---');
// The complaint this fixes: renderAll() destroys and rebuilds every chip, so a
// keyboard user was thrown back to <body> -- the top of the document -- on
// every single filter click.
reset();
renderAll();
const catGroup = document.getElementById('categoryChips');
const aChip = catGroup.children.find(c => c.getAttribute('data-chip-label') === 'Automobile');
ok('chips carry a key that survives rebuilding',
   !!aChip && aChip.getAttribute('data-focus-key') === 'categoryChips|Automobile',
   aChip && aChip.getAttribute('data-focus-key'));

aChip.focus();
ok('the chip has focus before the re-render', document.activeElement === aChip);
const keyBefore = activeFocusKey();
aChip.onclick();                       // toggles the filter and calls renderAll()
ok('focus is not lost to the document body', document.activeElement !== null);
ok('focus landed on the chip that replaced it',
   document.activeElement !== aChip &&
   activeFocusKey() === keyBefore,
   'now on: ' + activeFocusKey());
ok('the replacement really is a new element', document.activeElement !== aChip);

// A gameset switch legitimately removes chips. Focus must still land somewhere
// useful rather than at the top of the page.
reset();
renderAll();
const gone = document.getElementById('categoryChips').children
  .find(c => c.getAttribute('data-chip-label') === 'Automobile');
gone.focus();
state.gameset = 'Food & Beverage';
renderAll();
ok('a chip that no longer exists falls back to the visible pane',
   document.activeElement === document.getElementById('grid-view'),
   'landed on ' + (document.activeElement && document.activeElement.id));

// Nothing should steal focus when the user has not got it.
reset();
document.activeElement = null;
renderAll();
ok('a render with no prior focus does not grab it', document.activeElement === null);

// The Show Restricted checkbox triggers the render that destroys it.
reset();
state.scenario = 'DRAGON';
renderAll();
const toggle = _focusRegistry.get('sidebar|showRestricted');
ok('the Show Restricted checkbox is keyed', !!toggle);
toggle.focus();
toggle.onchange({ target: { checked: true } });
ok('toggling Show Restricted keeps focus on the checkbox',
   activeFocusKey() === 'sidebar|showRestricted',
   'landed on ' + activeFocusKey());

print('--- focus follows navigation ---');
reset();
setView('grid');
const target = PRODUCTS.find(p => p.gameset === 'Standard');
openDetail(target.id);
ok('opening a product moves focus to its heading',
   document.activeElement === document.getElementById('detailHeading'),
   'landed on ' + (document.activeElement && document.activeElement.id));

// A filter change while the detail page is open re-runs openDetail to refresh
// badges. That must not snatch focus from the control the user just used.
const chip2 = document.getElementById('classChips').children[0];
chip2.focus();
renderAll();
ok('re-rendering the open product does not steal focus back',
   document.activeElement !== document.getElementById('detailHeading'));

reset();
openDetail(target.id);
backToGrid();
ok('Back lands the user in the grid, not at the top of the document',
   document.activeElement === document.getElementById('grid-view'),
   'landed on ' + (document.activeElement && document.activeElement.id));

print('--- assistive-tech state matches visual state ---');
reset();
setView('graph');
ok('selected view tab reports aria-selected=true',
   document.getElementById('viewGraph').getAttribute('aria-selected') === 'true');
ok('unselected view tab reports aria-selected=false',
   document.getElementById('viewGrid').getAttribute('aria-selected') === 'false');
setView('grid');
ok('aria-selected follows the view change',
   document.getElementById('viewGrid').getAttribute('aria-selected') === 'true' &&
   document.getElementById('viewGraph').getAttribute('aria-selected') === 'false');

// Chips are toggle buttons; pressed state must be exposed, not just styled.
reset();
const chip = makeChip('Automobile', '#0533FF', true, () => {}, null);
ok('an active chip is a pressed button',
   chip.tag === 'button' && chip.getAttribute('aria-pressed') === 'true');
const chipOff = makeChip('Automobile', '#0533FF', false, () => {}, null);
ok('an inactive chip reports aria-pressed=false',
   chipOff.getAttribute('aria-pressed') === 'false');

// Restriction level reached the user only via opacity, a glyph and a title --
// none of which assistive tech or a touch device gets.
const restrictedChip = makeChip('Cigarettes', '#FF2600', false, () => {}, 'full');
const srText = restrictedChip.children.filter(c => c.className === 'sr-only');
ok('a fully-restricted chip carries readable restriction text',
   srText.length === 1 && srText[0].textContent.includes('restricted'));
ok('the decorative glyph is hidden from assistive tech',
   restrictedChip.children.some(c =>
     (c.children || []).some(g => g.getAttribute && g.getAttribute('aria-hidden') === 'true')));

print('--- a partial group is annotated, not restyled ---');
reset();
const partialChip = makeChip('Livestock', '#FF9300', false, () => {}, 'partial');
ok('a partial chip is not dimmed or bordered',
   partialChip.className === 'chip', partialChip.className);
ok('a partial chip still carries its marker glyph',
   JSON.stringify(partialChip.children).includes('chip-flag'));
ok('a partial chip still explains itself to assistive tech',
   partialChip.children.some(c => c.className === 'sr-only' && c.textContent.includes('Some products')));
const fullChip = makeChip('Cigarettes', '#FF2600', false, () => {}, 'full');
ok('a fully-restricted chip keeps its stronger treatment',
   fullChip.className.includes('chip-restricted'));

print('--- filtering is announced ---');
reset();
setView('grid');
const announced = document.getElementById('resultStatus').textContent;
ok('result count is announced as a sentence, not a bare number',
   /\d+ products? match the current filters\./.test(announced), announced);
state.category = ['Automobile'];
renderGrid();
ok('the announcement updates when the filter changes',
   document.getElementById('resultStatus').textContent !== announced);

print('--- every product page renders without throwing ---');
// Cheap but broad: the detail page is the most reference-heavy view, so a
// dangling product reference surfaces here first.
reset();
let rendered = 0;
for (const p of PRODUCTS) {
  state.gameset = p.gameset;
  openDetail(p.id);
  // esc(): product names reach the markup escaped, so "Wheel & Tire" appears as
  // "Wheel &amp; Tire".
  if (pane('detail-view').innerHTML.includes(esc(p.name))) rendered++;
}
ok('all ' + PRODUCTS.length + ' product pages render', rendered === PRODUCTS.length, 'rendered=' + rendered);

print('');
print('pass=' + pass + ' fail=' + fail);
if (fail) throw new Error(fail + ' behavioural assertion(s) failed');
