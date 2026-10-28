# After the Credits — Archive, Diary, Guestbook, Search and More

These seven additions work with the existing static Astro site and the previously configured Cloudflare Pages/D1 interaction backend. No additional Cloudflare database tables or Turnstile keys are needed.

## New public pages

- `/archive/` — the full reviews + short diary entries index, with medium/year filters, text search and rating/title sorting.
- `/diary/` — chronological brief notes and optional star ratings.
- `/guestbook/` — visitors leave moderated, Turnstile-protected named messages. Messages are not public until approved.
- `/search/` — local, client-side search of journal reviews, diary entries and portfolio projects.
- `/random/` — sends visitors to a randomly selected review, diary entry, or portfolio project.
- The homepage also contains a **Currently experiencing** section when at least one relevant CMS field is filled in.
- Journal reviews support a **click-to-reveal spoiler section** via two optional CMS fields.

## Editing your content

Go to [Pages CMS](https://app.pagescms.org/) and select `solarsyrup/film-review-website` on `main`. Refresh after deployment.

**The Diary**: create a new entry with a title, unique lowercase-with-dashes slug, medium, and date. Add a rating (0–5), cover, short note, and optionally a link to a full review. Diary entries automatically appear in the Archive; there's no need to enter them again. Conversely, full reviews are automatically included in the Archive.

**Reviews**: optional **Medium** and **Cover / Poster** fields allow accurate categorization and artwork in the Archive. Existing reviews without a medium appear as Film by default.

**Homepage**: edit the four optional **Currently Watching**, **Reading**, **Listening**, and **Playing** fields. The section stays hidden when all four are empty.

**Review spoilers**: fill in **Hidden Spoiler Section** and optionally **Spoiler Button Text**. Only the spoiler text is hidden, with a native accessible disclosure button; the main review remains readable.

## Moderation

Guestbook messages go to the same D1 `comments` table. Open `/moderate/` and use your existing moderation key. Guestbook entries have the key `guestbook:main`. Like counts are omitted on the guestbook page; your ordinary reviews and portfolio entries keep their existing like buttons.

## Important notes

- The archive includes reviews and diary records. If you create a diary entry for a film you have also reviewed, both records will be displayed (one links to the review, the other to the diary).
- The search searches titles, summaries/notes, creators, medium and categories—not the complete text of every long article.
- Random entries are chosen in the visitor's browser. It does not save any visitor data.
- The existing Pages CMS, D1 schema, comments, ratings, and other pages are not altered by these new routes.
- As with earlier changes, Cloudflare must successfully deploy the new commit for the pages to become public.
