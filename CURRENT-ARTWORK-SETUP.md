# Automatic artwork for "Currently Experiencing"

## How it works

The homepage supports four types of automatically downloaded artwork:

| Homepage field | Provider | Repository secret |
| --- | --- | --- |
| Currently Watching | [TMDB](https://www.themoviedb.org/) (movie or TV posters) | `TMDB_API_TOKEN` |
| Currently Reading | [Open Library](https://openlibrary.org/) (book and manga covers), with [Jikan](https://jikan.moe/) manga series-cover fallback | None |
| Currently Listening | [MusicBrainz](https://musicbrainz.org/) / [Cover Art Archive](https://coverartarchive.org/) (album artwork) | None |
| Currently Playing | [RAWG](https://rawg.io/apidocs) (game cover/background art) | `RAWG_API_KEY` |

**You only need two API keys, not four.** Watching uses the existing TMDB key from automatic review posters. MusicBrainz, Cover Art Archive and Open Library do not require new credentials for occasional homepage updates.

### One-time setup

1. In your GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.
2. Set `TMDB_API_TOKEN` to your TMDB **API Read Access Token** from https://www.themoviedb.org/settings/api (skip if you already added this for film posters).
3. Obtain a RAWG API key from https://rawg.io/apidocs and create the GitHub Actions secret `RAWG_API_KEY`.
4. Go to **Actions → Automatically import current media artwork → Run workflow → main** to fetch the artwork for the current homepage values.
5. Future Homepage saves in Pages CMS automatically trigger the same workflow. The workflow commits downloaded images to `public/images/currently/` and fills each matching `currently...Cover` field. Cloudflare deploys the resulting commit.

If the GitHub Action gets a git push 403 error, enable **Settings → Actions → General → Workflow permissions → Read and write permissions**.

### Using Pages CMS

Open **Homepage** in https://app.pagescms.org/. Fill in any of the four text fields:

- **Currently Watching**: Movie or show title. Select **Watching - Type** (`TV` or `Film`; defaults to `TV`). An optional original release year helps differentiate remakes.
- **Currently Reading**: Book or manga title. Optionally specify **Reading - Author**. A text value like `JoJolion - Hirohiko Araki` is also recognized. Set **Reading - Volume Number** to an exact volume, e.g. `7`; the importer will never choose a different volume. If you leave the volume blank, it prefers Volume 1, then a generic series cover if available. You can also write `JoJolion Vol. 7` in the title.
- **Currently Listening**: Album or EP title. Set **Listening - Music Artist** for accuracy, or write `Masayoshi Takanaka — Seychelles`.
- **Currently Playing**: Game title. Optionally set **Playing - Release Year**.

Each category also has:
- **Cover**: upload custom artwork. If supplied, the importer will never overwrite it.
- **Automatically Find Artwork**: turn off to disable lookup for that category.

If you change an item's title, the importer replaces a previous *automatically managed* cover with matching artwork. If no reliable match exists, it does not choose a random cover. For obscure manga, albums, games, or alternate editions, manually upload the preferred cover. Manga fallback artwork is fetched from Jikan/MyAnimeList only when no volume is explicitly requested.

### Technical and licensing notes

The automated workflow is in `.github/workflows/import-current-artwork.yml`; the source code is in `scripts/import_current_artwork.py`. No secrets are sent to browsers. Image files are stored in the site; the public homepage shows provider credits and a RAWG link as required by RAWG's free noncommercial API.

Provider usage must respect each service's terms. TMDB and RAWG free access are for noncommercial/personal projects; MusicBrainz noncommercial API access is free with a meaningful User-Agent and a strict one-request-per-second cap; Open Library's APIs are intended for occasional public-good lookup rather than bulk or high-traffic third-party backends. This workflow only runs when the owner updates the homepage or manually triggers it.

See `AUTO-POSTERS-SETUP.md` for the separate film/TV review and diary poster importer.
