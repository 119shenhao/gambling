"""Gambling community: authorized-export collector coordinator.
No sites are approved by default. Never copy spine sources or scrape arbitrary URLs.
A scheduled invocation without approved/implemented sources is a safe no-op.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

PREVIEW = "https://dev-gambling-community.119shenhao.workers.dev"
SITE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")
SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def api(path, data=None):
    payload = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    if payload and len(payload) > 150000:
        raise ValueError("payload_too_large")
    req = Request(PREVIEW + path, data=payload, headers={
        "Accept": "application/json",
        "User-Agent": "GamblingCommunityAuthorizedCollector/1.0",
        **({"Content-Type": "application/json"} if payload is not None else {}),
    })
    try:
        with urlopen(req, timeout=20) as res:
            return json.load(res)
    except (HTTPError, URLError) as error:
        raise ValueError("preview_http_unavailable:" + str(getattr(error, "code", "network"))) from None


def exclusions(site):
    seen = {}
    cursor = None
    visited = set()
    while True:
        options = {"site": site, "limit": 200}
        if cursor:
            options["cursor"] = cursor
        page = api("/api/collect/exclusions?" + urlencode(options))
        if page.get("site") != site:
            raise ValueError("site_mismatch")
        seen.update((row["source_id"], row["status"]) for row in page["items"])
        cursor = page.get("next_cursor")
        if cursor is None:
            return seen
        if not isinstance(cursor, str) or cursor in visited:
            raise ValueError("invalid_cursor")
        visited.add(cursor)


def flatten_comments(comments, depth=1):
    if depth > 8:
        raise ValueError("reply_depth_exceeded")
    out = []
    for c in comments:
        if set(c) - {"body", "source_lang", "replies"} or not isinstance(c.get("body"), str):
            raise ValueError("invalid_comment")
        out.append(c)
        out.extend(flatten_comments(c.get("replies", []), depth + 1))
    return out


def validated_draft(data):
    if not isinstance(data, dict) or set(data) - {"title", "body", "source_lang", "comments", "terms", "symptom_duration_days"}:
        raise ValueError("invalid_export")
    if not (isinstance(data.get("title"), str) and 1 <= len(data["title"].strip()) <= 200 and
            isinstance(data.get("body"), str) and 1 <= len(data["body"].strip()) <= 30000):
        raise ValueError("invalid_content")
    comments = flatten_comments(data.get("comments", []))
    if len(comments) > 49:
        raise ValueError("reply_limit_exceeded")
    return data, len(comments)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--export-dir", type=Path)
    args = parser.parse_args()
    req = json.loads(args.request.read_text())
    if set(req) != {"request_id", "mode", "sites", "candidates", "limit"} or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", req["request_id"]):
        raise ValueError("invalid_request")
    if req["mode"] not in ("inspect", "collect") or not 1 <= req["limit"] <= 10:
        raise ValueError("invalid_mode_or_limit")
    registry = json.loads(Path("scripts/gambling_sources.json").read_text())["sources"]
    registered = {s["id"]: s for s in registry if s.get("approved") is True and s.get("parser_verified") is True}
    if any(not SITE_RE.fullmatch(s) for s in registered):
        raise ValueError("invalid_site_registry")
    sites = list(registered) if req["sites"] == ["all"] else req["sites"]
    if any(s not in registered for s in sites) or any(s not in sites for s in req["candidates"]):
        raise ValueError("unapproved_source")
    health = api("/api/health")
    if health.get("environment") != "preview" or not health.get("importEnabled") or not health.get("collectEnabled"):
        raise ValueError("preview_collection_disabled")
    print(json.dumps({"event": "readiness", "preview": True, "registered_sources": len(registered)}), flush=True)
    if not sites:
        print(json.dumps({"event": "no_approved_sources", "new_topics": 0, "reason": "no gambling-specific approved verified source parsers"}), flush=True)
        return 0
    total = 0
    for site in sites:
        excluded = exclusions(site)
        candidates = req["candidates"].get(site, [])
        if not isinstance(candidates, list):
            raise ValueError("invalid_candidates")
        imported = duplicates = 0
        for source_id in candidates:
            if imported >= req["limit"]:
                break
            if not isinstance(source_id, str) or not SOURCE_RE.fullmatch(source_id):
                raise ValueError("invalid_source_id")
            if source_id in excluded:
                continue
            # No outbound scraping from runner: privately supplied, authorized exports only.
            if not args.export_dir:
                print(json.dumps({"event": "source_requires_authorized_export", "site": site}), flush=True)
                break
            file = args.export_dir / site / (source_id + ".json")
            if not file.is_file() or file.stat().st_size > 150000:
                raise ValueError("missing_or_oversized_authorized_export")
            draft, count = validated_draft(json.loads(file.read_text()))
            claim = api("/api/collect/claim", {"site": site, "source_ids": [source_id], "collector_id": "gambling-authorized-export"})
            result, = claim["results"]
            if result["result"] != "granted":
                continue
            token = result["lease_token"]
            committed = False
            try:
                receipt = api("/api/collect/complete", {"site": site, "source_id": source_id, "lease_token": token, "topic": draft})
                committed = receipt.get("status") == "completed"
                if not committed:
                    raise ValueError("completion_unconfirmed")
                if receipt.get("duplicate"):
                    duplicates += 1
                    continue
                record = api("/api/topics/" + receipt["topic_id"])
                if (record["topic"]["title"] != draft["title"] or
                        record["topic"]["body"] != draft["body"] or
                        len(record["comments"]) != count):
                    raise ValueError("readback_mismatch")
                imported += 1
                print(json.dumps({"event": "imported", "site": site, "source_id": source_id,
                                  "topic_id": receipt["topic_id"], "replies": count}), flush=True)
            finally:
                if not committed:
                    api("/api/collect/release", {"site": site, "source_id": source_id, "lease_token": token})
        total += imported
        print(json.dumps({"event": "site_summary", "site": site, "new_topics": imported,
                          "duplicates": duplicates, "target": req["limit"]}), flush=True)
    print(json.dumps({"event": "run_summary", "new_topics": total}), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({"event": "collector_error", "reason": str(error)}), flush=True)
        sys.exit(1)
