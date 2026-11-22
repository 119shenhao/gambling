"""Write a narrow, sanitized DEV probe report back to this repository.

Invoked only from the dedicated GitHub Actions report job with a scoped
GITHUB_TOKEN. Does not include any user content, authors, or source cookies.
Never updates source enablement or posts to the community API.
"""
import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPO = "119shenhao/gambling"
DEST = "docs/GAMBLING_CHINESE_PROBE_LATEST.json"
FIELDS = ("source_total", "captured", "pages", "capped")

def input_status(filename):
    path = Path(filename)
    if not path.is_file() or path.stat().st_size > 50_000:
        return {"status": "result_missing"}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        return {"status": "invalid_json"}
    status = record.get("status")
    if status not in ("parser_ok", "parser_rejected"):
        return {"status": "invalid_probe_status"}
    result = {"status": status}
    for field in FIELDS:
        value = record.get(field)
        if (type(value) is bool if field == "capped" else
                type(value) is int and 0 <= value <= 1_000_000):
            result[field] = value
    reason = record.get("reason")
    if isinstance(reason, str) and status == "parser_rejected":
        # Only machine-readable exception names; never echo external content.
        import re
        match = re.match(r"^[a-z][a-z0-9_]{0,59}$",reason)
        result["reason"] = reason if match else "unclassified_parser_error"
    return result

def douban_status(filename):
    path=Path(filename)
    if not path.is_file() or path.stat().st_size > 50_000:
        return {"status":"result_missing"}
    try:
        lines=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (ValueError,UnicodeError):
        return {"status":"invalid_json"}
    found=[record for record in lines if record.get("source")=="douban"]
    if len(found)!=1:
        return {"status":"no_single_douban_record"}
    raw=found[0]
    result={"status": raw.get("status") if raw.get("status") in ("ok","unavailable") else "unknown"}
    for field in ("public_topic_links","html_bytes"):
        val=raw.get(field)
        if type(val) is int and 0<=val<=5_000_000:
            result[field]=val
    reason=raw.get("reason")
    if isinstance(reason,str) and reason in (
            "http_403","http_404","http_429","network_error_or_timeout",
            "source_html_too_large","not_html","unsafe_source_redirect"):
        result["reason"]=reason
    return result

def api(url, token, payload=None):
    headers={"Authorization":"Bearer "+token,
             "Accept":"application/vnd.github+json",
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"gambling-source-probe-reporter"}
    if payload is not None:
        headers["Content-Type"]="application/json"
    request=Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                    headers=headers,method="PUT" if payload is not None else "GET")
    with urlopen(request,timeout=20) as response:
        return json.load(response)

def main():
    token=os.environ.get("GITHUB_TOKEN","")
    repo=os.environ.get("GITHUB_REPOSITORY","")
    ref=os.environ.get("GITHUB_REF_NAME","")
    run=os.environ.get("GITHUB_RUN_ID","")
    sha=os.environ.get("GITHUB_SHA","")
    job=os.environ.get("PROBE_JOB_RESULT","")
    if (not token or repo != REPO or ref != "dev" or not run.isdecimal()
            or len(sha)!=40 or job not in ("success","failure","cancelled","skipped")):
        raise SystemExit("invalid_report_environment")
    report={
        "report_type":"gambling_dev_chinese_sources_read_only_probe",
        "run_id":int(run),
        "run_url":f"https://github.com/{REPO}/actions/runs/{run}",
        "trigger_commit":sha,
        "probe_job_result":job,
        "v2ex":input_status("v2ex-probe.json"),
        "douban":douban_status("chinese-probe.jsonl"),
        "developer_db_writes":False,
        "source_enabled_by_this_run":False,
    }
    url=f"https://api.github.com/repos/{REPO}/contents/{DEST}"
    try:
        old=api(url+"?ref=dev",token)
        previous_sha=old["sha"]
    except HTTPError as error:
        if error.code!=404:
            raise
        previous_sha=None
    payload={
        "message":"ci(probe): record sanitized V2EX and Douban read-only test status",
        "content":base64.b64encode((json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")).decode("ascii"),
        "branch":"dev",
    }
    if previous_sha:
        payload["sha"]=previous_sha
    api(url,token,payload)
    print(json.dumps({"status":"report_saved","run_id":int(run),
                      "v2ex":report["v2ex"],"douban":report["douban"]},
                     ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
