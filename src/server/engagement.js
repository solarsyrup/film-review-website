// Cloudflare Pages Functions helpers. All sensitive values remain on the server.
const encoder = new TextEncoder();
const MAX_POST_BYTES = 10000;
const VISITOR_COOKIE = "__Host-atc_visitor";

export function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      ...headers,
    },
  });
}

export function configured(env) {
  return Boolean(
    env?.ENGAGEMENT_DB &&
    typeof env.TURNSTILE_SITE_KEY === "string" && env.TURNSTILE_SITE_KEY &&
    typeof env.TURNSTILE_SECRET_KEY === "string" && env.TURNSTILE_SECRET_KEY &&
    typeof env.COOKIE_SECRET === "string" && env.COOKIE_SECRET.length >= 32
  );
}

export function sameOrigin(request) {
  const origin = request.headers.get("Origin");
  return Boolean(origin && origin === new URL(request.url).origin);
}

export async function smallJson(request) {
  if (!(request.headers.get("Content-Type") || "").toLowerCase().startsWith("application/json")) {
    throw new Error("Send JSON data.");
  }
  const declared = Number(request.headers.get("Content-Length") || 0);
  if (declared > MAX_POST_BYTES) throw new Error("Submission is too large.");
  if (!request.body) throw new Error("Missing submission.");
  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_POST_BYTES) {
        await reader.cancel();
        throw new Error("Submission is too large.");
      }
      chunks.push(value);
    }
    const merged = new Uint8Array(total);
    let at = 0;
    for (const chunk of chunks) { merged.set(chunk, at); at += chunk.byteLength; }
    const data = JSON.parse(new TextDecoder().decode(merged));
    if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("Invalid submission.");
    return data;
  } catch (error) {
    if (error instanceof SyntaxError) throw new Error("Invalid JSON.");
    throw error;
  } finally {
    reader.releaseLock();
  }
}

async function hmacHex(secret, value) {
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(value));
  return Array.from(new Uint8Array(signature), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function constantTimeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let different = 0;
  for (let i = 0; i < a.length; i++) different |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return different === 0;
}

export async function visitorCookie(request, secret) {
  const raw = (request.headers.get("Cookie") || "")
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(VISITOR_COOKIE + "="));
  const value = raw?.slice(VISITOR_COOKIE.length + 1) ?? "";
  const match = value.match(/^([0-9a-f-]{36})\.([0-9a-f]{64})$/);
  if (match) {
    const expected = await hmacHex(secret, "visitor:" + match[1]);
    if (constantTimeEqual(match[2], expected)) return { id: match[1], header: null };
  }

  const id = crypto.randomUUID();
  const signature = await hmacHex(secret, "visitor:" + id);
  const header =
    `${VISITOR_COOKIE}=${id}.${signature}; Max-Age=31536000; Path=/; Secure; HttpOnly; SameSite=Lax`;
  return { id, header };
}

export function cookieHeaders(visitor) {
  return visitor?.header ? { "Set-Cookie": visitor.header } : {};
}

export async function ipActor(request, secret) {
  // Only use the trusted Cloudflare header, never a user-supplied X-Forwarded-For value.
  const ip = request.headers.get("CF-Connecting-IP");
  if (!ip || ip.length > 80) return null;
  return hmacHex(secret, "ip:" + ip);
}

export async function validEntry(env, request, entryKey) {
  if (typeof entryKey !== "string" || !/^(review|portfolio|guestbook):[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$/.test(entryKey)) return false;
  const [kind, slug] = entryKey.split(":");
  const sourceUrl = new URL("/interaction-entries.json", request.url);
  const res = await env.ASSETS.fetch(new Request(sourceUrl, { method: "GET" }));
  if (!res.ok) throw new Error("Entry allowlist unavailable");
  const manifest = await res.json();
  return Array.isArray(manifest?.[kind]) && manifest[kind].includes(slug);
}

export async function verifyTurnstile(env, request, token) {
  if (typeof token !== "string" || token.length < 10 || token.length > 2048) return false;
  const form = new FormData();
  form.set("secret", env.TURNSTILE_SECRET_KEY);
  form.set("response", token);
  const ip = request.headers.get("CF-Connecting-IP");
  if (ip) form.set("remoteip", ip);
  try {
    const result = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(8000),
    });
    if (!result.ok) return false;
    const data = await result.json();
    // Checking both action and hostname helps stop cross-site token reuse.
    return data.success === true &&
      data.action === "atc_engagement" &&
      data.hostname === new URL(request.url).hostname;
  } catch {
    return false; // Siteverify unavailable: fail closed.
  }
}

export function validName(value) {
  return typeof value === "string" &&
    value.trim().length >= 2 && value.trim().length <= 40 &&
    !/[\u0000-\u001f\u007f-\u009f]/.test(value);
}

export function validComment(value) {
  return typeof value === "string" &&
    value.trim().length >= 3 && value.trim().length <= 1600 &&
    !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/.test(value) &&
    (value.match(/https?:\/\//gi) || []).length <= 2;
}

export async function enforceRate(db, action, actor, now) {
  // Atomic INSERT IF under limit; parallel requests cannot bypass quotas.
  const isComment = action === "comment";
  const windowStart = now - (isComment ? 3600 : 86400);
  const maxHits = isComment ? 3 : 25;
  const minGap = isComment ? 90 : 8;
  const result = await db.prepare(`
    INSERT INTO request_events (action, actor_hash, created_at)
    SELECT ?, ?, ?
    WHERE (SELECT COUNT(*) FROM request_events
           WHERE action = ? AND actor_hash = ? AND created_at >= ?) < ?
      AND NOT EXISTS (SELECT 1 FROM request_events
                      WHERE action = ? AND actor_hash = ? AND created_at > ?)
  `).bind(action, actor, now, action, actor, windowStart, maxHits, action, actor, now - minGap).run();
  return (result.meta?.changes ?? 0) === 1;
}

export async function cleanOldRates(db, now) {
  await db.prepare("DELETE FROM request_events WHERE created_at < ?")
    .bind(now - 172800).run();
}

export async function checkAdminAuth(request, env) {
  const provided = request.headers.get("Authorization") || "";
  const expected = env.MODERATION_TOKEN;
  if (typeof expected !== "string" || expected.length < 32) return false;
  if (!provided.startsWith("Bearer ")) return false;
  // Digest both values to compare fixed-length strings without an early-exit secret match.
  const value = provided.slice(7);
  if (value.length > 512) return false;
  const [actualHash, expectedHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(value)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  const a = new Uint8Array(actualHash), b = new Uint8Array(expectedHash);
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) mismatch |= a[i] ^ b[i];
  return mismatch === 0;
}
