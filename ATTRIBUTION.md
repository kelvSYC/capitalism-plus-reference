# Attribution

> **Icon position: granted, in writing.** On 2026-08-02 Enlight Software gave
> permission to display the product icons and to include the files in this
> repository, public or not. The grant and the undertakings we gave in return are
> quoted below. The icons remain Enlight's property, not ours, and come out on
> request. Nothing in this document is open.

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

## Product icons: permission granted

`site/images/` holds 251 icons extracted from the game's own compiled raster
files — 245 products at 120×120, plus the six growing plants the game shows
beside their crops. They are displayed on the site and committed here under
written permission from Enlight Software.

**Granted by:** David Lee, Marketing and Community Manager, Enlight Software
(`info@enlight.com`)

**When:** 1 August 2026, extended 2 August 2026 on the question of the repository.

**The grant, quoted:**

> We are happy to grant permission for you to display the Capitalism Plus product
> icons on your fan reference site.

> Yes — the permission also extends to including the icon files in the source
> repository, even if it becomes public in the future. Your plan to provide
> attribution and to remove the files immediately upon request is appreciated and
> fully acceptable.

**What we undertook in return, and are bound by:**

- Non-commercial use, on this reference only.
- Icons at their original size, for identification, one per product entry.
- Attribution to Enlight Software Limited and a link to Capitalism Lab — in the
  rendered page, not only in this file.
- Immediate removal on request, without question.

The icons are **not** covered by this project's `LICENSE`, which covers only
material we are in a position to license. `REUSE.toml` marks `site/images/**`
with Enlight's copyright and `LicenseRef-Enlight-FanReference-2026`, so a file
appearing there can never be mistaken for one of ours.

The guards that used to keep the icons out are now inverted rather than deleted:
the `pages` workflow refuses to deploy artwork unless this grant is recorded in
this file, and `tests/test_data.py` asserts the tracked icons match the dataset
exactly. Removing the grant from this file breaks the deploy, which is the
intended way round — the permission and the artwork travel together.

### The one residual risk

Permission from Enlight settles Enlight's rights, not necessarily every right in
the images. On Enlight's own forum a user raised that "it is possible that enlight
could run into copyright issues for those images, particularly if they were
originally sourced from a third party who still holds copyright"
(<https://www.capitalism2.com/forum/viewtopic.php?t=922>), and the requester did
not know "what the license is that Enlight has with the images it used, whether
they were in the public domain (quite possibly) or if they actually licensed them
from somebody". For a 1996 product catalogue, licensed stock art is plausible.

Enlight has now twice asserted the authority to grant, including once in direct
answer to a question that offered "we cannot" as an acceptable reply. That is as
far as this can reasonably be taken by asking. The removal-on-request undertaking
is the mitigation if it ever proves mistaken.

## Engine / libraries

**None.** The site is a single self-contained HTML file: all CSS and JavaScript
is inlined, nothing is fetched from a CDN, and no third-party library is
redistributed. Even the dependency graph is drawn with plain DOM calls. There is
therefore no third-party license obligation to discharge and nothing here to
attribute.

If a third-party library is ever added, its full license text must ship beside
it; the `pages` workflow fails closed on any vendored file under `site/` to
enforce that.
