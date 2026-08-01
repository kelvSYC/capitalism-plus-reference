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

Written on a machine with no Node, so the first run is in CI. Selectors were
cross-checked against `site/index.html` by hand, but until `gh workflow run a11y`
has passed, treat every file here as unverified.

The likeliest thing to break is the module injection in `announcements.spec.js`:
the virtual reader is served to the page through a route and imported as an ES
module. If that browser bundle is not self-contained, the fallback is to run the
virtual reader in Node against jsdom instead of inside the page.

Two things are known-missing rather than broken:

- **No lockfile.** Direct dependencies are pinned exactly, transitives float.
  Commit a `package-lock.json` and switch the workflow to `npm ci`.
- **Not a deploy gate.** Wired to nothing; `pages.yml` does not depend on it.
  Promote it once it has been boring for a while.
