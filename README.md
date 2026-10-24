# After the Credits — Film Review Website

A text-focused, dark film journal built with Astro. Intended for free Cloudflare Pages hosting and browser-based editing with Pages CMS.

## Publish it
1. Upload these files to your GitHub repository, keeping the folder structure intact.
2. In Cloudflare, open **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**.
3. Choose this repository. Set framework preset to **Astro**, build command to `npm run build`, and output directory to `dist`.
4. Deploy. Cloudflare supplies a free `*.pages.dev` address.
5. Visit https://pagescms.org/, sign in with GitHub, and choose this repository. The `.pages.yml` file configures the Reviews editor.

## Add a review
In Pages CMS, choose **Reviews** and create an entry. Required fields: film title, director, year, rating (0–5), review date, and review text. Save it; the GitHub commit triggers a new Cloudflare build.

You can also add Markdown files under `src/content/reviews/`. See `sample-review.md` for the format.
