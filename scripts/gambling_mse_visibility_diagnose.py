"""Read-only live diagnosis: compare MSE reply moderation and public DEV readback.

No imported text, email address, user name or other personal data is logged.
No writes to Cloudflare, source forum, GitHub issues or production are made.
"""
import json
import re
from collections import Counter
from urllib.parse import urlencode

from gambling_mse import parse_topic_pages, source_id
from gambling_mse_live_probe import fetch
from gambling_collect import api, lookup_published_topic_id

URL = "https://forums.moneysavingexpert.com/discussion/6200242/gambling-recovery-and-covid-job-loss"

def moderation(body):
    links = len(re.findall(r"https?://", body))
    if links > 8 or re.search(r"(?:buy now|guaranteed cure|miracle cure).{0,80}(?:https?:|whatsapp|telegram)",body,re.I):
        return "blocked",links
    if links > 2 or re.search(r"(?:promo code|discount code|contact.{0,12}whatsapp)",body,re.I):
        return "pending_review",links
    return "published",links

def main():
    ident=source_id(URL)
    draft,meta=parse_topic_pages(ident,URL,fetch(URL),fetch)
    risk_counts=Counter()
    risk_indices=[]
    media_counts=Counter()
    for i,comment in enumerate(draft["comments"],1):
        body=comment["body"]
        risk,links=moderation(body)
        risk_counts[risk]+=1
        if risk!="published":
            risk_indices.append({"reply_position":i,"risk":risk,"url_count":links,
                                 "image_links":body.count("[Image:")})
        media_counts["image_references"]+=body.count("[Image:")
    result={"event":"mse_visibility_diagnosis","site":"moneysavingexpert",
            "source_id":ident,"source_total":meta["source_total"],
            "moderation_predicted":dict(risk_counts),"flagged":risk_indices,
            "media_counts":dict(media_counts),"writes":False}
    try:
        exclusions=api("/api/collect/exclusions?"+urlencode({"site":"moneysavingexpert","limit":200}))
        match=[r for r in exclusions.get("items",[]) if r.get("source_id")==ident]
        result["source_receipt"]=[{"status":r.get("status")} for r in match]
    except Exception as exc:
        result["receipt_error"]=type(exc).__name__
    try:
        topic_id=lookup_published_topic_id(draft)
        result["topic_found"]=bool(topic_id)
        if topic_id:
            result["topic_id"]=topic_id
            rows=[];cursor=None;seen=set()
            for p in range(20):
                path="/api/topics/"+topic_id+("?before="+str(cursor) if cursor else "")
                page=api(path)
                rows.extend(page.get("comments",[]))
                cursor=page.get("next")
                if not cursor: break
                if cursor in seen:
                    result["cursor_error"]=True
                    break
                seen.add(cursor)
            result["public_comments"]=len(rows)
            result["public_statuses"]=dict(Counter(c.get("status") for c in rows))
            result["expected_minus_public"]=meta["captured"]-len(rows)
            result["public_page_count"]=p+1
    except Exception as exc:
        result["public_readback_error"]=type(exc).__name__+":"+str(exc)[:80]
    print(json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
