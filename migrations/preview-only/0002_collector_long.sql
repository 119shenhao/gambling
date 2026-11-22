-- DEV-only staging for gambling threads with up to 500 preserved replies.
-- No staged post or comment enters public topics until an atomic finish.
CREATE TABLE IF NOT EXISTS collector_long_stages (
 site TEXT NOT NULL,
 source_id TEXT NOT NULL,
 topic_id TEXT NOT NULL,
 lease_hash TEXT NOT NULL,
 title TEXT NOT NULL,
 body TEXT NOT NULL,
 source_lang TEXT NOT NULL,
 source_lang_mode TEXT NOT NULL,
 topic_status TEXT NOT NULL,
 content_hash TEXT NOT NULL,
 source_total INTEGER NOT NULL CHECK(source_total>=1),
 target_count INTEGER NOT NULL CHECK(target_count BETWEEN 1 AND 500),
 received INTEGER NOT NULL DEFAULT 0 CHECK(received BETWEEN 0 AND 500),
 capped INTEGER NOT NULL CHECK(capped IN (0,1)),
 status TEXT NOT NULL DEFAULT 'staging' CHECK(status IN ('staging','completed')),
 created_at INTEGER NOT NULL DEFAULT (unixepoch()),
 PRIMARY KEY(site,source_id),
 UNIQUE(topic_id)
);
CREATE TABLE IF NOT EXISTS collector_long_replies (
 site TEXT NOT NULL,
 source_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL CHECK(ordinal BETWEEN 0 AND 499),
 id TEXT NOT NULL UNIQUE,
 parent_ordinal INTEGER CHECK(parent_ordinal IS NULL OR (parent_ordinal>=0 AND parent_ordinal<ordinal)),
 body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 12000),
 source_lang TEXT NOT NULL,
 source_lang_mode TEXT NOT NULL,
 reply_status TEXT NOT NULL,
 PRIMARY KEY(site,source_id,ordinal),
 FOREIGN KEY(site,source_id) REFERENCES collector_long_stages(site,source_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_long_replies_parent ON collector_long_replies(site,source_id,parent_ordinal);
