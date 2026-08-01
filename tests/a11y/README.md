# Accessibility harness

Three kinds of check against the **built** `site/index.html` — the same bytes the
deploy serves:

| Spec | Answers |
|---|---|
| `axe.spec.js` | Does the page break a WCAG 2.1 A/AA rule? |
| `aria.spec.js` | Has the accessibility tree changed — roles, names, heading levels, table headers? |
| `announcements.spec.js` | What would a screen reader *say*, and in what order? |

## Running it

**In CI, which is where snapshots should be recorded:**

```sh
gh workflow run a11y -f record_snapshots=true   # bootstrap: records and uploads
gh workflow run a11y                            # thereafter: verifies
```

Bootstrap mode uploads a `recorded-snapshots` artifact. Download it, read it,
commit it under `tests/a11y/__snapshots__/`. The workflow never commits for you —
a snapshot is an expectation, and it should arrive through a commit somebody read.

Recording on the runner rather than a laptop is deliberate: these snapshots are
*checked* on that runner, so recording them anywhere else bakes in a platform
difference that resurfaces later as a failure nobody can reproduce locally.

**Locally, if you have Node:**

```sh
npm install
npm run a11y:install     # downloads Chromium
npm run a11y             # verify
npm run a11y:update      # record (only when you mean to)
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

**Passing: 17 tests, verified in CI.** This was authored on a machine with no
Node and first run on the runner; the module injection in `announcements.spec.js`
works, with the virtual reader served to the page through a route.

Its first runs earned it, finding four defects that 87 Python tests and 258
behavioural assertions could not see, all four being properties of the
accessibility tree:

1. `role="button"` on the `<li>` of every relation row, so the `<ul>` was not a list.
2. The skip link placed after everything it skips.
3. Monogram initials read as part of all 245 product names.
4. The composition bar pairing names to percentages by colour alone.

The first two were caught by assertions. The other two were caught by *reading the
recorded snapshots* — worth doing whenever they change, because an assertion
confirms what you thought to ask and a transcript shows what you did not.

`package-lock.json` is committed and the workflow installs with `npm ci`, so a
transitive dependency cannot change underneath a gate that blocks deploys.

**This is a required gate.** `pages.yml` calls this workflow, so no deploy happens
unless the audit passes. It stayed out of the gate until several consecutive green
runs had shown it was boring — a gate people want to bypass is worse than none.
