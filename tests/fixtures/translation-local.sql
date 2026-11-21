-- Only for wrangler LOCAL sqlite migrations; never run against Cloudflare remote D1.
INSERT OR IGNORE INTO users(id,nickname,preferred_locale) VALUES('local-translation-user','Local Test User','en');
INSERT OR IGNORE INTO topics(id,author_id,title,body,source_lang,source_lang_mode,status)
 VALUES('local-trans-topic','local-translation-user','A new beginning','I am asking for support and taking small steps.','en','manual','published');
INSERT OR IGNORE INTO comments(id,topic_id,author_id,body,source_lang,source_lang_mode,status)
 VALUES('local-trans-comment','local-trans-topic','local-translation-user','You can take things one day at a time.','en','manual','published');
INSERT OR REPLACE INTO topic_translations
 (scope,topic_id,locale,source_version,title_text,body_text,provider,source_language,product_id,engine_type)
 VALUES('full','local-trans-topic','zh-CN',1,'新的开始','我正在寻求支持，一步一步向前。','azure','en','azure_ai_translator_text','nmt');
INSERT OR REPLACE INTO topic_translations
 (scope,topic_id,locale,source_version,title_text,body_text,provider,source_language,product_id,engine_type)
 VALUES('summary','local-trans-topic','zh-CN',1,'新的开始','我正在寻求支持，一步一步向前。','azure','en','azure_ai_translator_text','nmt-summary-sentence-v2');
INSERT OR REPLACE INTO comment_translations
 (scope,comment_id,locale,source_version,body_text,provider,source_language,product_id,engine_type)
 VALUES('full','local-trans-comment','zh-CN',1,'你可以一天一天慢慢来。','azure','en','azure_ai_translator_text','nmt');
