import {
  json, configured, sameOrigin, smallJson, checkAdminAuth,
  ipActor, enforceRate,
} from "../../src/server/engagement.js";

export async function onRequestPost({ request, env }) {
  if (!configured(env) || typeof env.MODERATION_TOKEN !== "string" || env.MODERATION_TOKEN.length < 32) {
    return json({ error: "Moderation is not configured." }, 503);
  }
  if (!sameOrigin(request)) return json({ error: "Request origin not allowed." }, 403);

  try {
    if (!(await checkAdminAuth(request, env))) {
      // Failed attempts are throttled; successful owner actions are not.
      const actor = await ipActor(request, env.COOKIE_SECRET);
      if (actor) {
        const rate = await enforceRate(env.ENGAGEMENT_DB, "admin_failed", actor, Math.floor(Date.now() / 1000));
        if (!rate) return json({ error: "Too many login attempts." }, 429);
      }
      return json({ error: "Invalid moderation key." }, 401);
    }

    let data;
    try { data = await smallJson(request); }
    catch (error) { return json({ error: error.message || "Invalid request." }, 400); }

    if (data.operation === "list") {
      const status = ["pending", "approved", "rejected"].includes(data.status) ? data.status : "pending";
      const offset = Number.isInteger(data.offset) && data.offset >= 0 && data.offset <= 10000 ? data.offset : 0;
      const [rows, count] = await Promise.all([
        env.ENGAGEMENT_DB.prepare(`
          SELECT id, entry_key AS entryKey, display_name AS name, body, created_at AS createdAt
          FROM comments WHERE status = ? ORDER BY created_at DESC LIMIT 50 OFFSET ?
        `).bind(status, offset).all(),
        env.ENGAGEMENT_DB.prepare("SELECT COUNT(*) AS total FROM comments WHERE status = ?")
          .bind(status).first(),
      ]);
      return json({ comments: rows.results || [], total: Number(count?.total || 0), status, offset });
    }

    if (!["approve", "reject", "delete"].includes(data.operation) ||
        typeof data.id !== "string" || !/^[a-z0-9-]{36}$/i.test(data.id)) {
      return json({ error: "Invalid moderation action." }, 400);
    }

    const result = data.operation === "delete"
      ? await env.ENGAGEMENT_DB.prepare("DELETE FROM comments WHERE id = ?").bind(data.id).run()
      : await env.ENGAGEMENT_DB.prepare("UPDATE comments SET status = ?, updated_at = ? WHERE id = ?")
          .bind(data.operation === "approve" ? "approved" : "rejected", Math.floor(Date.now() / 1000), data.id).run();

    if ((result.meta?.changes ?? 0) === 0) return json({ error: "Comment not found." }, 404);
    return json({ ok: true, operation: data.operation });
  } catch (error) {
    console.error("ATC moderation:", error);
    return json({ error: "Moderation request failed." }, 503);
  }
}
