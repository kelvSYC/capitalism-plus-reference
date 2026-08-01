# Accessibility harness

Three kinds of check against the **built** `site/index.html` — the same bytes the
deploy serves:

| Spec | Answers |
|---|---|
| `axe.spec.js` | Does the page break a WCAG 2.1 A/AA rule? |
| `aria.spec.js` | Has the accessibility tree changed — roles, names, heading levels, table headers? |
| `announcements.spec.js` | What would a screen reader *say*, and in what order? |

## Running it

```sh
npm install
npm run a11y:install     # downloads Chromium
npm run a11y:update      # FIRST RUN ONLY: records the snapshots
npm run a11y             # thereafter
npm run a11y:report      # open the HTML report after a failure
```

No dev server to start: `playwright.config.js` serves `site/` with `python3 -m
http.server`, so the only prerequisites are Node and the Python this repo
already needs. HTTP rather than `file://` because Chromium refuses to import ES
modules from `file://`, and because HTTP is what a visitor gets.

**The first run must be `a11y:update`.** Snapshots are recorded from a real run
and then reviewed as a diff. Hand-writing them would encode what somebody assumed
a screen reader says; recording them encodes what one actually says. CI never
updates them (`updateSnapshots: "none"`), so a snapshot can only enter the repo
through a reviewed commit.

## What this cannot tell you

**Whether the site is pleasant to listen to.** A twelve-cell calendar row can be
perfectly correct and still exhausting. Verbosity, ordering and phrasing are
judgement calls, and no tool makes them.

**Real screen-reader behaviour.** `@guidepup/virtual-screen-reader` computes
announcements from a real browser's accessibility tree, but it is a simulator.
The open question it cannot settle is the one `#resultStatus` carries a comment
about: whether an `aria-live` region survives being replaced by `innerHTML` in
VoiceOver and NVDA specifically. That needs Guidepup driving a real reader, or a
manual pass.

So this harness is the regression net, not the audit. The audit is a human with
VoiceOver; this is what stops the audit's findings from silently coming back.

## Status

**Never executed.** The machine this was written on has no Node, so every file
here is unverified: selectors were cross-checked against `site/index.html` by
hand, but nothing has run. Expect the first run to need fixes — most likely in
`announcements.spec.js`, where the virtual reader is injected as an ES module
through a route. If that bundle turns out not to be self-contained, the fallback
is to run the virtual reader in Node against jsdom instead of in the page.
