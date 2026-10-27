# Comments and Likes — Cloudflare Setup

The code is installed. **It deliberately refuses submissions until every required setting is present.** No API keys or other secrets belong in GitHub or Pages CMS.

## 1. Create and initialize D1

1. Open https://dash.cloudflare.com and choose **Workers & Pages > D1** (or **Storage & Databases > D1**, depending on the dashboard).
2. Create a database named `after-the-credits-engagement`.
3. Open its **Console** (SQL editor).
4. Open `engagement-schema.sql` from this GitHub repository. Copy **the entire SQL file** into the Console and run it. It creates the `likes`, `comments`, and `request_events` tables.
5. Open **Workers & Pages > afterthecredits > Settings > Bindings** (choose Production if your dashboard separates environments). Add a **D1 database** binding with:
   - **Variable name:** `ENGAGEMENT_DB`
   - **Database:** `after-the-credits-engagement`

Do not put database identifiers in a hand-written Wrangler configuration: the Dashboard binding is enough and does not risk overriding your existing Pages project settings.

## 2. Create a Turnstile widget

1. In Cloudflare, open **Turnstile** and create a widget for `afterthecredits.pages.dev`.
2. Select a managed/non-intrusive widget. If you also use the old `film-review-website.pages.dev` domain, allow it too or make a second widget for that project.
3. Copy the **Site key** and **Secret key**. They are different.
4. Open **Workers & Pages > afterthecredits > Settings > Variables and Secrets**. Add:
   - `TURNSTILE_SITE_KEY` — the **public** site key (text).
   - `TURNSTILE_SECRET_KEY` — the **private** secret key (**encrypt** this value).

Both the like button and the comment form require a valid Turnstile token. **The server** verifies every token using Cloudflare Siteverify and checks its hostname and action. Fake, expired, reused, or missing tokens are rejected. Do not turn off the server-side checks.

## 3. Set secret keys for visitors and moderation

Create **two different random** keys on your Linux computer:

```sh
openssl rand -hex 32
openssl rand -hex 32
```

Add each to **Workers & Pages > afterthecredits > Settings > Variables and Secrets** as encrypted secrets:

- `COOKIE_SECRET` — use the first random value. It signs the anonymous browser cookie and keys the IP hashes used for rate limiting.
- `MODERATION_TOKEN` — use the second, different random value. This is your private moderator login key.

Both must contain at least 32 characters. **Do not paste these secrets into GitHub, Pages CMS, the public website, or this chat.** Store the moderator key in your password manager.

If you have separate **Production** and **Preview** environments, configure the production bindings and variables at a minimum. Keep Preview disabled unless you intentionally configure it with its own secrets and allowed Turnstile hostnames.

## 4. Redeploy

After saving the D1 binding and all four variables/secrets, go to **Workers & Pages > afterthecredits > Deployments** and redeploy the current commit. A simple new commit also triggers a Git deployment.

Open a review, for example:
https://afterthecredits.pages.dev/reviews/clayface-review/

And a portfolio project:
https://afterthecredits.pages.dev/portfolio/cc1/

Beneath the entry you should now see:
- A **heart** and count (one like per signed browser identifier).
- A Turnstile challenge (complete it before liking or posting).
- A **display name** and **comment** form.
- Approved comments, if any.

Comments do not appear to visitors until you approve them.

## 5. Approve and remove comments

Visit **https://afterthecredits.pages.dev/moderate/**

1. Paste your `MODERATION_TOKEN` value into the password field.
2. Click **Load comments**. By default it shows **Awaiting approval**.
3. Click **Approve** to publish, **Reject** to hide, or **Delete permanently** to remove from the database.
4. Switch to **Published** to remove inappropriate comments that were already approved.

The page is **not linked** from the public site. Its location is not the security control: the API requires the long secret for every action. The secret isn't stored in localStorage or your database. Do not share it.

## Safety defaults and limitations

- Every write requires a **server-verified** Turnstile challenge plus an exact same-origin request.
- Comments are **pending by default** and displayed as **plain text**, preventing user-supplied HTML/JavaScript execution.
- Submission limits per hashed Cloudflare visitor IP: **3 comments/hour with 90 seconds between submissions**, and **25 like changes/day with 8 seconds between changes**. These are an additional guard, not a guarantee against all spam.
- Each browser has a year-long **signed, secure, HttpOnly, SameSite=Lax cookie** to limit repeat likes on each entry. Clearing cookies or using another browser can bypass one-person-one-like: accounts would be needed for stricter guarantees.
- Visitor IPs are never written in plaintext to D1. A secret-keyed hash is kept in a rate-limit table, and expired entries are pruned during subsequent submissions (normally within 48 hours, though idle databases are not actively cleaned).
- Each entry is verified against a **build-time allowlist of actual review and portfolio slugs**; arbitrary names cannot create fake discussions.
- Comments have a 40-character display-name limit and 1,600-character text limit, with link limits and a honeypot field.
- Public endpoints return `Cache-Control: no-store` and do not offer CORS access.
- The site needs JavaScript for submitting; disabling JS or blocking Turnstile prevents submissions. The existing static reviews and projects still display normally.
- Regular readers cannot view pending/rejected comments. The private moderation key is required for owner actions.
- Consider adding a Cloudflare rate limiting rule for `/api/engagement` if automated traffic becomes high. Watch Pages Functions and D1 request quotas.

## Troubleshooting

**“Comments and likes are not available until Cloudflare setup is complete.”**
One of the database binding, site key, secret key, or `COOKIE_SECRET` is missing in the deployed environment. Confirm the variables are assigned to **the Pages project you're actually visiting**, then redeploy.

**“Unable to load the discussion right now.”**
Most often, the D1 tables were not initialized. Check D1 Console for `likes`, `comments`, and `request_events`; then check Pages Functions logs.

**“Verification failed or expired.”**
Turnstile must allow the precise domain you're on. Both the widget action (`atc_engagement`) and the hostname are checked by the server. Complete the challenge again before resubmitting.

**Moderation key rejected.**
Check `MODERATION_TOKEN` in your Pages secrets. It must be the *same value* you enter on the private moderation page; changing it requires a redeploy.

**Cloudflare Pages builds normally but API routes return 404.**
Make sure you use the **Git-connected Pages project** and that the repo's root `functions/` directory is present in the deployment. The static site itself should still work if the API is unavailable.

Documentation:
- https://developers.cloudflare.com/pages/functions/bindings/
- https://developers.cloudflare.com/turnstile/get-started/
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
