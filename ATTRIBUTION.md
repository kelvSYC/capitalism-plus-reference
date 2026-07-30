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
see `data/site_template.html` for the methodology and verification evidence
behind each mechanic. No game code, script text, or executable is
reproduced. Scenario descriptions on the site are original paraphrases, not
reproductions of the game's narrative text.

## The open question: product icons

`site/images/` (git-ignored, not committed — see `.gitignore`) holds 245
small (120x120) product icons extracted from the game's own compiled raster
asset files, one per product, used purely to help players visually identify
items while playing.

Whether displaying these on a public reference site qualifies as fair use
(nominative, identificatory use of small game-asset icons in a
non-commercial fan reference, similar to how many game wikis display sprite
art) is a real question we have not resolved, not a settled conclusion.
Until it is, the icons stay out of version control and out of any public
deployment of this site; only the local working copy (populated from your
own legitimately-owned copy of the game) has them. Resolving this — either
via a fair-use determination, replacement placeholder art, or direct contact
with Enlight — is a precondition for making this site public, not an
afterthought.

## Engine / libraries

- **D3.js v7.9.0** (`site/d3.min.js`), BSD-licensed, Copyright 2010-2023 Mike
  Bostock — used for the interactive dependency graph. Redistributed
  unmodified; its own license header is intact in the file.
