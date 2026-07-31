# Attribution

**Capitalism Plus** (1996) is a product of **Enlight Software Limited**
(Hong Kong), founded by Trevor Chan. Enlight is still actively developing
this game series today as **Capitalism Lab** (the successor to Capitalism
II), currently at version 12.0 with regular updates:
- Official site: https://www.capitalismlab.com/
- Company site: https://www.enlight.com/

This project is an unofficial, non-commercial fan reference. It is not
affiliated with, endorsed by, or sponsored by Enlight Software Limited.
"Capitalism," "Capitalism Plus," "Capitalism II," and "Capitalism Lab" are
trademarks of their respective owner.

## What this repository is

A reference web site describing Capitalism Plus's product catalog, farming
data, production chains, and scenario goals. All gameplay facts are
independently decoded from the game's own data files (`.SET` gameset files
and `.SCN` scenario/save files) using our own reverse-engineered parsers —
see `docs/DECODING.md` for the file formats, byte offsets, and the verification
evidence behind each mechanic. No game code, script text, or executable is
reproduced. Scenario descriptions on the site are original paraphrases, not
reproductions of the game's narrative text.

## The open question: product icons

`site/images/` (git-ignored, not committed — see `.gitignore`) holds 245
small (120x120) product icons extracted from the game's own compiled raster
asset files, one per product, used purely to help players visually identify
items while playing.

Whether displaying these on a public reference site qualifies as fair use
(identificatory use of small game-asset icons in a non-commercial fan
reference, similar to how many game wikis display sprite art) is a real
question we have not resolved, not a settled conclusion.
Until it is, the icons stay out of version control and out of any public
deployment of this site; only the local working copy (populated from your
own legitimately-owned copy of the game) has them. Resolving this — either
via a fair-use determination, replacement placeholder art, or direct contact
with Enlight — is a precondition for making this site public, not an
afterthought.

The hold is enforced mechanically, not just in prose: `.gitignore` keeps the
icons untracked, `tests/test_data.py` asserts nothing but `.gitkeep` is tracked
under `site/images/`, and the `pages` deploy workflow refuses to publish if any
icon file is present in the tree it would upload. Removing any of those should
be a deliberate act recorded alongside a resolution of this section, not a
side effect.

**If permission is obtained.** Should Enlight grant permission to display the
product icons, they would be added under the terms of that grant and recorded
here — who granted it, when, its exact scope, and the granted terms quoted. They
would *not* fall under this project's own `LICENSE`, which covers only material
we are in a position to license; `REUSE.toml` marks `site/images/**` as
third-party precisely so that adding files there can never be mistaken for
placing them under our terms. Until such a grant exists, `site/images/` stays
empty in every published form of this site.

### Findings to date (research, not legal advice)

Recorded so the next person doesn't restart from zero. None of this is legal
advice and none of it resolves the question.

1. **"Nominative fair use" was the wrong frame, and has been removed above.**
   Nominative fair use is a **trademark** doctrine (*New Kids on the Block v.
   News America Publishing*, 9th Cir. 1992; *Toyota v. Tabari*, 9th Cir. 2010).
   It governs when you may use someone's *mark* to refer to their product —
   which is the right analysis for using the words "Capitalism Plus" on this
   site, and that use is on comparatively solid ground. It says nothing about
   copying the *icons*. Those are pictorial works, and reproducing them raises a
   **copyright** claim analysed under 17 U.S.C. §107's four factors. Conflating
   the two made the icon position look better supported than it is: the
   trademark half was never really the exposure.

2. **Enlight has no published fan-content or asset-use policy that we could
   find.** Their support FAQ carries only "© Copyright Enlight Software Limited.
   All rights reserved." and no fan-site, screenshot, or asset terms
   (<https://www.capitalismlab.com/support-faq/>). Absence of a policy is not
   permission, but it also means there is no published prohibition to point to —
   the position is simply undetermined rather than adverse.

3. **Enlight actively supports modding** ("How to Make a MOD", "Advanced
   Modding" documentation for Capitalism Lab), which is a materially different
   posture from a publisher that forbids touching its assets. It is not a
   licence and does not extend to a 1996 title by its own terms.

4. **The icons' own provenance is uncertain, and this may matter more than the
   fair-use question.** On Enlight's own forum, in a thread requesting that
   product images be exposed in standard formats
   (<https://www.capitalism2.com/forum/viewtopic.php?t=922>), a user raised that
   "it is possible that enlight could run into copyright issues for those
   images, particularly if they were originally sourced from a third party who
   still holds copyright," and the requester acknowledged not knowing "what the
   license is that Enlight has with the images it used, whether they were in the
   public domain (quite possibly) or if they actually licensed them from
   somebody." No Enlight staff member answered. For a 1996 product catalogue,
   licensed stock/clip art is entirely plausible. Two consequences: Enlight may
   not be able to grant permission even if willing, and some individual icons
   might carry thin or no protectable originality. Both are unverified.

5. **Community practice is tolerance, not entitlement.** A Capitalism Lab wiki
   on Fandom hosts product images (<https://capitalismlab.fandom.com/>). That
   such sites persist reflects publishers not objecting, which is not a legal
   safe harbour and can change without notice.

6. **Permission path:** `info@enlight.com` is the published support address. A
   narrow written request — non-commercial fan reference, 120x120 icons,
   identification only, attribution and a link to Capitalism Lab, takedown on
   request — is cheap to send and is the only step that actually converts this
   from an open question into an answer.

## Engine / libraries

**None.** The site is a single self-contained HTML file: all CSS and JavaScript
is inlined, nothing is fetched from a CDN, and no third-party library is
redistributed. Even the dependency graph is drawn with plain DOM calls. There is
therefore no third-party license obligation to discharge and nothing here to
attribute.

If a third-party library is ever added, its full license text must ship beside
it; the `pages` workflow fails closed on any vendored file under `site/` to
enforce that.
