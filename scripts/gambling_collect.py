"""Gambling Community independent, consent-gated external forum collector.

Every HTTP write is preview-only. Site IDs and parser code are unrelated to the
spine project. Without affirmative source rights and live parser verification,
inspect can discover candidates, but collect will not copy forum content.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from itertools import chain, zip_longest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from gambling_forums import discover, parse_topic, parse_topic_pages, source_id
from gambling_story_sources import ARTICLE_SOURCES
from gambling_link_cleanup import clean_collected_draft

PREVIEW = "https://dev-gambling-community.119shenhao.workers.dev"
SITE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")
SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_BYTES = 150_000
PAGINATED_SITES = ("gamcare", "moneysavingexpert", "v2ex", "psychforums")


class RejectedCandidate(ValueError):
    """Source post is ineligible (missing replies, private data, etc.)."""
    pass


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


def fetch_source(url):
    """Retry one transient read of a public PsychForums page."""
    try:
        return http(url)
    except ValueError as error:
        if (urlsplit(url).hostname != "www.psychforums.com"
                or str(error) != "network_error_or_timeout"):
            raise
        time.sleep(2)
        return http(url)


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


def validate(draft, *, allow_no_replies=False):
    if not isinstance(draft, dict) or set(draft) - {"title", "body", "source_lang", "comments"}:
        raise ValueError("invalid_topic_fields")
    if not all(isinstance(draft.get(k), str) and draft[k].strip()
               for k in ("title", "body", "source_lang")):
        raise ValueError("missing_topic_text")
    if len(draft["title"]) > 200 or len(draft["body"]) > 30_000:
        raise ValueError("topic_length_exceeded")
    comments = draft.get("comments")
    if not isinstance(comments, list):
        raise ValueError("invalid_comment_list")
    replies = flatten(comments)
    if len(replies) > 500 or (not replies and not allow_no_replies):
        raise ValueError("reply_count_invalid")
    serialized = json.dumps({"site": "placeholder", "source_id": "placeholder",
                             "lease_token": "x" * 90, "topic": draft},
                            ensure_ascii=False).encode()
    # 49-or-fewer comments may use the single atomic endpoint. Long topics
    # are sent as independent bounded pages, never as one giant request.
    return len(replies)


def readback(topic_id, draft, n, site=None, identifier=None):
    """Read all DEV detail pages, not just the first 20 comments."""
    if not re.fullmatch(r"[0-9a-f-]{36}", topic_id or ""):
        raise ValueError("invalid_topic_id")
    rows = []
    cursor = None
    visited = set()
    for _ in range(32):
        path = "/api/topics/" + topic_id + (("?before=" + str(cursor)) if cursor is not None else "")
        result = api(path)
        saved = result.get("topic", {})
        if any(saved.get(field) != draft[field] for field in ("title", "body")):
            raise ValueError("readback_topic_mismatch")
        # The Worker independently detects original language; source_lang in
        # the imported payload is only a hint. Short replies may become 'und'.
        if not isinstance(saved.get("source_lang"), str) or not saved["source_lang"]:
            raise ValueError("readback_missing_topic_language")
        page = result.get("comments", [])
        if not isinstance(page, list):
            raise ValueError("readback_invalid_page")
        rows.extend(page)
        if len(rows) > 500:
            raise ValueError("readback_reply_overflow")
        nxt = result.get("next")
        if nxt is None:
            break
        if (type(nxt) is not int or nxt < 1 or nxt in visited or
                (cursor is not None and nxt <= cursor)):
            raise ValueError("readback_invalid_cursor")
        visited.add(nxt)
        cursor = nxt
    else:
        raise ValueError("readback_pagination_unfinished")
    if len(rows) > n or len({row.get("id") for row in rows}) != len(rows):
        raise ValueError("readback_count_mismatch")
    # The Worker independently detects language. Exact public-body matching
    # must always pass, even if some private moderation records are withheld.
    expected = Counter(item["body"] for item in flatten(draft["comments"]))
    received = Counter(row.get("body") for row in rows)
    if received - expected:
        raise ValueError("readback_reply_body_mismatch")
    if len(rows) == n:
        if expected != received:
            raise ValueError("readback_reply_body_mismatch")
    else:
        # Moderated replies belong in the DEV database but are deliberately
        # omitted from the public detail API. Count them as *stored* only after
        # a fresh preview-only, DB-backed verification of the completed source.
        # Do NOT silently accept missing/deleted/blocked/unaccounted replies.
        if not site or not identifier:
            raise ValueError("readback_count_mismatch")
        proof = api("/api/collect/verification?" + urlencode({
            "site": site, "source_id": identifier}))
        counts = proof.get("status_counts", {})
        if (proof.get("site") != site or proof.get("source_id") != identifier
                or proof.get("topic_id") != topic_id
                or proof.get("status") != "completed"
                or proof.get("duplicate") is not False
                or type(proof.get("total")) is not int or proof["total"] != n
                or not isinstance(counts, dict)
                or any(type(v) is not int or v < 0 for v in counts.values())
                or sum(counts.values()) != n
                or counts.get("published", 0) != len(rows)
                or counts.get("pending_review", 0) != n - len(rows)
                or any(v for k, v in counts.items()
                       if k not in ("published", "pending_review"))):
            raise ValueError("readback_moderation_count_unverified")
        emit("readback_pending_review_verified", site=site,
             source_id=identifier, topic_id=topic_id,
             stored=n, public=len(rows),
             pending_review=counts["pending_review"])
    if any(not isinstance(row.get("source_lang"), str) or
           not row["source_lang"] for row in rows):
        raise ValueError("readback_missing_reply_language")
    detected = Counter(row["source_lang"] for row in rows)
    if detected != Counter({draft["source_lang"]: n}):
        emit("readback_language_detection", topic_id=topic_id,
             source_hint=draft["source_lang"], detected_languages=dict(detected))
    # Current GamCare/Gambling Therapy HTML adapters yield flat replies.
    # Never infer nesting from quotes or @mentions.
    if any(row.get("parent_comment_id") is not None for row in rows):
        if not any(c.get("replies") for c in draft["comments"]):
            raise ValueError("readback_parent_mismatch")
    return True


def lookup_published_topic_id(draft):
    """Find an existing DEV-published topic using exact title and full body."""
    for offset in range(0, 100, 20):
        feed = api("/api/topics?sort=latest&offset=" + str(offset))
        topics = feed.get("topics", [])
        if not isinstance(topics, list):
            raise ValueError("audit_invalid_feed")
        for topic in topics:
            if topic.get("title") != draft["title"]:
                continue
            topic_id = topic.get("id")
            if not isinstance(topic_id, str) or not re.fullmatch(r"[0-9a-f-]{36}", topic_id):
                continue
            detail = api("/api/topics/" + topic_id)
            if detail.get("topic", {}).get("body") == draft["body"]:
                return topic_id
        if feed.get("next") is None:
            break
    return None


def audit_completed(site, identifier, url, draft, n):
    """Read-only audit of old completed imports, never claim or re-import."""
    # Historical DEV records are intentionally not rewritten. Verify the exact
    # legacy or current representation, without claiming or importing again.
    topic_id = lookup_published_topic_id(draft)
    if not topic_id:
        clean_collected_draft(draft)
        topic_id = lookup_published_topic_id(draft)
    if not topic_id:
        raise ValueError("completed_topic_not_visible_in_dev_feed")
    try:
        readback(topic_id, draft, n, site, identifier)
    except ValueError as error:
        if str(error) not in ("readback_topic_mismatch", "readback_reply_mismatch"):
            raise
        clean_collected_draft(draft)
        readback(topic_id, draft, n, site, identifier)
    emit("completed_audit_ok", site=site, source_id=identifier,
         topic_id=topic_id, replies=n, source_url=url)

def available(source):
    return (source.get("approved") is True and
            source.get("parser_verified") is True and
            source.get("reuse_allowed") is True and
            bool(source.get("permission_evidence")))


def discover_source(source, excluded, cap=60):
    found = {}
    # Curated public discussion URLs are a *discovery fallback*, never evidence
    # that a thread is parseable or already collected. Each goes through exactly
    # the same source-ID exclusions, full parser, privacy and readback checks.
    # MSE cannot use onsite search; V2EX has gambling-related debt titles
    # that omit the literal word 'gambling' even when the original body
    # documents an explicit recovery attempt. Only vetted URL candidates
    # enter here, and the strict full-body filter still applies later.
    if source["id"] in ("moneysavingexpert", "v2ex") or source["id"] in ARTICLE_SOURCES:
        for url in source.get("seed_topics", [])[:80]:
            try:
                identifier = source_id(source["id"], url)
                if identifier not in excluded and identifier not in found:
                    found[identifier] = url
            except ValueError:
                emit("invalid_seed_skipped", site=source["id"])
        emit("source_seed_discovery", site=source["id"], candidates=len(found))
    interleave_listings = source["id"] == "gamcare"
    listing_batches = []
    listing_available = False
    listing_error = None
    for listing in source.get("listings", [])[:5]:
        try:
            candidates = discover(source["id"], listing, fetch_source(listing), excluded, cap)
            if interleave_listings:
                listing_batches.append(candidates.items())
            else:
                found.update({k: v for k, v in candidates.items() if k not in found})
            listing_available = True
            emit("listing_checked", site=source["id"], candidates=len(candidates))
        except ValueError as error:
            listing_error = error
            emit("listing_unavailable", site=source["id"], reason=str(error))
        if len(found) >= cap:
            break
        time.sleep(1)
    if interleave_listings:
        for row in zip_longest(*listing_batches):
            for candidate in row:
                if candidate is not None:
                    identifier, url = candidate
                    found.setdefault(identifier, url)
                    if len(found) >= cap:
                        return found
    if not listing_available and not found and listing_error:
        raise listing_error
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


def staged_replies(draft):
    """Flatten original comment preorder, preserving absolute parent indices."""
    output = []
    def visit(items, parent=None, depth=1):
        if depth > 8:
            raise ValueError("reply_depth_exceeded")
        for node in items:
            index = len(output)
            output.append({"body": node["body"],
                           "source_lang": node.get("source_lang", draft["source_lang"]),
                           "parent_index": parent})
            visit(node.get("replies", []), index, depth + 1)
    visit(draft["comments"])
    return output


def complete_staged(site, identifier, token, draft, source_total, n):
    """Stage up to 500 comments in bounded requests, then publish atomically."""
    stage = {"site": site, "source_id": identifier, "lease_token": token}
    started = False
    try:
        response = api("/api/collect/long/start", {
            **stage, "title": draft["title"], "body": draft["body"],
            "source_lang": draft["source_lang"], "source_total": source_total,
            "target_count": n})
        if response.get("status") == "completed" and response.get("duplicate"):
            return response
        if response.get("status") != "staging":
            raise ValueError("long_start_not_staging")
        started = True
        replies = staged_replies(draft)
        if len(replies) != n or n != min(source_total, 500):
            raise ValueError("long_count_mismatch")
        received = response["received"]
        if type(received) is not int or not 0 <= received <= n:
            raise ValueError("long_bad_resume_offset")
        for offset in range(received, n, 10):
            batch = replies[offset:offset + 10]
            answer = api("/api/collect/long/append", {
                **stage, "offset": offset, "comments": batch})
            if answer.get("received") != offset + len(batch):
                raise ValueError("long_append_not_confirmed")
        response = api("/api/collect/long/finish", stage)
        if response.get("status") != "completed":
            raise ValueError("long_finish_not_confirmed")
        if response.get("stored_comments") != n:
            raise ValueError("long_finish_count_mismatch")
        if response.get("capped") is not (source_total > 500):
            raise ValueError("long_cap_mismatch")
        return response
    except ValueError:
        # A timed-out finish could have succeeded. Do not abort until
        # the collector source exclusion proves the outcome is not completed.
        if started:
            status = None
            try:
                status = excluded_ids(site).get(identifier)
            except ValueError:
                pass
            if status == "claimed":
                try:
                    api("/api/collect/long/abort", stage)
                except ValueError:
                    emit("long_abort_failed", site=site, source_id=identifier)
        raise


def collect_one(site, source, identifier, url, export_dir):
    # Validate the entire public source before claiming. Ineligible candidates
    # must not churn D1 claim/release rows or exhaust the claim quota.
    # The server still atomically reserves and deduplicates immediately before
    # any import; a competing collector cannot cause a duplicate write.
    payload = None
    completed = False
    submitted = False
    try:
        if export_dir:
            file = export_dir / site / (identifier + ".json")
            if not file.is_file() or file.stat().st_size > MAX_BYTES:
                raise ValueError("export_missing_or_too_large")
            draft = json.loads(file.read_text(encoding="utf-8"))
        else:
            source_html = fetch_source(url)
            try:
                if site in PAGINATED_SITES:
                    draft, metadata = parse_topic_pages(site, identifier, url, source_html, fetch_source)
                else:
                    draft = parse_topic(site, identifier, url, source_html)
                    metadata = {"source_total": len(flatten(draft.get("comments", []))),
                                "capped": False, "pages": 1}
            except ValueError as error:
                raise RejectedCandidate(str(error)) from None
        if export_dir:
            metadata = {"source_total": len(flatten(draft.get("comments", []))),
                        "capped": False, "pages": 1}
        try:
            clean_collected_draft(draft)
            n = validate(draft, allow_no_replies=site in ARTICLE_SOURCES)
        except ValueError as error:
            raise RejectedCandidate(str(error)) from None
        whole_bytes = len(json.dumps({"site": site, "source_id": identifier,
                        "lease_token": "x" * 128, "topic": draft},
                        ensure_ascii=False).encode())
        long_mode = n > 49 or whole_bytes > MAX_BYTES or metadata["pages"] > 1
        if long_mode and n == 0:
            raise RejectedCandidate("standalone_article_payload_too_large")
        lease = api("/api/collect/claim", {
            "site": site, "source_ids": [identifier],
            "collector_id": "gambling-independent-collector",
        })["results"][0]
        if lease["result"] != "granted":
            emit("claim_skipped", site=site, source_id=identifier, reason=lease["result"])
            return 0, 0, 0
        token = lease["lease_token"]
        payload = {"site": site, "source_id": identifier, "lease_token": token}
        submitted = True
        if long_mode:
            receipt = complete_staged(site, identifier, token, draft,
                                      metadata["source_total"], n)
        else:
            receipt = api("/api/collect/complete", {**payload, "topic": draft})
        completed = receipt.get("status") == "completed"
        if not completed:
            raise ValueError("complete_not_confirmed")
        if receipt.get("duplicate"):
            emit("duplicate", site=site, source_id=identifier, topic_id=receipt.get("topic_id"))
            return 0, 0, 1
        if receipt.get("imported") != {"topics": 1, "comments": n}:
            raise ValueError("imported_count_mismatch")
        if metadata.get("capped"):
            emit("source_reply_cap", site=site, source_id=identifier,
                 captured=n, source_total=metadata["source_total"], limit=500)
        readback(receipt["topic_id"], draft, n, site, identifier)
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
        emit("candidate_rejected" if isinstance(e, RejectedCandidate) else "candidate_failed",
             site=site, source_id=identifier, reason=str(e),
             completion_possible=bool(submitted))
        raise
    finally:
        if payload is not None and not completed:
            try:
                if not submitted:
                    api("/api/collect/release", payload)
                else:
                    emit("release_deferred", site=site, source_id=identifier,
                         reason="completion_outcome_uncertain")
            except ValueError:
                emit("release_failed", site=site, source_id=identifier)




def older_pages_for_request(request_id):
    # Keep nearby pages and rotate one additional older page per run.
    offset = int.from_bytes(hashlib.sha256(request_id.encode()).digest()[:4], "big")
    return (2, 3, 4 + offset % 12)


def older_board_candidates(site, listings, boards, limit, seen, pages=(2, 3)):
    for page in pages:
        for listing in listings:
            path = urlsplit(listing).path.rstrip("/")
            if boards[path]["new_topics"] >= limit:
                continue
            board = path.rsplit("/", 1)[-1]
            page_url = f"{listing.rstrip('/')}/paged/{page}/"
            try:
                found = discover(site, page_url, fetch_source(page_url), seen)
            except ValueError as error:
                emit("listing_unavailable", site=site, board=board, page=page, reason=str(error))
                continue
            emit("listing_checked", site=site, board=board, page=page, candidates=len(found))
            seen.update(found)
            yield from found.items()


def collect_candidates(site, source, eligible, limit, export_dir, listings=(), excluded=(), older_pages=(2, 3)):
    # The site's original IDs still deduplicate topics across boards. Only the
    # successful import count is scoped to each configured automatic listing.
    boards = {urlsplit(url).path.rstrip("/"): Counter() for url in listings}
    if not boards:
        boards[""] = Counter()
    total = Counter()
    target = limit * len(boards)
    older = older_board_candidates(site, listings, boards, limit, {*excluded, *eligible}, older_pages) if listings else ()
    for identifier, url in chain(eligible.items(), older):
        if total["new_topics"] >= target:
            break
        board = urlsplit(url).path.rstrip("/").rpartition("/")[0] if listings else ""
        counts = boards[board]
        if counts["new_topics"] >= limit:
            continue
        try:
            n_topics, n_comments, n_dupes = collect_one(site, source, identifier, url, export_dir)
            outcome = Counter(new_topics=n_topics, new_comments=n_comments, duplicates=n_dupes)
        except RejectedCandidate:
            outcome = Counter(rejected=1)
        except ValueError:
            outcome = Counter(errors=1)
        counts.update(outcome)
        total.update(outcome)
    if listings:
        for board, counts in boards.items():
            emit("board_summary", site=site, board=board.rsplit("/", 1)[-1],
                 new_topics=counts["new_topics"], new_comments=counts["new_comments"],
                 duplicates=counts["duplicates"], rejected=counts["rejected"],
                 errors=counts["errors"], target=limit)
    return total, target


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
    total_topics = total_comments = total_duplicates = errors = rejected = total_target = 0
    for site in sites:
        source = sources[site]
        if req["mode"] == "collect" and not available(source):
            emit("source_not_enabled", site=site,
                 reason="source_not_enabled_or_parser_not_verified")
            continue
        explicit = req["candidates"].get(site, [])
        listings = (source.get("listings", [])[:5] if source.get("limit_per_listing") is True
                    and req["mode"] == "collect" and not explicit and not args.export_dir else [])
        site_target = req["limit"] * max(1, len(listings)) if req["mode"] == "collect" else 0
        total_target += site_target
        try:
            excluded = excluded_ids(site)
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
                candidates = discover_source(source, excluded, cap=60 * max(1, len(listings)))
            eligible = {identifier: url for identifier, url in candidates.items() if identifier not in excluded}
            emit("plan", site=site, candidates=len(candidates), excluded=len(candidates)-len(eligible),
                 eligible=len(eligible), import_allowed=available(source))
            if req["mode"] == "inspect":
                # Explicit inspection can verify sources already marked completed.
                # Automatic inspect still only probes newly discovered candidates.
                inspection = candidates if explicit else eligible
                for identifier, url in list(inspection.items())[:10]:
                    try:
                        if site in PAGINATED_SITES:
                            draft, meta = parse_topic_pages(site, identifier, url, fetch_source(url), fetch_source)
                        else:
                            draft = parse_topic(site, identifier, url, fetch_source(url))
                            meta = {"source_total": len(flatten(draft.get("comments", []))),
                                    "capped": False, "pages": 1}
                        # Preserve legacy completed audits; new candidates use the import policy.
                        if excluded.get(identifier) != "completed":
                            clean_collected_draft(draft)
                        count = validate(draft, allow_no_replies=site in ARTICLE_SOURCES)
                        emit("parser_probe_pagination", site=site, source_id=identifier,
                             pages=meta["pages"], source_total=meta["source_total"],
                             captured=count, capped=meta["capped"])
                        emit("parser_probe_ok", site=site, source_id=identifier,
                             replies=count, source_url=url)
                        if excluded.get(identifier) == "completed":
                            audit_completed(site, identifier, url, draft, count)
                    except ValueError as error:
                        emit("parser_probe_failed", site=site, source_id=identifier,
                             reason=str(error), source_url=url)
                        errors += 1
                    time.sleep(1)
                continue
            if not available(source):
                emit("source_not_enabled", site=site, reason="reuse_or_parser_verification_required")
                continue
            counts, target = collect_candidates(
                site, source, eligible, req["limit"], args.export_dir, listings, excluded,
                older_pages_for_request(req["request_id"]))
            total_topics += counts["new_topics"]
            total_comments += counts["new_comments"]
            total_duplicates += counts["duplicates"]
            rejected += counts["rejected"]
            errors += counts["errors"]
            emit("site_summary", site=site, new_topics=counts["new_topics"],
                 new_comments=counts["new_comments"], duplicates=counts["duplicates"],
                 rejected=counts["rejected"], errors=counts["errors"],
                 target=target, shortfall=max(0, target-counts["new_topics"]))
        except (ValueError, KeyError, TypeError) as error:
            errors += 1
            emit("site_error", site=site, reason=str(error))
            if site_target:
                emit("site_summary", site=site, new_topics=0, new_comments=0,
                     duplicates=0, rejected=0, errors=1, target=site_target, shortfall=site_target)
    emit("run_summary", new_topics=total_topics, new_comments=total_comments,
         duplicates=total_duplicates, rejected=rejected, errors=errors,
         target=total_target, shortfall=max(0, total_target-total_topics),
         ready_for_unattended_collect=bool(sum(available(s) for s in sources.values())))
    if errors:
        return 1
    if req["mode"] == "collect" and total_topics == 0:
        return 2  # A safe, visible failure, NEVER a green zero-post success.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, TypeError, KeyError, OSError) as error:
        emit("collector_error", reason=str(error))
        raise SystemExit(1) from None
