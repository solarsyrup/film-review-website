import {
  json, configured, sameOrigin, smallJson, visitorCookie, cookieHeaders,
  ipActor, validEntry, verifyTurnstile, validName, validComment,
  enforceRate, cleanOldRates,
} from "../_lib/engagement.js";

const unavailable = () => json({
  error: "Comments and likes are not available until Cloudflare setup is complete.",
}, 503);

export async function onRequestGet({ request, env }) {
  if (!configured(env)) return unavailable();
  try {
    const entry = new URL(request.url).searchParams.get("entry");
    if (!(await validEntry(env, request, entry))) return json({ error: "Entry not found." }, 404);
    const visitor = await visitorCookie(request, env.COOKIE_SECRET);

    const [countResult, mine, comments] = await Promise.all([
      env.ENGAGEMENT_DB.prepare("SELECT COUNT(*) AS total FROM likes WHERE entry_key = ?").bind(entry).first(),
      env.ENGAGEMENT_DB.prepare("SELECT 1 AS yes FROM likes WHERE entry_key = ? AND visitor_id = ? LIMIT 1")
        .bind(entry, visitor.id).first(),
      env.ENGAGEMENT_DB.prepare(`
        SELECT id, display_name AS name, body, created_at AS createdAt
        FROM comments
        WHERE entry_key = ? AND status = 'approved'
        ORDER BY created_at DESC LIMIT 50
      `).bind(entry).all(),
    ]);

    return json({
      count: Number(countResult?.total || 0),
      liked: Boolean(mine),
      comments: comments.results || [],
      siteKey: env.TURNSTILE_SITE_KEY,
    }, 200, cookieHeaders(visitor));
  } catch (error) {
    console.error("ATC engagements read:", error);
    return json({ error: "Unable to load the discussion right now." }, 503);
  }
}

export async function onRequestPost({ request, env }) {
  if (!configured(env)) return unavailable();
  if (!sameOrigin(request)) return json({ error: "Request origin not allowed." }, 403);

  let input;
  try { input = await smallJson(request); }
  catch (error) { return json({ error: error.message || "Invalid submission." }, 400); }

  const entry = input.entry;
  const action = input.action;
  if (!["like", "unlike", "comment"].includes(action)) {
    return json({ error: "Unknown action." }, 400);
  }

  try {
    if (!(await validEntry(env, request, entry))) return json({ error: "Entry not found." }, 404);

    if (action === "comment") {
      if (input.website) {
        // Honeypot: don't tell automated submissions which trap they hit.
        return json({ ok: true, pending: true, message: "Submitted for review." }, 202);
      }
      if (!validName(input.name) || !validComment(input.body)) {
        return json({ error: "Use a name (2–40 characters) and a comment (3–1600 characters). Maximum two links." }, 400);
      }
    }

    const actor = await ipActor(request, env.COOKIE_SECRET);
    if (!actor) return json({ error: "Request could not be verified." }, 403);

    if (!(await verifyTurnstile(env, request, input.turnstileToken))) {
      return json({ error: "Verification failed or expired. Please try the challenge again." }, 403);
    }

    const now = Math.floor(Date.now() / 1000);
    const allowed = await enforceRate(env.ENGAGEMENT_DB, action === "comment" ? "comment" : "like", actor, now);
    if (!allowed) return json({ error: "Too many submissions. Please try again later." }, 429, { "Retry-After": "90" });

    const visitor = await visitorCookie(request, env.COOKIE_SECRET);
    const headers = cookieHeaders(visitor);

    if (action === "comment") {
      await env.ENGAGEMENT_DB.prepare(`
        INSERT INTO comments (id, entry_key, display_name, body, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
      `).bind(crypto.randomUUID(), entry, input.name.trim(), input.body.trim(), now, now).run();

      // Opportunistic cleanup: no source IPs stored; only short-lived keyed hashes.
      await cleanOldRates(env.ENGAGEMENT_DB, now);
      return json({
        ok: true, pending: true,
        message: "Thanks! Your comment was sent for approval and is not public yet.",
      }, 202, headers);
    }

    if (action === "like") {
      await env.ENGAGEMENT_DB.prepare(`
        INSERT OR IGNORE INTO likes (entry_key, visitor_id, created_at)
        VALUES (?, ?, ?)
      `).bind(entry, visitor.id, now).run();
    } else {
      await env.ENGAGEMENT_DB.prepare(`
        DELETE FROM likes WHERE entry_key = ? AND visitor_id = ?
      `).bind(entry, visitor.id).run();
    }

    const result = await env.ENGAGEMENT_DB.prepare(`
      SELECT COUNT(*) AS total FROM likes WHERE entry_key = ?
    `).bind(entry).first();

    await cleanOldRates(env.ENGAGEMENT_DB, now);
    return json({
      ok: true, count: Number(result?.total || 0), liked: action === "like",
    }, 200, headers);
  } catch (error) {
    console.error("ATC engagements write:", error);
    return json({ error: "The submission could not be saved. Please try again." }, 503);
  }
}
