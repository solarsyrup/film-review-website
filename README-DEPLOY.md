# After the Credits — redesign files

This is a patch for your existing Astro repository, not a replacement for the whole project. It adds:
- a charcoal / muted-red design with a warm paper-inspired light theme
- a working light/dark toggle that remembers the reader's choice
- CMS-editable homepage and About page content
- CMS fields for optional review summaries

## Apply to your existing repository (Linux)

1. Download and extract this ZIP.
2. Open a terminal in your existing cloned `film-review-website` repository.
3. Copy the extracted files into the repository root, preserving their folders. When asked, overwrite the existing files.
4. Run `npm install` and `npm run build`.
5. If the build succeeds, run:
   ```
   git status
   git add .pages.yml src/layouts/BaseLayout.astro src/pages/index.astro src/pages/about.astro src/content.config.ts src/content/pages
   git commit -m "Redesign After the Credits"
   git push
   ```
6. Cloudflare Pages should start a deployment automatically after the push. Watch the Deployments page and open the live site when the build completes.
7. Open Pages CMS and refresh. You should see a **Site Pages** collection with entries for **home** and **about**. Edit their fields and save to publish text changes.

## Important notes

- This patch does not replace your existing review Markdown files or your Cloudflare settings.
- Keep the `slug` field as `home` for the homepage entry and `about` for the About entry. These IDs tell the website which content belongs on each route.
- If the local build fails, do not push yet; send the first error from the terminal.
- The theme toggle uses browser local storage, so each visitor's choice is remembered on that browser.
