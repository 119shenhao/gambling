-- DEV-only durable verification backlog for published PROD threads.
-- Never copy this coordination table into PROD D1.
-- A source sync receipt is written only after all PROD D1 rows are confirmed.
-- Preserve an independent CDN acceptance state so a later retry cannot
-- report success just because that source topic is already synchronized.
CREATE TABLE IF NOT EXISTS topic_cdn_sync_acceptance (
 source_topic_id TEXT PRIMARY KEY REFERENCES topic_sync_receipts(source_topic_id) ON DELETE CASCADE,
 production_topic_id TEXT NOT NULL,
 verified_version INTEGER,
 verified_at INTEGER,
 created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_topic_cdn_sync_pending
 ON topic_cdn_sync_acceptance(verified_at,created_at,source_topic_id);
CREATE TRIGGER IF NOT EXISTS topic_cdn_sync_receipt_insert
 AFTER INSERT ON topic_sync_receipts
BEGIN
 INSERT OR IGNORE INTO topic_cdn_sync_acceptance(source_topic_id,production_topic_id)
 VALUES(NEW.source_topic_id,NEW.production_topic_id);
END;
-- One-time backfill is idempotent across subsequent dev Preview builds.
INSERT OR IGNORE INTO topic_cdn_sync_acceptance(source_topic_id,production_topic_id)
 SELECT source_topic_id,production_topic_id FROM topic_sync_receipts;
