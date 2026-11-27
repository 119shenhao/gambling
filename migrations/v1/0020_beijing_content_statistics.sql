-- Beijing calendar-day content statistics; retain UTC traffic aggregates.
CREATE TABLE content_origin_beijing_day_totals (
 day_beijing TEXT NOT NULL,
 content_type TEXT NOT NULL CHECK(content_type IN ('topic','comment')),
 source TEXT NOT NULL CHECK(source IN ('imported','user','unknown')),
 n INTEGER NOT NULL DEFAULT 0 CHECK(n>=0),
 PRIMARY KEY(day_beijing,content_type,source)
);
INSERT INTO content_origin_beijing_day_totals(day_beijing,content_type,source,n)
 SELECT COALESCE(date(entered_at,'unixepoch','+8 hours'),''),content_type,source,count(*)
 FROM content_origins GROUP BY COALESCE(date(entered_at,'unixepoch','+8 hours'),''),content_type,source;
CREATE TRIGGER origin_beijing_add AFTER INSERT ON content_origins BEGIN
 INSERT INTO content_origin_beijing_day_totals(day_beijing,content_type,source,n)
 VALUES(COALESCE(date(NEW.entered_at,'unixepoch','+8 hours'),''),NEW.content_type,NEW.source,1)
 ON CONFLICT(day_beijing,content_type,source) DO UPDATE SET n=n+1;
END;
CREATE TRIGGER origin_beijing_remove AFTER DELETE ON content_origins BEGIN
 UPDATE content_origin_beijing_day_totals SET n=n-1
 WHERE day_beijing=COALESCE(date(OLD.entered_at,'unixepoch','+8 hours'),'')
 AND content_type=OLD.content_type AND source=OLD.source;
END;
CREATE TRIGGER origin_beijing_change AFTER UPDATE OF content_type,content_id,source,entered_at ON content_origins
WHEN OLD.content_type IS NOT NEW.content_type OR OLD.content_id IS NOT NEW.content_id
 OR OLD.source IS NOT NEW.source OR OLD.entered_at IS NOT NEW.entered_at
BEGIN
 UPDATE content_origin_beijing_day_totals SET n=n-1
 WHERE day_beijing=COALESCE(date(OLD.entered_at,'unixepoch','+8 hours'),'')
 AND content_type=OLD.content_type AND source=OLD.source;
 INSERT INTO content_origin_beijing_day_totals(day_beijing,content_type,source,n)
 VALUES(COALESCE(date(NEW.entered_at,'unixepoch','+8 hours'),''),NEW.content_type,NEW.source,1)
 ON CONFLICT(day_beijing,content_type,source) DO UPDATE SET n=n+1;
END;
