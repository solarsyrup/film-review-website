# Automatic posters and TV reviews

The site uses **TMDB (The Movie Database)** to find posters for Film and TV entries, download a local copy to `public/images/posters/`, and insert the local `cover` path into the entry's Markdown frontmatter.

## One-time setup (required before automatic posters work)

1. Make a free [TMDB account](https://www.themoviedb.org/signup) and request API credentials under [TMDB API settings](https://www.themoviedb.org/settings/api). Check the provider's license; their developer API is for non-commercial use with attribution. If your website becomes commercial, review TMDB licensing.
2. Copy the **API Read Access Token (v4 auth)**, NOT the short v3 API key.
3. In GitHub, open **solarsyrup/film-review-website → Settings → Secrets and variables → Actions → New repository secret**. Name it exactly `TMDB_API_TOKEN`, paste the long token, and save it. Never put the token in a Markdown entry, commit, or chat message.
4. Open **Actions → Automatically import film and TV posters → Run workflow → main → Run workflow**. This first run attempts to backfill existing entries. Future edits to reviews and diary entries trigger the workflow automatically.

The workflow requires repository Actions permissions to write contents. If the job ends in a 403 on git push, go to **Settings → Actions → General → Workflow permissions** and enable **Read and write permissions** for `GITHUB_TOKEN`, then rerun.

The script uses the standard TMDB `/search/movie`, `/search/tv`, and `/movie/{id}` or `/tv/{id}` endpoints, followed by a w500 poster image from `image.tmdb.org`. It only imports when a title matches confidently and, if a release year is supplied, that year matches. Ambiguous names or missing images are left untouched; nothing is guessed. Files are stored locally and committed by GitHub Actions so the static Cloudflare site does not need an API key.

## How to post a TV review right now

Go to **Pages CMS → Reviews → New**. Change the new **Medium** dropdown from Film to **TV**. Enter a TV title, release year, date and your rating. The **Director / Creator** field is now optional. Save. It will appear on your Journal, Archive, and site search with a TV label.

If you want a short viewing note instead, use **The Diary → New**, choose **TV**, and enter a date and note.

The Archive's **Medium** dropdown now shows Film, TV, Music, Game, Book and Other even when no entries of a type are published. The sitewide search `/search/` is text search; it searches any type.

## Posters

- Leave **Poster / Cover** empty for automatic matching.
- If you manually upload a poster in CMS, it takes priority and will never be overwritten by the importer.
- If the wrong work was matched, change the cover manually or clear it and add the correct **TMDB ID** from the matching TMDB title page; rerun the importer.
- Set **Automatically find a poster** to false to opt out.
- This automation only looks up posters for entries whose Medium is Film or TV. Other media can still use the normal CMS image upload field.
- To reuse artwork in the Archive and on a review's page, you only need one `cover` value. Once imported, Cloudflare rebuilds when the action commits.
- If you add a new secret after the original workflow has already run, manually rerun the workflow once.

Artwork and metadata are credited to TMDB on the About page. The API is free for non-commercial projects subject to TMDB's attribution and license conditions.
