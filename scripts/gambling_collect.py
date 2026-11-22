"""Gambling Community independent, consent-gated external forum collector.

Every HTTP write is preview-only. Site IDs and parser code are unrelated to the
spine project. Without affirmative source rights and live parser verification,
inspect can discover candidates, but collect will not copy forum content.
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gambling_forums import discover, parse_topic, source_id

PREVIEW = "https://dev-gambling-community.119shenhao.workers.dev"
SITE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")
SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_BYTES = 150_000


def emit(event, **fields):
    print(json.dumps({"event": event, **fields}, ensure_ascii=False), flush=True)


def http(url, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    if data is not None and len(data) > MAX_BYTES:
        raise ValueError("payload_too_large")
    headers = {"User-Agent": "GamblingCommunityCollector/2.0 (public pages)",
               "Accept": "application/json,text/html",
               **({"Content-Type": "application/json"} if data is not None else {})}
    req = Request(url, data=data, headers=headers)
    try:
        with urlopen(req, timeout=18) as res:
            body = res.read(4_000_001)
            if len(body) > 4_000_000:
                raise ValueError("source_response_too_large")
            return body
    except HTTPError as e:
        raise ValueError("http_" + str(e.code)) from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("network_error_or_timeout") from None


def api(path, payload=None):
    return json.loads(http(PREVIEW + path, payload))


def excluded_ids(site):
    found = {}
    cursor = None
    visited = set()
    while True:
        params = {"site": site, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        page = api("/api/collect/exclusions?" + urlencode(params))
        if page.get("site") != site:
            raise ValueError("exclusions_site_mismatch")
        for row in page.get("items", []):
            if row.get("status") in ("completed", "claimed"):
                found[row["source_id"]] = row["status"]
        cursor = page.get("next_cursor")
        if cursor is None:
            return found
        if not isinstance(cursor, str) or not cursor or cursor in visited:
            raise ValueError("invalid_exclusions_cursor")
        visited.add(cursor)


def flatten(comments, depth=1):
    if not isinstance(comments, list) or depth > 8:
        raise ValueError("reply_depth_exceeded")
    out = []
    for c in comments:
        if not isinstance(c, dict) or set(c) - {"body", "source_lang", "replies"}:
            raise ValueError("invalid_reply")
        if not isinstance(c.get("body"), str) or not 1 <= len(c["body"].strip()) <= 12000:
            raise ValueError("invalid_reply_body")
        out.append(c)
        if c.get("replies"):
            out.extend(flatten(c["replies"], depth + 1))
    return out


def validate(draft):
    if not isinstance(draft, dict) or set(draft) - {"title", "body", "source_lang", "comments"}:
        raise ValueError("invalid_topic_fields")
    if not all(isinstance(draft.get(k), str) and draft[k].strip()
               for k in ("title", "body", "source_lang")):
        raise ValueError("missing_topic_text")
    if len(draft["title"]) > 200 or len(draft["body"]) > 30_000:
        raise ValueError("topic_length_exceeded")
    replies = flatten(draft.get("comments", []))
    if not 1 <= len(replies) <= 49:
        raise ValueError("reply_count_invalid")
    serialized = json.dumps({"site": "placeholder", "source_id": "placeholder",
                             "lease_token": "x" * 90, "topic": draft},
                            ensure_ascii=False).encode()
    if len(serialized) > MAX_BYTES:
        raise ValueError("payload_too_large")
    return len(replies)


def readback(topic_id, draft, n):
    if not re.fullmatch(r"[0-9a-f-]{36}", topic_id or ""):
        raise ValueError("invalid_topic_id")
    result = api("/api/topics/" + topic_id)
    saved = result.get("topic", {})
    if any(saved.get(field) != draft[field] for field in ("title", "body", "source_lang")):
        raise ValueError("readback_topic_mismatch")
    records = result.get("comments", [])
    if result.get("next") is not None or len(records) != n:
        raise ValueError("readback_count_or_pagination_mismatch")
    expected = Counter((item["body"], item.get("source_lang", draft["source_lang"]))
                       for item in flatten(draft["comments"]))
    received = Counter((row.get("body"), row.get("source_lang")) for row in records)
    if expected != received:
        raise ValueError("readback_reply_mismatch")
    # A flat source must remain flat; nested source reply IDs are not inferred
    # merely from quoted text or @mentions.
    if any(row.get("parent_comment_id") is not None for row in records):
        if not any(c.get("replies") for c in draft["comments"]):
            raise ValueError("readback_parent_mismatch")
    return True


def available(source):
    return (source.get("approved") is True and
            source.get("parser_verified") is True and
            source.get("reuse_allowed") is True and
            bool(source.get("permission_evidence")))


def discover_source(source, excluded, cap=60):
    found = {}
    for listing in source.get("listings", [])[:5]:
        try:
            candidates = discover(source["id"], listing, http(listing), excluded, cap)
            found.update({k: v for k, v in candidates.items() if k not in found})
            emit("listing_checked", site=source["id"], candidates=len(candidates))
        except ValueError as error:
            emit("listing_unavailable", site=source["id"], reason=str(error))
        if len(found) >= cap:
            break
        time.sleep(1)
    return dict(list(found.items())[:cap])


def load_request(file):
    obj = json.loads(file.read_text(encoding="utf-8"))
    if (not isinstance(obj, dict) or set(obj) !=
            {"request_id", "mode", "sites", "candidates", "limit"}):
        raise ValueError("invalid_request_fields")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", obj["request_id"]):
        raise ValueError("invalid_request_id")
    if obj["mode"] not in ("inspect", "collect") or type(obj["limit"]) is not int or not 1 <= obj["limit"] <= 10:
        raise ValueError("invalid_request_mode_or_limit")
    if not isinstance(obj["sites"], list) or not obj["sites"] or not isinstance(obj["candidates"], dict):
        raise ValueError("invalid_sites_or_candidates")
    return obj


def load_registry():
    sources = json.loads(Path("scripts/gambling_sources.json").read_text(encoding="utf-8"))["sources"]
    known = {}
    for s in sources:
        if (not isinstance(s, dict) or not SITE_RE.fullmatch(s.get("id", ""))
                or s["id"] in known or s.get("adapter") != "gambling_forums"):
            raise ValueError("invalid_source_registry")
        known[s["id"]] = s
    return known


def collect_one(site, source, identifier, url, export_dir):
    lease = api("/api/collect/claim", {
        "site": site, "source_ids": [identifier],
        "collector_id": "gambling-independent-collector",
    })["results"][0]
    if lease["result"] != "granted":
        emit("claim_skipped", site=site, source_id=identifier, reason=lease["result"])
        return 0, 0, 0
    token = lease["lease_token"]
    payload = {"site": site, "source_id": identifier, "lease_token": token}
    completed = False
    submitted = False
    try:
        if export_dir:
            file = export_dir / site / (identifier + ".json")
            if not file.is_file() or file.stat().st_size > MAX_BYTES:
                raise ValueError("export_missing_or_too_large")
            draft = json.loads(file.read_text(encoding="utf-8"))
        else:
            draft = parse_topic(site, identifier, url, http(url))
        n = validate(draft)
        submitted = True
        receipt = api("/api/collect/complete", {**payload, "topic": draft})
        completed = receipt.get("status") == "completed"
        if not completed:
            raise ValueError("complete_not_confirmed")
        if receipt.get("duplicate"):
            emit("duplicate", site=site, source_id=identifier, topic_id=receipt.get("topic_id"))
            return 0, 0, 1
        if receipt.get("imported") != {"topics": 1, "comments": n}:
            raise ValueError("imported_count_mismatch")
        readback(receipt["topic_id"], draft, n)
        emit("imported", site=site, source_id=identifier, topic_id=receipt["topic_id"],
             replies=n, source_url=url)
        return 1, n, 0
    except ValueError as e:
        # A timeout from complete may have committed. Check exclusions rather
        # than issuing a second non-idempotent completion with unknown outcome.
        if submitted:
            try:
                completed = excluded_ids(site).get(identifier) == "completed"
            except ValueError:
                pass
        emit("candidate_failed", site=site, source_id=identifier, reason=str(e),
             completion_possible=bool(submitted))
        raise
    finally:
        if not completed:
            try:
                if not submitted:
                    api("/api/collect/release", payload)
                else:
                    emit("release_deferred", site=site, source_id=identifier,
                         reason="completion_outcome_uncertain")
            except ValueError:
                emit("release_failed", site=site, source_id=identifier)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--export-dir", type=Path)
    args = parser.parse_args()
    req = load_request(args.request)
    sources = load_registry()
    sites = list(sources) if req["sites"] == ["all"] else req["sites"]
    if len(set(sites)) != len(sites) or any(s not in sources for s in sites):
        raise ValueError("unsupported_site")
    if set(req["candidates"]) - set(sites):
        raise ValueError("candidate_site_not_selected")
    health = api("/api/health")
    if (health.get("environment") != "preview" or
            health.get("importEnabled") is not True or
            health.get("collectEnabled") is not True):
        raise ValueError("preview_not_ready")
    emit("readiness", preview=True, configured_sources=len(sources),
         importable_sources=sum(available(v) for v in sources.values()))
    total_topics = total_comments = total_duplicates = errors = 0
    for site in sites:
        source = sources[site]
        try:
            excluded = excluded_ids(site)
            explicit = req["candidates"].get(site, [])
            if not isinstance(explicit, list):
                raise ValueError("invalid_candidate_list")
            if explicit:
                candidates = {}
                for value in explicit:
                    if not isinstance(value, str):
                        raise ValueError("invalid_candidate")
                    if value.startswith("https://"):
                        identifier = source_id(site, value)
                        candidates[identifier] = value
                    elif SOURCE_RE.fullmatch(value) and args.export_dir:
                        candidates[value] = ""
                    else:
                        raise ValueError("candidate_requires_url_or_export")
            else:
                candidates = discover_source(source, excluded)
            eligible = {identifier: url for identifier, url in candidates.items() if identifier not in excluded}
            emit("plan", site=site, candidates=len(candidates), excluded=len(candidates)-len(eligible),
                 eligible=len(eligible), import_allowed=available(source))
            if req["mode"] == "inspect":
                continue
            if not available(source):
                emit("source_not_enabled", site=site, reason="reuse_or_parser_verification_required")
                continue
            imported = comments = duplicates = 0
            for identifier, url in eligible.items():
                if imported >= req["limit"]:
                    break
                try:
                    n_topics, n_comments, n_dupes = collect_one(site, source, identifier, url, args.export_dir)
                    imported += n_topics
                    comments += n_comments
                    duplicates += n_dupes
                except ValueError:
                    errors += 1
            total_topics += imported
            total_comments += comments
            total_duplicates += duplicates
            emit("site_summary", site=site, new_topics=imported,
                 new_comments=comments, duplicates=duplicates, target=req["limit"])
        except (ValueError, KeyError, TypeError) as error:
            errors += 1
            emit("site_error", site=site, reason=str(error))
    emit("run_summary", new_topics=total_topics, new_comments=total_comments,
         duplicates=total_duplicates, errors=errors,
         ready_for_unattended_collect=bool(sum(available(s) for s in sources.values())))
    if errors:
        return 1
    if req["mode"] == "collect" and not any(available(sources[s]) for s in sites):
        return 2  # A safe, visible failure, NEVER a green zero-post success.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, TypeError, KeyError, OSError) as error:
        emit("collector_error", reason=str(error))
        raise SystemExit(1) from None
