# מוריה | MORIAH

**The Jewish & Israel Review · כתב עת ליהדות ולישראל**  
Torah · People · Land / תורה · עם · ארץ

Public newspaper: https://moriahise.github.io/Moriah/

## What runs automatically

- RSS/Atom source collection approximately every four hours.
- Hebrew ↔ English headline translation using locally executed OPUS/Argos models; no paid AI key required. Arabic and Russian video titles can be translated through English.
- Attributed source links, official-channel video metadata, searchable headlines and a 24-section bilingual learning library.
- Location-specific Shabbat/Parashah/Haftarah data for Jerusalem, Tel Aviv, Haifa, Vienna, London and New York. Hebcal attribution and calculation settings remain visible.
- A navigable Hebrew/civil month calendar with local zmanim, holidays and readings, calculated in the browser.
- Direct weekly Shiurim and Haftarah links, all 54 Zohar portions, the actual daily Daf and embedded Jastrow search.
- Nine real Niggunim collections with rotating playlists/series, and daily Sanhedrin question cards linked to existing answers. [Integration details](docs/INTEGRATIONS.md).
- Frozen weekly editions after Wednesday 18:00 **Asia/Jerusalem**, with missed-run catch-up and correct daylight-saving conversion.
- Hebrew and English **16-page PDFs**, online reading editions, an archive and RSS.
- Data, interface, PDF and local-link checks before publishing. Last successful collection is retained if every live source fails.

Schedules can be delayed by GitHub. This is an automatically compiled newspaper, not a claim of independent reporting, human editorial review or rabbinic approval. Machine translations are labelled and the original headline is accessible. The original plan has been adapted to the owner’s request for autonomous operation.

## One-time hosting setup

If Pages is not already active: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Then open Actions, select **MORIAH · collect, translate & publish**, and choose **Run workflow**.

The normal public pipeline needs no personal token and no OpenAI secret. The workflow uses this repository’s built-in `GITHUB_TOKEN` with `contents: write`, `pages: write`, and `id-token: write`. Account/organisation restrictions may require the owner to enable Actions or allow those permissions. Pages deployment must be activated by an administrator once; the workflow cannot grant itself administrative permission. A failed Pages configuration does not discard the built website artifact or validated data.

## Two repositories

- **Moriah**: independently operating public newspaper, current published configuration, pipeline and website.
- **Moriah-Redaktion**: private configuration, drafts, private twice-daily previews and reports. Private drafts never enter the public build.

A public repository’s `GITHUB_TOKEN` cannot read a different private repository. Therefore the public newspaper deliberately continues autonomously using its own publishable configuration. To make private configuration edits flow automatically to the public repository, the owner can optionally add **`MORIAH_PUBLISH_TOKEN`** in the private repository. Its export script transmits only six explicitly allowlisted configuration/content files; it never exports drafts, private state, reviewer notes or secrets. Setup is documented in the private repo. Without this connection the public newspaper still updates and publishes; private configuration edits remain private.

## Source availability

Every requested publisher/broadcaster is represented in the source directory, including publishers whose current feed is unavailable. Feed status is measured on each run and displayed honestly. A directory entry does not imply a working feed, partnership or endorsement. Old or undated feed items are not promoted as current news. Ynet/Ynetnews, B’Sheva and Arutz Sheva are identified distinctly, with family grouping for selection diversity.

The system reads publisher-provided RSS/Atom metadata. It does not download article bodies, bypass paywalls or download/rehost videos. Official YouTube channel IDs were resolved from canonical channel metadata, rather than guessed from similarly named handles.

## Local development

Python 3.12 and Node 22:

```bash
pip install -r requirements.txt
npm ci --ignore-scripts
python scripts/pipeline.py
python scripts/ecosystem.py
npm run build:integrations
python -m unittest discover -s tests -v
npm test
python scripts/build.py
python scripts/verify_build.py
python -m http.server 8080 --directory _site
```

Use `python scripts/pipeline.py --offline` to rebuild from saved data without polling. Use `--no-translate` to avoid model downloads. Translation failure preserves the original headline; missing translations are never fabricated. Models are downloaded from Argos’s official hosts and cached, not committed. PDFs use installed fonts with Hebrew shaping.

## Files

- `config/`: sources, channel IDs, 24 sections, location/schedule settings.
- `content/features.json`: original bilingual, AI-assisted learning guides.
- `scripts/pipeline.py`: source polling, validation, translation, calendar and issue snapshots.
- `scripts/build.py`: complete static site and frozen issue PDFs.
- `scripts/verify_build.py`: 16-page/embedded-text PDF gate and generated local-link checks.
- `data/latest.json`: latest successful public source collection.
- `data/issues/*.json`: immutable issue snapshots with actual publication time and revision.
- `data/translations.json`: bounded plain-text translation cache, not included in the website artifact.
- `web/index.html`, `assets/`: newspaper interface.
- `_site/`: generated deployment artifact, not committed.

Before any significant PDF layout change, render both languages and inspect the resulting pages. Do not rewrite archived snapshots to make old news look new. See [OPERATIONS.md](docs/OPERATIONS.md) for maintenance and correction procedures.

