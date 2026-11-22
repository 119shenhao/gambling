"""Run strict V2EX multi-page parser against actual public pages (read-only).

No content, authors, comments, or PII are output or persisted.
This is not permission to republish, nor a successful DEV import.
"""
import json
import sys
from gambling_chinese_source_probe import fetch
from gambling_v2ex import source_id, parse_topic_pages

BASE="https://www.v2ex.com/t/1121755"

def load(url):
    code,body=fetch("v2ex",url)
    if code!=200:
        raise ValueError("unexpected_http_status")
    return body

def main():
    record={"event":"v2ex_strict_live_parse","site":"v2ex",
            "database_writes":False,"import_enabled":False}
    try:
        first=load(BASE+"?p=1")
        draft,meta=parse_topic_pages(source_id(BASE),BASE,first,load)
        record.update({"status":"parser_ok","source_lang":draft["source_lang"],
                       "captured":len(draft["comments"]), **meta})
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        record.update({"status":"parser_rejected","reason":str(exc)[:150]})
    print(json.dumps(record,sort_keys=True,ensure_ascii=False),flush=True)
    # Action success must prove actual multi-page parser success, not just
    # successful execution of the diagnostic script.
    if record.get("status") != "parser_ok":
        sys.exit(1)

if __name__=="__main__":
    main()
