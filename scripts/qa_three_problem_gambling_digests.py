#!/usr/bin/env python3
"""One-time integration: source-linked EDITORIAL DIGESTS, not reproduced Reddit content.
Only user-authorized QA summaries; no scraping; validates the real Worker, D1, nesting.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

PREVIEW = "https://dev-gambling-community.119shenhao.workers.dev"
def call(path, data=None):
    payload = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    request = Request(PREVIEW + path, data=payload, headers={
        "Accept":"application/json", "User-Agent":"GamblingQA-Digest/1.0",
        **({"Content-Type":"application/json"} if payload is not None else {})})
    try:
        with urlopen(request, timeout=22) as res:
            return res.status, json.load(res)
    except HTTPError as exc:
        raise RuntimeError("API failure "+path+": HTTP "+str(exc.code)) from None

def flatten(items, parent=None):
    out = []
    for item in items:
        out.append((item["body"],parent))
        out += flatten(item.get("replies",[]),item["body"])
    return out

def run():
    fixture = json.loads(Path("tests/fixtures/problem-gambling-digests-20261122.json").read_text())
    site = fixture["site"]
    status,health=call("/api/health")
    assert status==200 and health["environment"]=="preview" and health["databaseReady"]
    assert health.get("importEnabled") and health.get("collectEnabled")
    status,excluded=call("/api/collect/exclusions?site="+site)
    assert status==200 and excluded["site"]==site
    covered={x["source_id"]:x["status"] for x in excluded["items"]}
    total_new=0
    results=[]
    for item in fixture["cases"]:
        sid=item["source_id"]
        assert re.fullmatch("[A-Za-z0-9_-]{1,128}", sid)
        topic=item["topic"]
        assert topic["title"].startswith("[QA DIGEST]") and "TECHNICAL QA DIGEST" in topic["body"]
        assert item["url"] in topic["body"]
        assert 1<=len(flatten(topic["comments"]))<=49
        if sid in covered:
            print(json.dumps({"event":"existing_source","source_id":sid,"status":covered[sid]}),flush=True)
            continue
        status,resp=call("/api/collect/claim",{
            "site":site,"source_ids":[sid],"collector_id":"gambling-source-digest-qa"})
        lease=resp["results"][0]
        assert status==200 and lease["result"]=="granted" and resp["lease_seconds"]==21600
        token=lease["lease_token"]
        completed=False
        try:
            status,result=call("/api/collect/complete",{
                "site":site,"source_id":sid,"lease_token":token,"topic":topic})
            completed=result["status"]=="completed"
            assert completed and status in (200,201)
            assert not result.get("duplicate"),"Unexpected duplicate: source content should be unique"
            topic_id=result["topic_id"]
            status,page=call("/api/topics/"+topic_id)
            assert status==200 and page["topic"]["title"]==topic["title"] and page["topic"]["body"]==topic["body"]
            expected=flatten(topic["comments"])
            actual=page["comments"]
            assert len(expected)==len(actual),f"reply count mismatch for {sid}: {len(expected)} vs {len(actual)}"
            ids={row["body"]:row["id"] for row in actual}
            assert len(ids)==len(actual)
            for text,parent in expected:
                row=next((x for x in actual if x["body"]==text),None)
                assert row and row["parent_comment_id"]==(ids[parent] if parent else None),"hierarchy failure"
            status,after=call("/api/collect/exclusions?site="+site)
            assert status==200 and any(x["source_id"]==sid and x["status"]=="completed" for x in after["items"])
            total_new+=1
            results.append({"source_id":sid,"topic_id":topic_id,"replies":len(expected),"url":PREVIEW+"/topic/"+topic_id})
            print(json.dumps({"event":"digest_verified","source_id":sid,"topic_id":topic_id,"replies":len(expected),"url":PREVIEW+"/topic/"+topic_id}),flush=True)
        finally:
            if not completed:
                call("/api/collect/release",{"site":site,"source_id":sid,"lease_token":token})
        time.sleep(1)
    print(json.dumps({"event":"summary","new_topics":total_new,"verified":results},ensure_ascii=False),flush=True)
    assert total_new==3,f"Expected three fresh QA digests; got {total_new}"

if __name__=="__main__":
    try: run()
    except Exception as error:
        print(json.dumps({"event":"qa_failure","detail":str(error)[:220]}),flush=True)
        sys.exit(1)
