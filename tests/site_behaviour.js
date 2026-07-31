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
ok('icon is tinted by classification', productIcon(wheel).includes('--picon-bg:'));
ok('icon marks itself decorative (alt="")', productIcon(wheel).includes('alt=""'));
ok('icon defers loading', productIcon(wheel).includes('loading="lazy"'));
ok('restricted icons are dimmed', productIcon(wheel, true).includes('opacity:0.4'));
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

print('--- every product page renders without throwing ---');
// Cheap but broad: the detail page is the most reference-heavy view, so a
// dangling product reference surfaces here first.
reset();
let rendered = 0;
for (const p of PRODUCTS) {
  state.gameset = p.gameset;
  openDetail(p.id);
  if (pane('detail-view').innerHTML.includes(p.name)) rendered++;
}
ok('all ' + PRODUCTS.length + ' product pages render', rendered === PRODUCTS.length, 'rendered=' + rendered);

print('');
print('pass=' + pass + ' fail=' + fail);
if (fail) throw new Error(fail + ' behavioural assertion(s) failed');
