"""Post a sanitized DEV collector status summary in GitHub (no user content).

Only invoked after GitHub Actions collector job. Never writes to forum DB, never
logs the source post/replies or claim tokens. Repo writes are limited to docs/.
"""
import base64
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPO = "119shenhao/gambling"
DEST = "docs/GAMBLING_COLLECTOR_LATEST.json"
SAFE_EVENTS = {
    "readiness", "plan", "parser_probe_pagination", "parser_probe_ok",
    "parser_probe_failed", "imported", "duplicate", "site_summary",
    "run_summary", "completed_audit_ok", "readback_pending_review_verified",
    "candidate_rejected", "candidate_failed", "source_not_enabled",
    "site_error", "claim_skipped", "source_reply_cap",
    "listing_checked", "listing_unavailable",
}
SAFE_TEXT = {"site", "source_id", "topic_id", "event"}
SAFE_NUM = {"importable_sources", "configured_sources", "candidates", "excluded",
            "eligible", "replies", "new_topics", "new_comments", "duplicates",
            "rejected", "errors", "target", "pages", "source_total", "captured",
            "stored", "public", "pending_review", "limit"}
SAFE_BOOL = {"preview", "capped", "import_allowed", "ready_for_unattended_collect"}
REASON_CODES = ("http_403", "http_404", "http_429", "network_error_or_timeout",
                "v2ex_reply_total_changed", "v2ex_reply_page_incomplete",
                "v2ex_page_size_unverified", "v2ex_reply_pages_mismatch",
                "v2ex_only_private_identifier", "v2ex_empty_text",
                "v2ex_invalid_media_url", "v2ex_reply_body_missing",
                "readback_count_mismatch", "readback_moderation_count_unverified",
                "readback_reply_body_mismatch", "readback_topic_mismatch",
                "completed_topic_not_visible_in_dev_feed", "preview_not_ready",
                "v2ex_private_identifier", "long_start_not_staging",
                "long_finish_not_confirmed", "source_not_enabled_or_parser_not_verified")
SITE_PATTERN = re.compile(r"^[a-z0-9_-]{2,32}$")
SOURCE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
TOPIC_PATTERN = re.compile(r"^[0-9a-f-]{36}$")


def public_event(raw):
    if not isinstance(raw, dict) or raw.get("event") not in SAFE_EVENTS:
        return None
    event = {"event": raw["event"]}
    for key in SAFE_TEXT:
        value = raw.get(key)
        if not isinstance(value, str):
            continue
        pattern = (SITE_PATTERN if key == "site" else
                   TOPIC_PATTERN if key == "topic_id" else
                   SOURCE_PATTERN if key == "source_id" else None)
        if pattern and pattern.fullmatch(value):
            event[key] = value
    for key in SAFE_NUM:
        value = raw.get(key)
        if type(value) is int and 0 <= value <= 1_000_000:
            event[key] = value
    for key in SAFE_BOOL:
        value = raw.get(key)
        if type(value) is bool:
            event[key] = value
    if raw.get("reason") in REASON_CODES:
        event["reason"] = raw["reason"]
    elif "reason" in raw:
        event["reason"] = "other_error"
    return event


def api(url, token, payload=None):
    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "gambling-collector-summary"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=json.dumps(payload).encode() if payload else None,
                  headers=headers, method="PUT" if payload else "GET")
    with urlopen(req, timeout=20) as response:
        return json.load(response)


def main():
    token = os.getenv("GITHUB_TOKEN", "")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    branch = os.getenv("GITHUB_REF_NAME", "")
    run = os.getenv("GITHUB_RUN_ID", "")
    sha = os.getenv("GITHUB_SHA", "")
    result = os.getenv("COLLECTOR_JOB_RESULT", "")
    if (not token or repo != REPO or branch != "dev" or not run.isdecimal()
            or not re.fullmatch(r"[0-9a-f]{40}", sha)
            or result not in ("success", "failure", "cancelled", "skipped")):
        raise ValueError("invalid_collector_report_environment")
    events = []
    raw_file = Path("collector-events.jsonl")
    if raw_file.is_file():
        if raw_file.stat().st_size > 1_000_000:
            raise ValueError("collector_log_too_large")
        for line in raw_file.read_text(encoding="utf-8").splitlines():
            try:
                source = json.loads(line)
            except ValueError:
                continue
            record = public_event(source)
            if record is not None:
                events.append(record)
    summary = next((x for x in reversed(events) if x["event"] == "run_summary"), None)
    report = {
        "report_type": "gambling_dev_collector_sanitized",
        "run_id": int(run),
        "run_url": f"https://github.com/{REPO}/actions/runs/{run}",
        "trigger_commit": sha,
        "collector_job_result": result,
        "has_run_summary": summary is not None,
        "run_summary": summary,
        "events": events[-100:],
        "production_database_writes": False,
    }
    url = f"https://api.github.com/repos/{REPO}/contents/{DEST}"
    try:
        old = api(url + "?ref=dev", token)
        oldsha = old["sha"]
    except HTTPError as error:
        if error.code != 404:
            raise
        oldsha = None
    payload = {
        "message": "ci(collector): record sanitized DEV import and audit result",
        "branch": "dev",
        "content": base64.b64encode((json.dumps(report, sort_keys=True,
            ensure_ascii=False, indent=2) + "\n").encode()).decode(),
    }
    if oldsha:
        payload["sha"] = oldsha
    api(url, token, payload)
    print(json.dumps({"status": "saved", "run_id": int(run),
                      "collector_job_result": result,
                      "summary": summary,
                      "safe_events": len(events)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
