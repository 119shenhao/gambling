-- Restore UTC-only statistics. Keep the obsolete derived table inert for safe rolling deployment.
-- Original UTC triggers, content, timestamps and all provenance are unchanged.
DROP TRIGGER IF EXISTS origin_beijing_add;
DROP TRIGGER IF EXISTS origin_beijing_remove;
DROP TRIGGER IF EXISTS origin_beijing_change;
