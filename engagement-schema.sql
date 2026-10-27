-- After the Credits: Cloudflare D1 storage for likes, comments and throttling.
-- Paste this entire file into D1 > Console and run it once.
-- Every comment is invisible until explicitly approved by the site owner.

CREATE TABLE IF NOT EXISTS comments (
  id TEXT PRIMARY KEY,
  entry_key TEXT NOT NULL,
  display_name TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected')),
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS comments_public
  ON comments (entry_key, status, created_at DESC);

CREATE INDEX IF NOT EXISTS comments_moderation
  ON comments (status, created_at DESC);

CREATE TABLE IF NOT EXISTS likes (
  entry_key TEXT NOT NULL,
  visitor_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (entry_key, visitor_id)
);

CREATE INDEX IF NOT EXISTS likes_by_entry ON likes (entry_key);

-- Contains only keyed hashes of visitor IPs, no original addresses.
-- Entries older than 48 hours are deleted during subsequent submissions.
CREATE TABLE IF NOT EXISTS request_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  actor_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS request_events_limit
  ON request_events (action, actor_hash, created_at);
